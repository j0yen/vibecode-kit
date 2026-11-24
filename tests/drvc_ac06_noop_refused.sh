#!/usr/bin/env bash
# Review 4323f3ad finding F2: a correction that changes nothing (every row's slug equals its line's first token) is refused with its
# own id, review-correction-noop, and never read. Cases:
#   R23 (the reviewer's case, a1296-lint-verdict-correction-review-01 work/mytests/rv_neg.sh): the verified fixture's full-slug review
#       (rs-alpha APPROVE, rs-beta APPROVE) and an identity correction by a fresh role-review session: rc 1, findings exactly
#       [review-correction-noop], the correction not read
#   noop beside the r1 shape: the shortened-slug review with an identity mapping (alpha -> alpha, beta -> beta): review-correction-noop
#       (and its slugs are unscoped), the original's short-slug failures stand
#   partial (not a no-op): one shortened line corrected, one full-slug line kept: read, clean
# Known-bad control: the 9325ded lint reads R23 clean.
set -uo pipefail
# shellcheck source=tests/drvc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drvc_lib.sh"
setup_v
corr_ids() { printf '%s' "$JS" | jget '[x for x in d["findings"] if x.startswith("review-correction-")]'; }
read_vc() { printf '%s' "$JS" | jget '"verdict_correction" in d["reviews"][0]'; }
# R23: identity correction of a full-slug review
r23() { reset_v; fresh_row; correction '[rows[0], {"line": "rs-alpha APPROVE fable", "slug": "rs-alpha", "verdict": "APPROVE"},
                                              {"line": "rs-beta APPROVE fable", "slug": "rs-beta", "verdict": "APPROVE"}]'; }
r23; run
[ "$RC" = 1 ] || fail "R23: rc=$RC: $OUT"
want_ids '["review-correction-noop"]' R23
findline review-correction-noop "$OUT" | grep >/dev/null -F "$CORR" || fail "R23: the finding does not name $CORR: $OUT"
[ "$(read_vc)" = false ] || fail "R23: the no-op correction was read: $JS"
# identity mapping of the shortened slugs
reset_v; short_review; fresh_row
correction '[rows[0], dict(rows[1], slug="alpha"), dict(rows[2], slug="beta")]'; run
[ "$RC" = 1 ] || fail "short identity: rc=$RC: $OUT"
[ "$(corr_ids)" = '["review-correction-noop", "review-correction-slug-unscoped"]' ] || fail "short identity: $(corr_ids): $OUT"
not_read "short identity"
# partial: alpha -> rs-alpha corrected, rs-beta kept: not a no-op, read
reset_v; verdicts "alpha APPROVE fable${NL}rs-beta FIX fable${NL}" "alpha APPROVE fable${NL}rs-beta FIX fable" "$SHORT_STATE"
fresh_row; correction '[rows[0], rows[1], dict(rows[2], line="rs-beta FIX fable")]'; run
[ "$RC" = 0 ] || fail "partial: rc=$RC: $OUT"
want_ids '[]' partial
[ "$(read_vc)" = true ] || fail "partial: the correction was not read: $JS"
# known-bad control: the 9325ded lint reads R23
git -C "$REPO" show 9325ded:skills/dream/scripts/dream-run-note-lint.sh > "$T/d5.sh" 2>/dev/null || fail "git show 9325ded failed"
chmod +x "$T/d5.sh"
r23; keep=$LINT; LINT="$T/d5.sh"; run; LINT=$keep
[ "$RC" = 0 ] && [ "$(read_vc)" = true ] || fail "known-bad control: the 9325ded lint does not read R23 (rc=$RC): the test does not discriminate"
pass "a correction whose every slug equals its line's token is review-correction-noop and never read (R23 and the identity map of shortened slugs); a partial correction is read; the 9325ded lint read R23"
