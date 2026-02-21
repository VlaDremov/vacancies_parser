from __future__ import annotations

import argparse
import fcntl
import logging
import signal
import sys
from datetime import datetime, timezone

from app.logging_config import configure_logging
from app.pipeline import Pipeline
from app.settings import Settings

logger = logging.getLogger(__name__)
LOCK_PATH = "/tmp/vacancies_parser.run.lock"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run vacancy scraper once")
    parser.add_argument("--no-notify", action="store_true", help="Do not send Telegram messages")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    configure_logging()
    settings = Settings.from_env()

    timeout_seconds = settings.run_timeout_minutes * 60

    def timeout_handler(_signum, _frame):
        raise TimeoutError(f"Run timed out after {settings.run_timeout_minutes} minutes")

    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(timeout_seconds)
    except (AttributeError, ValueError):
        logger.warning("timeout_signal_unavailable")

    lock_file = open(LOCK_PATH, "w", encoding="utf-8")
    try:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            logger.warning("run_skipped_lock_active")
            return 0

        pipeline = Pipeline(settings)
        result = pipeline.run(run_at=datetime.now(timezone.utc), notify=not args.no_notify)
        logger.info(
            "run_complete",
            extra={
                "run_id": result.run_id,
                "status": result.status,
                "sources_total": result.sources_total,
                "jobs_fetched": result.jobs_fetched,
                "jobs_matched": result.jobs_matched,
                "jobs_sent": result.jobs_sent,
            },
        )
        return 0
    except Exception:
        logger.exception("run_failed")
        return 1
    finally:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
        except OSError:
            pass
        lock_file.close()
        try:
            signal.alarm(0)
        except (AttributeError, ValueError):
            pass


if __name__ == "__main__":
    sys.exit(main())
