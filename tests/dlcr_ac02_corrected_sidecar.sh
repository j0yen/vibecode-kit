#!/usr/bin/env bash
# Repair 2 (A1723 decision 3; followon7/dream/requests/source-03415-lint-contract-repairs.md) — a corrected sidecar
# <verdict>.findings.corrected-<n>.jsonl, first row {"corrects": <the original sidecar's sha256>, "session": <the chain
# review's session>}, written by that session resumed (a launch row with role review, the same scope_id and resume true),
# whose other rows are the original's in order changing only prds and consumers, is read for finding grammar and for the
# repairs rows' `changed`; the original's failures stay in JSON findings_historical and findings= still binds the
# original bytes. The original (review 12's R12-F3 shape: F1 names no PRD and an undeclared external) is
# mission-finding-incomplete and its repairs row repair-grammar. Positive: the corrected sidecar gives F1 its PRD and a
# member consumer: clean, the original failures historical. Negatives, each sidecar-correction-unbound with the original
# failures current: written by the author's session, by another reviewer, by r1's session with no resumed launch row;
# corrects naming another digest; a row changing id, class, counterexample, correction or control; review r21's L1 (the
# review's only launch row is the resume; the resume row is stamped before the review launch) and L2 (a row repeating a
# key, whose parsed value equals the original). Over-strict control:
# the installed rule (43d5b39), which reads only the original, refuses the positive.
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
SC=notes/reviews/r1/verdict.txt.findings.jsonl; CS=notes/reviews/r1/verdict.txt.findings.corrected-1.jsonl
cx r2-original; run_mr; findings_eq '["mission-finding-incomplete", "repair-grammar"]'
has_fail mission-finding-incomplete "$SC: row 1: field prds"; has_fail mission-finding-incomplete "$SC: row 1: field consumers"
has_fail repair-grammar "row 1: finding F1: changed names none of"
cx r2-positive; run_mr; clean
jtrue 'd["mission"]["chain_reviews"][0].get("sidecar_corrected") == "'"$CS"'" and d["mission"]["chain_reviews"][0]["sidecar_bound"] is True' \
  "r1 reads the corrected sidecar while findings= binds the original"
jtrue 'sorted(h["detail"].split(": field ")[1].split(":")[0] for h in d["mission"]["findings_historical"]
        if h["id"] == "mission-finding-incomplete" and h["corrected_by"] == "'"$CS"'") == ["consumers", "prds"]' \
  "the original's prds and consumers failures kept under findings_historical"
for c in r2-author-session r2-other-reviewer r2-no-resume-row r2-wrong-digest r2-changes-id r2-changes-class \
         r2-changes-counterexample r2-changes-correction r2-changes-control r2-resume-only-row r2-resume-before r2-dupkey \
         r2-dup-in-original; do
  cx "$c"; run_mr; findings_eq '["sidecar-correction-unbound", "mission-finding-incomplete", "repair-grammar"]'
  has_fail mission-finding-incomplete "$SC: row 1: field prds"
  jtrue '"findings_historical" not in d["mission"] and "sidecar_corrected" not in d["mission"]["chain_reviews"][0]' "$c: the correction is not read"
  case $c in
    r2-author-session) has_fail sidecar-correction-unbound "$CS: written by session" "not the chain review's own session";;
    r2-other-reviewer) has_fail sidecar-correction-unbound "$CS: written by session" "not the chain review's own session";;
    r2-no-resume-row) has_fail sidecar-correction-unbound "$CS: no launch row resumes session" "with role review and scope_id";;
    r2-wrong-digest) has_fail sidecar-correction-unbound "$CS: corrects" "is not the original sidecar's sha256";;
    r2-resume-only-row) has_fail sidecar-correction-unbound "$CS: session" "has no review launch row with scope_id" "that is not a resume";;
    r2-resume-before) has_fail sidecar-correction-unbound "$CS: no launch row resuming session" "is later than its review launch at";;
    r2-dupkey) has_fail sidecar-correction-unbound "$CS: a key repeated in one row (row 2: class)";;
    r2-dup-in-original) has_fail sidecar-correction-unbound "$CS: the original sidecar repeats a key in one row (row 1: class)";;
    r2-changes-id) has_fail sidecar-correction-unbound "$CS: row 2: id 'F9' is not original row 1's 'F1'";;
    *) has_fail sidecar-correction-unbound "$CS: row 2 (F1): changes ${c#r2-changes-}; only prds and consumers may change";;
  esac
done
today r2-positive; findings_eq '["mission-finding-incomplete", "repair-grammar"]'
pass "the original R12-F3 shape refused; the reviewer's own resumed correction read, the original failures historical; thirteen refused corrections (r21 L1 and L2, r23 L1 included); the installed rule refuses the positive"
