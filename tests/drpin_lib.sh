#!/usr/bin/env bash
# Shared helpers for the drpin_* tests (PRD-dream-route-pin-removal).
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$here/.." && pwd)"
SKILL="$REPO/skills/dream/SKILL.md"
DRIFT="$here/dream_analysis_skills_ref.sh"
ADOPTED=11cd41be9dbe07788113f1f9a6e5a67fbed3df9a
# R2's sentence, as the landed Phase routing paragraph carries it (joined to one line).
R2_SENTENCE='On a host without `.config/skill-routing/policy.json` and `fable-launch.sh` (redbaron and ryzen7 on 2026-11-14), `/dream` runs on the invoking session'"'"'s own model and effort; no pin stands in for the absent route, and the Phase 4 run note writes `Route: ungoverned`.'
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
pass() { echo "PASS $(basename "$0")${1:+: $1}"; exit 0; }
# frontmatter block (between the first two --- lines)
frontmatter() { awk 'NR==1&&$0!="---"{exit} NR==1{next} $0=="---"{exit} {print}' "$1"; }
# the Phase routing paragraph: from **Phase routing:** to the next blank line, joined
phase_routing() { awk '/^\*\*Phase routing:\*\*/{f=1} f&&/^$/{exit} f' "$1"; }
# insert a line into the frontmatter just before the closing ---
fm_insert() { awk -v L="$2" 'NR==1{print;next} !d&&$0=="---"{print L; d=1} {print}' "$1"; }
