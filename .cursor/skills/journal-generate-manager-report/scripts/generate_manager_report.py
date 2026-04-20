"""Generate a manager-focused markdown report from ``entries/`` for a date range (inclusive)."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import resolve_write_path_under_repo

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    if not body.strip():
        return sections
    pattern = re.compile(r"^## (.+)$", re.MULTILINE)
    matches = list(pattern.finditer(body))
    if not matches:
        return {"Freeform": body.strip()}
    for i, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        sections[title] = body[start:end].rstrip()
    return sections


def parse_frontmatter(raw: str) -> tuple[dict[str, str | list[str]], str]:
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
            meta[k.strip()] = v.strip().strip("'\"")
    return meta, body


def iter_dates(d0: date, d1: date):
    d = d0
    while d <= d1:
        yield d
        d += timedelta(days=1)


def bullet_lines(text: str) -> list[str]:
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("- "):
            out.append(s[2:].strip())
        elif s.startswith("* "):
            out.append(s[2:].strip())
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate manager report from entries/")
    parser.add_argument("--from", dest="date_from", required=True, help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--to", dest="date_to", required=True, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--output",
        default=None,
        help="Output path (default: reports/manager-report-<from>-to-<to>.md)",
    )
    args = parser.parse_args()

    if not ISO_DATE.match(args.date_from) or not ISO_DATE.match(args.date_to):
        sys.exit("ERROR: dates must be YYYY-MM-DD")

    d_from = date.fromisoformat(args.date_from)
    d_to = date.fromisoformat(args.date_to)
    if d_from > d_to:
        sys.exit("ERROR: --from must be <= --to")

    repo = find_journaling_repo_root(Path(__file__))
    entries_dir = repo / "entries"

    chunks: list[tuple[date, dict[str, str], str]] = []
    for d in iter_dates(d_from, d_to):
        path = entries_dir / f"{d.isoformat()}.md"
        if not path.is_file():
            continue
        raw = path.read_text()
        meta, body = parse_frontmatter(raw)
        sections = parse_sections(body)
        rel = str(path.relative_to(repo))
        chunks.append((d, sections, rel))

    if not chunks:
        sys.exit("ERROR: no entry files found in range (nothing to report).")

    all_wins: list[str] = []
    all_blockers: list[str] = []
    all_next: list[str] = []
    all_metrics: list[str] = []
    freeform_bits: list[str] = []

    for d, sec, _rel in chunks:
        if ff := sec.get("Freeform", "").strip():
            freeform_bits.append(f"### {d.isoformat()}\n\n{ff}\n")
        all_wins.extend(bullet_lines(sec.get("Wins", "")))
        all_blockers.extend(bullet_lines(sec.get("Blockers", "")))
        all_next.extend(bullet_lines(sec.get("Next Steps", "")))
        for line in sec.get("Metrics", "").splitlines():
            t = line.strip()
            if t.startswith("- "):
                all_metrics.append(t)

    # Executive summary: dedupe-ish first lines
    summary_bullets: list[str] = []
    for w in all_wins[:3]:
        summary_bullets.append(f"- {w}")
    for n in all_next[:2]:
        item = f"- {n}"
        if item not in summary_bullets:
            summary_bullets.append(item)
    if not summary_bullets and freeform_bits:
        summary_bullets.append("- See Highlights and Completed work below.")

    report_name = f"manager-report-{args.date_from}-to-{args.date_to}.md"
    out_path = (
        resolve_write_path_under_repo(repo, args.output)
        if args.output
        else repo / "reports" / report_name
    )

    lines: list[str] = [
        f"# Manager update ({args.date_from} – {args.date_to})",
        "",
        f"_Generated {datetime.now().date().isoformat()}_",
        "",
        "## Executive summary",
        "",
    ]
    lines.extend(summary_bullets[:5] if summary_bullets else ["- (No structured wins/next steps in range.)"])
    lines.extend(["", "## Highlights", ""])
    for w in dict.fromkeys(all_wins):
        lines.append(f"- {w}")
    if not all_wins:
        lines.append("- _(none)_")
    lines.extend(["", "## Completed work", ""])
    if freeform_bits:
        for bit in freeform_bits:
            lines.append(bit)
            lines.append("")
    else:
        lines.append("_(No freeform sections in range.)_")
        lines.append("")
    lines.extend(["## Blockers / risks", ""])
    for b in dict.fromkeys(all_blockers):
        lines.append(f"- {b}")
    if not all_blockers:
        lines.append("- _(none)_")
    lines.extend(["", "## Next actions", ""])
    for n in dict.fromkeys(all_next):
        lines.append(f"- {n}")
    if not all_next:
        lines.append("- _(none)_")
    lines.extend(["", "## Metrics snapshot", ""])
    if all_metrics:
        lines.extend(all_metrics)
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Source entries", ""])
    for _d, _sec, rel in chunks:
        lines.append(f"- `{rel}`")
    lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines))
    print(f"Wrote {out_path.relative_to(repo)}")


if __name__ == "__main__":
    main()
