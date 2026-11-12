"""Look up live status for GitHub PR / issue / commit URLs in one GraphQL call (via ``gh``).

Used by ``status_render.py`` (tags in drafts and Block Kit posts) and
``status_context.py`` (digest). Read-only. URLs are passed as GraphQL *variables*,
never interpolated into the query text, and only canonical github.com item URLs are
accepted. Any failure (no ``gh``, not authenticated, network) returns ``{}`` so
callers degrade to untagged output instead of failing.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field

GH_TIMEOUT_SECONDS = 30
BATCH = 40
MAX_LABELS = 3

GITHUB_URL = re.compile(
    r"https://github\.com/([A-Za-z0-9][\w.-]*)/([\w.-]+)/"
    r"(?:(pull|issues)/(\d+)|commit/([0-9a-fA-F]{7,40}))"
)

_FIELDS = """
  __typename
  ... on PullRequest { number isDraft merged state reviewDecision
      repository { name } labels(first: 3) { nodes { name } }
      commits(last: 1) { nodes { commit { statusCheckRollup { state } } } } }
  ... on Issue { number state stateReason repository { name } labels(first: 3) { nodes { name } } }
  ... on Commit { abbreviatedOid repository { name } }
"""


@dataclass
class ItemStatus:
    kind: str                 # "pr" | "issue" | "commit"
    label: str                # short link label: repo#12 / repo@abc1234
    emoji: str = ""           # status dot
    state: str = ""           # approved / in review / draft / merged / open / closed ...
    labels: list[str] = field(default_factory=list)
    ci_failing: bool = False

    def tag(self) -> str:
        """``🟢 approved ❌ CI `label``` (empty for commits)."""
        parts = []
        if self.state:
            parts.append(f"{self.emoji} {self.state}".strip())
        if self.ci_failing:
            parts.append("❌ CI")
        parts += [f"`{lbl}`" for lbl in self.labels]
        return " ".join(parts)


def canonical(url: str) -> str | None:
    """Canonical form of a GitHub item URL (drops /files, #fragments, ?query), else None."""

    m = GITHUB_URL.match(url)
    if not m:
        return None
    owner, repo, kind, num, sha = m.groups()
    if sha:
        return f"https://github.com/{owner}/{repo}/commit/{sha.lower()}"
    return f"https://github.com/{owner}/{repo}/{kind}/{num}"


def short_label(url: str) -> str | None:
    m = GITHUB_URL.match(url)
    if not m:
        return None
    _owner, repo, _kind, num, sha = m.groups()
    return f"{repo}@{sha[:7].lower()}" if sha else f"{repo}#{num}"


def _labels(node: dict) -> list[str]:
    return [n["name"] for n in (node.get("labels") or {}).get("nodes", []) if n.get("name")][:MAX_LABELS]


def _pr_status(node: dict, label: str) -> ItemStatus:
    if node.get("merged"):
        emoji, state = "🟣", "merged"
    elif node.get("state") == "CLOSED":
        emoji, state = "⚫", "closed"
    elif node.get("isDraft"):
        emoji, state = "⚪", "draft"
    elif node.get("reviewDecision") == "APPROVED":
        emoji, state = "🟢", "approved"
    elif node.get("reviewDecision") == "CHANGES_REQUESTED":
        emoji, state = "🔴", "changes requested"
    else:
        emoji, state = "🟡", "in review"
    rollup = None
    commits = (node.get("commits") or {}).get("nodes") or []
    if commits:
        rollup = ((commits[0].get("commit") or {}).get("statusCheckRollup") or {}).get("state")
    is_open = state not in ("merged", "closed")
    return ItemStatus(kind="pr", label=label, emoji=emoji, state=state, labels=_labels(node),
                      ci_failing=is_open and rollup in ("FAILURE", "ERROR"))


def _issue_status(node: dict, label: str) -> ItemStatus:
    if node.get("state") == "OPEN":
        emoji, state = "🔵", "open"
    elif node.get("stateReason") == "NOT_PLANNED":
        emoji, state = "⚫", "not planned"
    else:
        emoji, state = "✅", "closed"
    return ItemStatus(kind="issue", label=label, emoji=emoji, state=state, labels=_labels(node))


def _query_batch(urls: list[str]) -> dict:
    decls = ", ".join(f"$u{i}: URI!" for i in range(len(urls)))
    body = "\n".join(f"r{i}: resource(url: $u{i}) {{ {_FIELDS} }}" for i in range(len(urls)))
    cmd = ["gh", "api", "graphql", "-f", f"query=query({decls}) {{\n{body}\n}}"]
    for i, u in enumerate(urls):
        cmd += ["-f", f"u{i}={u}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=GH_TIMEOUT_SECONDS, check=False)
        data = json.loads(res.stdout or "{}")
    except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
        return {}
    # Partial errors (e.g. one inaccessible URL) still return data for the rest.
    return data.get("data") or {}


def fetch_statuses(urls) -> dict[str, ItemStatus]:
    """Map canonical URL -> ItemStatus for every resolvable GitHub item URL."""

    if shutil.which("gh") is None:
        return {}
    wanted = sorted({c for u in urls if (c := canonical(u))})
    out: dict[str, ItemStatus] = {}
    for start in range(0, len(wanted), BATCH):
        chunk = wanted[start:start + BATCH]
        data = _query_batch(chunk)
        for i, url in enumerate(chunk):
            node = data.get(f"r{i}") or {}
            label = short_label(url) or url
            t = node.get("__typename")
            if t == "PullRequest":
                out[url] = _pr_status(node, label)
            elif t == "Issue":
                out[url] = _issue_status(node, label)
            elif t == "Commit":
                out[url] = ItemStatus(kind="commit", label=label)
    return out
