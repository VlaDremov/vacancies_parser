from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import Source, build_session_factory, init_db, session_scope
from app.fetcher import BotBlockedError, FetchError, SourceFetcher
from app.matcher import compute_match
from app.normalizer import normalize_job
from app.notifier import build_digest_message, send_telegram_message
from app.pagination import build_additional_page_urls
from app.parsers import get_parser
from app.settings import Settings
from app.source_loader import iter_source_configs
from app.store import (
    finish_run,
    is_suppressed,
    record_notifications,
    save_match,
    start_run,
    upsert_source,
    upsert_vacancy,
)
from app.types import DigestItem, MatchResult, RawJob, RunStats, SourceConfig

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        init_db(settings.database_url)
        self.session_factory = build_session_factory(settings.database_url)
        self.fetcher = SourceFetcher(timeout_seconds=settings.fetch_timeout_seconds)

    def run(self, run_at: datetime | None = None, notify: bool = True) -> RunStats:
        now = run_at or datetime.now(timezone.utc)
        errors: dict[str, str] = {}
        jobs_fetched = 0
        jobs_matched = 0
        jobs_sent = 0
        digest_items: list[DigestItem] = []

        with session_scope(self.session_factory) as session:
            source_configs = list(iter_source_configs(self.settings.source_config_dir))
            source_config_by_id = {cfg.id: cfg for cfg in source_configs}
            for source_config in source_configs:
                upsert_source(session, source_config)

            sources = list(session.scalars(select(Source).where(Source.enabled.is_(True))))
            run_row = start_run(session, len(sources), now)

            for source in sources:
                source_cfg = self._build_source_config(source=source, source_config_by_id=source_config_by_id)

                try:
                    raw_jobs = self._fetch_and_parse(source_cfg)
                except BotBlockedError as exc:
                    message = f"blocked by anti-bot policy: {exc}"
                    errors[source.id] = message
                    logger.warning("source_blocked", extra={"source_id": source.id, "reason": str(exc)})
                    continue
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    errors[source.id] = str(exc)
                    logger.exception("source_failed", extra={"source_id": source.id})
                    continue

                jobs_fetched += len(raw_jobs)
                for raw_job in raw_jobs:
                    normalized = normalize_job(raw_job, company=source.company_name, country_hint=source.country_hint)
                    vacancy = upsert_vacancy(session, normalized, now=now)

                    computed = compute_match(
                        normalized,
                        min_score=self.settings.min_match_score,
                        enable_remote_eu=self.settings.enable_remote_eu,
                        match_profile=self.settings.match_profile,
                        source_profile=source_cfg.matching_profile,
                    )
                    match_result = MatchResult(
                        vacancy_id=vacancy.id,
                        score=computed.score,
                        matched_terms=computed.matched_terms,
                        geo_pass=computed.geo_pass,
                        decision=computed.decision,
                    )
                    save_match(session, match_result, now=now)

                    if computed.decision != "send":
                        continue

                    jobs_matched += 1
                    if is_suppressed(session, vacancy.id, channel="telegram", now=now):
                        continue

                    digest_items.append(
                        DigestItem(
                            vacancy_id=vacancy.id,
                            company=source.company_name,
                            title=normalized.title,
                            location=normalized.location,
                            url=normalized.url,
                            score=computed.score,
                            posted_at=normalized.posted_at,
                        )
                    )

            if notify and digest_items:
                digest_items = sorted(digest_items, key=lambda x: x.score, reverse=True)
                to_send = digest_items[: self.settings.max_items_per_digest]
                message = build_digest_message(
                    to_send,
                    run_at=now,
                    sources_total=len(sources),
                    matched_total=jobs_matched,
                    run_timezone=self.settings.run_timezone,
                )
                send_telegram_message(
                    bot_token=self.settings.telegram_bot_token,
                    chat_id=self.settings.telegram_chat_id,
                    text=message,
                )
                record_notifications(
                    session,
                    vacancy_ids=[item.vacancy_id for item in to_send],
                    channel="telegram",
                    now=now,
                    dedupe_days=self.settings.dedupe_days,
                )
                jobs_sent = len(to_send)

            status = self._compute_status(errors=errors, jobs_fetched=jobs_fetched)
            finish_run(
                run_row,
                now=datetime.now(timezone.utc),
                status=status,
                jobs_fetched=jobs_fetched,
                jobs_matched=jobs_matched,
                jobs_sent=jobs_sent,
                error_summary=(json.dumps(errors, sort_keys=True) if errors else None),
            )

            return RunStats(
                run_id=run_row.id,
                status=status,
                sources_total=len(sources),
                jobs_fetched=jobs_fetched,
                jobs_matched=jobs_matched,
                jobs_sent=jobs_sent,
                errors=errors,
            )

    def _fetch_and_parse(self, source: SourceConfig) -> list[RawJob]:
        parser = get_parser(source.parser_type)
        jobs = self._fetch_single_page_with_retries(source=source, parser=parser, url=source.careers_url)

        page_urls = build_additional_page_urls(source)
        for page_url in page_urls:
            try:
                page_jobs = self._fetch_single_page_with_retries(source=source, parser=parser, url=page_url)
            except BotBlockedError as exc:
                logger.warning(
                    "pagination_blocked",
                    extra={"source_id": source.id, "url": page_url, "reason": str(exc)},
                )
                break
            except FetchError as exc:
                logger.warning(
                    "pagination_page_failed",
                    extra={"source_id": source.id, "url": page_url, "reason": str(exc)},
                )
                continue
            if not page_jobs:
                logger.info("pagination_page_empty", extra={"source_id": source.id, "url": page_url})
                continue
            jobs.extend(page_jobs)

        return _dedupe_jobs(jobs)

    def _fetch_single_page_with_retries(self, source: SourceConfig, parser, url: str) -> list[RawJob]:
        for attempt in range(self.settings.max_fetch_retries):
            try:
                result = self.fetcher.fetch_http(source, url=url)
                if result.blocked_reason:
                    raise BotBlockedError(result.blocked_reason)

                jobs = parser.parse(result.content, source)
                if jobs:
                    return jobs

                fallback = self.fetcher.fetch_playwright(source, url=url)
                if fallback.blocked_reason:
                    raise BotBlockedError(fallback.blocked_reason)
                return parser.parse(fallback.content, source)
            except BotBlockedError:
                raise
            except Exception as exc:
                if attempt >= self.settings.max_fetch_retries - 1:
                    raise FetchError(f"fetch failed for {source.id}: {exc}") from exc
                delay = 2**attempt
                time.sleep(delay)

        return []

    @staticmethod
    def _build_source_config(source: Source, source_config_by_id: dict[str, SourceConfig]) -> SourceConfig:
        config_from_file = source_config_by_id.get(source.id)
        return SourceConfig(
            id=source.id,
            company_name=source.company_name,
            careers_url=source.careers_url,
            parser_type=source.parser_type,
            country_hint=source.country_hint,
            enabled=source.enabled,
            selectors=source.selectors,
            pagination=config_from_file.pagination if config_from_file else None,
            parser_options=config_from_file.parser_options if config_from_file else None,
            matching_profile=config_from_file.matching_profile if config_from_file else None,
            job_url_template=config_from_file.job_url_template if config_from_file else None,
            extra=config_from_file.extra if config_from_file else {},
        )

    @staticmethod
    def _compute_status(errors: dict[str, str], jobs_fetched: int) -> str:
        if not errors:
            return "success"
        if jobs_fetched > 0:
            return "partial_failure"
        return "failure"


def _dedupe_jobs(jobs: list[RawJob]) -> list[RawJob]:
    seen = set()
    unique: list[RawJob] = []
    for job in jobs:
        key = (job.url, job.title)
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)
    return unique
