#!/usr/bin/env bash
# Chain review 29 R29-F4 (A1723; lint owner 03415): a repaired row that follows its finding's decline may hold the decline's own pair,
# before = the issuing review's manifest and after = the next listed one, as the real record's row 164 (R12-F3) does after its
# decline in row 125; it may still hold a pair whose before is a later chain review's manifest. Refused as before: a before earlier
# than the issuing review's manifest, an after that is not the next listed manifest, and (the F49 literal of drfc_ac04) a later pair
# whose following review is bound earlier than its after, which reports that line alone. The drfc fixture (drfc_lib.sh), one
# mutation per case; each case runs in its own subshell, and the file passes only when every case does.
set -uo pipefail
# shellcheck source=tests/drfc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drfc_lib.sh"
setup_fc
DECL="dict(R[{i}], disposition='declined', reason='declined as a packet repair; repaired in place later')"
scm() { printf '%s\n' "$ERR" | grep -c '^FAIL repair-scope-mismatch: '; }
# F1 (chain review r1 on before): the decline inserted before its repaired row on (before, after)
rad_own_pair() { use base; redit "R.insert(0, ${DECL/\{i\}/0})"; run_fc
  [ "$RC" = 0 ] || fail "own pair: rc=$RC $ERR"; findings_eq '[]'
  rep 'm["rows"] == 3 and m["repaired"] == 2 and m["declined"][0]["superseded"] is True and m["declined"][0]["accepted_by"] is None' \
    "own pair: rows 3, the decline superseded"; }
# F4 (chain review r2 on after, the middle manifest): the decline inserted before its repaired row on (after, third)
rad_own_pair_mid() { use three; redit "R.insert(2, ${DECL/\{i\}/2})"; run_fc
  [ "$RC" = 0 ] || fail "own pair, middle issuer: rc=$RC $ERR"; findings_eq '[]'
  rep 'm["declined"][0]["finding"] == "F4" and m["declined"][0]["superseded"] is True' "own pair, middle issuer: F4 superseded"; }
# F4 declined, then repaired on (before, after): before is earlier than r2's manifest
rad_earlier_before() { use three; redit "R.insert(2, ${DECL/\{i\}/2}); R[3]['before'] = '$BEF'; R[3]['after'] = '$AFT'"; run_fc
  has_fail repair-scope-mismatch "row 4 (finding F4): before $BEF canonicalizes to" "the issuing review $R2D/verdict.txt is bound to"; }
# F1 declined on (before, after), then repaired on (before, third): after is not the next listed manifest
rad_far_after() { use three; redit "R.insert(0, ${DECL/\{i\}/0}); R[1]['after'] = '$THR'"; run_fc
  has_fail repair-scope-mismatch "row 2: after $THR is not the listed scope= manifest following before $BEF"; }
# the variant's later pair (after, third): r2 is bound earlier than third, that line alone (before is r2's manifest)
rad_later_pair() { use declined-repaired; run_fc
  has_fail repair-scope-mismatch "row 3: its following review $R2D/verdict.txt is bound to"
  [ "$(scm)" = 1 ] || fail "later pair: $(scm) repair-scope-mismatch lines, want 1: $ERR"; }
# a plain repaired row (no decline) on (after, third) for r1's F1: before is not r1's manifest
rad_plain_later() { use three; redit "R[0]['before'] = '$AFT'; R[0]['after'] = '$THR'"; run_fc
  has_fail repair-scope-mismatch "row 1 (finding F1): before $AFT canonicalizes to" "the issuing review $R1D/verdict.txt is bound to"; }
n=0 bad=""
for c in rad_own_pair rad_own_pair_mid rad_earlier_before rad_far_after rad_later_pair rad_plain_later; do
  n=$((n + 1)); out=$( "$c" ) || bad="$bad $c"
  [ -z "$out" ] || printf '%s: %s\n' "$c" "$out"
done
[ -z "$bad" ] || fail "cases failed:$bad"
pass "$n cases: own pair x2, earlier before, far after, later pair, plain later"
