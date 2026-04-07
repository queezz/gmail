"""Load and normalize messages from an mbox file."""

from __future__ import annotations

import email.header
from datetime import datetime, timezone
from email.message import Message
from email.utils import parsedate_to_datetime
from mailbox import mbox
from pathlib import Path

from bs4 import BeautifulSoup

_BODY_MAX_LEN = 5000


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, charset in email.header.decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(charset or "utf-8", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def _to_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _message_date_utc(msg: Message) -> datetime | None:
    raw = msg.get("Date")
    if not raw:
        return None
    try:
        return _to_utc(parsedate_to_datetime(raw))
    except (TypeError, ValueError, OverflowError):
        return None


def _html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def _decode_payload(part: Message) -> str:
    raw = part.get_payload(decode=True)
    if raw is None:
        return ""
    charset = part.get_content_charset() or "utf-8"
    if isinstance(raw, str):
        return raw
    return raw.decode(charset, errors="replace")


def _extract_body(msg: Message) -> str:
    if msg.is_multipart():
        plain_chunks: list[str] = []
        html_chunks: list[str] = []
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            disp = part.get_content_disposition() or ""
            if disp == "attachment":
                continue
            ctype = part.get_content_type()
            payload = _decode_payload(part)
            if ctype == "text/plain":
                plain_chunks.append(payload)
            elif ctype == "text/html":
                html_chunks.append(payload)
        if plain_chunks:
            text = "\n".join(plain_chunks)
        elif html_chunks:
            text = _html_to_text("\n".join(html_chunks))
        else:
            text = ""
    else:
        ctype = msg.get_content_type()
        payload = _decode_payload(msg)
        if ctype == "text/html":
            text = _html_to_text(payload)
        else:
            text = payload
    return text[:_BODY_MAX_LEN]


def load_emails(
    mbox_path: Path,
    *,
    since: datetime | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Read mbox_path into dicts with subject, from, date, body.

    If since is set, skip messages with missing Date or date strictly before since (UTC).
    If limit is set, stop after that many messages pass filters.
    """
    if since is not None:
        since = _to_utc(since)

    out: list[dict] = []
    box = mbox(str(mbox_path), create=False)
    try:
        for msg in box:
            if since is not None:
                md = _message_date_utc(msg)
                if md is None or md < since:
                    continue

            subject = _decode_header(msg.get("Subject"))
            from_ = _decode_header(msg.get("From"))
            date = _decode_header(msg.get("Date"))
            body = _extract_body(msg)
            out.append({"subject": subject, "from": from_, "date": date, "body": body})

            if limit is not None and len(out) >= limit:
                break
    finally:
        box.close()

    return out
