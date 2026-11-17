#!/usr/bin/env bash
# AC8 (R11) — SKILL.md Phase 3 carries, before **Adversarial pass**, the paragraph
# "Whole-chain review (before the first independent review)": the packet freeze with external
# contract copies, review.snapshot, the attack sentence, the five finding fields, the six
# classes, the findings= and mission= lines and the one-name-per-mission rule; Phase 4's labels
# include `mission` and the lint step names the seven new ids; history.md names R3B5-05;
# tests/dream_analysis_skills_ref.sh exits 0. DREAM_SKILL_MD, when set, names the SKILL.md.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
T_OUT=$(mktemp); trap 'rm -f "$T_OUT"' EXIT
f="${DREAM_SKILL_MD:-$REPO/skills/dream/SKILL.md}"
[ -r "$f" ] || fail "skill file missing or unreadable: $f"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
p3=$(section '## Phase 3 — Draft' | tr '\n' ' ' | tr -s ' ')
wc=$(printf '%s' "$p3" | grep -o 'Whole-chain review (before the first independent review).*') || fail "Phase 3 lacks the whole-chain review paragraph"
printf '%s' "$wc" | grep -qF '**Adversarial pass' || fail "the whole-chain review paragraph is not before **Adversarial pass**"
wc=${wc%%\*\*Adversarial pass*}
# shellcheck disable=SC2016  # literal backticks of the skill text
for s in 'freeze' 'external' 'contract' 'review.snapshot' 'sha256sum -c' 'satisfies every local AC while failing the mission' \
  counterexample 'affected consumers' 'minimal correction' 'discriminating control' 'failure class' \
  provenance missing-producer-runner authority-bypass unreachable-transition semantic-incompatibility false-green-acceptance \
  'findings=' '`mission=' 'result=' 'one `Mission:` name' 'appends'; do
  printf '%s' "$wc" | grep -qF -- "$s" || fail "whole-chain review paragraph lacks '$s'"
done
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
# shellcheck disable=SC2016
printf '%s' "$p4" | grep -qF -- '`mission`' || fail "Phase 4 reply labels do not include \`mission\`"
hdr=$(sed -n '1,80p' "$LINT")   # read once: `sed | grep -q` races SIGPIPE under pipefail
for id in mission-scope-mismatch mission-scope-incomplete mission-review-missing mission-verdict-missing mission-finding-incomplete mission-snapshot-stale mission-approval-blocked; do
  printf '%s' "$p4" | grep -qF -- "$id" || fail "Phase 4 lint step does not name $id"
  grep -q -- "$id" <<<"$hdr" || fail "lint header finding-id list lacks $id"
done
grep -q 'R3B5-05' "$REPO/skills/dream/history.md" || fail "history.md lacks R3B5-05"
bash "$REPO/tests/dream_analysis_skills_ref.sh" >"$T_OUT" 2>&1 || fail "dream_analysis_skills_ref.sh: $(tail -3 "$T_OUT")"
pass "Phase 3 whole-chain paragraph, Phase 4 mission label + ids, history R3B5-05, skills ref"
