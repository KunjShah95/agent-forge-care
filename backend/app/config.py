import os
import re
import secrets
from pathlib import Path

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

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


# Known default secrets that must never be used in production
_KNOWN_INSECURE_SECRETS = {
    "change-me-to-a-random-secret-key",
    "dev-secret-change-in-production",
    "secret",
    "password",
    "changeme",
    "default",
}


class Settings(BaseSettings):
    # App
    app_name: str = "AgentForge Career OS"
    debug: bool = False
    port: int = 8000
    cors_origins: str = "http://localhost:5173,http://localhost:8080"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",")]
        # Allow all Vercel preview deployments dynamically
        vercel_url = os.environ.get("VERCEL_URL")
        if vercel_url and vercel_url not in origins:
            origins.append(f"https://{vercel_url}")
        return origins

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge"

    # JWT — auto-generated cryptographically random key if not set
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Firebase — must be configured per environment
    firebase_project_id: str = ""

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # ── AI Model Providers ────────────────────────────────────
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"
    openrouter_api_key: str = ""
    mistral_api_key: str = ""
    huggingface_api_key: str = ""
    deepseek_api_key: str = ""
    together_api_key: str = ""
    fireworks_api_key: str = ""

    # ── Embeddings / Rerank ────────────────────────────────────
    cohere_api_key: str = ""

    # ── Observability ──────────────────────────────────────────
    langchain_api_key: str = ""

    # ── Email ──────────────────────────────────────────────────
    sendgrid_api_key: str = ""
    from_email: str = "noreply@agentforge.ai"

    # ── Search APIs ────────────────────────────────────────────
    google_cse_id: str = ""
    serpapi_key: str = ""
    tavily_api_key: str = ""
    brave_api_key: str = ""
    exa_api_key: str = ""
    mojeek_api_key: str = ""
    searxng_base_url: str = ""

    # ── Match Scoring ──────────────────────────────────────────
    match_profile_weight: float = 0.7
    match_external_weight: float = 0.3

    # ── Security ───────────────────────────────────────────────
    github_token: str = ""
    secret_key: str = ""
    rate_limit_per_minute: int = 100
    # Stricter rate limit for auth endpoints (login/register) to prevent brute force
    auth_rate_limit_per_minute: int = 5

    model_config = {
        "env_file": str(_ENV_FILE),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if not v or v.strip() == "":
            # Auto-generate a cryptographically secure key
            generated = secrets.token_urlsafe(48)
            return generated
        # Warn if an insecure default is still being used
        if v.strip().lower() in _KNOWN_INSECURE_SECRETS:
            import warnings

            warnings.warn(
                f"jwt_secret is set to a known insecure value ('{v[:20]}...'). "
                "This is dangerous in production. Generate a strong random key."
            )
        return v

    @field_validator("firebase_project_id")
    @classmethod
    def validate_firebase_project_id(cls, v: str) -> str:
        if not v or v.strip() == "":
            import warnings

            warnings.warn(
                "firebase_project_id is not set. Firebase authentication will fail. "
                "Set FIREBASE_PROJECT_ID environment variable."
            )
        return v

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v or v.strip() == "":
            # Auto-generate if empty
            return secrets.token_urlsafe(32)
        return v

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("database_url cannot be empty")
        if "://" not in v:
            raise ValueError("database_url must contain protocol (e.g., postgresql://)")
        return v

    @field_validator(
        "openai_api_key",
        "anthropic_api_key",
        "google_api_key",
        "groq_api_key",
        "openrouter_api_key",
        "mistral_api_key",
        "huggingface_api_key",
        "deepseek_api_key",
        "together_api_key",
        "fireworks_api_key",
        "cohere_api_key",
        "langchain_api_key",
        "sendgrid_api_key",
        "serpapi_key",
        "tavily_api_key",
        "brave_api_key",
        "exa_api_key",
        "github_token",
    )
    @classmethod
    def validate_api_keys(cls, v: str, info) -> str:
        if v and not re.match(r"^[a-zA-Z0-9_\-\.]{10,}$", v):
            raise ValueError(f"{info.field_name} appears to be an invalid API key format")
        return v

    @model_validator(mode="after")
    def validate_required_fields(self):
        if self.debug:
            return self
        if not self.firebase_project_id:
            raise ValueError("firebase_project_id is required in non-debug mode. Set FIREBASE_PROJECT_ID env var.")
        if not self.secret_key or self.secret_key.strip() == "":
            raise ValueError("secret_key cannot be empty in non-debug mode")
        # Log info about auto-generated keys in non-debug mode
        return self


settings = Settings()
