#!/usr/bin/env bash
# AC7 (R1) — correct pending entries exit 0 from `--packet-only --pending`, governed and with no
# decisions log, with no repair-missing, repair-grammar or repair-author-mismatch (and no finding): a
# first repair round in one run (legacy header keeping x1, and header matrices x1 -> x2: a correct
# matrix rename), a first manifest with no note, an empty note and a title-only note, and continued
# missions (run 2 after run 1's recorded entry; run 2 with a bound m2 and a pending m3), each with a
# legacy header and with header matrices.
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
n=0
for c in ok-inrun ok-inrun-hm ok-inrun-empty ok-inrun-title ok-first ok-first-hm ok-first-empty ok-first-title \
         ok-continued ok-continued-hm ok-three ok-three-hm; do
  for v in "" "@nolog"; do
    pe "$c$v"; pk; rc0
    jtrue 'd["exit"] == 0 and d["findings"] == [] and not d["packet_errors"] and not d["held_packet_errors"] and not d["pending_errors"]' "$c$v clean"
    for id in repair-missing repair-grammar repair-author-mismatch; do no_id "$id"; done
    n=$((n+1))
  done
done
pass "$n correct pending entries exit 0, governed and with no log"
