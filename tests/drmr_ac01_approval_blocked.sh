#!/usr/bin/env bash
# AC1 (R6, R2, R9) — the unknown-edge variant (its own frozen manifest and review row, verdict
# file mission=APPROVE) with one slug eligible: exit 1, findings exactly
# [mission-approval-blocked] naming the edge E4 and the slug, the producer a or the consumer b
# (R6: both endpoints of an unknown edge are dependent; review M4); in a FIX round (E4 moved to
# a -> c, the chain review a FIX and mission=FIX with one finding on a) c eligible, reached by no
# finding, is held by the unknown edge alone; the passing fixture gives []
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
use unknown; state "$ST_ALL b=eligible"; run_mr
[ "$RC" = 1 ] || fail "unknown edge, consumer b eligible: rc=$RC"; findings_eq '["mission-approval-blocked"]'
has_fail mission-approval-blocked "slug b=eligible" "unknown edge E4"
jtrue '"unknown edge E4" in {x["slug"]: x["reason"] for x in d["mission"]["dependent_slugs"]}.get("b", "")' "b dependent by E4"
# the FIX round: E4 (unknown) a -> c in the live edges file and its frozen copy, the manifest
# re-signed and the review row's scope_id re-recorded through --scope-id; the chain review a FIX
# and mission=FIX (verdict file and capture) with one finding, F1 on a (consumers external:x),
# re-signed; c, reached by no finding, is held by the unknown edge alone
use unknown; UM=notes/snapshots/unknown/snapshot.sha256; UR=notes/reviews/unknown
for f in "notes/missions/$MR_EB" "notes/snapshots/unknown/$MR_EB"; do
  vedit "$f" "import json
L[:] = [json.dumps(dict(json.loads(l), consumer='PRD-c.md')) if l.strip() and json.loads(l).get('id') == 'E4' else l for l in L]"
done
vedit "$UM" "L[:] = [('$(sha256sum "$H/notes/snapshots/unknown/$MR_EB" | cut -d' ' -f1)  $MR_EB' if l.endswith('  $MR_EB') else l) for l in L]"
uid=$("$LINT" --scope-id "$H/$UM") || fail "--scope-id $UM: $uid"
decedit "dict(r, scope_id='$uid') if r.get('scope') == '$UM' else r"
fixl="L[:] = [l.replace('APPROVE', 'FIX', 1) if l.startswith(('a ', 'mission=')) else l for l in L]"
vedit "$UR/verdict.txt" "$fixl"; capture "$UR/result.json" "$fixl"
head -1 "$MRFIX/variants/fix/home/$MR_CHAIN/verdict.txt.findings.jsonl" > "$H/$UR/verdict.txt.findings.jsonl"; resign "$UR"
state "a=linted a=reviewed:FIX b=linted b=reviewed:APPROVE c=linted c=reviewed:APPROVE c=eligible"; run_mr
[ "$RC" = 1 ] || fail "FIX round, unknown edge's consumer c eligible: rc=$RC $ERR"; findings_eq '["mission-approval-blocked"]'
has_fail mission-approval-blocked "slug c=eligible" "unknown edge E4"
jtrue 'd["mission"]["verdict"] == "FIX" and d["mission"]["findings"] == 1 and {x["slug"]: x["reason"] for x in d["mission"]["dependent_slugs"]}.get("c") == "unknown edge E4"' "FIX round: c held by E4 alone"
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
pass "unknown edge exact (producer a, consumer b); FIX-round consumer c held by E4 alone; passing verified; outside PRD ignored; four reasons refuse every eligible"
