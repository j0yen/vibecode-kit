#!/usr/bin/env bash
# Repair 3 (A1723 decision 3; followon7/dream/requests/source-03415-lint-contract-repairs-addendum-1.md) — a later amended
# row carrying "consolidates": [<row numbers>] is accepted when every listed row is amended with its before and after, its
# changed and sweep are the union of theirs, its author_session is theirs, and no listed row is consolidated twice; the
# duplicate check then judges it in place of the listed rows, whose repair-duplicate findings move to JSON
# repairs_historical. The original (A1723 rows 129-131 shape: amended rows 3-5 of (m1, m2), 3 and 4 naming PRD-foo.md, 3
# and 5 the edge map) is repair-duplicate twice. Positive: row 6 consolidates 3-5: clean, the two duplicates historical.
# Negatives, each repair-consolidation-mismatch with the duplicates current: a listed row of another manifest pair; changed
# omitting a file a listed row names; another author session; a row consolidated twice. Over-strict control: the
# installed rule (43d5b39), which cannot consolidate an append-only file, refuses the positive.
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
P="($M1, $M2)"; EB=drmx-mission.edges.jsonl
cx r3-original; run_mr; findings_eq '["repair-duplicate"]'
has_fail repair-duplicate "amended rows 3 and 4 of $P both name PRD-foo.md"; has_fail repair-duplicate "amended rows 3 and 5 of $P both name $EB"
cx r3-positive; run_mr; clean
jtrue 'sorted((h["id"], h["detail"], h["consolidated_by"]) for h in d["mission"]["repairs_historical"]) == [
        ("repair-duplicate", "amended rows 3 and 4 of '"$P"' both name PRD-foo.md", [6]),
        ("repair-duplicate", "amended rows 3 and 5 of '"$P"' both name '"$EB"'", [6])]' "rows 3-5's duplicates historical"
cx r3-other-pair; run_mr; findings_eq '["repair-consolidation-mismatch", "repair-duplicate"]'
has_fail repair-consolidation-mismatch "row 7: consolidates [3, 4, 5, 6]: row 6 is not an amended row of $P"
has_fail repair-duplicate "amended rows 3 and 4 of $P both name PRD-foo.md"
cx r3-omits-changed; run_mr; findings_eq '["repair-consolidation-mismatch", "repair-duplicate"]'
has_fail repair-consolidation-mismatch "row 6: consolidates [3, 4, 5]: changed ['PRD-foo.md'] is not the union of the listed rows' changed"
has_fail repair-duplicate "amended rows 3 and 4 of $P both name PRD-foo.md"
cx r3-other-session; run_mr; findings_eq '["repair-consolidation-mismatch", "repair-duplicate"]'
has_fail repair-consolidation-mismatch "row 6: consolidates [3, 4, 5]: row 3's author_session" "is not this row's"
has_fail repair-duplicate "amended rows 3 and 5 of $P both name $EB"
cx r3-twice; run_mr; findings_eq '["repair-consolidation-mismatch", "repair-duplicate"]'
has_fail repair-consolidation-mismatch "row 7: consolidates [3]: row 3 is consolidated by row 6 already"
for c in r3-other-pair r3-omits-changed r3-other-session; do
  cx "$c"; run_mr; jtrue '"repairs_historical" not in d["mission"]' "$c: nothing historical"
done
today r3-positive; findings_eq '["repair-duplicate"]'
pass "rows 129-131 shape refused; consolidated in place, duplicates historical; other pair, omitted file, other author, twice refused; the installed rule refuses the positive"
