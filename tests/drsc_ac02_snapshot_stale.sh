#!/usr/bin/env bash
# AC2 — one byte of an APPROVE slug's PRD file changed after the manifest was taken:
# exit 1, review-snapshot-stale naming the slug and the first 12 hex of both digests;
# the same edit after a FIX or REJECT last verdict fires no such finding. The current
# file is the first of build-queue/, built-prds/, parked/ holding PRD-<slug>.md (a
# queued PRD is digest-compared); an unreadable PRD file is stale, never a pass.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
setup_v
Q=build-queue; B=built-prds; P=parked
MAN_A=$(awk '$2=="PRD-rs-alpha.md"{print substr($1,1,12)}' "$H/$SNAP")
[ ${#MAN_A} = 12 ] || fail "manifest digest for PRD-rs-alpha.md not found"
stale_ok() { # <case> <slug> <changed file>
  local js rc out l cur
  js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
  expect_exact "$rc" 1 "$js" review-snapshot-stale
  [ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"self"' ] || fail "$1: snapshot label not self: $js"
  out=$(lint 2>&1)
  l=$(findline review-snapshot-stale "$out") || fail "$1: no FAIL line: $out"
  printf '%s' "$l" | grep -qw "$2" || fail "$1: slug $2 not named: $l"
  cur=$(sha256sum "$3" | cut -c1-12)
  printf '%s' "$l" | grep -q "$cur" && printf '%s' "$l" | grep -q "$MAN_A" || fail "$1: digests $cur/$MAN_A not named: $l"
}
printf 'x' >> "$H/$B/PRD-rs-alpha.md"
stale_ok approve rs-alpha "$H/$B/PRD-rs-alpha.md"
# FIX and REJECT last verdicts: the same edit is not checked
for v in FIX REJECT; do
  verdicts "rs-alpha $v fable
rs-beta APPROVE fable
" "rs-alpha $v fable
rs-beta APPROVE fable" "State: rs-alpha=linted rs-alpha=reviewed:$v rs-beta=linted rs-beta=reviewed:APPROVE"
  js=$(lint --json 2>"$T/err"); rc=$?
  [ "$rc" = 0 ] || fail "$v: rc=$rc $js $(cat "$T/err")"
  case "$js" in *review-snapshot-stale*) fail "$v: stale fired: $js";; esac
  [ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"verified"' ] || fail "$v: snapshot not verified: $js"
done
# APPROVE after a FIX in one file: the last verdict binds, so stale fires
verdicts "rs-alpha FIX fable
rs-alpha APPROVE fable
rs-beta APPROVE fable
" "rs-alpha FIX fable
rs-alpha APPROVE fable
rs-beta APPROVE fable" "State: rs-alpha=linted rs-alpha=reviewed:APPROVE rs-beta=linted rs-beta=reviewed:APPROVE"
stale_ok fix-then-approve rs-alpha "$H/$B/PRD-rs-alpha.md"
# a queued PRD: the stubs moved to build-queue/; unchanged = verified, one byte = stale
reset_v; mkdir -p "$H/$Q"; mv "$H/$B/PRD-rs-alpha.md" "$H/$B/PRD-rs-beta.md" "$H/$Q/"
js=$(lint --json 2>/dev/null); rc=$?
[ "$rc" = 0 ] && [ "$(printf '%s' "$js" | jget 'd["provenance"].get("snapshot")')" = '"verified"' ] || fail "queued unchanged: rc=$rc $js"
printf 'x' >> "$H/$Q/PRD-rs-alpha.md"
stale_ok queued rs-alpha "$H/$Q/PRD-rs-alpha.md"
# order: build-queue/ is read before built-prds/ (an unchanged copy in built-prds/ does not hide it)
cp "$T/home.orig/$B/PRD-rs-alpha.md" "$H/$B/PRD-rs-alpha.md"
stale_ok queued-before-built rs-alpha "$H/$Q/PRD-rs-alpha.md"
# parked/ only
reset_v; mkdir -p "$H/$P"; mv "$H/$B/PRD-rs-alpha.md" "$H/$P/"; printf 'x' >> "$H/$P/PRD-rs-alpha.md"
stale_ok parked rs-alpha "$H/$P/PRD-rs-alpha.md"
# raw bytes: a CRLF rewrite of the same text is a different digest
reset_v; sed -i 's/$/\r/' "$H/$B/PRD-rs-alpha.md"
stale_ok crlf rs-alpha "$H/$B/PRD-rs-alpha.md"
# unreadable PRD file: stale naming it unreadable
reset_v; not_root; chmod 000 "$H/$B/PRD-rs-alpha.md"
js=$(lint --json 2>"$T/err"); rc=$?; no_traceback "$(cat "$T/err")"
expect_exact "$rc" 1 "$js" review-snapshot-stale
out=$(lint 2>&1); l=$(findline review-snapshot-stale "$out") || fail "unreadable: $out"
printf '%s' "$l" | grep -q 'PRD-rs-alpha.md' && printf '%s' "$l" | grep -qi unreadable || fail "unreadable: path/unreadable not named: $l"
chmod 644 "$H/$B/PRD-rs-alpha.md"
pass
