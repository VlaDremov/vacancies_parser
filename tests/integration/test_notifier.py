from datetime import datetime, timezone

from app.notifier import build_digest_message, build_run_summary_message
from app.types import DigestItem, SourceRunSummary


def test_digest_payload_formatting_and_truncation():
    items = [
        DigestItem(
            vacancy_id=1,
            company="Company",
            title="Machine Learning Engineer",
            location="London, UK",
            url="https://example.com/jobs/1",
            score=0.9,
            posted_at=None,
        )
    ]

    message = build_digest_message(
        items=items,
        run_at=datetime(2026, 2, 17, 12, 0, tzinfo=timezone.utc),
        sources_total=10,
        matched_total=4,
    )

    assert "ML Vacancy Digest" in message
    assert "Company | Machine Learning Engineer" in message
    assert "Sources scanned: 10" in message
    assert len(message) < 4096


def test_run_summary_message_includes_counts_and_errors():
    summaries = [
        SourceRunSummary(
            source_id="trivago",
            company_name="trivago",
            careers_url="https://careers.trivago.com/jobs/",
            jobs_fetched=7,
        ),
        SourceRunSummary(
            source_id="sap",
            company_name="SAP",
            careers_url="https://jobs.sap.com/search/",
            jobs_fetched=400,
        ),
        SourceRunSummary(
            source_id="zalando",
            company_name="Zalando",
            careers_url="https://jobs.zalando.com/",
            jobs_fetched=0,
            error="timeout after 20s",
        ),
    ]

    message = build_run_summary_message(
        summaries=summaries,
        run_at=datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc),
        run_timezone="UTC",
    )

    assert "Scrape Summary" in message
    assert "Vacancies scraped: 407 across 2/3 sources" in message
    assert "- SAP: 400" in message
    assert "- trivago: 7" in message
    assert "Errored sources (1):" in message
    assert "Zalando (https://jobs.zalando.com/): timeout after 20s" in message
    assert message.index("- SAP: 400") < message.index("- trivago: 7")


def test_run_summary_message_without_errors():
    summaries = [
        SourceRunSummary(
            source_id="trivago",
            company_name="trivago",
            careers_url="https://careers.trivago.com/jobs/",
            jobs_fetched=7,
        )
    ]

    message = build_run_summary_message(
        summaries=summaries,
        run_at=datetime(2026, 4, 17, 12, 0, tzinfo=timezone.utc),
    )

    assert "Vacancies scraped: 7 across 1/1 sources" in message
    assert "Errored sources" not in message
