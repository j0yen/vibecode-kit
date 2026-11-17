#!/usr/bin/env bash
# AC8 (R2, R4) — the AC 2 withdrawal of m2 whose edges copy is unlisted, recorded as entry E2 (r2 on the
# replacement m2r returned APPROVE), then a later same-Task entry E3 whose scope= is extended by m3 (an
# amended bar, r3 APPROVE) and omits withdrawn=: the full lint on the note with E3 appended exits 0, no
# finding names m2 (the continuity pass skips it), and its mission.withdrawn equals AC 2's record for
# the same withdrawal (from `--packet-only --pending` on wd1-edges-unlisted).
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
pe wd1-edges-unlisted; pk; rc0
want=$(printf '%s' "$JS" | python3 -c 'import sys,json; print(json.dumps(json.load(sys.stdin)["mission"]["withdrawn"]))')
[ "$want" != "[]" ] || fail "AC 2 record is empty"
pe ac8; grep -q 'withdrawn=' "$P" && fail "E3 carries withdrawn= (it must inherit)"
full; rc0; findings_eq '[]'
printf '%s\n' "$ERR" | grep -F "$M2" | grep -v "$M2R" && fail "a line names the withdrawn m2: $ERR"
got=$(printf '%s' "$JS" | python3 -c 'import sys,json; print(json.dumps(json.load(sys.stdin)["mission"]["withdrawn"]))')
[ "$got" = "$want" ] || fail "mission.withdrawn $got, AC 2's $want"
jtrue 'd["provenance"]["mission"] == "verified" and "notes/snapshots/m2/m2.sha256" in d["mission"]["scope"] and len(d["mission"]["scope_ids"]) == 3' "E3 verified, m2 kept in scope=, three bound scope ids"
pass "E3 after a withdrawal: exit 0, no finding names m2, mission.withdrawn equals AC 2's"
