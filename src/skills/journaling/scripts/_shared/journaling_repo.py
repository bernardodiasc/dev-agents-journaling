"""Locate the journaling *home*: the directory that holds journal data and ``.env``.

Resolution order (first match wins):

1. ``JOURNALING_HOME`` environment variable (explicit, works for packaged installs).
2. The git checkout that contains this skill. Scripts resolve their own path through
   symlinks, so ``~/.claude/skills/journaling -> <repo>/src/skills/journaling`` still
   finds ``<repo>`` — data and ``.env`` stay in the repo no matter where Claude runs.
3. ``~/.journaling`` (fallback for a copied/packaged skill with no repo around it).

The function name is kept for backwards compatibility with existing scripts.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

DATA_DIRS = ("entries", "reports", "plans", "context", "updates")
_MARKER = Path("src") / "skills" / "journaling" / "SKILL.md"


def _resolve_home(anchor: Path) -> Path:
    env_home = os.environ.get("JOURNALING_HOME", "").strip()
    if env_home:
        return Path(env_home).expanduser().resolve()
    here = anchor.resolve()
    for p in [here, *here.parents]:
        if (p / _MARKER).is_file():
            return p
    return (Path.home() / ".journaling").resolve()


def find_journaling_repo_root(start: Path | None = None) -> Path:
    """Return the resolved journaling home, creating the data directories if needed."""

    root = _resolve_home(start if start is not None else Path(__file__))
    try:
        for d in DATA_DIRS:
            (root / d).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        sys.exit(f"ERROR: cannot create journaling data dirs under {root}: {e.strerror}")
    return root
