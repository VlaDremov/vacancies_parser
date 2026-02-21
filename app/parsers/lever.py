from __future__ import annotations

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import anchor_url, compact, parse_json_ld_job_postings
from app.types import RawJob, SourceConfig


class LeverParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        for anchor in soup.select("a[href*='jobs.lever.co'], a[href*='lever.co']"):
            title = compact(anchor.get_text(" ", strip=True))
            url = anchor_url(source.careers_url, anchor.get("href"))
            if not title or not url or url in seen_urls:
                continue

            path_parts = [part for part in url.rstrip("/").split("/") if part]
            external_id = path_parts[-1] if path_parts else None

            location = ""
            node = anchor.parent
            if node:
                text = compact(node.get_text(" ", strip=True))
                if text and text != title:
                    location = text.replace(title, "").strip(" |,-")

            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=external_id,
                    url=url,
                    title=title,
                    location=location,
                    description="",
                    posted_at=None,
                )
            )
            seen_urls.add(url)

        return jobs
