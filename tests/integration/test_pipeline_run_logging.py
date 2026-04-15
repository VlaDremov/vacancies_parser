import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

from app.db import Run, Source, build_session_factory
from app.fetcher import FetchError, FetchResult
from app.pipeline import Pipeline
from app.settings import Settings
from app.types import RawJob, SourceConfig

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "parsers"


def test_pipeline_logs_partial_failure(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir(parents=True)

    (source_dir / "good.json").write_text(
        """
        {
          "id": "good",
          "company_name": "GoodCo",
          "careers_url": "https://example.com/good",
          "parser_type": "generic_html",
          "enabled": true
        }
        """,
        encoding="utf-8",
    )
    (source_dir / "bad.json").write_text(
        """
        {
          "id": "bad",
          "company_name": "BadCo",
          "careers_url": "https://example.com/bad",
          "parser_type": "generic_html",
          "enabled": true
        }
        """,
        encoding="utf-8",
    )

    db_url = f"sqlite:///{tmp_path / 'pipeline.sqlite'}"
    settings = Settings(
        database_url=db_url,
        telegram_bot_token="",
        telegram_chat_id="",
        run_timezone="UTC",
        min_match_score=0.62,
        max_items_per_digest=20,
        dedupe_days=7,
        max_fetch_retries=1,
        fetch_timeout_seconds=5,
        run_timeout_minutes=40,
        source_config_dir=str(source_dir),
        enable_remote_eu=False,
    )

    pipeline = Pipeline(settings)

    def fake_fetch_and_parse(source: SourceConfig):
        if source.id == "bad":
            raise FetchError("boom")
        return [
            RawJob(
                source_id="good",
                external_id="1",
                url="https://example.com/good/jobs/1",
                title="Machine Learning Engineer",
                location="London, UK",
                description="build ML systems",
                posted_at=None,
            )
        ]

    pipeline._fetch_and_parse = fake_fetch_and_parse  # type: ignore[attr-defined]

    result = pipeline.run(run_at=datetime.now(timezone.utc), notify=False)
    assert result.status == "partial_failure"
    assert "bad" in result.errors

    session_factory = build_session_factory(db_url)
    with session_factory() as session:
        run_row = session.scalar(select(Run).order_by(Run.id.desc()).limit(1))
        assert run_row is not None
        assert run_row.status == "partial_failure"
        assert run_row.error_summary is not None
        payload = json.loads(run_row.error_summary)
        assert payload["bad"]

        sources = list(session.scalars(select(Source)))
        assert {source.id for source in sources} == {"good", "bad"}


def test_pipeline_handles_mixed_source_types_end_to_end(tmp_path):
    source_dir = tmp_path / "sources"
    source_dir.mkdir(parents=True)

    (source_dir / "smartrecruiters.json").write_text(
        """
        {
          "id": "smart",
          "company_name": "SmartCo",
          "careers_url": "https://jobs.smartrecruiters.com/Example",
          "parser_type": "smartrecruiters",
          "enabled": true
        }
        """,
        encoding="utf-8",
    )
    (source_dir / "generic_json.json").write_text(
        """
        {
          "id": "jsonapi",
          "company_name": "JsonCo",
          "careers_url": "https://api.example.com/jobs",
          "parser_type": "generic_json",
          "enabled": true,
          "parser_options": {
            "jobs_path": "jobs.items",
            "fields": {
              "title": "jobTitle",
              "url": "jobUrl",
              "external_id": "jobId",
              "location": "meta.location",
              "description": "details.summary",
              "posted_at": "meta.publishedAt"
            }
          }
        }
        """,
        encoding="utf-8",
    )

    db_url = f"sqlite:///{tmp_path / 'mixed.sqlite'}"
    settings = Settings(
        database_url=db_url,
        telegram_bot_token="",
        telegram_chat_id="",
        run_timezone="UTC",
        min_match_score=0.55,
        max_items_per_digest=20,
        dedupe_days=7,
        max_fetch_retries=1,
        fetch_timeout_seconds=5,
        run_timeout_minutes=40,
        source_config_dir=str(source_dir),
        enable_remote_eu=True,
    )

    pipeline = Pipeline(settings)
    smart_content = (FIXTURES / "smartrecruiters.json").read_text(encoding="utf-8")
    generic_json_content = (FIXTURES / "generic_json.json").read_text(encoding="utf-8")

    def fake_fetch_http(source: SourceConfig, url: str | None = None):
        target = url or source.careers_url
        if source.id == "smart":
            return FetchResult(
                content=smart_content,
                final_url=target,
                status_code=200,
                used_playwright=False,
                blocked_reason=None,
            )
        return FetchResult(
            content=generic_json_content,
            final_url=target,
            status_code=200,
            used_playwright=False,
            blocked_reason=None,
        )

    pipeline.fetcher.fetch_http = fake_fetch_http  # type: ignore[method-assign]
    pipeline.fetcher.fetch_playwright = fake_fetch_http  # type: ignore[method-assign]

    result = pipeline.run(run_at=datetime.now(timezone.utc), notify=False)

    assert result.status == "success"
    assert result.jobs_fetched == 2
    assert result.jobs_matched == 2
