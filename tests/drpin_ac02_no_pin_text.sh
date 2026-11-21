#!/usr/bin/env bash
# AC2 — grep for Fable/max pin text prints nothing and exits 1; the Phase routing
# paragraph names .config/skill-routing/policy.json, --route-request and R2's
# ungoverned-host sentence.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
out=$(cd "$REPO" && grep -nE 'Fable at max|effort: max|model: fable' skills/dream/SKILL.md); rc=$?
[ "$rc" = 1 ] && [ -z "$out" ] || fail "grep rc=$rc out=[$out]"
para=$(phase_routing "$SKILL" | tr '\n' ' ')
[ -n "$para" ] || fail "no Phase routing paragraph"
p3=$(awk '/^## Phase 3 — Draft/{f=1;next} /^## /{f=0} f' "$SKILL")
printf '%s\n' "$p3" | grep >/dev/null '^\*\*Phase routing:\*\*' || fail "Phase routing paragraph not in Phase 3"
for s in '.config/skill-routing/policy.json' '--route-request' "$R2_SENTENCE"; do
  case "$para" in *"$s"*) ;; *) fail "Phase routing paragraph lacks: $s";; esac
done
pass
