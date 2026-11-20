#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 3 (R3 residual, R4, R8), check mode: a residual accepted by an independent review session of the Task passes;
# one accepted by the author lineage, by a role-less session, by a review of another Task, or with no `accepts <id>` line gives
# consumption-residual-unaccepted and leaves its finding unconsumed; receipt-only rows (a session, a run id, a report) give consumption-receipt-only;
# check mode without --reviews or --prd-home gives consumption-context-missing. Authoring mode (R1's `Consumption:` line on a run note) is a later
# stage of this PRD and is not exercised here.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
out="$(python3 -I "$here/fixtures/dfcn/dfcnfx.py" --run ac03- "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0"): $(printf '%s\n' "$out" | grep -v '^PASS' | head -20)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') cases (check mode)"
