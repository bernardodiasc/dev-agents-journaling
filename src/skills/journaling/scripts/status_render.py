"""Render a status-update draft into (a) paste-ready text with live GitHub status tags
and (b) a Slack Block Kit payload for bot posts.

The draft is plain Slack mrkdwn with bare URLs (what Claude writes):

    *Status update · Thu Nov 12*
    Optional context paragraph…
    *In progress*
    • Sandbox MVP agents https://github.com/o/agents/pull/11 https://github.com/o/agents/pull/12

Every GitHub PR / issue / commit URL gets a status tag looked up live (see
``github_status.py``), e.g. ``🟢 approved``, ``🔵 open `wayfinder:map```, ``❌ CI``.
Existing tags are stripped first, so re-rendering an already-tagged draft refreshes
the statuses instead of duplicating them.

Usage:
    status_render.py < draft.txt                 # tagged paste text (bare URLs)
    status_render.py --blocks --context "Since Wed 11:34 · 1 merged" < draft.txt   # JSON payload
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from github_status import GITHUB_URL, ItemStatus, canonical, fetch_statuses, short_label  # noqa: E402
from render_slack_from_markdown import slackify_links  # noqa: E402

MAX_BLOCKS = 50
SECTION_MAX = 2900
HEADER_MAX = 150

_STATUS_WORDS = r"(?:approved|in review|changes requested|draft|merged|closed|open|not planned)"
_STATUS_EMOJI = r"(?:🟢|🟡|🔴|⚪|🟣|⚫|🔵|✅)"
_URL_WITH_TAG = re.compile(
    r"(?P<url>" + GITHUB_URL.pattern + r"[^\s<>)`]*)"
    r"(?P<tag>(?:[ \t]+" + _STATUS_EMOJI + r"[ \t]+" + _STATUS_WORDS + r")"
    r"(?:[ \t]+❌ CI)?(?:[ \t]+`[^`\n]+`)*|[ \t]+❌ CI(?:[ \t]+`[^`\n]+`)*)?"
)
_TITLE = re.compile(r"^\*([^*\n]+)\*\s*$")
_BULLET = re.compile(r"^\s*[•\-]\s+(.*)$")
_TRAILING_PUNCT = ".,;:!?"


def _split_url(raw: str) -> tuple[str, str]:
    tail = ""
    while raw and raw[-1] in _TRAILING_PUNCT:
        tail, raw = raw[-1] + tail, raw[:-1]
    return raw, tail


def github_urls(text: str) -> list[str]:
    return [_split_url(m.group("url"))[0] for m in _URL_WITH_TAG.finditer(text)]


def _link(url: str, st: ItemStatus | None, style: str) -> str:
    if style == "bare":
        return url
    label = (st.label if st else None) or short_label(url) or url
    return f"<{url}|{label}>"


def annotate(text: str, statuses: dict[str, ItemStatus], *, style: str = "bare") -> str:
    """Replace each GitHub URL (+ any stale tag) with ``URL tag``. ``style``: bare | slack."""

    def sub(m: re.Match) -> str:
        url, tail = _split_url(m.group("url"))
        st = statuses.get(canonical(url) or "")
        tag = st.tag() if st else ""
        return _link(url, st, style) + tail + (f" {tag}" if tag else "")

    out = _URL_WITH_TAG.sub(sub, text)
    return slackify_links(out) if style == "slack" else out


# --------------------------------------------------------------------------- blocks

def _section(text: str) -> dict:
    return {"type": "section", "text": {"type": "mrkdwn", "text": text[:SECTION_MAX]}}


def _context(elements: list[str]) -> list[dict]:
    blocks = []
    for i in range(0, len(elements), 10):  # Slack: max 10 elements per context block
        blocks.append({"type": "context",
                       "elements": [{"type": "mrkdwn", "text": e[:SECTION_MAX]} for e in elements[i:i + 10]]})
    return blocks


def _link_chip(url: str, st: ItemStatus | None) -> str:
    link = _link(url, st, "slack")
    if not st or not st.tag():
        return link
    lead = f"{st.emoji} " if st.state else ""
    rest = st.tag()[len(f"{st.emoji} {st.state}"):].strip() if st.state else st.tag()
    return f"{lead}{link} {st.state}{(' ' + rest) if rest else ''}".strip()


def _item_text(line: str) -> tuple[str, list[str]]:
    urls = github_urls(line)
    text = _URL_WITH_TAG.sub("", line)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"\s*[—-]\s*$", "", text)  # dangling "—" left after removing links
    return slackify_links(text), urls


def build_blocks(draft: str, statuses: dict[str, ItemStatus], *, context: str | None = None) -> list[dict]:
    blocks: list[dict] = []
    para: list[str] = []
    seen_header = False

    def flush_para():
        if para:
            blocks.append(_section(annotate("\n".join(para), statuses, style="slack")))
            para.clear()

    for raw in draft.splitlines():
        line = raw.rstrip()
        if not line.strip():
            flush_para()
            continue
        title = _TITLE.match(line)
        if title and not seen_header:
            seen_header = True
            blocks.append({"type": "header",
                           "text": {"type": "plain_text", "text": title.group(1).strip()[:HEADER_MAX], "emoji": True}})
            if context:
                blocks += _context([context])
            continue
        seen_header = True
        if title:
            flush_para()
            blocks.append({"type": "divider"})
            blocks.append(_section(f"*{title.group(1).strip()}*"))
            continue
        bullet = _BULLET.match(line)
        if bullet:
            flush_para()
            text, urls = _item_text(bullet.group(1))
            blocks.append(_section(f"• {text}" if text else "•"))
            chips = [_link_chip(u, statuses.get(canonical(u) or "")) for u in urls]
            if chips:
                blocks += _context(["   ".join(chips)])
            continue
        para.append(line)
    flush_para()

    if len(blocks) > MAX_BLOCKS:
        # Too many blocks: one section per group with inline tags.
        compact = annotate(draft, statuses, style="slack")
        chunks = [c for c in re.split(r"\n\s*\n", compact) if c.strip()]
        blocks = [_section(c) for c in chunks][:MAX_BLOCKS]
    return blocks


def render_payload(draft: str, *, context: str | None = None) -> dict:
    """``{"text": fallback mrkdwn, "blocks": [...]}`` with live statuses."""

    statuses = fetch_statuses(github_urls(draft))
    return {"text": annotate(draft, statuses, style="slack"),
            "blocks": build_blocks(draft, statuses, context=context)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Tag a status-update draft with live GitHub status.")
    ap.add_argument("--blocks", action="store_true", help="Print the Block Kit payload as JSON.")
    ap.add_argument("--context", default=None, help="Small grey line under the header (blocks only).")
    args = ap.parse_args()

    draft = sys.stdin.read()
    if not draft.strip():
        sys.exit("ERROR: pipe the draft on stdin.")
    if args.blocks:
        print(json.dumps(render_payload(draft, context=args.context), ensure_ascii=False, indent=2))
    else:
        print(annotate(draft, fetch_statuses(github_urls(draft))).rstrip("\n"))


if __name__ == "__main__":
    main()
