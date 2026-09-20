# 🔍 Data Q&A — AI-Powered Data Analyst

> **Ask natural language questions across multiple CSV and Excel datasets. Get verified numerical answers, rich interactive visualizations, and full analytical provenance powered by DuckDB and Google Gemini.**

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB.svg?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![DuckDB](https://img.shields.io/badge/DuckDB-In--Memory_OLAP-FFF000.svg?logo=duckdb&logoColor=black)](https://duckdb.org)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg?logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Google Gemini](https://img.shields.io/badge/LLM-Gemini_Flash-8E75B2.svg?logo=google&logoColor=white)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-94_Passing-brightgreen.svg)]()

---

## 📋 Deliverables Summary

| Deliverable | Location / Access |
|---|---|
| 🖥️ **Working Prototype** | Local Run: `http://localhost:5173` (See [Quick Start](#-quick-start)) |
| 📦 **Source Code Repository** | Full source code with setup and architecture docs (See [Project Structure](#-project-structure)) |
| 📝 **1-Page Write-Up** | [WRITEUP.md](WRITEUP.md) (Approach, Key Decisions, Future Roadmap) |
| 📊 **Sample Datasets** | [sample_data/](sample_data/) (`customers.csv`, `orders.csv`, `products.xlsx`) |

---

## ✨ Core Features & Highlights

- 📁 **Multi-File & Multi-Sheet Ingestion**: Upload multiple CSVs and Excel (.xlsx) workbooks in a single workspace. Automatically skips non-tabular notes sheets.
- 🔗 **Cross-Dataset Relational Joins**: Intelligently identifies primary/foreign key relationships across distinct files (e.g., joining orders with customers and product catalogs).
- 🛡️ **Zero-Hallucination Numerical Engine**: Queries are compiled into deterministic **DuckDB SQL** and executed against real data. The LLM interprets the intent and narrates findings, but never invents calculations.
- 📈 **Dynamic Visualizations**: Auto-selects and renders responsive Bar, Line, Scatter, and Pie charts using Recharts.
- 💬 **Conversational Context**: Preserves multi-turn conversation memory for natural follow-up questions and iterative slicing/dicing.
- 🔒 **Enterprise-Grade Security**: Automatic CSV formula injection neutralization (`=`, `@`, `+`, `-`), prompt injection defense, SQL AST read-only enforcement, and PII detection.
- 🕵️ **Provenance & Auditability**: Every answer includes full evidence inspection—showing executed SQL, execution duration, and contributing datasets.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                          React 18 + TypeScript UI                      │
│   (Dataset Explorer · Conversational Thread · Recharts · Provenance)   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST / SSE API
┌───────────────────────────────────▼────────────────────────────────────┐
│                           FastAPI Backend                              │
│                                                                        │
│  ┌────────────────────────┐            ┌────────────────────────────┐  │
│  │    Ingestion Layer     │            │      Security Guards       │  │
│  │  • CSV Delimiter / BOM │            │  • Formula Sanitization    │  │
│  │  • Multi-Sheet Excel   ├───────────►│  • Prompt Injection Filter │  │
│  │  • Type Inference      │            │  • SQL AST Read-Only Check │  │
│  └───────────┬────────────┘            └─────────────┬──────────────┘  │
│              │                                       │                 │
│  ┌───────────▼────────────┐            ┌─────────────▼──────────────┐  │
│  │   Dataset Catalog      │            │     LLM Query Planner      │  │
│  │  • Schema Profiling    │            │  • Intent Extraction       │  │
│  │  • Relationship Detect │            │  • Gemini Flash API        │  │
│  └───────────┬────────────┘            └─────────────┬──────────────┘  │
│              │                                       │                 │
│  ┌───────────▼───────────────────────────────────────▼──────────────┐  │
│  │              Deterministic SQL Compiler & Runner                 │  │
│  │              (Session-Isolated In-Memory DuckDB)                 │  │
│  └───────────────────────────────────┬──────────────────────────────┘  │
│                                      │                                 │
│                        ┌─────────────▼──────────────┐                  │
│                        │ Result Verifier & Narrator │                  │
│                        └────────────────────────────┘                  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3.11+, FastAPI, DuckDB, Pandas, OpenPyXL, Pydantic v2, Pytest
- **AI / LLM**: Google Gemini API (`gemini-2.5-flash` / `gemini-1.5-flash`)
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS / Custom Modern CSS, Recharts, Lucide Icons
- **DevOps & Packaging**: Docker, Docker Compose

---

## 🚀 Quick Start

### Option A: Local Run (Recommended for Dev)

#### 1. Clone the repository
```bash
git clone https://github.com/yash-gupta-7/Data-Q-A.git
cd Data-Q-A
```

#### 2. Backend Setup
```bash
cd backend
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run backend API (port 8000)
uvicorn app.main:app --reload --port 8000
```

#### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser!

---

### Option B: Docker Compose

```bash
# In the project root
cp backend/.env.example backend/.env
# Edit backend/.env and supply your GEMINI_API_KEY

docker-compose up --build
```
Access the application at [http://localhost:5173](http://localhost:5173).

---

## 🧪 Running Tests

The test suite covers unit tests, security sanitization, multi-file ingestion pipelines, and golden analytical evaluation questions.

```bash
cd backend
PYTHONPATH=. .venv/bin/pytest -v
```

All 94 tests validate:
- ✅ CSV/XLSX multi-sheet parsing & normalization
- ✅ Formula injection & malicious input sanitization
- ✅ AST SQL security verification (blocking mutations/injections)
- ✅ Cross-table DuckDB SQL compilation
- ✅ Multi-turn conversation intent merging

---

## 📊 Demo Walkthrough with Sample Data

Ready-to-use sample datasets are provided in [`sample_data/`](sample_data/):
1. **`customers.csv`**: Customer demographic and signup data.
2. **`orders.csv`**: Transactional sales data with quantities, unit prices, and status.
3. **`products.xlsx`**: Multi-sheet product catalog and pricing tiers.

### Try Asking:
1. **Multi-Table Aggregation**: *"What is the total revenue by product category?"*
2. **Cross-File Ranking**: *"Who are the top 5 customers by spend and which industry are they in?"*
3. **Time Series Trend**: *"Show monthly sales trends over time."*
4. **Follow-Up Drilldown**: *"Filter that down to only the Software category and show as a bar chart."*

---

## 📄 Documentation

- 📝 [WRITEUP.md](WRITEUP.md) — 1-Page Approach, Decisions & Future Roadmap
- 🏛️ [docs/architecture.md](docs/architecture.md) — Detailed Architecture Specification
- 📡 [docs/api-spec.md](docs/api-spec.md) — REST API Endpoints Specification
- 📋 [DECISIONS.md](DECISIONS.md) — Architectural Decision Log

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
