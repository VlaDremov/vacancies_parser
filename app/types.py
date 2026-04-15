from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SourceConfig:
    id: str
    company_name: str
    careers_url: str
    parser_type: str
    country_hint: str | None = None
    enabled: bool = True
    selectors: dict[str, str] = field(default_factory=dict)
    pagination: dict[str, Any] | None = None
    parser_options: dict[str, Any] | None = None
    matching_profile: dict[str, Any] | None = None
    job_url_template: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawJob:
    source_id: str
    external_id: str | None
    url: str
    title: str
    location: str | None
    description: str | None
    posted_at: datetime | None


@dataclass(frozen=True)
class NormalizedVacancy:
    canonical_id: str
    company: str
    title: str
    location: str
    url: str
    posted_at: datetime | None
    description_text: str
    source_id: str
    external_id: str | None


@dataclass(frozen=True)
class MatchResult:
    vacancy_id: int
    score: float
    matched_terms: list[str]
    geo_pass: bool
    decision: str


@dataclass(frozen=True)
class DigestItem:
    vacancy_id: int
    company: str
    title: str
    location: str
    url: str
    score: float
    posted_at: datetime | None


@dataclass(frozen=True)
class RunStats:
    run_id: int
    status: str
    sources_total: int
    jobs_fetched: int
    jobs_matched: int
    jobs_sent: int
    errors: dict[str, str]
