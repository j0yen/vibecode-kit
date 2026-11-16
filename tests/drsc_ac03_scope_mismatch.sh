#!/usr/bin/env bash
# AC3 — review-scope-mismatch, exit 1, naming the slug, basename or path (and line
# number), never a traceback: a verdict slug absent from the manifest; a manifest that
# no longer recomputes to the row's scope_id; an unreadable manifest; the line rule
# (CR, blank line, missing final LF, empty file); one PRD-*.md basename with two
# digests; an empty scope_id; a manifest listing a path with a non-UTF-8 byte.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
setup_v
mismatch() { # <case> <grep -F needle>...: exactly [review-scope-mismatch], every needle on its FAIL lines
  local c=$1 js rc out l n; shift
  js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
  expect_exact "$rc" 1 "$js" review-scope-mismatch
  [ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"self"' ] || fail "$c: snapshot label not self: $js"
  out=$(lint 2>&1); no_traceback "$out"
  l=$(findline review-scope-mismatch "$out") || fail "$c: no FAIL line: $out"
  for n in "$@"; do printf '%s' "$l" | grep -qF -- "$n" || fail "$c: '$n' not named: $l"; done
}
# the launcher's canonical text (fable-launch.sh canon(): awk basename, LC_ALL=C sort -u)
id_of() { LC_ALL=C awk '{n=split($2,p,"/"); print $1 "  " p[n]}' "$1" | LC_ALL=C sort -u | sha256sum | cut -d' ' -f1; }
# a verdict slug absent from the manifest: single.sha256 lists PRD-rs-alpha.md only
cp "$RSFIX/single.sha256" "$H/$SNAP"
sid=$(id_of "$H/$SNAP")
decedit "dict(r,scope_id='$sid') if r['session']=='$S_REV' and r['decision']=='launch' else r"
mismatch slug-absent rs-beta
# the manifest no longer recomputes to the row's scope_id (dupname adds other/notes.md)
reset_v; cp "$RSFIX/dupname.sha256" "$H/$SNAP"
mismatch id-moved "$SNAP" "$ID_HAPPY"
# unreadable: absent file, a directory, a mode-000 file
reset_v; rm "$H/$SNAP"
mismatch absent "$SNAP"
reset_v; rm "$H/$SNAP"; mkdir "$H/$SNAP"
mismatch directory "$SNAP"
reset_v; not_root; chmod 000 "$H/$SNAP"
mismatch mode-000 "$SNAP"
chmod 644 "$H/$SNAP"
# line rule: CR (line 1), blank line (line 2), no final LF (line 0), empty (line 0), a tab (line 3)
for v in crlf:1 blank:2 nonl:0; do
  reset_v; cp "$RSFIX/${v%%:*}.sha256" "$H/$SNAP"
  mismatch "${v%%:*}" "$SNAP" "line ${v##*:}" line-rule
done
reset_v; : > "$H/$SNAP"
mismatch empty "$SNAP" "line 0" line-rule
reset_v; sed -i '3s/  /\t/' "$H/$SNAP"
mismatch tab "$SNAP" "line 3" line-rule
# one PRD-*.md basename, two digests: dupprd (the row keeps happy's scope_id)
reset_v; cp "$RSFIX/dupprd.sha256" "$H/$SNAP"
mismatch dupprd "PRD-rs-alpha.md" prd-repeat
# a byte-identical repeated line is admitted (dupline = happy's id): verified
reset_v; cp "$RSFIX/dupline.sha256" "$H/$SNAP"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"verified"' ] || fail "dupline: rc=$rc $js"
# empty scope_id
reset_v; decedit "dict(r,scope_id='') if r['session']=='$S_REV' and r['decision']=='launch' else r"
mismatch empty-scope_id scope_id
# a path with a non-UTF-8 byte: canonicalized over bytes; the slug rs-beta is absent from it
reset_v; cp "$RSFIX/nonutf8.sha256" "$H/$SNAP"
sid=$(id_of "$H/$SNAP")
decedit "dict(r,scope_id='$sid') if r['session']=='$S_REV' and r['decision']=='launch' else r"
mismatch nonutf8-slug rs-beta
reset_v; cp "$RSFIX/nonutf8.sha256" "$H/$SNAP"
mismatch nonutf8-id "$SNAP" "$ID_HAPPY"
# a non-UTF-8 byte inside a line the line rule refuses (a space in the path)
reset_v; printf '%s  bad \377name.md\n' "$(printf '%064d' 0)" >> "$H/$SNAP"
mismatch nonutf8-line-rule "$SNAP" "line 4" line-rule
pass
