#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 8 (R10) — skills/dream/SKILL.md Phase 4 names the `Consumption:` line (in the run-note template and its rule), the
# "Consuming analysis findings" paragraph with R2's grammar (`analysis-consumption.v1`, id, page, page_sha256, finding, binding, author_session,
# note) and the five bindings with their keys, and the consumption finding ids the lint checks; history.md names the `Consumption:` line, the five
# bindings and PRD dream-finding-consumption; notes written as the text says lint clean (tests/fixtures/dfcn/dfcnlog.py ac08 cases: a record at
# notes/consumption/<ISO-ts>-<slug>.jsonl using all five bindings, and a note that binds no page without the line); and every landed test that reads
# that text still passes: each test that reads SKILL.md or history.md and passes at the Cited tree (43d5b39), and the trigger record's own
# text test (datr_ac08_skill_text.sh, landed before this PRD).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"           # REPO, BASE_SHA, fail, pass, here
S="$REPO/skills/dream/SKILL.md"; HI="$REPO/skills/dream/history.md"
section() { awk -v h="$1" '/^```/{fence=!fence} !fence&&/^## /{f=(index($0,h)==1);next} f' "$S"; }
tpl=$(section '## Phase 4 — Persist' | awk '/^```/{n++; next} n==1')
printf '%s\n' "$tpl" | grep >/dev/null -xF 'Consumption: <record path>' || fail "Phase 4 template: no 'Consumption: <record path>' line"
p4=$(section '## Phase 4 — Persist' | tr '\n' ' ' | tr -s ' ')
for s in '**Consuming analysis findings.**' '`Consumption: <record path>`' 'notes/consumption/<ISO-ts>-<slug>.jsonl' '`analysis-consumption.v1`' \
         '`id` (unique in the file)' '`page_sha256`' '`falsifier` or `mechanism:<n>`' '`author_session`' '`note`' 'The five bindings' \
         '`requirement`: `prd`' '`kill` = {`script`, `sha256`, `string`}' 'AC 1 of a first PRD' '`control`' \
         '`repair`: `ask`, `owner` and `successor`' 'closes-after=row:<ask>' '--require-closed' \
         '`test`: `repo`, `commit` (40 hex) and `path`' '`residual`: `owner`, `evidence`' '`accepts <id>`' '`pending`: `owner`, `due`' \
         'binds nothing' 'cannot reach `eligible`' 'needs no line' '`consumption.held`' \
         '`consumption-missing`' '`consumption-grammar`' '`consumption-binding-invalid`' '`consumption-binding-not-discriminating`' \
         '`consumption-repair-unbound`' '`consumption-repair-unproven`' '`consumption-residual-unaccepted`' '`consumption-pending-overdue`' \
         '`consumption-receipt-only`' '`consumption-finding-unbound`' '`consumption-page-stale`' '`consumption-page-unparsed`' \
         '`canonical-unavailable`' '`falsifier-not-first`' '`consumption-blocked`'; do
  printf '%s' "$p4" | grep >/dev/null -F -- "$s" || fail "Phase 4 does not state '$s'"
done
hi=$(tr '\n' ' ' < "$HI" | tr -s ' ')
for s in '`Consumption:`' '`requirement`' '`repair`' '`test`' '`residual`' '`pending`' 'PRD dream-finding-consumption'; do
  printf '%s' "$hi" | grep >/dev/null -F -- "$s" || fail "history.md does not name $s"
done
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/base" "$T/cases"
out=$(python3 -I "$here/fixtures/dfcn/dfcnlog.py" --run ac08- "$REPO/skills/dream/scripts/dream-run-note-lint.sh" "$T/cases" 2>&1) \
  || fail "notes written as the text says: $(printf '%s\n' "$out" | grep -v '^PASS' | head -5)"
nc=$(printf '%s\n' "$out" | grep -c '^PASS')
git -C "$REPO" archive "$BASE_SHA" | tar -x -C "$T/base" || fail "git archive $BASE_SHA failed"
broke=""; pre=""; tails=""; n=0
for t in $(grep -l -E 'SKILL\.md|history\.md' "$here"/*.sh | xargs -n1 basename | grep -v -E '^(datr|dfcn)_|_lib\.sh$'); do
  [ -f "$T/base/tests/$t" ] || continue
  n=$((n+1))
  bash "$here/$t" < /dev/null > "$T/h.out" 2>&1 && continue
  if (cd "$T/base" && bash "tests/$t" < /dev/null > "$T/b.out" 2>&1); then broke="$broke $t"; tails="$tails
--- $t (here) ---
$(tail -n 15 "$T/h.out")"; else pre="$pre $t"; fi
done
[ -z "$broke" ] || fail "landed tests that read the skill text and pass at $BASE_SHA fail here:$broke$tails"
bash "$here/datr_ac08_skill_text.sh" < /dev/null > "$T/datr.out" 2>&1 || fail "the trigger record's text test fails: $(tail -n 3 "$T/datr.out")"
pass "Phase 4 and history.md name the Consumption: line, R2's grammar and the five bindings; $nc ac08 notes lint clean; $n landed text-reading tests still pass${pre:+ (failing at $BASE_SHA too:$pre)}; datr_ac08_skill_text.sh passes"
