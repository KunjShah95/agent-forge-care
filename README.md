# AgentForge — Career OS

AgentForge is an AI-powered career operating system that automates job search, interview preparation, resume optimization, and networking. It orchestrates **8 specialized agents** coordinated by a central planner to provide personalized career coaching at scale.

## Quick Start

```bash
# Frontend
npm install
npm run dev               # → http://localhost:8080

# Backend
cd backend
python -m venv .venv && .venv\Scripts\activate && pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --app-dir backend  # → http://localhost:8000
```

Or use Docker: `docker compose up` (Postgres, Redis, Qdrant, backend).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | React 18 + Vite + TypeScript + Tailwind CSS |
| **UI** | shadcn/ui (Radix primitives), Framer Motion, Recharts |
| **State** | TanStack React Query, React Router DOM |
| **Backend** | Python FastAPI + SQLAlchemy 2.0 (async) + Alembic |
| **Database** | PostgreSQL 16 |
| **Vector DB** | Qdrant (semantic memory / RAG) |
| **Cache / Queue** | Redis + RQ worker |
| **AI Agents** | LangGraph + LangChain |
| **LLM Providers** | OpenAI, Anthropic, Google Gemini, Groq, DeepSeek, Mistral, Ollama (fallback chain) |
| **Search** | Tavily, Google CSE, Brave, SerpAPI, Exa, SearXNG (adapter chain) |
| **Auth** | Firebase (email/password + Google SSO) with JWT |
| **Container** | Docker Compose (4 services) |
| **Deployment** | Vercel (frontend), Render / Railway (backend) |

## Architecture

```
Browser → Vite/React → REST/WS → FastAPI → Agents (LangGraph)
                                          → PostgreSQL (canonical data)
                                          → Qdrant (vector memory)
                                          → Redis (cache, queues)
                                          → LLM providers (fallback chain)
```

8 agents orchestrated via LangGraph:
1. **Planner** — career strategy and goal breakdown
2. **Job Agent** — full-time job discovery and matching
3. **Internship Agent** — internship, hackathon, fellowship scanning
4. **Research Agent** — company intelligence and market analysis
5. **Resume Agent** — ATS analysis and tailored rewrites
6. **Interview Agent** — mock interviews with scoring and feedback
7. **Networking Agent** — contact discovery and outreach generation
8. **Opportunity Monitor** — 24/7 background scanning and alerts

A **memory layer** (Qdrant + PostgreSQL) stores user preferences, application history, interview feedback, and career goals so recommendations improve over time.

## Project Structure

```
agent-forge-care/
├── src/                 # React frontend (Vite)
│   ├── pages/           # 16 routed pages (Dashboard, Onboarding, ResumeStudio, etc.)
│   ├── components/      # shadcn/ui + custom components
│   └── lib/             # API client, auth, utilities
├── backend/
│   ├── app/
│   │   ├── main.py      # FastAPI entry point
│   │   ├── api/v1/      # 35 REST routes (14 modules)
│   │   ├── agents/      # LangGraph agent implementations
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── schemas/     # Pydantic request/response schemas
│   │   ├── services/    # Business logic (auth, memory, matching, etc.)
│   │   ├── memory/      # Qdrant vector store client
│   │   ├── search/      # Multi-provider search adapters
│   │   ├── tasks/       # Background workers (RQ)
│   │   └── middleware/  # Auth middleware
│   ├── tests/           # 119 test functions (22 files, all passing)
│   └── alembic/         # 5 database migrations
├── docker-compose.yml   # Local dev services
├── Dockerfile.frontend  # Frontend container
└── backend/Dockerfile   # Backend container
```

## Scripts

| Command | Purpose |
|---------|---------|
| `npm run dev` | Frontend dev server (port 8080) |
| `npm run build` | Production build → `dist/` |
| `npm run test` | Vitest (frontend) |
| `npm run lint` | ESLint |
| `cd backend && pytest -q` | Backend tests (167 passing) |
| `cd backend && alembic upgrade head` | Run migrations |
| `python -m backend.app.worker` | Start background worker |

## Key Features

- **ATS Resume Analysis** — keyword gap detection, tailored rewriting
- **Mock Interviews** — AI-powered with real-time scoring (STAR, technical, system design)
- **Opportunity Discovery** — scans 50+ sources with 78% match accuracy
- **Networking Automation** — contact discovery + personalized outreach
- **Pipeline Tracking** — Kanban-style application management
- **Career Analytics** — conversion tracking, skill demand insights
- **Persistent Memory** — learns from every interaction across sessions

## Environment

Key variables (see `.env.example`):

- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `QDRANT_URL` / `QDRANT_API_KEY` — Vector DB
- `OPENAI_API_KEY` — Primary LLM provider
- `FIREBASE_CREDENTIALS_JSON` — Auth credentials
- `TAVILY_API_KEY` — Primary search provider

## Deployment

- **Frontend:** `vercel.json` → Vercel (SPA rewrite)
- **Backend:** `render.yaml` / `railway.json` → Render / Railway
- **Container:** `docker compose -f docker-compose.prod.yml up`

## Testing

```bash
cd backend && pytest -q        # 167 backend tests
npm run test                   # Frontend tests
```

## Docs

- `docs/product-vision.md` — Full concept walkthrough
- `docs/status.md` — Current state and known gaps
- `docs/architecture.svg` — System architecture diagram
- `frontend.md` — Frontend development guide
- `backend.md` — Backend development guide

## License

MIT
