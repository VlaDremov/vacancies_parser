from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.types import RawJob, SourceConfig

WHITESPACE_RE = re.compile(r"\s+")


def compact(text: str | None) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", text).strip()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw.replace("Z", "+00:00")

    for candidate in (raw, raw.replace("/", "-")):
        try:
            dt = datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            pass

    try:
        dt2 = parsedate_to_datetime(raw)
        if dt2.tzinfo is None:
            return dt2.replace(tzinfo=timezone.utc)
        return dt2.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def parse_json_ld_job_postings(soup: BeautifulSoup, source: SourceConfig) -> list[RawJob]:
    jobs: list[RawJob] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        payload = script.string or script.get_text(strip=True)
        if not payload:
            continue
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            continue
        objects = data if isinstance(data, list) else [data]
        for obj in objects:
            jobs.extend(_extract_jobs_from_ld_object(obj, source))
    return jobs


def _extract_jobs_from_ld_object(obj: object, source: SourceConfig) -> list[RawJob]:
    if not isinstance(obj, dict):
        return []

    type_value = str(obj.get("@type", "")).lower()
    if type_value == "jobposting":
        title = compact(str(obj.get("title", "")))
        if not title:
            return []

        location_value = ""
        job_location = obj.get("jobLocation")
        if isinstance(job_location, dict):
            address = job_location.get("address")
            if isinstance(address, dict):
                parts = [address.get("addressLocality"), address.get("addressCountry")]
                location_value = compact(" ".join(str(p) for p in parts if p))

        return [
            RawJob(
                source_id=source.id,
                external_id=(str(obj.get("identifier")) if obj.get("identifier") else None),
                url=str(obj.get("url") or source.careers_url),
                title=title,
                location=location_value or compact(str(obj.get("jobLocationType", ""))),
                description=compact(str(obj.get("description", ""))),
                posted_at=parse_datetime(str(obj.get("datePosted", ""))),
            )
        ]

    graph = obj.get("@graph")
    if isinstance(graph, list):
        all_jobs: list[RawJob] = []
        for entry in graph:
            all_jobs.extend(_extract_jobs_from_ld_object(entry, source))
        return all_jobs

    return []


def anchor_url(base_url: str, href: str | None) -> str:
    if not href:
        return ""
    return urljoin(base_url, href.strip())
