"""Render a Markdown report or plan file into its Slack-mrkdwn sibling ``.slack.txt``.

Called by ``post_slack_message.py`` just before posting. The produced ``.slack.txt`` is
left on disk as a *receipt* — its existence means the ``.md`` was delivered to Slack.

Conversion rules (Slack mrkdwn, not GitHub Markdown):
  - ``#``/``##``/``###`` headings  → ``*text*`` on its own line (inner ``**`` / ``__`` stripped first)
  - ``[label](url)``               → ``<url|label>`` (before bold / bare URL)
  - Bare GitHub PR/issue URLs      → ``<url|repo#123>`` (short, clickable label)
  - Bare GitHub commit URLs        → ``<url|repo@abc1234>``
  - Other bare URLs                → ``<url>`` (before ``**`` → ``*`` so ``**https://…**`` does not break)
  - ``**bold**``                   → ``*bold*``
  - ``__bold__``                   → ``*bold*``
  - ``- item`` bullets             → unchanged (Slack renders these fine)
  - Code fences                    → unchanged (Slack renders ``` blocks)
  - Italic (``_x_``), strike (``~x~``), inline code (`````x`````)  → unchanged
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
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
# Do not treat a trailing * as part of the URL (e.g. after **url** → *url*).
_BARE_URL = re.compile(r"(?<![<\w/|])https?://[^\s<>)`]+(?<!\*)")
_GITHUB_ITEM = re.compile(
    r"^https://github\.com/[\w.-]+/([\w.-]+)/(?:pull|issues)/(\d+)(?:[/?#][^\s]*)?$"
)
_GITHUB_COMMIT = re.compile(
    r"^https://github\.com/[\w.-]+/([\w.-]+)/commit/([0-9a-fA-F]{7,40})(?:[/?#][^\s]*)?$"
)
_TRAILING_PUNCT = ".,;:!?"
_INLINE_CODE = re.compile(r"(`[^`]*`)")


def _bare_url_to_slack(match: re.Match) -> str:
    """``https://github.com/o/repo/pull/12`` → ``<…|repo#12>``; other URLs → ``<url>``.

    Trailing sentence punctuation is kept outside the link.
    """

    url = match.group(0)
    tail = ""
    while url and url[-1] in _TRAILING_PUNCT:
        tail = url[-1] + tail
        url = url[:-1]
    gh = _GITHUB_ITEM.match(url)
    if gh:
        return f"<{url}|{gh.group(1)}#{gh.group(2)}>{tail}"
    commit = _GITHUB_COMMIT.match(url)
    if commit:
        return f"<{url}|{commit.group(1)}@{commit.group(2)[:7].lower()}>{tail}"
    return f"<{url}>{tail}"


def _outside_inline_code(line: str, fn) -> str:
    parts = _INLINE_CODE.split(line)
    return "".join(p if p.startswith("`") and p.endswith("`") and len(p) > 1 else fn(p) for p in parts)


def slackify_links(text: str) -> str:
    """Label bare URLs in text that is *already* Slack mrkdwn (e.g. a status update draft).

    Existing ``<url|label>`` links, code fences and inline code are left untouched, so
    running this twice is a no-op. Used by ``post_slack_message.py`` for inline / stdin
    messages so a paste-friendly draft (bare URLs) posts with tidy ``repo#123`` labels.
    """

    out: list[str] = []
    in_code = False
    for raw in text.splitlines():
        if raw.lstrip().startswith("```"):
            in_code = not in_code
            out.append(raw)
            continue
        out.append(raw if in_code else _outside_inline_code(raw, lambda s: _BARE_URL.sub(_bare_url_to_slack, s)))
    return "\n".join(out)


def _heading_plain_title(raw_title: str) -> str:
    """Strip GitHub-style bold/underline from heading text before wrapping in Slack *…*."""
    t = raw_title.strip()
    t = _BOLD_STAR.sub(r"\1", t)
    t = _BOLD_UNDER.sub(r"\1", t)
    return t.strip()


def _convert_line(line: str, *, in_code: bool) -> str:
    if in_code:
        return line
    m = _HEADING.match(line)
    if m:
        inner = _heading_plain_title(m.group(2))
        return f"*{inner}*"
    line = _MD_LINK.sub(lambda mo: f"<{mo.group(2)}|{mo.group(1)}>", line)
    line = _BARE_URL.sub(_bare_url_to_slack, line)
    line = _BOLD_STAR.sub(r"*\1*", line)
    line = _BOLD_UNDER.sub(r"*\1*", line)
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
