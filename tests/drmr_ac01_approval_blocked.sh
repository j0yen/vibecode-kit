#!/usr/bin/env bash
# AC1 (R6, R2, R9) — the unknown-edge variant (its own frozen manifest and review row, verdict
# file mission=APPROVE) with one slug eligible: exit 1, findings exactly
# [mission-approval-blocked] naming the edge E4 and the slug; the passing fixture gives []
# and provenance.mission verified; a PRD outside prds changing fires nothing; with no chain
# review, none of the last manifest, no scope= or no decisions log every eligible member is
# refused naming its reason. Known-bad: an implementation that treats "no chain review" as
# "nothing to block", or holds every slug, or never names the edge.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
use unknown; state "$ST_ALL a=eligible"; run_mr
[ "$RC" = 1 ] || fail "unknown edge, a eligible: rc=$RC"; findings_eq '["mission-approval-blocked"]'
has_fail mission-approval-blocked "slug a" "E4"
has_fail mission-approval-blocked "mission=APPROVE" "E4"
use base; run_mr
[ "$RC" = 0 ] || fail "passing fixture: rc=$RC: $ERR"; findings_eq '[]'
jtrue 'd["provenance"]["mission"] == "verified" and d["mission"]["verdict"] == "APPROVE"' "passing fixture verified"
printf '# PRD zz, outside the mission\n' > "$H/built-prds/PRD-zz.md"; run_mr; findings_eq '[]'
printf 'edited\n' >> "$H/built-prds/PRD-zz.md"; run_mr; findings_eq '[]'
every() { # <reason> : a, b and c eligible are each refused naming the reason
  for s in a b c; do has_fail mission-approval-blocked "slug $s" "$1"; done
}
EL="$ST_ALL a=eligible b=eligible c=eligible"
use base; decedit "dict(r, scope_id='0'*64) if r.get('role')=='review' else r"; state "$EL"; run_mr
has_id mission-review-missing; every "no bound chain review"
use twomanifest; decedit "None if r['session']=='$S_M2' else r"
python3 - "$LOG" <<'PY'
import sys
p = sys.argv[1]; L = [l for l in open(p).read().split("\n") if not (l.startswith("Review:") and "/t2/" in l)]; open(p, "w").write("\n".join(L))
PY
state "$EL"; run_mr; every "no chain review of the last manifest"
use noscope; state "$EL"; run_mr; findings_eq '["mission-approval-blocked"]'; every "no mission scope"
use base; setline Route "Route: ungoverned session=$S_MAUTH host=$(hostname)"; state "$EL"; run_mr_ungov
[ "$RC" = 1 ] || fail "ungoverned: rc=$RC $ERR"; findings_eq '["mission-approval-blocked"]'; every "no bound chain review"
state "$ST_ALL"; run_mr_ungov; [ "$RC" = 0 ] || fail "ungoverned, nothing eligible: rc=$RC $ERR"
jtrue 'd["provenance"]["mission"] == "self" and d["mission"]["chain_reviews"] == []' "ungoverned self"
pass "unknown edge exact; passing verified; outside PRD ignored; four reasons refuse every eligible"
