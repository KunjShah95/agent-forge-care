"""
Status endpoint — reports availability of all integrated services.

Provides a live snapshot of:
- AI model providers (LLM + embeddings)
- Search sources (web search APIs + scrapers)
- Database connections (PostgreSQL, Qdrant, Redis)
- Agent system health
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.config import settings
from app.database import get_db
from app.dependencies import rate_limiter
from app.memory.qdrant_client import get_qdrant_client

logger = logging.getLogger("agentforge.status")

router = APIRouter()


AI_MODEL_PROVIDERS = [
    {
        "name": "openai",
        "display": "OpenAI",
        "type": "paid",
        "models": ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "o3-mini", "o1-mini"],
        "env_var": "OPENAI_API_KEY",
    },
    {
        "name": "anthropic",
        "display": "Anthropic Claude",
        "type": "paid",
        "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "env_var": "ANTHROPIC_API_KEY",
    },
    {
        "name": "gemini",
        "display": "Google Gemini",
        "type": "free_tier",
        "models": ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"],
        "env_var": "GOOGLE_API_KEY",
    },
    {
        "name": "groq",
        "display": "Groq",
        "type": "free_tier",
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "env_var": "GROQ_API_KEY",
    },
    {
        "name": "mistral",
        "display": "Mistral AI",
        "type": "free_tier",
        "models": ["mistral-large-latest", "mistral-small-latest", "codestral-latest"],
        "env_var": "MISTRAL_API_KEY",
    },
    {
        "name": "openrouter",
        "display": "OpenRouter (200+ models)",
        "type": "free_tier",
        "models": ["openai/gpt-4o-mini", "anthropic/claude-3.5-haiku", "google/gemini-2.0-flash-001"],
        "env_var": "OPENROUTER_API_KEY",
    },
    {
        "name": "ollama",
        "display": "Ollama (Local)",
        "type": "free_local",
        "models": ["llama3.2", "llama3.1", "mistral", "qwen2.5", "deepseek-coder"],
        "env_var": None,
    },
    {
        "name": "deepseek",
        "display": "DeepSeek",
        "type": "paid",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "env_var": "DEEPSEEK_API_KEY",
    },
    {
        "name": "together",
        "display": "Together AI",
        "type": "paid",
        "models": [
            "meta-llama/Meta-Llama-3.1-8B-Instruct",
            "deepseek-ai/DeepSeek-V3",
            "Qwen/Qwen2.5-72B-Instruct-Turbo",
        ],
        "env_var": "TOGETHER_API_KEY",
    },
    {
        "name": "fireworks",
        "display": "Fireworks AI",
        "type": "free_tier",
        "models": ["accounts/fireworks/models/deepseek-v3p1", "accounts/fireworks/models/llama-v3p3-70b-instruct"],
        "env_var": "FIREWORKS_API_KEY",
        "free_tier": "$1 free starter credits",
    },
]

EMBEDDING_PROVIDERS = [
    {
        "name": "openai",
        "display": "OpenAI",
        "type": "paid",
        "models": ["text-embedding-3-small", "text-embedding-3-large"],
        "env_var": "OPENAI_API_KEY",
    },
    {
        "name": "gemini",
        "display": "Google Gemini",
        "type": "free_tier",
        "models": ["text-embedding-004"],
        "env_var": "GOOGLE_API_KEY",
    },
    {
        "name": "huggingface",
        "display": "HuggingFace (Local)",
        "type": "free_local",
        "models": ["sentence-transformers/all-mpnet-base-v2", "BAAI/bge-small-en-v1.5"],
        "env_var": None,
    },
    {
        "name": "ollama",
        "display": "Ollama (Local)",
        "type": "free_local",
        "models": ["nomic-embed-text", "mxbai-embed-large"],
        "env_var": None,
    },
]

SEARCH_SOURCES = [
    {
        "name": "tavily",
        "display": "Tavily (AI-native)",
        "type": "api",
        "env_var": "TAVILY_API_KEY",
    },
    {
        "name": "google_cse",
        "display": "Google Custom Search",
        "type": "api",
        "requires": ["GOOGLE_API_KEY", "GOOGLE_CSE_ID"],
    },
    {
        "name": "brave",
        "display": "Brave Search",
        "type": "api",
        "env_var": "BRAVE_API_KEY",
        "free_tier": "2,000 queries/month",
    },
    {
        "name": "exa",
        "display": "Exa (AI-native)",
        "type": "api",
        "env_var": "EXA_API_KEY",
    },
    {
        "name": "searxng",
        "display": "SearXNG (Self-hosted)",
        "type": "self_hosted",
        "env_var": "SEARXNG_BASE_URL",
    },
    {
        "name": "mojeek",
        "display": "Mojeek (Privacy-first)",
        "type": "api",
        "env_var": "MOJEEK_API_KEY",
        "free_tier": True,
    },
    {
        "name": "mojeek_scrape",
        "display": "Mojeek Scraping (no API key)",
        "type": "builtin",
        "requires": [],
    },
    {
        "name": "serpapi",
        "display": "SerpAPI (Google Jobs)",
        "type": "api",
        "env_var": "SERPAPI_KEY",
    },
    {
        "name": "web_scrape",
        "display": "Web Scraping (Google HTML)",
        "type": "builtin",
        "requires": [],
    },
    {
        "name": "duckduckgo_scrape",
        "display": "DuckDuckGo Scraping",
        "type": "builtin",
        "requires": [],
    },
    {
        "name": "job_board_scrape",
        "display": "Job Board Scraping (Indeed, LinkedIn, Glassdoor)",
        "type": "builtin",
        "requires": [],
    },
    {
        "name": "linkedin_direct",
        "display": "LinkedIn Direct Scraping",
        "type": "builtin",
        "requires": [],
    },
]

OTHER_SERVICES = [
    {
        "name": "cohere",
        "display": "Cohere (Reranking)",
        "type": "api",
        "env_var": "COHERE_API_KEY",
    },
    {
        "name": "sendgrid",
        "display": "SendGrid (Email)",
        "type": "api",
        "env_var": "SENDGRID_API_KEY",
    },
    {
        "name": "langsmith",
        "display": "LangSmith (Observability)",
        "type": "api",
        "env_var": "LANGCHAIN_API_KEY",
    },
    {
        "name": "github",
        "display": "GitHub API",
        "type": "api",
        "env_var": "GITHUB_TOKEN",
        "free_tier": "5,000 req/hr with token, 60 req/hr without",
    },
    {
        "name": "match_profile_weight",
        "display": "Match Profile Weight",
        "type": "config",
        "env_var": "MATCH_PROFILE_WEIGHT",
        "default": 0.7,
        "description": "Weight given to profile-declared skills in match scoring blend",
    },
    {
        "name": "match_external_weight",
        "display": "Match External Weight",
        "type": "config",
        "env_var": "MATCH_EXTERNAL_WEIGHT",
        "default": 0.3,
        "description": "Weight given to GitHub/portfolio-detected skills in match scoring blend",
    },
]


def _check_env(env_var: str) -> bool:
    """Check if an environment variable is set and non-empty."""
    val = getattr(settings, env_var.lower(), None)
    return bool(val and str(val).strip())


def _check_envs(env_vars: list[str]) -> bool:
    """Check if all required environment variables are set."""
    return all(_check_env(ev) for ev in env_vars)


@router.get("/status")
async def system_status():
    """Report live availability of all integrated services and providers."""
    timestamp = datetime.now(UTC).isoformat()

    # ── AI Model Providers ─────────────────────────────────
    llm_providers = []
    for p in AI_MODEL_PROVIDERS:
        if p["env_var"]:
            available = _check_env(p["env_var"])
        else:
            # Ollama is always listed as available if running locally
            available = True  # Will be confirmed at runtime
        llm_providers.append(
            {
                "name": p["name"],
                "display": p["display"],
                "type": p["type"],
                "available": available,
                "models": p["models"],
            }
        )

    embedding_providers = []
    for p in EMBEDDING_PROVIDERS:
        if p["env_var"]:
            available = _check_env(p["env_var"])
        else:
            available = True
        embedding_providers.append(
            {
                "name": p["name"],
                "display": p["display"],
                "type": p["type"],
                "available": available,
                "models": p["models"],
            }
        )

    # ── Search Sources ──────────────────────────────────────
    search_sources = []
    for s in SEARCH_SOURCES:
        if s["type"] == "builtin":
            available = True
        elif "requires" in s:
            available = _check_envs(s["requires"])
        elif s.get("env_var"):
            available = _check_env(s["env_var"])
        else:
            available = False

        entry = {
            "name": s["name"],
            "display": s["display"],
            "type": s["type"],
            "available": available,
        }
        if s.get("free_tier"):
            entry["free_tier"] = s["free_tier"]
        search_sources.append(entry)

    # ── Other Services ─────────────────────────────────────
    other_services = []
    for s in OTHER_SERVICES:
        if s.get("env_var"):
            available = _check_env(s["env_var"])
        else:
            available = False
        other_services.append(
            {
                "name": s["name"],
                "display": s["display"],
                "type": s["type"],
                "available": available,
            }
        )

    # ── Database Connections ────────────────────────────────
    databases = {}

    # PostgreSQL
    try:
        async for session in get_db():
            await session.execute(text("SELECT 1"))
            break
        databases["postgresql"] = {"status": "connected"}
    except Exception as e:
        databases["postgresql"] = {"status": "error", "error": str(e)[:100]}

    # Qdrant
    try:
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections()
        collection_names = [c.name for c in collections.collections]
        qdrant.close()
        databases["qdrant"] = {"status": "connected", "collections": collection_names}
    except Exception as e:
        databases["qdrant"] = {"status": "unavailable", "error": str(e)[:100]}

    # Redis
    try:
        limiter = await rate_limiter()
        r = await limiter._get_redis()
        await r.ping()
        databases["redis"] = {"status": "connected"}
    except Exception as e:
        databases["redis"] = {"status": "unavailable", "error": str(e)[:100]}

    # ── Agent System ───────────────────────────────────────
    try:
        from app.agents.graph import get_planner_graph

        graph = get_planner_graph()
        agent_system = {
            "status": "ready" if graph is not None else "unhealthy",
            "agent_count": 8,
            "agents": [
                "planner",
                "internship",
                "job",
                "research",
                "resume",
                "interview",
                "networking",
                "monitor",
            ],
            "graph_compiled": graph is not None,
        }
    except Exception as e:
        agent_system = {
            "status": "error",
            "error": str(e)[:200],
        }

    # ── Overall Health ─────────────────────────────────────
    llm_available = any(p["available"] for p in llm_providers)
    any(p["available"] for p in embedding_providers)
    search_available = any(s["available"] for s in search_sources)
    db_ok = databases.get("postgresql", {}).get("status") == "connected"

    if llm_available and db_ok:
        overall = "healthy"
    elif db_ok:
        overall = "degraded"  # No LLM but DB works
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "service": settings.app_name,
        "version": "1.0.0",
        "timestamp": timestamp,
        "environment": "debug" if settings.debug else "production",
        "components": {
            "ai_models": {
                "status": "available" if llm_available else "unavailable",
                "llm_providers": {
                    "count": len(llm_providers),
                    "available": sum(1 for p in llm_providers if p["available"]),
                    "providers": llm_providers,
                },
                "embedding_providers": {
                    "count": len(embedding_providers),
                    "available": sum(1 for p in embedding_providers if p["available"]),
                    "providers": embedding_providers,
                },
            },
            "search": {
                "status": "available" if search_available else "unavailable",
                "count": len(search_sources),
                "available": sum(1 for s in search_sources if s["available"]),
                "sources": search_sources,
            },
            "databases": databases,
            "agent_system": agent_system,
            "other_services": {
                "count": len(other_services),
                "available": sum(1 for s in other_services if s["available"]),
                "services": other_services,
            },
        },
        "summary": {
            "llm_providers_available": sum(1 for p in llm_providers if p["available"]),
            "embedding_providers_available": sum(1 for p in embedding_providers if p["available"]),
            "search_sources_available": sum(1 for s in search_sources if s["available"]),
            "databases_connected": sum(1 for d in databases.values() if d.get("status") == "connected"),
        },
    }
