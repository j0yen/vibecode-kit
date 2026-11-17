#!/usr/bin/env bash
# AC7 (R8, R9, R1, R2) — every recorded scope_id recomputes through --scope-id; chain_reviews
# are FIX then APPROVE; entry 2's scope= naming after alone is refused (a later entry extends
# the list, never shortens it); a later manifest without the repairs file is
# mission-scope-incomplete naming it and the manifest (r3 F23); entry 2 without repairs= is
# repair-missing x2 ("no repairs= token") and nothing else of this PRD (r4 F27), as is the
# approve-with-finding variant once entry 2's review exists (r6 F33); the fixture is linted from
# the test's temporary directory, not the PRD home; drrec/, drei/ and drmr/ lint as at 373ff679
# once `mission` and `provenance.mission` are deleted, and --selftest keeps every predecessor
# PASS line plus one refusal per new id and one passing repaired mission.
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
n=0
for d in "$FCFIX" "$FCFIX"/variants/*; do
  v=base; [ "$d" = "$FCFIX" ] || v=$(basename "$d")
  while IFS= read -r l; do
    sc=$(printf '%s' "$l" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("scope") or "")')
    [ -n "$sc" ] || continue
    want=$(printf '%s' "$l" | python3 -c 'import sys,json; print(json.load(sys.stdin)["scope_id"])')
    use "$v"; got=$("$LINT" --scope-id "$H/$sc"); [ "$got" = "$want" ] || fail "$v $sc: --scope-id $got, recorded $want"
    n=$((n+1))
  done < "$d/decisions.jsonl"
done
echo "ok $n recorded scope_id values recompute"
cd "$T" || fail "cd $T"
use base; run_fc; [ "$RC" = 0 ] || fail "from the temp dir: rc=$RC $ERR"
jtrue '[c["verdict"] for c in d["mission"]["chain_reviews"]] == ["FIX", "APPROVE"]' "chain_reviews FIX then APPROVE"
use base; ml2 "Mission: drfc-mission scope=$AFT repairs=$FC_RP"; run_fc; has_fail mission-grammar "$FC_E1_TS"
use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  $FC_RB')]"; run_fc; has_fail mission-scope-incomplete "$FC_RB" "$AFT"
use base; ml2 "Mission: drfc-mission scope=$BEF,$AFT"; run_fc; findings_eq '["repair-missing"]'
[ "$(printf '%s\n' "$ERR" | grep -c '^FAIL repair-missing: .*no repairs= token')" = 2 ] || fail "want two repair-missing lines: $ERR"
has_fail repair-missing "F1" "no repairs= token"; has_fail repair-missing "F2" "no repairs= token"
use approve-finding; run_fc; findings_eq '["repair-missing"]'; has_fail repair-missing "F1" "no repairs= token"
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
cp -r "$here/fixtures/drrec" "$T/drrec"; cp -r "$here/fixtures/drei" "$T/drei"; cp -r "$here/fixtures/drmr" "$T/drmr"; export ANALYSIS_WIKI_DIR="$T/drrec/wiki"
eq drrec "$T/drrec/home/notes/dream-log.md" "$T/drrec/home" "$T/drrec/decisions.jsonl"
eq drrec-verified "$T/drrec/verified/home/notes/dream-log.md" "$T/drrec/verified/home" "$T/drrec/verified/decisions.jsonl"
eq drei "$T/drei/home/notes/dream-log.md" "$T/drei/home" "$T/drei/decisions.jsonl"
eq drmr "$T/drmr/home/notes/dream-log.md" "$T/drmr/home" "$T/drmr/decisions.jsonl"
bash "$OLD" --selftest > "$T/st.old" 2>&1; "$LINT" --selftest > "$T/st.new" 2>&1 || fail "selftest failed: $(grep -v '^PASS' "$T/st.new" | head)"
while IFS= read -r l; do grep -qxF -- "$l" "$T/st.new" || fail "predecessor PASS line missing: $l"; done < <(grep '^PASS ' "$T/st.old")
for id in repair-grammar mission-repairs-missing repair-duplicate repair-missing repair-class-mismatch sweep-missing repair-author-mismatch repair-hash-mismatch repair-scope-mismatch affected-consumer-unreviewed repair-declined-unaccepted; do
  grep -q "^PASS refuse:$id:drfc-" "$T/st.new" || fail "selftest has no drfc refusal fixture for $id"
done
grep -q '^PASS pass:drfc-' "$T/st.new" || fail "selftest has no passing repaired-mission fixture"
pass "$n scope_ids; FIX then APPROVE; after alone; repairs unlisted; no token x2; approve-with-finding; drrec/drei/drmr; selftest"
