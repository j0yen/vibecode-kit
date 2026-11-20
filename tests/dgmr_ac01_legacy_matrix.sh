#!/usr/bin/env bash
# AC1 (R1) — the A1724 GEN1 shape: manifest m1, frozen with matrix x1 and an edges header without
# `matrix`, is first listed by entry 2, whose adversarial= names x2; entry 1 (no scope=) names x1.
# First listed before LEGACY_MATRIX_SINCE (every fixture date on 2026-11-17): m1 listing x1 alone
# passes (x1 is its matrix member, named by entry 1), and so does x1 named but failing the matrix
# grammar (a name suffices; the grammar is not read) and one unnamed matrix whose copy at its listed
# digest passes the grammar; m1 listing none, two, one unnamed stale matrix (sections for another
# slug), or one unnamed matrix whose frozen copy no longer hashes to its listed digest is
# mission-scope-incomplete naming x2 and the adversarial= rule. The
# same one-matrix shape on 2027-03-01, after the constant, and drmx `rename-no-header`, are
# mission-scope-incomplete as installed;
# with only the linted entry's header ts on 2027-03-01 and its Route decision= on 2026-11-17 it passes
# (an entry is dated by its Route decision= on a governed host); and a later round on 2027-03-01 (m3,
# r3, x3), linted last, keeps m1's legacy matrix (m1 is dated by the entry that first listed it);
# and a mission whose headers name `matrix` (rounds of three) lints clean.
set -uo pipefail
# shellcheck source=tests/dgmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dgmr_lib.sh"
setup_mx
since=$(grep -m1 '^LEGACY_MATRIX_SINCE = ' "$LINT" | sed 's/.*= "\(.*\)"/\1/')
[ -n "$since" ] || fail "the lint defines no LEGACY_MATRIX_SINCE"
python3 -c 'import sys,datetime as d; a,b,c=(d.datetime.fromisoformat(x) for x in sys.argv[1:4]); sys.exit(0 if a<b<c else 1)' \
  "${OLD_DAY}T23:59:59-08:00" "$since" "${NEW_DAY}T00:00:00-08:00" \
  || fail "LEGACY_MATRIX_SINCE $since is not between the two fixture days"
gx legacy-one-before; run_mr; clean
gx legacy-named-stale-before; run_mr; clean
gx legacy-unnamed-valid-before; run_mr; clean
gx legacy-route-before; run_mr; clean
gx legacy-later-entry; run_mr; clean
for c in legacy-none-before legacy-two-before legacy-stale-before legacy-unnamed-moved-before; do
  gx "$c"; run_mr; [ "$RC" = 1 ] || fail "$c: rc=$RC (want 1): $ERR"
  has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(gmxb $OLD_DAY 13)" \
    "matrix named by adversarial= (the header names none)"
done
gx legacy-one-after; run_mr; [ "$RC" = 1 ] || fail "legacy-one-after: rc=$RC (want 1): $ERR"
has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(gmxb $NEW_DAY 13)" \
  "matrix named by adversarial= (the header names none)"
mx rename-no-header; run_mr          # drmx's legacy header on its own day, after the constant: drmx R2 unchanged
has_fail mission-scope-incomplete "manifest notes/snapshots/m1/m1.sha256:" "lists no $(mxb 10)" "matrix named by adversarial= (the header names none)"
gx header-matrix; run_mr; clean
pass "one listed matrix (named, or unnamed and valid at its digest) passes before the constant; none, two, stale, moved and after-the-constant stay mission-scope-incomplete; header matrix unchanged"
