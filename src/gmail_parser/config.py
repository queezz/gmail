"""Paths and defaults for the gmail-parser pipeline."""

from __future__ import annotations

import os
from pathlib import Path

MBOX_PATH = Path.home() / "Dropbox" / "email_dump" / "mail.mbox"
OUTPUT_PATH = Path("data") / "emails.csv"
CACHE_PATH = Path("data") / "cache.json"

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.3")

# Bump when prompts / response shape / cache key strategy changes.
CACHE_SCHEMA_VERSION = 1
