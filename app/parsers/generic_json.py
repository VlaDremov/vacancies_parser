from __future__ import annotations

from app.parsers.base import BaseParser
from app.parsers.common import (
    anchor_url,
    load_json_payload,
    read_datetime_path,
    read_identifier_path,
    read_text_path,
    resolve_data_path,
)
from app.types import RawJob, SourceConfig


class GenericJsonParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        payload = load_json_payload(content)
        if payload is None:
            return []

        parser_options = source.parser_options or {}
        fields = parser_options.get("fields", {})
        jobs_payload = resolve_data_path(payload, str(parser_options.get("jobs_path", "")).strip())
        if not isinstance(jobs_payload, list) or not isinstance(fields, dict):
            return []

        jobs: list[RawJob] = []
        seen_urls: set[str] = set()
        for item in jobs_payload:
            if not isinstance(item, dict):
                continue

            title = read_text_path(item, _field(fields, "title"))
            if not title:
                continue

            external_id = read_identifier_path(item, _field(fields, "external_id"))
            url = _resolve_url(item, source, fields, title=title, external_id=external_id)
            if not url or url in seen_urls:
                continue

            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=external_id,
                    url=url,
                    title=title,
                    location=_resolve_location(item, fields),
                    description=read_text_path(item, _field(fields, "description")),
                    posted_at=read_datetime_path(item, _field(fields, "posted_at")),
                )
            )
            seen_urls.add(url)

        return jobs


def _field(fields: dict, key: str) -> str | None:
    value = fields.get(key)
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _resolve_url(
    item: dict,
    source: SourceConfig,
    fields: dict,
    title: str,
    external_id: str | None,
) -> str:
    url = read_text_path(item, _field(fields, "url"))
    if url:
        return anchor_url(source.careers_url, url)

    if not source.job_url_template or not external_id:
        return ""

    slug = read_text_path(item, _field(fields, "slug")) or _slugify(title)
    try:
        return source.job_url_template.format(id=external_id, slug=slug, title=title)
    except Exception:
        return ""


def _resolve_location(item: dict, fields: dict) -> str:
    location = read_text_path(item, _field(fields, "location"))
    if location:
        return location

    offices = item.get("offices")
    if isinstance(offices, list):
        text = ", ".join(str(value).strip() for value in offices if str(value).strip())
        if text:
            return text

    location_value = item.get("location")
    if isinstance(location_value, dict):
        text = ", ".join(
            str(value).strip()
            for value in (location_value.get("city"), location_value.get("region"), location_value.get("country"))
            if str(value).strip()
        )
        if text:
            return text

    return ""


def _slugify(value: str) -> str:
    sanitized = "".join(ch.lower() if ch.isalnum() else "-" for ch in value)
    return "-".join(part for part in sanitized.split("-") if part) or "job"
