"""Deprecated alias for ``save_context.py`` (kept so older commands still work)."""

import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "save_context.py"), run_name="__main__")
