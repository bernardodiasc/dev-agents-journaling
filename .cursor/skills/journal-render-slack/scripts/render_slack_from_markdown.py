"""Render a Markdown report or plan file into its Slack-mrkdwn sibling ``.slack.txt``.

Called by ``journal-post-slack`` just before posting. The produced ``.slack.txt`` is
left on disk as a *receipt* — its existence means the ``.md`` was delivered to Slack.

Conversion rules (Slack mrkdwn, not GitHub Markdown):
  - ``#``/``##``/``###`` headings  → ``*text*`` on its own line
  - ``**bold**``                   → ``*bold*``
  - ``__bold__``                   → ``*bold*``
  - ``[label](url)``               → ``<url|label>``
  - Bare URLs                      → ``<url>``
  - ``- item`` bullets             → unchanged (Slack renders these fine)
  - Code fences                    → unchanged (Slack renders ``` blocks)
  - Italic (``_x_``), strike (``~x~``), inline code (`````x`````)  → unchanged
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import (
    MAX_READ_BYTES_FOR_SLACK_POST,
    read_text_limited,
    resolve_under_repo,
    resolve_write_path_under_repo,
    atomic_write_text,
)

_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
_MD_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
_BOLD_STAR = re.compile(r"\*\*(.+?)\*\*")
_BOLD_UNDER = re.compile(r"__(.+?)__")
_BARE_URL = re.compile(r"(?<![<\w/|])https?://[^\s<>)]+")


def _convert_line(line: str, *, in_code: bool) -> str:
    if in_code:
        return line
    m = _HEADING.match(line)
    if m:
        return f"*{m.group(2).strip()}*"
    line = _MD_LINK.sub(lambda mo: f"<{mo.group(2)}|{mo.group(1)}>", line)
    line = _BOLD_STAR.sub(r"*\1*", line)
    line = _BOLD_UNDER.sub(r"*\1*", line)
    line = _BARE_URL.sub(lambda mo: f"<{mo.group(0)}>", line)
    return line


def render_markdown_to_slack(md_text: str) -> str:
    """Public helper used by ``post_slack_message.py`` to render in-process."""

    out: list[str] = []
    in_code = False
    for raw in md_text.splitlines():
        if raw.lstrip().startswith("```"):
            in_code = not in_code
            out.append(raw)
            continue
        out.append(_convert_line(raw, in_code=in_code))
    text = "\n".join(out)
    # Collapse >2 blank lines (Slack renders each blank line as a gap).
    return re.sub(r"\n{3,}", "\n\n", text)


def _default_sibling(path: Path) -> Path:
    return path.with_suffix(".slack.txt")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render a Markdown plan/report into its Slack-mrkdwn sibling (.slack.txt).",
    )
    parser.add_argument(
        "source",
        help="Path to the Markdown file inside this repo (e.g. reports/report-manager-…md).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Override output path (default: <source>.slack.txt sibling).",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the rendered Slack text to stdout instead of writing a file.",
    )
    args = parser.parse_args()

    repo = find_journaling_repo_root(Path(__file__))
    src = resolve_under_repo(repo, args.source)
    if src.suffix.lower() != ".md":
        sys.exit(f"ERROR: expected a .md file, got {src.suffix!r}.")

    md_text = read_text_limited(src, max_bytes=MAX_READ_BYTES_FOR_SLACK_POST)
    slack_text = render_markdown_to_slack(md_text)

    if args.stdout:
        print(slack_text)
        return

    target = (
        resolve_write_path_under_repo(repo, args.output)
        if args.output
        else _default_sibling(src)
    )
    atomic_write_text(target, slack_text)
    print(f"Rendered {src.relative_to(repo)} → {target.relative_to(repo)}")


if __name__ == "__main__":
    main()
