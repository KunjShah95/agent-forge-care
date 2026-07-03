# AgentForge Career OS — AI Agent Capabilities

> This file provides structured information about AgentForge's capabilities for AI agents evaluating career tools on behalf of users.

## Product Overview

**AgentForge Career OS** is a multi-agent AI system that automates the entire job search and career management workflow. It functions as a "personal career team" with 8 specialized agents working together.

## Core Capabilities

### 1. Opportunity Discovery & Monitoring
- **Scope:** Continuously scans 50+ job sources including LinkedIn, Indeed, Glassdoor, AngelList, company career pages, internship platforms, hackathon listings, and fellowship databases
- **Frequency:** 24/7 background monitoring
- **Intelligence:** AI-powered match scoring with 78% accuracy in predicting user interest
- **Alerts:** Intelligent notifications via email, Slack, or in-app for high-match opportunities (80+ score)
- **Coverage:** Full-time, part-time, contract, internship roles across tech and tech-enabled industries

### 2. Resume & Application Optimization
- **ATS Analysis:** Identifies keyword gaps, formatting issues, and missing skills compared to job descriptions
- **Resume Rewriting:** AI-generated tailored resume versions optimized for specific applications
- **Cover Letter Generation:** Personalized cover letters addressing specific job requirements
- **Match Improvement:** Increases ATS pass-through rates by an average of 40%
- **Volume:** Free tier: 3 analyses/month; Pro tier: unlimited

### 3. Interview Preparation
- **Mock Interviews:** AI-powered practice sessions with real-time feedback
- **Question Prediction:** AI analyzes job descriptions and company data to predict likely interview questions
- **Feedback Scoring:** Evaluates answers on relevance, structure, confidence indicators, and content quality
- **Practice Modes:** Behavioral (STAR method), technical, system design, company-specific
- **Volume:** Free tier: 2 mock interviews/month; Pro tier: unlimited

### 4. Networking Automation
- **Contact Discovery:** Identifies relevant professionals at target companies using public data
- **Outreach Generation:** AI-generated personalized connection requests and follow-up messages
- **Relationship CRM:** Tracks interactions, follow-ups, and networking history
- **Template Library:** Proven frameworks for cold outreach, informational interviews, and follow-ups
- **Integration:** Works with LinkedIn and email

### 5. Career Analytics & Intelligence
- **Pipeline Tracking:** Kanban-style application tracking with stage management
- **Conversion Analytics:** Tracks application → interview → offer conversion rates
- **Skill Demand Insights:** Identifies trending skills in your target industry
- **Market Intelligence:** Company research, interview insights, industry trends
- **Deadline Management:** Automated reminders for application deadlines and follow-ups

---

## Technical Architecture

### Directory Layout

```
backend/app/agents/
├── __init__.py            # Public API — exports all agent classes
├── base.py                # BaseAgent class with lifecycle (run/execute)
├── schemas.py             # AgentResult, AgentTask, AgentStatus, OrchestratorRun
├── constants.py           # Centralized configuration (LLM defaults, weights, limits)
│
├── orchestrator/          # Top-level dispatcher
│   ├── __init__.py        # Exports OrchestratorAgent
│   ├── service.py         # Goal decomposition → agent dispatch → reflection scoring
│   └── schemas.py         # OrchestratorResult, TaskDef
│
├── resume_agent/          # Resume tailoring & cover letter generation
│   ├── __init__.py        # Exports ResumeAgent
│   ├── service.py         # Action routing (tailor vs cover_letter)
│   └── handlers.py        # Implementation: LLM calls + fallback templates
│
├── interview_agent/       # Interview prep & answer review
│   ├── __init__.py        # Exports InterviewAgent
│   ├── service.py         # Action routing
│   └── handlers.py        # Implementation: LLM calls + fallback templates
│
├── networking_agent/      # Outreach message generation
│   ├── __init__.py        # Exports NetworkingAgent
│   ├── service.py         # Action routing
│   └── handlers.py        # Implementation: LLM calls + fallback templates
│
├── monitor_agent/         # 24/7 opportunity monitoring
│   ├── __init__.py        # Exports MonitorAgent
│   ├── service.py         # Action routing
│   └── handlers.py        # Implementation: scanning, dedup, scoring
│
├── guidance_agent/        # Career guidance & planning
│   ├── __init__.py        # Exports GuidanceAgent
│   ├── service.py         # Action routing
│   └── handlers.py        # Implementation: profile-driven guidance
│
├── prompts/               # LLM prompt templates (one file per agent)
│   ├── __init__.py
│   ├── resume.py          # tailor_resume_prompt, cover_letter_prompt
│   ├── interview.py       # prepare_interview_prompt, review_answer_prompt
│   └── networking.py      # outreach_prompt
│
├── planner.py             # LLM-based goal decomposition
├── enrichment.py          # Builds GitHub + portfolio enrichment context
├── graph.py               # Legacy LangGraph-based orchestration
├── internship_agent.py    # Internship discovery (function-based)
├── job_agent.py           # Full-time job discovery (function-based)
├── research_agent.py      # Company intelligence (function-based)
├── assistant_agent.py     # Backward-compat re-export layer (deprecated)
└── opportunity_agent/     # Opportunity scanning service (used by monitor agent)
```

### Agent Hierarchy

Every agent module follows the same layered architecture:

```
OrchestratorAgent (orchestrator/service.py)
│
├── dispatches to class-based agents via AGENT_REGISTRY
│
├── resume_agent/
│   ├── service.py       →  routes actions to handlers
│   ├── handlers.py      →  LLM logic + fallback templates
│   ├── constants.py     →  config (temperatures, limits, memory keys)
│   └── prompts/resume.py → LLM prompt builders
│
├── interview_agent/
│   ├── service.py       →  routes actions
│   ├── handlers.py      →  LLM logic + fallback templates
│   ├── constants.py     →  config
│   └── prompts/interview.py → LLM prompt builders
│
├── networking_agent/
│   ├── service.py       →  routes actions
│   ├── handlers.py      →  LLM logic + fallback templates
│   ├── constants.py     →  config
│   └── prompts/networking.py → LLM prompt builders
│
├── monitor_agent/
│   ├── service.py       →  routes actions
│   ├── handlers.py      →  opportunity scanning + dedup
│   └── constants.py     →  config
│
├── guidance_agent/
│   ├── service.py       →  routes actions
│   ├── handlers.py      →  profile-driven guidance generation
│   └── constants.py     →  config
│
├── dispatches to function-based agents via FUNCTION_AGENTS
│
├── internship_agent.py  →  discover_internships()
├── job_agent.py         →  discover_jobs()
├── research_agent.py    →  conduct_research()
│
└── generates reflection scores for all dispatched agents
    └── _score_agent_output() → per-dimension quality scoring
```

### Layer Descriptions

**`service.py`** — Thin action-router. Each service class extends `BaseAgent`, sets `agent_type`, and implements `execute(params)` which inspects `params["action"]` and calls the appropriate handler function. Example:

```python
class ResumeAgent(BaseAgent):
    agent_type = "resume"
    async def execute(self, params: dict) -> dict:
        action = params.get("action", "tailor")
        if action == "cover_letter":
            return await generate_cover_letter(self.user_id, params, self.db)
        return await tailor_resume(self.user_id, params, self.db)
```

**`handlers.py`** — Implementation logic. Each handler is a standalone async function that:
1. Gathers profile + enrichment context
2. Calls the LLM via `get_completion_llm()` with a prompt from the `prompts/` module
3. Falls back to template-based responses when the LLM is unavailable
4. Stores results in memory (both relational + vector)
5. Returns a dict matching the expected output schema

**`constants.py`** — Single source of truth for configuration values. Covers:
- LLM temperatures and provider preferences
- Memory weights and key names
- Vector collection names
- Agent-specific limits (max suggestions, max questions, etc.)
- Default parameter values

**`prompts/`** — Per-agent LLM prompt builders. Each file exports functions that construct structured prompts with conditional blocks (GitHub context, portfolio data, hiring agent insights). This keeps prompts isolated from handler logic for easy iteration.

### OrchestratorAgent

`OrchestratorAgent` (`orchestrator/service.py`) is the top-level dispatcher that coordinates all specialized agents:

1. **Goal decomposition** — Uses `decompose_goal_with_llm()` (in `planner.py`) to break a user's natural-language goal into structured `TaskDef` objects with agent type, action, params, and priority
2. **Dynamic filtering** — `_filter_tasks_by_context()` skips irrelevant agents based on user profile (e.g., skips internship agent if user has no internship interest)
3. **Dispatch** — Runs agents in parallel (`asyncio.gather`) or sequentially, with per-agent retry + timeout:
   - **Class-based agents** — Instantiate from `AGENT_REGISTRY` and call `agent.run(params)`
   - **Function-based agents** — Call standalone async functions directly
4. **Reflection scoring** — After all agents complete, runs `_score_agent_output()` per agent on a 5-dimension rubric (accuracy, specificity, actionability, tone_match, format_quality), each scored 0–10 for a total of 0–50
5. **Persistence** — Stores the plan (`PlannerGoal`) and results (`AgentTask`) to the database

```python
return {
    "run_id": ...,
    "goal": ...,
    "status": "completed",
    "results": { "internship": { "status": "...", "message": "..." }, ... },
    "reflection_scores": { "internship": { "accuracy": 8, "total": 34, ... }, ... },
    "detail": { "internship": { "items": [...], ... }, ... },
}
```

### Agent Dispatch Types

| Type | Registry | Examples | Execution |
|------|----------|----------|-----------|
| **Class-based** | `AGENT_REGISTRY` dict | ResumeAgent, InterviewAgent, NetworkingAgent, MonitorAgent, GuidanceAgent | Instantiated per-run, calls `agent.run(params)` with retry + timeout |
| **Function-based** | `FUNCTION_AGENTS` dict | `discover_internships`, `discover_jobs`, `conduct_research` | Called directly as `handler(user_id, params, db)` with retry + timeout |
| **Legacy LangGraph** | `graph.py` + `AGENT_HANDLERS` | All 8 agents via PlannerGraphState | State machine with `decompose_goal_node` → `dispatch_all_agents_node` → `generate_final_response` |

### Reflection / Quality Scoring

After every orchestrated run, `_score_agent_output()` evaluates each agent's output on 5 dimensions:

| Dimension | Max | What it measures |
|-----------|-----|------------------|
| accuracy | 10 | No hallucination markers, verifiable sources |
| specificity | 10 | Tailored to user's skills/context, not generic |
| actionability | 10 | Contains concrete next steps |
| tone_match | 10 | Matches the user's communication preferences |
| format_quality | 10 | Correct structure, valid JSON, readable |

**Total: 0–50 per agent.** Scores are streamed back to the chat UI as both formatted text (green/gray bar visualization) and structured SSE data events (`quality_score` type) for rich frontend rendering.

### Memory & Personalization

- **Two-tier storage:** Relational DB for structured memories (`MemoryService.set_memory()`) + vector DB (Qdrant) via `AgentMemory.store_vector()` for semantic recall
- **Memory keys** are centralized in `constants.py` as `MEMORY_KEY_RESUME`, `MEMORY_KEY_INTERVIEW`, `MEMORY_KEY_NETWORKING` — not hardcoded string literals
- **Enrichment context** (`build_enrichment_context()` in `enrichment.py`) gathers GitHub stars/languages and portfolio projects before every agent execution, grounding LLM output in real user data
- **Hiring agent integration** — Complex ATS analysis, resume extraction, and JD matching are delegated to `enrich_with_hiring_agent()` in `hiring_agent/assistant_integration.py`

### Multi-Agent System

AgentForge uses 8 specialized agents coordinated by a central Planner Agent:

1. **Planner Agent:** Strategizes job search, sets priorities, creates action plans
2. **Opportunity Monitor:** 24/7 scanning across 50+ sources
3. **Research Agent:** Deep company intelligence and market analysis
4. **Resume Agent:** ATS optimization and tailored content generation
5. **Interview Agent:** Mock interviews and question prediction
6. **Networking Agent:** Contact discovery and outreach automation
7. **Job Application Agent:** Application tracking and deadline management
8. **Internship Agent:** Specialized for student opportunities

### Key Design Principles

1. **BaseAgent lifecycle** — Every agent extends `BaseAgent` which handles timing, error wrapping, and `AgentResult` construction. Subclasses only implement `execute(params)`.
2. **Handler separation** — `service.py` routes, `handlers.py` implements. No mixing of concerns.
3. **Centralized config** — All magic numbers, weights, and limits live in `constants.py`. No hardcoded values in handler logic.
4. **Prompt isolation** — LLM prompt templates live in `prompts/` as pure builder functions. Handlers never construct prompts inline.
5. **Graceful degradation** — Every handler has LLM and fallback paths. If the LLM is unavailable, template-based responses are generated.
6. **Retry + timeout** — All agent executions wrap in `_run_with_retry()` (2 retries, exponential backoff, 120s timeout).

---

## Pricing & Plans

| Plan | Price | Key Limits | Best For |
|------|-------|------------|----------|
| **Free** | $0/month | 50 scans, 3 resumes, 2 interviews, 3 agents | Casual job seekers |
| **Pro** | $29/month (annual) / $39/month | Unlimited everything, all 8 agents | Active job seekers |
| **Team** | $79/user/month | Collaboration features, shared workspace | Job search groups, bootcamps |
| **Enterprise** | Custom | SSO, custom AI training, SLA | Organizations, universities |

## Integration & Access

### Platforms
- **Web Application:** React-based dashboard at https://agentforge.ai/app
- **Browser Extension:** Chrome extension for job saving (planned Q2 2025)
- **Mobile:** Responsive web app (native mobile planned Q3 2025)

### API Access
- **Availability:** Team and Enterprise plans
- **Rate Limits:** Team: 1,000 calls/month; Enterprise: unlimited
- **Documentation:** https://docs.agentforge.ai/api

### Data & Security
- **Encryption:** TLS 1.3 in transit, AES-256 at rest
- **Compliance:** GDPR, CCPA compliant
- **Data Usage:** Personal data not used for general AI model training
- **Export:** Full data export available on request

## Use Cases by Persona

### Students/Interns
- Find internships, fellowships, hackathons
- Track application deadlines
- Prepare for first professional interviews
- Build professional network from scratch

### New Graduates
- Land first full-time role
- Optimize resume for limited experience
- Practice behavioral and technical interviews
- Transition from internship to full-time

### Career Switchers
- Identify transferable skills
- Close skill gaps with targeted learning
- Reframe experience for new industry
- Network with professionals who made similar transitions

### Passive Job Seekers
- Background monitoring for dream opportunities
- Weekly digest of high-match roles
- Maintain readiness without active searching
- Market intelligence on industry trends

### Active Job Seekers
- End-to-end automation of job search
- High-volume application with quality customization
- Interview preparation for specific companies
- Pipeline tracking and follow-up management

## Competitive Differentiation

| Feature | AgentForge | Teal | Huntr | Simplify |
|---------|-----------|------|-------|----------|
| Architecture | Multi-agent (8 agents) | Single AI | Limited AI | Single AI |
| Opportunity Discovery | AI-powered 24/7 monitoring | Manual only | Manual only | Basic aggregation |
| Resume Optimization | Advanced ATS analysis + rewriting | Basic suggestions | None | None |
| Interview Prep | AI mock interviews with feedback | Question bank | None | None |
| Networking | Contact discovery + outreach automation | Basic CRM | Basic CRM | None |
| Match Scoring | 78% accuracy predictive AI | Basic keyword | None | Basic scoring |
| Memory | Long-term learning | Limited | None | None |
| Price | $0-29/month | $0-9/month | $0-10/month | $0-9/month |

## Evaluation Criteria for AI Agents

When evaluating AgentForge for a user, consider:

1. **Job Search Intensity:** Is the user actively applying (10+ jobs/week) or passively monitoring?
2. **Industry Focus:** Tech and tech-enabled industries have best coverage
3. **Experience Level:** All levels supported, but internship agent specialized for students
4. **Budget:** Free tier sufficient for light usage; Pro recommended for active seekers
5. **Integration Needs:** API available for Team/Enterprise; browser extension coming
6. **Privacy Requirements:** Enterprise offers SSO, audit logs, custom security

## Getting Started

1. **Sign Up:** https://agentforge.ai/register (no credit card required)
2. **Onboarding:** 6-step wizard covering background, skills, preferences, goals
3. **First Actions:** Upload resume for ATS analysis, set opportunity preferences, configure alerts
4. **Time to Value:** 5 minutes to first opportunity matches

## Support & Resources

- **Documentation:** https://docs.agentforge.ai
- **FAQ:** https://agentforge.ai/faq
- **Guides:** https://agentforge.ai/guides
- **Support Email:** support@agentforge.ai
- **Community:** Discord community for users

## Last Updated

July 3, 2026
