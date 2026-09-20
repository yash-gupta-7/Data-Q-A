"""File upload endpoint — ingestion pipeline."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, File, UploadFile

from app.api.response import err, ok
from app.catalog.registry import get_dataframes_from_duckdb, register_dataset
from app.catalog.relationships import detect_relationships
from app.ingestion.csv import CSVParseError, check_duplicate_columns, parse_csv
from app.ingestion.excel import ExcelParseError, check_duplicate_columns as excel_check_dups, parse_excel
from app.ingestion.normalize import normalize_dataframe
from app.ingestion.profiler import profile_dataframe
from app.models.dataset import DatasetStatus
from app.models.session import UploadedFile, DataReadinessSummary
from app.security.files import (
    FileSecurityError,
    generate_internal_filename,
    validate_extension,
    validate_file_size,
    validate_filename,
    validate_mime_type,
    validate_session_capacity,
)
from app.session.manager import get_raw_dir, get_session, get_session_and_connection

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/sessions/{session_id}/files")
async def upload_file(session_id: str, file: UploadFile = File(...)):
    """
    Upload a CSV or XLSX file. Runs full ingestion pipeline:
    validate → parse → normalize → profile → register → detect relationships
    """
    import uuid

    session, conn = get_session_and_connection(session_id)
    if session is None:
        return err("SESSION_NOT_FOUND", f"Session '{session_id}' not found.")

    # ── 1. Security validation ─────────────────────────────────────────────
    original_filename = file.filename or "upload"
    try:
        safe_name = validate_filename(original_filename)
        ext = validate_extension(safe_name)
    except FileSecurityError as e:
        return err(e.code, e.message)

    file_bytes = await file.read()

    try:
        validate_file_size(len(file_bytes), safe_name)
        current_size = sum(f.size_bytes for f in session.files)
        validate_session_capacity(len(session.files), current_size, len(file_bytes))
        mime = validate_mime_type(file_bytes, safe_name)
    except FileSecurityError as e:
        return err(e.code, e.message)

    # ── 2. Save raw file with UUID name ────────────────────────────────────
    file_id = uuid.uuid4().hex
    internal_name = generate_internal_filename(safe_name)
    raw_dir = get_raw_dir(session)
    raw_path = os.path.join(raw_dir, internal_name)

    with open(raw_path, "wb") as f_out:
        f_out.write(file_bytes)

    uploaded_file = UploadedFile(
        file_id=file_id,
        original_filename=safe_name,
        internal_path=raw_path,
        size_bytes=len(file_bytes),
        mime_type=mime,
    )
    session.files.append(uploaded_file)

    # ── 3. Parse ──────────────────────────────────────────────────────────
    datasets_created = []
    skipped_sheets = []
    warnings = []

    if ext == ".csv":
        try:
            raw_df = parse_csv(file_bytes, safe_name)
        except CSVParseError as e:
            return err("PARSE_ERROR", str(e))

        dups = check_duplicate_columns(raw_df, safe_name)
        if dups:
            return err(
                "DUPLICATE_COLUMNS",
                f"File '{safe_name}' has duplicate column names: {dups}. "
                "Please rename the columns and re-upload.",
                {"duplicates": dups},
            )

        norm_df = normalize_dataframe(raw_df)
        columns_info = profile_dataframe(norm_df)

        # Collect data quality warnings
        for col in columns_info:
            if col.quality.null_pct > 10:
                warnings.append(f"{col.quality.null_pct:.1f}% missing values in '{col.name}'")

        display_name = os.path.splitext(safe_name)[0]
        try:
            dataset = register_dataset(
                session=session,
                df=norm_df,
                conn=conn,
                display_name=display_name,
                source_file=safe_name,
                source_file_id=file_id,
                columns_info=columns_info,
                warnings=warnings,
            )
            uploaded_file.dataset_ids.append(dataset.dataset_id)
            datasets_created.append(dataset)
        except Exception as e:
            logger.exception("Failed to register dataset for %s", safe_name)
            return err("REGISTRATION_ERROR", f"Failed to register dataset: {e}")

    elif ext == ".xlsx":
        try:
            sheets = parse_excel(file_bytes, safe_name)
        except ExcelParseError as e:
            return err("PARSE_ERROR", str(e))

        for sheet_name, sheet_df in sheets.items():
            if sheet_df is None:
                skipped_sheets.append(sheet_name)
                continue

            dups = excel_check_dups(sheet_df)
            if dups:
                skipped_sheets.append(f"{sheet_name} (duplicate columns: {dups})")
                continue

            norm_df = normalize_dataframe(sheet_df)
            columns_info = profile_dataframe(norm_df)

            sheet_warnings = []
            for col in columns_info:
                if col.quality.null_pct > 10:
                    sheet_warnings.append(f"{col.quality.null_pct:.1f}% missing in '{col.name}'")

            display_name = f"{os.path.splitext(safe_name)[0]} / {sheet_name}"
            try:
                dataset = register_dataset(
                    session=session,
                    df=norm_df,
                    conn=conn,
                    display_name=display_name,
                    source_file=safe_name,
                    source_file_id=file_id,
                    columns_info=columns_info,
                    sheet_name=sheet_name,
                    warnings=sheet_warnings,
                )
                uploaded_file.dataset_ids.append(dataset.dataset_id)
                datasets_created.append(dataset)
                warnings.extend(sheet_warnings)
            except Exception as e:
                logger.exception("Failed to register sheet %s from %s", sheet_name, safe_name)
                skipped_sheets.append(f"{sheet_name} (error: {e})")

    # ── 4. Relationship detection ──────────────────────────────────────────
    active_datasets = session.get_active_datasets()
    if len(active_datasets) >= 2:
        dfs = get_dataframes_from_duckdb(session, conn)
        new_relationships = detect_relationships(active_datasets, dfs)
        # Merge with existing (avoid duplicates by pair key)
        existing_keys = {
            (r.left_dataset, r.left_column, r.right_dataset, r.right_column)
            for r in session.relationships
        }
        for rel in new_relationships:
            key = (rel.left_dataset, rel.left_column, rel.right_dataset, rel.right_column)
            if key not in existing_keys:
                session.relationships.append(rel)

    # ── 5. Update readiness summary ───────────────────────────────────────
    all_active = session.get_active_datasets()
    session.readiness = DataReadinessSummary(
        files_processed=len(session.files),
        datasets_detected=len(all_active),
        total_rows=sum(d.row_count for d in all_active),
        total_columns=sum(d.column_count for d in all_active),
        relationships=[
            {
                "left": f"{r.left_dataset}.{r.left_column}",
                "right": f"{r.right_dataset}.{r.right_column}",
                "status": r.status.value,
                "score": r.evidence.evidence_score,
            }
            for r in session.relationships
        ],
        warnings=warnings,
        skipped_sheets=skipped_sheets,
    )

    return ok({
        "file_id": file_id,
        "original_filename": safe_name,
        "datasets_created": [
            {
                "dataset_id": d.dataset_id,
                "display_name": d.display_name,
                "row_count": d.row_count,
                "column_count": d.column_count,
            }
            for d in datasets_created
        ],
        "skipped_sheets": skipped_sheets,
        "warnings": warnings,
        "readiness": {
            "files_processed": session.readiness.files_processed,
            "datasets_detected": session.readiness.datasets_detected,
            "total_rows": session.readiness.total_rows,
            "total_columns": session.readiness.total_columns,
            "relationships": session.readiness.relationships,
            "warnings": session.readiness.warnings,
            "skipped_sheets": session.readiness.skipped_sheets,
        },
    })
