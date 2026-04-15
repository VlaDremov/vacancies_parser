from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

import yaml

from app.parsers import PARSER_REGISTRY
from app.types import SourceConfig

REQUIRED_KEYS = {"id", "company_name", "careers_url", "parser_type"}
KNOWN_SELECTOR_KEYS = {"job_card", "title", "link", "location", "description", "posted_at", "external_id"}
PARSER_OPTION_KEYS = {
    "generic_html": set(),
    "generic_json": {"jobs_path", "fields"},
    "greenhouse": set(),
    "lever": set(),
    "smartrecruiters": set(),
    "teamtailor": set(),
    "workable": set(),
    "workday": set(),
}


def _load_raw_config(path: Path) -> dict:
    if path.suffix.lower() in {".yaml", ".yml"}:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    raise ValueError(f"Unsupported config file extension: {path}")


def _to_source_config(data: dict, path: Path) -> SourceConfig:
    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ValueError(f"Missing required keys in {path}: {sorted(missing)}")

    selectors = _normalize_mapping(data.get("selectors"), field_name="selectors", path=path) or {}
    pagination = _normalize_pagination(data.get("pagination"), path=path)
    parser_options = _normalize_mapping(data.get("parser_options"), field_name="parser_options", path=path)
    matching_profile = _normalize_mapping(data.get("matching_profile"), field_name="matching_profile", path=path)
    job_url_template = _normalize_job_url_template(data)

    source = SourceConfig(
        id=str(data["id"]).strip(),
        company_name=str(data["company_name"]).strip(),
        careers_url=str(data["careers_url"]).strip(),
        parser_type=str(data["parser_type"]).strip(),
        country_hint=(str(data["country_hint"]).strip() if data.get("country_hint") else None),
        enabled=bool(data.get("enabled", True)),
        selectors=selectors,
        pagination=pagination,
        parser_options=parser_options,
        matching_profile=matching_profile,
        job_url_template=job_url_template,
        extra={
            k: v
            for k, v in data.items()
            if k
            not in REQUIRED_KEYS
            | {
                "country_hint",
                "enabled",
                "selectors",
                "pagination",
                "parser_options",
                "matching_profile",
                "job_url_template",
                "json_job_url_template",
            }
        },
    )
    errors, _warnings = validate_source_config(source)
    if errors:
        raise ValueError(f"Invalid config in {path}: {'; '.join(errors)}")
    return source


def iter_source_configs(source_config_dir: str) -> Iterable[SourceConfig]:
    config_root = Path(source_config_dir)
    if not config_root.exists():
        return []

    configs: list[SourceConfig] = []
    seen_ids: set[str] = set()
    for path in sorted(config_root.glob("*")):
        if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
            continue
        raw = _load_raw_config(path)
        source = _to_source_config(raw, path)
        if source.id in seen_ids:
            raise ValueError(f"Duplicate source id '{source.id}' in {path}")
        seen_ids.add(source.id)
        configs.append(source)
    return configs


def validate_source_config(source: SourceConfig) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    if source.parser_type not in PARSER_REGISTRY:
        errors.append(f"unknown parser type '{source.parser_type}'")
        return errors, warnings

    if not source.careers_url.startswith("http"):
        errors.append("careers_url must be absolute URL")

    if source.parser_type == "generic_json":
        parser_options = source.parser_options or {}
        jobs_path = parser_options.get("jobs_path")
        fields = parser_options.get("fields")
        if not jobs_path or not isinstance(jobs_path, str):
            errors.append("generic_json requires parser_options.jobs_path")
        if not isinstance(fields, dict):
            errors.append("generic_json requires parser_options.fields")
        else:
            if not fields.get("title"):
                errors.append("generic_json requires parser_options.fields.title")
            if not fields.get("url") and not source.job_url_template:
                errors.append("generic_json requires parser_options.fields.url or job_url_template")

    if source.pagination:
        pagination_errors = _validate_pagination_config(source.pagination)
        errors.extend(pagination_errors)

    unknown_selectors = sorted(set(source.selectors) - KNOWN_SELECTOR_KEYS)
    if unknown_selectors:
        warnings.append(f"unknown selector keys: {', '.join(unknown_selectors)}")

    supported_options = PARSER_OPTION_KEYS.get(source.parser_type)
    if supported_options is not None and source.parser_options:
        unknown_options = sorted(set(source.parser_options) - supported_options)
        if unknown_options:
            warnings.append(f"unsupported parser_options: {', '.join(unknown_options)}")

    return errors, warnings


def _normalize_mapping(value: object, field_name: str, path: Path) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object in {path}")
    return dict(value)


def _normalize_pagination(value: object, path: Path) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"pagination must be an object in {path}")
    pagination = dict(value)
    errors = _validate_pagination_config(pagination)
    if errors:
        raise ValueError(f"pagination invalid in {path}: {'; '.join(errors)}")
    return pagination


def _validate_pagination_config(pagination: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    strategy = str(pagination.get("strategy", "")).strip().lower()
    if strategy not in {"query_param", "attrax_page_query", "offset_limit"}:
        errors.append("pagination.strategy must be one of query_param, attrax_page_query, offset_limit")

    max_pages = _try_int(pagination.get("max_pages"))
    if max_pages is None or max_pages < 1:
        errors.append("pagination.max_pages must be an integer >= 1")

    if strategy in {"query_param", "attrax_page_query"}:
        start_page = _try_int(pagination.get("start_page", 1))
        if start_page is None or start_page < 1:
            errors.append("pagination.start_page must be an integer >= 1")

    if strategy == "offset_limit":
        limit = _try_int(pagination.get("limit", 15))
        start_offset = _try_int(pagination.get("start_offset", 0))
        if limit is None or limit < 1:
            errors.append("pagination.limit must be an integer >= 1")
        if start_offset is None or start_offset < 0:
            errors.append("pagination.start_offset must be an integer >= 0")

    return errors


def _normalize_job_url_template(data: dict[str, Any]) -> str | None:
    raw = data.get("job_url_template", data.get("json_job_url_template"))
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _try_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
