# 💀 SKULL.md — AgentForge Career OS
## Master System Blueprint · Structural Knowledge Unified Layer Layout

> *"This document is the skeleton. Every bone has a purpose."*

---

## 🧠 What Is SKULL.md?

`SKULL.md` is the **top-level architectural document** for AgentForge Career OS. It defines the complete system topology, module ownership, integration contracts, and engineering philosophy. Every sub-system (`FRONTEND.md`, `BACKEND.md`, `AIML.md`, `CLAUDE.md`) derives from this blueprint.

Think of it as the **founder's technical bible** — the document you hand to a new engineering hire, an investor's due-diligence team, or an AI agent spinning up a new service.

---

## 🏗️ System Identity

| Field              | Value                                              |
|--------------------|----------------------------------------------------|
| **Product Name**   | AgentForge Career OS                               |
| **Version**        | 0.1.0-alpha                                        |
| **Architecture**   | Multi-Agent Autonomous System (MAAS)               |
| **Paradigm**       | Memory-Driven, Event-Sourced, Tool-Augmented       |
| **Primary Stack**  | Next.js · FastAPI · LangGraph · Qdrant · Neo4j     |
| **AI Backbone**    | GPT-4o · Claude 3.5 · Gemini 1.5 · Llama 3        |
| **Deployment**     | Kubernetes on AWS · Vercel (Edge) · Docker         |
| **License**        | Proprietary / Internal Use Only                    |

---

## 📐 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER INTERFACE LAYER                         │
│              Next.js 14 · React · TailwindCSS · Framer Motion       │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │ HTTPS / WebSocket
┌─────────────────────────────────▼───────────────────────────────────┐
│                          API GATEWAY LAYER                          │
│                   Kong / AWS API Gateway · OAuth2                   │
└──────┬──────────────────────────┬───────────────────────────────────┘
       │                          │
┌──────▼──────┐           ┌───────▼────────┐
│  Auth       │           │  Rate Limiter  │
│  Clerk/     │           │  Redis Token   │
│  Auth0      │           │  Bucket        │
└──────┬──────┘           └───────┬────────┘
       │                          │
┌──────▼──────────────────────────▼───────────────────────────────────┐
│                      ORCHESTRATOR CORE                              │
│   Intent Router → Planner → Task Graph → Execution → Validation    │
│                           → Reflection → Synthesis                  │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
     ┌────────────────────────────┼────────────────────────────┐
     │                            │                            │
┌────▼────────┐          ┌────────▼───────┐          ┌────────▼────────┐
│  AGENT      │          │   MEMORY       │          │  TOOL           │
│  ECOSYSTEM  │          │   SYSTEM       │          │  REGISTRY       │
│  9 Agents   │          │  6-Tier Mem    │          │  8+ Adapters    │
└────┬────────┘          └────────┬───────┘          └────────┬────────┘
     │                            │                            │
     └────────────────────────────▼────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                         DATA LAYER                                  │
│   PostgreSQL · Redis · Qdrant · Neo4j · S3                         │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
┌─────────────────────────────────▼───────────────────────────────────┐
│                         EVENT BUS                                   │
│                    Kafka / NATS · Event Sourcing                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Module Map

| Module          | File          | Responsibility                                      |
|-----------------|---------------|-----------------------------------------------------|
| Frontend        | FRONTEND.md   | UI, UX, State Management, SSR, WebSocket clients    |
| Backend         | BACKEND.md    | API, Orchestrator, DB, Auth, Event Bus, Services    |
| AI/ML           | AIML.md       | Agents, Memory, LLM Router, Embeddings, Validation  |
| Claude Protocol | CLAUDE.md     | AI behavior spec, prompting rules, memory contracts |

---

## 🔀 Data Flow — Request Lifecycle

```
1. User submits goal: "Find me remote Python internships in Europe"
2. Frontend sends POST /api/v1/intent
3. API Gateway validates JWT, applies rate limit
4. Intent Router classifies: [SEARCH_INTERNSHIP, FILTER_LOCATION, FILTER_REMOTE]
5. Planner Agent decomposes into 4 sub-tasks
6. Task Graph Builder creates DAG with parallelism opportunities
7. Execution Engine dispatches:
   - Internship Agent → LinkedIn + Internshala + Wellfound
   - Research Agent → Company intelligence fetch
8. Results written to Working Memory
9. Resume Agent pulls user's CV from Long-Term Memory
10. Cover Letter Agent generates tailored draft
11. Validation Layer checks output quality
12. Reflection Agent scores and iterates if needed
13. Response Synthesizer compiles final JSON
14. Frontend renders opportunity cards + application drafts
15. Event Bus emits: OpportunityDiscovered, DraftGenerated
```

---

## 🌐 Service Registry

| Service              | Port  | Protocol    | Owner       |
|----------------------|-------|-------------|-------------|
| Next.js Frontend     | 3000  | HTTP/WS     | Frontend    |
| FastAPI Backend      | 8000  | HTTP        | Backend     |
| Orchestrator Engine  | 8001  | HTTP/gRPC   | Backend     |
| LangGraph Runner     | 8002  | HTTP        | AIML        |
| Qdrant Vector DB     | 6333  | HTTP/gRPC   | AIML        |
| Neo4j Graph DB       | 7474  | HTTP/Bolt   | Backend     |
| PostgreSQL           | 5432  | TCP         | Backend     |
| Redis                | 6379  | TCP         | Backend     |
| Kafka Broker         | 9092  | TCP         | Backend     |
| Grafana              | 3001  | HTTP        | Infra       |
| LangSmith            | SaaS  | HTTPS       | AIML        |

---

## 🔐 Security Model

```
Authentication:   Clerk (Web) / Auth0 (Enterprise)
Authorization:    RBAC with 4 roles: viewer, user, power_user, admin
Encryption:       AES-256 at rest · TLS 1.3 in transit
Secrets:          AWS Secrets Manager / HashiCorp Vault
PII Handling:     Anonymized in logs · Encrypted in DB · GDPR Article 17 compliant
Audit Trail:      Every agent action logged with user_id, timestamp, tool_used
Rate Limiting:    Per-user: 100 req/min · Per-IP: 500 req/min
```

---

## 📊 Observability Stack

| Concern          | Tool               | What It Tracks                            |
|------------------|--------------------|-------------------------------------------|
| LLM Traces       | LangSmith          | Prompt, completion, latency, cost         |
| Metrics          | Prometheus/Grafana | API latency, DB queries, error rates      |
| Distributed Trace| OpenTelemetry      | Cross-service request tracing             |
| Logs             | CloudWatch/Loki    | Structured JSON logs, error aggregation   |
| Alerts           | PagerDuty          | P1/P2 on-call escalation                  |

---

## 🚀 Deployment Architecture

```
                    ┌──────────────┐
                    │   Vercel     │  ← Frontend (Edge SSR)
                    │   CDN Edge   │
                    └──────┬───────┘
                           │
                    ┌──────▼───────┐
                    │ AWS ALB      │  ← Load Balancer
                    └──────┬───────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌─────▼──────┐ ┌────▼───────┐
     │  K8s Pod    │ │  K8s Pod   │ │  K8s Pod   │
     │  FastAPI    │ │  FastAPI   │ │  Orchestr. │
     └──────┬──────┘ └─────┬──────┘ └────┬───────┘
            │              │              │
            └──────────────▼──────────────┘
                    ┌──────────────┐
                    │  RDS Aurora  │  PostgreSQL
                    │  ElastiCache │  Redis
                    │  Qdrant EC2  │  Vector
                    │  Neo4j AuraDB│  Graph
                    └──────────────┘
```

---

## 📋 Engineering Principles

1. **Memory-First Design** — Every agent action must read and write to the memory system.
2. **Tool Composability** — All external APIs are wrapped as versioned, observable tools.
3. **Human-in-the-Loop** — No application is submitted without explicit user approval.
4. **Fail-Safe Execution** — Every agent task has a validation step and retry budget.
5. **Cost Awareness** — Route cheap tasks to cheap models. Log token spend per user.
6. **Auditability** — Every AI decision must be explainable and reversible.
7. **Privacy by Design** — Minimize PII surface area. Encrypt everything.
8. **Async by Default** — Use event queues for all non-blocking tasks.

---

## 📁 Monorepo Structure

```
agentforge/
├── apps/
│   ├── web/                    # Next.js frontend
│   ├── api/                    # FastAPI backend
│   └── orchestrator/           # LangGraph engine
├── packages/
│   ├── agents/                 # Agent definitions
│   ├── memory/                 # Memory system
│   ├── tools/                  # Tool registry
│   ├── models/                 # Shared Pydantic/TypeScript types
│   └── ui/                     # Shared component library
├── infra/
│   ├── k8s/                    # Kubernetes manifests
│   ├── terraform/              # AWS infrastructure
│   └── docker/                 # Dockerfiles
├── docs/
│   ├── SKULL.md                # ← You are here
│   ├── CLAUDE.md               # AI behavior spec
│   ├── FRONTEND.md             # Frontend architecture
│   ├── BACKEND.md              # Backend architecture
│   └── AIML.md                 # AI/ML architecture
└── scripts/
    ├── seed.py                 # DB seeding
    └── eval/                   # Agent evaluation scripts
```

---

## 🗺️ Roadmap Overview

| Phase | Name                         | Status      | Target     |
|-------|------------------------------|-------------|------------|
| 1     | Career Copilot               | 🟡 In Dev   | Q3 2025    |
| 2     | Autonomous Monitoring        | 🔵 Planned  | Q4 2025    |
| 3     | One-Click Application Engine | 🔵 Planned  | Q1 2026    |
| 4     | AI Recruiter Marketplace     | 🔵 Planned  | Q2 2026    |
| 5     | Multi-Agent Career OS        | 🔵 Planned  | Q4 2026    |

---

## 🤝 Contributing

Read the sub-system docs before contributing:
- **AI/ML work** → Read `AIML.md` + `CLAUDE.md`
- **Frontend work** → Read `FRONTEND.md`
- **Backend work** → Read `BACKEND.md`
- **Full-stack features** → Read all four

> *"A system without memory is just a script. AgentForge remembers."*

---
*Last updated: May 2025 · Maintained by the AgentForge Core Team*
