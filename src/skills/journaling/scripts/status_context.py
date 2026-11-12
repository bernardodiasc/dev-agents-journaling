"""Collect everything needed to write a status update, in one call (stdlib + ``gh``).

Prints a compact, model-friendly digest:

  1. The period (since → now) and *why* that start was chosen.
  2. GitHub activity for ``@me`` in that period (via the ``gh`` CLI, read-only):
     merged PRs, open PRs (draft / ready), PRs reviewed, issues closed, open issues
     assigned — each with title, ``owner/repo#N`` and URL.
  3. Journal entries (``entries/YYYY-MM-DD.md``) that fall inside the period.

Period start (``--since auto``, the default):
  - the timestamp of the newest ``updates/status-*.slack.txt`` (last posted update), else
  - the start of the last working day (Friday when today is Monday).

Nothing is written; nothing is posted. ``gh`` is invoked with an argument list (no
shell), a timeout, and only ``search`` subcommands.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _shared.journaling_repo import find_journaling_repo_root
from _shared.path_guard import read_text_limited
from _shared.script_utils import load_optional_install_config
from github_status import canonical, fetch_statuses

GH_TIMEOUT_SECONDS = 30
GH_LIMIT = 50
_RECEIPT = re.compile(r"^status-(\d{4}-\d{2}-\d{2})T(\d{2})(\d{2})(\d{2})?Z\.slack\.txt$")
_OWNER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$")
_ENTRY_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})\.md$")
_FIELDS = "number,title,url,repository,isDraft,updatedAt,closedAt"


# --------------------------------------------------------------------------- period

def last_posted_update(repo: Path) -> datetime | None:
    newest: datetime | None = None
    for f in (repo / "updates").glob("status-*.slack.txt"):
        m = _RECEIPT.match(f.name)
        if not m:
            continue
        d, hh, mm, ss = m.group(1), m.group(2), m.group(3), m.group(4) or "00"
        ts = datetime.fromisoformat(f"{d}T{hh}:{mm}:{ss}+00:00")
        if newest is None or ts > newest:
            newest = ts
    return newest


def last_working_day_start(today: date) -> datetime:
    delta = 3 if today.weekday() == 0 else (2 if today.weekday() == 6 else 1)
    day = today - timedelta(days=delta)
    return datetime.combine(day, time.min).astimezone()


def resolve_since(raw: str, repo: Path) -> tuple[datetime, str]:
    if raw == "auto":
        last = last_posted_update(repo)
        if last is not None:
            return last, "last posted status update"
        return last_working_day_start(date.today()), "last working day (no posted update found)"
    m = re.fullmatch(r"(\d+)d", raw)
    if m:
        start = datetime.combine(date.today() - timedelta(days=int(m.group(1))), time.min).astimezone()
        return start, f"last {m.group(1)} days"
    try:
        if len(raw) == 10:
            return datetime.combine(date.fromisoformat(raw), time.min).astimezone(), "explicit date"
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        return (dt if dt.tzinfo else dt.astimezone()), "explicit timestamp"
    except ValueError:
        sys.exit("ERROR: --since must be auto, Nd (e.g. 7d), YYYY-MM-DD, or an ISO timestamp.")


# --------------------------------------------------------------------------- github

def _gh_search(kind: str, args: list[str]) -> list[dict] | None:
    cmd = ["gh", "search", kind, *args, "--json", _FIELDS, "--limit", str(GH_LIMIT)]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if res.returncode != 0:
        return None
    try:
        data = json.loads(res.stdout or "[]")
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, list) else None


def github_activity(since: datetime, owners: list[str]) -> dict[str, list[dict]] | str:
    if shutil.which("gh") is None:
        return "gh CLI not installed — skipping GitHub activity."
    stamp = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    scope: list[str] = []
    for o in owners:
        scope += ["--owner", o]

    queries = {
        "merged_prs": ("prs", ["--author", "@me", "--merged", "--merged-at", f">={stamp}"]),
        "open_prs": ("prs", ["--author", "@me", "--state", "open", "--updated", f">={stamp}"]),
        "reviewed_prs": ("prs", ["--reviewed-by", "@me", "--updated", f">={stamp}", "--", "-author:@me"]),
        "closed_issues": ("issues", ["--assignee", "@me", "--closed", f">={stamp}"]),
        "open_issues": ("issues", ["--assignee", "@me", "--state", "open", "--updated", f">={stamp}"]),
    }
    out: dict[str, list[dict]] = {}
    failures = 0
    for key, (kind, q) in queries.items():
        # owner flags must precede a bare "--" separator
        if "--" in q:
            i = q.index("--")
            args = q[:i] + scope + q[i:]
        else:
            args = q + scope
        items = _gh_search(kind, args)
        if items is None:
            failures += 1
            items = []
        out[key] = items
    if failures == len(queries):
        return "gh search failed (not authenticated? run `gh auth status`) — skipping GitHub activity."
    return out


def _fmt_item(it: dict, statuses: dict) -> str:
    repo = (it.get("repository") or {}).get("nameWithOwner", "?")
    title = " ".join(str(it.get("title", "")).split())
    st = statuses.get(canonical(str(it.get("url", ""))) or "")
    tag = f" [{st.tag()}]" if st and st.tag() else (" [draft]" if it.get("isDraft") else "")
    return f"- {title}{tag} — {repo}#{it.get('number')} — {it.get('url')}"


# --------------------------------------------------------------------------- journal

def journal_entries(repo: Path, since: datetime) -> list[tuple[str, str]]:
    first = since.astimezone().date()
    found: list[tuple[str, str]] = []
    for f in sorted((repo / "entries").glob("*.md")):
        m = _ENTRY_NAME.match(f.name)
        if not m or date.fromisoformat(m.group(1)) < first:
            continue
        found.append((m.group(1), read_text_limited(f, max_bytes=200_000).strip()))
    return found


# --------------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser(description="Collect status-update context (period + GitHub + journal).")
    ap.add_argument("--since", default="auto", help="auto (default) | Nd | YYYY-MM-DD | ISO timestamp")
    ap.add_argument("--owner", action="append", default=None,
                    help="Limit GitHub to this org/user (repeatable). Default: JOURNALING_GITHUB_OWNERS.")
    ap.add_argument("--no-github", action="store_true", help="Skip GitHub activity.")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = ap.parse_args()

    repo = find_journaling_repo_root(Path(__file__))
    since, reason = resolve_since(args.since, repo)

    owners = args.owner
    if owners is None:
        cfg = load_optional_install_config("JOURNALING_GITHUB_OWNERS", start=repo) or ""
        owners = [o.strip() for o in cfg.split(",") if o.strip()]
    for o in owners:
        if not _OWNER.fullmatch(o):
            sys.exit(f"ERROR: invalid GitHub owner {o!r}.")

    gh = "skipped (--no-github)" if args.no_github else github_activity(since, owners)
    entries = journal_entries(repo, since)
    now = datetime.now().astimezone()

    if args.json:
        print(json.dumps({
            "since": since.isoformat(), "until": now.isoformat(), "since_reason": reason,
            "owners": owners, "github": gh,
            "journal": [{"date": d, "text": t} for d, t in entries],
        }, indent=2))
        return

    print(f"PERIOD: {since.strftime('%Y-%m-%d %H:%M %Z')} → {now.strftime('%Y-%m-%d %H:%M %Z')} ({reason})")
    if owners:
        print(f"GITHUB SCOPE: {', '.join(owners)}")
    print()
    if isinstance(gh, str):
        print(f"GITHUB: {gh}\n")
    else:
        labels = {
            "merged_prs": "Merged PRs (authored)",
            "open_prs": "Open PRs (authored, updated in period)",
            "reviewed_prs": "PRs reviewed (others')",
            "closed_issues": "Issues closed (assigned)",
            "open_issues": "Open issues (assigned, updated in period)",
        }
        statuses = fetch_statuses(it.get("url", "") for items in gh.values() for it in items)
        for key, label in labels.items():
            items = gh.get(key, [])
            print(f"## {label}: {len(items)}")
            for it in items:
                print(_fmt_item(it, statuses))
            print()
    print(f"## Journal entries in period: {len(entries)}")
    for d, text in entries:
        print(f"\n### entries/{d}.md\n{text}")


if __name__ == "__main__":
    main()
