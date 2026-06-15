"""Application configuration for CapitalLens AI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = ROOT_DIR / "reports"
DB_PATH = ROOT_DIR / "capital_lens_watchlist.db"


@dataclass(frozen=True)
class Settings:
    """Small dependency-free settings object backed by environment variables."""

    app_name: str = "CapitalLens AI"
    demo_mode: bool = True
    openai_api_key: str | None = None
    openai_model: str = "gpt-4.1-mini"
    news_api_key: str | None = None
    sec_user_agent: str = "CapitalLensAI/1.0 contact@example.com"
    cache_ttl_seconds: int = 900
    database_path: Path = DB_PATH


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_settings() -> Settings:
    """Load settings on demand so tests can override environment variables."""

    api_key = os.getenv("OPENAI_API_KEY")
    default_demo = not bool(api_key)
    return Settings(
        demo_mode=_env_bool("DEMO_MODE", default_demo),
        openai_api_key=api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
        news_api_key=os.getenv("NEWS_API_KEY"),
        sec_user_agent=os.getenv("SEC_USER_AGENT", "CapitalLensAI/1.0 contact@example.com"),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "900")),
        database_path=Path(os.getenv("CAPITALLENS_DB_PATH", str(DB_PATH))),
    )

