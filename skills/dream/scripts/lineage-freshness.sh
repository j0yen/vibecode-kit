#!/usr/bin/env bash
# lineage-freshness.sh — report how far a local checkout has drifted from
# origin/main, so /dream never cites file:line from a stale tree.
# See PRD-dream-lineage-freshness.
#
# Usage: lineage-freshness.sh <path>
#
# Verdict on stdout (one line): fresh | behind <n> | ahead <n> | dirty <n> |
# no-remote | missing. behind/ahead append local/remote manifest versions
# when a Cargo.toml or pyproject.toml exists at <path>'s root
# ("... (local=<lv> remote=<rv>)"). fresh/behind/ahead also print a second
# line, `remote-sha=<sha>`, for a caller that needs it (dream's
# `Cited-tree:` frontmatter). Exit 0 for fresh, 2 for every other verdict,
# 1 on usage error.
#
# Read-only: `git fetch` only updates remote-tracking refs (never the
# working tree); every other call is read-only git plumbing. The checkout
# is never stashed, reset, or modified — a dirty tree is reported, not
# cleaned up.

set -uo pipefail

usage() { echo "usage: $(basename "$0") <path>" >&2; exit 1; }
[ $# -eq 1 ] || usage
repo=$1

if [ ! -d "$repo" ] || ! git -C "$repo" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "missing"
  exit 2
fi

if ! git -C "$repo" remote get-url origin >/dev/null 2>&1; then
  echo "no-remote"
  exit 2
fi

dirty_n=$(git -C "$repo" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
if [ "${dirty_n:-0}" -gt 0 ]; then
  echo "dirty $dirty_n"
  exit 2
fi

timeout 10 git -C "$repo" fetch --quiet origin >/dev/null 2>&1 || true

if ! git -C "$repo" rev-parse -q --verify origin/main >/dev/null 2>&1; then
  echo "no-remote"
  exit 2
fi

# git rev-list --left-right --count HEAD...origin/main prints two numbers:
# the left count is commits reachable from HEAD but not origin/main (ahead
# of the remote); the right count is commits reachable from origin/main but
# not HEAD (behind the remote).
counts=$(git -C "$repo" rev-list --left-right --count HEAD...origin/main 2>/dev/null)
ahead=$(printf '%s' "$counts" | awk '{print $1}')
behind=$(printf '%s' "$counts" | awk '{print $2}')
ahead=${ahead:-0}
behind=${behind:-0}

extract_version() {
  grep -m1 -E '^[[:space:]]*version[[:space:]]*=[[:space:]]*"' | sed -E 's/^[^"]*"([^"]*)".*/\1/'
}

manifest=""
for f in Cargo.toml pyproject.toml; do
  if [ -f "$repo/$f" ]; then manifest=$f; break; fi
done

versions=""
if [ -n "$manifest" ]; then
  local_v=$(extract_version < "$repo/$manifest")
  remote_v=$(git -C "$repo" show "origin/main:$manifest" 2>/dev/null | extract_version)
  versions=" (local=${local_v:-unknown} remote=${remote_v:-unknown})"
fi

remote_sha=$(git -C "$repo" rev-parse -q --verify origin/main 2>/dev/null)

if [ "$behind" -eq 0 ] && [ "$ahead" -eq 0 ]; then
  echo "fresh"
  echo "remote-sha=$remote_sha"
  exit 0
elif [ "$behind" -gt 0 ]; then
  echo "behind ${behind}${versions}"
  echo "remote-sha=$remote_sha"
  exit 2
else
  echo "ahead ${ahead}${versions}"
  echo "remote-sha=$remote_sha"
  exit 2
fi
