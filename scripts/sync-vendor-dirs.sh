#!/usr/bin/env bash
# Regenerate .cursor/ and .claude/ as symlinks into src/.
#
# Canonical source: src/{agents,rules,skills}. Vendor dirs are gitignored and
# derived from src/ on demand.
#
# Usage:
#   bash scripts/sync-vendor-dirs.sh            # regenerate (idempotent)
#   bash scripts/sync-vendor-dirs.sh --check    # report-only; exit non-zero on drift

set -euo pipefail

mode="regenerate"
if [[ "${1:-}" == "--check" ]]; then
  mode="check"
elif [[ $# -gt 0 ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

if [[ ! -d src/agents || ! -d src/rules || ! -d src/skills ]]; then
  echo "ERROR: expected src/{agents,rules,skills} under $repo_root" >&2
  exit 1
fi

drift=0

# Declarative spec: "<link_path>|<target_relative_to_link_parent>"
# Rules intentionally use different extensions per vendor (.mdc vs .md).
# skills/ is symlinked as a whole directory so new skills don't need per-file entries.
declare -a links=(
  # Cursor
  ".cursor/agents/journaling-specialist.md|../../src/agents/journaling-specialist.md"
  ".cursor/rules/journaling-repo.mdc|../../src/rules/journaling-repo.md"
  ".cursor/rules/journaling-interaction.mdc|../../src/rules/journaling-interaction.md"
  ".cursor/rules/journaling-slack-formatting.mdc|../../src/rules/journaling-slack-formatting.md"
  ".cursor/skills|../src/skills"
  # Claude
  ".claude/agents/journaling-specialist.md|../../src/agents/journaling-specialist.md"
  ".claude/rules/journaling-repo.md|../../src/rules/journaling-repo.md"
  ".claude/rules/journaling-interaction.md|../../src/rules/journaling-interaction.md"
  ".claude/rules/journaling-slack-formatting.md|../../src/rules/journaling-slack-formatting.md"
  ".claude/skills|../src/skills"
)

ensure_link() {
  local link_path="$1"
  local target="$2"
  local parent
  parent="$(dirname -- "$link_path")"

  # Resolve expected absolute target for existence check.
  local abs_target
  abs_target="$(cd -- "$parent" 2>/dev/null && cd -- "$(dirname -- "$target")" 2>/dev/null && pwd)/$(basename -- "$target")" || true

  if [[ -L "$link_path" ]]; then
    local current
    current="$(readlink -- "$link_path")"
    if [[ "$current" == "$target" ]]; then
      return 0
    fi
    if [[ "$mode" == "check" ]]; then
      echo "drift: $link_path -> $current (expected $target)"
      drift=1
      return 0
    fi
    rm -- "$link_path"
  elif [[ -e "$link_path" ]]; then
    # Regular file or directory occupies the path.
    if [[ "$mode" == "check" ]]; then
      echo "drift: $link_path is not a symlink (expected -> $target)"
      drift=1
      return 0
    fi
    rm -rf -- "$link_path"
  else
    if [[ "$mode" == "check" ]]; then
      echo "missing: $link_path (expected -> $target)"
      drift=1
      return 0
    fi
  fi

  mkdir -p -- "$parent"
  ln -s -- "$target" "$link_path"

  if [[ ! -e "$link_path" ]]; then
    echo "ERROR: created symlink $link_path but target resolves nowhere ($target)" >&2
    exit 1
  fi
}

for entry in "${links[@]}"; do
  link_path="${entry%%|*}"
  target="${entry#*|}"
  ensure_link "$link_path" "$target"
done

# Warn (non-fatal) about orphans: files in src/ without a vendor link, or
# non-symlink files in vendor dirs that aren't covered by the spec.

# Skills are whole-directory symlinks, so any new skill under src/skills/
# appears in both vendor dirs automatically. Only rules + agents need per-file entries.
for f in src/rules/*.md; do
  [[ -e "$f" ]] || continue
  base="$(basename -- "$f" .md)"
  if [[ ! -L ".cursor/rules/${base}.mdc" ]]; then
    echo "warn: src/rules/${base}.md has no .cursor/rules/${base}.mdc symlink (update scripts/sync-vendor-dirs.sh spec)" >&2
  fi
  if [[ ! -L ".claude/rules/${base}.md" ]]; then
    echo "warn: src/rules/${base}.md has no .claude/rules/${base}.md symlink (update scripts/sync-vendor-dirs.sh spec)" >&2
  fi
done
for f in src/agents/*.md; do
  [[ -e "$f" ]] || continue
  base="$(basename -- "$f")"
  if [[ ! -L ".cursor/agents/${base}" ]]; then
    echo "warn: src/agents/${base} has no .cursor/agents/${base} symlink (update scripts/sync-vendor-dirs.sh spec)" >&2
  fi
  if [[ ! -L ".claude/agents/${base}" ]]; then
    echo "warn: src/agents/${base} has no .claude/agents/${base} symlink (update scripts/sync-vendor-dirs.sh spec)" >&2
  fi
done

if [[ "$mode" == "check" ]]; then
  if [[ $drift -ne 0 ]]; then
    echo "vendor-dirs: drift detected (run: bash scripts/sync-vendor-dirs.sh)" >&2
    exit 1
  fi
  echo "vendor-dirs: OK"
else
  echo "vendor-dirs: synced (.cursor/ and .claude/)"
fi
