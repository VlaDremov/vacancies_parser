from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.types import SourceConfig


def build_additional_page_urls(source: SourceConfig) -> list[str]:
    pagination = source.extra.get("pagination")
    if not isinstance(pagination, dict):
        return []

    strategy = str(pagination.get("strategy", "")).strip().lower()
    if strategy in {"query_param", "attrax_page_query"}:
        return _build_query_param_urls(source, pagination)
    if strategy == "offset_limit":
        return _build_offset_limit_urls(source, pagination)
    return []


def _build_query_param_urls(source: SourceConfig, pagination: dict) -> list[str]:
    max_pages = _read_int(pagination.get("max_pages"), default=1, minimum=1)
    if max_pages <= 1:
        return []

    start_page = _read_int(pagination.get("start_page"), default=1, minimum=1)
    page_param = str(pagination.get("page_param", "page")).strip() or "page"
    base_url = str(pagination.get("base_url", source.careers_url)).strip() or source.careers_url
    template = str(pagination.get("url_template", "")).strip()

    urls: list[str] = []
    for page in range(start_page + 1, start_page + max_pages):
        if template:
            try:
                candidate = template.format(page=page)
            except Exception:
                continue
        else:
            candidate = _replace_query_params(base_url, {page_param: str(page)})
        if candidate:
            urls.append(candidate)

    return _dedupe_urls(urls, excluded={source.careers_url})


def _build_offset_limit_urls(source: SourceConfig, pagination: dict) -> list[str]:
    max_pages = _read_int(pagination.get("max_pages"), default=1, minimum=1)
    if max_pages <= 1:
        return []

    limit = _read_int(pagination.get("limit"), default=15, minimum=1)
    start_offset = _read_int(pagination.get("start_offset"), default=0, minimum=0)
    base_url = str(pagination.get("base_url", source.careers_url)).strip() or source.careers_url
    template = str(pagination.get("url_template", "")).strip()

    urls: list[str] = []
    for index in range(1, max_pages):
        offset = start_offset + index * limit
        if template:
            try:
                candidate = template.format(offset=offset, limit=limit, page=index + 1)
            except Exception:
                continue
        else:
            candidate = _replace_query_params(base_url, {"offset": str(offset), "limit": str(limit)})
        if candidate:
            urls.append(candidate)

    return _dedupe_urls(urls, excluded={source.careers_url})


def _replace_query_params(url: str, params: dict[str, str]) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(params)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _dedupe_urls(urls: list[str], excluded: set[str]) -> list[str]:
    seen = set(excluded)
    deduped: list[str] = []
    for url in urls:
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _read_int(value: object, default: int, minimum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, parsed)
