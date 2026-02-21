from __future__ import annotations

import json

from bs4 import BeautifulSoup

from app.parsers.base import BaseParser
from app.parsers.common import anchor_url, compact, parse_datetime, parse_json_ld_job_postings
from app.types import RawJob, SourceConfig


class WorkdayParser(BaseParser):
    def parse(self, content: str, source: SourceConfig) -> list[RawJob]:
        soup = BeautifulSoup(content, "lxml")
        jobs = parse_json_ld_job_postings(soup, source)
        seen_urls = {job.url for job in jobs}

        for script in soup.find_all("script"):
            text = script.string or ""
            if "jobPostings" not in text:
                continue
            start = text.find("{")
            end = text.rfind("}")
            if start == -1 or end == -1:
                continue
            snippet = text[start : end + 1]
            try:
                data = json.loads(snippet)
            except json.JSONDecodeError:
                continue
            postings = data.get("jobPostings", [])
            if not isinstance(postings, list):
                continue
            for item in postings:
                if not isinstance(item, dict):
                    continue
                title = compact(str(item.get("title", "")))
                url = anchor_url(source.careers_url, item.get("externalPath"))
                if not title or not url or url in seen_urls:
                    continue
                jobs.append(
                    RawJob(
                        source_id=source.id,
                        external_id=str(item.get("bulletFields", [None])[0] or "") or None,
                        url=url,
                        title=title,
                        location=compact(str(item.get("locationsText", ""))),
                        description=compact(str(item.get("description", ""))),
                        posted_at=parse_datetime(str(item.get("postedOn", ""))),
                    )
                )
                seen_urls.add(url)

        for anchor in soup.select("a[href*='workdayjobs.com'], a[href*='/job/']"):
            title = compact(anchor.get_text(" ", strip=True))
            url = anchor_url(source.careers_url, anchor.get("href"))
            if not title or not url or url in seen_urls:
                continue
            jobs.append(
                RawJob(
                    source_id=source.id,
                    external_id=None,
                    url=url,
                    title=title,
                    location="",
                    description="",
                    posted_at=None,
                )
            )
            seen_urls.add(url)

        return jobs
