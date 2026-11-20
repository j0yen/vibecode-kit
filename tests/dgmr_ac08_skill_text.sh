#!/usr/bin/env bash
# AC8 (R8, the items of the rules this build carries: R1 and R4) — SKILL.md Phase 3 states the
# legacy-matrix rule (its constant, how an entry is dated, the one listed matrix kept when named or
# passing --matrix at its digest, the fallback) in the Adversarial pass paragraph and the repair
# row's paths, `delta`, the ambiguous listing and the repairs file as a basename-keyed header member
# in the failure-class paragraph; history.md has one entry naming dream-generation-aware-mission-
# records whose LEGACY_MATRIX_SINCE value is the lint's; notes that follow the text lint clean, ones
# that break it get the named finding; the drift test exits 0. Not built here: R8's `lineage` (R5),
# the generation each entry judges (R3) and `sidecar=` (R2) items, and AC8's `Review: none` entry
# merging a FIX chain review (R3).
set -uo pipefail
# shellcheck source=tests/dgmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dgmr_lib.sh"
f="$REPO/skills/dream/SKILL.md"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
para() { printf '%s\n' "$1" | awk -v h="$2" 'index($0,h)==1{f=1} f&&/^[[:space:]]*$/{exit} f' | tr '\n' ' ' | sed 's/[[:space:]]\{1,\}/ /g'; }
p3=$(section '## Phase 3 — Draft')
adv=$(para "$p3" '**Adversarial pass')
# shellcheck disable=SC2016  # literal backticks of the skill text
for s in 'first listed before `LEGACY_MATRIX_SINCE`' 'dated by its `Route:` line'"'"'s `decision=`, else by its header ts' \
  'lists exactly one `*-adversarial.md` keeps that one as its matrix member' 'not later than the linted one names it' \
  'its copy at the listed digest passes `--matrix`' 'listing none, two or more, or one neither named nor passing, it keeps the rule above'; do
  case "$adv" in *"$s"*) ;; *) fail "Phase 3 Adversarial pass paragraph lacks '$s'";; esac
done
rep=$(para "$p3" '**After the first systemic finding')
# shellcheck disable=SC2016
for s in 'is keyed by that path' '`changed` and `added` relative to the `after` manifest'"'"'s directory' \
  '`removed` relative to the `before` manifest'"'"'s' '`delta` record `{changed: [{path, before, after}], added: [{path, sha256}], removed: [{path, sha256}]}`' \
  'sits under `delta.added` is served by it' 'A row without `delta` is a legacy row' '`repairs.ambiguous`, never failed' \
  'a row with `delta` names such a file by path' 'the edges file, and the repairs file) is keyed by its basename in every pass' \
  'a row without `delta` that names one by path is checked by its basename'; do
  case "$rep" in *"$s"*) ;; *) fail "Phase 3 failure-class paragraph lacks '$s'";; esac
done
e=$(awk '/^- \*\*/{n++} n{print n "\t" $0}' "$REPO/skills/dream/history.md" | awk -F'\t' '{a[$1]=a[$1] " " $2} END{for(k in a) print a[k]}' | grep -F 'dream-generation-aware-mission-records')
[ "$(printf '%s\n' "$e" | grep -c .)" = 1 ] || fail "history.md: want one entry naming dream-generation-aware-mission-records, got: $e"
since=$(grep -m1 '^LEGACY_MATRIX_SINCE = ' "$LINT" | sed 's/.*= "\(.*\)"/\1/')
# shellcheck disable=SC2016
case "$e" in *'`LEGACY_MATRIX_SINCE` = '"$since "*) ;; *) fail "history.md entry does not record LEGACY_MATRIX_SINCE = $since: $e";; esac
setup_mx
for c in legacy-one-before paths-ok; do gx "$c"; run_mr; clean; done
gx legacy-two-before; run_mr; has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(gmxb $OLD_DAY 13)"
gx paths-delta-bare; run_mr; findings_eq '["repair-grammar"]'
out=$(bash "$REPO/tests/dream_analysis_skills_ref.sh" 2>&1) || fail "dream_analysis_skills_ref.sh: $out"
pass "Phase 3 legacy-matrix and path-key rules; history records the constant; text-following notes clean; violations named; drift test"
