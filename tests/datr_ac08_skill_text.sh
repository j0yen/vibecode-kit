#!/usr/bin/env bash
# AC8 (R8) — skills/dream/SKILL.md Phase 1 names the typed Failure: line (its five classes, the routing
# policy's evidence.ref_pattern, the verdict-file floor); Phase 2 states R2 (`skipped: blocked
# decision=<ts>`, the outage reasons, no later launch for any task), R3 (`sha256=<64 hex>
# inputs=<manifest>`, `sha256sum -c` in the manifest's own directory), R5 (the three trigger classes,
# `page:<path>`, `skipped: transient`) and the `notes/analysis/` page home; history.md names PRD
# dream-analysis-trigger-record; notes written as the text says lint clean (dfx ac08 cases); and every
# landed test that reads that text and passes at the Cited-tree still passes.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
S="$REPO/skills/dream/SKILL.md"; HI="$REPO/skills/dream/history.md"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$S" | tr '\n' ' ' | tr -s ' '; }
p1=$(section '## Phase 1 — Research'); p2=$(section '## Phase 2 — Vision')
for s in 'Failure: none' 'Failure: <class> <ref> [<ref> ...]' '`recurring-failure`' '`failed-acceptance`' '`consequential-obstacle`' '`transient`' '`other`' \
         'evidence.ref_pattern' 'evidence.placeholders' "notes/reviews/" 'named on a `Review:` line or not'; do
  printf '%s' "$p1" | grep -qF -- "$s" || fail "Phase 1 does not state '$s'"
done
for s in 'skipped: blocked decision=<ts>' '`policy-missing:`' '`policy file not found`' '`policy is malformed`' '`malformed policy JSON: <Error>`' \
         '`ledger lookup unavailable; cannot verify ledger:<id> (fail closed)`' 'require_permission_mode' '(policy error, fail closed)' 'excuses no skip' 'A1300' \
         'for any task' 'live-worker' 'reused <page> sha256=<64 hex> inputs=<manifest>' 'sha256sum -c' "manifest's own directory" 'seed file' \
         'reused <page> sha256=<64 hex>`' 'page:<path>' 'skipped: transient' '`recurring-failure`, `failed-acceptance` and `consequential-obstacle`' 'notes/analysis/'; do
  printf '%s' "$p2" | grep -qF -- "$s" || fail "Phase 2 does not state '$s'"
done
grep -qF 'PRD dream-analysis-trigger-record' "$HI" || fail "history.md does not name PRD dream-analysis-trigger-record"
cases ac08
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/base"
git -C "$REPO" archive "$BASE_SHA" | tar -x -C "$T/base" || fail "git archive $BASE_SHA failed"
broke=""; pre=""; n=0
for t in $(grep -l -E 'SKILL\.md|history\.md' "$here"/*.sh | xargs -n1 basename | grep -v -E '^datr_|_lib\.sh$'); do
  [ -f "$T/base/tests/$t" ] || continue
  n=$((n+1))
  bash "$here/$t" < /dev/null > "$T/h.out" 2>&1 && continue
  if (cd "$T/base" && bash "tests/$t" < /dev/null > "$T/b.out" 2>&1); then broke="$broke $t"; else pre="$pre $t"; fi
done
[ -z "$broke" ] || fail "landed tests that read the skill text and pass at $BASE_SHA fail here:$broke"
pass "text states R2, R3, R5 and notes/analysis/; $CASES_PASSED ac08 notes lint clean; $n landed text-reading tests still pass${pre:+ (failing at $BASE_SHA too:$pre)}"
