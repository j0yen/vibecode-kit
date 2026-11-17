#!/usr/bin/env bash
# AC3 (R2, R3, R8) — a review row matching no listed manifest is mission-review-missing
# (provenance.mission self); the Route session is review-self; a chain review bound to the
# later manifest listed before the earlier one, or a later-launched review of one manifest
# listed before an earlier-launched one, is mission-review-missing naming the out-of-order
# file with verdict null; in order the verdict is FIX; with the later FIX's line gone,
# unlisted_review_sessions names it and eligible a is blocked naming a and its session; an
# earlier-launched unnamed review row only reports.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
use base; decedit "dict(r, scope_id='e'*64) if r.get('role')=='review' else r"; run_mr
has_fail mission-review-missing "$(printf 'e%.0s' $(seq 64))"; jtrue 'd["provenance"]["mission"] == "self" and d["mission"]["chain_reviews"] == []'
use base; setline Review "Review: $MR_CHAIN/verdict.txt reviewer-session=$S_MAUTH result=$MR_CHAIN/result.json"; run_mr
has_fail review-self "$S_MAUTH"
swap() { python3 - "$LOG" <<'PY'
import sys
p = sys.argv[1]; L = open(p).read().split("\n"); i = [k for k, l in enumerate(L) if l.startswith("Review:")]
L[i[0]], L[i[1]] = L[i[1]], L[i[0]]; open(p, "w").write("\n".join(L))
PY
}
FIXST="a=linted a=reviewed:FIX a=reviewed:APPROVE b=linted b=reviewed:APPROVE b=reviewed:APPROVE c=linted c=reviewed:APPROVE c=reviewed:APPROVE"
use twomanifest-fix; swap; state "$FIXST"; run_mr
has_fail mission-review-missing "notes/reviews/t1/verdict.txt"; jtrue 'd["mission"]["verdict"] is None' "out-of-order index: verdict null"
use twomanifest-fix; run_mr; no_id mission-review-missing; jtrue 'd["mission"]["verdict"] == "FIX"' "in order: FIX"
use rereview; swap; state "$FIXST"; run_mr
has_fail mission-review-missing "notes/reviews/chain/verdict.txt"; jtrue 'd["mission"]["verdict"] is None' "out of launch order: verdict null"
use rereview; run_mr; no_id mission-review-missing; jtrue 'd["mission"]["verdict"] == "FIX"' "launch order: FIX"
use rereview; python3 - "$LOG" <<'PY'
import sys
p = sys.argv[1]; L = [l for l in open(p).read().split("\n") if not (l.startswith("Review:") and "chain-r2" in l)]; open(p, "w").write("\n".join(L))
PY
state "$ST_ALL a=eligible"; run_mr
jtrue '[u["session"] for u in d["mission"]["unlisted_review_sessions"]] == ["'"$S_M2"'"]' "unlisted names R2"
has_fail mission-approval-blocked "slug a" "unlisted later review $S_M2"
use later-unlisted; state "$ST_ALL a=eligible"; run_mr
jtrue 'sorted(u["session"] for u in d["mission"]["unlisted_review_sessions"]) == sorted(["'"$S_M0"'", "'"$S_M2"'"])' "two unlisted"
has_fail mission-approval-blocked "slug a" "unlisted later review $S_M2"
decedit "None if r['session']=='$S_M2' else r"; run_mr
[ "$RC" = 0 ] || fail "earlier-launched unnamed row only: rc=$RC $ERR"; findings_eq '[]'
jtrue '[u["session"] for u in d["mission"]["unlisted_review_sessions"]] == ["'"$S_M0"'"] and d["provenance"]["mission"] == "verified"' "earlier unnamed reports only"
pass "unmatched row, review-self, out-of-order x2, in-order FIX x2, latest unlisted held, earlier unlisted reported"
