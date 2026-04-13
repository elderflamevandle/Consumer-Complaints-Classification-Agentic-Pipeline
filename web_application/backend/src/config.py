"""Environment-aware settings loader for early-phase bootstrap."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from os import getenv
from pathlib import Path


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv
    except Exception:
        return
    load_dotenv()


def _as_int(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_float(name: str, default: float) -> float:
    value = getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    groq_api_key: str | None
    groq_base_url: str
    request_timeout_seconds: float
    max_retries: int
    backoff_base_seconds: float
    backoff_max_seconds: float
    daily_token_budget: int
    dataset_seed: int
    data_dir: Path
    chroma_dir: Path

    @property
    def groq_enabled(self) -> bool:
        return bool(self.groq_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv()
    return Settings(
        groq_api_key=getenv('GROQ_API_KEY'),
        groq_base_url=getenv('GROQ_BASE_URL', 'https://api.groq.com/openai/v1'),
        request_timeout_seconds=_as_float('GROQ_TIMEOUT_SECONDS', 45.0),
        max_retries=_as_int('GROQ_MAX_RETRIES', 3),
        backoff_base_seconds=_as_float('GROQ_BACKOFF_BASE_SECONDS', 1.0),
        backoff_max_seconds=_as_float('GROQ_BACKOFF_MAX_SECONDS', 8.0),
        daily_token_budget=_as_int('DAILY_TOKEN_BUDGET', 200_000),
        dataset_seed=_as_int('DATASET_SEED', 42),
        data_dir=Path(getenv('DATA_DIR', 'data')),
        chroma_dir=Path(getenv('CHROMA_DIR', 'chroma_db')),
    )
