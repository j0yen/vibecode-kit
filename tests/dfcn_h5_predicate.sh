#!/usr/bin/env bash
# Hermes H5 reading 6 in finding consumption (chain review 11 R11-F2; Hermes' CR7 direction of 2026-11-19 3:23 PM): `--require-closed` counts a repair
# as satisfied under the close gate's own predicate (PRD-swarm-decide-asks-waits-on-close-gate R1 and R4): its ask is closed or currently
# intake-accepted, never intake-cancelled; its proof is an accept FAIL followed by a run-mode PASS at one sha, read from the ask's own events whichever
# kind of row it is. Controls: closed (passes, as before), intake-accepted but open (passes), intake-cancelled after a proof (refused), open (waits),
# a PASS of a different check, an attested PASS and an unrelated ask's PASS (each refused). The canonical rows are served in the real CLI's shapes by
# a scenario `wm-asks`, because intake acceptance on the real CLI needs the root-owned intake policy.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
out="$(python3 -I "$here/fixtures/dfcn/dfcnfx.py" --run h5p- "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0"): $(printf '%s\n' "$out" | grep -v '^PASS' | head -20)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') cases"
