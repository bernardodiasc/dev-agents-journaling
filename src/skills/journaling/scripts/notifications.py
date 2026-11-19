"""Unread GitHub notifications, grouped for the morning catch-up (stdlib + ``gh``).

``fetch_threads`` and ``fetch_my_review_states`` only GET from ``gh api`` (reading
does not mark anything read). ``notification_digest`` turns the threads into groups
the plan can use; it does no I/O, so it is the part under test.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess

GH_TIMEOUT_SECONDS = 30
MAX_PAGES = 3

_API_ITEM = re.compile(
    r"^https://api\.github\.com/repos/([A-Za-z0-9][\w.-]*)/([\w.-]+)/(pulls|issues)/(\d+)$"
)


def html_url(api_url: str | None) -> str:
    """``https://api.github.com/repos/o/r/pulls/12`` → ``https://github.com/o/r/pull/12``."""

    m = _API_ITEM.match(api_url or "")
    if not m:
        return ""
    owner, repo, kind, num = m.groups()
    return f"https://github.com/{owner}/{repo}/{'pull' if kind == 'pulls' else 'issues'}/{num}"


# Reasons that put the thread on the user: someone asked for them.
_ON_ME = {
    "review_requested": "review requested",
    "mention": "mentioned",
    "team_mention": "team mentioned",
    "assign": "assigned",
    "author": "activity on my thread",
    "approval_requested": "deployment approval requested",
    "invitation": "invited",
}


def notification_digest(threads: list[dict], owners: list[str], my_reviews: dict[str, dict]) -> dict:
    """Group unread notification threads into ``on_me`` and ``watching``.

    ``owners`` are the orgs the user works in (empty: no noise flag).
    ``my_reviews`` maps a PR's github.com URL to ``{"states": [...], "pending": bool}``:
    the states of the user's reviews on it, oldest first (``APPROVED``,
    ``DISMISSED``...), and whether a review request to the user is still open.
    GitHub keeps ``reason=review_requested`` after the review is in, so a request
    that is no longer pending moves to ``watching``.
    """

    orgs = {o.casefold() for o in owners}
    out: dict[str, list[dict]] = {"on_me": [], "watching": []}
    for t in threads:
        subject = t.get("subject") or {}
        reason = str(t.get("reason", ""))
        url = html_url(subject.get("url"))
        repo = str((t.get("repository") or {}).get("full_name", ""))
        item = {
            "url": url,
            "repo": repo,
            "title": " ".join(str(subject.get("title", "")).split()),
            "reason": reason,
            "why": _ON_ME.get(reason, reason.replace("_", " ")),
            "other_org": bool(orgs) and repo.split("/")[0].casefold() not in orgs,
        }
        on_me = reason in _ON_ME
        mine = my_reviews.get(url)
        if reason == "review_requested" and mine is not None:
            earlier = mine.get("states") or []
            if not mine.get("pending", True):
                on_me = False
                item["why"] = "reviewed; new activity since" if earlier else "review request removed"
            elif "DISMISSED" in earlier:
                item["why"] = "re-review (my review was dismissed)"
            elif earlier:
                item["why"] = "re-review"
        out["on_me" if on_me else "watching"].append(item)
    for items in out.values():
        items.sort(key=lambda i: (i["other_org"], i["repo"].casefold()))
    return out


# --------------------------------------------------------------------------- gh (read-only)

def _gh_api(path: str):
    try:
        res = subprocess.run(["gh", "api", path], capture_output=True, text=True,
                             timeout=GH_TIMEOUT_SECONDS, check=False)
        return json.loads(res.stdout) if res.returncode == 0 and res.stdout.strip() else None
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return None


def fetch_threads() -> list[dict] | None:
    """Unread notification threads (participating and watched), newest first; None on failure."""

    if shutil.which("gh") is None:
        return None
    threads: list[dict] = []
    for page in range(1, MAX_PAGES + 1):
        batch = _gh_api(f"notifications?all=false&per_page=50&page={page}")
        if not isinstance(batch, list):
            return threads or None
        threads += [t for t in batch if isinstance(t, dict)]
        if len(batch) < 50:
            break
    return threads


def fetch_my_review_states(urls: list[str], login: str) -> dict[str, dict]:
    """For each PR URL: ``login``'s review states (oldest first) and whether a request
    to ``login`` is still pending. PRs the lookup fails for are left out."""

    out: dict[str, dict] = {}
    for url in urls:
        m = re.fullmatch(r"https://github\.com/([\w.-]+)/([\w.-]+)/pull/(\d+)", url)
        if not m:
            continue
        base = f"repos/{m.group(1)}/{m.group(2)}/pulls/{m.group(3)}"
        reviews = _gh_api(f"{base}/reviews?per_page=100")
        requested = _gh_api(f"{base}/requested_reviewers")
        if not isinstance(reviews, list) or not isinstance(requested, dict):
            continue
        me = login.casefold()
        out[url] = {
            "states": [str(r.get("state", "")) for r in reviews
                       if str((r.get("user") or {}).get("login", "")).casefold() == me],
            "pending": any(str(u.get("login", "")).casefold() == me for u in requested.get("users") or []),
        }
        # A team request can't be matched to the user here; count it while unreviewed.
        if not out[url]["pending"] and requested.get("teams") and not out[url]["states"]:
            out[url]["pending"] = True
    return out
