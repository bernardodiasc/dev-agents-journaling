"""Resolve user-supplied paths so file reads stay inside the journaling repository."""

from __future__ import annotations

import sys
import tempfile
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

    # Check for symlink escapes
    if resolved.is_symlink():
        sys.exit(f"ERROR: refusing to follow symlink: {resolved}")

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
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as e:
        sys.exit(f"ERROR: file is not valid UTF-8: {e}")


def resolve_write_path_under_repo(repo_root: Path, user_path: str) -> Path:
    """Resolve a path for writing; must stay under ``repo_root``."""

    repo_r = repo_root.resolve()
    raw = Path(user_path).expanduser()
    resolved = (raw if raw.is_absolute() else (repo_r / raw)).resolve()

    # Check for symlink escapes (check parent too for write operations)
    if resolved.exists() and resolved.is_symlink():
        sys.exit(f"ERROR: refusing to write to symlink: {resolved}")

    try:
        resolved.relative_to(repo_r)
    except ValueError:
        sys.exit(
            "ERROR: --output must be inside the journaling repository "
            f"(refusing to write {user_path!r}).",
        )
    return resolved


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> None:
    """Write text atomically using temp file and rename (prevents corruption on interrupt)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        dir=path.parent,
        delete=False,
    ) as tmp:
        try:
            tmp.write(text)
            tmp.flush()
            tmp_path = Path(tmp.name)
        except (OSError, IOError) as e:
            try:
                tmp_path.unlink()
            except OSError:
                pass
            sys.exit(f"ERROR: failed to write temp file: {e}")

    try:
        tmp_path.replace(path)
    except OSError as e:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        sys.exit(f"ERROR: failed to finalize write to {path}: {e}")
