from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import Match, Notification, Run, Source, Vacancy
from app.types import MatchResult, NormalizedVacancy, SourceConfig


def upsert_source(session: Session, source: SourceConfig) -> None:
    existing = session.get(Source, source.id)
    now = datetime.now(timezone.utc)
    if existing is None:
        session.add(
            Source(
                id=source.id,
                company_name=source.company_name,
                careers_url=source.careers_url,
                parser_type=source.parser_type,
                country_hint=source.country_hint,
                selectors=source.selectors,
                enabled=source.enabled,
                created_at=now,
                updated_at=now,
            )
        )
        return

    existing.company_name = source.company_name
    existing.careers_url = source.careers_url
    existing.parser_type = source.parser_type
    existing.country_hint = source.country_hint
    existing.selectors = source.selectors
    existing.enabled = source.enabled
    existing.updated_at = now


def upsert_vacancy(session: Session, vacancy: NormalizedVacancy, now: datetime) -> Vacancy:
    row = session.scalar(
        select(Vacancy).where(
            Vacancy.source_id == vacancy.source_id,
            Vacancy.canonical_hash == vacancy.canonical_id,
        )
    )
    if row is None:
        row = Vacancy(
            source_id=vacancy.source_id,
            canonical_hash=vacancy.canonical_id,
            external_id=vacancy.external_id,
            url=vacancy.url,
            title=vacancy.title,
            location=vacancy.location,
            description=vacancy.description_text,
            posted_at=vacancy.posted_at,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(row)
        session.flush()
        return row

    row.external_id = vacancy.external_id
    row.url = vacancy.url
    row.title = vacancy.title
    row.location = vacancy.location
    row.description = vacancy.description_text
    row.posted_at = vacancy.posted_at
    row.last_seen_at = now
    session.flush()
    return row


def save_match(session: Session, match_result: MatchResult, now: datetime) -> None:
    session.add(
        Match(
            vacancy_id=match_result.vacancy_id,
            score=match_result.score,
            matched_terms_json=match_result.matched_terms,
            geo_pass=match_result.geo_pass,
            decision=match_result.decision,
            created_at=now,
        )
    )


def is_suppressed(
    session: Session,
    vacancy_id: int,
    channel: str,
    now: datetime,
) -> bool:
    row = session.scalar(
        select(Notification)
        .where(
            Notification.vacancy_id == vacancy_id,
            Notification.channel == channel,
            Notification.dedupe_until > now,
        )
        .limit(1)
    )
    return row is not None


def record_notifications(
    session: Session,
    vacancy_ids: list[int],
    channel: str,
    now: datetime,
    dedupe_days: int,
) -> None:
    dedupe_until = now + timedelta(days=dedupe_days)
    for vacancy_id in vacancy_ids:
        session.add(
            Notification(
                vacancy_id=vacancy_id,
                channel=channel,
                sent_at=now,
                dedupe_until=dedupe_until,
            )
        )


def start_run(session: Session, sources_total: int, now: datetime) -> Run:
    run = Run(
        started_at=now,
        finished_at=None,
        status="running",
        sources_total=sources_total,
        jobs_fetched=0,
        jobs_matched=0,
        jobs_sent=0,
        error_summary=None,
    )
    session.add(run)
    session.flush()
    return run


def finish_run(
    run: Run,
    now: datetime,
    status: str,
    jobs_fetched: int,
    jobs_matched: int,
    jobs_sent: int,
    error_summary: str | None,
) -> None:
    run.finished_at = now
    run.status = status
    run.jobs_fetched = jobs_fetched
    run.jobs_matched = jobs_matched
    run.jobs_sent = jobs_sent
    run.error_summary = error_summary
