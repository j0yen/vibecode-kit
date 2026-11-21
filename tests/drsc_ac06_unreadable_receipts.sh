#!/usr/bin/env bash
# AC6 — a verdict file that exists with no read permission: review-file-missing naming
# it, the line labelled self (provenance.reviews self, and provenance.snapshot self: no
# verdict was read, so no snapshot binding was checked); a result= JSON that exists with
# no read permission: review-result-mismatch naming it as missing or not JSON, the line
# labelled self. Run over the verified note (role review), where both labels would
# otherwise be checked/verified. Fails, never skips, under euid 0. Review r23i LOW-3: a
# result= JSON nested too deeply to decode is review-result-mismatch, missing or not JSON;
# one that decodes but whose result str() cannot print (its depth taken between the two
# limits this host's stack sets) ends in the lint's ERROR line and exit 2; never a traceback.
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
python3 -I -c 'import sys; sys.stdout.write("[" * 200000 + "]" * 200000 + "\n")' > "$H/$RESULT"
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
expect_exact "$rc" 1 "$js" review-result-mismatch
out=$(lint 2>&1); l=$(findline review-result-mismatch "$out") || fail "deep result: $out"
printf '%s' "$l" | grep >/dev/null -F 'missing or not JSON' || fail "deep result: reason not named: $l"
win=$(python3 -I - <<'PY'
import json


def deepest(ok, lo=1000, hi=400000):
    while hi - lo > 1:
        m = (lo + hi) // 2
        lo, hi = (m, hi) if ok(m) else (lo, m)
    return lo


def decodes(n):
    try:
        json.loads("[" * n + "]" * n)
        return True
    except RecursionError:
        return False


def prints(n):
    v = []
    for _ in range(n - 1):
        v = [v]
    try:
        str(v)
        return True
    except RecursionError:
        return False


print(deepest(prints), deepest(decodes))
PY
) || fail "the depth probe did not run"
p=${win% *}; j=${win#* }
if [ "$p" -lt $(( j - 2000 )) ]; then
  d=$(( (p + j) / 2 ))
  python3 -I -c 'import sys; n = int(sys.argv[2]); sys.stdout.write("{\"type\": \"result\", \"is_error\": false, \"session_id\": \"%s\", \"result\": %s%s}\n" % (sys.argv[1], "[" * n, "]" * n))' \
    "$S_REV" "$d" > "$H/$RESULT"
  js=$(lint --json 2>"$T/err"); rc=$?; err=$(cat "$T/err"); no_traceback "$err"
  [ "$rc" = 2 ] && [ -z "$js" ] || fail "deep value ($d levels; str() prints $p, json decodes $j): rc=$rc ${js:0:200} ${err:0:300}"
  printf '%s\n' "$err" | grep >/dev/null '^ERROR an input is nested too deeply to check' || fail "deep value: no ERROR line: ${err:0:300}"
else
  echo "note: on this stack json decodes no list str() cannot print (str() $p, json $j), so the deep-value case is not run"
fi
cp "$T/home.orig/$RESULT" "$H/$RESULT"
pass
