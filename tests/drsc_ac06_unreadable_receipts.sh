#!/usr/bin/env bash
# AC6 — a verdict file that exists with no read permission: review-file-missing naming
# it, the line labelled self (provenance.reviews self, and provenance.snapshot self: no
# verdict was read, so no snapshot binding was checked); a result= JSON that exists with
# no read permission: review-result-mismatch naming it as missing or not JSON, the line
# labelled self. Run over the verified note (role review), where both labels would
# otherwise be checked/verified. Fails, never skips, under euid 0.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
not_root
setup_v
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget '[d["provenance"]["reviews"], d["provenance"].get("snapshot")]')" = '["checked", "verified"]' ] \
  || fail "control: the readable note is not checked/verified: rc=$rc $js"
chmod 000 "$H/$VERDICTS"
[ -e "$H/$VERDICTS" ] && ! [ -r "$H/$VERDICTS" ] || fail "verdict file is readable after chmod 000"
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
expect_exact "$rc" 1 "$js" review-file-missing
out=$(lint 2>&1); l=$(findline review-file-missing "$out") || fail "verdicts: $out"
printf '%s' "$l" | grep >/dev/null -F "$VERDICTS" || fail "verdicts: path not named: $l"
[ "$(printf '%s' "$js" | jget '[d["provenance"]["reviews"], d["provenance"].get("snapshot")]')" = '["self", "self"]' ] \
  || fail "verdicts: labels not self: $js"
chmod 644 "$H/$VERDICTS"
chmod 000 "$H/$RESULT"
[ -e "$H/$RESULT" ] && ! [ -r "$H/$RESULT" ] || fail "result file is readable after chmod 000"
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
expect_exact "$rc" 1 "$js" review-result-mismatch
out=$(lint 2>&1); l=$(findline review-result-mismatch "$out") || fail "result: $out"
printf '%s' "$l" | grep >/dev/null -F "$RESULT" && printf '%s' "$l" | grep >/dev/null -F 'missing or not JSON' || fail "result: path/reason not named: $l"
[ "$(printf '%s' "$js" | jget 'd["provenance"]["reviews"]')" = '"self"' ] || fail "result: line not labelled self: $js"
[ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" != 'null' ] || fail "result: no snapshot label: $js"
chmod 644 "$H/$RESULT"
pass
