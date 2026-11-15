#!/usr/bin/env bash
# AC7 — exit 2 (no JSON) for an empty or missing log or --decisions file; a failing
# entry under --json exits 1 with exit 1 and the ids in the object; foo=approved is
# state-grammar; no Route: is line-missing: Route; the drift test passes the landed
# SKILL.md and fails, by name, a copy lacking any R5 string.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
setup; cp "$LOG" "$T/log.orig"
: > "$T/empty.md"
out=$("$LINT" "$T/empty.md" --last --json --decisions "$DEC" 2>"$T/err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] && grep -q "$T/empty.md" "$T/err" || fail "empty log: rc=$rc out=$out err=$(cat "$T/err")"
out=$("$LINT" "$T/nope.md" --last --json --decisions "$DEC" 2>"$T/err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] && grep -q "$T/nope.md" "$T/err" || fail "missing log: rc=$rc"
out=$("$LINT" "$LOG" --last --json --prd-dir "$H" --decisions "$T/nodec.jsonl" 2>"$T/err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] && grep -q "$T/nodec.jsonl" "$T/err" || fail "missing decisions: rc=$rc"
: > "$T/emptydec.jsonl"
out=$("$LINT" "$LOG" --last --json --prd-dir "$H" --decisions "$T/emptydec.jsonl" 2>"$T/err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] && grep -q "$T/emptydec.jsonl" "$T/err" || fail "empty decisions: rc=$rc out=$out"
out=$("$LINT" "$LOG" --entry 1999-01-01T00:00:00Z --json --prd-dir "$H" --decisions "$DEC" 2>"$T/err"); rc=$?
[ "$rc" = 2 ] && [ -z "$out" ] || fail "unknown entry: rc=$rc"
setline State "State: foo=approved"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 1 ] || fail "approved: rc=$rc"
printf '%s' "$js" | python3 -c 'import sys,json; d=json.load(sys.stdin); assert d["exit"]==1 and d["findings"]==["state-grammar"], d' || fail "approved json: $js"
out=$(lint 2>&1); printf '%s\n' "$out" | grep -q '^FAIL state-grammar' || fail "approved text: $out"
cp "$T/log.orig" "$LOG"; setline Route ""
out=$(lint 2>&1); printf '%s\n' "$out" | grep -q '^FAIL line-missing: Route' || fail "no Route: $out"
js=$(lint --json 2>/dev/null); expect_exact "$?" 1 "$js" line-missing
# drift test (R5): landed passes; each R5 string removed from its section fails by name
D="$REPO/tests/dream_analysis_skills_ref.sh"; S="$REPO/skills/dream/SKILL.md"
o=$(env -u DREAM_SKILL_MD bash "$D" 2>&1) || fail "drift test on landed SKILL.md: $o"
while IFS='|' read -r sec str; do
  [ -n "$sec" ] || continue
  python3 - "$S" "$T/copy.md" "$sec" "$str" <<'PY' || fail "could not build copy lacking [$str] in $sec"
import sys,re
src,dst,sec,s=sys.argv[1:]
L=open(src).read().split('\n'); out=[]; inside=False; fence=False; n=0
for l in L:
    if l.startswith('```'): fence=not fence
    if not fence and l.startswith('## '): inside=l.startswith(sec)
    if inside and s.lower() in l.lower():
        l=re.sub(re.escape(s),'XXREMOVEDXX',l,flags=re.I); n+=1
    out.append(l)
open(dst,'w').write('\n'.join(out))
sys.exit(0 if n else 3)
PY
  o=$(DREAM_SKILL_MD="$T/copy.md" bash "$D" 2>&1); rc=$?
  [ "$rc" = 1 ] || fail "copy lacking [$str] in [$sec]: rc=$rc"
  printf '%s\n' "$o" | grep '^FAIL' | grep -qiF -- "$str" || fail "copy lacking [$str]: FAIL does not name it: $o"
done <<'LIST'
## Phase 4|Task:
## Phase 4|Route:
## Phase 4|Analysis:
## Phase 4|Review:
## Phase 4|State:
## Phase 4|adversarial=
## Phase 4|dream-run-note-lint.sh
## Phase 2|`ran
## Phase 2|`reused
## Phase 2|`skipped
## Phase 2|`inline`
## Phase 2|--session-id
## Phase 3|Adversarial pass
## Phase 3|still-broken implementation
## Phase 3|counterexample
## Phase 3|discriminating check
## Phase 3|`evidence`
## Phase 3|`invariant`
## Phase 3|Identity and provenance
## Phase 3|Boundary environment
## Phase 3|Evidence interpretation
## Phase 3|Alternative bypasses and ordering
## Phase 3|Falsifier quality
## Phase 3|Whole-scope coverage and handoff
## Phase 3|## PRD-<slug>
## Phase 3|### <family name>
## Phase 3|unconditional fallback:
## Phase 3|`conditional fallback:
## Phase 3|## Uncovered
## Phase 3|final message
LIST
# placement: an Adversarial pass paragraph moved after **Review:** fails
python3 - "$S" "$T/moved.md" <<'PY'
import sys
L=open(sys.argv[1]).read().split('\n')
i=next(k for k,l in enumerate(L) if l.startswith('**Adversarial pass'))
j=i
while j<len(L) and not L[j].startswith('**Review:**'): j+=1
para=L[i:j]; rest=L[:i]+L[j:]
r=next(k for k,l in enumerate(rest) if l.startswith('**Review:**'))
e=r
while e<len(rest) and rest[e].strip(): e+=1
out=rest[:e]+['']+para+rest[e:]
open(sys.argv[2],'w').write('\n'.join(out))
PY
o=$(DREAM_SKILL_MD="$T/moved.md" bash "$D" 2>&1); rc=$?
[ "$rc" = 1 ] && printf '%s\n' "$o" | grep -q '^FAIL.*before' || fail "moved paragraph not refused: rc=$rc $o"
pass
