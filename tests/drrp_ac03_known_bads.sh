#!/usr/bin/env bash
# AC3 (R1-R3) — known-bad copies of the landed SKILL.md make tests/drfc_ac08_skill_text.sh exit 1
# naming the paragraph and the missing clause: the sentence removed from the **Whole-chain review
# paragraph, from the repair paragraph, present only in Phase 4, or kept with its prefix while
# dropping "later than the earliest `before`" or "including that row's own `after`" (each drop in
# each paragraph). Each copy is first checked to lack the sentence in the extracted paragraph, so
# a copy that removed some other line cannot pass for a known-bad. An empty DREAM_SKILL_MD exits 2
# naming it (Technical considerations, edge cases); a missing or unreadable one is refused as the
# landed test refuses it (exit 1 naming the path).
set -uo pipefail
# shellcheck source=tests/drrp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrp_lib.sh"
SK="$REPO/skills/dream/SKILL.md"
T=$(mktemp -d); trap 'chmod -R u+rw "$T"; rm -rf "$T"' EXIT
AC8="$REPO/tests/drfc_ac08_skill_text.sh"
for h in "$RP_H1" "$RP_H2"; do
  [ -z "$(rp_missing "$(rp_para "$SK" "$h")")" ] || fail "landed SKILL.md: paragraph '$h' lacks R1's sentence (the known-bads need a landed sentence to remove)"
done
# mk <name> <python statement on s (the whole file text), with S (the sentence) and P1/P2 (the
# two paragraph headings)>: write a copy
mk() { python3 - "$SK" "$T/$1.md" "$RP_SENTENCE" "$RP_H1" "$RP_H2" "$2" <<'PY' || fail "copy $1"
import sys, re
src, dst, S, P1, P2, stmt = sys.argv[1:]
s = open(src, encoding="utf-8").read()
def para_span(s, h):
    i = s.index("\n" + h) + 1
    j = s.find("\n\n", i)
    return i, (len(s) if j < 0 else j)
def sub_in(s, h, old, new):
    """Replace old (whitespace-flexible) inside the paragraph starting with heading h."""
    i, j = para_span(s, h)
    pat = r"\s+".join(re.escape(w) for w in old.split())
    seg, n = re.subn(pat, lambda m: new, s[i:j], count=1)
    assert n == 1, f"sentence not found in {h}"
    return s[:i] + seg + s[j:]
env = {"s": s, "S": S, "P1": P1, "P2": P2, "sub_in": sub_in}
exec(stmt, env)
open(dst, "w", encoding="utf-8").write(env["s"])
PY
}
# run1 <name> <paragraph heading> <clause substring>: the copy lacks the sentence in that paragraph,
# drfc_ac08 on it exits 1 with a FAIL line naming the paragraph and the clause
run1() { local c="$T/$1.md" out rc
  [ -n "$(rp_missing "$(rp_para "$c" "$2")")" ] || fail "$1: fixture still carries R1's sentence in '$2'"
  out=$(DREAM_SKILL_MD="$c" bash "$AC8" 2>&1); rc=$?
  [ "$rc" = 1 ] || fail "$1: drfc_ac08 rc=$rc (want 1): $out"
  printf '%s\n' "$out" | grep -F "paragraph '$2' lacks R1's sentence" | grep -qF -- "$3" \
    || fail "$1: no FAIL naming paragraph '$2' and clause '$3': $out"
}
mk no-wc "s = sub_in(s, P1, S, '')"
run1 no-wc "$RP_H1" "${RP_CLAUSES[0]}"
mk no-repair "s = sub_in(s, P2, S, '')"
run1 no-repair "$RP_H2" "${RP_CLAUSES[0]}"
mk phase4-only "s = sub_in(sub_in(s, P1, S, ''), P2, S, ''); s = s.replace('After appending the note, run', S + ' After appending the note, run', 1)"
grep -qF "$RP_SENTENCE After appending the note" "$T/phase4-only.md" || fail "phase4-only: the sentence was not placed in Phase 4"
run1 phase4-only "$RP_H1" "${RP_CLAUSES[0]}"
run1 phase4-only "$RP_H2" "${RP_CLAUSES[0]}"
# shellcheck disable=SC2016
D1='later than the earliest `before` any row names, '; D2='including that row'"'"'s own `after`, '
for which in 1 2; do
  h=$RP_H1; [ "$which" = 2 ] && h=$RP_H2
  P=P$which
  mk "drop-before-$which" "s = sub_in(s, $P, S, S.replace('''$D1''', ''))"
  run1 "drop-before-$which" "$h" 'later than the earliest `before`'
  mk "drop-after-$which" "s = sub_in(s, $P, S, S.replace('''$D2''', ''))"
  run1 "drop-after-$which" "$h" "including that row's own \`after\`"
done
# empty path: exit 2 naming it (Technical considerations, edge cases); missing and unreadable paths
# keep the landed test's refusal (exit 1, "skill file missing or unreadable: <path>")
out=$(DREAM_SKILL_MD='' bash "$AC8" 2>&1); rc=$?
[ "$rc" = 2 ] && printf '%s' "$out" | grep -qF "''" || fail "empty path: rc=$rc: $out"
out=$(DREAM_SKILL_MD="$T/nope/SKILL.md" bash "$AC8" 2>&1); rc=$?
[ "$rc" = 1 ] && printf '%s' "$out" | grep -qF "skill file missing or unreadable: $T/nope/SKILL.md" || fail "missing path: rc=$rc: $out"
note=""
if [ "$(id -u)" != 0 ]; then
  cp "$SK" "$T/unreadable.md"; chmod 000 "$T/unreadable.md"
  out=$(DREAM_SKILL_MD="$T/unreadable.md" bash "$AC8" 2>&1); rc=$?
  [ "$rc" = 1 ] && printf '%s' "$out" | grep -qF "skill file missing or unreadable: $T/unreadable.md" || fail "unreadable path: rc=$rc: $out"
else note=" (unreadable case skipped as root)"; fi
pass "3 removal copies + 4 clause drops refused naming paragraph and clause; empty path exit 2, missing/unreadable path refused as landed$note"
