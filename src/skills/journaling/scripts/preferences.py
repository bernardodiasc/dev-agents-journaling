"""Read or set one key in ``context/preferences.md`` in the journaling home.

Preferences are ``- Key: value`` lines. ``--set`` replaces that one key's line (or
appends it) and leaves every other line as it was. Resolving the home like the other
scripts lets a session in a git worktree update the main checkout's preferences.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import atomic_write_text, read_text_limited

_REL_PATH = Path("context") / "preferences.md"
_HEADER = "# Journaling preferences (gitignored; never commit)\n"
_LINE = re.compile(r"^- ([^:]+):\s*(.*)$")


def _parse(text: str) -> dict[str, str]:
    prefs: dict[str, str] = {}
    for line in text.splitlines():
        m = _LINE.match(line)
        if m:
            prefs[m.group(1).strip()] = m.group(2).strip()
    return prefs


def _find(prefs: dict[str, str], key: str) -> str | None:
    return next((k for k in prefs if k.casefold() == key.casefold()), None)


def set_value(text: str, key: str, value: str) -> str:
    """Return ``text`` with ``key`` set to ``value``; other lines are untouched."""

    lines = text.splitlines()
    for i, line in enumerate(lines):
        m = _LINE.match(line)
        if m and m.group(1).strip().casefold() == key.casefold():
            lines[i] = f"- {m.group(1).strip()}: {value}"  # keep the file's spelling
            return "\n".join(lines) + "\n"
    if not lines:
        lines = [_HEADER.rstrip("\n")]
    return "\n".join([*lines, f"- {key}: {value}"]) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Read or set a key in context/preferences.md")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--get", metavar="KEY", help="Print one key's value (exit 1 if missing)")
    g.add_argument("--set", nargs=2, metavar=("KEY", "VALUE"), help="Set one key, keep the rest")
    args = ap.parse_args()

    path = find_journaling_repo_root(Path(__file__)) / _REL_PATH
    text = read_text_limited(path, max_bytes=200_000) if path.is_file() else ""

    if args.set:
        key, value = (s.strip() for s in args.set)
        if not key or ":" in key or "\n" in key or "\n" in value:
            sys.exit("ERROR: KEY must be non-empty without ':' or newlines; VALUE must be one line")
        atomic_write_text(path, set_value(text, key, value))
        print(f"Set {key!r} in {_REL_PATH}")
        return

    prefs = _parse(text)
    if args.get:
        k = _find(prefs, args.get)
        if k is None:
            sys.exit(1)
        print(prefs[k])
        return
    if text:
        print(text, end="")
    else:
        print(f"No {_REL_PATH} yet.")


if __name__ == "__main__":
    main()
