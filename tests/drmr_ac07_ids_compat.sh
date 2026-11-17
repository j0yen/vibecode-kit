#!/usr/bin/env bash
# AC7 (R10, R9, R7, R1) — every recorded scope_id recomputes through --scope-id; the drrec/
# notes and the drei note lint as at 373ff679 (read by git show, sha256 acde611f…) once
# `mission` and `provenance.mission` are deleted; --selftest keeps every predecessor PASS
# line and carries one passing refusal per new chain-review id plus a passing bound mission;
# a one-PRD single_component mission passes and echoes its reason, and is edge-grammar after
# a same-Task entry of the same mission with three PRDs; entry 2 with scope=m1 after entry 1's
# scope=m1,m2 is mission-grammar naming entry 1.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
n=0
for d in "$MRFIX" "$MRFIX"/variants/*; do
  v=base; [ "$d" = "$MRFIX" ] || v=$(basename "$d")
  while IFS= read -r l; do
    sc=$(printf '%s' "$l" | python3 -c 'import sys,json; r=json.load(sys.stdin); print(r.get("scope") or "")')
    [ -n "$sc" ] || continue
    want=$(printf '%s' "$l" | python3 -c 'import sys,json; print(json.load(sys.stdin)["scope_id"])')
    use "$v"
    got=$("$LINT" --scope-id "$H/$sc"); [ "$got" = "$want" ] || fail "$v $sc: --scope-id $got, recorded $want"
    n=$((n+1))
  done < "$d/decisions.jsonl"
done
echo "ok $n recorded scope_id values recompute"
OLD="$T/pred.sh"; git -C "$REPO" show "$PRED_SHA:skills/dream/scripts/dream-run-note-lint.sh" > "$OLD" 2>/dev/null || fail "git show $PRED_SHA failed"
[ "$(sha256sum "$OLD" | cut -d' ' -f1)" = "$PRED_LINT_SHA" ] || fail "predecessor sha256"
eq() { # <tag> <log> <home> <decisions>
  local jo jn
  jo=$(bash "$OLD" "$2" --last --prd-dir "$3" --decisions "$4" --json 2>/dev/null); jn=$("$LINT" "$2" --last --prd-dir "$3" --decisions "$4" --json 2>/dev/null)
  python3 - "$jo" "$jn" <<'PY' || fail "$1: head differs from 373ff679 minus mission: $jo / $jn"
import sys, json
o, n = json.loads(sys.argv[1]), json.loads(sys.argv[2])
n.pop("mission"); n["provenance"].pop("mission")
assert o == n
PY
}
cp -r "$here/fixtures/drrec" "$T/drrec"; cp -r "$here/fixtures/drei" "$T/drei"; export ANALYSIS_WIKI_DIR="$T/drrec/wiki"
eq drrec "$T/drrec/home/notes/dream-log.md" "$T/drrec/home" "$T/drrec/decisions.jsonl"
eq drrec-verified "$T/drrec/verified/home/notes/dream-log.md" "$T/drrec/verified/home" "$T/drrec/verified/decisions.jsonl"
eq drei "$T/drei/home/notes/dream-log.md" "$T/drei/home" "$T/drei/decisions.jsonl"
bash "$OLD" --selftest > "$T/st.old" 2>&1; "$LINT" --selftest > "$T/st.new" 2>&1 || fail "selftest failed: $(grep -v '^PASS' "$T/st.new" | head)"
while IFS= read -r l; do grep -qxF -- "$l" "$T/st.new" || fail "predecessor PASS line missing: $l"; done < <(grep '^PASS ' "$T/st.old")
for id in mission-scope-mismatch mission-scope-incomplete mission-review-missing mission-verdict-missing mission-finding-incomplete mission-snapshot-stale mission-approval-blocked; do
  grep -q "^PASS refuse:$id:drmr-" "$T/st.new" || fail "selftest has no drmr refusal fixture for $id"
done
grep -q '^PASS pass:drmr-' "$T/st.new" || fail "selftest has no passing bound-mission fixture"
use single; run_mr
[ "$RC" = 0 ] || fail "single component: rc=$RC $ERR"; findings_eq '[]'
jtrue 'd["mission"]["single_component"] and d["mission"]["prds"] == 1 and d["provenance"]["mission"] == "verified"' "single component echoed"
use single-split; run_mr; has_fail edge-grammar "single_component"
use prefix; run_mr; has_fail mission-grammar "$MR_E1_TS"
pass "$n scope_ids; drrec/drei equal 373ff679 minus mission; selftest; single component; prefix"
