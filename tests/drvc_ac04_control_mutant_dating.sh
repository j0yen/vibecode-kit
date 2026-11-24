#!/usr/bin/env bash
# Request 01 (A1296 Increment-2, e9d18227): the correction's launch and the control-mutant newest-freeze rule (five-whys page e784471d
# mechanism 2, review lint-e784c P2). D5 of 9325ded (a read correction's session dated no freeze) is WITHDRAWN (review 4323f3ad F1,
# option A): a correction session's launch is a review launch like any other, read or not, because the decisions row of a correction
# launch and of a re-review launch have one shape. A correction of an earlier freeze's review therefore makes that freeze the newer one
# (control-mutants-missing) until the rule's own remedy: a later review launch of the last listed manifest, listed on a Review: line.
# Fixture: tests/fixtures/drvc/vfx.py over the datr case cm-freezes-in-launch-order-none-unread (m0, m1, m2 reviewed in launch order).
#   fresh-row     the fresh session's row with no correction: control-mutants-missing naming m0
#   identity      the row and an identity (no-op) correction of m0's review: review-correction-noop (F2) and control-mutants-missing
#   refused       as identity with a verdict word changed: + review-correction-verdict-changed
#   listed-later  the row, then a later listed chain review of m2: clean, unread [] (the remedy)
# Structure: control_mutant_check and its one call site are byte-identical to 6ba4b87's.
# Known-bad control: the 9325ded lint (D5) reads `identity` clean.
set -uo pipefail
# shellcheck source=tests/drrec_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
mkdir -p "$T/fakehome" "$T/cwd"
VFX="$here/fixtures/drvc/vfx.py"
# vrun <variant> [<lint>]: build the variant into $T/<variant> and lint it as dfx.py does; JSON in JS, stderr in ERRT, exit in RC
vrun() {
  local out="$T/$1"; rm -rf "$out"
  python3 -I "$VFX" "$1" "$out" >/dev/null || fail "$1: fixture did not build"
  JS=$(cd "$T/cwd" && env -u SKILL_ROUTING_DECISIONS -u ANALYSIS_WIKI_DIR HOME="$T/fakehome" SKILL_ROUTING_POLICY="$out/policy.json" \
       GIT_CONFIG_NOSYSTEM=1 bash "${2:-$LINT}" "$out/home/notes/dream-log.md" --last --prd-dir "$out/home" --json \
       --decisions "$out/decisions.jsonl" 2>"$T/err"); RC=$?
  ERRT=$(cat "$T/err"); case "$ERRT" in *Traceback*) fail "$1: traceback: $ERRT";; esac
}
cm() { printf '%s' "$JS" | jget "$1"; }
UNREAD_M0='["notes/snapshots/m0/m.sha256"]'
vrun fresh-row
[ "$RC" = 1 ] || fail "fresh-row: rc=$RC: $ERRT"
[ "$(cm 'd["findings"]')" = '["control-mutants-missing"]' ] || fail "fresh-row: findings: $(cm 'd["findings"]'): $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = "$UNREAD_M0" ] || fail "fresh-row: unread: $JS"
vrun identity
[ "$RC" = 1 ] || fail "identity: rc=$RC: $ERRT"
[ "$(cm 'sorted(d["findings"])')" = '["control-mutants-missing", "review-correction-noop"]' ] || fail "identity: findings: $(cm 'd["findings"]'): $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = "$UNREAD_M0" ] || fail "identity: unread: $JS"
[ "$(cm '"verdict_correction" in d["reviews"][0]')" = false ] || fail "identity: the no-op correction was read: $JS"
vrun refused
[ "$RC" = 1 ] || fail "refused: rc=$RC: $ERRT"
[ "$(cm 'sorted(d["findings"])')" = '["control-mutants-missing", "review-correction-noop", "review-correction-verdict-changed"]' ] \
  || fail "refused: findings: $(cm 'd["findings"]'): $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = "$UNREAD_M0" ] || fail "refused: unread: $JS"
vrun listed-later
[ "$RC" = 0 ] || fail "listed-later: rc=$RC: $ERRT"
[ "$(cm 'd["findings"]')" = '[]' ] || fail "listed-later: findings: $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = '[]' ] || fail "listed-later: unread: $JS"
# structure: the rule and its call site are the base's bytes
git -C "$REPO" show 6ba4b87:skills/dream/scripts/dream-run-note-lint.sh > "$T/base.sh" 2>/dev/null || fail "git show 6ba4b87 failed"
python3 - "$T/base.sh" "$LINT" <<'PY' || fail "control_mutant_check or its call site differs from 6ba4b87"
import sys, re
def parts(p):
    s = open(p, encoding="utf-8").read()
    fn = re.search(r"\ndef control_mutant_check\(.*?(?=\ndef )", s, re.S).group(0)
    call = re.search(r"\n *cm = control_mutant_check\(.*?\n *if cm is not None", s, re.S).group(0)
    return fn, call
b, h = parts(sys.argv[1]), parts(sys.argv[2])
assert b[0] == h[0], "control_mutant_check differs"
assert b[1] == h[1], "the call site differs"
PY
# known-bad control: 9325ded's D5 reads the identity correction and hides m0
git -C "$REPO" show 9325ded:skills/dream/scripts/dream-run-note-lint.sh > "$T/d5.sh" 2>/dev/null || fail "git show 9325ded failed"
vrun identity "$T/d5.sh"
[ "$RC" = 0 ] || fail "known-bad control: the 9325ded lint no longer reads the identity variant clean (rc=$RC): the test does not discriminate"
pass "a correction session's launch dates its freeze as any review launch (D5 withdrawn): fresh row, no-op and refused corrections give control-mutants-missing naming m0; a later listed review of the last manifest clears it; the rule and its call site are 6ba4b87's bytes; the 9325ded lint (D5) reads the no-op variant clean"
