"""Locate the journaling repository root (directory containing ``journaling-repo.mdc``)."""

from __future__ import annotations

import sys
from pathlib import Path

def find_journaling_repo_root(start: Path | None = None) -> Path:
    """Return resolved repo root, or exit with an error."""

    anchor = start if start is not None else Path(__file__)
    here = anchor.resolve()
    marker = Path(".cursor") / "rules" / "journaling-repo.mdc"
    for p in [here, *here.parents]:
        if (p / marker).is_file():
            root = p.resolve()
            for d in ("entries", "reports", "plans", "context"):
                (root / d).mkdir(parents=True, exist_ok=True)
            return root
    sys.exit(
        "ERROR: journaling repo root not found "
        "(expected .cursor/rules/journaling-repo.mdc in a parent directory).",
    )
