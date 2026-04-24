"""Generate a daily planning brief from recent journal entries and optional Slack context.

Writes Markdown only. The Slack-mrkdwn sibling (``.slack.txt``) is produced at
post-time by ``journal-post-slack`` — its presence means the plan was delivered.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import read_text_limited, resolve_under_repo, resolve_write_path_under_repo, atomic_write_text

_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)
_BULLET_RE = re.compile(r"^[-*] (.+)$", re.MULTILINE)
MAX_READ_BYTES = 512 * 1024


def _parse_sections(text: str) -> dict[str, str]:
    parts = _SECTION_RE.split(text)
    sections: dict[str, str] = {}
    i = 1
    while i + 1 <= len(parts) - 1:
        sections[parts[i].strip()] = parts[i + 1].strip()
        i += 2
    return sections


def _bullets(section_text: str) -> list[str]:
    return _BULLET_RE.findall(section_text)


def _load_entries(repo_root: Path, lookback_days: int) -> list[dict]:
    today = date.today()
    entries = []
    for i in range(1, lookback_days + 1):
        d = today - timedelta(days=i)
        path = repo_root / "entries" / f"{d}.md"
        if path.exists():
            text = read_text_limited(path, max_bytes=MAX_READ_BYTES)
            sections = _parse_sections(text)
            entries.append({
                "date": str(d),
                "wins": _bullets(sections.get("Wins", "")),
                "blockers": _bullets(sections.get("Blockers", "")),
                "next_steps": _bullets(sections.get("Next Steps", "")),
            })
    return entries  # most recent first


def _render_markdown(entries: list[dict], slack_context: str | None, today: str) -> str:
    lines: list[str] = [f"# Daily Planning — {today}", ""]

    if not entries:
        lines += ["_No recent entries found._", ""]
    else:
        latest = entries[0]
        lines += [f"## Last entry: {latest['date']}", ""]

        if latest["wins"]:
            lines.append("**Completed:**")
            lines.extend(f"- {w}" for w in latest["wins"])
            lines.append("")

        if latest["next_steps"]:
            lines.append("**Planned next steps:**")
            lines.extend(f"- {s}" for s in latest["next_steps"])
            lines.append("")

        if latest["blockers"]:
            lines.append("**Blockers:**")
            lines.extend(f"- {b}" for b in latest["blockers"])
            lines.append("")

        older_steps = [
            (entry["date"], step)
            for entry in entries[1:]
            for step in entry["next_steps"]
        ]
        if older_steps:
            lines += ["## Earlier outstanding next steps", ""]
            for entry_date, step in older_steps:
                lines.append(f"- {step}  _(from {entry_date})_")
            lines.append("")

    if slack_context:
        lines += ["## Recent Slack activity", "", "```", slack_context.strip(), "```", ""]

    lines += [
        "## Today's plan",
        "_Add your plan here, or tell the journaling specialist what you're working on._",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a daily planning brief (Markdown) from recent journal entries. "
            "Slack sibling .slack.txt is produced at post-time by journal-post-slack."
        ),
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=7,
        metavar="DAYS",
        help="Days of entries to include (default: 7)",
    )
    parser.add_argument(
        "--context-file",
        metavar="PATH",
        default=None,
        help=(
            "Optional pre-gathered context file to embed verbatim "
            "(e.g. context/slack-…, context/jira-…, context/note-…)."
        ),
    )
    parser.add_argument(
        "--slack-context-file",
        metavar="PATH",
        default=None,
        help="[deprecated alias for --context-file]",
    )
    parser.add_argument(
        "--output",
        metavar="PATH",
        default=None,
        help="Write plan to an explicit file inside repo (mutually exclusive with --save).",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help=(
            "Auto-save to plans/plan-YYYY-MM-DD.md "
            "(mutually exclusive with --output)."
        ),
    )
    args = parser.parse_args()

    if args.lookback <= 0:
        sys.exit("ERROR: --lookback must be a positive integer.")
    if args.output and args.save:
        sys.exit("ERROR: use --output or --save, not both.")

    repo = find_journaling_repo_root(Path(__file__))
    entries = _load_entries(repo, args.lookback)
    today = str(date.today())

    ctx_arg = args.context_file or args.slack_context_file
    slack_context: str | None = None
    if ctx_arg:
        ctx_path = resolve_under_repo(repo, ctx_arg)
        slack_context = read_text_limited(ctx_path, max_bytes=MAX_READ_BYTES)

    rendered = _render_markdown(entries, slack_context, today)

    if args.save:
        md_path = resolve_write_path_under_repo(repo, f"plans/plan-{today}.md")
        atomic_write_text(md_path, rendered)
        print(f"Wrote {md_path.relative_to(repo)}")
    elif args.output:
        out_path = resolve_write_path_under_repo(repo, args.output)
        atomic_write_text(out_path, rendered)
        print(f"Wrote {out_path.relative_to(repo)}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
