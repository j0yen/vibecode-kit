#!/usr/bin/env bash
# AC1 (R2, R4) — run3's shape reduced (tests/fixtures/drmx/mfx.py `run3`): three manifests, each
# listing the matrix its own frozen edges header names, a different matrix basename each round,
# and repaired rows naming the old and the new matrix in `changed` as run3's did. The head lint
# exits 0 with no finding, so no mission-scope-incomplete or repair-hash-mismatch names a matrix;
# so does the variant whose rows name only the old matrix. Control: the 8559929e lint refuses the
# same fixture with mission-scope-incomplete and repair-hash-mismatch naming a matrix (the defect
# this PRD removes), so the fixture exercises it.
set -uo pipefail
# shellcheck source=tests/drmx_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmx_lib.sh"
setup_mx; base_lint
for c in run3 run3-old; do
  mx "$c"; run_mr; clean
  printf '%s\n' "$ERR" | grep -E '^FAIL (mission-scope-incomplete|repair-hash-mismatch): .*-adversarial\.md' && fail "$c: a finding names a matrix"
  jtrue 'd["provenance"]["mission"] == "verified" and len(d["mission"]["scope_ids"]) == 3' "$c: verified over three manifests"
done
mx run3; o=$(bash "$T/base.sh" "$LOG" --last --prd-dir "$H" --decisions "$DEC" 2>&1); rc=$?
[ "$rc" = 1 ] || fail "control: 8559929e lint rc=$rc on run3 (want 1): $o"
printf '%s\n' "$o" | grep >/dev/null -E '^FAIL mission-scope-incomplete: .*lists no .*-adversarial\.md' || fail "control: no matrix mission-scope-incomplete at 8559929e: $o"
printf '%s\n' "$o" | grep >/dev/null -E '^FAIL repair-hash-mismatch: .*-adversarial\.md: claimed changed' || fail "control: no matrix repair-hash-mismatch at 8559929e: $o"
pass "run3 shape (rows naming old+new, and old only) exits 0 verified; 8559929e refuses it"
