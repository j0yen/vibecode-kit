#!/usr/bin/env bash
# shellcheck disable=SC2329  # the c_* cells and their helpers run through "c_$c" in the loop at the end
# AC5 (R1 held rule, the whole held/fail class) — one case per row of the class table whose
# classification differs between 1d7f07b2, 98e467db and R1. R1 holds an error on a bound manifest "only
# when it is also present in the bound manifest's own frozen copies (... which record the state when its
# review launched)". On bound m2 (r2 launched on it, listed APPROVE), `--packet-only --pending`, governed:
# - a defect m2's frozen edges header raises too (the same prds/packet member or contract copy m2 lacks,
#   the same contract collision or contract/member clash), or one no header supplies (m2 lists no edges
#   file; the note's matrix with no readable frozen header, without --pending) is HELD under both labels
#   with exit 0 and no FAIL line for it; the matrix a pending adversarial= names is FAIL;
# - a live collision or clash on another basename, a live member with no readable frozen header, and F1's
#   five live-only defects are FAIL with exit 1;
# - m2 edited or deleted after r2's launch holds nothing (its errors and the rows of its repairs copy FAIL);
#   a launch row with no scope_id records no edit (held), unless m2 no longer canonicalizes;
# - with the live repairs file missing a row the copy beside the latest bound manifest holds (repair-missing,
#   an undeclared change), FAIL; with a copy that lacks it or no listed repairs file, HELD; a listed copy
#   that differs from its digest grants no hold.
# The full lint on each note with the pending entry appended still exits 1. Each case runs on its own and
# prints ok or RED, so a known-bad lint (DRREC_LINT) shows every cell.
set -uo pipefail
# shellcheck source=tests/drpe_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drpe_lib.sh"
setup_pe
# noline <prefix> <substring...>: no stderr line starting with <prefix> carries every substring
noline() { local pre=$1; shift
  python3 - "$ERR" "$pre" "$@" <<'PY' && fail "${CASE}: a '$pre' line carries [$*] (rc=$RC): $ERR"
import sys
err, pre, subs = sys.argv[1], sys.argv[2], sys.argv[3:]
sys.exit(0 if any(l.startswith(pre) and all(s in l for s in subs) for l in err.split("\n")) else 1)
PY
  return 0; }
nofail() { local id=$1; shift; noline "FAIL $id: " "$@"; }
noheld() { noline "HELD " "$@"; }
# pkl: --last --packet-only on the note with the pending entry appended (no --pending: no pending token)
pkl() { local d; mapfile -t d < <(decargs); appended
  JS=$("$LINT" "$LOG" --last --packet-only --prd-dir "$H" "${d[@]}" --json 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb; }
held0() { rc0; jtrue 'd["exit"] == 0 and not d["packet_errors"] and d["held_packet_errors"]' "${CASE}: held, exit 0"; }
fullrc1() { full; rc1; }
SI=mission-scope-incomplete SM=mission-scope-mismatch

f1() { local kind=$1 base=$2 what=$3
  pe "live-bound-$kind"; pk; rc1; pfail "$SI" "manifest $M2:" "lists no $base" "($what of the live edges header)"
  noheld "lists no $base"; fullrc1; }
c_f1_packet() { f1 packet drpe-glossary.md "packet member"; }
c_f1_prds() { f1 prds PRD-baz.md "prds member"; }
c_f1_contract() { f1 contract hermes-contract.md "external hermes contract copy"; }
c_f1_clash() { pe live-bound-clash; pk; rc1
  pfail "$SM" "manifest $M2: live edges header: contract path contracts/PRD-foo.md and the member PRD-foo.md"; noheld "live edges header"; fullrc1; }
c_f1_dupbase() { pe live-bound-dupbase; pk; rc1
  pfail "$SM" "manifest $M2: live edges header: contract paths contracts/a/hermes.md and contracts/b/hermes.md"
  pfail "$SI" "lists no hermes.md" "(external hermes contract copy of the live edges header)"; noheld "live edges header"; fullrc1; }

both() { local kind=$1 base=$2 what=$3
  pe "$kind"; pk; held0
  pheld "$SI" "manifest $M2:" "lists no $base" "($what of the frozen edges header)"
  pheld "$SI" "manifest $M2:" "lists no $base" "($what of the live edges header)"
  nofail "$SI" "lists no $base"; fullrc1; }
c_frozen_prds() { both live-bound-frozen-prds PRD-bar.md "prds member"; }
c_frozen_packet() { both live-bound-frozen-packet drpe-glossary.md "packet member"; }
c_frozen_contract() { both live-bound-frozen-contract hermes-contract.md "external hermes contract copy"; }
c_frozen_dupbase() { pe live-bound-frozen-dupbase; pk; held0
  for l in frozen live; do pheld "$SM" "manifest $M2: $l edges header: contract paths contracts/a/hermes.md and contracts/b/hermes.md"; done
  nofail "$SM" "share the basename hermes.md"; fullrc1; }
c_frozen_clash() { pe live-bound-frozen-clash; pk; held0
  for l in frozen live; do pheld "$SM" "manifest $M2: $l edges header: contract path contracts/PRD-foo.md and the member PRD-foo.md"; done
  nofail "$SM" "share the basename PRD-foo.md"; fullrc1; }
c_dupbase_other() { pe live-bound-dupbase-other; pk; rc1
  pheld "$SM" "manifest $M2: frozen edges header: contract paths contracts/a/x.md and contracts/b/x.md"
  pfail "$SM" "manifest $M2: live edges header: contract paths contracts/a/hermes.md and contracts/b/hermes.md"
  noheld "live edges header"; fullrc1; }
c_clash_other() { pe live-bound-clash-other; pk; rc1
  pheld "$SM" "manifest $M2: frozen edges header: contract path contracts/PRD-foo.md and the member PRD-foo.md"
  pfail "$SM" "manifest $M2: live edges header: contract path contracts/PRD-bar.md and the member PRD-bar.md"
  noheld "live edges header"; fullrc1; }
c_edges() { pe live-bound-edges; pk; held0
  pheld "$SM" "manifest $M2:" "lists no edges basename $PE_EB"
  pheld "$SI" "manifest $M2: lists no $PE_EB (edges file of the live edges header)"; nofail "$SI" "lists no $PE_EB"; fullrc1; }
c_edges_member() { pe live-bound-edges-member; pk; held0
  pheld "$SI" "manifest $M2: lists no $PE_EB (packet member of the live edges header)"
  pheld "$SI" "manifest $M2: lists no $PE_EB (edges file of the live edges header)"; nofail "$SI" "lists no $PE_EB"; fullrc1; }
c_noheader_dupbase() { pe live-bound-noheader-dupbase; pk; rc1
  pfail "$SM" "manifest $M2: live edges header: contract paths contracts/a/hermes.md and contracts/b/hermes.md"
  pfail "$SI" "manifest $M2: lists no hermes.md (external hermes contract copy of the live edges header)"
  pheld "$SI" "manifest $M2: lists no $PE_EB (edges file of the live edges header)"; nofail "$SI" "lists no $PE_EB"; fullrc1; }
c_matrix_noheader() { pe live-bound-matrix-noheader; pkl; held0
  pheld "$SI" "manifest $M2: lists no" "-adversarial.md (matrix named by adversarial= (the header names none))"
  pheld "$SI" "manifest $M2: lists no $PE_EB (edges file of the live edges header)"; nofail "$SI" "manifest $M2:"
  pe live-bound-matrix-noheader; pk; rc1     # with --pending the pending entry's own adversarial= names x2
  pfail "$SI" "manifest $M2: lists no" "-adversarial.md (matrix named by adversarial= (the header names none))"
  pheld "$SI" "manifest $M2: lists no $PE_EB (edges file of the live edges header)"; fullrc1; }
c_matrix_member() { local mx="-adversarial.md (packet member of the live edges header)"
  pe live-bound-matrix-member; pk; rc1      # the pending adversarial= names x2: neither need is carried
  pfail "$SI" "manifest $M2: lists no" "-adversarial.md (matrix named by adversarial= (the header names none))"
  pfail "$SI" "manifest $M2: lists no" "$mx"; noheld "$mx"
  pe live-bound-matrix-member; pkl; held0   # without --pending both are m2's own listing
  pheld "$SI" "manifest $M2: lists no" "$mx"; nofail "$SI" "manifest $M2:"; fullrc1; }
c_mx_member_frozen() { local mx="-adversarial.md (packet member of the live edges header)"
  pe live-bound-mx-member-frozen; pk; rc1  # frozen header kept; the pending adversarial= names x2 (S3)
  pfail "$SI" "manifest $M2: lists no" "-adversarial.md (matrix named by adversarial= (the header names none))"
  pfail "$SI" "manifest $M2: lists no" "$mx"; noheld "$mx"; fullrc1; }
c_late_noid_held() { both late-noid-held PRD-bar.md "prds member"; }
c_late_noid_deleted() { pe late-noid-deleted; pk; rc1; pfail "$SM" "manifest $M2:" "unreadable"; noheld "manifest $M2:"; fullrc1; }
c_late_edited() { pe late-edited; pk; rc1
  pfail "$SI" "manifest $M2: lists no PRD-bar.md (prds member of the frozen edges header)"
  pfail "$SI" "manifest $M2: lists no PRD-bar.md (prds member of the live edges header)"; noheld "PRD-bar.md"; fullrc1; }
c_late_edited_row() { pe late-edited-row; pk; rc1; pfail sweep-missing "finding F1 (row 1): sweep lacks"; noheld "row 1"; fullrc1; }
c_late_deleted() { pe late-deleted; pk; rc1; pfail "$SM" "manifest $M2:" "unreadable"; noheld "manifest $M2:"; fullrc1; }
dropped() { pe "$1"; pk; rc1
  pfail repair-missing "finding F1 of notes/reviews/r1/verdict.txt: no row in notes/missions/$PE_REP"
  pfail repair-hash-mismatch "PRD-foo.md: changed but undeclared between $M1 and $M2"; noheld "F1"; noheld "PRD-foo.md"; fullrc1; }
c_row_dropped() { dropped row-dropped; }
c_row_dropped_badcopy() { dropped row-dropped-badcopy; }
kept_row() { pe "$1"; pk; held0
  pheld repair-missing "finding F1 of notes/reviews/r1/verdict.txt: no row in notes/missions/$PE_REP"
  pheld repair-hash-mismatch "PRD-foo.md: changed but undeclared between $M1 and $M2"
  nofail repair-missing "F1"; nofail repair-hash-mismatch "PRD-foo.md"; fullrc1; }
c_row_dropped_empty() { kept_row row-dropped-empty; }
c_row_dropped_unlisted() { kept_row row-dropped-unlisted; }
c_row_dropped_pair() { pe row-dropped-pair; pk; rc1
  pfail repair-missing "finding F2 of notes/reviews/r2/verdict.txt: no row in notes/missions/$PE_REP" "(the review about to launch on $M3 follows it)"
  pfail repair-hash-mismatch "PRD-bar.md: changed but undeclared between $M2 and $M3"
  pfail repair-hash-mismatch "$PE_REP: changed but undeclared between $M2 and $M3"; noheld "$M3"; fullrc1; }

red=0
for c in f1_packet f1_prds f1_contract f1_clash f1_dupbase frozen_prds frozen_packet frozen_contract frozen_dupbase \
         frozen_clash dupbase_other clash_other edges edges_member noheader_dupbase matrix_noheader matrix_member mx_member_frozen \
         late_edited late_edited_row late_deleted late_noid_held late_noid_deleted row_dropped row_dropped_badcopy row_dropped_empty row_dropped_unlisted row_dropped_pair; do
  if out=$("c_$c" 2>&1); then echo "ok  $c"; else echo "RED $c: $out"; red=1; fi
done
[ "$red" = 0 ] || fail "held/fail class: RED cells above"
pass "held/fail class: frozen-carried live-header defects and header-independent needs HELD (exit 0); live-only, other-basename and no-frozen-header defects FAIL; edited or deleted bound manifest and rows missing from the live repairs file FAIL; full lint exit 1"
