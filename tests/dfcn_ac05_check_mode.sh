#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 5 (R3, R8; PRD 13236dbb) — a temp store driven by the close gate's own code (the swarm-decide tree DFCN_SWARM_DECIDE
# names: asks add/accept/resolve, intake submit/claim/transition, the acceptance core), read by the lint through that tree's own CLI; repairs A->S1
# and B->S2 (S2 bound first, its lint on a row it closes-after, added with `asks add --blocks`). R3's command for S1 with A open, closed on a PASS
# only, FAIL then attested PASS (the store refuses to close it, so A stays open), FAIL then run PASS, an intake A accepted (open) or cancelled
# after that proof, S1's check lacking the lint, for S2 after B's FAIL then run PASS, and without wm-asks exits 1 (consumption-repair-open), 1, 1,
# 0, 0, 1, 1, 0, 2. Without DFCN_SWARM_DECIDE it fails, saying so (the close gate's `mode` field and intake states exist only in that tree until it is installed).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
sd="${DFCN_SWARM_DECIDE:-}"
[ -n "$sd" ] && [ -f "$sd/wm_decide/asks.py" ] || { echo "FAIL $(basename "$0"): set DFCN_SWARM_DECIDE to a swarm-decide tree that carries the close gate (wm_decide/asks.py _satisfied)"; exit 1; }
grep -q '^def _satisfied' "$sd/wm_decide/asks.py" || { echo "FAIL $(basename "$0"): $sd/wm_decide/asks.py has no _satisfied (no close gate)"; exit 1; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
out="$(python3 -I "$here/fixtures/dfcn/dfcnfx.py" --ac05 "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T" "$sd" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0"): $(printf '%s\n' "$out" | grep -v '^PASS' | head -12)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') cases; $(printf '%s\n' "$out" | grep '^# ac05 exits' | sed 's/^# //')"
