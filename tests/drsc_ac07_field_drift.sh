#!/usr/bin/env bash
# AC7 — field and scope drift against the launcher's record. Every row of the copied
# review-scope/rows.jsonl and of verified/decisions.jsonl has exactly the fourteen fields
# the launcher writes; every scope-vectors.tsv row recomputes through the lint's
# --scope-id as its canonical column says (a hex id printed equal, exit 0; refused:
# line-rule / refused:prd-repeat exit 1 with a detail naming the path and the line or
# basename; never a traceback; nonutf8 over bytes), and the launcher's own canonical text
# (awk basename, LC_ALL=C sort -u) agrees; the verified row's scope_id recomputes from its
# copied manifest; --selftest exits 0 with one fixture per new finding id and a passing
# verified fixture. Reads the fixture files in place (no glob over the tree, no writes).
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; T_ERR="$T/err"; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"
WANT="ts decision task_id skill route model effort account session resume reasons role scope scope_id"
for f in "$RSFIX/rows.jsonl" "$VFIX/decisions.jsonl"; do
  python3 - "$f" "$WANT" <<'PY' || fail "field drift in $f"
import sys,json
p,want=sys.argv[1],sys.argv[2].split()
n=0
for i,l in enumerate(open(p,encoding="utf-8").read().splitlines(),1):
    r=json.loads(l); n+=1
    assert sorted(r)==sorted(want), (i, sorted(set(r)^set(want)))
assert n==5, n
PY
done
TSV="$RSFIX/scope-vectors.tsv"
[ "$(head -1 "$TSV")" = "$(printf 'manifest\tcanonical\tlauncher')" ] || fail "scope-vectors.tsv header: $(head -1 "$TSV")"
rows=0
while IFS=$'\t' read -r man canon _launcher; do
  [ "$man" = manifest ] && continue
  rows=$((rows+1))
  out=$("$LINT" --scope-id "$RSFIX/$man" 2>"$T_ERR"); rc=$?
  no_traceback "$(cat "$T_ERR")"
  case "$canon" in
    refused:line-rule|refused:prd-repeat)
      [ "$rc" = 1 ] || fail "$man: rc=$rc want 1 ($canon): $out"
      [ "$(printf '%s\n' "$out" | wc -l)" = 1 ] || fail "$man: more than one detail line: $out"
      printf '%s' "$out" | grep -qF "review-scope-mismatch" && printf '%s' "$out" | grep -qF "$man" || fail "$man: detail names no id/path: $out"
      printf '%s' "$out" | grep -qF "${canon#refused:}" || fail "$man: detail does not name ${canon#refused:}: $out"
      if [ "$canon" = refused:line-rule ]; then printf '%s' "$out" | grep -qE 'line [0-9]+' || fail "$man: no line number: $out"
      else printf '%s' "$out" | grep -qF 'PRD-rs-alpha.md' || fail "$man: basename not named: $out"; fi ;;
    *)
      printf '%s' "$canon" | grep -qE '^[0-9a-f]{64}$' || fail "$man: canonical column '$canon' is neither hex nor refused:"
      [ "$rc" = 0 ] && [ "$out" = "$canon" ] || fail "$man: --scope-id rc=$rc '$out' want '$canon'"
      bc=$(LC_ALL=C awk '{n=split($2,p,"/"); print $1 "  " p[n]}' "$RSFIX/$man" | LC_ALL=C sort -u | sha256sum | cut -d' ' -f1)
      [ "$bc" = "$canon" ] || fail "$man: launcher canonical text gives $bc, tsv $canon" ;;
  esac
done < "$TSV"
[ "$rows" = 14 ] || fail "scope-vectors.tsv rows=$rows want 14"
h=$(awk -F'\t' '$1=="happy.sha256"{print $2}' "$TSV"); d=$(awk -F'\t' '$1=="dupline.sha256"{print $2}' "$TSV")
[ -n "$h" ] && [ "$h" = "$d" ] || fail "dupline ($d) is not happy ($h)"
[ "$(awk -F'\t' '$1=="dupprd.sha256"{print $2}' "$TSV")" = refused:prd-repeat ] || fail "dupprd not refused:prd-repeat"
# the verified row's scope_id recomputes from its copied manifest
vid=$(python3 -c 'import json,sys; print([r for r in map(json.loads,open(sys.argv[1])) if r["decision"]=="launch" and r["role"]=="review"][0]["scope_id"])' "$VFIX/decisions.jsonl")
[ "$("$LINT" --scope-id "$VFIX/home/$SNAP")" = "$vid" ] || fail "verified manifest does not recompute to $vid"
# usage: --scope-id without a value is exit 2, never a traceback
"$LINT" --scope-id >/dev/null 2>"$T_ERR"; rc=$?; [ "$rc" = 2 ] || fail "--scope-id without a path: rc=$rc"; no_traceback "$(cat "$T_ERR")"
# selftest: one passing refusal fixture per new finding id, a passing verified fixture
st=$("$LINT" --selftest 2>&1); rc=$?
[ "$rc" = 0 ] || fail "selftest rc=$rc: $(printf '%s\n' "$st" | grep -v '^PASS' | head -20)"
for id in review-scope-mismatch review-snapshot-stale; do
  printf '%s\n' "$st" | grep -q "^PASS refuse:$id:" || fail "selftest has no passing refusal fixture for $id"
done
printf '%s\n' "$st" | grep -q '^PASS pass:snapshot-verified' || fail "selftest has no passing verified fixture"
pass "$rows vectors; $(printf '%s\n' "$st" | tail -1)"
