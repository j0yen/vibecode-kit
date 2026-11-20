#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 2 (R3): one row per binding kind, valid and invalid, linted in check mode (`--consumption`). Valid requirement,
# test, repair, pending and residual rows and a part residual beside a binding exit 0; each invalid row (AC absent or commandless, a falsifier AC
# without its script and kill string, a falsifier row without kill, a kill script not the page's own, a mechanism row without its control, a test
# row without commit or path or whose blob names no finding, an unbound repair successor or wrong repair owner, an overdue pending row, a second
# unparted row beside a binding, an unaccepted part residual) exits 1 with its exact finding id, on a FAIL line naming its row, key and finding.
# The cases live in tests/fixtures/dfcn/dfcnfx.py; repair and pending rows read a temp canonical store through a `wm-asks` shim over the
# wm-decide named by DFCN_WM_DECIDE (else the one on PATH), with its own state and HOME.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
out="$(python3 -I "$here/fixtures/dfcn/dfcnfx.py" --run ac02- "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0"): $(printf '%s\n' "$out" | grep -v '^PASS' | head -20)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') cases"
