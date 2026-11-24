#!/usr/bin/env bash
# Request 01 (A1296 Increment-2, e9d18227) item 1, positive — an append-only verdict correction bound to the original
# snapshot. The verified fixture's reviewer writes the shortened slugs `alpha` APPROVE and `beta` FIX (the r1 shape:
# PRD-alpha.md and PRD-beta.md are not in its scope manifest, which lists PRD-rs-alpha.md and PRD-rs-beta.md).
# Control: with no correction the note is refused (review-scope-mismatch naming alpha and beta, review-verdict-mismatch).
# Positive: <verdict file>.verdicts.corrected-1.jsonl, written by a fresh session whose launch row is role review on the
# original scope_id (resume false, launched after the review), naming the original file, its sha256 and session, and
# per original verdict line in order the full slug and the unchanged verdict word: clean; the JSON's review keeps the
# original text and records the correction; the original file and result= capture are byte-unchanged and still compared
# as written (review-result-mismatch stays live: a result= capture missing a line is refused with the correction read).
# The corrected APPROVE binds to the snapshot: rs-alpha edited after the review is review-snapshot-stale. A refused
# higher-numbered correction beside a valid one is reported and the valid one read (the highest valid n, as the sidecar
# correction). Over-strict control: the base lint (vibecode-kit 6ba4b87) refuses the positive.
set -uo pipefail
# shellcheck source=tests/drvc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drvc_lib.sh"
setup_v
# control: no correction, the original is refused
short_review; run
[ "$RC" = 1 ] || fail "control: rc=$RC: $OUT"
findline review-scope-mismatch "$OUT" | grep >/dev/null -F 'slug alpha: PRD-alpha.md is not among the basenames' || fail "control: alpha not refused: $OUT"
findline review-scope-mismatch "$OUT" | grep >/dev/null -F 'slug beta: PRD-beta.md is not among the basenames' || fail "control: beta not refused: $OUT"
findline review-verdict-mismatch "$OUT" >/dev/null || fail "control: no review-verdict-mismatch: $OUT"
# positive
sha_before=$(sha256sum "$H/$VERDICTS" "$H/$RESULT")
fresh_row; correction; run
[ "$RC" = 0 ] || fail "positive: rc=$RC: $OUT"
want_ids '[]' positive
[ "$(sha256sum "$H/$VERDICTS" "$H/$RESULT")" = "$sha_before" ] || fail "positive: the original file or its result= capture changed"
printf '%s' "$JS" | jget 'd["reviews"][0]["verdict_correction"]' > "$T/vc.json" || fail "positive: no verdict_correction: $JS"
python3 - "$T/vc.json" "$CORR" "$S_FRESH" "$H/$VERDICTS" <<'PY' || fail "positive: verdict_correction wrong: $(cat "$T/vc.json")"
import sys, json, hashlib
vc, corr, fresh, orig = sys.argv[1:]
d = json.load(open(vc))
assert d["file"] == corr, d
assert d["corrected_by"] == fresh, d
assert d["sha256"] == hashlib.sha256(open(orig, "rb").read()).hexdigest(), d
assert d["lines"] == [{"line": "alpha APPROVE fable", "slug": "rs-alpha", "verdict": "APPROVE"},
                      {"line": "beta FIX fable", "slug": "rs-beta", "verdict": "FIX"}], d
PY
[ "$(printf '%s' "$JS" | jget 'd["provenance"]["snapshot"]')" = '"verified"' ] || fail "positive: snapshot not verified: $JS"
# the result= capture is still compared with the original text
python3 -c 'import json,sys; print(json.dumps({"type":"result","is_error":False,"session_id":sys.argv[1],"result":"alpha APPROVE fable"}))' \
  "$S_REV" > "$H/$RESULT"
run; [ "$RC" = 1 ] || fail "result drift: rc=$RC: $OUT"
findline review-result-mismatch "$OUT" | grep >/dev/null -F 'file-not-in-result: beta FIX fable' || fail "result drift: not refused on the original text: $OUT"
# the corrected APPROVE pins the snapshot digest of PRD-rs-alpha.md
reset_v; short_review; fresh_row; correction
printf '\nedited after the review\n' >> "$H/built-prds/PRD-rs-alpha.md"
run; [ "$RC" = 1 ] || fail "stale: rc=$RC: $OUT"
want_ids '["review-snapshot-stale"]' stale
findline review-snapshot-stale "$OUT" | grep >/dev/null -F 'slug rs-alpha' || fail "stale: rs-alpha not named: $OUT"
# a refused correction-2 beside a valid correction-1: reported, correction-1 read
reset_v; short_review; fresh_row; correction
correction 'rows[:2]' 2
run; [ "$RC" = 1 ] || fail "two corrections: rc=$RC: $OUT"
want_ids '["review-correction-lines-mismatch"]' "two corrections"
findline review-correction-lines-mismatch "$OUT" | grep >/dev/null -F "$VERDICTS.verdicts.corrected-2.jsonl" || fail "two corrections: n=2 not named: $OUT"
[ "$(printf '%s' "$JS" | jget 'd["reviews"][0]["verdict_correction"]["file"]')" = "\"$CORR\"" ] || fail "two corrections: correction-1 not read: $JS"
# over-strict control: the base lint refuses the positive
git -C "$REPO" show 6ba4b87:skills/dream/scripts/dream-run-note-lint.sh > "$T/base.sh" 2>/dev/null || fail "git show 6ba4b87 failed"
chmod +x "$T/base.sh"
reset_v; short_review; fresh_row; correction
keep=$LINT; LINT="$T/base.sh"; run; LINT=$keep
[ "$RC" = 1 ] || fail "over-strict: the base lint accepts the positive: $OUT"
findline review-scope-mismatch "$OUT" | grep >/dev/null -F 'slug alpha' || fail "over-strict: base does not refuse alpha: $OUT"
pass "a fresh role-review session's correction of shortened slugs is read: clean, original text kept and still compared with result=, the corrected APPROVE pinned to the snapshot, a refused higher n reported; the base lint refuses the positive"
