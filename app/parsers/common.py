from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.types import RawJob, SourceConfig

WHITESPACE_RE = re.compile(r"\s+")


def compact(text: str | None) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", unescape(text)).strip()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = compact(value)
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


def anchor_url(base_url: str, href: str | None) -> str:
    if not href:
        return ""
    return urljoin(base_url, compact(href))


def load_json_payload(content: str) -> Any | None:
    stripped = content.lstrip()
    if not stripped.startswith("{") and not stripped.startswith("["):
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def resolve_data_path(payload: Any, path: str | None) -> Any | None:
    if not path:
        return payload

    current = payload
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            if 0 <= index < len(current):
                current = current[index]
                continue
        return None
    return current


def read_text_path(payload: Any, path: str | None) -> str:
    value = resolve_data_path(payload, path)
    if value is None:
        return ""
    if isinstance(value, list):
        return compact(", ".join(compact(str(item)) for item in value if compact(str(item))))
    if isinstance(value, dict):
        return compact(str(value.get("value", "")))
    return compact(str(value))


def read_datetime_path(payload: Any, path: str | None) -> datetime | None:
    return parse_datetime(read_text_path(payload, path))


def read_identifier_path(payload: Any, path: str | None) -> str | None:
    value = resolve_data_path(payload, path)
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("value") or value.get("@id") or value.get("name")
    text = compact(str(value))
    return text or None


def _extract_jobs_from_ld_object(obj: object, source: SourceConfig) -> list[RawJob]:
    if not isinstance(obj, dict):
        return []

    type_value = obj.get("@type", "")
    type_values = {str(value).lower() for value in (type_value if isinstance(type_value, list) else [type_value])}
    if "jobposting" in type_values:
        title = compact(str(obj.get("title", "")))
        if not title:
            return []

        return [
            RawJob(
                source_id=source.id,
                external_id=_extract_identifier(obj.get("identifier")),
                url=anchor_url(source.careers_url, str(obj.get("url") or source.careers_url)),
                title=title,
                location=_extract_job_location(obj),
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


def _extract_identifier(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        for key in ("value", "@id", "name"):
            raw = value.get(key)
            if raw:
                text = compact(str(raw))
                if text:
                    return text
        return None
    text = compact(str(value))
    return text or None


def _extract_job_location(obj: dict[str, Any]) -> str:
    job_location = obj.get("jobLocation")
    parts: list[str] = []
    if isinstance(job_location, list):
        for item in job_location:
            value = _extract_location_part(item)
            if value:
                parts.append(value)
    else:
        value = _extract_location_part(job_location)
        if value:
            parts.append(value)

    if parts:
        return compact(", ".join(dict.fromkeys(parts)))

    return compact(str(obj.get("jobLocationType", "")))


def _extract_location_part(job_location: Any) -> str:
    if isinstance(job_location, str):
        return compact(job_location)
    if not isinstance(job_location, dict):
        return ""

    address = job_location.get("address", job_location)
    if isinstance(address, str):
        return compact(address)
    if not isinstance(address, dict):
        return ""

    values = [
        address.get("streetAddress"),
        address.get("addressLocality"),
        address.get("addressRegion"),
        address.get("addressCountry"),
    ]
    return compact(", ".join(str(value) for value in values if value))
