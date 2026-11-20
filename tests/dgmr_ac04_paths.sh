#!/usr/bin/env bash
# AC4 (R4) — manifests at two depths (m1 in notes/snapshots/m1, m2 in notes/snapshots/deep/m2), five
# data/gN/graph.json listed by path in both, g2 and g4 moved. Undeclared, the two moved paths are
# repair-hash-mismatch naming each path; declared by path with their delta records they pass (a
# before-side lookup uses the resolved key, so the depths compare); a wrong delta pair, a path with
# no record, and a wrong delta.added digest are repair-hash-mismatch naming path and digests; added
# and removed paths with their records pass, and so does a changed path whose record sits under
# delta.added. A row without delta naming a path is repair-hash-mismatch per path ("needs its delta
# record"), never also undeclared. A bare graph.json in a row without delta (legacy) is listed in repairs.ambiguous with
# its five paths and never failed (and declares every path of that basename); in a row with delta it
# is repair-grammar naming the candidate paths. A header member listed twice in one manifest (the
# edges file; the repairs file by its frozen copy and its live path) is mission-scope-mismatch. Rows
# shaped like A1724 rows 16 and 41 (a changed path and an added path resolving outside the PRD home,
# at two depths, with their records) pass, and a wrong pair there names the outside path. An amended
# row naming PRD-bar.md by path is compared by basename: a sweep that omits the edges incident to
# PRD-bar.md is sweep-missing, the full sweep passes, and while the mission's last verdict is FIX the
# amended row holds bar (with the sweep omitted too, both fire).
set -uo pipefail
# shellcheck source=tests/dgmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dgmr_lib.sh"
setup_mx
D=notes/snapshots/deep/m2/m2.sha256
gx paths-plain; run_mr; findings_eq '["repair-hash-mismatch"]'
for g in g2 g4; do has_fail repair-hash-mismatch "../../../../data/$g/graph.json: changed but undeclared between notes/snapshots/m1/m1.sha256 and $D"; done
no_fail_g() { python3 -c 'import sys; sys.exit(1 if any(l.startswith("FAIL") and "data/"+sys.argv[2]+"/" in l for l in sys.argv[1].split("\n")) else 0)' "$ERR" "$1" \
  || fail "a FAIL line names $1: $ERR"; }
no_fail_g g1; no_fail_g g3; no_fail_g g5
gx paths-ok; run_mr; clean
gx paths-wrong-pair; run_mr; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "row 1: changed ../../../../data/g4/graph.json: delta before" "notes/snapshots/m1/m1.sha256 holds" "$D holds"
gx paths-no-record; run_mr; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "row 1: changed ../../../../data/g4/graph.json: no delta.changed record"
gx paths-added-removed; run_mr; clean
gx paths-changed-added; run_mr; clean
gx paths-added-wrong; run_mr; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "row 1: added ../../../../data/g6/graph.json: delta added" "notes/snapshots/m1/m1.sha256 holds none"
gx paths-legacy-path; run_mr; findings_eq '["repair-hash-mismatch"]'
for g in g2 g4; do has_fail repair-hash-mismatch "row 1: changed ../../../../data/$g/graph.json: a path entry needs its delta record (the row carries no delta)"; done
case "$ERR" in *"changed but undeclared"*) fail "paths-legacy-path: a declared path is also undeclared: $ERR";; esac
gx paths-legacy-bare; run_mr; clean
rep 'any(a["row"] == 1 and a["name"] == "graph.json" and len(a["paths"]) == 5 for a in m["ambiguous"])' "graph.json listed as ambiguous"
gx paths-ok; run_mr; jtrue '"ambiguous" not in d["mission"]["repairs"]' "repairs.ambiguous absent when empty"
gx paths-delta-bare; run_mr; findings_eq '["repair-grammar"]'
has_fail repair-grammar "row 1: changed graph.json: a bare basename that 5 entries" "../../../data/g1/graph.json" "../../../data/g5/graph.json"
gx paths-member-twice; run_mr; has_id mission-scope-mismatch
has_fail mission-scope-mismatch "manifest $D: header member drmx-mission.edges.jsonl occurs 2 times"
gx paths-repairs-twice; run_mr; findings_eq '["mission-scope-mismatch"]'
has_fail mission-scope-mismatch "manifest $D: header member drmx-mission.repairs.jsonl occurs 2 times"
gx paths-a1724-rows; run_mr; clean
gx paths-a1724-rows-wrong; run_mr; findings_eq '["repair-hash-mismatch"]'
has_fail repair-hash-mismatch "row 1: changed ../../../../../contract/EDIT-LOG.md: delta before" "notes/snapshots/m1/m1.sha256 holds"
gx paths-amended-unswept; run_mr; findings_eq '["sweep-missing"]'
has_fail sweep-missing "amended row (row 2)" "incident to PRD-bar.md"
gx paths-amended-swept; run_mr; clean
gx paths-amended-held; run_mr; no_id sweep-missing
jtrue 'any(x["slug"] == "bar" and "amended row 2" in x["reason"] for x in d["mission"]["dependent_slugs"])' "bar held by amended row 2"
gx paths-amended-unswept-held; run_mr; has_fail sweep-missing "amended row (row 2)" "incident to PRD-bar.md"
jtrue 'any(x["slug"] == "bar" and "amended row 2" in x["reason"] for x in d["mission"]["dependent_slugs"])' "bar held by amended row 2 (unswept)"
pass "path keys over two depths; undeclared, wrong pair, no record, no delta, added, removed, changed-as-added; legacy bare listed; delta bare refused; header member and repairs file twice; A1724 rows 16/41 outside the home; amended path swept and held by basename"
