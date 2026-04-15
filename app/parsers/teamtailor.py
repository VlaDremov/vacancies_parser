from __future__ import annotations

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


class TeamtailorParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        payload = load_json_payload(content)
        if payload is not None:
            jobs = _parse_teamtailor_payload(payload, source)
            if jobs:
                return jobs

        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        for anchor in soup.select("a[href*='/jobs/'], a[data-job-url]"):
            url = anchor_url(source.careers_url, anchor.get("href") or anchor.get("data-job-url"))
            title = compact(anchor.get("data-job-title")) or compact(anchor.get_text(" ", strip=True))
            if not title or not url or url in seen_urls:
                continue

            container = anchor.parent
            location = ""
            if container:
                location = compact(container.get("data-location")) or compact(
                    " ".join(
                        child.get_text(" ", strip=True)
                        for child in container.select("[data-job-location], .job-location, .location")
                    )
                )

            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=compact(anchor.get("data-job-id")) or _url_tail(url),
                    url=url,
                    title=title,
                    location=location,
                    description="",
                    posted_at=parse_datetime(anchor.get("data-posted-at")),
                )
            )
            seen_urls.add(url)

        return jobs


def _parse_teamtailor_payload(payload, source: SourceConfig) -> list[RawJob]:
    items = resolve_data_path(payload, "data")
    if not isinstance(items, list):
        return []

    jobs: list[RawJob] = []
    seen_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue

        attributes = item.get("attributes", {})
        title = compact(str(attributes.get("title") or item.get("title") or ""))
        if not title:
            continue

        url = anchor_url(
            source.careers_url,
            attributes.get("human_status_url")
            or attributes.get("url")
            or item.get("links", {}).get("careersite-job-url"),
        )
        if not url or url in seen_urls:
            continue

        location = compact(
            ", ".join(
                str(value)
                for value in (
                    attributes.get("location"),
                    attributes.get("location_name"),
                    attributes.get("remote_status"),
                )
                if value
            )
        )
        jobs.append(
            RawJob(
                source_id=source.id,
                external_id=compact(str(item.get("id") or "")) or _url_tail(url),
                url=url,
                title=title,
                location=location,
                description=compact(str(attributes.get("body") or attributes.get("description") or "")),
                posted_at=parse_datetime(str(attributes.get("created_at") or attributes.get("published_at") or "")),
            )
        )
        seen_urls.add(url)
    return jobs


def _url_tail(url: str) -> str | None:
    parts = [part for part in url.rstrip("/").split("/") if part]
    return parts[-1] if parts else None
