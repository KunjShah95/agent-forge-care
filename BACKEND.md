# 🖥️ BACKEND.md — AgentForge Backend Architecture
## FastAPI · SQLAlchemy · PostgreSQL · Qdrant · Redis

> *"This document is the backend blueprint. Every API has a purpose."*

---

## 📌 Overview

The AgentForge backend is a **Python async web application** built with **FastAPI**, **SQLAlchemy 2.0** (async), and **PostgreSQL 16**. It serves as the data plane for the AgentForge Career OS — handling authentication, CRUD operations, background task processing, search integrations, and memory storage.

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Framework** | FastAPI + Uvicorn | High-performance async web server, auto OpenAPI docs |
| **ORM** | SQLAlchemy 2.0 (async) | Database models, queries, migrations |
| **Migrations** | Alembic | Schema versioning (5 migrations) |
| **Database** | PostgreSQL 16 | Canonical data store |
| **Vector DB** | Qdrant | Semantic memory, AI embeddings |
| **Cache / Queue** | Redis | Rate limiting, RQ worker queues |
| **Auth** | Firebase (JWT via jose) | Token verification, auto-provisioning |
| **Background** | RQ (Redis Queue) | Async task processing |
| **Testing** | pytest + httpx + pytest-asyncio | 167+ test functions |

---

## 🏗️ Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry, middleware, lifespan, health check
│   ├── config.py            # Pydantic settings (env vars, validation, auto-generation)
│   ├── database.py          # Async engine, session factory, get_db dependency
│   ├── dependencies.py      # Firebase token verification, Redis rate limiter, auth deps
│   │
│   ├── models/
│   │   ├── user.py          # SQLAlchemy models (User, Profile, Opportunity, Application, etc.)
│   │   └── __init__.py
│   │
│   ├── schemas/
│   │   ├── user.py          # Pydantic request/response schemas
│   │   └── __init__.py
│   │
│   ├── api/
│   │   ├── router.py        # Route registration (all v1 endpoints)
│   │   └── v1/              # 14 route modules
│   │       ├── auth.py      # GET/PATCH /auth/me
│   │       ├── profile.py   # Profile CRUD + avatar upload
│   │       ├── opportunities.py  # Opportunities CRUD, matches, filters, locations, hackathons
│   │       ├── applications.py   # Application pipeline CRUD
│   │       ├── contacts.py      # Networking contacts CRUD
│   │       ├── agents.py        # Agent task management + execution
│   │       ├── memory.py        # Long-term memory CRUD
│   │       ├── analytics.py     # Dashboard metrics, funnel, skills demand
│   │       ├── monitor.py       # Alert configs + monitor settings
│   │       ├── chat.py          # Streaming chat (SSE)
│   │       ├── resume.py        # Resume upload, ATS analysis, search, PDF generation
│   │       ├── notifications.py # Notification CRUD
│   │       ├── status.py        # System status endpoint
│   │       └── hiring_agent.py  # Hiring agent pipeline
│   │
│   ├── agents/              # [See AIML.md]
│   │
│   ├── memory/
│   │   ├── qdrant_client.py # Qdrant connection + collection management
│   │   └── memory_layer.py  # AgentMemory (vector store, search, hybrid scoring)
│   │
│   ├── middleware/
│   │   └── auth.py          # RequestLogMiddleware (timing + status logging)
│   │
│   ├── services/
│   │   ├── model_manager.py    # Multi-provider LLM routing (OpenAI, Anthropic, Gemini, etc.)
│   │   ├── memory_service.py   # Relational memory CRUD
│   │   ├── profile_service.py  # Profile + skills management
│   │   ├── match_service.py    # Opportunity match scoring
│   │   ├── rerank_service.py   # Cohere reranking
│   │   ├── email_service.py    # SendGrid email notifications
│   │   ├── notification_service.py  # Notification creation + dispatch
│   │   └── profile_scraper.py  # GitHub + portfolio enrichment scraping
│   │
│   ├── search/
│   │   └── adapters.py     # 12 search sources (SerpAPI, Tavily, Brave, Exa, scrapes, etc.)
│   │
│   ├── hiring_agent/       # [See AIML.md]
│   │
│   ├── opportunity_agent/  # [See AIML.md]
│   │
│   ├── tasks/
│   │   ├── worker.py           # RQ worker entry point
│   │   ├── agent_tasks.py      # Background agent task execution
│   │   ├── hackathon_scanner.py # Scheduled hackathon scanning
│   │   └── memory_cleanup.py   # Expired memory cleanup
│   │
│   └── utils/
│       ├── embedding.py     # Text embedding generation
│       ├── location.py      # Location parsing (city, state, country)
│       ├── industry.py      # Industry detection
│       ├── work_mode.py     # Remote/hybrid/onsite inference
│       ├── coordinates.py   # Geocoding for map display
│       └── demo_data.py     # Fallback demo data (marked with is_demo: True)
│
├── tests/                   # 22 test files, 167+ test functions
│   ├── conftest.py          # Fixtures, factories, mock data, token generation
│   ├── test_auth.py         # Auth endpoints, Firebase verification, rate limiting
│   ├── test_planner.py      # Goal decomposition, agent dispatch, response formatting
│   ├── test_planner_e2e.py  # End-to-end planner flow
│   ├── test_orchestrator.py # Orchestrator dispatch + scoring
│   ├── test_opportunities.py
│   ├── test_applications.py
│   ├── test_contacts.py
│   ├── test_profile.py
│   ├── test_resume.py       # Resume upload, ATS analysis, search
│   ├── test_analytics.py
│   ├── test_memory.py
│   ├── test_monitor.py
│   ├── test_notifications.py
│   ├── test_notification_service.py
│   ├── test_chat.py
│   ├── test_agents.py
│   ├── test_hiring_agent.py
│   ├── test_integration.py
│   ├── test_errors.py       # Error handling tests
│   ├── test_adapters.py     # Search adapter tests
│   └── test_work_mode.py    # Work mode detection tests
│
├── alembic/                 # Database migrations
├── requirements.txt
├── Dockerfile
├── railway.json             # Railway deployment config
├── render.yaml              # Render deployment config
└── nixpacks.toml            # Nixpacks build config
```

---

## 🔗 API Routes (35+ Endpoints)

| Router | Prefix | Endpoints | Auth |
|--------|--------|-----------|------|
| Auth | `/auth` | GET/PATCH `/me` | Token |
| Profile | `/profile` | GET, PUT, POST `/avatar` | Token |
| Opportunities | `/opportunities` | GET (list), GET `/matches`, GET `/{id}`, POST `/refresh`, GET `/hackathons`, POST `/hackathons/scan`, GET `/filters`, GET `/locations` | Token |
| Applications | `/applications` | GET (list), POST, PATCH `/{id}`, DELETE `/{id}` | Token |
| Contacts | `/contacts` | GET (list), POST, PATCH `/{id}`, DELETE `/{id}` | Token |
| Agents | `/agents` | POST `/planner/run`, GET `/tasks`, GET `/tasks/{id}`, POST `/monitor/run`, POST `/interview-prep`, POST `/research`, POST `/cover-letter`, POST `/resume-tailor`, POST `/career-guidance`, POST `/networking-outreach`, POST `/internship-discover`, POST `/job-discover`, POST `/tasks/{id}/retry`, POST `/tasks/{id}/cancel`, DELETE `/tasks/{id}`, DELETE `/tasks/clear` | Token |
| Memory | `/memory` | GET (list), POST, PATCH `/{id}`, DELETE `/{id}`, GET `/context` | Token |
| Analytics | `/analytics` | GET `/summary`, GET `/funnel`, GET `/skills-demand`, GET `/activity` | Token |
| Monitor | `/monitor` | GET/POST `/alerts`, PATCH/DELETE `/alerts/{id}`, GET/PATCH `/settings` | Token |
| Resume | `/resume` | GET (list), POST `/upload`, GET `/ats-analysis`, GET `/search`, DELETE `/{filename}`, POST `/generate-pdf`, POST `/generate-cover-letter-pdf` | Token |
| Notifications | `/notifications` | GET (list), PATCH `/{id}`, POST `/read-all` | Token |
| Chat | `/chat` | POST `/stream` (SSE) | Optional |
| Hiring Agent | `/hiring-agent` | POST `/pipeline`, GET `/extract`, POST `/evaluate-text`, GET `/ats`, POST `/match-jd`, POST `/cover-letter`, POST `/github-enrich`, POST `/portfolio-enrich`, POST `/live-demos`, GET `/report`, GET `/history` | Token |
| Status | `/status` | GET | None |
| Orchestrator | `/orchestrator` | POST `/run` | Token |
| Health | `/health` | GET | None |

---

## 🔐 Authentication & Security

### Firebase Token Verification

The backend verifies Firebase ID tokens **without needing a service account JSON file**:

1. JWTs use RS256 with dynamic key ID (`kid`) in the header
2. Google's public x509 certificates are fetched from `https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com`
3. Certificates are cached for up to 24 hours (respecting `cache-control` max-age)
4. Token is decoded with `python-jose`, verifying:
   - **Audience** = Firebase Project ID
   - **Issuer** = `https://securetoken.google.com/{project_id}`
   - **Algorithm** = RS256

### User Auto-Provisioning

When a valid Firebase token arrives for a new user:
1. New `User` record created with `firebase_uid`, `email`, `full_name`
2. New `Profile` record created with `is_onboarded: False`
3. Existing users get `firebase_uid` linked on first Firebase login

### Email Verification Enforcement

Most endpoints use `get_current_user()` which checks `email_verified` claim.
Auth/profile endpoints use `get_current_user_unverified()` so users can check their verification status.

### Redis Rate Limiter

- **Sliding window** algorithm using Redis sorted sets
- **100 req/min** for regular endpoints
- **5 req/min** for auth endpoints (login/register)
- **In-memory fallback** when Redis is unavailable
- Stricter limits based on user ID (authenticated) or IP (anonymous)

### Security Headers (API)
All API responses include:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Permissions-Policy: camera=(), microphone=(), geolocation=()`
- `X-RateLimit-*` headers (dynamically computed)

### Log Sanitization
All log messages are auto-sanitized to redact:
- Password/secret/token/key values
- API keys
- Email addresses
- Authorization headers

---

## 🗄️ Database Schema (SQLAlchemy Models)

All models live in `backend/app/models/user.py`:

| Model | Key Fields | Relationships |
|-------|-----------|---------------|
| **User** | id, email, firebase_uid, password_hash (null), full_name, avatar_url, email_verified | → Profile, Opportunity, Application, Contact, etc. |
| **Profile** | id, user_id, school, graduation_date, bio, portfolio_url, linkedin_url, github_url, target_locations, salary_min/max, role_types, company_sizes, career_goal, is_onboarded | → User, → ProfileSkill |
| **Skill** | id, name | → ProfileSkill |
| **ProfileSkill** | profile_id, skill_id, proficiency | → Profile, → Skill |
| **Opportunity** | id, user_id, title, company, location, remote, type, salary_min/max, description, apply_url, skills_required, source, is_demo, is_active | → User, → MatchScore, → Application |
| **Application** | id, user_id, opportunity_id, stage (enum: saved/applied/interviewing/offered/rejected), notes, resume_version, cover_letter | → User, → Opportunity |
| **Contact** | id, user_id, name, role, company, email, status (enum: new/contacted/replied/meeting/connected) | → User |
| **AgentTask** | id, user_id, agent_type (enum), goal_id, input, output, status (queued/running/completed/failed), error | → User |
| **MemoryEntry** | id, user_id, key, value (JSON), weight, ttl_days, created_at | → User |
| **AlertConfig** | id, user_id, name, keywords, locations, opportunity_types, min_match_score, frequency, is_active | → User |
| **MatchScore** | id, opportunity_id, user_id, overall_score, skill_score, location_score, experience_score, company_score, reasons | → User, → Opportunity |
| **PlannerGoal** | id, user_id, goal, status, result | → User |
| **Notification** | id, user_id, title, body, type, read, created_at | → User |

---

## 🔧 Core Services

### config.py (Settings)

Pydantic `BaseSettings` with:
- Auto-generated cryptographically random `jwt_secret` and `secret_key` if not set
- Validation of insecure defaults
- 20+ AI/API key fields with format validation
- Strict production mode requiring `firebase_project_id` and `secret_key`
- Dynamic CORS origin list with Vercel preview support

### database.py

Async SQLAlchemy engine with:
- Connection pooling (10 pool size, 20 overflow)
- Connection health checks (`pool_pre_ping`)
- Recycling idle connections (3600s)
- Async session factory with auto-commit/rollback/close
- `init_db()` creates tables (development); production uses Alembic

### middleware/auth.py

`RequestLogMiddleware` — logs every HTTP request with method, path, status code, and elapsed time.

### services/memory_service.py

Relational memory CRUD with:
- Per-user key-value storage
- Weighted entries for importance ranking
- TTL-based automatic expiration

### services/match_service.py

Opportunity match scoring with:
- Skill matching (profile skills vs. opportunity requirements)
- Location proximity scoring
- Experience level matching
- Company preferences
- Blended overall score (0-100)

### search/adapters.py

Unified search interface across 12 sources:
1. **SerpAPI** (Google Jobs) — structured job listings with company, location, salary
2. **Tavily** — AI-native search for research queries
3. **Google Custom Search** — broad web search
4. **Brave Search** — API-based (2,000 free queries/month)
5. **Exa** — AI-native search API
6. **SearXNG** — self-hosted meta search
7. **Mojeek API** — privacy-focused search
8. **Web scraping** — Google HTML parsing
9. **Mojeek scraping** — privacy-first fallback
10. **DuckDuckGo scraping** — resilient fallback
11. **Job board scraping** — Indeed, LinkedIn, Glassdoor via Google site: search
12. **LinkedIn direct scraping** — jobs search page

Features: User-Agent rotation, retry with exponential backoff, in-memory caching (5 min TTL), deduplication, quality filtering.

---

## 🧪 Testing

| Metric | Value |
|--------|-------|
| Total tests | 167+ |
| Test files | 22 |
| Framework | pytest + pytest-asyncio |
| HTTP client | httpx (ASGITransport) |
| Mock DB | AsyncMock + custom MockResult |
| Coverage | auth, planner, orchestrator, opportunities, applications, contacts, analytics, memory, monitor, resume, notifications, errors, search adapters, integrations |

### Test Conftest

`conftest.py` provides:
- `make_user()`, `make_profile()`, `make_opportunity()`, etc. — factory functions
- `create_firebase_token()` — generates RS256 JWTs with test RSA keys
- `mock_db` fixture — `AsyncMock`-based DB session
- `async_client`, `auth_client` fixtures — HTTPhx clients with overridden dependencies

---

## 🚀 Deployment

### Services
| Service | Provider | Notes |
|---------|----------|-------|
| FastAPI | Railway / Render | Docker container, auto-deploy from GitHub |
| PostgreSQL | Railway / Render Add-on | Managed 16.x |
| Qdrant | Qdrant Cloud (free 1GB) / Self-hosted | Vector search |
| Redis | Railway Add-on | Rate limiter + RQ queue |
| Frontend | Vercel | SPA with API proxy |

### Environment (see DEPLOYMENT.md for full list)
```
Required: JWT_SECRET, SECRET_KEY, FIREBASE_PROJECT_ID, CORS_ORIGINS
At least one: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, GROQ_API_KEY, etc.
Optional for search: TAVILY_API_KEY, SERPAPI_KEY, BRAVE_API_KEY, etc.
Optional: COHERE_API_KEY (reranking), SENDGRID_API_KEY (email), LANGCHAIN_API_KEY (observability)
```

---

## 📐 Design Principles

1. **Async by default** — All DB/IO operations are async; no blocking calls in request handlers
2. **Defense in depth** — Auth, rate limiting, log sanitization, security headers, validation
3. **Graceful degradation** — Every external dependency has a fallback (Redis → in-memory, LLM → template, search → demo data labeled `is_demo: True`)
4. **Zero-config auth** — Firebase tokens verified via dynamic Google certs; no service account file needed
5. **Composable dependencies** — FastAPI `Depends` chain: `get_db` → `get_current_user` → route handler
6. **Consistent error handling** — Global exception handler returns structured `{error, status_code}` JSON

---

> *"A backend that scales from local development to production with zero configuration changes."*

---
*BACKEND.md v1.0 · AgentForge Backend Team · July 2026*
