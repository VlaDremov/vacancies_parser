import json
from datetime import datetime, timezone

from sqlalchemy import select

from app.db import Run, Source, build_session_factory
from app.fetcher import FetchError
from app.pipeline import Pipeline
from app.settings import Settings
from app.types import RawJob, SourceConfig


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
