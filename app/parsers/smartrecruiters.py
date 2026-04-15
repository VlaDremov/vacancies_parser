from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import (
    anchor_url,
    compact,
    load_json_payload,
    parse_datetime,
    parse_json_ld_job_postings,
    resolve_data_path,
)
from app.types import RawJob, SourceConfig

SMARTRECRUITERS_ID_RE = re.compile(r"/([^/]+)/[^/]+/(\d+)$")


class SmartRecruitersParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        payload = load_json_payload(content)
        if payload is not None:
            jobs = _parse_smartrecruiters_payload(payload, source)
            if jobs:
                return jobs

        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        for anchor in soup.select("a[href*='smartrecruiters.com'], a[href*='/job/']"):
            title = compact(anchor.get_text(" ", strip=True))
            url = anchor_url(source.careers_url, anchor.get("href"))
            if not title or not url or url in seen_urls:
                continue

            container = anchor.parent
            location = compact(container.get("data-location")) if container else ""
            if not location and container:
                siblings = [container.get("data-department"), container.get("data-location")]
                location = compact(", ".join(str(value) for value in siblings if value))

            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=_extract_external_id(url),
                    url=url,
                    title=title,
                    location=location,
                    description="",
                    posted_at=None,
                )
            )
            seen_urls.add(url)

        return jobs


def _parse_smartrecruiters_payload(payload, source: SourceConfig) -> list[RawJob]:
    job_list = resolve_data_path(payload, "content")
    if not isinstance(job_list, list):
        job_list = resolve_data_path(payload, "jobs")
    if not isinstance(job_list, list):
        return []

    jobs: list[RawJob] = []
    seen_urls: set[str] = set()
    for item in job_list:
        if not isinstance(item, dict):
            continue
        title = compact(str(item.get("name") or item.get("title") or ""))
        url = anchor_url(source.careers_url, item.get("ref") or item.get("jobAdUrl"))
        if not title or not url or url in seen_urls:
            continue

        department = item.get("department") or {}
        location = item.get("location") or {}
        location_parts = [
            location.get("city"),
            location.get("region"),
            location.get("country"),
            department.get("label") if isinstance(department, dict) else department,
        ]
        jobs.append(
            RawJob(
                source_id=source.id,
                external_id=compact(str(item.get("id") or "")) or _extract_external_id(url),
                url=url,
                title=title,
                location=compact(", ".join(str(value) for value in location_parts if value)),
                description=compact(str(item.get("jobAd", {}).get("sections", "") if isinstance(item.get("jobAd"), dict) else "")),
                posted_at=parse_datetime(str(item.get("releasedDate") or item.get("createdOn") or "")),
            )
        )
        seen_urls.add(url)
    return jobs


def _extract_external_id(url: str) -> str | None:
    match = SMARTRECRUITERS_ID_RE.search(url.rstrip("/"))
    if not match:
        return None
    return match.group(2)
