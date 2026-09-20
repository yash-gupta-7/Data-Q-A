# 🔍 Data Q&A — AI-Powered Data Analyst

> Ask natural language questions about your CSV/Excel data and get instant answers, visualizations, and insights powered by Google Gemini.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6.svg)](https://typescriptlang.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://docker.com)

---

## ✨ Features

- 📊 **Upload CSV/Excel** files and auto-detect schema
- 💬 **Natural language Q&A** — ask anything about your data
- 📈 **Auto-generated charts** — bar, line, scatter, pie
- 🧠 **Powered by Google Gemini** for intelligent query understanding
- 🔒 **Session-based** — each user gets an isolated data session
- ⚡ **Real-time streaming** responses

---

## 🏗️ Architecture

```
┌──────────────┐     HTTP/REST     ┌─────────────────────────┐
│   React UI   │ ◄──────────────► │   FastAPI Backend        │
│  (Vite/TS)   │                  │                          │
└──────────────┘                  │  ┌──────────────────┐    │
                                  │  │  Ingestion Layer  │    │
                                  │  │  (CSV → pandas)   │    │
                                  │  └────────┬─────────┘    │
                                  │           │               │
                                  │  ┌────────▼─────────┐    │
                                  │  │   LLM Analyst     │    │
                                  │  │ (Gemini + prompt) │    │
                                  │  └────────┬─────────┘    │
                                  │           │               │
                                  │  ┌────────▼─────────┐    │
                                  │  │  Visualization    │    │
                                  │  │ (Plotly/Recharts) │    │
                                  │  └──────────────────┘    │
                                  └─────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Gemini API key

### 1. Clone & Setup

```bash
git clone https://github.com/yash-gupta-7/Data-Q-A.git
cd Data-Q-A
```

### 2. Backend

```bash
cd backend
cp .env.example .env          # fill in GEMINI_API_KEY
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
cp .env.example .env          # set VITE_API_URL=http://localhost:8000
npm install
npm run dev
```

### 4. Docker (recommended)

```bash
cp .env.example .env
docker-compose up --build
```

Open [http://localhost:5173](http://localhost:5173)

---

## 📁 Project Structure

```
Data-Q-A/
├── backend/
│   ├── app/
│   │   ├── analyst/        # Core query analysis engine
│   │   ├── api/            # FastAPI route handlers
│   │   ├── catalog/        # Dataset metadata catalog
│   │   ├── ingestion/      # File upload & parsing
│   │   ├── llm/            # Gemini LLM integration
│   │   ├── models/         # Pydantic schemas
│   │   ├── security/       # Input validation & rate limiting
│   │   ├── session/        # User session management
│   │   ├── visualization/  # Chart generation
│   │   ├── config.py       # App configuration
│   │   └── main.py         # FastAPI app entrypoint
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/     # React UI components
│   │   ├── api.ts          # API client (axios)
│   │   ├── App.tsx         # Root component
│   │   └── index.css       # Global styles
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── CONTRIBUTING.md
└── README.md
```

---

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | ✅ |
| `SECRET_KEY` | JWT signing secret | ✅ |
| `ALLOWED_ORIGINS` | CORS allowed origins | ✅ |
| `MAX_FILE_SIZE_MB` | Upload limit (default: 50) | ❌ |
| `SESSION_TTL_MINUTES` | Session expiry (default: 60) | ❌ |

---

## 🧪 Testing

```bash
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
