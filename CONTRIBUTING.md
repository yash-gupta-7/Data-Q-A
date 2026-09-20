# Contributing to Data Q&A

Thank you for your interest in contributing! Please read these guidelines before submitting pull requests.

## Project Structure

```
Data-Q-A/
├── backend/          # FastAPI backend (Python)
│   ├── app/
│   │   ├── analyst/      # Query analysis engine
│   │   ├── api/          # REST API routes
│   │   ├── catalog/      # Data catalog management
│   │   ├── ingestion/    # CSV/file ingestion pipeline
│   │   ├── llm/          # LLM integration (Gemini)
│   │   ├── models/       # Pydantic data models
│   │   ├── security/     # Auth & validation
│   │   ├── session/      # Session management
│   │   └── visualization/# Chart generation
│   └── tests/
├── frontend/         # React + TypeScript (Vite)
│   └── src/
│       ├── components/   # UI components
│       ├── api.ts        # API client
│       └── App.tsx       # Root component
└── docker-compose.yml
```

## SDLC Workflow

We follow a standard SDLC process:

1. **Planning** — Feature scoping and issue creation
2. **Design** — Architecture & API design reviewed in PRs
3. **Development** — Feature branches off `main`
4. **Testing** — Unit + integration tests required
5. **Review** — Code review mandatory before merge
6. **Release** — Versioned releases with CHANGELOG updates

## Branch Naming

- `feat/<feature-name>` — New features
- `fix/<bug-name>` — Bug fixes
- `chore/<task>` — Maintenance tasks
- `docs/<topic>` — Documentation only

## Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(scope): short description

[optional body]
[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`

## Running Locally

```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend && npm install && npm run dev
```

## Pull Request Checklist

- [ ] Tests added/updated for new functionality
- [ ] No sensitive data (API keys, tokens) committed
- [ ] README or docs updated if needed
- [ ] Conventional commit messages used
