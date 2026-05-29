# AgentForge Career OS — Backend

FastAPI + LangGraph + Qdrant + PostgreSQL backend for the AgentForge Career OS.

## Quick Start

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your API keys

# 2. Start infrastructure
docker compose up -d db qdrant redis

# 3. Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Start development server
uvicorn app.main:app --reload --port 8000

# 7. Open API docs
open http://localhost:8000/docs
```

## Project Structure

```
backend/
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings / environment variables
│   ├── database.py             # Async SQLAlchemy setup
│   ├── dependencies.py         # Shared FastAPI dependencies
│   ├── models/                 # SQLAlchemy ORM models
│   │   └── user.py            # All 12+ models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── api/v1/                 # REST API routes
│   │   ├── auth.py
│   │   ├── profile.py
│   │   ├── opportunities.py
│   │   ├── applications.py
│   │   ├── contacts.py
│   │   ├── agents.py
│   │   ├── memory.py
│   │   ├── analytics.py
│   │   └── monitor.py
│   ├── services/               # Business logic layer
│   ├── agents/                 # LangGraph agent orchestration
│   │   ├── graph.py           # Agent graph + runners
│   │   └── planner.py         # Planner agent + task decomposition
│   ├── memory/                 # Qdrant vector memory layer
│   │   ├── qdrant_client.py   # Qdrant connection + collections
│   │   └── memory_layer.py    # High-level memory interface
│   ├── search/                 # Search adapters (Google, SerpAPI, etc.)
│   └── utils/                  # Embeddings, scoring, helpers
├── alembic/                    # Database migrations
├── Dockerfile
├── requirements.txt
└── .env.example
```

## API Endpoints

Full auto-generated docs at `/docs` when server is running.

### Core Routes

| Prefix | Description |
|--------|-------------|
| `/api/v1/auth` | Register, login, refresh tokens |
| `/api/v1/profile` | User profile + skills CRUD |
| `/api/v1/opportunities` | Opportunities + match scores |
| `/api/v1/applications` | Application pipeline |
| `/api/v1/contacts` | Networking contacts |
| `/api/v1/agents` | Planner + agent task management |
| `/api/v1/memory` | Long-term memory entries |
| `/api/v1/analytics` | Dashboard metrics, funnel, skills demand |
| `/api/v1/monitor` | Alert configs + monitor settings |

## Agent System

The planner agent orchestrates 8 specialist agents:

1. **Planner Agent** — Decomposes goals into sub-tasks
2. **Internship Agent** — Searches for internships
3. **Job Agent** — Searches for full-time roles
4. **Research Agent** — Company/industry research
5. **Resume Agent** — Resume tailoring + ATS optimization
6. **Interview Agent** — Mock question generation
7. **Networking Agent** — Outreach message drafting
8. **Opportunity Monitor** — Continuous scan + alerts

## Docker Compose (Full Stack)

```bash
docker compose up --build
```

Starts:
- **FastAPI** (port 8000)
- **PostgreSQL** (port 5432)
- **Qdrant** (port 6333)
- **Redis** (port 6379)
