#!/usr/bin/env bash
# Chain review 11 R11-F2's no-drift control: the consumption lint's reading of a repair (consumed or not under --require-closed, a valid proof present)
# equals the close gate's own `_satisfied` on closed, intake-accepted-but-open, intake-cancelled and open rows. The predicate has one owner, the
# close gate (swarm-decide wm_decide/asks.py); DFCN_SWARM_DECIDE names the swarm-decide tree to read it from. Without it this control cannot run and
# fails, saying so.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
sd="${DFCN_SWARM_DECIDE:-}"
[ -n "$sd" ] && [ -f "$sd/wm_decide/asks.py" ] || { echo "FAIL $(basename "$0"): set DFCN_SWARM_DECIDE to a swarm-decide tree that carries the close gate (wm_decide/asks.py _satisfied)"; exit 1; }
grep -q '^def _satisfied' "$sd/wm_decide/asks.py" || { echo "FAIL $(basename "$0"): $sd/wm_decide/asks.py has no _satisfied (no close gate)"; exit 1; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
out="$(python3 -I "$here/fixtures/dfcn/dfcnfx.py" --nodrift "$repo/skills/dream/scripts/dream-run-note-lint.sh" "$T" "$sd" 2>&1)"; rc=$?
[ "$rc" = 0 ] || { echo "FAIL $(basename "$0"): $(printf '%s\n' "$out" | grep -v '^PASS' | head -10)"; exit 1; }
echo "PASS $(basename "$0"): $(printf '%s\n' "$out" | grep -c '^PASS') states agree with the close gate at $(git -C "$sd" rev-parse --short HEAD 2>/dev/null || echo "$sd")"
