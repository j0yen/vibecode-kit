#!/usr/bin/env bash
# AC7 — the lint's --selftest holds every Cited-tree (43d5b39) PASS line verbatim, has no FAIL, and adds
# one datr-<case> line per R2-R5 refusal, each `PASS refuse:<id>:datr-<case>` (the selftest's refuse()
# requires the exact finding-id set): analysis-skip-refused (R2), analysis-grammar, analysis-reuse-stale
# and analysis-reuse-incomplete (R3), line-missing, failure-grammar and failure-class-mismatch (R4),
# analysis-trigger-unmet (R5); at least one passing datr fixture; and the datr-cutover-zone twin (R7's cutover
# instant, Q3 of A1723 source request 4): one instant written in two zones (-08:00 and Z, Z also as a lower-case z,
# review r20 F2), in the header and in a
# bound Route row's ts, passes just before the cutover and is refused (analysis-skip-refused) just after it, and an
# after-side instant at -10:00, whose date text is the day before, is refused too.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
base_lint "$T/base.sh"
bash "$T/base.sh" --selftest > "$T/base.out" 2>&1 || fail "43d5b39 selftest exit $?"
"$LINT" --selftest > "$T/head.out" 2>&1 || fail "selftest exit $?: $(grep -v '^PASS' "$T/head.out" | head -5)"
grep -qE '^(FAIL|ERROR)' "$T/head.out" && fail "selftest FAIL lines: $(grep -E '^(FAIL|ERROR)' "$T/head.out" | head -3)"
nb=0
while IFS= read -r l; do grep -qxF -- "$l" "$T/head.out" || fail "43d5b39 PASS line missing: $l"; nb=$((nb+1)); done < <(grep '^PASS ' "$T/base.out")
for id in analysis-skip-refused analysis-grammar analysis-reuse-stale analysis-reuse-incomplete line-missing failure-grammar failure-class-mismatch analysis-trigger-unmet; do
  grep -qE "^PASS refuse:$id:datr-" "$T/head.out" || fail "no datr refusal line for $id"
done
grep -q '^PASS pass:datr-' "$T/head.out" || fail "no passing datr fixture"
for w in header route; do
  for z in pst utc utcz; do
    grep -qxF "PASS pass:datr-cutover-zone-$w-before-$z" "$T/head.out" || fail "no passing datr-cutover-zone-$w-before-$z line"
    grep -qxF "PASS refuse:analysis-skip-refused:datr-cutover-zone-$w-after-$z" "$T/head.out" || fail "no refused datr-cutover-zone-$w-after-$z line"
  done
  grep -qxF "PASS refuse:analysis-skip-refused:datr-cutover-zone-$w-after-hst" "$T/head.out" || fail "no refused datr-cutover-zone-$w-after-hst line"
done
pass "$nb 43d5b39 PASS lines kept; $(grep -c '^PASS .*datr-' "$T/head.out") datr lines"
