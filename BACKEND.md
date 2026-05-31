# ⚙️ BACKEND.md — AgentForge Career OS
## Backend Architecture · API Design · Database Schema · Event System · Services

> *"The backend is the nervous system. Every signal, every memory, every action flows through here."*

---

## 🧭 Overview

The AgentForge backend is a **Python-first distributed system** built on FastAPI, orchestrated with LangGraph, and backed by a polyglot persistence layer. It implements an event-sourced architecture with a clear separation between the API layer, the orchestration engine, and the data layer.

---

## ⚙️ Technology Stack

| Category             | Technology          | Version   | Purpose                                          |
|----------------------|---------------------|-----------|--------------------------------------------------|
| API Framework        | FastAPI             | 0.111.x   | Async REST API, WebSockets, OpenAPI docs         |
| Language             | Python              | 3.12      | Backend, agents, ML                              |
| Orchestration        | LangGraph           | 0.1.x     | Agent DAG execution, state machines              |
| Task Queue           | Celery + Redis      | 5.3.x     | Async job processing, periodic tasks            |
| Message Broker       | Kafka (MSK) / NATS  | 3.7.x     | Event streaming, inter-service messaging         |
| ORM                  | SQLAlchemy 2.0      | 2.0.x     | Async DB access, migrations via Alembic          |
| Validation           | Pydantic v2         | 2.7.x     | Request/response models, settings               |
| Auth Middleware      | PyJWT + Clerk SDK   | -         | JWT validation, RBAC enforcement                 |
| HTTP Client          | httpx               | 0.27.x    | Async external API calls                         |
| Caching              | Redis (via aioredis)| 7.x       | Response cache, rate limiting, sessions          |
| Object Storage       | boto3 (S3)          | 1.34.x    | Resume storage, report archival                  |
| Testing              | pytest + pytest-asyncio | latest | Unit, integration, contract tests            |
| Container            | Docker              | 25.x      | Service containerization                         |
| Orchestration        | Kubernetes (EKS)    | 1.29      | Production deployment, scaling                   |

---

## 📁 Directory Structure

```
apps/api/
├── main.py                       # FastAPI app factory
├── config.py                     # Settings (pydantic-settings)
├── routers/
│   ├── auth.py                   # Authentication endpoints
│   ├── agents.py                 # Agent invocation endpoints
│   ├── opportunities.py          # Job/internship endpoints
│   ├── applications.py           # Application tracking
│   ├── resume.py                 # Resume management
│   ├── memory.py                 # Memory read/write
│   ├── analytics.py              # Career analytics
│   └── webhooks.py               # External webhook receivers
├── services/
│   ├── agent_service.py          # Agent orchestration
│   ├── opportunity_service.py    # Opportunity discovery + ranking
│   ├── resume_service.py         # Resume parsing + generation
│   ├── memory_service.py         # Memory layer abstraction
│   ├── notification_service.py   # Email + push notifications
│   └── search_service.py         # Unified search orchestration
├── models/
│   ├── db/                       # SQLAlchemy ORM models
│   ├── schemas/                  # Pydantic request/response schemas
│   └── events/                   # Event schemas (Kafka)
├── middleware/
│   ├── auth.py                   # JWT verification + RBAC
│   ├── rate_limit.py             # Per-user rate limiting
│   ├── logging.py                # Structured JSON logging
│   └── tracing.py                # OpenTelemetry instrumentation
├── workers/
│   ├── opportunity_worker.py     # Background opportunity scanning
│   ├── notification_worker.py    # Email/push delivery
│   └── analytics_worker.py      # Career metrics computation
├── db/
│   ├── session.py                # Async SQLAlchemy session
│   ├── migrations/               # Alembic migrations
│   └── seeds/                    # Development seed data
└── tests/
    ├── unit/
    ├── integration/
    └── e2e/
```

---

## 🔌 API Design

### Base URL
```
https://api.agentforge.ai/v1
```

### Authentication
```
Authorization: Bearer <clerk_jwt_token>
X-Request-ID: <uuid4>            # For distributed tracing
```

### Core Endpoints

#### Agents

```http
POST   /v1/agents/invoke
POST   /v1/agents/stream          # SSE streaming response
GET    /v1/agents/status/{id}
DELETE /v1/agents/{id}/cancel
GET    /v1/agents/history
```

**POST /v1/agents/invoke**
```json
Request:
{
  "agent_type": "resume_agent",
  "intent": "optimize_for_role",
  "context": {
    "job_description": "...",
    "resume_id": "uuid",
    "target_company": "Google"
  },
  "stream": false
}

Response:
{
  "task_id": "uuid",
  "status": "completed",
  "output": {
    "resume_variant": {...},
    "ats_score": 87,
    "keywords_added": ["distributed systems", "kubernetes"],
    "reflection": {...}
  },
  "tokens_used": 2341,
  "model_used": "claude-3-5-sonnet",
  "duration_ms": 3420
}
```

#### Opportunities

```http
GET    /v1/opportunities?filters=...
GET    /v1/opportunities/{id}
POST   /v1/opportunities/search     # Trigger fresh agent search
POST   /v1/opportunities/{id}/save
DELETE /v1/opportunities/{id}/save
GET    /v1/opportunities/saved
```

**GET /v1/opportunities** Query Params:
```
type:         internship | full-time | contract
location:     remote | hybrid | on-site | city_name
experience:   0-1 | 1-3 | 3-5 | 5+
min_match:    integer (0-100)
sort:         match_score | deadline | posted_date
page:         integer
limit:        integer (max 50)
```

#### Applications

```http
GET    /v1/applications
POST   /v1/applications
GET    /v1/applications/{id}
PATCH  /v1/applications/{id}/status
POST   /v1/applications/{id}/notes
GET    /v1/applications/{id}/timeline
```

#### Memory

```http
GET    /v1/memory/context
POST   /v1/memory/episode
GET    /v1/memory/episodes?limit=20
POST   /v1/memory/search           # Semantic search over memory
DELETE /v1/memory/episode/{id}
```

#### Analytics

```http
GET    /v1/analytics/overview
GET    /v1/analytics/funnel         # Application → Offer funnel
GET    /v1/analytics/skills         # Skill gap analysis
GET    /v1/analytics/market         # Market demand for user's skills
```

---

## 🗄️ Database Schema

### PostgreSQL (Relational Data)

```sql
-- Users
CREATE TABLE users (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  clerk_id      VARCHAR(255) UNIQUE NOT NULL,
  email         VARCHAR(255) UNIQUE NOT NULL,
  name          VARCHAR(255),
  current_role  VARCHAR(255),
  target_role   VARCHAR(255),
  experience_level VARCHAR(50),
  location_pref JSONB,              -- {remote: true, cities: [...]}
  skills        JSONB,              -- [{name, level, years}]
  career_goals  TEXT,
  preferences   JSONB,              -- communication, risk tolerance
  created_at    TIMESTAMPTZ DEFAULT NOW(),
  updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Opportunities
CREATE TABLE opportunities (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  external_id   VARCHAR(500),       -- Source platform's ID
  source        VARCHAR(100),       -- linkedin, wellfound, internshala
  title         VARCHAR(500) NOT NULL,
  company_name  VARCHAR(255) NOT NULL,
  company_id    UUID REFERENCES companies(id),
  type          VARCHAR(50),        -- internship, full-time, contract
  location_type VARCHAR(50),        -- remote, hybrid, on-site
  location      VARCHAR(255),
  description   TEXT,
  requirements  JSONB,
  salary_range  JSONB,              -- {min, max, currency}
  deadline      DATE,
  posted_at     TIMESTAMPTZ,
  raw_data      JSONB,              -- Original scraped data
  embedding_id  VARCHAR(255),       -- Reference to Qdrant embedding
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- Applications
CREATE TABLE applications (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
  opportunity_id  UUID REFERENCES opportunities(id),
  status          VARCHAR(50) DEFAULT 'saved',
                  -- saved, applied, screening, interview, offer, rejected, withdrawn
  applied_at      TIMESTAMPTZ,
  resume_id       UUID REFERENCES resumes(id),
  cover_letter_id UUID REFERENCES cover_letters(id),
  match_score     FLOAT,
  notes           TEXT,
  metadata        JSONB,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Application Timeline
CREATE TABLE application_events (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID REFERENCES applications(id) ON DELETE CASCADE,
  event_type     VARCHAR(100),
  description    TEXT,
  data           JSONB,
  created_at     TIMESTAMPTZ DEFAULT NOW()
);

-- Resumes
CREATE TABLE resumes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
  name        VARCHAR(255) NOT NULL,
  s3_key      VARCHAR(500),         -- Original file
  content     JSONB,                -- Parsed structured content
  is_master   BOOLEAN DEFAULT FALSE,
  version     INTEGER DEFAULT 1,
  ats_score   FLOAT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Episodes (Episodic Memory)
CREATE TABLE memory_episodes (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
  agent_type   VARCHAR(100),
  action       VARCHAR(255),
  result       TEXT,
  quality_score FLOAT,
  tokens_used  INTEGER,
  model_used   VARCHAR(100),
  tool_calls   JSONB,
  metadata     JSONB,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Companies
CREATE TABLE companies (
  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name         VARCHAR(255) UNIQUE NOT NULL,
  website      VARCHAR(500),
  size         VARCHAR(50),
  funding      VARCHAR(100),
  tech_stack   JSONB,
  culture_tags JSONB,
  glassdoor    JSONB,
  last_scraped TIMESTAMPTZ,
  created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_applications_user_status ON applications(user_id, status);
CREATE INDEX idx_opportunities_source ON opportunities(source, external_id);
CREATE INDEX idx_memory_episodes_user ON memory_episodes(user_id, created_at DESC);
```

### Redis Schema (Cache & Sessions)

```
# User sessions
session:{user_id}                  → JWT + metadata (TTL: 24h)

# Rate limiting
rate:{user_id}:{endpoint}          → request count (TTL: 60s)

# Response cache
cache:opportunities:{filter_hash}  → JSON array (TTL: 30min)
cache:company:{company_id}         → company brief (TTL: 6h)

# Agent task status
agent:task:{task_id}               → {status, progress, output} (TTL: 1h)

# Working memory (active session)
memory:working:{user_id}           → JSON session context (TTL: 4h)

# Job queues
celery:queue:default               → task payloads
celery:queue:agents                → agent task payloads
celery:queue:notifications         → email/push payloads
```

---

## 🎯 Orchestrator Engine

### Task Graph Builder

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class AgentState(TypedDict):
    user_id: str
    intent: str
    tasks: List[Task]
    completed: List[str]
    outputs: dict
    memory_context: dict
    error: str | None

def build_career_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    
    # Nodes
    graph.add_node("intent_router",    intent_router_node)
    graph.add_node("planner",          planner_node)
    graph.add_node("internship_agent", internship_agent_node)
    graph.add_node("job_agent",        job_agent_node)
    graph.add_node("resume_agent",     resume_agent_node)
    graph.add_node("research_agent",   research_agent_node)
    graph.add_node("cover_agent",      cover_letter_agent_node)
    graph.add_node("validator",        validation_node)
    graph.add_node("reflector",        reflection_node)
    graph.add_node("synthesizer",      response_synthesizer_node)
    
    # Edges
    graph.set_entry_point("intent_router")
    graph.add_edge("intent_router", "planner")
    graph.add_conditional_edges("planner", route_to_agents, {
        "internship": "internship_agent",
        "job":        "job_agent",
        "resume":     "resume_agent",
        "research":   "research_agent",
        "cover":      "cover_agent",
    })
    
    for agent in ["internship_agent", "job_agent", "resume_agent", 
                  "research_agent", "cover_agent"]:
        graph.add_edge(agent, "validator")
    
    graph.add_conditional_edges("validator", check_quality, {
        "pass":   "synthesizer",
        "fail":   "reflector",
        "abort":  END
    })
    
    graph.add_edge("reflector", "validator")
    graph.add_edge("synthesizer", END)
    
    return graph.compile()
```

---

## 📨 Event System

### Event Schemas

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any

class BaseEvent(BaseModel):
    event_id: str
    event_type: str
    user_id: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}

class OpportunityDiscoveredEvent(BaseEvent):
    event_type: str = "opportunity.discovered"
    opportunity_id: str
    source: str
    match_score: float

class ApplicationSubmittedEvent(BaseEvent):
    event_type: str = "application.submitted"
    application_id: str
    opportunity_id: str
    company_name: str

class InterviewScheduledEvent(BaseEvent):
    event_type: str = "interview.scheduled"
    application_id: str
    scheduled_at: datetime
    interview_type: str  # technical, behavioral, system_design

class OfferReceivedEvent(BaseEvent):
    event_type: str = "offer.received"
    application_id: str
    company_name: str
    role: str
    deadline: Optional[datetime]
```

### Kafka Topics

```
agentforge.opportunities.discovered   → analytics, notification consumers
agentforge.applications.submitted     → tracker, reminder, analytics
agentforge.applications.status_change → notification, analytics
agentforge.interviews.scheduled       → reminder, prep agent trigger
agentforge.offers.received            → notification, analytics
agentforge.users.profile_updated      → memory update, re-ranking trigger
agentforge.agents.completed           → analytics, cost tracking
```

---

## 🔐 Security Implementation

```python
# middleware/auth.py
from fastapi import Request, HTTPException, status
from functools import wraps
import jwt

class AuthMiddleware:
    RBAC_POLICIES = {
        "viewer":     {"read"},
        "user":       {"read", "write", "agent_invoke"},
        "power_user": {"read", "write", "agent_invoke", "bulk_apply"},
        "admin":      {"read", "write", "agent_invoke", "bulk_apply", "admin"}
    }
    
    async def verify_token(self, request: Request):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise HTTPException(status_code=401, detail="Missing token")
        
        try:
            payload = jwt.decode(token, settings.CLERK_PUBLIC_KEY, 
                                algorithms=["RS256"])
            request.state.user_id = payload["sub"]
            request.state.role = payload.get("role", "user")
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")
    
    def require_permission(self, permission: str):
        def decorator(func):
            @wraps(func)
            async def wrapper(request: Request, *args, **kwargs):
                role = request.state.role
                allowed = self.RBAC_POLICIES.get(role, set())
                if permission not in allowed:
                    raise HTTPException(status_code=403, detail="Insufficient permissions")
                return await func(request, *args, **kwargs)
            return wrapper
        return decorator
```

---

## 📊 Background Workers (Celery)

```python
# workers/opportunity_worker.py
from celery import Celery
from celery.schedules import crontab

app = Celery('agentforge')

@app.task(bind=True, max_retries=3, default_retry_delay=60)
def scan_opportunities(self, user_id: str):
    """
    Runs every 6 hours per active user.
    Triggers Opportunity Monitor Agent to scan all configured platforms.
    """
    try:
        user = UserService.get(user_id)
        agent = OpportunityMonitorAgent(user=user)
        new_opps = agent.scan_all_platforms()
        
        for opp in new_opps:
            if opp.match_score > user.preferences.min_match_threshold:
                OpportunityService.save(opp, user_id)
                events.publish(OpportunityDiscoveredEvent(
                    user_id=user_id,
                    opportunity_id=opp.id,
                    source=opp.source,
                    match_score=opp.match_score
                ))
    except Exception as exc:
        self.retry(exc=exc)

# Schedule
app.conf.beat_schedule = {
    'scan-opportunities-every-6-hours': {
        'task': 'workers.opportunity_worker.scan_opportunities',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    'send-daily-digest': {
        'task': 'workers.notification_worker.send_daily_digest',
        'schedule': crontab(hour=8, minute=0),
    },
    'compute-analytics': {
        'task': 'workers.analytics_worker.compute_user_analytics',
        'schedule': crontab(hour='*/12', minute=30),
    }
}
```

---

## 🔍 Rate Limiting

```python
# middleware/rate_limit.py
RATE_LIMITS = {
    "/v1/agents/invoke":    "10/minute",
    "/v1/agents/stream":    "5/minute",
    "/v1/opportunities":    "60/minute",
    "/v1/applications":     "30/minute",
    "default":              "100/minute"
}
```

---

## 🧪 Testing Strategy

```python
# tests/integration/test_agent_flow.py
@pytest.mark.asyncio
async def test_resume_optimization_flow(client, test_user, test_resume):
    response = await client.post(
        "/v1/agents/invoke",
        json={
            "agent_type": "resume_agent",
            "intent": "optimize_for_role",
            "context": {
                "job_description": SAMPLE_JD,
                "resume_id": test_resume.id
            }
        },
        headers={"Authorization": f"Bearer {test_user.token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["output"]["ats_score"] > 70
    assert len(data["output"]["keywords_added"]) > 0
```

---

## 🚀 Deployment Config

```yaml
# k8s/backend-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentforge-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentforge-api
  template:
    spec:
      containers:
      - name: api
        image: agentforge/api:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: agentforge-secrets
              key: database-url
```

---

> *"A backend that scales is one that was designed to scale from day one."*

---
*BACKEND.md v1.0 · AgentForge Backend Team · Confidential*
