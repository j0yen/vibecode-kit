#!/usr/bin/env bash
# Q5 (A1723 source request 6, ruled A by the PRD author; the contract text is in PRD-dream-finding-consumption's case-11
# gate clause): --scope-root <recorded root>=<this run's PRD home>. On the drrec verified note, the review row's scope
# is rewritten to an absolute path under another host's root, absent here (the A1113 shape).
#   positive: with the map the note lints as the relative original does (exit 0, snapshot verified), and the JSON
#     records the map and the read with both paths (scope_roots, reviews[].scope_read); a trailing slash names the same
#     root, and a scope whose .. stays under the root is read under it
#   over-strict: the literal path (no map, today's rule) refuses the positive: review-scope-mismatch, unreadable
#   negative 1: a map onto a home whose manifest differs: review-scope-mismatch naming the recorded scope, the path read,
#     the root and the row's scope_id
#   negative 2: a scope under no recorded root stays unreadable: another root, a root that is only a string prefix, a
#     scope leaving the root by ..; nothing is read under the map
#   negative 3 (the lint's half; the gate refuses a root the delivery does not name): a map onto another directory, a
#     root of /, a relative root, a value without exactly one '=', two roots where one holds the other, a root that
#     holds this run's PRD home or lies inside it: exit 2 with no JSON; so does --scope-root with --scope-id, --edges,
#     --matrix or --consumption
#   unchanged: without --scope-root the JSON carries neither key; a relative scope under a map, or under the identity
#     map (root = this home), is read as before
set -uo pipefail
# shellcheck source=tests/drsc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
ABS="$here/fixtures/dsrt/absscope.py"
setup_v
TP=$(cd "$T" && pwd -P)
XR="$TP/carbon/prds-clone"           # the recorded root: another host's PRD home, absent here (a normalized path)
RH=$(cd "$H" && pwd -P)
run() { JS=$(lint --json "$@" 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_traceback "$ERR"; }
jt() { printf '%s' "$JS" | python3 -c 'import sys,json; d=json.load(sys.stdin); sys.exit(0 if eval(sys.argv[1],{"d":d}) else 1)' "$1" \
  || fail "$2: $1 is false (rc=$RC): $JS $ERR"; }
fline() { python3 - "$ERR" "$@" <<'PY' || fail "no FAIL $1 line carrying [${*:2}]: $ERR"
import sys
err, fid, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
sys.exit(0 if any(l.startswith(f"FAIL {fid}: ") and all(s in l for s in subs) for l in err.split("\n")) else 1)
PY
}
# same_as_base: the JSON, without scope_roots and reviews[].scope_read, is the relative original's
same_as_base() { python3 - "$BASE_JS" "$JS" <<'PY' || fail "$1: the JSON differs from the relative original's: $JS"
import sys, json
a, b = json.loads(sys.argv[1]), json.loads(sys.argv[2])
b.pop("scope_roots", None)
for r in b.get("reviews") or []:
    r.pop("scope_read", None)
sys.exit(0 if a == b else 1)
PY
}
usage2() { # <case> <needle> <args...>: exit 2, no JSON on stdout, the needle on stderr
  local c=$1 n=$2; shift 2
  JS=$("$LINT" "$@" 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_traceback "$ERR"
  [ "$RC" = 2 ] && [ -z "$JS" ] || fail "$c: rc=$RC want 2 with no JSON: $JS $ERR"
  printf '%s' "$ERR" | grep -qF -- "$n" || fail "$c: '$n' not on stderr: $ERR"
}
# unchanged: no --scope-root
run; [ "$RC" = 0 ] || fail "baseline: rc=$RC $ERR"
jt 'd["provenance"]["snapshot"] == "verified" and "scope_roots" not in d and all("scope_read" not in r for r in d["reviews"])' baseline
BASE_JS=$JS
# a relative scope under a map: read as before, nothing read under the map; the identity map too (root = this home)
run --scope-root "$XR=$H"; [ "$RC" = 0 ] || fail "relative under a map: rc=$RC $ERR"
jt 'd["scope_roots"] == {"map": [{"recorded": "'"$XR"'", "local": "'"$RH"'"}], "reads": []}' relative-under-map
same_as_base relative-under-map
run --scope-root "$RH=$H"; [ "$RC" = 0 ] || fail "identity map: rc=$RC $ERR"
jt 'd["scope_roots"] == {"map": [{"recorded": "'"$RH"'", "local": "'"$RH"'"}], "reads": []}' identity-map
same_as_base identity-map
# the A1113 shape
[ "$(python3 "$ABS" "$DEC" "$XR" "$S_REV")" = 1 ] || fail "absscope rewrote other than one row"
# over-strict: the literal path refuses it
run; [ "$RC" = 1 ] || fail "literal path: rc=$RC $ERR"
jt 'd["findings"] == ["review-scope-mismatch"] and d["provenance"]["snapshot"] == "self"' literal-path
fline review-scope-mismatch "scope $XR/$SNAP" unreadable
# positive: the root as given, and with a trailing slash
for root in "$XR" "$XR/"; do
  run --scope-root "$root=$H"; [ "$RC" = 0 ] || fail "positive $root: rc=$RC $ERR"
  jt 'd["findings"] == [] and d["provenance"]["snapshot"] == "verified"' "positive $root"
  jt 'd["scope_roots"]["map"] == [{"recorded": "'"$XR"'", "local": "'"$RH"'"}]' "map $root"
  jt 'd["scope_roots"]["reads"] == [{"scope": "'"$XR/$SNAP"'", "read": "'"$RH/$SNAP"'", "root": "'"$XR"'", "session": "'"$S_REV"'"}]' "reads $root"
  jt 'd["reviews"][0]["scope_read"] == {"scope": "'"$XR/$SNAP"'", "read": "'"$RH/$SNAP"'", "root": "'"$XR"'"}' "scope_read $root"
  same_as_base "positive $root"
done
# negative 1: the local manifest differs (dupname adds other/notes.md)
cp "$RSFIX/dupname.sha256" "$H/$SNAP"
run --scope-root "$XR=$H"; [ "$RC" = 1 ] || fail "differing manifest: rc=$RC $ERR"
jt 'd["findings"] == ["review-scope-mismatch"] and d["provenance"]["snapshot"] == "self"' differing-manifest
fline review-scope-mismatch "the row's scope $XR/$SNAP" "read at $RH/$SNAP" "--scope-root $XR" "$ID_HAPPY"
cp "$T/home.orig/$SNAP" "$H/$SNAP"
# negative 2: a scope under no recorded root
run --scope-root "$TP/other/prds-clone=$H"; [ "$RC" = 1 ] || fail "another root: rc=$RC $ERR"
jt 'd["findings"] == ["review-scope-mismatch"] and d["scope_roots"]["reads"] == []' another-root
fline review-scope-mismatch "scope $XR/$SNAP" unreadable
run --scope-root "$TP/carbon/prds=$H"; [ "$RC" = 1 ] || fail "string-prefix root: rc=$RC $ERR"
jt 'd["findings"] == ["review-scope-mismatch"] and d["scope_roots"]["reads"] == []' string-prefix-root
decedit "dict(r,scope='$XR/../elsewhere/$SNAP') if r['session']=='$S_REV' and r['decision']=='launch' else r"
run --scope-root "$XR=$H"; [ "$RC" = 1 ] || fail "leaving by ..: rc=$RC $ERR"
jt 'd["findings"] == ["review-scope-mismatch"] and d["scope_roots"]["reads"] == []' leaving-by-dotdot
fline review-scope-mismatch "$XR/../elsewhere/$SNAP" unreadable
decedit "dict(r,scope='$XR/notes/../$SNAP') if r['session']=='$S_REV' and r['decision']=='launch' else r"
run --scope-root "$XR=$H"; [ "$RC" = 0 ] || fail "dotdot under the root: rc=$RC $ERR"
jt 'd["scope_roots"]["reads"] == [{"scope": "'"$XR/notes/../$SNAP"'", "read": "'"$RH/$SNAP"'", "root": "'"$XR"'", "session": "'"$S_REV"'"}]' dotdot-under-root
# negative 3: exit 2
usage2 other-home "not this run's PRD home" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$XR=$T"
usage2 slash-root "absolute directory below /" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "/=$H"
usage2 double-slash-root "absolute directory below /" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "//=$H"   # review r22 L2
mkdir -p "$TP/lex"; ln -s "$RH" "$TP/lex/home"   # review r22 L1: this run's home given through a link inside the root
usage2 root-holds-linked-home "hold one another" "$TP/lex/home/${LOG#"$H"/}" --last --prd-dir "$TP/lex/home" --decisions "$DEC" --scope-root "$TP/lex=$TP/lex/home"
usage2 relative-root "absolute directory below /" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "carbon/prds-clone=$H"
usage2 no-equals "one '='" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$XR"
usage2 two-equals "one '='" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$XR=$H=x"
usage2 empty-home "not this run's PRD home" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$XR="
usage2 nested "overlaps" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$XR=$H" --scope-root "$XR/notes=$H"
usage2 same-twice "overlaps" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$XR=$H" --scope-root "$XR/=$H"
usage2 root-holds-home "hold one another" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$TP=$H"
usage2 root-in-home "hold one another" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root "$RH/notes=$H"
usage2 no-value "needs a value" "$LOG" --last --prd-dir "$H" --decisions "$DEC" --scope-root
usage2 scope-id-mode "nothing else" --scope-id "$H/$SNAP" --scope-root "$XR=$H"
usage2 edges-mode "--edges takes" --edges "$H/$SNAP" --scope-root "$XR=$H"
usage2 matrix-mode "--matrix and --states" --matrix "$H/$SNAP" --states a=linted --scope-root "$XR=$H"
usage2 consumption-mode "--consumption" --consumption "$H/$SNAP" --task RS-ROWS --scope-root "$XR=$H"
pass "Q5 review scope: positive (two spellings, .. under the root), literal-path over-strict, differing manifest, no recorded root (three ways), exit 2 (17 ways), unchanged without the option"
