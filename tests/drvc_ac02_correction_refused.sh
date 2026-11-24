#!/usr/bin/env bash
# Request 01 (A1296 Increment-2, e9d18227) item 3, negatives — each refused correction is never read (the original's
# short-slug failures stand) and is refused with its own finding id, the only review-correction-* id of the case:
#   review-correction-self             a correction by the original reviewer session; by the note's Route (author) session
#   review-correction-unlaunched       no launch row for the correcting session; its review row on another scope_id; a
#                                      resumed row; a row stamped before the original review's launch; a role author row; a
#                                      denied row; a correction beside a review bound by no role-review row (legacy)
#   review-correction-verdict-changed  a changed verdict word
#   review-correction-lines-mismatch   an added line; a dropped line; reordered lines; a changed original line text
#   review-correction-slug-unscoped    a full slug whose PRD-<slug>.md is not in the original manifest
#   review-correction-slug-undenoted   a scoped slug the original token does not denote (two slugs swapped; a scoped
#                                      original slug remapped)
#   review-correction-original-changed the original file edited after the correction
#   review-correction-foreign          a correction naming another review file; naming another reviewer session
#   review-correction-grammar          a line that is no JSON; an extra header key; an extra row key (an added verdict
#                                      field); a key repeated in one row; a slug that is no PRD slug; no row at all
set -uo pipefail
# shellcheck source=tests/drvc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drvc_lib.sh"
setup_v
# only_corr <id> <label>: refused, not read, and <id> is the case's only review-correction-* id
only_corr() {
  [ "$RC" = 1 ] || fail "$2: rc=$RC: $OUT"
  got=$(printf '%s' "$JS" | jget '[x for x in d["findings"] if x.startswith("review-correction-")]')
  [ "$got" = "[\"$1\"]" ] || fail "$2: review-correction ids $got, want [\"$1\"]: $OUT"
  findline "$1" "$OUT" | grep >/dev/null -F "$CORR" || fail "$2: $1 does not name $CORR: $OUT"
  not_read "$2"
}
case_() { reset_v; short_review; }
hdr() { printf '[dict(rows[0], %s)] + rows[1:]' "$1"; }
# self
case_; correction "$(hdr "corrected_by='$S_REV'")"; run; only_corr review-correction-self self-original
findline review-correction-self "$OUT" | grep >/dev/null -F "is the original reviewer session" || fail "self-original: detail: $OUT"
case_; fresh_row "$S_AUTH"; correction "$(hdr "corrected_by='$S_AUTH'")"; run; only_corr review-correction-self self-route
findline review-correction-self "$OUT" | grep >/dev/null -F "is the Route session" || fail "self-route: detail: $OUT"
# unlaunched
case_; correction; run; only_corr review-correction-unlaunched unlaunched-none
case_; fresh_row "$S_FRESH" 'dict(r, scope_id="0"*64)'; correction; run; only_corr review-correction-unlaunched unlaunched-scope
case_; fresh_row "$S_FRESH" 'dict(r, resume=True)'; correction; run; only_corr review-correction-unlaunched unlaunched-resume
case_; fresh_row "$S_FRESH" 'dict(r, ts="2026-11-16T04:05:00-08:00")'; correction; run; only_corr review-correction-unlaunched unlaunched-before
case_; fresh_row "$S_FRESH" 'dict(r, role="author")'; correction; run; only_corr review-correction-unlaunched unlaunched-author
case_; fresh_row "$S_FRESH" 'dict(r, decision="denied")'; correction; run; only_corr review-correction-unlaunched unlaunched-denied
case_; fresh_row "$S_FRESH" '[r, dict(r, ts="2026-11-16T04:08:00-08:00", scope_id="1"*64)]'; correction; run
only_corr review-correction-unlaunched unlaunched-latest-other-scope
case_; fresh_row; correction; decedit 'dict(r) if r.get("session") != "'"$S_REV"'" else {k: v for k, v in r.items() if k != "role"}'
run; [ "$RC" = 1 ] || fail "legacy: rc=$RC: $OUT"
got=$(printf '%s' "$JS" | jget '[x for x in d["findings"] if x.startswith("review-correction-")]')
[ "$got" = '["review-correction-unlaunched"]' ] || fail "legacy: $got: $OUT"
findline review-correction-unlaunched "$OUT" | grep >/dev/null -F "no role-review launch row" || fail "legacy: detail: $OUT"
[ "$(printf '%s' "$JS" | jget '"verdict_correction" in d["reviews"][0]')" = false ] || fail "legacy: the correction was read"
# verdict word
case_; fresh_row; correction '[rows[0], rows[1], dict(rows[2], verdict="APPROVE")]'; run; only_corr review-correction-verdict-changed verdict-word
# lines
case_; fresh_row; correction 'rows + [{"line": "gamma FIX fable", "slug": "rs-beta", "verdict": "FIX"}]'; run; only_corr review-correction-lines-mismatch line-added
case_; fresh_row; correction 'rows[:2]'; run; only_corr review-correction-lines-mismatch line-dropped
case_; fresh_row; correction '[rows[0], rows[2], rows[1]]'; run; only_corr review-correction-lines-mismatch line-reordered
case_; fresh_row; correction '[rows[0], dict(rows[1], line="alpha APPROVE other"), rows[2]]'; run; only_corr review-correction-lines-mismatch line-text
# slugs
case_; fresh_row; correction '[rows[0], rows[1], dict(rows[2], slug="zz-beta")]'; run; only_corr review-correction-slug-unscoped slug-unscoped
findline review-correction-slug-unscoped "$OUT" | grep >/dev/null -F "PRD-zz-beta.md" || fail "slug-unscoped: detail: $OUT"
case_; fresh_row; correction '[rows[0], dict(rows[1], slug="rs-beta"), dict(rows[2], slug="rs-alpha")]'; run; only_corr review-correction-slug-undenoted slug-swapped
reset_v; verdicts "rs-alpha APPROVE fable${NL}beta FIX fable${NL}" "rs-alpha APPROVE fable${NL}beta FIX fable" "$SHORT_STATE"
fresh_row; correction '[rows[0], {"line": "rs-alpha APPROVE fable", "slug": "rs-beta", "verdict": "APPROVE"}, rows[2]]'; run
[ "$RC" = 1 ] || fail "scoped-remapped: rc=$RC: $OUT"
got=$(printf '%s' "$JS" | jget '[x for x in d["findings"] if x.startswith("review-correction-")]')
[ "$got" = '["review-correction-slug-undenoted"]' ] || fail "scoped-remapped: $got: $OUT"
findline review-scope-mismatch "$OUT" | grep >/dev/null -F 'slug beta: PRD-beta.md' || fail "scoped-remapped: the original failure is gone: $OUT"
# original edited after the correction
case_; fresh_row; correction; printf '# a comment appended after the correction\n' >> "$H/$VERDICTS"; run; only_corr review-correction-original-changed original-edited
# another review
case_; fresh_row; cp "$H/$VERDICTS" "$H/notes/reviews/other-review.txt"
correction "$(hdr "corrects='notes/reviews/other-review.txt'")"; run; only_corr review-correction-foreign foreign-file
case_; fresh_row; correction "$(hdr "session='$S_OTHER'")"; run; only_corr review-correction-foreign foreign-session
# grammar
case_; fresh_row; correction '"not json\n"'; run; only_corr review-correction-grammar grammar-not-json
case_; fresh_row; correction "$(hdr "note='x'")"; run; only_corr review-correction-grammar grammar-header-key
case_; fresh_row; correction '[rows[0], dict(rows[1], verdicts=["FIX"]), rows[2]]'; run; only_corr review-correction-grammar grammar-row-key
case_; fresh_row; correction '[rows[0], "{\"line\": \"alpha APPROVE fable\", \"slug\": \"rs-alpha\", \"verdict\": \"APPROVE\", \"verdict\": \"APPROVE\"}", rows[2]]'
run; only_corr review-correction-grammar grammar-dup-key
case_; fresh_row; correction '[rows[0], dict(rows[1], slug="RS-alpha"), rows[2]]'; run; only_corr review-correction-grammar grammar-slug
case_; fresh_row; correction '""'; run; only_corr review-correction-grammar grammar-empty
pass "27 refused corrections, each with its own review-correction-* id and never read: self (2), unlaunched (8), verdict-changed, lines-mismatch (4), slug-unscoped, slug-undenoted (2), original-changed, foreign (2), grammar (6)"
