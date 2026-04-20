"""Resolve user-supplied paths so file reads stay inside the journaling repository."""

from __future__ import annotations

import sys
from pathlib import Path

# Aligns with Slack ``chat.postMessage`` text limits (characters).
MAX_READ_BYTES_FOR_SLACK_POST = 1_000_000


def resolve_under_repo(repo_root: Path, user_path: str) -> Path:
    """Resolve ``user_path`` to an absolute path that must lie under ``repo_root``.

    Relative paths are interpreted relative to the repo root (not the process CWD),
    which blocks ``../`` escapes that depend on where the script was launched.
    """

    repo_r = repo_root.resolve()
    raw = Path(user_path).expanduser()
    resolved = (raw if raw.is_absolute() else (repo_r / raw)).resolve()
    try:
        resolved.relative_to(repo_r)
    except ValueError:
        sys.exit(
            "ERROR: file path must be inside the journaling repository "
            f"(refusing to read {user_path!r}).",
        )
    if not resolved.is_file():
        sys.exit(f"ERROR: not a file or missing: {resolved}")
    return resolved


def read_text_limited(path: Path, *, max_bytes: int) -> str:
    """Read UTF-8 text with a byte cap (avoid loading huge files into memory)."""

    data = path.read_bytes()
    if len(data) > max_bytes:
        sys.exit(
            f"ERROR: file too large ({len(data)} bytes); max {max_bytes} bytes.",
        )
    return data.decode("utf-8")


def resolve_write_path_under_repo(repo_root: Path, user_path: str) -> Path:
    """Resolve a path for writing; must stay under ``repo_root``."""

    repo_r = repo_root.resolve()
    raw = Path(user_path).expanduser()
    resolved = (raw if raw.is_absolute() else (repo_r / raw)).resolve()
    try:
        resolved.relative_to(repo_r)
    except ValueError:
        sys.exit(
            "ERROR: --output must be inside the journaling repository "
            f"(refusing to write {user_path!r}).",
        )
    return resolved
