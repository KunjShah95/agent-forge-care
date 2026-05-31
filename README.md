# AgentForge — Career OS

AgentForge (agent-forge-care) is an integrated career coaching and job search assistant combining a React frontend with a Python backend of modular agents to help users with resumes, interview prep, research, opportunity monitoring, and personalized memory-driven coaching.

## Table of contents

- Overview
- Why we're building this
- Problems we solve
- High-level solution
- Architecture diagram
- Component responsibilities
- Data flow
- Important design decisions & tradeoffs
- Security & privacy
- Local development (quick start)
- Environment variables
- Testing
- Deployment & operations
- Roadmap
- Contributing
- License & contact

## Overview

AgentForge provides:

- Personalized career guidance and ATS-aware resume optimizations
- Mock technical & behavioral interviews with feedback
- Opportunity discovery, tracking, and monitoring
- Persistent memory (user context, past applications, interview feedback)
- Agent-based workflows (research agent, planner, job/internship agents)

The repository contains a Vite + React frontend (`src/`) and a Python backend (`backend/`) with modular agents, API routes, database models, and tests.

## Why we're building this

- Job search and career development are fragmented across tools and documents.
- Coaching is expensive and inconsistent; automation + human-in-the-loop can scale high-quality support.
- Developers and students need contextual, continuous practice and feedback tied to real application history.

## Problems we solve

- Fragmented context across job applications and interviews — persistent memory keeps continuity.
- Generic, low-quality advice — agents produce role-specific, evidence-driven guidance.
- Time-consuming tailoring of resumes and cover letters — automated, ATS-aware rewrites.
- Lack of practice and measurable feedback for interviews — integrated mock interviews with scoring and improvement suggestions.
- Monitoring opportunities at scale — background monitors surface new matches and changes.

## High-level solution

- Frontend: React + Vite UI providing chat, dashboards, consoles.
- Backend: Python (FastAPI-style) exposing REST and WebSocket endpoints and orchestrating agents.
- Postgres (SQLAlchemy/Alembic) for canonical data; Redis for cache/queues; Vector DB for semantic memory.
- External LLM/embedding providers for natural language capabilities (pluggable).

## Architecture diagram

Rendered architecture diagram (SVG):

![Architecture diagram](docs/architecture.svg)

Mermaid source (if you prefer to render locally):

```mermaid
flowchart LR
  Browser[Browser / React (Vite)] -->|HTTPS| CDN[Nginx / CDN]
  CDN --> Frontend[Frontend App (Vite/React)]
  Frontend -->|REST / WebSocket| API[Backend API (FastAPI/Uvicorn)]
  subgraph Backend
    API --> Agents[(Agent Manager)]
    Agents --> ResearchAgent[Research Agent]
    Agents --> PlannerAgent[Planner Agent]
    Agents --> InterviewAgent[Interview Agent]
    Agents --> MemoryService[(Memory & Vector Store)]
    API --> Auth[Auth Layer (Firebase / JWT)]
    API --> WorkerQueue[Worker / Background Tasks (RQ/Celery)]
  end

  API -->|SQL| Postgres[(Postgres / SQLAlchemy)]
  API -->|Cache| Redis[(Redis)]
  MemoryService -->|Vectors| VectorDB[(Vector DB / Faiss or Pinecone)]
  WorkerQueue -->|pub/sub| Redis
  WorkerQueue --> ExternalAI[External LLMs / Embeddings]
  ExternalAI -->|responses| Agents
  Storage[(File Storage / S3)] --- API
  Monitoring[Monitoring / Logging] --- Backend
  CI/CD -->|deploy| Infra[Docker / Docker-Compose / Cloud]
```

## Component responsibilities

- Frontend (`src/`): UI pages (Dashboard, Applications, Interview Prep, Memory Viewer), chat components, theme & auth integration.
- Backend (`backend/app/`): API endpoints, agent orchestration, memory management, models, migrations, and tests.
- Agents (`backend/app/agents/`): discrete, testable units implementing domain logic (resume rewrite, research, interview simulation).
- Persistence: Postgres for canonical data, Vector DB for semantic memory, Redis for cache and queues.
- Integrations: LLM providers, optional job-board connectors, cloud object storage for uploads.

## Data flow (typical)

1. User interacts via browser → frontend calls backend API.
2. API authenticates and serves cached/DB data or dispatches an Agent for processing.
3. Agents may call embeddings/LLMs and write to the Vector DB and Postgres.
4. Responses are stored and returned to the frontend; background monitors update opportunities and notify users.

## Important design decisions & tradeoffs

- Modular agents improve testability and isolation but add orchestration complexity.
- External LLMs accelerate feature development but require strong privacy controls and cost management.
- Vector DB enables semantic search (RAG) but adds another datastore to operate and back up.

## Security & privacy considerations

- Scrub or avoid sending raw PII to external LLMs unless explicitly permitted by the user.
- Provide user-facing data export and deletion flows.
- Use HTTPS, short-lived tokens, secrets management, and rotate API keys.
- Validate scanned uploads (resumes, avatars) and limit file types/sizes.

## Local development (quick start)

Prerequisites:

- Node >= 18, npm or pnpm
- Python 3.10+
- Postgres (local) and Redis (optional)
- Docker (recommended for parity)

1) Frontend

```bash
# from repo root
npm install
npm run dev
# open http://localhost:5173
```

1) Backend (dev)

```bash
# from repo root
cd backend
python -m venv .venv
.venv\Scripts\activate    # Windows
# or: source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
# Configure DATABASE_URL (see .env.example)
alembic upgrade head
# Start dev server (note --app-dir to resolve imports on Windows)
python -m uvicorn app.main:app --reload --app-dir backend
```

1) Background worker (optional)

```bash
# Start Redis
# Start the worker (adapt to your worker entrypoint)
python -m backend.app.worker
```

If you prefer Docker, review `docker-compose.yml` and `docker-compose.prod.yml` for service definitions and environment variables.

## Environment variables

Create a `.env` or set environment variables. Example placeholders are in `.env.example`.

Key variables (examples):

- DATABASE_URL=postgres://user:pass@localhost:5432/agentforge
- REDIS_URL=redis://localhost:6379/0
- SECRET_KEY=super-secret-key
- FIREBASE_CREDENTIALS_JSON=/path/to/firebase.json
- OPENAI_API_KEY=<key> or AZURE_* variables
- VECTOR_DB_CONFIG (Pinecone/Chroma/host config)
- S3 / CLOUD_STORAGE credentials for production uploads

## Testing

- Backend: run pytest from `backend/`:

```bash
cd backend
pytest -q
```

- Frontend: run vitest / npm test:

```bash
npm run test
```

Add integration tests for agent behaviors and the RAG/memory pipeline.

## Deployment & operations

- Build and containerize with the provided Dockerfiles (`Dockerfile.frontend`, `backend/Dockerfile`).
- Use CI to run tests, build images, and push to a registry; deploy to Kubernetes or managed app services.
- Recommended production components: managed Postgres, managed Redis, managed Vector DB (Pinecone/Weaviate) or durable Faiss/Chroma, secrets manager, observability (Prometheus/Grafana, Sentry).

## Roadmap (suggested)

- Harden privacy controls and add user data export/delete.
- Provider-agnostic vector store abstraction.
- Job-board connectors & OAuth pipelines.
- Browser extension to capture job posts in one click.
- Admin dashboards and audit tooling.
- Human-in-the-loop moderation for generated content.

## Contributing

- Follow existing project style (TypeScript/React lint rules and Python formatting).
- Add unit tests for agent logic and integration tests for memory/search flows.
- Open PRs against `main` with a short changelog and test plan. For large changes, open an issue first.

## License & contact

- Add your license (e.g., MIT) and maintainer contact details here.

---

If you'd like, I can also:

- add a rendered Mermaid SVG to `docs/` (requires a Mermaid renderer), or
- create a concise one-page architecture PDF for stakeholders.

## AgentForge Career OS

AgentForge is an AI-powered career operating system that helps people discover internships, jobs, research programs, hackathons, scholarships, and networking opportunities — then turns those results into a guided action plan.

## What it does

- Finds and ranks opportunities based on a user’s profile, goals, and preferences
- Uses specialized agents for internships, jobs, research, resume tailoring, interview prep, networking, and monitoring
- Maintains memory for skills, target locations, applications, interview notes, and career goals
- Runs a daily discovery loop so the system keeps working even when the user is not searching manually

## Product vision

The product is designed as a planner-first multi-agent system:

1. The user states a goal.
2. A planner breaks the goal into subtasks.
3. Domain agents search, score, prepare, and track outcomes.
4. A memory layer stores preferences and outcomes so future recommendations improve.

## Frontend structure

- `src/pages/Landing.tsx` — product story, architecture, agent fleet, workflow, and roadmap
- `src/pages/Dashboard.tsx` — daily planner view, matches, application pipeline, and activity feed
- `src/pages/Onboarding.tsx` — captures profile, skills, preferences, and goals

## Suggested core agents

- Planner Agent
- Internship Agent
- Job Agent
- Research Agent
- Resume Agent
- Interview Agent
- Networking Agent
- Opportunity Monitor

## Next steps

- Connect the frontend to a backend search/memory service
- Add persisted user profiles and application tracking
- Add source adapters for internship/job sites and company career pages
- Add notifications for new matches and deadlines
- Expand interview prep and networking automation

## Notes

For the full concept and system breakdown, see `docs/product-vision.md`.
