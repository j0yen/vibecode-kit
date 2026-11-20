#!/usr/bin/env bash
# AC7 (R7, for the rules this build carries: R1 and R4) — the checked-in compatibility notes (the
# drmx_ac05 corpus: tests/fixtures/drrec, drei, drsp, drmr and drfc with every variant, each entry
# and --last, text and --json) lint at 43d5b39 (the installed tree these rules extend) and at the
# head with byte-identical text and equal JSON: none lists a path entry, an ambiguous basename or a
# legacy manifest whose one matrix differs from the adversarial= one, so no designed delta applies.
# Every drmx fixture case (tests/fixtures/drmx/mfx.py, dated after LEGACY_MATRIX_SINCE, basename
# entries only) lints identically too, text and JSON. --selftest: the head selftest passes, keeps
# every PASS line of the 43d5b39 selftest, and adds a failing fixture per built rule (R1
# dgmr-legacy-two-matrices; R4 dgmr-path-entry-undeclared and dgmr-path-entry-no-delta) beside its
# passing twin. Sensitivity controls: on dgmr paths-ok and legacy-one-before 43d5b39 refuses and
# the head passes, so the comparisons are not vacuous. Not built here (R2, R3, R5): AC7's merged
# chain review and its review-provenance-missing / review-snapshot-stale outcome, and the deltas
# R3 designs. drfc_ac02, drfc_ac04, drfc_ac05, drsp_ac05 and drmr_ac03 run unchanged in the family.
set -uo pipefail
# shellcheck source=tests/dgmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dgmr_lib.sh"
setup_mx; base43_lint; chmod +x "$T/base43.sh"
compat "$T/base43.sh" "$LINT" "$T/compat.tsv" || fail "compat differences: $(cat "$T/compat.tsv")"
head -1 "$T/compat.tsv"
n=0
for c in $(python3 -I "$MFX" --list); do
  mx "$c"
  for mode in text json; do
    a=(); [ "$mode" = json ] && a=(--json)
    o=$("$T/base43.sh" "$LOG" --last --prd-dir "$H" --decisions "$DEC" "${a[@]}" 2>&1); ro=$?
    w=$("$LINT" "$LOG" --last --prd-dir "$H" --decisions "$DEC" "${a[@]}" 2>&1); rw=$?
    [ "$ro" = "$rw" ] && [ "$o" = "$w" ] \
      || fail "drmx $c ($mode): 43d5b39 exit $ro, head exit $rw: $(diff <(printf '%s\n' "$o") <(printf '%s\n' "$w") | head -6)"
    n=$((n + 1))
  done
done
echo "drmx cases: $n runs per lint, 0 differing"
"$T/base43.sh" --selftest > "$T/st.old" 2>&1 || fail "43d5b39 selftest failed"
"$LINT" --selftest > "$T/st.new" 2>&1 || fail "head selftest failed: $(grep -v '^PASS' "$T/st.new" | head)"
while IFS= read -r l; do grep -qxF -- "$l" "$T/st.new" || fail "43d5b39 PASS line missing at head: $l"; done < <(grep '^PASS ' "$T/st.old")
for l in 'PASS pass:dgmr-legacy-one-matrix' 'PASS refuse:mission-scope-incomplete:dgmr-legacy-two-matrices' \
         'PASS pass:dgmr-path-entry-declared' 'PASS refuse:repair-hash-mismatch:dgmr-path-entry-undeclared' \
         'PASS refuse:repair-hash-mismatch:dgmr-path-entry-no-delta'; do
  grep -qxF -- "$l" "$T/st.new" || fail "head selftest lacks: $l"
done
for c in paths-ok legacy-one-before; do
  gx "$c"
  "$T/base43.sh" "$LOG" --last --prd-dir "$H" --decisions "$DEC" >/dev/null 2>&1; ro=$?
  "$LINT" "$LOG" --last --prd-dir "$H" --decisions "$DEC" >/dev/null 2>&1; rw=$?
  [ "$ro" = 1 ] && [ "$rw" = 0 ] || fail "sensitivity control $c: exit 43d5b39=$ro head=$rw, want 1 and 0"
done
pass "compat corpus and drmx cases identical at 43d5b39 and head; selftest keeps every 43d5b39 PASS line and adds R1/R4 fixtures; controls differ"
