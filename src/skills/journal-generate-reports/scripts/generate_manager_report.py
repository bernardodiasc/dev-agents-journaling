"""Generate period reports from ``entries/`` for a date range (inclusive).

Supports multiple *report audiences* (tone/structure): manager, self, team, qa.
Captures stay technical in ``entries/``; each audience reshapes the same data differently.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import resolve_write_path_under_repo, atomic_write_text
from _shared.script_utils import load_optional_install_config

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_MD_HEADING = re.compile(r"^(#{1,3})\s+(.+)$")
_SLACK_USER_ID = re.compile(r"^U[A-Za-z0-9]{8,}$")

REPORT_AUDIENCES = ("manager", "self", "team", "qa")


@dataclass
class PeriodReportData:
    date_from: str
    date_to: str
    chunks: list[tuple[date, dict[str, str], str]]
    all_wins: list[str]
    all_blockers: list[str]
    all_next: list[str]
    all_metrics: list[str]
    freeform_sections: list[tuple[date, str]]


def _uniq(seq: list[str]) -> list[str]:
    return list(dict.fromkeys(seq))


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


def slack_convert_inline_markdown_headings(text: str) -> str:
    out_lines: list[str] = []
    for line in text.splitlines():
        m = _MD_HEADING.match(line)
        if m:
            out_lines.append(f"*{m.group(2).strip()}*")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)


def aggregate_report(
    repo: Path,
    date_from: str,
    date_to: str,
) -> PeriodReportData:
    entries_dir = repo / "entries"
    d_from = date.fromisoformat(date_from)
    d_to = date.fromisoformat(date_to)

    chunks: list[tuple[date, dict[str, str], str]] = []
    for d in iter_dates(d_from, d_to):
        path = entries_dir / f"{d.isoformat()}.md"
        if not path.is_file():
            continue
        raw = path.read_text()
        _meta, body = parse_frontmatter(raw)
        sections = parse_sections(body)
        rel = str(path.relative_to(repo))
        chunks.append((d, sections, rel))

    if not chunks:
        sys.exit("ERROR: no entry files found in range (nothing to report).")

    all_wins: list[str] = []
    all_blockers: list[str] = []
    all_next: list[str] = []
    all_metrics: list[str] = []
    freeform_sections: list[tuple[date, str]] = []

    for d, sec, _rel in chunks:
        if ff := sec.get("Freeform", "").strip():
            freeform_sections.append((d, ff))
        all_wins.extend(bullet_lines(sec.get("Wins", "")))
        all_blockers.extend(bullet_lines(sec.get("Blockers", "")))
        all_next.extend(bullet_lines(sec.get("Next Steps", "")))
        for line in sec.get("Metrics", "").splitlines():
            t = line.strip()
            if t.startswith("- "):
                all_metrics.append(t)

    return PeriodReportData(
        date_from=date_from,
        date_to=date_to,
        chunks=chunks,
        all_wins=all_wins,
        all_blockers=all_blockers,
        all_next=all_next,
        all_metrics=all_metrics,
        freeform_sections=freeform_sections,
    )


def _manager_summary_sentence(data: PeriodReportData) -> str:
    """Plain, outcome-oriented line for leadership (no raw technical journal dump)."""

    wins = _uniq(data.all_wins)
    if wins:
        joined = "; ".join(wins[:5])
        if len(wins) > 5:
            joined += " (additional items logged in the journal)."
        return f"Progress this period included: {joined}."
    if data.all_next:
        return "Focus is on the priorities listed below; add wins to the journal to summarize delivery highlights."
    return "No structured wins were logged for this range; raw notes remain in daily entries if needed."


# --- manager: concise, non-technical surface ---


def format_markdown_manager(data: PeriodReportData) -> str:
    para = _manager_summary_sentence(data)
    lines: list[str] = [
        f"# Leadership update ({data.date_from} – {data.date_to})",
        "",
        f"_Generated {datetime.now().date().isoformat()}_",
        "",
        para,
        "",
        "## Priorities ahead",
        "",
    ]
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt[:8]:
            lines.append(f"- {n}")
    else:
        lines.append("- _(none listed)_")
    blk = _uniq(data.all_blockers)
    if blk:
        lines.extend(["", "## Needs visibility", ""])
        for b in blk[:5]:
            lines.append(f"- {b}")
    lines.extend(
        [
            "",
            "_Technical detail and narrative capture live in `entries/`; this summary stays high level._",
            "",
        ],
    )
    return "\n".join(lines)


def format_slack_manager(data: PeriodReportData) -> str:
    para = _manager_summary_sentence(data)
    lines: list[str] = [
        f"*Leadership update · {data.date_from}–{data.date_to}*",
        "",
        para,
        "",
        "*Priorities ahead*",
        "",
    ]
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt[:8]:
            lines.append(f"- {n}")
    else:
        lines.append("- _none listed_")
    blk = _uniq(data.all_blockers)
    if blk:
        lines.extend(["", "*Needs visibility*", ""])
        for b in blk[:5]:
            lines.append(f"- {b}")
    lines.extend(["", f"_Generated {datetime.now().date().isoformat()}_", ""])
    return "\n".join(lines)


# --- self: personal / reflection; can include mention in Slack ---


def format_markdown_self(data: PeriodReportData) -> str:
    lines: list[str] = [
        f"# Personal check-in ({data.date_from} – {data.date_to})",
        "",
        f"_Generated {datetime.now().date().isoformat()}_",
        "",
        "_For you: full detail from captures, including technical notes._",
        "",
        "## Wins",
        "",
    ]
    wins = _uniq(data.all_wins)
    if wins:
        for w in wins:
            lines.append(f"- {w}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Blockers", ""])
    blk = _uniq(data.all_blockers)
    if blk:
        for b in blk:
            lines.append(f"- {b}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Next focus", ""])
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt:
            lines.append(f"- {n}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Notes (from captures)", ""])
    if data.freeform_sections:
        for d, ff in data.freeform_sections:
            lines.append(f"### {d.isoformat()}")
            lines.append("")
            lines.append(ff)
            lines.append("")
    else:
        lines.append("_(no freeform)_")
        lines.append("")
    if data.all_metrics:
        lines.extend(["## Metrics", ""])
        lines.extend(data.all_metrics)
        lines.append("")
    lines.extend(["## Source entries", ""])
    for _d, _sec, rel in data.chunks:
        lines.append(f"- `{rel}`")
    lines.append("")
    return "\n".join(lines)


def format_slack_self(data: PeriodReportData, slack_user_id: str | None) -> str:
    lines: list[str] = []
    if slack_user_id:
        if not _SLACK_USER_ID.match(slack_user_id):
            sys.exit("ERROR: --slack-user-id / JOURNALING_SLACK_USER_ID must look like U0123456789.")
        lines.extend([f"<@{slack_user_id}>", ""])
    lines.extend(
        [
            f"*Personal check-in · {data.date_from}–{data.date_to}*",
            "",
            "_Snapshot from your journal (includes technical detail from captures)._",
            "",
            "*Wins*",
            "",
        ],
    )
    wins = _uniq(data.all_wins)
    if wins:
        for w in wins:
            lines.append(f"- {w}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Blockers*", ""])
    blk = _uniq(data.all_blockers)
    if blk:
        for b in blk:
            lines.append(f"- {b}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Next focus*", ""])
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt:
            lines.append(f"- {n}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Notes from captures*", ""])
    if data.freeform_sections:
        for d, ff in data.freeform_sections:
            lines.append(f"*{d.isoformat()}*")
            lines.append("")
            lines.append(slack_convert_inline_markdown_headings(ff))
            lines.append("")
    else:
        lines.append("_no freeform_")
        lines.append("")
    if data.all_metrics:
        lines.extend(["*Metrics*", ""])
        lines.extend(data.all_metrics)
        lines.append("")
    lines.extend(["*Source entries*", ""])
    for _d, _sec, rel in data.chunks:
        lines.append(f"- `{rel}`")
    lines.append("")
    return "\n".join(lines)


# --- team: colleagues / shared context ---


def format_markdown_team(data: PeriodReportData) -> str:
    lines: list[str] = [
        f"# Team sync ({data.date_from} – {data.date_to})",
        "",
        f"_Generated {datetime.now().date().isoformat()}_",
        "",
        "High-level share-out from the journal for this period.",
        "",
        "## Highlights",
        "",
    ]
    wins = _uniq(data.all_wins)
    if wins:
        for w in wins:
            lines.append(f"- {w}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Heads-up / dependencies", ""])
    blk = _uniq(data.all_blockers)
    if blk:
        for b in blk:
            lines.append(f"- {b}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Coming up", ""])
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt:
            lines.append(f"- {n}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Source entries", ""])
    for _d, _sec, rel in data.chunks:
        lines.append(f"- `{rel}`")
    lines.append("")
    return "\n".join(lines)


def format_slack_team(data: PeriodReportData) -> str:
    lines: list[str] = [
        f"*Team sync · {data.date_from}–{data.date_to}*",
        "",
        "_Share-out from the journal for this period._",
        "",
        "*Highlights*",
        "",
    ]
    wins = _uniq(data.all_wins)
    if wins:
        for w in wins:
            lines.append(f"- {w}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Heads-up / dependencies*", ""])
    blk = _uniq(data.all_blockers)
    if blk:
        for b in blk:
            lines.append(f"- {b}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Coming up*", ""])
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt:
            lines.append(f"- {n}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Source entries*", ""])
    for _d, _sec, rel in data.chunks:
        lines.append(f"- `{rel}`")
    lines.append("")
    return "\n".join(lines)


# --- qa: verification / risk lens ---


def format_markdown_qa(data: PeriodReportData) -> str:
    lines: list[str] = [
        f"# QA lens ({data.date_from} – {data.date_to})",
        "",
        f"_Generated {datetime.now().date().isoformat()}_",
        "",
        "Framed for validation, risk, and test planning (from journal fields).",
        "",
        "## Deliverables & changes to be aware of",
        "",
    ]
    wins = _uniq(data.all_wins)
    if wins:
        for w in wins:
            lines.append(f"- {w}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Risks / blockers", ""])
    blk = _uniq(data.all_blockers)
    if blk:
        for b in blk:
            lines.append(f"- {b}")
    else:
        lines.append("- _(none)_")
    lines.extend(["", "## Suggested verification / follow-up", ""])
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt:
            lines.append(f"- {n}")
    else:
        lines.append("- _(none)_")
    if data.all_metrics:
        lines.extend(["", "## Signals / metrics", ""])
        lines.extend(data.all_metrics)
        lines.append("")
    lines.extend(["## Source entries", ""])
    for _d, _sec, rel in data.chunks:
        lines.append(f"- `{rel}`")
    lines.append("")
    return "\n".join(lines)


def format_slack_qa(data: PeriodReportData) -> str:
    lines: list[str] = [
        f"*QA lens · {data.date_from}–{data.date_to}*",
        "",
        "_Validation and risk framing from journal fields._",
        "",
        "*Deliverables & changes*",
        "",
    ]
    wins = _uniq(data.all_wins)
    if wins:
        for w in wins:
            lines.append(f"- {w}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Risks / blockers*", ""])
    blk = _uniq(data.all_blockers)
    if blk:
        for b in blk:
            lines.append(f"- {b}")
    else:
        lines.append("- _none_")
    lines.extend(["", "*Suggested verification / follow-up*", ""])
    nxt = _uniq(data.all_next)
    if nxt:
        for n in nxt:
            lines.append(f"- {n}")
    else:
        lines.append("- _none_")
    if data.all_metrics:
        lines.extend(["", "*Signals / metrics*", ""])
        lines.extend(data.all_metrics)
        lines.append("")
    lines.extend(["*Source entries*", ""])
    for _d, _sec, rel in data.chunks:
        lines.append(f"- `{rel}`")
    lines.append("")
    return "\n".join(lines)


def render_report(
    data: PeriodReportData,
    output_format: str,
    audience: str,
    slack_user_id: str | None,
) -> str:
    if audience == "manager":
        return format_slack_manager(data) if output_format == "slack" else format_markdown_manager(data)
    if audience == "self":
        return format_slack_self(data, slack_user_id) if output_format == "slack" else format_markdown_self(data)
    if audience == "team":
        return format_slack_team(data) if output_format == "slack" else format_markdown_team(data)
    if audience == "qa":
        return format_slack_qa(data) if output_format == "slack" else format_markdown_qa(data)
    sys.exit(f"ERROR: unknown audience {audience!r}")


def default_output_basename(date_from: str, date_to: str, audience: str, output_format: str) -> str:
    ext = "slack.txt" if output_format == "slack" else "md"
    return f"report-{audience}-{date_from}-to-{date_to}.{ext}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate period reports from entries/. By default writes all audiences "
            "(manager, self, team, qa) as Markdown so they stay in sync. Use "
            "--report-audience to write just one. Slack .slack.txt is produced only at "
            "post-time by journal-post-slack."
        ),
    )
    parser.add_argument("--from", dest="date_from", required=True, help="Start date YYYY-MM-DD (inclusive)")
    parser.add_argument("--to", dest="date_to", required=True, help="End date YYYY-MM-DD (inclusive)")
    parser.add_argument(
        "--output",
        default=None,
        help=(
            "Override output path (single-audience only; requires --report-audience "
            "and is incompatible with --all-audiences)."
        ),
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "slack"),
        default="markdown",
        help=(
            "Output format for the generated file(s). Default: markdown. "
            "The 'slack' option is retained for advanced use; prefer journal-post-slack "
            "which renders the sibling .slack.txt at post time."
        ),
    )
    audience_group = parser.add_mutually_exclusive_group()
    audience_group.add_argument(
        "--report-audience",
        choices=REPORT_AUDIENCES,
        default=None,
        help="Single audience (manager | self | team | qa). Omit to write all audiences.",
    )
    audience_group.add_argument(
        "--all-audiences",
        action="store_true",
        help="Write all audiences together (default when --report-audience is omitted).",
    )
    parser.add_argument(
        "--slack-user-id",
        default=None,
        help=(
            "For --report-audience self + --format slack: prepend <@ID> "
            "(else uses JOURNALING_SLACK_USER_ID from .env)."
        ),
    )
    args = parser.parse_args()

    if not ISO_DATE.match(args.date_from) or not ISO_DATE.match(args.date_to):
        sys.exit("ERROR: dates must be YYYY-MM-DD")

    d_from = date.fromisoformat(args.date_from)
    d_to = date.fromisoformat(args.date_to)
    if d_from > d_to:
        sys.exit("ERROR: --from must be <= --to")

    # Default: all audiences in one go (keeps .md set in sync).
    write_all = args.all_audiences or args.report_audience is None
    if args.output and write_all:
        sys.exit(
            "ERROR: --output requires --report-audience (single-audience writes only).",
        )

    repo = find_journaling_repo_root(Path(__file__))
    data = aggregate_report(repo, args.date_from, args.date_to)

    def _resolve_uid(audience: str) -> str | None:
        if audience == "self" and args.format == "slack":
            uid = args.slack_user_id or load_optional_install_config(
                "JOURNALING_SLACK_USER_ID", start=repo,
            )
            return uid
        if args.slack_user_id:
            uid = args.slack_user_id.strip()
            if uid and not _SLACK_USER_ID.match(uid):
                sys.exit("ERROR: --slack-user-id must look like U0123456789.")
            return uid
        return None

    audiences = REPORT_AUDIENCES if write_all else (args.report_audience,)
    written: list[Path] = []
    for audience in audiences:
        body = render_report(data, args.format, audience, _resolve_uid(audience))
        default_name = default_output_basename(
            args.date_from, args.date_to, audience, args.format,
        )
        if args.output and not write_all:
            out_path = resolve_write_path_under_repo(repo, args.output)
        else:
            out_path = repo / "reports" / default_name
        atomic_write_text(out_path, body)
        written.append(out_path)

    for p in written:
        print(f"Wrote {p.relative_to(repo)}")


if __name__ == "__main__":
    main()
