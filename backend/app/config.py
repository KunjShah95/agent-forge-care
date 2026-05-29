from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    app_name: str = "AgentForge Career OS"
    debug: bool = True
    port: int = 8000
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/agentforge"

    # JWT
    jwt_secret: str = "change-me-to-a-random-secret-key"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # OpenAI
    openai_api_key: str = ""

    # Cohere
    cohere_api_key: str = ""

    # LangSmith
    langchain_api_key: str = ""

    # Search APIs
    google_api_key: str = ""
    google_cse_id: str = ""
    serpapi_key: str = ""

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
