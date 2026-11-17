"""Render a status-update draft into (a) paste-ready text with live GitHub status tags
and (b) a Slack Block Kit payload for bot posts.

The draft is plain Slack mrkdwn with bare URLs (what Claude writes):

    *Status update · Thu Nov 12*
    Optional context paragraph…
    *In progress*
    • Sandbox MVP agents https://github.com/o/agents/pull/11 https://github.com/o/agents/pull/12

Every GitHub PR / issue / commit URL gets a status tag looked up live (see
``github_status.py``), e.g. ``🟢 approved``, ``🔵 open `wayfinder:map```, ``🟠 CI failing``.
Existing tags are stripped first, so re-rendering an already-tagged draft refreshes
the statuses instead of duplicating them.

The paste-mode render also saves the draft to ``updates/draft.txt`` so a later
"post status update" — even from another session — posts exactly this draft
(``--saved`` prints it, freshly tagged). A post clears it only when the posted text
is that draft (compared without status tags), so posting one session's update never
wipes another session's pending draft. ``--discard`` clears it by hand.

Usage:
    status_render.py < draft.txt                 # tagged paste text (bare URLs), saves draft
    status_render.py --saved                     # print the pending saved draft (exit 2 if none)
    status_render.py --discard                   # delete the saved draft
    status_render.py --blocks --context "Since Wed 11:34 · 1 merged" < draft.txt   # JSON payload
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from github_status import CI_FAILING, GITHUB_URL, ItemStatus, canonical, fetch_statuses, short_label  # noqa: E402
from render_slack_from_markdown import slackify_links  # noqa: E402
from _shared.journaling_repo import find_journaling_repo_root  # noqa: E402
from _shared.path_guard import atomic_write_text, read_text_limited  # noqa: E402

DRAFT_NAME = "draft.txt"


def draft_path() -> Path:
    return find_journaling_repo_root(Path(__file__)) / "updates" / DRAFT_NAME


def pending_draft() -> str | None:
    """The saved draft, or None. Posting that draft deletes it (``settle_saved_draft``)."""

    p = draft_path()
    if not p.is_file():
        return None
    return read_text_limited(p, max_bytes=200_000)

MAX_BLOCKS = 50
SECTION_MAX = 2900
HEADER_MAX = 150

_STATUS_WORDS = r"(?:approved|in review|changes requested|draft|merged|completed|closed|open|not planned)"
_STATUS_EMOJI = r"(?:🟢|🟡|🔴|⚪|🟣|⚫|🔵|✅)"
_CI_TAG = r"(?:🟠 CI failing|❌ CI)"
_URL_WITH_TAG = re.compile(
    r"(?P<url>" + GITHUB_URL.pattern + r"[^\s<>)`]*)"
    r"(?P<tag>(?:[ \t]+" + _STATUS_EMOJI + r"[ \t]+" + _STATUS_WORDS + r")"
    r"(?:[ \t]+" + _CI_TAG + r")?(?:[ \t]+`[^`\n]+`)*|[ \t]+" + _CI_TAG + r"(?:[ \t]+`[^`\n]+`)*)?"
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
        return _link(url, st, style) + (f" {tag}" if tag else "") + tail

    out = _URL_WITH_TAG.sub(sub, text)
    return slackify_links(out) if style == "slack" else out


_SLACK_LINK = re.compile(r"<(https?://[^|>\s]+)\|[^>]*>")


def normalize_draft(text: str) -> str:
    """The draft without status tags, Slack link labels or trailing whitespace, so a
    draft and its tagged render (bare or ``<url|repo#12>`` style) compare equal."""

    bare = annotate(_SLACK_LINK.sub(r"\1", text), {})
    return "\n".join(line.rstrip() for line in bare.strip().splitlines())


def settle_saved_draft(posted: str) -> bool:
    """After a successful post: delete the saved draft if ``posted`` is that draft.

    Returns True when a *different* saved draft is still pending (another session's,
    or an earlier version of this update), which the caller reports.
    """

    p = draft_path()
    if not p.is_file():
        return False
    saved = read_text_limited(p, max_bytes=200_000)
    if normalize_draft(saved) == normalize_draft(posted):
        p.unlink()
        return False
    return True


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
# Legend order (by circle); only circles that appear in the post are listed, and
# states sharing a circle share one entry ("🟣 merged/completed").
_LEGEND_ORDER = ["🟣", "🟢", "🟡", "🔴", "⚪", "🔵", "⚫", "🟠"]
_WORD_ORDER = ["merged", "completed", "approved", "in review", "changes requested", "draft",
               "open", "closed", "not planned", "CI failing"]


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
    """``repo#12 🟡`` (+ ``🟠`` for failing CI + `label`s) as rich_text elements."""

    label = (st.label if st else None) or short_label(url) or url
    els: list[dict] = [{"type": "link", "url": url, "text": label}]
    if st and st.state:
        els.append(_txt(f" {st.emoji}"))
        used.add((st.emoji, st.state))
    if st and st.ci_failing:
        els.append(_txt(f" {CI_FAILING[0]}"))
        used.add(CI_FAILING)
    for lbl in (st.labels if st else []):
        els += [_txt(" "), _txt(lbl, code=True)]
    return els


def _line_elements(line: str, statuses: dict[str, ItemStatus], used: set) -> list[dict]:
    """A draft line as rich_text elements; each GitHub URL (and any stale tag after it)
    becomes ``repo#12 🟡`` right where it was, so bullets and paragraphs look alike."""

    els: list[dict] = []
    pos = 0
    for m in _URL_WITH_TAG.finditer(line):
        els += _rich_inline(line[pos:m.start()])
        url, tail = _split_url(m.group("url"))
        els += _link_elements(url, statuses.get(canonical(url) or ""), used)
        if tail:
            els.append(_txt(tail))
        pos = m.end()
    els += _rich_inline(line[pos:])
    els = [e for e in els if e.get("type") != "text" or e.get("text")]
    return els or [_txt(" ")]


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
            flush_bullets()
            for i, ln in enumerate(para):
                lead = [_txt("\n")] if (rich and i == 0) else ([_txt("\n")] if i else [])
                rich.append({"type": "rich_text_section", "elements": lead + _line_elements(ln, statuses, used)})
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
            bullets.append({"type": "rich_text_section",
                            "elements": _line_elements(bullet.group(1), statuses, used)})
            continue
        para.append(line)
    flush_para()
    flush_rich()

    by_circle: dict[str, list[str]] = {}
    for emoji, word in sorted(used, key=lambda u: _WORD_ORDER.index(u[1]) if u[1] in _WORD_ORDER else 99):
        by_circle.setdefault(emoji, []).append(word)
    legend = [f"{e} {'/'.join(by_circle[e])}" for e in _LEGEND_ORDER if e in by_circle]
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
    ap.add_argument("--discard", action="store_true", help="Delete the saved draft and exit.")
    args = ap.parse_args()

    if args.discard:
        p = draft_path()
        if p.is_file():
            p.unlink()
            print("Discarded the saved draft (updates/draft.txt).")
        else:
            print("No saved draft.")
        return
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
