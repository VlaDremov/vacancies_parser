from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from app.matcher import (
    DEFAULT_GEO_TERMS,
    DEFAULT_NEGATIVE_RULES,
    DEFAULT_POSITIVE_RULES,
    DEFAULT_REMOTE_REGION_TERMS,
    DEFAULT_REMOTE_TERMS,
    MatchProfile,
    build_match_profile,
)


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
    match_positive_terms: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_POSITIVE_RULES))
    match_negative_terms: dict[str, Any] = field(default_factory=lambda: dict(DEFAULT_NEGATIVE_RULES))
    match_geo_terms: set[str] = field(default_factory=lambda: set(DEFAULT_GEO_TERMS))
    match_remote_terms: set[str] = field(default_factory=lambda: set(DEFAULT_REMOTE_TERMS))
    match_remote_region_terms: set[str] = field(default_factory=lambda: set(DEFAULT_REMOTE_REGION_TERMS))

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
            match_positive_terms=_load_json_object("MATCH_POSITIVE_TERMS_JSON", DEFAULT_POSITIVE_RULES),
            match_negative_terms=_load_json_object("MATCH_NEGATIVE_TERMS_JSON", DEFAULT_NEGATIVE_RULES),
            match_geo_terms=_load_string_set("MATCH_GEO_TERMS_JSON", DEFAULT_GEO_TERMS),
            match_remote_terms=_load_string_set("MATCH_REMOTE_TERMS_JSON", DEFAULT_REMOTE_TERMS),
            match_remote_region_terms=_load_string_set(
                "MATCH_REMOTE_REGION_TERMS_JSON",
                DEFAULT_REMOTE_REGION_TERMS,
            ),
        )

    @property
    def match_profile(self) -> MatchProfile:
        return build_match_profile(
            positive_terms=self.match_positive_terms,
            negative_terms=self.match_negative_terms,
            geo_terms=self.match_geo_terms,
            remote_terms=self.match_remote_terms,
            remote_region_terms=self.match_remote_region_terms,
        )


def _load_json_object(name: str, default: dict[str, Any]) -> dict[str, Any]:
    raw = os.getenv(name)
    if not raw:
        return dict(default)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return dict(default)
    return payload if isinstance(payload, dict) else dict(default)


def _load_string_set(name: str, default: set[str]) -> set[str]:
    raw = os.getenv(name)
    if not raw:
        return set(default)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return set(default)
    if not isinstance(payload, list):
        return set(default)
    return {str(item).strip().lower() for item in payload if str(item).strip()}
