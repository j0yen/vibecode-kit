#!/usr/bin/env bash
# Request 01 (A1296 Increment-2, e9d18227) item 2 — the write-time (producer-side) check, so a shortened slug cannot
# recur: `dream-run-note-lint.sh --verdicts <verdict file or result.json> --scope <manifest> [--json]` refuses every
# verdict line whose PRD-<slug>.md is not a basename of the manifest (verdict-slug-unscoped, naming the line number and
# the slug), and a file with no verdict line (verdict-lines-missing); it accepts the scope's own slugs (exit 0, `OK`),
# reads a result.json capture's `result` text, keeps prose and table rows out (Repair 7's verdict-line grammar), exits 2
# for an unreadable verdict file and reports a malformed manifest as review-scope-mismatch (as --scope-id). Usage
# errors exit 2. SKILL.md's whole-chain review and Review paragraphs name the check and the correction contract.
set -uo pipefail
# shellcheck source=tests/drvc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drvc_lib.sh"
setup_v
M="$H/$SNAP"
vchk() { OUT=$("$LINT" --verdicts "$1" --scope "$M" "${@:2}" 2>"$T/err"); RC=$?; ERRT=$(cat "$T/err"); no_traceback "$ERRT"; }
# the scope's own slugs, with prose and a table row beside them: accepted
printf '# verdicts\nrs-alpha APPROVE fable\nthe table below restates it\n| FIX and UNKNOWN hold | x |\nrs-beta FIX fable\n' > "$T/ok.txt"
vchk "$T/ok.txt"; [ "$RC" = 0 ] || fail "scoped: rc=$RC: $OUT $ERRT"
[ "$OUT" = "OK $T/ok.txt verdicts=2 scope=$ID_HAPPY" ] || fail "scoped: output: $OUT"
# the r1 shape: shortened slugs refused at write time, one line each, naming the line number
printf '# verdicts\nalpha APPROVE fable\nrs-beta FIX fable\nbeta FIX fable\n' > "$T/short.txt"
vchk "$T/short.txt"; [ "$RC" = 1 ] || fail "short: rc=$RC: $OUT"
[ "$(printf '%s\n' "$OUT" | grep -c '^FAIL verdict-slug-unscoped: ')" = 2 ] || fail "short: want two refusals: $OUT"
printf '%s\n' "$OUT" | grep >/dev/null -F "FAIL verdict-slug-unscoped: $T/short.txt: line 2: slug alpha: PRD-alpha.md is not among the basenames of scope $M" \
  || fail "short: alpha line 2 not named: $OUT"
printf '%s\n' "$OUT" | grep >/dev/null -F "line 4: slug beta: PRD-beta.md" || fail "short: beta line 4 not named: $OUT"
printf '%s\n' "$OUT" | grep >/dev/null -F "rs-beta" && fail "short: the scoped slug rs-beta is named: $OUT"
# --json: one object on stdout, text on stderr
vchk "$T/short.txt" --json; [ "$RC" = 1 ] || fail "json: rc=$RC"
[ "$(printf '%s' "$OUT" | jget 'd["findings"]')" = '["verdict-slug-unscoped"]' ] || fail "json: findings: $OUT"
[ "$(printf '%s' "$OUT" | jget '[x["slug"] for x in d["unscoped"]]')" = '["alpha", "beta"]' ] || fail "json: unscoped: $OUT"
[ "$(printf '%s' "$OUT" | jget 'd["scope_id"]')" = "\"$ID_HAPPY\"" ] || fail "json: scope_id: $OUT"
# a result.json capture is read by its result text
python3 -c 'import json; print(json.dumps({"type":"result","session_id":"s","result":"done\nalpha APPROVE fable\nrs-beta FIX fable"}))' > "$T/result.json"
vchk "$T/result.json"; [ "$RC" = 1 ] || fail "result: rc=$RC: $OUT"
printf '%s\n' "$OUT" | grep >/dev/null -F "line 2: slug alpha" || fail "result: alpha not refused: $OUT"
# no verdict line at all
printf '# verdicts\nnothing here\n' > "$T/none.txt"
vchk "$T/none.txt"; [ "$RC" = 1 ] || fail "none: rc=$RC: $OUT"
printf '%s\n' "$OUT" | grep >/dev/null "^FAIL verdict-lines-missing: $T/none.txt" || fail "none: $OUT"
# unreadable verdict file: exit 2
vchk "$T/absent.txt"; [ "$RC" = 2 ] || fail "absent: rc=$RC: $OUT"
printf '%s' "$ERRT" | grep >/dev/null '^ERROR ' || fail "absent: no ERROR line: $ERRT"
# malformed manifest: review-scope-mismatch, exit 1
printf 'not a manifest\n' > "$T/bad.sha256"
OUT=$("$LINT" --verdicts "$T/ok.txt" --scope "$T/bad.sha256" 2>&1); RC=$?
[ "$RC" = 1 ] || fail "bad manifest: rc=$RC: $OUT"
printf '%s\n' "$OUT" | grep >/dev/null '^FAIL review-scope-mismatch: scope ' || fail "bad manifest: $OUT"
# usage: --verdicts without --scope, or beside a log
"$LINT" --verdicts "$T/ok.txt" >/dev/null 2>&1; [ $? = 2 ] || fail "usage: --verdicts without --scope is not exit 2"
"$LINT" "$LOG" --verdicts "$T/ok.txt" --scope "$M" >/dev/null 2>&1; [ $? = 2 ] || fail "usage: --verdicts beside a log is not exit 2"
# SKILL.md names the write-time check and the correction contract
S="${DREAM_SKILL_MD:-$here/../skills/dream/SKILL.md}"
J=$(tr '\n' ' ' < "$S" | tr -s ' ')
for s in 'dream-run-note-lint.sh --verdicts' 'verdict-slug-unscoped' '.verdicts.corrected-<n>.jsonl' 'fresh review session' \
         'review-correction-self' 'review-correction-unlaunched' 'review-correction-verdict-changed' 'review-correction-lines-mismatch' \
         'review-correction-slug-unscoped' 'review-correction-slug-undenoted' 'review-correction-original-changed' \
         'review-correction-foreign' 'review-correction-grammar' 'review-correction-noop'; do
  printf '%s' "$J" | grep >/dev/null -F -- "$s" || fail "SKILL.md does not name $s"
done
# the lint's header lists every new finding id
for id in verdict-slug-unscoped verdict-lines-missing review-correction-self review-correction-unlaunched review-correction-verdict-changed \
          review-correction-lines-mismatch review-correction-slug-unscoped review-correction-slug-undenoted \
          review-correction-original-changed review-correction-foreign review-correction-grammar review-correction-noop; do
  sed -n '/^# Finding ids:/,/^#$/p' "$LINT" | grep >/dev/null -w -- "$id" || fail "the lint header's Finding ids do not list $id"
done
pass "the write-time check refuses shortened slugs (line and slug named, text and JSON, verdict file and result.json), a file with no verdict line and a malformed manifest, accepts the scope's slugs beside prose; SKILL.md and the lint header name the check and the correction ids"
