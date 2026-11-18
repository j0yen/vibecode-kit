#!/usr/bin/env bash
# AC5 (R5) — skills/dream/history.md holds exactly one entry naming this PRD; it names the
# predecessor (PRD-dream-failure-class-sweep), native run2r and R1's sentence; and the drift test
# tests/dream_analysis_skills_ref.sh exits 0.
set -uo pipefail
# shellcheck source=tests/drrp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrp_lib.sh"
HM="$REPO/skills/dream/history.md"
# entries: top-level bullets `- **<title> (<date>...).**`, each up to the next top-level bullet
ents=$(awk '/^- \*\*/{n++} n{print n "\t" $0}' "$HM")
ids=$(printf '%s\n' "$ents" | grep -F 'dream-repairs-file-in-packet' | cut -f1 | sort -u)
[ -n "$ids" ] || fail "no history.md entry names dream-repairs-file-in-packet"
[ "$(printf '%s\n' "$ids" | wc -l)" = 1 ] || fail "more than one history.md entry names dream-repairs-file-in-packet: $ids"
e=$(printf '%s\n' "$ents" | awk -F'\t' -v k="$ids" '$1==k{sub(/^[^\t]*\t/,""); print}' | tr '\n' ' ' | sed 's/[[:space:]]\{1,\}/ /g')
printf '%s' "$e" | grep -qE '^- \*\*.*\(2026-11-[0-9][0-9][^)]*\)\.\*\*' || fail "the entry is not in the file's form '- **<title> (2026-11-..).**': $e"
for s in 'dream-failure-class-sweep' 'run2r' "$RP_SENTENCE"; do
  case "$e" in *"$s"*) ;; *) fail "the entry lacks: $s";; esac
done
out=$(bash "$REPO/tests/dream_analysis_skills_ref.sh" 2>&1) || fail "dream_analysis_skills_ref.sh: $out"
pass "one entry (PRD, predecessor, run2r, sentence); drift test exits 0"
