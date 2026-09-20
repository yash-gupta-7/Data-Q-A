# Data Q&A — Architecture, Decisions & Future Roadmap
*Final Submission Write-Up (1-Page Summary)*

---

## 1. Approach & Technical Architecture

The core philosophy of **Data Q&A** is simple yet rigorous: **The LLM interprets and explains; deterministic code validates and calculates.** 

Rather than relying on unconstrained LLM code execution (e.g., raw `eval` or unsafe python scripts) or trusting LLMs with arithmetic calculations, we designed a closed-loop analytical pipeline:

1. **Ingestion & Auto-Profiling Layer**: When CSV or multi-sheet Excel files are uploaded, the engine strips malicious formula injection vectors (`=`, `+`, `-`, `@`), detects delimiters, infers strict types, profiles null ratios/distributions, identifies primary/foreign key candidates across files, and registers tables in an in-memory **DuckDB** OLAP instance per user session.
2. **Deterministic Query Planning**: User natural language questions are sanitized against prompt injection and mapped via Gemini into a structured, typed analytical intent (filters, groupings, aggregations, joins, sort criteria).
3. **Safe SQL Compilation & Execution**: The intent is compiled into parameterized, sandboxed DuckDB SQL queries. SQL safety guards enforce read-only `SELECT` queries, eliminating any risk of data mutation or SQL injection.
4. **Verification & Provenance**: Query results pass through a verification engine that checks for empty sets, anomalies, and schema invariants before sending both the numerical truth and provenance metadata to the user.
5. **Adaptive UI & Visualizations**: The React/TypeScript interface renders conversational threads, evidence accordions (showing SQL, execution metrics, and dataset sources), and dynamically selects optimal Recharts visualizations (bar, line, scatter, or pie).

```
[CSV / XLSX Upload] ──► [Ingestion & Sanitization] ──► [DuckDB In-Memory OLAP]
                                                              ▲
[User Question]     ──► [Gemini Query Planner]   ──► [SQL Compiler & Validator]
                                                              │
[React / Recharts]  ◄── [Explanation Engine]     ◄── [Result Verification]
```

---

## 2. Key Decisions & Rationale

- **DuckDB over Raw Pandas / Dynamic Python Scripts:** DuckDB provides lightning-fast columnar vectorized execution, native SQL support for multi-table joins and window functions, and an isolated, memory-safe analytical engine without exposing the host OS to arbitrary code execution risks.
- **Structured Schema & Metadata Context Injection:** Rather than passing raw dataset rows into the LLM context (which balloons token costs and breaches data privacy), we inject only column schemas, types, top distinct values, and detected cross-table relationships.
- **Session-Isolated Ephemeral Workspaces:** Each session maintains an independent DuckDB database and metadata catalog with automatic TTL cleanup, ensuring zero data leakage between concurrent users.
- **Conversational Memory with Intent Merging:** Follow-up questions (e.g., *"Filter that down to only Q3"*) merge with preceding analytical intents to maintain context across multi-turn investigations.

---

## 3. What I Would Build Next

1. **Proactive Anomaly & Insight Discovery Agent:** Automatically compute statistical deviations, correlation matrices, and seasonal anomalies upon upload to suggest "Questions You Should Ask" before the user types anything.
2. **Direct Enterprise Data Connectors:** Extend beyond static CSV/XLSX uploads to include live connectors for PostgreSQL, Snowflake, Google BigQuery, and S3 parquet lakes with streaming ingest.
3. **Multi-Modal Export & Automated Slide Deck Generation:** One-click generation of presentation-ready executive briefs (PDF/PPTX) combining AI narratives, generated charts, and verified SQL audit logs.
4. **Semantic Layer & Custom Metric Governance:** Allow enterprise teams to define business metrics (e.g., *ARR*, *Churn Rate*, *Gross Margin*) in a YAML semantic catalog so all LLM-generated SQL adheres to standard company definitions.
