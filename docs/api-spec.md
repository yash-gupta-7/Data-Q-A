# API Design Specification

## REST API Conventions

- Base URL: `/api/v1`
- Content-Type: `application/json` (except file uploads)
- Authentication: Session-based (session_id in request body)
- Error format: `{ "error": "message", "detail": "...", "code": 4xx }`

## Endpoints Summary

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload CSV/Excel file |
| POST | `/api/query` | Ask question about dataset |
| GET | `/api/sessions/{id}` | Get session info |
| DELETE | `/api/sessions/{id}` | Terminate session |
| GET | `/api/health` | Health check |

## Error Codes

| Code | Meaning |
|------|---------|
| 400 | Bad request / validation error |
| 404 | Session not found or expired |
| 413 | File too large |
| 422 | Unprocessable entity |
| 429 | Rate limit exceeded |
| 500 | Internal server error (LLM/execution failure) |

## Versioning

API is versioned via URL prefix `/api/v1`. Breaking changes bump the version.
