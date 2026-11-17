#!/usr/bin/env bash
# AC7 (R10, R9, R7, R1) — every recorded scope_id recomputes through --scope-id;
# tests/fixtures/drmr/README.md names every file under tests/fixtures/drmr/ (a backticked path
# relative to it, every variant included) and every scope_id its decisions files record (R10:
# "a README.md names every file and every recorded scope_id"); the drrec/ notes and the drei
# note lint as at 373ff679 (read by git show, sha256 acde611f…) once
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
# R10: the README names every fixture file and every recorded scope_id; an absent README names
# nothing, so each path and id is reported missing, one per line
python3 - "$MRFIX" "$T/readme.count" > "$T/readme.miss" <<'PY'
import json, os, sys
root, count = sys.argv[1:]
rp = os.path.join(root, "README.md")
text = open(rp, encoding="utf-8").read() if os.path.isfile(rp) else ""
files = sorted(os.path.relpath(os.path.join(d, f), root) for d, _, fs in os.walk(root) for f in fs)
files = [f for f in files if f != "README.md"]
ids = sorted({json.loads(l)["scope_id"] for d, _, fs in os.walk(root) if "decisions.jsonl" in fs
              for l in open(os.path.join(d, "decisions.jsonl"), encoding="utf-8")
              if l.strip() and json.loads(l).get("scope_id")})
for f in files:
    if f"`{f}`" not in text:
        print(f"missing file {f}")
for i in ids:
    if i not in text:
        print(f"missing scope_id {i}")
open(count, "w").write(f"{len(files)} {len(ids)}\n")
PY
read -r nf ni < "$T/readme.count" || fail "README check did not run"
[ "$nf" -gt 0 ] && [ "$ni" -gt 0 ] || fail "README check is vacuous: $nf files, $ni scope_ids"
if [ -s "$T/readme.miss" ]; then
  cat "$T/readme.miss"
  fail "tests/fixtures/drmr/README.md (R10) does not name $(grep -c '^missing file ' "$T/readme.miss") of $nf files and $(grep -c '^missing scope_id ' "$T/readme.miss") of $ni recorded scope_ids (listed above)"
fi
echo "ok README.md names all $nf fixture files and $ni recorded scope_ids"
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
pass "$n scope_ids; README names $nf files and $ni scope_ids; drrec/drei equal 373ff679 minus mission; selftest; single component; prefix"
