#!/usr/bin/env bash
# AC1 — Given a checkout 3 commits behind its remote, When
# lineage-freshness.sh runs, Then it prints "behind 3" with both versions
# and exits 2.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/lineage_lib.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
make_fixture "$tmp"

git clone -q "$tmp/remote.git" "$tmp/behind_clone"

cd "$tmp/origin_clone"
sed -i 's/version = .*/version = "1.0.1"/' Cargo.toml
git commit -qam "bump 1"
sed -i 's/version = .*/version = "1.0.2"/' Cargo.toml
git commit -qam "bump 2"
sed -i 's/version = .*/version = "1.1.0"/' Cargo.toml
git commit -qam "bump 3 (final)"
git push -q origin main

rc=0
out=$("$SCRIPT_UNDER_TEST" "$tmp/behind_clone") || rc=$?

echo "$out" | head -1 | grep -qE '^behind 3 \(local=1\.0\.0 remote=1\.1\.0\)$' \
  || fail "unexpected verdict line: $(echo "$out" | head -1)"
[ "$rc" -eq 2 ] || fail "expected exit 2, got $rc"

echo "ok"
