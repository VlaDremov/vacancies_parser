from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import yaml

from app.types import SourceConfig

REQUIRED_KEYS = {"id", "company_name", "careers_url", "parser_type"}


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

    return SourceConfig(
        id=str(data["id"]).strip(),
        company_name=str(data["company_name"]).strip(),
        careers_url=str(data["careers_url"]).strip(),
        parser_type=str(data["parser_type"]).strip(),
        country_hint=(str(data["country_hint"]).strip() if data.get("country_hint") else None),
        enabled=bool(data.get("enabled", True)),
        selectors=dict(data.get("selectors", {})),
        extra={k: v for k, v in data.items() if k not in REQUIRED_KEYS | {"country_hint", "enabled", "selectors"}},
    )


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
