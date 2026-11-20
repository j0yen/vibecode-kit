#!/usr/bin/env bash
# AC4 — role binding by the session's latest launch row: a Review: session whose latest
# row is role author is review-provenance-missing (first failing field: role), even when
# an earlier row of that session has no role; a Route: matched row with role review is
# route-provenance-mismatch naming role=review; a reviewer-session equal to the Route
# session is review-self; a latest row with no role passes both role checks (legacy).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
setup_v
rev="r['session']=='$S_REV' and r['decision']=='launch'"
aut="r['session']=='$S_AUTH' and r['decision']=='launch'"
# earlier row without role, latest row role author
decedit "[dict({k:v for k,v in r.items() if k not in ('role','scope','scope_id')},ts='2026-11-16T04:00:00-08:00'), dict(r,role='author',scope='',scope_id='')] if $rev else r"
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
expect_exact "$rc" 1 "$js" review-provenance-missing
out=$(lint 2>&1); l=$(findline review-provenance-missing "$out") || fail "author: $out"
printf '%s' "$l" | grep >/dev/null -F 'first failing field: role' && printf '%s' "$l" | grep >/dev/null -F "$S_REV" || fail "author: field/session not named: $l"
[ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"self"' ] || fail "author: snapshot not self: $js"
# latest row with another role value
reset_v; decedit "dict(r,role='reviewer') if $rev else r"
out=$(lint 2>&1); l=$(findline review-provenance-missing "$out") || fail "other role: $out"
printf '%s' "$l" | grep >/dev/null -F 'first failing field: role' || fail "other role: field not named: $l"
# Route row with role review
reset_v; decedit "dict(r,role='review') if $aut else r"
js=$(lint --json 2>"$T/err"); rc=$?
expect_exact "$rc" 1 "$js" route-provenance-mismatch
out=$(lint 2>&1); l=$(findline route-provenance-mismatch "$out") || fail "route role: $out"
printf '%s' "$l" | grep >/dev/null -F 'role=review' || fail "route role: role=review not named: $l"
[ "$(printf '%s' "$js" | jget 'd["provenance"]["route"]')" = '"self"' ] || fail "route role: route label not self: $js"
# reviewer-session equal to the Route session: review-self as today
reset_v; setline Review "Review: $VERDICTS reviewer-session=$S_AUTH"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" review-self
# a latest row with no role passes both role checks: legacy
reset_v; decedit "{k:v for k,v in r.items() if k not in ('role','scope','scope_id')} if ($rev or $aut) else r"
js=$(lint --json 2>"$T/err"); rc=$?
[ "$rc" = 0 ] || fail "no role: rc=$rc $js $(cat "$T/err")"
[ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"legacy"' ] || fail "no role: snapshot not legacy: $js"
[ "$(printf '%s' "$js" | jget '[d["reviews"][0].get("role","<absent>"), d["reviews"][0].get("scope_id","<absent>")]')" = '[null, null]' ] \
  || fail "no role: reviews[] role/scope_id not null: $js"
pass
