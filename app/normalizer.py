from __future__ import annotations

import hashlib
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from app.types import NormalizedVacancy, RawJob

WHITESPACE_RE = re.compile(r"\s+")
DROP_QUERY_PARAMS = {"gh_src", "lever-source", "source", "tracking"}


def _clean(text: str | None) -> str:
    if not text:
        return ""
    return WHITESPACE_RE.sub(" ", text).strip()


def _normalize_url(url: str) -> str:
    parts = urlsplit(url.strip())
    filtered_query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in DROP_QUERY_PARAMS
    ]
    normalized = urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), urlencode(filtered_query), "")
    )
    return normalized


def canonical_hash(source_id: str, external_id: str | None, url: str, title: str, location: str) -> str:
    token = "|".join(
        [
            source_id,
            external_id or "",
            _normalize_url(url),
            _clean(title).lower(),
            _clean(location).lower(),
        ]
    )
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_job(raw: RawJob, company: str, country_hint: str | None = None) -> NormalizedVacancy:
    title = _clean(raw.title)
    location = _clean(raw.location) or _clean(country_hint)
    description = _clean(raw.description)
    normalized_url = _normalize_url(raw.url)
    canonical_id = canonical_hash(raw.source_id, raw.external_id, normalized_url, title, location)

    return NormalizedVacancy(
        canonical_id=canonical_id,
        company=_clean(company),
        title=title,
        location=location,
        url=normalized_url,
        posted_at=raw.posted_at,
        description_text=description,
        source_id=raw.source_id,
        external_id=raw.external_id,
    )
