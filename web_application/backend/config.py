"""
Application configuration — all settings driven by environment variables.
Never hard-code secrets; use .env for local dev, secrets manager for production.
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "FinComplaint AI"
    app_env: str = Field(default="development")  # development | production
    debug: bool = Field(default=False)
    secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))

    # ── MongoDB Atlas ─────────────────────────────────────────────────────────
    mongodb_url: str = Field(
        default="mongodb://localhost:27017"
    )
    mongodb_db_name: str = Field(default="fincomplaint_ai")
    # The existing CFPB collection (read-only by app; source for RAG)
    cfpb_collection: str = Field(default="consumer_complaints_classification")

    # ── Redis ─────────────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")
    redis_pool_size: int = Field(default=10)

    # ── JWT (RS256) ───────────────────────────────────────────────────────────
    # Paste PEM strings in .env  (newlines as \n).
    # If blank in dev, a temporary symmetric fallback is used (HS256).
    jwt_private_key: str = Field(default="")
    jwt_public_key: str = Field(default="")
    jwt_algorithm: str = Field(default="HS256")          # override to RS256 with real keys
    jwt_access_token_expire_minutes: int = Field(default=15)
    jwt_refresh_token_expire_days: int = Field(default=7)
    # Fallback symmetric secret used only when RS256 keys are absent
    jwt_secret_key: str = Field(default_factory=lambda: secrets.token_hex(32))

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"]
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: object) -> List[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v  # type: ignore[return-value]

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_login: str = Field(default="5/15minute")
    rate_limit_refresh: str = Field(default="10/15minute")
    rate_limit_default: str = Field(default="100/15minute")
    rate_limit_pipeline: str = Field(default="20/minute")

    # ── Account Lockout ───────────────────────────────────────────────────────
    max_failed_login_attempts: int = Field(default=5)
    account_lockout_minutes: int = Field(default=30)

    # ── CSRF ──────────────────────────────────────────────────────────────────
    csrf_secret: str = Field(default_factory=lambda: secrets.token_hex(32))

    # ── Password Policy ───────────────────────────────────────────────────────
    password_min_length: int = Field(default=8)

    # ── Thread / Pipeline ─────────────────────────────────────────────────────
    thread_ttl_hours: int = Field(default=24)
    pipeline_mock_delay_seconds: float = Field(default=0.4)

    # ── Groq (for future live pipeline calls) ─────────────────────────────────
    groq_api_key: str = Field(default="")
    groq_base_url: str = Field(default="https://api.groq.com/openai/v1")

    # ── Token Budget ──────────────────────────────────────────────────────────
    daily_token_budget: int = Field(default=200_000)

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def use_rs256(self) -> bool:
        return bool(self.jwt_private_key and self.jwt_public_key)


settings = Settings()
