#!/usr/bin/env bash
# AC8 — skills/dream/SKILL.md: Phase 2 names the reviewer launch with review.snapshot
# (paths absolute or relative to the manifest's own directory) and a pre-drawn
# --session-id; Phase 3's **Review:** paragraph says an APPROVE binds to the snapshot's
# bytes; Phase 4's reply labels include `snapshot`; tests/dream_analysis_skills_ref.sh
# exits 0. DREAM_SKILL_MD, when set, names the SKILL.md to check (as the ref test).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
f="${DREAM_SKILL_MD:-$here/../skills/dream/SKILL.md}"
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
[ -r "$f" ] || fail "skill file missing or unreadable: $f"
# section "<heading prefix>": lines under a `## ` heading up to the next; fenced `## ` lines are not headings
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$f"; }
para() { awk -v s="$1" 'index($0,s)==1{f=1} f&&/^$/{exit} f' | tr '\n' ' ' | tr -s ' '; }
p2=$(section '## Phase 2 — Vision')
launch=$(printf '%s\n' "$p2" | grep -n 'review\.snapshot' | head -1 | cut -d: -f1)
[ -n "$launch" ] || fail "Phase 2 does not name review.snapshot"
p2j=$(printf '%s\n' "$p2" | tr '\n' ' ' | tr -s ' ')
for s in 'review.snapshot' '--session-id' 'sha256sum' "relative to the manifest's" 'absolute'; do
  printf '%s' "$p2j" | grep >/dev/null -F -- "$s" || fail "Phase 2 reviewer launch does not name $s"
done
p3=$(section '## Phase 3 — Draft')
rv=$(printf '%s\n' "$p3" | para '**Review:**')
[ -n "$rv" ] || fail "Phase 3 has no **Review:** paragraph"
printf '%s' "$rv" | grep >/dev/null -F "binds to the snapshot's bytes" || fail "Phase 3 Review paragraph does not say an APPROVE binds to the snapshot's bytes: $rv"
printf '%s' "$rv" | grep >/dev/null -F 'APPROVE' && printf '%s' "$rv" | grep >/dev/null -iF 'new review' || fail "Phase 3 Review paragraph does not say a later edit needs a new review"
p4=$(section '## Phase 4 — Persist')
printf '%s\n' "$p4" | tr '\n' ' ' | tr -s ' ' | grep >/dev/null -F '`snapshot`' || fail "Phase 4 reply labels do not include \`snapshot\`"
for s in '`verified`' '`legacy`'; do
  printf '%s\n' "$p4" | tr '\n' ' ' | grep >/dev/null -F -- "$s" || fail "Phase 4 does not name the snapshot label $s"
done
out=$(bash "$here/dream_analysis_skills_ref.sh" 2>&1); rc=$?
[ "$rc" = 0 ] || fail "dream_analysis_skills_ref.sh rc=$rc: $out"
echo "PASS $(basename "$0")"
