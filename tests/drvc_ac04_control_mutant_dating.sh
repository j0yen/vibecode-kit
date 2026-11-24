#!/usr/bin/env bash
# Request 01 (A1296 Increment-2, e9d18227), the correction's launch and the control-mutant newest-freeze rule (five-whys page e784471d
# mechanism 2, review lint-e784c P2). A verdict correction of an earlier freeze's chain review is written by a fresh session launched
# with role review on that freeze's scope_id, so its launch row always comes after the later freezes' reviews. That launch reviews no
# round: when the correction is read (valid, for a Review: line of the entry), its session is not a review launch that dates a freeze;
# when it is not read, the launch row stands as any review launch (fail closed).
# Fixture: tests/fixtures/drvc/vfx.py over the datr case cm-freezes-in-launch-order-none-unread (m0, m1, m2 reviewed in launch order).
#   fresh-row  the fresh session's row with no correction: control-mutants-missing naming m0 (the base rule, kept)
#   corrected  the row and a valid correction of m0's review: clean, unread []
#   refused    the row and a correction changing a verdict word: review-correction-verdict-changed and control-mutants-missing (m0)
# Control: the base lint (6ba4b87) refuses `corrected` with control-mutants-missing.
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
vrun fresh-row
[ "$RC" = 1 ] || fail "fresh-row: rc=$RC: $ERRT"
[ "$(cm 'd["findings"]')" = '["control-mutants-missing"]' ] || fail "fresh-row: findings: $(cm 'd["findings"]'): $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = '["notes/snapshots/m0/m.sha256"]' ] || fail "fresh-row: unread: $JS"
vrun corrected
[ "$RC" = 0 ] || fail "corrected: rc=$RC: $ERRT"
[ "$(cm 'd["findings"]')" = '[]' ] || fail "corrected: findings: $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = '[]' ] || fail "corrected: unread: $JS"
[ "$(cm 'd["reviews"][0]["verdict_correction"]["corrected_by"]')" = '"cccccccc-0000-4000-8000-00000000c0c3"' ] || fail "corrected: correction not read: $JS"
vrun refused
[ "$RC" = 1 ] || fail "refused: rc=$RC: $ERRT"
[ "$(cm 'sorted(d["findings"])')" = '["control-mutants-missing", "review-correction-verdict-changed"]' ] || fail "refused: findings: $(cm 'd["findings"]'): $ERRT"
[ "$(cm 'd["mission"]["control_mutants"]["unread"]')" = '["notes/snapshots/m0/m.sha256"]' ] || fail "refused: unread: $JS"
git -C "$REPO" show 6ba4b87:skills/dream/scripts/dream-run-note-lint.sh > "$T/base.sh" 2>/dev/null || fail "git show 6ba4b87 failed"
vrun corrected "$T/base.sh"
[ "$RC" = 1 ] || fail "over-strict: the base lint accepts the corrected variant"
[ "$(cm 'd["findings"]')" = '["control-mutants-missing"]' ] || fail "over-strict: base findings: $(cm 'd["findings"]')"
pass "a read correction's fresh session dates no freeze (clean); with no correction, or a refused one, its launch still makes m0 the newer freeze (control-mutants-missing); the base lint refuses the corrected variant"
