# Changelog

All notable changes to **Data Q&A** are documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] — 2026-09-20

### 🎉 Initial Release

This is the first production-ready release of **Data Q&A**, an AI-powered tabular data analyst.

### Added

#### Backend
- **Data Ingestion** — CSV and Excel upload pipeline with:
  - Multi-encoding detection (UTF-8, UTF-8 BOM, Latin-1, CP1252)
  - Formula injection sanitization
  - Row/column shape limits (1M rows, 500 columns)
  - Heuristic delimiter detection (comma, semicolon, tab, pipe)
- **LLM Integration** — Google Gemini-powered query engine:
  - Versioned prompt templates (v1.2.0)
  - Structured JSON response schema (answer + code + chart config)
  - Automatic retry with exponential backoff (rate limits)
  - Full exception hierarchy: LLMRateLimitError, LLMTransientError
- **Security Layer**:
  - Prompt injection detection (12 regex patterns)
  - LLM-generated code validation (blocks os, subprocess, eval, exec, etc.)
  - Filename sanitization with path traversal prevention
  - PII detection module
- **Session Management** — In-memory DataFrame sessions with TTL expiry
- **Data Catalog** — Schema registry with column metadata
- **Visualization** — Chart config generation for Recharts (bar, line, scatter, pie, histogram)
- **FastAPI Application** — Async REST API with:
  - CORS middleware
  - Global exception handlers
  - Health check endpoint

#### Frontend
- **React 18 + TypeScript** application (Vite)
- **Chat Interface** — Conversational Q&A with message history
- **File Upload** — Drag-and-drop CSV/Excel upload with preview
- **Data Visualization** — Interactive charts via Recharts
- **Shared Component Library** — Skeleton, LoadingSpinner, EmptyState, Badge, Tooltip
- **Custom Hooks** — useLocalStorage, useDebounce, useCopyToClipboard

#### DevOps
- **Docker Compose** — Single-command local development
- **GitHub Actions CI**:
  - Backend: ruff + mypy lint, pytest unit tests, 70% coverage gate, Codecov
  - Frontend: oxlint, TypeScript check, Vite production build

#### Documentation
- Full README with architecture diagram, quick-start, env var reference
- System architecture doc (docs/architecture.md) with ASCII diagrams and data flows
- API specification (docs/api-spec.md)
- CONTRIBUTING.md with branch naming, commit conventions, PR checklist
- `.env.example` files for both backend and frontend

### Fixed
- N/A (initial release)

### Security
- Formula injection attack surface eliminated in CSV parsing
- LLM prompt injection patterns blocked with regex guards
- Generated code execution sandbox with restricted builtins
- Path traversal prevention in file upload handler

---

## [Unreleased]

### Planned for v1.5.0
- Redis session store for horizontal scaling
- Excel formula support via openpyxl
- Query result caching (same question → cached response)
- User authentication (optional JWT)
- Export results to CSV/PNG

### Planned for v2.0.0
- DuckDB persistent query history
- Multi-file join queries
- Scheduled report generation
- Public sharing of dashboards
