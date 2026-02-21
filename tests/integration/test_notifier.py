from datetime import datetime, timezone

from app.notifier import build_digest_message
from app.types import DigestItem


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
