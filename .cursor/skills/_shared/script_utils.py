"""Shared helpers for journaling skill scripts (load tokens from ``.env``)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

# Slack token env vars: SLACK_* (team convention) or journaling-specific name.
_TOKEN_VAR_PATTERN = re.compile(r"^(SLACK_[A-Z0-9_]{1,120}|JOURNALING_SLACK_BOT_TOKEN)$")


def validate_token_env_var(var_name: str) -> str:
    if not _TOKEN_VAR_PATTERN.fullmatch(var_name):
        sys.exit(
            "ERROR: --token-var must be SLACK_* or JOURNALING_SLACK_BOT_TOKEN.",
        )
    return var_name


def find_dotenv(start: Path | None = None) -> Path | None:
    """Search upward from ``start`` (or this file's directory) for a ``.env`` file."""

    current = (start or Path(__file__).resolve()).parent
    for parent in [current, *current.parents]:
        candidate = parent / ".env"
        if candidate.is_file():
            return candidate
    return None


def load_token(var_name: str) -> str:
    """Return token from environment or the first ``.env`` found upward."""

    validate_token_env_var(var_name)
    v = os.environ.get(var_name, "").strip()
    if v:
        return v

    env_path = find_dotenv()
    if env_path is None:
        sys.exit("ERROR: .env file not found in any parent directory (or set env var).")

    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == var_name and (val := value.strip().strip("'\"")):
            return val

    sys.exit(
        f"ERROR: {var_name} not found or empty in .env / environment (see --token-var).",
    )
