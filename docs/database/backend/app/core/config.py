"""
Application configuration.

Loaded from environment variables (see config/.env.example at the repo
root). No secrets are hardcoded. If a required value for a feature is
missing, that feature must report NOT_CONFIGURED rather than silently
degrading to fake behavior (see app.agents.llm.client).
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "Multi-Agent Project Platform"
    ENV: str = "development"
    DEBUG: bool = True

    # --- Database ---
    DATABASE_URL: str = (
        "postgresql+psycopg://postgres:postgres@localhost:5432/multiagent_dev"
    )

    # --- Auth ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24

    # --- LLM ---
    # provider: "anthropic" | "openai_compatible" | "ollama" | "" (unconfigured)
    LLM_PROVIDER: str = ""
    LLM_MODEL: str = ""
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""

    # --- Sandbox execution ---
    SANDBOX_MODE: str = "subprocess"  # "docker" | "subprocess" | "disabled"
    MAX_REPAIR_ATTEMPTS: int = 3


@lru_cache
def get_settings() -> Settings:
    return Settings()
