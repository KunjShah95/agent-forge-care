# 🤖 AIML.md — AgentForge AI/ML Architecture
## LangGraph · Multi-Agent Orchestration · Memory · LLM Routing

> *"This document is the AI/ML blueprint. Every agent has a purpose."*

---

## 📌 Overview

The AgentForge AI/ML layer is a **multi-agent orchestration system** built on **LangGraph** and **LangChain**, integrating 8 specialized agents coordinated by a central Planner/Orchestrator. It features a hybrid memory system (relational + vector), multi-provider LLM routing, and automated quality scoring.

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Orchestration** | LangGraph (StateGraph) + Custom Orchestrator | Agent coordination, task graph execution |
| **Class-based Agents** | BaseAgent (custom) | ResumeAgent, InterviewAgent, NetworkingAgent, MonitorAgent, GuidanceAgent, InternshipAgent, JobAgent, ResearchAgent |
| **LLM Routing** | ModelManager (LangChain) | Multi-provider fallback chain |
| **Vector Memory** | Qdrant | Semantic embeddings, hybrid search |
| **Relational Memory** | PostgreSQL | Structured key-value memory |
| **Reranking** | Cohere | Two-stage scoring (cosine + semantic) |
| **Hiring Agent** | Custom pipeline | ATS analysis, resume evaluation, JD matching |
| **Prompt Management** | Jinja2 templates | Isolated prompt templates per agent |

---

## 🏗️ Agent Hierarchy

```
User Goal
    │
    ▼
OrchestratorAgent (orchestrator/service.py)
    │
    ├── 1. Goal Decomposition (planner.py)
    │      └── LLM breaks goal into structured TaskDef[] with agent_type, action, params, priority
    │
    ├── 2. Dynamic Filtering
    │      └── Skips irrelevant agents (e.g., internship if user has no interest)
    │
    ├── 3. Dispatch
    │      ├── Class-based agents (AGENT_REGISTRY)
    │      │   ├── ResumeAgent      — ATS analysis, resume tailoring, cover letters
    │      │   ├── InterviewAgent   — Mock questions, answer review, feedback
    │      │   ├── NetworkingAgent  — Outreach messages, contact generation
    │      │   ├── MonitorAgent     — 24/7 opportunity scanning + alerts
    │      │   └── GuidanceAgent    — Career planning, strategy, advice
    │      │
    │      └── Function-based agents (FUNCTION_AGENTS)
    │          ├── internship_agent.py  — discover_internships()
    │          ├── job_agent.py         — discover_jobs()
    │          └── research_agent.py    — conduct_research()
    │
    ├── 4. Retry + Timeout
    │      └── 2 retries, exponential backoff, 120s timeout per agent
    │
    ├── 5. Reflection Scoring
    │      └── _score_agent_output() — 5 dimensions (0-10 each, total 0-50)
    │
    └── 6. Persistence
           └── PlannerGoal + AgentTask → PostgreSQL
```

### Class-Based Agents (AGENT_REGISTRY)

Each agent follows a three-layer architecture:

```
agent_name/
├── __init__.py      # Exports agent class
├── service.py       # Thin action-router (extends BaseAgent, implements execute())
├── handlers.py      # Implementation: LLM calls, enrichment context, fallback templates
└── constants.py     # Config: temperatures, limits, memory keys
```

#### ResumeAgent
- **Actions:** `tailor`, `cover_letter`
- **Handlers:** Gathers profile + GitHub/portfolio enrichment, calls LLM for tailored suggestions, stores in memory
- **Fallback:** Template-based suggestions when LLM unavailable

#### InterviewAgent
- **Actions:** `prepare`, `review_answer`
- **Handlers:** Generates behavioral + technical questions based on skills/company, scores answers on relevance/clarity/impact
- **Fallback:** Pre-written question templates

#### NetworkingAgent
- **Actions:** `outreach`
- **Handlers:** Generates personalized connection requests, follow-up messages, informational interview requests
- **Fallback:** Template-based outreach drafts

#### MonitorAgent
- **Actions:** `scan`, `analyze`
- **Handlers:** Discovers opportunities across 50+ sources, deduplicates, scores against user profile
- **Fallback:** Returns labeled demo data (`is_demo: True`)

#### GuidanceAgent
- **Actions:** `guidance`, `plan`
- **Handlers:** Profile-driven career strategy, skill gap analysis, 30/60/90-day action plans
- **Fallback:** Structured template responses

### Function-Based Agents (FUNCTION_AGENTS)

Standalone async functions called directly:

| Function | Source | Purpose |
|----------|--------|---------|
| `discover_internships()` | internship_agent.py | Searches internship listings |
| `discover_jobs()` | job_agent.py | Searches job listings |
| `conduct_research()` | research_agent.py | Company intelligence, market analysis |

### Legacy LangGraph

`graph.py` contains an alternative orchestration path using a compiled `StateGraph` with three nodes:
1. `decompose_goal_node` — LLM goal → JSON task list
2. `dispatch_all_agents_node` — Parallel `asyncio.gather()` over all agents
3. `generate_final_response_node` — Synthesize results into final output

---

## 🧠 Memory System

### Two-Tier Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Memory System                        │
├───────────────┬─────────────────────────────────────┤
│  Relational   │         Vector (Qdrant)              │
│  (PostgreSQL) │                                     │
├───────────────┼─────────────────────────────────────┤
│  MemoryEntry  │  memory_notes (user preferences)     │
│  key/value    │  opportunity_embeddings (job vectors)│
│  weight/ttl   │  resume_embeddings (resume chunks)   │
└───────────────┴─────────────────────────────────────┘
```

### Relational Memory (`MemoryService`)
- **Storage:** `MemoryEntry` table with `(user_id, key, value(JSON), weight, ttl_days)`
- **Usage:** Agent preferences, session history, user feedback
- **TTL:** Automatic expiration via `cleanup_expired_memory()` background task

### Vector Memory (`AgentMemory`)
- **Storage:** Qdrant collections with 1536-dim embeddings
- **Collections:**
  - `memory_notes` — Semantic user knowledge (profile, preferences, feedback)
  - `opportunity_embeddings` — Opportunity descriptions for match scoring
  - `resume_embeddings` — Chunked resume text for semantic search
- **Hybrid Scoring:** Two-stage blend:
  1. Qdrant cosine similarity (fast recall)
  2. Cohere reranker (deep semantic relevance)
  3. Weighted formula: `score = 0.4 * qdrant_score + 0.6 * reranker_score`

### Enrichment Context (`build_enrichment_context()`)
Before any agent execution, enrichment gathers:
- **GitHub:** Public repos, languages, stars, project highlights
- **Portfolio:** Scraped portfolio website (skills, projects, experience)
- **Hiring Agent:** ATS analysis, resume extraction, JD match scores

---

## 🔄 LLM Routing

### ModelManager (`services/model_manager.py`)

Multi-provider routing with automatic fallback chain:

```
get_completion_llm(temperature, preferred_provider)
    │
    ├── 1. Try preferred provider (e.g., "openai")
    ├── 2. Fall back to configured providers in priority order
    ├── 3. Return None if all providers unavailable
    └── Route to appropriate model:
         ├── Simple tasks → Gemini Flash / Groq (cost-optimized)
         └── Complex tasks → Claude / GPT-4o (deep reasoning)
```

**Supported Providers:** OpenAI, Anthropic, Google Gemini, Groq, Mistral, OpenRouter, Ollama, DeepSeek, Together AI, Fireworks AI

**Embedding Providers:** OpenAI, Google Gemini, HuggingFace (local), Ollama (local)

### Cost Management

| Model | Max Tokens | Use Case |
|-------|-----------|----------|
| gpt-4o-mini | 16K | Planning, structured output |
| claude-sonnet-4 | 8K | Research, coaching, writing |
| gemini-2.0-flash | 8K | Fast retrieval, classification |
| llama-3.3-70b (Groq) | 8K | Batch processing, cost control |

---

## 📝 Prompt Templates

Housed in `backend/app/agents/prompts/` and `backend/app/hiring_agent/prompts/templates/`:

```
agents/prompts/
├── resume.py         # tailor_resume_prompt, cover_letter_prompt
├── interview.py      # prepare_interview_prompt, review_answer_prompt
└── networking.py     # outreach_prompt

hiring_agent/prompts/templates/
├── system_message.jinja          # Agent persona + behavioral rules
├── basics.jinja                  # Resume basics extraction
├── work.jinja                    # Work experience extraction
├── education.jinja               # Education extraction
├── skills.jinja                  # Skills extraction
├── projects.jinja                # Project extraction
├── awards.jinja                  # Awards extraction
├── resume_evaluation_system_message.jinja  # Eval system prompt
├── resume_evaluation_criteria.jinja        # Grading rubric
└── github_project_selection.jinja         # GitHub project scoring
```

All prompts follow a structured format with conditional blocks for enrichment context (GitHub, portfolio, hiring agent data).

---

## 🏷️ Quality Scoring (Reflection)

After every orchestrated run, each agent's output is scored on 5 dimensions:

| Dimension | Max | What It Measures |
|-----------|-----|------------------|
| accuracy | 10 | No hallucination markers, verifiable sources |
| specificity | 10 | Tailored to user's skills/context, not generic |
| actionability | 10 | Contains concrete next steps |
| tone_match | 10 | Matches user's communication preferences |
| format_quality | 10 | Correct structure, valid JSON, readable |

**Total: 0–50 per agent.** Scores streamed to UI as structured SSE events (`quality_score`) for rich frontend rendering.

**Threshold:** Total < 35 → trigger reflection loop, regenerate (up to 2 iterations).

---

## 🏥 Hiring Agent

The Hiring Agent is a specialized pipeline for resume evaluation and JD matching:

```
resume PDF ──→ PyMuPDF extract ──→ LLM section parsing (ThreadPool, 6 sections)
                                          │
                    ┌─────────────────────┼──────────────────┐
                    ▼                     ▼                  ▼
              ResumeBasics           WorkExperience       Skills
              (name, email,           (company,            (name,
               summary)                position, dates)     keywords)
                    │
                    ▼
          Resume Evaluation ──→ JD Matching ──→ ATS Analysis
          (open source,          (skill,               (keyword coverage,
           projects,              experience,           format score,
           production code)       education match)      action verbs)
                    │
                    ▼
          Final Report
          (scores, improvements, recommendations)
```

- **PDF Extraction:** PyMuPDF with optional `pymupdf4llm` RAG for markdown output
- **Section Parsing:** 6 parallel LLM calls via `ThreadPoolExecutor` for resumes, education, skills, projects, awards
- **Enrichment:** GitHub profile scraping, portfolio website scraping, live demo status checks
- **Evaluation:** Weighted scoring on open_source, self_projects, production, technical_skills
- **Cover Letter:** LLM-generated personalized cover letters from resume + JD

---

## 📊 Data Flow — Full Agent Lifecycle

```
1. User submits goal: "Find remote Python internships in Europe"
2. Frontend → POST /api/v1/agents/planner/run { goal: "..." }
3. Backend creates AgentTask (status=queued)
4. Orchestrator decomposes goal:
   → TaskDef(agent=monitor, action=scan, params={skills, location, remote})
   → TaskDef(agent=internship, action=discover, params={query, location})
5. Agents execute in parallel (asyncio.gather):
   ├── MonitorAgent.scan() → SerpAPI + web scraping → opportunities
   ├── InternshipAgent.discover() → demo data (is_demo=True) if APIs fail
   └── ResearchAgent.conduct_research() → company intel
6. Results stored in memory (relational + vector)
7. Scores generated (accuracy, specificity, etc.)
8. Task status → completed, output synthesized
9. Frontend polls GET /agents/tasks/{id} → renders results
```

---

## 🔧 Agent Execution Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| **Retry** | 2 retries with exponential backoff |
| **Timeout** | 120s per agent execution |
| **Isolation** | Separate DB sessions per agent (no session sharing conflicts) |
| **Fallback** | LLM unavailable → template responses; search unavailable → demo data |
| **Persistence** | All agent tasks stored to PostgreSQL |
| **Observability** | LangSmith tracing when `LANGCHAIN_API_KEY` is set |

---

## 🧪 Testing

| Test File | Focus | Tests |
|-----------|-------|-------|
| test_planner.py | Goal decomposition, task priorities, response formatting | 13 |
| test_planner_e2e.py | End-to-end planner flow with mock agents | 8 |
| test_orchestrator.py | Orchestrator dispatch, task filtering, reflection scoring | 4 |
| test_agents.py | Agent task management API | 6 |
| test_hiring_agent.py | Resume extraction, ATS analysis, JD matching | 5 |
| test_resume.py | Resume upload, ATS analysis, vector search | 12 |
| test_memory.py | Memory CRUD, context retrieval | 4 |

---

## 📐 Design Principles

1. **Memory-first** — Every agent action reads and writes to the memory system
2. **Isolation over sharing** — Each agent gets its own DB session for thread safety
3. **Graceful degradation** — Every external dependency has a fallback path
4. **Cost-aware routing** — Simple tasks → cheap models, complex tasks → capable models
5. **Auditability** — Every agent execution is logged, scored, and stored
6. **Prompt isolation** — LLM templates live separately from handler logic for easy iteration
7. **Deterministic fallbacks** — Template responses when LLMs are unavailable, ensuring the UI never breaks

---

> *"Every agent has a memory. Every memory improves the next action."*

---
*AIML.md v1.0 · AgentForge AI/ML Team · July 2026*
