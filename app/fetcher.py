from __future__ import annotations

import logging
import re
from dataclasses import dataclass

import httpx

from app.types import SourceConfig

logger = logging.getLogger(__name__)

BLOCKED_STATUS_CODES = {401, 403, 429, 503}
BLOCKED_TITLE_PATTERNS = [
    "attention required",
    "just a moment",
    "verify you are human",
    "access denied",
    "security check",
    "temporarily blocked",
]
BLOCKED_BODY_PATTERNS = [
    "cf-chl",
    "cf_chl",
    "cf-challenge",
    "ray id",
    "please enable javascript and cookies to continue",
    "request unsuccessful. incident id",
    "automated queries",
    "unusual traffic",
    "/cdn-cgi/challenge-platform/",
]
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


class FetchError(RuntimeError):
    pass


class BotBlockedError(FetchError):
    pass


@dataclass(frozen=True)
class FetchResult:
    content: str
    final_url: str
    status_code: int
    used_playwright: bool
    blocked_reason: str | None


class SourceFetcher:
    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_seconds = timeout_seconds

    def fetch_http(self, source: SourceConfig, url: str | None = None) -> FetchResult:
        target_url = url or source.careers_url
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
            )
        }
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=True, headers=headers) as client:
            response = client.get(target_url)
            response.raise_for_status()
            content = response.text
            return FetchResult(
                content=content,
                final_url=str(response.url),
                status_code=response.status_code,
                used_playwright=False,
                blocked_reason=_detect_blocked(content=content, status_code=response.status_code),
            )

    def fetch_playwright(self, source: SourceConfig, url: str | None = None) -> FetchResult:
        target_url = url or source.careers_url
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover
            raise FetchError("Playwright is not installed. Run `playwright install chromium`.") from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(target_url, timeout=self.timeout_seconds * 1000, wait_until="networkidle")
            content = page.content()
            final_url = page.url
            browser.close()

        return FetchResult(
            content=content,
            final_url=final_url,
            status_code=200,
            used_playwright=True,
            blocked_reason=_detect_blocked(content=content, status_code=200),
        )


def _detect_blocked(content: str, status_code: int) -> str | None:
    if status_code in BLOCKED_STATUS_CODES:
        return f"http_{status_code}"

    lowered = content.lower()

    title_match = TITLE_RE.search(content)
    title = title_match.group(1).strip().lower() if title_match else ""
    for pattern in BLOCKED_TITLE_PATTERNS:
        if pattern in title:
            return f"title:{pattern}"

    for pattern in BLOCKED_BODY_PATTERNS:
        if pattern in lowered:
            return pattern

    return None
