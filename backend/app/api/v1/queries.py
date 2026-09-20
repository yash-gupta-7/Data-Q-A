"""Query endpoint — full analytical pipeline."""

from __future__ import annotations

import hashlib
import logging
import time

from fastapi import APIRouter
from pydantic import BaseModel

from app.analyst.compiler import SQLCompileError, SQLCompiler
from app.analyst.evidence import compute_evidence_score
from app.analyst.executor import ExecutionError, execute_query
from app.analyst.explainer import Explainer
from app.analyst.planner import Planner
from app.analyst.result_validator import validate_result
from app.analyst.validator import PlanValidator
from app.api.response import err, ok
from app.config import get_settings
from app.llm.base import LLMError
from app.llm.openai_compatible import get_llm_provider
from app.models.plan import PlanStatus
from app.models.result import ProvenanceInfo, QueryResponse
from app.models.session import ConversationMessage
from app.security.sql import SQLSafetyError, validate_sql_safety
from app.session.manager import get_session_and_connection
from app.visualization.selector import get_compatible_chart_types, select_chart

logger = logging.getLogger(__name__)
router = APIRouter()


class QueryRequest(BaseModel):
    question: str


@router.post("/sessions/{session_id}/queries")
async def submit_query(session_id: str, body: QueryRequest):
    """
    Full analytical pipeline:
    question → plan → validate → compile → safety → execute → verify → evidence → explain → respond
    """
    session, conn = get_session_and_connection(session_id)
    if session is None:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")

    question = body.question.strip()
    if not question:
        return err("EMPTY_QUESTION", "Question cannot be empty.")

    active_datasets = session.get_active_datasets()
    if not active_datasets:
        return err("NO_DATASETS", "Please upload at least one file before asking questions.")

    settings = get_settings()
    stages: list[str] = []
    start_total = time.perf_counter()

    # ── Cache key ────────────────────────────────────────────────────────
    question_hash = hashlib.sha256(question.encode()).hexdigest()[:12]
    cache_key = f"{question_hash}:{len(active_datasets)}:{settings.prompt_version}"
    cached = session._planner_cache.get(cache_key)

    # ── Add user message to conversation ─────────────────────────────────
    session.conversation.add_user_message(question)
    recent_messages = session.conversation.get_context_messages()[:-1]  # exclude current

    # ── Step 1: Planning ─────────────────────────────────────────────────
    stages.append("Analyzing your question...")
    llm = get_llm_provider()

    try:
        if cached:
            plan = cached
            stages.append("✓ Retrieved cached analytical plan")
        else:
            planner = Planner(llm)
            plan = await planner.plan(
                question=question,
                datasets=active_datasets,
                relationships=session.relationships,
                recent_messages=recent_messages,
            )
            session._planner_cache[cache_key] = plan
            stages.append("✓ Built analytical plan")
    except LLMError as e:
        session.conversation.add_assistant_message(
            "I'm having trouble connecting to the AI model. Please check the LLM configuration."
        )
        return err("LLM_ERROR", e.message, {"code": e.code})

    # ── Plan status: clarification or unsupported ─────────────────────────
    if plan.status == PlanStatus.CLARIFICATION:
        response = QueryResponse(
            question=question,
            plan_status="clarification",
            clarification_question=plan.clarification_question,
            processing_stages=stages,
        )
        session.conversation.add_assistant_message(
            plan.clarification_question or "Could you clarify your question?",
            response,
        )
        return ok(response.model_dump())

    if plan.status == PlanStatus.UNSUPPORTED:
        response = QueryResponse(
            question=question,
            plan_status="unsupported",
            unsupported_reason=plan.unsupported_reason,
            processing_stages=stages,
        )
        session.conversation.add_assistant_message(
            plan.unsupported_reason or "This type of analysis is not currently supported.",
            response,
        )
        return ok(response.model_dump())

    # ── Step 2: Plan validation ───────────────────────────────────────────
    stages.append("✓ Identified relevant datasets")
    validator = PlanValidator(active_datasets, session.relationships)
    plan_validation = validator.validate(plan)

    if plan_validation.status.value == "BLOCKED":
        response = QueryResponse(
            question=question,
            plan_status="ready",
            validation=plan_validation,
            explanation=None,
            processing_stages=stages,
        )
        msg = f"I couldn't build a valid query: {plan_validation.blocking_reason}"
        session.conversation.add_assistant_message(msg, response)
        return ok(response.model_dump())

    stages.append("✓ Validated analytical plan")

    # ── Step 3: SQL Compilation ───────────────────────────────────────────
    compiler = SQLCompiler(active_datasets)
    compiled = None
    try:
        compiled = compiler.compile(plan)
        stages.append("✓ Compiled query")
    except SQLCompileError as e:
        evidence = compute_evidence_score(plan, None, None, plan_validation, None, False)
        response = QueryResponse(
            question=question,
            plan_status="ready",
            validation=evidence,
            processing_stages=stages,
        )
        session.conversation.add_assistant_message(f"Query compilation failed: {e.message}", response)
        return ok(response.model_dump())

    # ── Step 4: SQL Safety ────────────────────────────────────────────────
    sql_safe = True
    try:
        validate_sql_safety(compiled.sql)
        stages.append("✓ SQL safety validated")
    except SQLSafetyError as e:
        sql_safe = False
        logger.error("SQL SAFETY FAILURE: %s\nSQL: %s", e.message, compiled.sql)
        evidence = compute_evidence_score(plan, compiled, None, plan_validation, None, False)
        response = QueryResponse(
            question=question,
            plan_status="ready",
            validation=evidence,
            processing_stages=stages,
        )
        session.conversation.add_assistant_message("Query blocked for safety reasons.", response)
        return ok(response.model_dump())

    # ── Step 5: Execute ───────────────────────────────────────────────────
    result = None
    try:
        result = execute_query(conn, compiled)
        stages.append(f"✓ Executed query ({result.execution_time_ms:.0f}ms, {result.row_count} rows)")
    except ExecutionError as e:
        evidence = compute_evidence_score(plan, compiled, None, plan_validation, None, sql_safe)
        response = QueryResponse(
            question=question,
            plan_status="ready",
            validation=evidence,
            processing_stages=stages,
        )
        session.conversation.add_assistant_message(f"Query failed: {e.message}", response)
        return err(e.code, e.message)

    # ── Step 6: Result Validation ─────────────────────────────────────────
    result_validation = validate_result(result, plan)
    stages.append("✓ Verified result")

    # ── Step 7: Evidence Score ────────────────────────────────────────────
    evidence = compute_evidence_score(plan, compiled, result, plan_validation, result_validation, sql_safe)

    # ── Step 8: Visualization ─────────────────────────────────────────────
    chart_spec = select_chart(plan, result, plan.visualization)
    compatible_charts = get_compatible_chart_types(chart_spec)
    chart_spec["compatible_types"] = compatible_charts
    stages.append("✓ Generated visualization")

    # ── Step 9: Explain ───────────────────────────────────────────────────
    explainer = Explainer(llm)
    try:
        explanation = await explainer.explain(
            question=question,
            result=result,
            validation=evidence,
            compiled=compiled,
            assumptions=plan.assumptions,
        )
        stages.append("✓ Generated explanation")
    except Exception as e:
        logger.warning("Explainer failed: %s", e)
        from app.analyst.explainer import _fallback_explanation
        explanation = _fallback_explanation(question, result, evidence, plan.assumptions)

    # ── Step 10: Provenance ───────────────────────────────────────────────
    provenance = ProvenanceInfo(
        datasets_used=compiled.datasets_used,
        columns_used=list(set(compiled.columns_used)),
        rows_analyzed=result.row_count,
        operations_summary=compiled.operations_summary,
        compiled_sql=compiled.sql,
    )

    # ── Assemble response ─────────────────────────────────────────────────
    response = QueryResponse(
        question=question,
        plan_status="ready",
        result=result,
        validation=evidence,
        explanation=explanation,
        provenance=provenance,
        visualization=chart_spec,
        processing_stages=stages,
    )

    session.conversation.add_assistant_message(
        explanation.answer if explanation else "Analysis complete.",
        response,
    )

    total_ms = (time.perf_counter() - start_total) * 1000
    logger.info(
        "Query completed: session=%s hash=%s status=%s rows=%d total_ms=%.0f",
        session_id,
        question_hash,
        evidence.status.value,
        result.row_count,
        total_ms,
    )

    return ok(response.model_dump())


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """Get conversation history for a session."""
    session, _ = get_session_and_connection(session_id)
    if session is None:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")

    messages = []
    for msg in session.conversation.messages:
        m = {
            "role": msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat(),
        }
        if msg.query_response:
            m["query_response"] = msg.query_response.model_dump()
        messages.append(m)

    return ok({"messages": messages, "count": len(messages)})
