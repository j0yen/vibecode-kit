#!/usr/bin/env bash
# AC1 — a Review: line whose row carries role review, scope and scope_id, a manifest
# that recomputes to scope_id and lists every verdict slug, and APPROVE slugs whose
# PRD files hash to the manifest's digests: exit 0, provenance.snapshot verified, and
# with result= provenance.reviews checked; reviews[] carry role and scope_id. The same
# with scope written as an absolute path, and with the reviewer's rows [no role, review].
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
setup_v
check_ok() { # <case> <json> <rc>
  [ "$3" = 0 ] || fail "$1: rc=$3 $2"
  printf '%s' "$2" | python3 -c '
import sys,json
d=json.load(sys.stdin); sid=sys.argv[1]; rid=sys.argv[2]
assert d["exit"]==0 and d["findings"]==[], d["findings"]
p=d["provenance"]
assert p.get("snapshot")=="verified", ("snapshot", p)
assert p["reviews"]=="checked", ("reviews", p)
assert p["route"]=="boundary", ("route", p)
r=d["reviews"]
assert len(r)==1 and r[0].get("role")=="review" and r[0].get("scope_id")==sid and r[0]["session"]==rid, r
assert d["trust"]=="same-uid"
' "$ID_HAPPY" "$S_REV" || fail "$1: json: $2"
}
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
check_ok relative "$js" "$rc"
out=$(lint); [ "$?" = 0 ] && [ "$out" = "OK 2026-11-16T04:10:00-08:00" ] || fail "text: $out"
# scope written as an absolute path
decedit "dict(r,scope='$H/$SNAP') if r['session']=='$S_REV' and r['scope']=='$SNAP' else r"
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
check_ok absolute "$js" "$rc"
# an earlier row of the reviewer session without role, then the review row: binds
reset_v
decedit "[dict({k:v for k,v in r.items() if k not in ('role','scope','scope_id')},ts='2026-11-16T04:00:00-08:00'), r] if r['session']=='$S_REV' and r['decision']=='launch' else r"
js=$(lint --json 2>"$T/err"); rc=$?
check_ok earlier-legacy-row "$js" "$rc"
pass
