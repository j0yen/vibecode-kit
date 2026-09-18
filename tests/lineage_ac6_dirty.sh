#!/usr/bin/env bash
# AC6 — Given two modified files, When lineage-freshness.sh runs, Then it
# prints "dirty 2" and the worktree is unchanged afterward.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/lineage_lib.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
make_fixture "$tmp"

echo "unstaged edit" >> "$tmp/origin_clone/Cargo.toml"
echo "untracked file" > "$tmp/origin_clone/scratch.txt"

before=$(git -C "$tmp/origin_clone" status --porcelain | sort)

rc=0
out=$("$SCRIPT_UNDER_TEST" "$tmp/origin_clone") || rc=$?

after=$(git -C "$tmp/origin_clone" status --porcelain | sort)

[ "$out" = "dirty 2" ] || fail "unexpected output: $out"
[ "$rc" -eq 2 ] || fail "expected exit 2, got $rc"
[ "$before" = "$after" ] || fail "worktree changed: before=[$before] after=[$after]"

echo "ok"
