from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import anchor_url, compact, parse_json_ld_job_postings
from app.types import RawJob, SourceConfig


class GenericHtmlParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        json_jobs = _parse_json_jobs(content, source)
        if json_jobs:
            return json_jobs

        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        selectors = source.selectors or {}
        card_selector = selectors.get("job_card")
        title_selector = selectors.get("title")
        link_selector = selectors.get("link")
        location_selector = selectors.get("location")
        desc_selector = selectors.get("description")

        if card_selector:
            for card in soup.select(card_selector):
                title = ""
                if title_selector:
                    title_node = card.select_one(title_selector)
                    if title_node:
                        title = compact(title_node.get_text(" ", strip=True))
                if not title:
                    title = compact(card.get_text(" ", strip=True))

                link = ""
                if link_selector:
                    link_node = card.select_one(link_selector)
                    if link_node and link_node.get("href"):
                        link = anchor_url(source.careers_url, link_node.get("href"))
                if not link and card.get("href"):
                    link = anchor_url(source.careers_url, card.get("href"))
                if not link:
                    anchor = card.find("a")
                    link = anchor_url(source.careers_url, anchor.get("href") if anchor else "")

                if not title or not link or link in seen_urls:
                    continue

                location = ""
                if location_selector:
                    location_node = card.select_one(location_selector)
                    if location_node:
                        location = compact(location_node.get_text(" ", strip=True))

                description = ""
                if desc_selector:
                    description_node = card.select_one(desc_selector)
                    if description_node:
                        description = compact(description_node.get_text(" ", strip=True))

                jobs.append(
                    RawJob(
                        source_id=source.id,
                        external_id=None,
                        url=link,
                        title=title,
                        location=location,
                        description=description,
                        posted_at=None,
                    )
                )
                seen_urls.add(link)

            # When source-specific card selectors are configured, avoid broad anchor crawling.
            if jobs:
                return jobs

        for anchor in soup.select("a[href]"):
            title = compact(anchor.get_text(" ", strip=True))
            link = anchor_url(source.careers_url, anchor.get("href"))
            if not title or not link or link in seen_urls:
                continue
            lower = f"{title} {link}".lower()
            if "job" not in lower and "career" not in lower and "position" not in lower:
                continue

            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=None,
                    url=link,
                    title=title,
                    location="",
                    description="",
                    posted_at=None,
                )
            )
            seen_urls.add(link)

        return jobs


def _parse_json_jobs(content: str, source: SourceConfig) -> list[RawJob]:
    stripped = content.lstrip()
    if not stripped.startswith("{") and not stripped.startswith("["):
        return []

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        return []

    if not isinstance(payload, dict):
        return []

    items = payload.get("data")
    if not isinstance(items, list):
        return []

    template = str(source.extra.get("json_job_url_template", "")).strip()
    jobs: list[RawJob] = []
    for item in items:
        if not isinstance(item, dict):
            continue

        title = compact(str(item.get("title", "")))
        if not title:
            continue

        external_id = str(item.get("id")) if item.get("id") is not None else None
        url = _json_job_url(item=item, source=source, title=title, external_id=external_id, template=template)
        if not url:
            continue

        location = _json_location(item)
        description = compact(str(item.get("description", "")))
        jobs.append(
            RawJob(
                source_id=source.id,
                external_id=external_id,
                url=url,
                title=title,
                location=location,
                description=description,
                posted_at=None,
            )
        )

    return jobs


def _json_job_url(
    item: dict,
    source: SourceConfig,
    title: str,
    external_id: str | None,
    template: str,
) -> str:
    for key in ("url", "job_url", "apply_url", "link", "href"):
        value = item.get(key)
        if not value:
            continue
        return anchor_url(source.careers_url, str(value))

    if not template:
        return ""
    if not external_id:
        return ""

    slug = _slugify(title)
    try:
        return template.format(id=external_id, slug=slug, title=title)
    except Exception:
        return ""


def _json_location(item: dict) -> str:
    offices = item.get("offices")
    if isinstance(offices, list):
        return compact(", ".join(str(value) for value in offices if value))
    return compact(str(item.get("location", "")))


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "job"
