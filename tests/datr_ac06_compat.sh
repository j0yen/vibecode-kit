#!/usr/bin/env bash
# AC6 (R7) — every fixture checked in at 43d5b39 (through tests/fixtures/drmx/compat.py: drrec home and
# verified, drei, drsp, and drmr and drfc with every variant; every entry and --last, text and --json; drmr, drfc
# and the drmx generator as re-dated before the cutover by tests/fixtures/redate.py, PRD amendment H1)
# and the 20 real Dream-log entries (CR6, 2026-11-19) at their own dates lint byte-identically (stdout, stderr, exit) with
# the Cited-tree lint and this one. The real entries come from DATR_REAL_LOGS: a directory of read-only
# copies of the four Dream logs with their SHA256SUMS (the A1723 continuation's carbon read CR6); without
# it the test cannot decide the real-entry half and exits 2 after the fixture half. Both lints read the
# same decisions log: the carbon copy decisions.jsonl when CR6 brought one, else one well-formed row of an
# unrelated skill (an empty log stops both lints at exit 2 before any entry check; code review 88ec4f26 F3),
# and at least one run must get past that step.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
base_lint "$T/base.sh"
python3 -I "$here/fixtures/drmx/compat.py" "$here/fixtures" "$T/base.sh" "$LINT" "$T/compat.tsv" False > "$T/compat.out" 2>&1 \
  || fail "fixtures: $(head -1 "$T/compat.tsv" | sed 's/^# //'); first: $(sed -n '2,4p' "$T/compat.tsv" | cut -f1-4 | tr '\n' ' ')"
[ -n "${DATR_REAL_LOGS:-}" ] || { echo "UNDECIDED $(basename "$0"): fixtures byte-identical ($(cat "$T/compat.out")); the real entries need DATR_REAL_LOGS (carbon read CR6)"; exit 2; }
(cd "$DATR_REAL_LOGS" && sha256sum -c --quiet SHA256SUMS) || fail "DATR_REAL_LOGS copies do not match their SHA256SUMS"
dec="$DATR_REAL_LOGS/decisions.jsonl"
if [ ! -f "$dec" ]; then
  dec="$T/dec.jsonl"
  printf '%s\n' '{"ts": "2026-01-01T00:00:00-08:00", "decision": "launch", "task_id": "none", "skill": "datr-unrelated", "route": "-", "model": "-", "effort": "-", "account": "-", "session": "00000000-0000-4000-8000-000000000000", "resume": false, "reasons": "datr ac06 fixture row"}' > "$dec"
fi
n=0; reached=0
for log in "$DATR_REAL_LOGS"/*.md; do
  rm -rf "$T/h"; mkdir -p "$T/h/notes"; cp "$log" "$T/h/notes/dream-log.md"
  while IFS= read -r ts; do
    for js in "" --json; do
      bash "$T/base.sh" "$T/h/notes/dream-log.md" --entry "$ts" --prd-dir "$T/h" --decisions "$dec" $js > "$T/o.out" 2> "$T/o.err"; ro=$?
      "$LINT" "$T/h/notes/dream-log.md" --entry "$ts" --prd-dir "$T/h" --decisions "$dec" $js > "$T/n.out" 2> "$T/n.err"; rn=$?
      [ "$ro" = "$rn" ] && cmp -s "$T/o.out" "$T/n.out" && cmp -s "$T/o.err" "$T/n.err" || fail "$(basename "$log") $ts ${js:-text}: differs (exit $ro/$rn)"
      [ "$rn" = 2 ] || reached=$((reached+1))
    done
    n=$((n+1))
  done < <(python3 -I - "$T/h/notes/dream-log.md" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
for m in re.finditer(r"^## (\S+)  /dream  vision-[^\n]*\n((?:(?!## ).*\n?)*)", t, re.M):
    if re.search(r"^Analysis:", m.group(2), re.M):
        print(m.group(1))
PY
)
done
[ "$n" = "${DATR_REAL_ENTRIES:-20}" ] || fail "linted $n governed real entries, want ${DATR_REAL_ENTRIES:-20}"
[ "$reached" -gt 0 ] || fail "every real-entry run exited 2 before the entry checks; the comparison decided nothing"
pass "fixtures byte-identical; $n real entries byte-identical at their own dates ($reached of $((2*n)) lint pairs past the decisions step; decisions: $dec)"
