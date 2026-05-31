from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import List
import os


class Settings(BaseSettings):
    # App
    app_name: str = "AgentForge Career OS"
    debug: bool = False
    port: int = 8000
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

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
    firebase_project_id: str = "agentforge-career-os"

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

    @model_validator(mode="after")
    def validate_jwt_secret(self):
        if not self.debug and self.jwt_secret == "change-me-to-a-random-secret-key":
            raise ValueError(
                "jwt_secret must be changed from the default value when debug is False"
            )
        return self


settings = Settings()
