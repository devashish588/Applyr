# Applyr — AI-Powered Job Search Platform

Applyr is an AI-powered job search automation platform that discovers jobs, matches them to your resume, tailors applications, and sends emails — all from a single dashboard.

## Architecture

```
applyr/
├── frontend/        # React + Vite + TypeScript (port 5173)
├── ui/              # Flask REST API backend (port 5000)
├── agents/          # LangChain/CrewAI AI agents
├── core/            # Models, services, orchestrator
├── db/              # PostgreSQL client + schema
├── email/           # Gmail OAuth + Resend sender
├── pipeline/        # Orchestration pipeline
├── scraper/         # Job scraping modules
└── docker-compose.yml
```

## Quick Start

### 1. Backend

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Start Flask API
python ui/app.py
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** — the frontend proxies `/api/*` to Flask on port 5000.

### 3. Docker (optional)

```bash
docker-compose up --build
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | ✅ | PostgreSQL connection string |
| `GROQ_API_KEY` | ✅ | Groq LLM API key |
| `TAVILY_API_KEY` | ✅ | Tavily search API key |
| `RESEND_API_KEY` | ❌ | Resend email API key |
| `GMAIL_CREDENTIALS` | ❌ | Path to Gmail OAuth credentials |
| `VITE_API_URL` | ❌ | Frontend API URL (default: proxy) |

## Tech Stack

**Frontend**: React, TypeScript, Vite, Tailwind CSS v4, TanStack Query, React Router, Framer Motion, Recharts, Zustand, Lucide Icons

**Backend**: Flask, PostgreSQL, psycopg2, LangChain, CrewAI, LlamaIndex

## License

Private — All rights reserved.