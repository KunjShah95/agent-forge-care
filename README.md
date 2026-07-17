# CareerOS — Your AI Career Operating System

CareerOS is an AI-powered career operating system that automates job search, interview preparation, resume optimization, and networking. It orchestrates **8 specialized agents** coordinated by a central planner to provide personalized career coaching at scale.

## Quick Start

```bash
# Frontend
npm install
npm run dev               # → http://localhost:8080

# Backend
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload  # → http://localhost:8000
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
| **Deployment** | Vercel (frontend), Render (backend) |

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
├── src/                 # React frontend (Vite)
│   ├── pages/           # 14+ routed pages
│   ├── components/      # shadcn/ui + custom components
│   └── lib/             # API client, auth, utilities
├── backend/
│   ├── app/
│   │   ├── main.py      # FastAPI entry point
│   │   ├── api/v1/      # REST routes (15+ modules)
│   │   ├── agents/      # LangGraph agent implementations
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── services/    # Business logic
│   │   ├── memory/      # Qdrant vector store client
│   │   ├── search/      # Multi-provider search adapters
│   │   └── tasks/       # Background workers
│   ├── tests/           # 300+ test functions
│   └── alembic/         # Database migrations
├── docker-compose.yml   # Local dev services
├── Dockerfile.frontend  # Frontend container
└── backend/Dockerfile   # Backend container
```

## Key Features

- **ATS Resume Analysis** — keyword gap detection, tailored rewriting
- **Mock Interviews** — AI-powered with real-time scoring (STAR, technical, system design)
- **Opportunity Discovery** — scans 50+ sources with 78% match accuracy
- **Networking Automation** — contact discovery + personalized outreach
- **Pipeline Tracking** — Kanban-style application management
- **Career Analytics** — conversion tracking, skill demand insights
- **Persistent Memory** — learns from every interaction across sessions

## Deployment

- **Frontend:** Deploy `dist/` to **Vercel** (SPA rewrite via `vercel.json`)
- **Backend:** Deploy to **Render** using `render.yaml` (Python)
- **Container:** `docker compose -f docker-compose.prod.yml up`

## License

MIT
