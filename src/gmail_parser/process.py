"""LLM processing with JSON file cache."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any

import pandas as pd
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from tqdm import tqdm

from gmail_parser import config

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SEC = 2.0

_SYSTEM_PROMPT = """You analyze email text. The user message is the email (subject and body combined).
1. Translate the content to English mentally; all output fields must be in English.
2. Produce exactly one JSON object with these keys:
   - "summary": string, concise summary of the email.
   - "action_required": boolean, true if the recipient should do something explicit.
   - "actions": array of strings, concrete action items (empty array if none).
   - "keywords": array of strings, short tag-like keywords.
No other keys. No markdown. No prose outside the JSON object."""


def _cache_key(combined: str) -> str:
    payload = f"{config.CACHE_SCHEMA_VERSION}\n{config.OPENAI_MODEL}\n{combined}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_cache() -> dict[str, Any]:
    path = config.CACHE_PATH
    if not path.is_file():
        return {"schema_version": config.CACHE_SCHEMA_VERSION, "entries": {}}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema_version": config.CACHE_SCHEMA_VERSION, "entries": {}}
    if data.get("schema_version") != config.CACHE_SCHEMA_VERSION:
        return {"schema_version": config.CACHE_SCHEMA_VERSION, "entries": {}}
    entries = data.get("entries")
    if not isinstance(entries, dict):
        entries = {}
    return {"schema_version": config.CACHE_SCHEMA_VERSION, "entries": entries}


def _save_cache(data: dict[str, Any]) -> None:
    config.CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    config.CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_llm_json(content: str) -> dict[str, Any]:
    data = json.loads(content)
    if not isinstance(data, dict):
        raise ValueError("expected JSON object")
    for key in ("summary", "action_required", "actions", "keywords"):
        if key not in data:
            raise ValueError(f"missing key {key!r}")
    if not isinstance(data["summary"], str):
        raise ValueError("summary must be a string")
    if not isinstance(data["action_required"], bool):
        raise ValueError("action_required must be a boolean")
    if not isinstance(data["actions"], list) or not all(isinstance(x, str) for x in data["actions"]):
        raise ValueError("actions must be a list of strings")
    if not isinstance(data["keywords"], list) or not all(
        isinstance(x, str) for x in data["keywords"]
    ):
        raise ValueError("keywords must be a list of strings")
    return data


def _call_openai(client: OpenAI, combined: str) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        try:
            resp = client.chat.completions.create(
                model=config.OPENAI_MODEL,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": combined},
                ],
            )
            content = resp.choices[0].message.content or ""
            return _parse_llm_json(content)
        except (
            APIError,
            APIConnectionError,
            APITimeoutError,
            RateLimitError,
            json.JSONDecodeError,
            ValueError,
            IndexError,
            KeyError,
        ) as e:
            last_err = e
            if attempt < _MAX_ATTEMPTS:
                time.sleep(_RETRY_DELAY_SEC)
    assert last_err is not None
    raise last_err


def process_emails(emails: list[dict]) -> pd.DataFrame:
    cache = _load_cache()
    entries: dict[str, Any] = cache["entries"]
    client = OpenAI()

    rows: list[dict] = []
    for item in tqdm(emails, desc="Processing emails"):
        combined = f"{item.get('subject', '')}\n\n{item.get('body', '')}"
        key = _cache_key(combined)
        if key in entries:
            processed = entries[key]
        else:
            processed = _call_openai(client, combined)
            entries[key] = processed
            cache["entries"] = entries
            _save_cache(cache)

        row = {
            **item,
            "summary": processed["summary"],
            "action_required": processed["action_required"],
            "actions_json": json.dumps(processed["actions"], ensure_ascii=False),
            "keywords_json": json.dumps(processed["keywords"], ensure_ascii=False),
        }
        rows.append(row)

    return pd.DataFrame(rows)
