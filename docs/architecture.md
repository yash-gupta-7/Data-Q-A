# System Architecture — Data Q&A

## Overview

Data Q&A is a full-stack application that enables users to upload tabular datasets (CSV/Excel) and query them using natural language. The system leverages Google Gemini as its LLM backbone to understand user intent, generate analytical code, and produce visualizations.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Client Layer                        │
│         React 18 + TypeScript + Vite (Port 5173)         │
└───────────────────────┬─────────────────────────────────┘
                        │ HTTP/REST + JSON
┌───────────────────────▼─────────────────────────────────┐
│                    API Gateway                            │
│              FastAPI (Uvicorn, Port 8000)                 │
│  ┌──────────────────────────────────────────────────┐    │
│  │                   Middleware                      │    │
│  │   CORS │ Rate Limiting │ Request Validation       │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐   │
│  │  /upload    │  │  /query      │  │  /sessions    │   │
│  │  Ingestion  │  │  Analysis    │  │  Management   │   │
│  └──────┬──────┘  └──────┬───────┘  └───────────────┘   │
└─────────┼────────────────┼─────────────────────────────┘
          │                │
┌─────────▼────────────────▼─────────────────────────────┐
│                   Service Layer                          │
│                                                          │
│  ┌──────────────┐   ┌─────────────┐   ┌─────────────┐  │
│  │  Ingestion   │   │  LLM Analyst│   │  Catalog    │  │
│  │  Service     │   │  Service    │   │  Service    │  │
│  │              │   │             │   │             │  │
│  │ • CSV parse  │   │ • Prompt    │   │ • Schema    │  │
│  │ • Schema     │   │   template  │   │   registry  │  │
│  │   detection  │   │ • Gemini    │   │ • Metadata  │  │
│  │ • Validation │   │   API call  │   │   store     │  │
│  └──────┬───────┘   └──────┬──────┘   └─────────────┘  │
│         │                  │                             │
│  ┌──────▼───────┐   ┌──────▼──────┐                     │
│  │  Session     │   │  Viz Service│                     │
│  │  Manager     │   │             │                     │
│  │              │   │ • Plotly    │                     │
│  │ • In-memory  │   │ • Chart     │                     │
│  │   DataFrames │   │   config    │                     │
│  │ • TTL expiry │   │   builder   │                     │
│  └──────────────┘   └─────────────┘                     │
└─────────────────────────────────────────────────────────┘
```

---

## Data Flow

### Upload Flow
```
User selects CSV
    → Frontend validates file type/size
    → POST /api/upload (multipart/form-data)
    → Ingestion Service: pandas.read_csv()
    → Schema detection (dtypes, nulls, ranges)
    → DataFrame stored in SessionManager
    → Catalog updated with metadata
    → Return: { session_id, schema, row_count, columns }
```

### Query Flow
```
User types question
    → Frontend sends: { question, session_id }
    → POST /api/query
    → Security: validate session, sanitize input
    → Catalog: fetch dataset schema for context
    → LLM Analyst: build system prompt with schema
    → Gemini API: generate pandas code + insights
    → Execute generated code against DataFrame
    → Visualization: build chart config if applicable
    → Return: { answer, chart_config, sql_equivalent }
```

---

## API Specification

### POST /api/upload
```json
Request: multipart/form-data { file: File }
Response: {
  "session_id": "uuid",
  "filename": "sales_data.csv",
  "row_count": 1500,
  "columns": ["date", "revenue", "category"],
  "schema": {
    "date": { "type": "datetime", "nulls": 0 },
    "revenue": { "type": "float64", "min": 10.5, "max": 99999 },
    "category": { "type": "string", "unique": 8 }
  }
}
```

### POST /api/query
```json
Request: {
  "question": "What is the total revenue by category?",
  "session_id": "uuid"
}
Response: {
  "answer": "Electronics leads with $2.4M (34%), followed by...",
  "chart": {
    "type": "bar",
    "x": ["Electronics", "Clothing", ...],
    "y": [2400000, 1200000, ...]
  },
  "code": "df.groupby('category')['revenue'].sum()"
}
```

### GET /api/sessions/{session_id}
```json
Response: {
  "session_id": "uuid",
  "created_at": "2026-09-20T10:00:00Z",
  "expires_at": "2026-09-20T11:00:00Z",
  "dataset": { ... }
}
```

---

## Security Considerations

- **Input Validation**: All user inputs sanitized before LLM context injection
- **Code Execution Safety**: Generated pandas code runs in a restricted exec() sandbox
- **Session Isolation**: Each session has independent DataFrame storage
- **Rate Limiting**: 10 queries/minute per session
- **File Validation**: Magic bytes check, size limit (50MB), allowed types only

---

## Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Backend Framework | FastAPI | Async, auto OpenAPI docs, pydantic native |
| LLM | Google Gemini | Best CSV/tabular data reasoning, affordable |
| Data Processing | pandas | Industry standard, rich API |
| Frontend | React + Vite | Fast HMR, TypeScript-first |
| Charting | Recharts | Declarative, React-native, lightweight |
| Session Storage | In-memory | MVP simplicity; Redis planned for v2 |

---

## Scalability Roadmap

- **v1.0** — Single-instance, in-memory sessions (current)
- **v1.5** — Redis session store for horizontal scaling
- **v2.0** — DuckDB for persistent query history + caching
- **v3.0** — Multi-tenant with database-backed auth
