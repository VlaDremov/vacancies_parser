from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db import Notification, Source, Vacancy, build_session_factory, init_db
from app.store import is_suppressed


def test_dedupe_suppresses_vacancy_within_window(tmp_path):
    db_path = tmp_path / "dedupe.sqlite"
    db_url = f"sqlite:///{db_path}"
    init_db(db_url)
    session_factory = build_session_factory(db_url)

    now = datetime.now(timezone.utc)
    with session_factory() as session:
        source = Source(
            id="s1",
            company_name="Company",
            careers_url="https://example.com/careers",
            parser_type="generic_html",
            country_hint=None,
            selectors={},
            enabled=True,
            created_at=now,
            updated_at=now,
        )
        session.add(source)
        session.flush()

        vacancy = Vacancy(
            source_id="s1",
            canonical_hash="hash1",
            external_id="ext",
            url="https://example.com/jobs/1",
            title="Data Scientist",
            location="London",
            description="desc",
            posted_at=now,
            first_seen_at=now,
            last_seen_at=now,
        )
        session.add(vacancy)
        session.flush()

        session.add(
            Notification(
                vacancy_id=vacancy.id,
                channel="telegram",
                sent_at=now,
                dedupe_until=now + timedelta(days=7),
            )
        )
        session.commit()

    with session_factory() as session:
        vacancy_id = session.scalar(select(Vacancy.id).limit(1))
        assert vacancy_id is not None
        assert is_suppressed(session, vacancy_id=vacancy_id, channel="telegram", now=now) is True
        assert (
            is_suppressed(
                session,
                vacancy_id=vacancy_id,
                channel="telegram",
                now=now + timedelta(days=8),
            )
            is False
        )
