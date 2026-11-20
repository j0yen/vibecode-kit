#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the dlcr_* tests: the Dream lint's producer-contract repairs of A1723 decision 3 (the PRD author's
# request followon7/dream/requests/source-03415-lint-contract-repairs.md, Repairs 1 and 2; its addendum 1, Repair 3;
# addendum 2, Repair 4, a sidecar consumer declared at the next freeze; addendum 3, Repair 5, a post-review matrix;
# addendum 4, Repair 6, a planned freeze never written, withdrawn).
# Reuses the dgmr helpers (setup_mx's private HOME, lint, run_mr, findings_eq, has_id, no_id, has_fail, jtrue, clean,
# base43_lint). `cx <case>` builds one case of tests/fixtures/dlcr/cfx.py into $W and points LOG, DEC and H at it.
# `today <case>` builds the case and lints it with the installed rule each repair extends (vibecode-kit 43d5b39): the
# over-strict control. DRREC_LINT runs the tests against another copy (known-bad controls).
# shellcheck source=tests/dgmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dgmr_lib.sh"
CFX="$here/fixtures/dlcr/cfx.py"
cx() { rm -rf "${W:?}"; python3 -I "$CFX" "$1" "$W" || fail "fixture $1 did not build"
  LOG="$W/home/notes/dream-log.md"; DEC="$W/decisions.jsonl"; H="$W/home"; CASE=$1; }
today() { cx "$1"; base43_lint; chmod +x "$T/base43.sh"; local keep=$LINT; LINT="$T/base43.sh"; run_mr; LINT=$keep; }
M1=notes/snapshots/m1/m1.sha256; M2=notes/snapshots/m2/m2.sha256; M3=notes/snapshots/m3/m3.sha256
