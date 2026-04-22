"""Save a Jira context snapshot from pasted ticket / epic / project URLs and notes.

No Jira API call is made — this is a **link-based** capture. The file written is a
human-readable text blob that can be passed to ``journal-daily-plan --context-file``
or referenced by the journaling specialist when capturing progress.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
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
from _shared.script_utils import load_optional_install_config

# Accepts classic and next-gen Atlassian URLs for tickets, epics, and projects.
# Examples:
#   https://x-team-internal.atlassian.net/browse/AIAUT-436
#   https://x-team-internal.atlassian.net/jira/software/projects/AIAUT/boards/123?selectedIssue=AIAUT-436
_ATLASSIAN_URL = re.compile(
    r"^https://[a-z0-9-]+\.atlassian\.net(?:/[A-Za-z0-9._~%!$&'()*+,;=:@/-]*)?$"
)
_TICKET_KEY = re.compile(r"\b([A-Z][A-Z0-9]{1,9}-\d+)\b")
_PROJECT_KEY_IN_PATH = re.compile(r"/projects/([A-Z][A-Z0-9]{1,9})(?:/|$|\?)")
_SLUG_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")

KIND_CHOICES = ("ticket", "epic", "project", "note")


def _slugify(s: str) -> str:
    s = s.strip().lower().replace("_", "-")
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:64] or "note"


def _validate_url(url: str, expected_base: str | None) -> None:
    if not _ATLASSIAN_URL.match(url):
        sys.exit(
            f"ERROR: URL must be an https Atlassian link (got {url!r}).",
        )
    if expected_base and not url.startswith(expected_base.rstrip("/") + "/"):
        sys.exit(
            f"ERROR: URL does not match JOURNALING_JIRA_BASE_URL "
            f"({expected_base!r}): {url!r}.",
        )


def _extract_auto_slug(kind: str, urls: list[str]) -> str:
    """Pick a concise slug from the first URL (e.g. AIAUT-436 or AIAUT)."""

    for url in urls:
        proj = _PROJECT_KEY_IN_PATH.search(url)
        if kind == "project" and proj:
            return proj.group(1).lower()
        ticket = _TICKET_KEY.search(url)
        if ticket:
            return ticket.group(1).lower()
        if proj:
            return proj.group(1).lower()
    return kind


def _read_notes(repo: Path, note_args: list[str], note_file: str | None) -> str:
    parts: list[str] = []
    if note_file:
        path = resolve_under_repo(repo, note_file)
        parts.append(read_text_limited(path, max_bytes=MAX_READ_BYTES_FOR_SLACK_POST).rstrip())
    parts.extend(n.strip() for n in note_args if n.strip())
    return "\n\n".join(parts).strip()


def _render(kind: str, urls: list[str], title: str | None, notes: str, today: str) -> str:
    lines: list[str] = [
        f"Source: Jira ({kind})",
        f"Captured: {today}",
    ]
    if title:
        lines.append(f"Title: {title.strip()}")
    lines.append("")
    lines.append("Links:")
    for url in urls:
        lines.append(f"- {url}")
    lines.append("")
    if notes:
        lines.append("Notes:")
        lines.append(notes)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Save a link-based Jira context file under context/ (no API call).",
    )
    parser.add_argument(
        "--kind",
        choices=KIND_CHOICES,
        required=True,
        help="Scope of the context: ticket, epic, project, or note.",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        metavar="URL",
        help="Jira URL (repeatable). All must be under the configured Atlassian host.",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional human title for this context (recorded in the file).",
    )
    parser.add_argument(
        "--note",
        action="append",
        default=[],
        metavar="TEXT",
        help="Free-form note about why this context matters (repeatable).",
    )
    parser.add_argument(
        "--note-file",
        default=None,
        help="Read additional notes from a file inside the repo.",
    )
    parser.add_argument(
        "--slug",
        default=None,
        help=(
            "Filename slug (a-z 0-9 -). Default: derived from the first URL "
            "(ticket key or project key) or the --kind."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Override output path (default: context/jira-<slug>-<today>.txt).",
    )
    parser.add_argument(
        "--stdout",
        action="store_true",
        help="Print the rendered context to stdout instead of writing a file.",
    )
    args = parser.parse_args()

    if not args.url and args.kind != "note":
        sys.exit("ERROR: --url is required unless --kind note is used with --note/--note-file.")
    if args.kind == "note" and not (args.note or args.note_file):
        sys.exit("ERROR: --kind note requires --note or --note-file.")

    repo = find_journaling_repo_root(Path(__file__))
    expected_base = load_optional_install_config("JOURNALING_JIRA_BASE_URL", start=repo)
    for url in args.url:
        _validate_url(url, expected_base)

    today = str(date.today())
    if args.slug:
        if not _SLUG_OK.match(args.slug):
            sys.exit("ERROR: --slug must match [a-z0-9-]{1,64} starting alphanumeric.")
        slug = args.slug
    else:
        slug = _slugify(_extract_auto_slug(args.kind, args.url))

    notes = _read_notes(repo, args.note, args.note_file)
    body = _render(args.kind, args.url, args.title, notes, today)

    if args.stdout:
        print(body)
        return

    if args.output:
        target = resolve_write_path_under_repo(repo, args.output)
    else:
        target = resolve_write_path_under_repo(
            repo, f"context/jira-{slug}-{today}.txt",
        )
    atomic_write_text(target, body)
    print(f"Wrote {target.relative_to(repo)}")


if __name__ == "__main__":
    main()
