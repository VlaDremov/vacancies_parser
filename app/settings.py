from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    telegram_bot_token: str
    telegram_chat_id: str
    run_timezone: str
    min_match_score: float
    max_items_per_digest: int
    dedupe_days: int
    max_fetch_retries: int
    fetch_timeout_seconds: int
    run_timeout_minutes: int
    source_config_dir: str
    enable_remote_eu: bool


    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./vacancies.db"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            run_timezone=os.getenv("RUN_TIMEZONE", "UTC"),
            min_match_score=float(os.getenv("MIN_MATCH_SCORE", "0.60")),
            max_items_per_digest=int(os.getenv("MAX_ITEMS_PER_DIGEST", "20")),
            dedupe_days=int(os.getenv("DEDUPE_DAYS", "7")),
            max_fetch_retries=int(os.getenv("MAX_FETCH_RETRIES", "3")),
            fetch_timeout_seconds=int(os.getenv("FETCH_TIMEOUT_SECONDS", "20")),
            run_timeout_minutes=int(os.getenv("RUN_TIMEOUT_MINUTES", "40")),
            source_config_dir=os.getenv("SOURCE_CONFIG_DIR", "config/sources"),
            enable_remote_eu=os.getenv("ENABLE_REMOTE_EU", "false").lower() == "true",
        )
