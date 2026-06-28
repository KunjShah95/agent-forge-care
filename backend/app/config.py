from pydantic_settings import BaseSettings
from pydantic import model_validator, field_validator
from typing import List, Optional
import os
import re
from pathlib import Path

# Resolve .env path relative to this config file so it works from any working directory
_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

# Manually inject .env values into os.environ BEFORE pydantic-settings initializes.
# This works around an issue where pydantic-settings' internal .env loading can
# interfere with certain env var values on Windows.
if _ENV_FILE.exists():
    with open(_ENV_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip().upper()
            # Only set if absent or empty — some imports preset env vars to ''
            # but real production env vars (Docker/CI) must never be overridden
            current = os.environ.get(key)
            if key and value and (current is None or current == ""):
                os.environ[key] = value.strip().strip("\"'")


class Settings(BaseSettings):
    # App
    app_name: str = "AgentForge Career OS"
    debug: bool = False
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> List[str]:
        origins = [o.strip() for o in self.cors_origins.split(",")]
        # Allow all Vercel preview deployments dynamically
        vercel_url = os.environ.get("VERCEL_URL")
        if vercel_url and vercel_url not in origins:
            origins.append(f"https://{vercel_url}")
        return origins

    # Database
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge"
    )

    # JWT
    jwt_secret: str = "change-me-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Firebase
    firebase_project_id: str = "developer-portfolio-aggregator"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # ── AI Model Providers ────────────────────────────────────

    # OpenAI (paid)
    openai_api_key: str = ""

    # Anthropic Claude (paid)
    anthropic_api_key: str = ""

    # Google Gemini (free tier: 60 req/min)
    google_api_key: str = ""

    # Groq (free tier available — fast open-source inference)
    groq_api_key: str = ""

    # Ollama (free, local — no API key needed)
    ollama_base_url: str = "http://localhost:11434"

    # OpenRouter (gateway to 200+ models, free tier available)
    openrouter_api_key: str = ""

    # Mistral AI (free tier available)
    mistral_api_key: str = ""

    # HuggingFace (optional, for embeddings via inference API)
    huggingface_api_key: str = ""

    # DeepSeek (very cheap, open-source reasoning models)
    deepseek_api_key: str = ""

    # Together AI (OpenAI-compatible, wide open-source model catalog)
    together_api_key: str = ""

    # Fireworks AI (OpenAI-compatible, fast open-source inference, $1 free credits)
    fireworks_api_key: str = ""

    # ── Embeddings / Rerank ────────────────────────────────────

    # Cohere (used for reranking)
    cohere_api_key: str = ""

    # ── Observability ──────────────────────────────────────────

    # LangSmith
    langchain_api_key: str = ""

    # ── Email ──────────────────────────────────────────────────

    # SendGrid
    sendgrid_api_key: str = ""
    from_email: str = "noreply@agentforge.ai"

    # ── Search APIs ────────────────────────────────────────────

    google_cse_id: str = ""
    serpapi_key: str = ""
    tavily_api_key: str = ""

    # Brave Search (2,000 free queries/month)
    brave_api_key: str = ""

    # Exa (formerly Metaphor) — AI-native search
    exa_api_key: str = ""

    # Mojeek — privacy-focused search (free tier, no API key required for scraping)
    mojeek_api_key: str = ""

    # SearXNG — self-hosted meta search engine URL
    searxng_base_url: str = ""

    # ── Match Scoring ──────────────────────────────────────────

    # Blend weight for profile-based skill match vs combined (profile + GitHub + portfolio)
    # 0.7 = 70% profile, 30% external. Lower = more weight on external skills.
    match_profile_weight: float = 0.7
    match_external_weight: float = 0.3

    # ── Security ───────────────────────────────────────────────

    # GitHub Token (for authenticated GitHub API calls — 5,000 req/hr vs 60 unauthenticated)
    github_token: str = ""

    secret_key: str = ""
    rate_limit_per_minute: int = 100

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        if not v or v.strip() == "":
            raise ValueError("jwt_secret cannot be empty")
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("database_url cannot be empty")
        if "://" not in v:
            raise ValueError("database_url must contain protocol (e.g., postgresql://)")
        return v

    @field_validator("openai_api_key", "anthropic_api_key", "google_api_key", "groq_api_key", "openrouter_api_key", "mistral_api_key", "huggingface_api_key", "deepseek_api_key", "together_api_key", "fireworks_api_key", "cohere_api_key", "langchain_api_key", "sendgrid_api_key", "serpapi_key", "tavily_api_key", "brave_api_key", "exa_api_key", "github_token")
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        if v and not re.match(r"^[a-zA-Z0-9_\-\.]{10,}$", v):
            raise ValueError(f"{info.field_name} appears to be an invalid API key format")
        return v

    @model_validator(mode="after")
    def validate_required_fields(self):
        if self.debug:
            return self
        if not self.secret_key or self.secret_key.strip() == "":
            raise ValueError("secret_key cannot be empty in non-debug mode")
        return self


settings = Settings()
