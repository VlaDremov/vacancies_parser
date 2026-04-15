from __future__ import annotations

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import anchor_url, compact, parse_datetime, parse_json_ld_job_postings
from app.parsers.generic_json import GenericJsonParser
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
        posted_at_selector = selectors.get("posted_at")
        external_id_selector = selectors.get("external_id")

        if card_selector:
            structured_jobs = _extract_structured_jobs(
                soup=soup,
                source=source,
                seen_urls=seen_urls,
                card_selector=card_selector,
                title_selector=title_selector,
                link_selector=link_selector,
                location_selector=location_selector,
                desc_selector=desc_selector,
                posted_at_selector=posted_at_selector,
                external_id_selector=external_id_selector,
            )
            jobs.extend(structured_jobs)

            if structured_jobs:
                return jobs

        for anchor in soup.select("a[href]"):
            title = compact(anchor.get_text(" ", strip=True))
            if not title:
                title = compact(anchor.get("title"))
            link = anchor_url(source.careers_url, anchor.get("href"))
            if not title or not link or link in seen_urls:
                continue

            lower = f"{title} {link}".lower()
            if not any(term in lower for term in ("job", "career", "position", "opening", "role")):
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


def _extract_structured_jobs(
    soup: BeautifulSoup,
    source: SourceConfig,
    seen_urls: set[str],
    card_selector: str,
    title_selector: str | None,
    link_selector: str | None,
    location_selector: str | None,
    desc_selector: str | None,
    posted_at_selector: str | None,
    external_id_selector: str | None,
) -> list[RawJob]:
    jobs: list[RawJob] = []
    for card in soup.select(card_selector):
        title = _select_text(card, title_selector)
        if not title:
            title = compact(card.get("title")) or compact(card.get_text(" ", strip=True))

        link = _select_link(card, source, link_selector)
        if not title or not link or link in seen_urls:
            continue

        jobs.append(
            RawJob(
                source_id=source.id,
                external_id=_select_external_id(card, external_id_selector),
                url=link,
                title=title,
                location=_select_text(card, location_selector),
                description=_select_text(card, desc_selector),
                posted_at=parse_datetime(_select_text(card, posted_at_selector)),
            )
        )
        seen_urls.add(link)
    return jobs


def _select_text(node, selector: str | None) -> str:
    if not selector:
        return ""
    selected = node.select_one(selector)
    if not selected:
        return ""
    return compact(selected.get_text(" ", strip=True))


def _select_link(node, source: SourceConfig, selector: str | None) -> str:
    if selector:
        selected = node.select_one(selector)
        if selected and selected.get("href"):
            return anchor_url(source.careers_url, selected.get("href"))

    if node.get("href"):
        return anchor_url(source.careers_url, node.get("href"))

    if selector:
        selected = node.select_one(selector)
        if selected:
            href = selected.get("data-href") or selected.get("data-url")
            if href:
                return anchor_url(source.careers_url, href)

    anchor = node.find("a", href=True)
    if anchor:
        return anchor_url(source.careers_url, anchor.get("href"))
    return ""


def _select_external_id(node, selector: str | None) -> str | None:
    if selector:
        selected = node.select_one(selector)
        if selected:
            value = selected.get("data-id") or selected.get("id") or selected.get_text(" ", strip=True)
            text = compact(value)
            return text or None

    for attr in ("data-job-id", "data-id", "data-posting-id"):
        if node.get(attr):
            text = compact(node.get(attr))
            if text:
                return text
    return None


def _parse_json_jobs(content: str, source: SourceConfig) -> list[RawJob]:
    parser_options = source.parser_options or {}
    if source.job_url_template or parser_options.get("fields"):
        merged_options = {
            "jobs_path": parser_options.get("jobs_path", "data"),
            "fields": {
                "title": "title",
                "url": "url",
                "external_id": "id",
                "location": "location",
                "description": "description",
                "posted_at": "posted_at",
                **(parser_options.get("fields", {}) if isinstance(parser_options.get("fields"), dict) else {}),
            },
        }
    else:
        merged_options = {
            "jobs_path": "data",
            "fields": {
                "title": "title",
                "url": "url",
                "external_id": "id",
                "location": "location",
                "description": "description",
                "posted_at": "posted_at",
            },
        }

    json_source = SourceConfig(
        id=source.id,
        company_name=source.company_name,
        careers_url=source.careers_url,
        parser_type="generic_json",
        country_hint=source.country_hint,
        enabled=source.enabled,
        selectors=source.selectors,
        pagination=source.pagination,
        parser_options=merged_options,
        matching_profile=source.matching_profile,
        job_url_template=source.job_url_template,
        extra=source.extra,
    )

    return GenericJsonParser().parse(content, json_source)
