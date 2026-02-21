from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone

from app.logging_config import configure_logging
from app.pipeline import Pipeline
from app.settings import Settings

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run historical backfill by hour")
    parser.add_argument("--hours", type=int, required=True, help="How many trailing hours to replay")
    parser.add_argument("--notify", action="store_true", help="Send Telegram during backfill")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hours <= 0:
        print("--hours must be > 0")
        return 1

    configure_logging()
    settings = Settings.from_env()
    pipeline = Pipeline(settings)
    base = datetime.now(timezone.utc)

    for offset in range(args.hours - 1, -1, -1):
        run_at = base - timedelta(hours=offset)
        result = pipeline.run(run_at=run_at, notify=args.notify)
        logger.info(
            "backfill_run_complete",
            extra={
                "run_id": result.run_id,
                "run_at": run_at.isoformat(),
                "status": result.status,
            },
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
