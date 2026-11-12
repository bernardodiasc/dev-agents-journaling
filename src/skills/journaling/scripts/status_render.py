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

The paste-mode render also saves the draft to ``updates/draft.txt`` so a later
"post status update" — even from another session — posts exactly this draft
(``--saved`` prints it, freshly tagged, if it is newer than the last posted update).

Usage:
    status_render.py < draft.txt                 # tagged paste text (bare URLs), saves draft
    status_render.py --saved                     # print the pending saved draft (exit 2 if none)
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
from _shared.journaling_repo import find_journaling_repo_root  # noqa: E402
from _shared.path_guard import atomic_write_text, read_text_limited  # noqa: E402

DRAFT_NAME = "draft.txt"


def draft_path() -> Path:
    return find_journaling_repo_root(Path(__file__)) / "updates" / DRAFT_NAME


def pending_draft() -> str | None:
    """The saved draft if it is newer than the last posted update, else None."""

    p = draft_path()
    if not p.is_file():
        return None
    posted = [f.stat().st_mtime for f in p.parent.glob("status-*.slack.txt")]
    if posted and max(posted) >= p.stat().st_mtime:
        return None
    return read_text_limited(p, max_bytes=200_000)

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


_INLINE = re.compile(
    r"`(?P<code>[^`\n]+)`"
    r"|<(?P<lurl>https?://[^|>\s]+)(?:\|(?P<ltext>[^>]+))?>"
    r"|(?P<url>https?://[^\s<>]+)"
    r"|(?<![\w*])\*(?P<bold>[^*\n]+)\*(?![\w*])"
    r"|(?<![\w_])_(?P<ital>[^_\n]+)_(?![\w_])"
    r"|(?<![\w~])~(?P<strike>[^~\n]+)~(?![\w~])"
)
# Legend order for the footer; only statuses that appear in the post are listed.
_LEGEND = ["🟣 merged", "🟢 approved", "🟡 in review", "🔴 changes requested", "⚪ draft",
           "⚫ closed", "🔵 open", "✅ closed", "⚫ not planned"]


def _txt(text: str, **style) -> dict:
    el = {"type": "text", "text": text}
    if style:
        el["style"] = style
    return el


def _rich_inline(text: str) -> list[dict]:
    """Slack mrkdwn-ish text -> rich_text elements (code, links, bold, italic, strike)."""

    out: list[dict] = []
    pos = 0
    for m in _INLINE.finditer(text):
        if m.start() > pos:
            out.append(_txt(text[pos:m.start()]))
        if m.group("code"):
            out.append(_txt(m.group("code"), code=True))
        elif m.group("lurl"):
            el = {"type": "link", "url": m.group("lurl")}
            if m.group("ltext"):
                el["text"] = m.group("ltext")
            out.append(el)
        elif m.group("url"):
            url, tail = _split_url(m.group("url"))
            out.append({"type": "link", "url": url})
            if tail:
                out.append(_txt(tail))
        elif m.group("bold"):
            out.append(_txt(m.group("bold"), bold=True))
        elif m.group("ital"):
            out.append(_txt(m.group("ital"), italic=True))
        elif m.group("strike"):
            out.append(_txt(m.group("strike"), strike=True))
        pos = m.end()
    if pos < len(text):
        out.append(_txt(text[pos:]))
    return out


def _link_elements(url: str, st: ItemStatus | None, used: set[str]) -> list[dict]:
    """``repo#12 🟡`` (+ ``❌ CI`` + `label`s) as rich_text elements."""

    label = (st.label if st else None) or short_label(url) or url
    els: list[dict] = [{"type": "link", "url": url, "text": label}]
    if st and st.state:
        els.append(_txt(f" {st.emoji}"))
        used.add(f"{st.emoji} {st.state}")
    if st and st.ci_failing:
        els.append(_txt(" ❌ CI"))
        used.add("❌ CI failing")
    for lbl in (st.labels if st else []):
        els += [_txt(" "), _txt(lbl, code=True)]
    return els


def _item_text(line: str) -> tuple[str, list[str]]:
    urls = github_urls(line)
    text = _URL_WITH_TAG.sub("", line)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"\s*[—-]\s*$", "", text)  # dangling "—" left after removing links
    return text, urls


def build_blocks(draft: str, statuses: dict[str, ItemStatus], *, context: str | None = None) -> list[dict]:
    """Compact layout: header, grey context, one rich_text block per run of sections
    (bold titles + tight bullet lists, ``repo#12 🟡`` links), legend footer."""

    blocks: list[dict] = []
    para: list[str] = []
    rich: list[dict] = []          # elements of the current rich_text block
    bullets: list[dict] = []       # pending rich_text_list items
    used: set[str] = set()
    seen_header = False

    def flush_bullets():
        if bullets:
            rich.append({"type": "rich_text_list", "style": "bullet", "elements": list(bullets)})
            bullets.clear()

    def flush_rich():
        flush_bullets()
        if rich:
            blocks.append({"type": "rich_text", "elements": list(rich)})
            rich.clear()

    def flush_para():
        if para:
            flush_rich()
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
            flush_bullets()
            lead = "\n" if rich else ""
            rich.append({"type": "rich_text_section",
                         "elements": ([_txt(lead)] if lead else []) + [_txt(title.group(1).strip(), bold=True)]})
            continue
        bullet = _BULLET.match(line)
        if bullet:
            flush_para()
            text, urls = _item_text(bullet.group(1))
            els = _rich_inline(text)
            for i, u in enumerate(urls):
                els.append(_txt("  " if (i or text) else ""))
                els += _link_elements(u, statuses.get(canonical(u) or ""), used)
            els = [e for e in els if e.get("type") != "text" or e.get("text")]
            bullets.append({"type": "rich_text_section", "elements": els or [_txt(" ")]})
            continue
        para.append(line)
    flush_para()
    flush_rich()

    legend = [x for x in _LEGEND if x in used] + (["❌ CI failing"] if "❌ CI failing" in used else [])
    if legend:
        blocks += _context(["   ".join(legend)])

    if len(blocks) > MAX_BLOCKS:
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
    ap.add_argument("--saved", action="store_true", help="Use the pending saved draft instead of stdin.")
    ap.add_argument("--no-save", action="store_true", help="Don't save the draft to updates/draft.txt.")
    args = ap.parse_args()

    if args.saved:
        draft = pending_draft()
        if draft is None:
            print("No pending draft (none saved, or already posted).", file=sys.stderr)
            sys.exit(2)
    else:
        draft = sys.stdin.read()
        if not draft.strip():
            sys.exit("ERROR: pipe the draft on stdin.")
        if not args.blocks and not args.no_save:
            atomic_write_text(draft_path(), draft)
    if args.blocks:
        print(json.dumps(render_payload(draft, context=args.context), ensure_ascii=False, indent=2))
    else:
        print(annotate(draft, fetch_statuses(github_urls(draft))).rstrip("\n"))


if __name__ == "__main__":
    main()
