#!/usr/bin/env bash
# Positive controls P1, P3, P4 (gate fix: superseded chain-review APPROVE pins, G1-G7).
# P1 (fixture, no mutation): K on manifest k APPROVEs a with result=; a's bytes change;
#   J on manifest j, launched later with result= and mission=APPROVE J, APPROVEs a on the
#   new bytes; `Mission: ... scope=k,j`. Expect exit 0, findings [], snapshot verified,
#   K's superseded == [{"slug":"a","by":J}], J has no superseded key, text `OK <ts>`.
# P3 (mutation: K also APPROVEs b, unchanged): b's pin is current, b not under superseded.
# P4 (mutation: K and J both APPROVE b, unchanged): b absent from K's superseded;
#   P4-only-b (mutation: K names only b): K's object has no superseded key.
# P3/P4's preservation half holds at base trivially (no superseded key at all); their
# discrimination is the G6.2 mutant (P4 turns red when K-stale is a constant True).
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
pos() { # <case> <python assertions on d (head --json)>
  pair "$1"
  printf '%s' "$JS" | python3 -c "import sys,json
d=json.load(sys.stdin); K,J='$S_K','$S_J'
r={x['session']:x for x in d['reviews']}
$2" 2>"$T/assert.err" || fail "$1: $(tail -1 "$T/assert.err") json=$JS text=$OUT"
}
if want P1; then
  mut P1
  pos P1 '
assert d["exit"]==0 and d["findings"]==[], ("findings", d["findings"])
assert d["provenance"]["snapshot"]=="verified", ("snapshot", d["provenance"])
assert d["provenance"]["reviews"]=="checked", ("reviews", d["provenance"])
assert r[K]["superseded"]==[{"slug":"a","by":J}], ("K superseded", r[K])
assert "superseded" not in r[J], ("J superseded", r[J])
assert list(r[K])==["file","session","result","role","scope_id","superseded"], ("K keys", list(r[K]))'
  [ "$RC" = 0 ] && [ "$(cat "$T/r/P1.head.txt.out")" = "OK $TS" ] || fail "P1: text rc=$RC: $OUT"
  case "$OUT" in *review-snapshot-stale*) fail "P1: review-snapshot-stale: $OUT";; esac
  echo "ok P1: exit 0, findings [], snapshot verified, K superseded [a by J]"
fi
pres_b='
assert "b" not in [x["slug"] for x in r[K].get("superseded",[])], ("b superseded", r[K])
assert not [x for x in d["reviews"] if x["session"]!=K and "superseded" in x], ("other superseded", d["reviews"])'
for c in P3 P4; do
  want "$c" || continue
  mut "$c"
  pos "$c" "$pres_b"
  printf '%s\n' "$OUT" | grep >/dev/null 'slug b:' && fail "$c: a finding names slug b: $OUT"
  echo "ok $c preservation: b's pin current, b not under superseded"
  pos "$c" '
assert d["exit"]==0 and d["findings"]==[] and d["provenance"]["snapshot"]=="verified", (d["findings"], d["provenance"])
assert r[K]["superseded"]==[{"slug":"a","by":J}], ("K superseded", r[K])'
  echo "ok $c: exit 0, K superseded exactly [a by J]"
done
if want P4-only-b; then
  mut P4-only-b
  pos P4-only-b '
assert d["exit"]==0 and d["findings"]==[], d["findings"]
assert "superseded" not in r[K] and "superseded" not in r[J], d["reviews"]'
  [ "$SAME" = 1 ] || fail "P4-only-b: head differs from base"
  echo "ok P4-only-b: no superseded key, base==head bytes"
fi
pass "P1 P3 P4 P4-only-b"
