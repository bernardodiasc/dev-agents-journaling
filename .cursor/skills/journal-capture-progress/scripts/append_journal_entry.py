"""Append or create a daily journal entry under ``entries/YYYY-MM-DD.md``.

Merges into existing sections; appends timestamped subsections under ``## Freeform``.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in here.parents:
        if (p / ".cursor" / "skills" / "journal-capture-progress").is_dir():
            (p / "entries").mkdir(parents=True, exist_ok=True)
            (p / "reports").mkdir(parents=True, exist_ok=True)
            return p
    sys.exit(
        "ERROR: could not find journaling repo root "
        "(expected .cursor/skills/journal-capture-progress).",
    )


def parse_simple_frontmatter(raw: str) -> tuple[dict[str, str | list[str]], str]:
    """Minimal frontmatter: date, tags list, optional audience."""

    raw = raw.lstrip("\ufeff")
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    fm_block = parts[1].strip()
    body = parts[2].lstrip("\n")
    meta: dict[str, str | list[str]] = {}
    for line in fm_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("tags:"):
            rest = line[len("tags:") :].strip()
            if rest.startswith("["):
                inner = rest.strip("[]")
                meta["tags"] = [t.strip().strip("'\"") for t in inner.split(",") if t.strip()]
            else:
                meta["tags"] = [t.strip() for t in rest.split(",") if t.strip()]
        elif ":" in line:
            k, v = line.split(":", 1)
            key = k.strip()
            val = v.strip().strip("'\"")
            if key != "tags":
                meta[key] = val
    return meta, body


def ensure_frontmatter(date_str: str, tags: list[str] | None, audience: str | None) -> str:
    lines = ["---", f"date: {date_str}"]
    if tags:
        lines.append("tags: [" + ", ".join(repr(t) for t in tags) + "]")
    if audience:
        lines.append(f"audience: {audience}")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


SECTION_ORDER = ["Freeform", "Wins", "Blockers", "Next Steps", "Metrics"]


def parse_sections(body: str) -> dict[str, str]:
    """Split body by ## headings (first line of section includes title)."""

    sections: dict[str, str] = {}
    if not body.strip():
        return sections
    pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        return {"Freeform": body.strip()} if body.strip() else {}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:end].rstrip()
    return sections


def render_sections(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for name in SECTION_ORDER:
        if name in sections and sections[name].strip():
            parts.append(f"## {name}\n{sections[name].strip()}\n")
    for name, content in sections.items():
        if name not in SECTION_ORDER and name:
            parts.append(f"## {name}\n{content.strip()}\n")
    return "\n".join(parts).rstrip() + "\n"


def merge_bullets(existing: str, new_lines: list[str]) -> str:
    old = existing.strip()
    bullets = []
    if old:
        bullets.append(old)
    for line in new_lines:
        line = line.strip()
        if not line:
            continue
        if not line.startswith("- "):
            line = "- " + line
        bullets.append(line)
    return "\n".join(bullets) + ("\n" if bullets else "")


def append_capture_to_freeform(freeform: str, note: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    block = f"### Capture {ts}\n\n{note.strip()}\n"
    base = freeform.strip()
    if not base:
        return block
    return base + "\n\n" + block


def main() -> None:
    parser = argparse.ArgumentParser(description="Append content to entries/YYYY-MM-DD.md")
    parser.add_argument(
        "--date",
        default=None,
        help="Entry date YYYY-MM-DD (default: today UTC)",
    )
    parser.add_argument(
        "--audience",
        default=None,
        help="Optional frontmatter audience (e.g. manager_update)",
    )
    parser.add_argument(
        "--tag",
        action="append",
        default=[],
        dest="tags",
        help="Optional tag (repeatable)",
    )
    parser.add_argument(
        "--freeform",
        default=None,
        help="Freeform paragraph (optional if --freeform-file)",
    )
    parser.add_argument(
        "--freeform-file",
        default=None,
        help="Read freeform text from file",
    )
    parser.add_argument("--win", action="append", default=[], dest="wins", help="Win bullet (repeatable)")
    parser.add_argument("--blocker", action="append", default=[], dest="blockers")
    parser.add_argument("--next-step", action="append", default=[], dest="next_steps")
    parser.add_argument(
        "--metric",
        action="append",
        default=[],
        help="Metric as key=value (repeatable)",
    )
    args = parser.parse_args()

    d = args.date or date.today().isoformat()
    if not ISO_DATE.match(d):
        sys.exit("ERROR: --date must be YYYY-MM-DD")

    repo = find_repo_root()
    path = repo / "entries" / f"{d}.md"

    freeform_text = args.freeform
    if args.freeform_file:
        freeform_text = Path(args.freeform_file).read_text()
    if freeform_text is None:
        freeform_text = ""

    metrics_lines: list[str] = []
    for m in args.metric or []:
        if "=" not in m:
            sys.exit(f"ERROR: --metric must be key=value, got {m!r}")
        k, _, v = m.partition("=")
        metrics_lines.append(f"- {k.strip()}: {v.strip()}")

    has_new = bool(
        freeform_text.strip()
        or args.wins
        or args.blockers
        or args.next_steps
        or metrics_lines
        or args.tags
        or args.audience,
    )
    if not path.is_file() and not has_new:
        sys.exit(
            "ERROR: provide at least one of --freeform, --freeform-file, "
            "--win, --blocker, --next-step, --metric, --tag, --audience",
        )
    if path.is_file() and not has_new:
        sys.exit("ERROR: nothing new to append (add content flags).")

    if path.is_file():
        raw = path.read_text()
        meta, body = parse_simple_frontmatter(raw)
        sections = parse_sections(body)
        # merge tags
        if args.tags:
            old_tags = meta.get("tags")
            if isinstance(old_tags, list):
                merged = list(dict.fromkeys([*old_tags, *args.tags]))
                meta["tags"] = merged
            else:
                meta["tags"] = args.tags
        if args.audience:
            meta["audience"] = args.audience
        ff = sections.get("Freeform", "")
        if freeform_text.strip():
            sections["Freeform"] = append_capture_to_freeform(ff, freeform_text)
        if args.wins:
            sections["Wins"] = merge_bullets(sections.get("Wins", ""), args.wins)
        if args.blockers:
            sections["Blockers"] = merge_bullets(sections.get("Blockers", ""), args.blockers)
        if args.next_steps:
            sections["Next Steps"] = merge_bullets(sections.get("Next Steps", ""), args.next_steps)
        if metrics_lines:
            sections["Metrics"] = merge_bullets(sections.get("Metrics", ""), metrics_lines)
        entry_date = str(meta.get("date", d))
        tags_out = meta.get("tags") if isinstance(meta.get("tags"), list) else None
        audience_out = str(meta["audience"]) if meta.get("audience") else None
        fm = ensure_frontmatter(entry_date, tags_out, audience_out)
        out = fm + render_sections(sections)
        path.write_text(out)
    else:
        sections: dict[str, str] = {}
        if freeform_text.strip():
            sections["Freeform"] = append_capture_to_freeform("", freeform_text)
        if args.wins:
            sections["Wins"] = merge_bullets("", args.wins)
        if args.blockers:
            sections["Blockers"] = merge_bullets("", args.blockers)
        if args.next_steps:
            sections["Next Steps"] = merge_bullets("", args.next_steps)
        if metrics_lines:
            sections["Metrics"] = merge_bullets("", metrics_lines)
        fm = ensure_frontmatter(d, args.tags or None, args.audience)
        path.write_text(fm + render_sections(sections))

    print(f"Wrote {path.relative_to(repo)}")


if __name__ == "__main__":
    main()
