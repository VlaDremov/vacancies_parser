from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from app.types import DigestItem, SourceRunSummary


class NotifierError(RuntimeError):
    pass


def build_digest_message(
    items: list[DigestItem],
    run_at: datetime,
    sources_total: int,
    matched_total: int,
    run_timezone: str = "UTC",
) -> str:
    tz_label = run_timezone
    try:
        tz = ZoneInfo(run_timezone)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
        tz_label = "UTC"

    timestamp = run_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    lines = [f"ML Vacancy Digest | {timestamp}", f"New matched vacancies: {len(items)}", ""]

    max_chars = 3900
    truncated_count = 0
    for index, item in enumerate(items, start=1):
        location = item.location or "Unknown location"
        line = f"{index}. {item.company} | {item.title} | {location} | {item.url}"
        tentative = "\n".join(lines + [line])
        if len(tentative) > max_chars:
            truncated_count = len(items) - index + 1
            break
        lines.append(line)

    if truncated_count > 0:
        lines.append(f"...and {truncated_count} more matches were omitted due to Telegram length limits.")

    lines.extend(
        [
            "",
            f"Sources scanned: {sources_total} | Matched before dedupe: {matched_total} | Timezone: {tz_label}",
        ]
    )
    return "\n".join(lines)


def build_run_summary_message(
    summaries: list[SourceRunSummary],
    run_at: datetime,
    run_timezone: str = "UTC",
) -> str:
    tz_label = run_timezone
    try:
        tz = ZoneInfo(run_timezone)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
        tz_label = "UTC"

    timestamp = run_at.astimezone(tz).strftime("%Y-%m-%d %H:%M")
    successes = [summary for summary in summaries if summary.error is None]
    failures = [summary for summary in summaries if summary.error is not None]
    total_scraped = sum(summary.jobs_fetched for summary in successes)

    lines = [
        f"Scrape Summary | {timestamp} {tz_label}",
        f"Vacancies scraped: {total_scraped} across {len(successes)}/{len(summaries)} sources",
    ]

    if successes:
        lines.append("")
        lines.append("Per company:")
        sorted_successes = sorted(
            successes,
            key=lambda summary: (-summary.jobs_fetched, summary.company_name.lower()),
        )
        for summary in sorted_successes:
            lines.append(f"- {summary.company_name}: {summary.jobs_fetched}")

    if failures:
        lines.append("")
        lines.append(f"Errored sources ({len(failures)}):")
        for summary in failures:
            lines.append(f"- {summary.company_name} ({summary.careers_url}): {summary.error}")

    return _truncate_to_telegram_limit("\n".join(lines))


def _truncate_to_telegram_limit(text: str, max_chars: int = 3900) -> str:
    if len(text) <= max_chars:
        return text
    suffix = "\n...(truncated)"
    cutoff = max_chars - len(suffix)
    return text[:cutoff] + suffix


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    if not bot_token or not chat_id:
        raise NotifierError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    endpoint = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }

    with httpx.Client(timeout=15) as client:
        response = client.post(endpoint, json=payload)
        response.raise_for_status()
        data = response.json()

    if not data.get("ok"):
        raise NotifierError(f"Telegram API error: {data}")
