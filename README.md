# 🔍 Data Q&A — AI-Powered Multi-Dataset Data Analyst

<div align="center">

**An enterprise-grade conversational data analysis platform that turns multi-file CSV and Excel datasets into verified numerical answers, rich interactive visualizations, and full analytical provenance.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-In--Memory_OLAP-FFF000.svg?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini_Flash-8E75B2.svg?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-94_Passing-brightgreen.svg?style=for-the-badge)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

</div>

---

## 📖 Table of Contents

- [🎯 Core Philosophy](#-core-philosophy)
- [📦 Deliverables Summary](#-deliverables-summary)
- [✨ Key Features](#-key-features)
- [🏗️ System Architecture](#-system-architecture)
- [🛠️ Tech Stack](#-tech-stack)
- [🚀 Quick Start (Local & Docker)](#-quick-start)
- [📊 Demo Walkthrough & Sample Datasets](#-demo-walkthrough--sample-datasets)
- [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
- [🛡️ Security & Guardrails](#-security--guardrails)
- [📡 API Specification](#-api-specification)
- [📁 Project Directory Structure](#-project-directory-structure)
- [🗺️ What's Next (Roadmap)](#-whats-next-roadmap)
- [📄 Documentation & Links](#-documentation--links)

---

## 🎯 Core Philosophy

> **"The LLM interprets. Deterministic code validates. DuckDB calculates. Result verification confirms. The LLM explains. The frontend visualizes."**

Traditional LLM data agents frequently suffer from:
1. **Arithmetic Hallucinations:** Large Language Models are probabilistic text generators, not arithmetic calculators.
2. **Security Vulnerabilities:** Running arbitrary LLM-generated Python scripts with `exec()` or `eval()` exposes hosts to remote code execution.
3. **Data Privacy Leaks:** Shoveling raw user dataset rows into LLM prompt contexts incurs massive token costs and breaches privacy.

**Data Q&A solves this with a hybrid architecture:**
- **Zero Calculation Hallucinations:** Raw data stays in an isolated in-memory **DuckDB OLAP** database. 
- **Deterministic SQL Generation:** Natural language is parsed into structured analytical intents and compiled into parameterized, sandboxed SQL queries.
- **Strict Privacy Invariants:** Only sanitized schema metadata (column names, inferred types, null ratios, sample value ranges) is ever sent to Google Gemini.

---

## 📦 Deliverables Summary

| # | Deliverable | Description & Access |
|---|---|---|
| **1** | 🖥️ **Working Prototype** | • **Frontend:** `http://localhost:5173`<br>• **Backend API & Swagger:** `http://localhost:8000/docs`<br>• Step-by-step [Quick Start](#-quick-start) for local & Docker. |
| **2** | 📦 **Source Code Repository** | Complete, clean Git repository containing frontend, backend, test suite, and CI workflows. |
| **3** | 📝 **1-Page Architecture Write-Up** | [WRITEUP.md](WRITEUP.md) covering approach, design decisions, trade-offs, and future roadmap. |
| **4** | 📊 **Sample Datasets & Queries** | [sample_data/](sample_data/) with `customers.csv`, `orders.csv`, and multi-sheet `products.xlsx`. |

---

## ✨ Key Features

- 📁 **Multi-File & Multi-Sheet Ingestion**: Drag and drop multiple CSVs and Excel (`.xlsx`) workbooks into a single workspace. Supports multi-sheet parsing and automatically filters out non-tabular notes/metadata sheets.
- 🔗 **Cross-Dataset Relational Auto-Joins**: Automatically detects primary key / foreign key relationships across disparate files (e.g. `orders.customer_id` → `customers.customer_id`) and executes cross-table queries.
- 💬 **Conversational Context & Intent Merging**: Multi-turn dialogue support. Ask follow-up questions like *"Filter that down to only Q3"* or *"Now break it down by region"*, and the system merges conversational state seamlessly.
- 📊 **Dynamic Adaptive Visualizations**: Automatically evaluates result cardinality and data types to pick and render optimal Recharts (Bar, Line, Area, Scatter, and Pie).
- 🔍 **Auditability & Provenance Evidence**: Inspect the exact compiled DuckDB SQL query, execution timings, and source dataset lineage behind every response.
- 🛡️ **Multi-Tiered Security**:
  - **Formula Injection Defense:** Strips dangerous Excel/CSV prefixes (`=`, `+`, `-`, `@`, `\t`, `\r`).
  - **Prompt Injection Defense:** Regex and heuristic filters blocking jailbreak attempts and system override commands.
  - **Read-Only SQL AST Validation:** Strictly enforces `SELECT`-only execution. `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, and multi-statement queries are strictly blocked.
  - **PII Detection:** Automatically flags sensitive columns (SSN, credit card, email, phone numbers).

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           React 18 + TypeScript UI                          │
│  (Dataset Explorer · Chat Stream · Interactive Recharts · Provenance Modal)  │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ REST / SSE API
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                              FastAPI Backend                                │
│                                                                             │
│  ┌────────────────────────┐               ┌──────────────────────────────┐  │
│  │    Ingestion Layer     │               │       Security Guards        │  │
│  │  • CSV Sniffer / Delim │               │  • Formula Neutralization    │  │
│  │  • Multi-Sheet Excel   ├──────────────►│  • Prompt Injection Filter   │  │
│  │  • Normalization Engine│               │  • AST SQL Safety Validator  │  │
│  └───────────┬────────────┘               └──────────────┬───────────────┘  │
│              │                                           │                  │
│  ┌───────────▼────────────┐               ┌──────────────▼───────────────┐  │
│  │     Metadata Catalog   │               │      LLM Query Planner       │  │
│  │  • Statistical Profile │               │  • Natural Language Intent   │  │
│  │  • Auto-Relationship   │               │  • Gemini Flash LLM          │  │
│  └───────────┬────────────┘               └──────────────┬───────────────┘  │
│              │                                           │                  │
│  ┌───────────▼───────────────────────────────────────────▼───────────────┐  │
│  │                 Deterministic SQL Compiler & Runner                   │  │
│  │                (Session-Isolated In-Memory DuckDB OLAP)               │  │
│  └───────────────────────────────────┬───────────────────────────────────┘  │
│                                      │                                      │
│                        ┌─────────────▼───────────────┐                      │
│                        │ Result Verifier & Narrator  │                      │
│                        │ • Invariant Checks          │                      │
│                        │ • Insight Synthesis         │                      │
│                        └─────────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

| Layer | Technologies | Rationale |
|---|---|---|
| **Backend Engine** | Python 3.11+, FastAPI, Pydantic v2 | High-performance asynchronous API framework with type safety and automatic OpenAPI schema generation. |
| **Analytical OLAP** | DuckDB, Pandas, OpenPyXL | Fast in-memory columnar database with zero overhead, rich SQL-92 support, window functions, and cross-file joins. |
| **AI / LLM** | Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`) | Sub-second latency, structured JSON output mode, superior reasoning for semantic intent translation. |
| **Frontend UI** | React 18, TypeScript, Vite, TailwindCSS | Ultra-fast SPA with reactive state management, typed client models, and fluid animations. |
| **Visualizations** | Recharts, Lucide Icons | Responsive, accessible, SVG-based charting components (Bar, Line, Area, Scatter, Pie). |
| **DevOps & Testing** | Docker, Docker Compose, Pytest, Pytest-Asyncio | Hermetic containerization, 94 automated tests covering unit, security, integration, and E2E evaluation. |

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & **npm**
- **Google Gemini API Key** ([Get a free key here](https://aistudio.google.com/))
- *(Optional)* Docker & Docker Compose

---

### Option 1: Local Development Setup (Recommended)

#### 1. Clone the Repository
```bash
git clone https://github.com/yash-gupta-7/Data-Q-A.git
cd Data-Q-A
```

#### 2. Backend Setup
```bash
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and paste your GEMINI_API_KEY

# Start the FastAPI server
uvicorn app.main:app --reload --port 8000
```
Backend will be live at: `http://localhost:8000` (Interactive Swagger Docs: `http://localhost:8000/docs`)

#### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend

# Configure environment
cp .env.example .env

# Install dependencies and start Vite dev server
npm install
npm run dev
```
Frontend will be live at: `http://localhost:5173`

---

### Option 2: Docker Compose Setup

Run the entire application (Backend + Frontend) in one command:
```bash
# In project root
cp backend/.env.example backend/.env
# Edit backend/.env and add your GEMINI_API_KEY

docker-compose up --build
```
Access the application at [http://localhost:5173](http://localhost:5173).

---

## 🔑 Environment Configuration

### Backend (`backend/.env`)
| Variable | Description | Default / Example | Required |
|---|---|---|---|
| `GEMINI_API_KEY` | Google Gemini API key | `AIzaSy...` | ✅ Yes |
| `GEMINI_MODEL` | Gemini model variant | `gemini-2.5-flash` | ❌ No |
| `SECRET_KEY` | Session signing secret | `your-secret-key` | ❌ No |
| `ALLOWED_ORIGINS` | CORS allowed origins | `http://localhost:5173` | ❌ No |
| `MAX_FILE_SIZE_MB` | Upload file size ceiling | `50` | ❌ No |
| `SESSION_TTL_MINUTES` | In-memory session cleanup TTL | `60` | ❌ No |

### Frontend (`frontend/.env`)
| Variable | Description | Default | Required |
|---|---|---|---|
| `VITE_API_URL` | Base URL for the FastAPI backend | `http://localhost:8000` | ❌ No |

---

## 📊 Demo Walkthrough & Sample Datasets

We provide 3 sample datasets in [`sample_data/`](sample_data/) to test single-file, multi-file, and cross-sheet analysis:

```
sample_data/
├── customers.csv     # 10 customer profiles (ID, name, email, region, industry, signup date)
├── orders.csv        # 25 transaction records (order ID, customer ID, product ID, quantity, amount)
└── products.xlsx     # Multi-sheet workbook:
                      #   ├── Sheet 1: "Products" (ID, name, category, subcategory, unit price)
                      #   ├── Sheet 2: "Pricing Tiers" (tier, discount %, min quantity)
                      #   └── Sheet 3: "Notes" (informational notes, automatically skipped)
```

### Try These Example Questions:

#### 1. Single-Table Aggregations & Metrics
- *"What is the total revenue generated across all orders?"*
- *"Show the distribution of customers by industry."*
- *"What is the average order value?"*

#### 2. Cross-File Relational Joins (Multi-Table)
- *"What is the total revenue by product category?"* *(Joins `orders.csv` + `products.xlsx`)*
- *"Who are the top 5 customers by total spend and what industry are they in?"* *(Joins `customers.csv` + `orders.csv`)*
- *"Show revenue breakdown by customer region and product category."* *(Joins `customers.csv` + `orders.csv` + `products.xlsx`)*

#### 3. Time Series Trends
- *"Show monthly sales trends over time."*
- *"Which month had the highest order volume?"*

#### 4. Conversational Drilldown / Follow-Ups
- *Initial Question:* *"What are the top selling products?"*
- *Follow-up:* *"Filter that down to only the Software category."*
- *Follow-up:* *"Show this as a bar chart."*

---

## 🧪 Testing & Quality Assurance

The codebase includes an extensive suite of **94 automated tests** covering unit logic, security rules, integration pipelines, and golden evaluation questions.

```bash
cd backend
source .venv/bin/activate
PYTHONPATH=. pytest -v --tb=short
```

```
============================== 94 passed in 1.14s ==============================
```

### Test Coverage Highlights:
- **`tests/unit/test_csv_parser.py` & `test_excel_parser.py`**: Delimiter detection (comma, tab, semicolon), encoding fallbacks (UTF-8, Latin-1, UTF-8-BOM), null markers (`NA`, `null`, `-`), multi-sheet extraction.
- **`tests/unit/test_security.py` & `test_sanitize.py`**: Formula injection neutralization, prompt injection & jailbreak detection, filename sanitization, PII regex detection, AST SQL read-only validation.
- **`tests/unit/test_compiler.py`**: Deterministic DuckDB SQL compilation for filters, groupings, aggregations, joins, date truncations, and sorting.
- **`tests/integration/test_ingestion_pipeline.py`**: End-to-end multi-file upload, catalog schema registration, foreign key detection, and DuckDB table creation.
- **`tests/evaluation/test_golden_questions.py`**: Verification of deterministic analytical query results against baseline fixtures.

---

## 🛡️ Security & Guardrails

1. **Formula Injection Sanitization:** CSV and Excel cells starting with dangerous characters (`=`, `+`, `-`, `@`, `\t`, `\r`) are automatically escaped with leading single quotes to prevent CSV injection attacks in spreadsheet viewers.
2. **Prompt Injection & Jailbreak Defense:** User questions pass through a pattern-matching and heuristic filter that rejects attempts to manipulate system prompts or bypass analytical tasks.
3. **AST SQL Security Enforcement:** All compiled queries are parsed into Abstract Syntax Trees (ASTs) before execution. Only `SELECT` statements are permitted. `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `EXEC`, and stacked queries are strictly rejected.
4. **Session Isolation & Memory Safety:** Each session receives an isolated, in-memory DuckDB database. Datasets and queries never bleed across sessions, and sessions expire automatically via TTL.
5. **PII Redaction Alerts:** Schemas are scanned for potential Personally Identifiable Information (SSN, credit card patterns, passwords), displaying non-intrusive warnings in the UI.

---

## 📡 API Specification

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/session/init` | Initializes a new isolated user session. |
| `POST` | `/api/session/{session_id}/upload` | Ingests CSV or Excel files, profiles schema, detects relationships, registers DuckDB tables. |
| `GET` | `/api/session/{session_id}/datasets` | Lists all uploaded datasets, column schemas, inferred types, and row counts. |
| `POST` | `/api/analyst/query` | Submits a natural language analytical question (supports conversational follow-ups). |
| `GET` | `/api/session/{session_id}/history` | Retrieves the conversation thread and execution provenance. |
| `DELETE` | `/api/session/{session_id}` | Destroys the session and purges in-memory DuckDB tables. |

---

## 📁 Project Directory Structure

```
Data-Q-A/
├── backend/
│   ├── app/
│   │   ├── analyst/          # Semantic query planner, SQL compiler, verifier, explanation
│   │   ├── api/              # FastAPI route endpoints (session, ingest, analyst)
│   │   ├── catalog/          # Dataset metadata catalog & cross-table relationship detector
│   │   ├── ingestion/        # CSV & multi-sheet Excel parsers, delimiter sniffer, normalizer
│   │   ├── llm/              # Google Gemini LLM client, prompt templates, structured output
│   │   ├── models/           # Pydantic schemas (Session, Dataset, Query, Visualization)
│   │   ├── security/         # Formula sanitizer, SQL AST validator, prompt injection filter
│   │   ├── session/          # Session manager & in-memory DuckDB connection pool
│   │   ├── visualization/    # Chart config generator (Bar, Line, Scatter, Pie)
│   │   ├── config.py         # Application settings & environment configuration
│   │   └── main.py           # FastAPI application entrypoint & middleware
│   ├── tests/                # 94 automated tests (unit, security, integration, evaluation)
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Backend container definition
├── frontend/
│   ├── src/
│   │   ├── components/       # React components (Workspace, ChatThread, Chart, ProvenanceModal)
│   │   ├── api.ts            # Typed Axios API client
│   │   ├── App.tsx           # Main analyst workspace UI
│   │   └── index.css         # Modern design tokens, glassmorphism & dark palette
│   ├── package.json          # Node dependencies
│   └── vite.config.ts        # Vite build configuration
├── sample_data/              # Sample CSV & Excel datasets for immediate testing
│   ├── customers.csv
│   ├── orders.csv
│   ├── products.xlsx
│   └── README.md
├── docs/                     # Architecture & API specifications
│   ├── api-spec.md
│   └── architecture.md
├── WRITEUP.md                # 1-Page Architecture, Key Decisions & Roadmap write-up
├── DECISIONS.md              # Detailed architectural decision records
├── docker-compose.yml        # Multi-container orchestration
└── README.md                 # Project documentation & overview
```

---

## 🗺️ What's Next (Roadmap)

1. **Proactive Anomaly & Insight Discovery:** Automatically compute statistical deviations, correlation matrices, and seasonal anomalies upon upload to suggest high-value questions before the user types anything.
2. **Direct Enterprise Data Connectors:** Extend beyond static CSV/XLSX uploads to include live connectors for PostgreSQL, Snowflake, Google BigQuery, and AWS S3 parquet lakes.
3. **One-Click Executive Slide Deck Generator:** Export presentation-ready PDF / PPTX executive briefs combining AI narrative summaries, rendered charts, and verified SQL audit trails.
4. **Governed Semantic Metric Layer:** Enable data teams to define standard business metrics (e.g., *ARR*, *Net Churn*, *Customer LTV*) in a YAML semantic catalog so all generated SQL adheres to official company definitions.

---

## 📄 Documentation & Links

- 📝 [WRITEUP.md](WRITEUP.md) — 1-Page Submission Write-up
- 🏛️ [docs/architecture.md](docs/architecture.md) — Deep Architecture Specification
- 📡 [docs/api-spec.md](docs/api-spec.md) — REST API Endpoints Specification
- 📋 [DECISIONS.md](DECISIONS.md) — Architectural Decisions Record
- 📊 [sample_data/](sample_data/) — Sample Test Datasets

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
