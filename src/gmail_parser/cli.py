"""Command-line entrypoint for the mbox to LLM to CSV pipeline."""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone

from gmail_parser import config
from gmail_parser.parse_mbox import load_emails
from gmail_parser.process import process_emails


def _parse_since(value: str) -> datetime:
    s = value.strip()
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.strptime(s, "%Y-%m-%d")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Parse an mbox, summarize with OpenAI, write CSV.")
    parser.add_argument(
        "--since",
        type=str,
        default=None,
        help="Only include messages on or after this date/time (ISO-8601 or YYYY-MM-DD, UTC).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of messages to load after filters.",
    )
    args = parser.parse_args(argv)

    since = _parse_since(args.since) if args.since else None
    limit = args.limit

    print(f"Loading mbox: {config.MBOX_PATH}", flush=True)
    emails = load_emails(config.MBOX_PATH, since=since, limit=limit)
    print(f"Loaded {len(emails)} message(s).", flush=True)

    if not emails:
        print("No messages to process; exiting.", flush=True)
        return

    print("Processing with OpenAI...", flush=True)
    df = process_emails(emails)

    config.OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(config.OUTPUT_PATH, index=False)
    print(f"Wrote {config.OUTPUT_PATH}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
