#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drsc_* tests (PRD-dream-run-record-review-scope). Reuses the
# drrec helpers (lint, setline, decedit, jget, expect_exact, fail, pass) unchanged and adds
# setup_v: copy tests/fixtures/drrec/verified into a temporary directory (private HOME,
# no default decisions log) so each case mutates one element of the passing verified note.
# shellcheck source=tests/drrec_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drrec_lib.sh"
VFIX="$FIX/verified"
RSFIX="$FIX/review-scope"
S_AUTH=08e700e0-4ffa-4ef6-b028-3d9454fa7b54     # rows.jsonl row 1: author launch
S_REV=0b6b700d-6ba2-4493-9d72-bc1e2da83594      # rows.jsonl row 2: review launch (happy)
ID_HAPPY=280387bf25e5fd1f0d64b1acae84019a1e109bd9871ea891c3b92b550eb0d5fc
VERDICTS="notes/reviews/rs-rows-review.txt"
RESULT="notes/reviews/rs-rows-review.json"
SNAP="notes/snapshots/happy.sha256"
setup_v() {
  T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
  cp -r "$VFIX/." "$T/"
  mkdir -p "$T/fakehome"
  export HOME="$T/fakehome" ANALYSIS_WIKI_DIR="$T/wiki"
  unset SKILL_ROUTING_DECISIONS
  LOG="$T/home/notes/dream-log.md"; DEC="$T/decisions.jsonl"; H="$T/home"
  cp "$DEC" "$T/dec.orig"; cp "$LOG" "$T/log.orig"
  cp -r "$H" "$T/home.orig"
}
# reset_v: restore the decisions log, the note and the PRD home to the copied fixture
reset_v() { cp "$T/dec.orig" "$DEC"; cp "$T/log.orig" "$LOG"; rm -rf "$H"; cp -r "$T/home.orig" "$H"; }
# verdicts <file text> <result text> <State line>: rewrite the reviewer's verdict file,
# its result= capture (same session) and the note's State: line together
verdicts() {
  printf '%s' "$1" > "$H/$VERDICTS"
  python3 -c 'import json,sys; print(json.dumps({"type":"result","is_error":False,"session_id":sys.argv[1],"result":sys.argv[2]}))' \
    "$S_REV" "$2" > "$H/$RESULT"
  setline State "$3"
}
# no_traceback <stderr text>
no_traceback() { case "$1" in *Traceback*) fail "traceback: $1";; esac; }
# findline <id> <text>: the FAIL <id> lines of a text run's output
findline() { printf '%s\n' "$2" | grep "^FAIL $1: "; }
not_root() { [ "$(id -u)" != 0 ] || fail "euid 0: root reads a mode-000 file, so this case would be vacuous"; }
