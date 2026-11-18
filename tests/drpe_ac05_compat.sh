#!/usr/bin/env bash
# AC5 (R1 held rule, R5, Migration) — a note with neither withdrawn= nor --packet-only lints
# byte-identically: the checked-in compatibility notes (tests/fixtures/drrec, drei, drsp, drmr and drfc
# with every variant, each entry and --last, text and --json) give equal text, stderr, exit and JSON,
# `mission` included, at 8559929e and after; and on bound manifests a row error held in a
# digest-matching repairs copy beside the latest bound manifest (three: frozen row 1's short sweep) and a
# matrix-rule failure on a bound manifest's frozen matrix (three with header matrices: m2's x2 holds no
# bar section) are each reported under held_packet_errors (HELD lines) with exit 0 from
# `--packet-only --pending`, governed.
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe; base_lint
compat "$T/base.sh" "$LINT" "$T/compat.tsv" || fail "compat differences: $(cat "$T/compat.tsv")"
head -1 "$T/compat.tsv"
pe held-row-copy; pk; rc0; pheld sweep-missing "row 1"
jtrue 'd["exit"] == 0 and any(e["id"] == "sweep-missing" for e in d["held_packet_errors"]) and not d["packet_errors"]' "held row error"
pe held-matrix; pk; rc0; pheld adversarial-slug-missing "manifest $M2:" "PRD-bar"
jtrue 'd["exit"] == 0 and any(e["id"] == "adversarial-slug-missing" for e in d["held_packet_errors"]) and not d["packet_errors"]' "held matrix-rule failure"
pass "compat corpus byte-identical; held row error and held matrix-rule failure under held_packet_errors, exit 0"
