#!/usr/bin/env bash
# AC2 — Given a checkout equal to origin/main, When lineage-freshness.sh
# runs, Then it prints "fresh" and exits 0.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/lineage_lib.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
make_fixture "$tmp"

rc=0
out=$("$SCRIPT_UNDER_TEST" "$tmp/origin_clone") || rc=$?

[ "$out" = "$(printf 'fresh\nremote-sha=%s' "$(git -C "$tmp/origin_clone" rev-parse HEAD)")" ] \
  || fail "unexpected output: $out"
[ "$rc" -eq 0 ] || fail "expected exit 0, got $rc"

echo "ok"
