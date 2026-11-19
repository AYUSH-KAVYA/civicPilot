"""
Application configuration using pydantic-settings.
Source of truth: docs/CONTRACT.md Section 8.
"""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # LLM & AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-pro"
    GEMINI_EMBED_MODEL: str = "text-embedding-004"
    MOCK_LLM: bool = False
    CONFIDENCE_THRESHOLD: float = 0.65

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/civicpilot"

    # Supabase & Storage
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    UPLOAD_DIR: str = "uploads"

    # Authentication
    JWT_SECRET: str = "dev-secret-key-civicpilot-minimum-32-chars-needed"
    OFFICER_PASSWORD: str = "adminpassword"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    CITIZEN_TOKEN_EXPIRATION_DAYS: int = 30

    # Simulation Clock & Demo
    SIM_TIME_SCALE: float = 1.0

    # Geocoding & External Services
    NOMINATIM_USER_AGENT: str = "CivicPilot/1.0 (contact: civicpilot@example.com)"
    RESEND_API_KEY: Optional[str] = None

    # Frontend & CORS
    FRONTEND_ORIGIN: str = "http://localhost:3000"
    NEXT_PUBLIC_API_URL: str = "http://localhost:8000"
    NEXT_PUBLIC_USE_MOCKS: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
