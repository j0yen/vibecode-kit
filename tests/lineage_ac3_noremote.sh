#!/usr/bin/env bash
# AC3 — Given a path with no git remote, When lineage-freshness.sh runs,
# Then it prints "no-remote" and exits 2 without fetching.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$here/lineage_lib.sh"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
git init -q "$tmp/lonely"

# A fake `git` shim earlier on PATH that fails the run if `fetch` is ever
# invoked — proves the script returns before attempting a fetch.
shim=$(mktemp -d)
cat > "$shim/git" <<EOF
#!/usr/bin/env bash
if [ "\$1" = "fetch" ]; then
  echo "TEST FAILURE: fetch was called" >&2
  exit 99
fi
exec "$(command -v git)" "\$@"
EOF
chmod +x "$shim/git"

rc=0
out=$(PATH="$shim:$PATH" "$SCRIPT_UNDER_TEST" "$tmp/lonely") || rc=$?

[ "$out" = "no-remote" ] || fail "unexpected output: $out"
[ "$rc" -eq 2 ] || fail "expected exit 2, got $rc"

echo "ok"
