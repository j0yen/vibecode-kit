#!/usr/bin/env bash
# AC5 (R2 legacy fallback, R5b scoped to headers carrying `matrix`) — the checked-in compatibility
# notes (tests/fixtures/drrec, drei, drsp, drmr and drfc with every variant, each entry and --last,
# text and --json; none carries `matrix`, and drfc's base and variants are missions split over two
# run entries) lint at 8559929e and after with byte-identical text and equal JSON, `mission`
# included; and --selftest keeps every expected finding: the head selftest passes and every PASS
# line of the 8559929e selftest (drfc-bar-dropped-unreviewed among them) is a PASS line of it.
# Sensitivity control: on a note whose headers carry `matrix` (tests/fixtures/drmx `run3`) the two
# lints differ (8559929e refuses it, the head passes), so the corpus comparison is not vacuous.
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx; base_lint
compat "$T/base.sh" "$LINT" "$T/compat.tsv" || fail "compat differences: $(cat "$T/compat.tsv")"
head -1 "$T/compat.tsv"
bash "$T/base.sh" --selftest > "$T/st.old" 2>&1 || fail "8559929e selftest failed"
"$LINT" --selftest > "$T/st.new" 2>&1 || fail "head selftest failed: $(grep -v '^PASS' "$T/st.new" | head)"
while IFS= read -r l; do grep -qxF -- "$l" "$T/st.new" || fail "8559929e PASS line missing at head: $l"; done < <(grep '^PASS ' "$T/st.old")
grep -qx 'PASS refuse:affected-consumer-unreviewed:drfc-bar-dropped-unreviewed' "$T/st.new" || fail "drfc-bar-dropped-unreviewed missing"
mx run3
bash "$T/base.sh" "$LOG" --last --prd-dir "$H" --decisions "$DEC" >/dev/null 2>&1; ro=$?
"$LINT" "$LOG" --last --prd-dir "$H" --decisions "$DEC" >/dev/null 2>&1; rn=$?
[ "$ro" = 1 ] && [ "$rn" = 0 ] || fail "sensitivity control: run3 (header matrix) exit 8559929e=$ro head=$rn, want 1 and 0"
pass "compat corpus byte-identical (text, JSON with mission); selftest keeps every 8559929e PASS line; header-matrix control differs"
