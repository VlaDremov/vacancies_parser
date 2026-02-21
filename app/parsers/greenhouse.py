from __future__ import annotations

import re

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import anchor_url, compact, parse_json_ld_job_postings
from app.types import RawJob, SourceConfig

GREENHOUSE_ID_RE = re.compile(r"(\d{4,})")


class GreenhouseParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        for anchor in soup.select("a[href*='/jobs/'], a[href*='greenhouse.io']"):
            title = compact(anchor.get_text(" ", strip=True))
            href = anchor.get("href")
            url = anchor_url(source.careers_url, href)
            if not title or not url or url in seen_urls:
                continue

            location = ""
            parent_text = compact(anchor.parent.get_text(" ", strip=True)) if anchor.parent else ""
            if parent_text and parent_text != title:
                location = parent_text.replace(title, "").strip(" |,-")

            external_match = GREENHOUSE_ID_RE.search(url)
            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=external_match.group(1) if external_match else None,
                    url=url,
                    title=title,
                    location=location,
                    description="",
                    posted_at=None,
                )
            )
            seen_urls.add(url)

        return jobs
