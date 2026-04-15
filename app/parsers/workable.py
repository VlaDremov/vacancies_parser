from __future__ import annotations

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import anchor_url, compact, load_json_payload, parse_datetime, parse_json_ld_job_postings
from app.types import RawJob, SourceConfig


class WorkableParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        payload = load_json_payload(content)
        if isinstance(payload, dict):
            jobs = _parse_workable_payload(payload, source)
            if jobs:
                return jobs

        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        for card in soup.select("[data-ui='job'], .jobs li, .job"):
            anchor = card.select_one("a[href]")
            if not anchor:
                continue
            title = compact(anchor.get_text(" ", strip=True))
            url = anchor_url(source.careers_url, anchor.get("href"))
            if not title or not url or url in seen_urls:
                continue

            location = compact(
                " ".join(node.get_text(" ", strip=True) for node in card.select(".location, [data-ui='job-location']"))
            )
            posted = card.get("data-posted-at")
            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=compact(card.get("data-job-id")) or _url_tail(url),
                    url=url,
                    title=title,
                    location=location,
                    description="",
                    posted_at=parse_datetime(posted),
                )
            )
            seen_urls.add(url)

        return jobs


def _parse_workable_payload(payload: dict, source: SourceConfig) -> list[RawJob]:
    items = payload.get("results") or payload.get("jobs")
    if not isinstance(items, list):
        return []

    jobs: list[RawJob] = []
    seen_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = compact(str(item.get("title") or item.get("name") or ""))
        url = anchor_url(source.careers_url, item.get("url") or item.get("shortcode"))
        if not title or not url or url in seen_urls:
            continue

        location = item.get("location") or {}
        if isinstance(location, dict):
            location_text = compact(
                ", ".join(str(value) for value in (location.get("city"), location.get("country")) if value)
            )
        else:
            location_text = compact(str(location))

        jobs.append(
            RawJob(
                source_id=source.id,
                external_id=compact(str(item.get("id") or item.get("shortcode") or "")) or _url_tail(url),
                url=url,
                title=title,
                location=location_text,
                description=compact(str(item.get("description") or "")),
                posted_at=parse_datetime(str(item.get("published") or item.get("created_at") or "")),
            )
        )
        seen_urls.add(url)
    return jobs


def _url_tail(url: str) -> str | None:
    parts = [part for part in url.rstrip("/").split("/") if part]
    return parts[-1] if parts else None
