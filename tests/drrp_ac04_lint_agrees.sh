#!/usr/bin/env bash
# AC4 (R4) — the sentence and the lint cannot disagree. The landed SKILL.md carries R1's sentence
# in both paragraphs (the rule this test holds the lint to), and the installed lint, run on drfc
# fixture notes that cover the sentence's cases, agrees with it:
#   compliant   the base (manifests after the earliest `before` list the repairs file) and the
#               three-manifest variant: no mission-scope-incomplete for the repairs basename;
#   own-after   a row's own `after` frozen without the file: exactly that finding, naming the file
#               and `after` (beside it only the snapshot-stale the same omission causes under the
#               final mission=APPROVE);
#   out-of-order rows written out of `before` order (the later-written row names the earlier
#               `before`), `after` frozen without the file: exactly that finding, naming `after`;
#   between     a manifest frozen between a finding (r2's F4) and its row, without the file:
#               exactly that finding, naming `third`.
# The fixtures are tests/fixtures/drfc plus one mutation each (tests/fixtures/drrp/README.md).
set -uo pipefail
# shellcheck source=tests/drrp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrp_lib.sh"
SK="$REPO/skills/dream/SKILL.md"
for h in "$RP_H1" "$RP_H2"; do
  m=$(rp_missing "$(rp_para "$SK" "$h")")
  [ -z "$m" ] || fail "SKILL.md paragraph '$h' lacks R1's sentence (missing clause: $m); the lint enforces it"
done
setup_fc
# sic <n> <manifest>: exactly n mission-scope-incomplete lines name the repairs basename; with n=1 that
# line names <manifest>
sic() { local got; got=$(printf '%s\n' "$ERR" | grep -c "^FAIL mission-scope-incomplete: .*lists no $FC_RB ")
  [ "$got" = "$1" ] || fail "${CASE}: $got mission-scope-incomplete line(s) name $FC_RB, want $1: $ERR"
  [ "$1" = 0 ] || has_fail mission-scope-incomplete "$FC_RB" "manifest $2:"; }
# only <manifest>: the repairs-file finding is the only mission-scope-incomplete, and nothing but it
# and the mission-snapshot-stale of the omitted file on the last manifest fires
only() { sic 1 "$1"
  [ "$(printf '%s\n' "$ERR" | grep -c '^FAIL mission-scope-incomplete: ')" = 1 ] || fail "${CASE}: another mission-scope-incomplete: $ERR"
  jtrue 'set(d["findings"]) <= {"mission-scope-incomplete", "mission-snapshot-stale"} and "mission-scope-incomplete" in d["findings"]' "${CASE}: findings"
  printf '%s\n' "$ERR" | grep '^FAIL mission-snapshot-stale: ' | grep -vq "^FAIL mission-snapshot-stale: $FC_RB: " && fail "${CASE}: a snapshot-stale not about $FC_RB: $ERR"
  return 0; }
CASE=compliant-base; use base; run_fc; [ "$RC" = 0 ] || fail "$CASE: rc=$RC $ERR"; sic 0
CASE=compliant-three; use three; run_fc; [ "$RC" = 0 ] || fail "$CASE: rc=$RC $ERR"; sic 0
CASE=own-after; use base; mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  $FC_RB')]"; run_fc
only "$AFT"
CASE='out-of-order'; use three
redit 'R[:] = [R[2], R[0], R[1]]'
mansign "$AFT" "L[:] = [l for l in L if not l.endswith('  $FC_RB')]"; run_fc
python3 -c 'import json,sys; R=[json.loads(l) for l in open(sys.argv[1]) if l.strip()]; sys.exit(0 if R[0]["before"].endswith("after.sha256") and R[1]["before"].endswith("before.sha256") else 1)' "$H/$FC_RP" \
  || fail "$CASE: fixture rows are not out of before order"
only "$AFT"
CASE=between; use three; mansign "$THR" "L[:] = [l for l in L if not l.endswith('  $FC_RB')]"; run_fc
only "$THR"
pass "sentence in both paragraphs; compliant x2 clean; own-after, out-of-order, between: exactly the repairs-file finding"
