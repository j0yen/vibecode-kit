#!/usr/bin/env bash
# AC2 (R1, R2) — a manifest lacking a prds member, the matrix, the edges file or a contract
# copy is mission-scope-incomplete naming it; a line-rule break, or two header contracts of
# one basename (both paths named), is mission-scope-mismatch; scope=m1,m2 whose m2 header adds
# a packet member and a contract exits 0 with two scope_ids; m1's frozen edges copy absent or
# differing is mission-scope-mismatch naming m1 and the copy; with no decisions log the
# binding is undecidable: no mission-review-missing, provenance.mission self.
set -uo pipefail
# shellcheck source=tests/drmr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drmr_lib.sh"
setup_mr
for b in PRD-b.md "$MR_MXB" "$MR_EB" x-contract.md drmr-vision.md; do
  use base; vedit "$MR_MAN" "L[:] = [l for l in L if not l.endswith('  $b')]"; run_mr
  has_id mission-scope-incomplete; has_fail mission-scope-incomplete "$b" "$MR_MAN"
done
use base; printf 'not a manifest line\n' >> "$H/$MR_MAN"; run_mr
has_fail mission-scope-mismatch "$MR_MAN" "line-rule"
use base; python3 - "$H/notes/missions/$MR_EB" <<'PY'
import sys, json
p = sys.argv[1]; L = open(p).read().split("\n"); h = json.loads(L[0])
h["external"].append({"name": "y", "contract": "other/x-contract.md"}); L[0] = json.dumps(h); open(p, "w").write("\n".join(L))
PY
run_mr; has_fail mission-scope-mismatch "contracts/x-contract.md" "other/x-contract.md"
use twomanifest; run_mr
[ "$RC" = 0 ] || fail "two manifests: rc=$RC $ERR"; findings_eq '[]'
jtrue 'len(d["mission"]["scope_ids"]) == 2 and d["mission"]["scope_id"] == d["mission"]["scope_ids"][1] and d["mission"]["scope_ids"][0] != d["mission"]["scope_ids"][1]' "two scope_ids"
use twomanifest; rm "${H:?}/notes/snapshots/t1/$MR_EB"; run_mr
has_fail mission-scope-mismatch "notes/snapshots/t1/snapshot.sha256" "notes/snapshots/t1/$MR_EB"
use twomanifest; printf '\n' >> "$H/notes/snapshots/t1/$MR_EB"; run_mr
has_fail mission-scope-mismatch "notes/snapshots/t1/snapshot.sha256" "notes/snapshots/t1/$MR_EB"
use base; setline Route "Route: ungoverned session=$S_MAUTH host=$(hostname)"; run_mr_ungov
[ "$RC" = 0 ] || fail "ungoverned: rc=$RC $ERR"; no_id mission-review-missing
jtrue 'd["provenance"]["mission"] == "self"' "ungoverned self"
pass "incomplete x5, line-rule, shared contract basename, two manifests, frozen copy x2, ungoverned"
