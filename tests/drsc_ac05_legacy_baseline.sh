#!/usr/bin/env bash
# AC5 — a Review: line whose row lacks role, scope and scope_id (today's drrec fixture,
# and the verified fixture with those three keys deleted from every row): findings, exit
# and every provenance label but snapshot equal the baseline, the JSON equals it once
# provenance.snapshot, reviews[].role and reviews[].scope_id are deleted, the text output
# is identical, and provenance.snapshot is legacy. The baseline is recorded at run time by
# the predecessor lint (git show 7d4c70ff:skills/dream/scripts/dream-run-note-lint.sh,
# sha256 16fe0c6f...) over the same copied fixture bytes; nothing here is hand-written.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
BASE_COMMIT=7d4c70ff6e3b243c930a39b8ca828b08bac2e1a9
BASE_SHA=16fe0c6f4f432d0db2076e8c1bfc9883f3f29441fec006f6e2b56b8843636e54
OLD=$(mktemp); trap 'rm -f "$OLD"' EXIT
git -C "$REPO" show "$BASE_COMMIT:skills/dream/scripts/dream-run-note-lint.sh" > "$OLD" 2>/dev/null \
  || fail "predecessor lint not readable by git show $BASE_COMMIT (shallow clone?)"
[ "$(sha256sum "$OLD" | cut -d' ' -f1)" = "$BASE_SHA" ] || fail "predecessor lint sha256 differs from $BASE_SHA"
chmod +x "$OLD"
ncase=0
same() { # <case>: old vs new over the current temp fixture, JSON and text
  local c=$1 jo jn ro rn to tn
  jo=$(bash "$OLD" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --json 2>/dev/null); ro=$?
  jn=$(lint --json 2>"$T/err"); rn=$?; no_traceback "$(cat "$T/err")"
  [ "$ro" = "$rn" ] || fail "$c: exit old=$ro new=$rn"
  printf '%s\n%s\n' "$jo" "$jn" | python3 -c '
import sys,json
o,n=(json.loads(x) for x in sys.stdin.read().split("\n")[:2])
assert n["provenance"].get("snapshot")=="legacy", ("snapshot", n["provenance"])
assert n["findings"]==o["findings"] and n["exit"]==o["exit"], (o["findings"], n["findings"])
for k,v in o["provenance"].items(): assert n["provenance"][k]==v, (k, o["provenance"], n["provenance"])
assert all(r.get("role") is None and r.get("scope_id") is None for r in n["reviews"]), n["reviews"]
assert n.pop("mission") is None and n["provenance"].pop("mission") == "none", n   # edge-map R5: added keys, no Mission: line
del n["provenance"]["snapshot"]
for r in n["reviews"]:
    del r["role"]; del r["scope_id"]
assert n==o, (o, n)
' || fail "$c: JSON differs from the baseline: old=$jo new=$jn"
  to=$(bash "$OLD" "$LOG" --last --prd-dir "$H" --decisions "$DEC" 2>&1)
  tn=$(lint 2>&1)
  [ "$to" = "$tn" ] || fail "$c: text differs: old=$to new=$tn"
  ncase=$((ncase+1))
}
# today's drrec fixture and one-element mutations of it (rows have no role/scope/scope_id)
setup; trap 'rm -rf "$T" "$OLD"' EXIT
cp "$DEC" "$T/dec.orig"; cp "$LOG" "$T/log.orig"; cp -r "$H" "$T/home.orig"
restore() { cp "$T/dec.orig" "$DEC"; cp "$T/log.orig" "$LOG"; rm -rf "$H"; cp -r "$T/home.orig" "$H"; }
same drrec-fixture
python3 -c 'import json,sys; print(json.dumps({"type":"result","is_error":False,"session_id":sys.argv[1],"result":"Done.\nfoo APPROVE fable"}))' "$S_R1" > "$H/notes/reviews/review-A.json"
setline Review "Review: notes/reviews/review-A.txt reviewer-session=$S_R1 result=notes/reviews/review-A.json"
same drrec-checked
restore; printf 'foo FIX fable\n' > "$H/notes/reviews/review-A.txt"
same drrec-verdict-mismatch
restore; printf 'x' >> "$H/built-prds/PRD-foo.md"
same drrec-edited-stub
restore; rm "$H/notes/reviews/review-A.txt"
same drrec-file-missing
rm -rf "$T"
# the verified fixture with role, scope and scope_id deleted from every row
setup_v; trap 'rm -rf "$T" "$OLD"' EXIT
decedit "{k:v for k,v in r.items() if k not in ('role','scope','scope_id')}"
cp "$DEC" "$T/dec.orig"
same verified-keys-deleted
printf 'x' >> "$H/built-prds/PRD-rs-alpha.md"
same verified-keys-deleted-edited-stub
pass "$ncase cases equal the predecessor lint's output"
