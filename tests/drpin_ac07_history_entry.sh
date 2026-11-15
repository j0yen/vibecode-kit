#!/usr/bin/env bash
# AC7 — history.md carries an entry dated 2026-11 that quotes both instructions,
# names forbidden_efforts, A1300, A1301, commit 11cd41be, and states that no
# approvals number is recorded for either instruction.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/drpin_lib.sh"
H="$REPO/skills/dream/history.md"
# the entry: a top-level bullet `- **<title> (2026-11-...).**` up to the next top-level bullet
e=$(awk '/^- \*\*/{f=0} /^- \*\*.*\(2026-11-[0-9][0-9][^)]*\)\.\*\*/{f=1} f' "$H")
[ -n "$e" ] || fail "no '- **<title> (2026-11-..).**' entry"
j=$(printf '%s\n' "$e" | tr '\n' ' ' | tr -s ' ')
for s in 'make /dream use Fable Max' 'expressly supersedes the old blanket Fable/max instruction' \
         'forbidden_efforts' 'A1300' 'A1301' '11cd41be' 'no approvals number is recorded for either instruction'; do
  case "$j" in *"$s"*) ;; *) fail "entry lacks: $s";; esac
done
pass
