import json

import pytest

from app.source_loader import iter_source_configs, validate_source_config
from app.types import SourceConfig


def test_source_loader_keeps_backward_compatible_generic_config(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    payload = {
        "id": "legacy",
        "company_name": "Legacy Co",
        "careers_url": "https://example.com/careers",
        "parser_type": "generic_html",
        "selectors": {"job_card": ".job-card", "title": "a"},
        "pagination": {"strategy": "query_param", "max_pages": 2, "page_param": "page"},
        "json_job_url_template": "https://example.com/jobs/{id}-{slug}",
    }
    (source_dir / "legacy.json").write_text(json.dumps(payload), encoding="utf-8")

    sources = list(iter_source_configs(str(source_dir)))

    assert len(sources) == 1
    assert sources[0].pagination == payload["pagination"]
    assert sources[0].job_url_template == "https://example.com/jobs/{id}-{slug}"


def test_source_loader_validates_generic_json_requirements(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir()
    payload = {
        "id": "json-api",
        "company_name": "JSON API Co",
        "careers_url": "https://api.example.com/jobs",
        "parser_type": "generic_json",
        "parser_options": {"jobs_path": "jobs.items", "fields": {"title": "title"}},
    }
    (source_dir / "invalid.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError):
        list(iter_source_configs(str(source_dir)))


def test_validate_source_config_returns_warnings_for_unknown_keys():
    source = SourceConfig(
        id="warn",
        company_name="Warn Co",
        careers_url="https://example.com/jobs",
        parser_type="generic_html",
        selectors={"job_card": ".job", "mystery": ".x"},
        parser_options={"jobs_path": "data"},
    )

    errors, warnings = validate_source_config(source)
    assert not errors
    assert any("unknown selector keys" in warning for warning in warnings)
    assert any("unsupported parser_options" in warning for warning in warnings)
