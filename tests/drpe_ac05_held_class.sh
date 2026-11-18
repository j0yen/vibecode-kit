#!/usr/bin/env bash
# shellcheck disable=SC2329  # the c_* cells and their helpers run through "c_$c" in the loop at the end
# AC5 (R1 held rule, the whole held/fail class) — one case per row of the class table whose
# classification differs between 1d7f07b2, 98e467db and R1. R1 holds an error on a bound manifest "only
# when it is also present in the bound manifest's own frozen copies (... which record the state when its
# review launched)". On bound m2 (r2 launched on it, listed APPROVE), `--packet-only --pending`, governed:
# - a defect m2's frozen edges header raises too (the same prds/packet member or contract copy m2 lacks,
#   the same contract collision or contract/member clash), or one no header supplies (m2 lists no edges
#   file; the note's matrix with no readable frozen header, without --pending) is HELD under both labels
#   with exit 0 and no FAIL line for it; the matrix a pending adversarial= names is FAIL, and so is a live
#   member named like it when the frozen header is kept;
# - a live collision or clash on another basename, or on a basename the frozen header carries only as a
#   need, a live member with no readable frozen header, and F1's five live-only defects are FAIL with exit 1;
# - m2 edited or deleted after r2's launch holds nothing (its errors and the rows of its repairs copy FAIL);
#   a launch row with no scope_id records no edit (held), unless m2 no longer canonicalizes;
# - with the live repairs file missing a row the copy beside the latest bound manifest holds (repair-missing,
#   an undeclared change), FAIL; with a copy that lacks it or no listed repairs file, HELD; a listed copy
#   that differs from its digest grants no hold. The copy is read as at the latest bound manifest's latest
#   launch: no repairs= token ever means no row (HELD); a row naming a manifest whose withdrawal was recorded
#   before that launch is void (HELD), one only the pending entry withdraws is not, and the pair it forms
#   did not exist (FAIL); a deleted live file does not empty the copy (FAIL); a finding of that manifest's
#   own latest review did not exist at the launch (FAIL). The copy read is that of the repairs= in force at that
#   launch: the latest entry recorded before it (two recorded: the later; one recorded exactly at the launch is
#   not before it), else the repairs file the manifest lists, because a pending repairs= is never in force at a
#   launch: renamed after it, the old file's copy decides (rows it holds answer: FAIL; a defect it carries too:
#   HELD), also when the pending entry is the first to name repairs= (FAIL); renamed back to a file the manifests
#   list as a plain member, that member's undeclared change is HELD. A finding is dated by its issuing review's
#   first launch on the manifest it reviewed (a later relaunch of that session: HELD; another session's earlier
#   launch there: FAIL), and the manifest's launch for it by its latest binding row from another session (a resume
#   of the issuing review refreezes nothing: FAIL; a session reused across reviews is one session: FAIL; a row
#   from a session no Review: line names binds nothing: FAIL). The launch time counts every tier that binds (a
#   Review: line's reviewer row: HELD) and is the latest launch (a re-review: HELD, also for a withdrawal
#   recorded between the two launches), a withdrawal counts only when recorded before it (recorded later, or
#   pending even with an earlier header: FAIL); decisions rows count by their time, not their order in the file
#   (HELD), and a time with no UTC offset is no time (FAIL).
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
c_clash_need() { pe live-bound-clash-need; pk; rc1   # a frozen need and a live clash on one basename: two defects
  pfail "$SM" "manifest $M2: live edges header: contract path contracts/PRD-baz.md and the member PRD-baz.md"
  pheld "$SI" "manifest $M2: lists no PRD-baz.md (prds member of the frozen edges header)"
  pheld "$SI" "manifest $M2: lists no PRD-baz.md (prds member of the live edges header)"
  pheld "$SI" "manifest $M2: lists no PRD-baz.md (external hermes contract copy of the live edges header)"
  nofail "$SI" "PRD-baz.md"; noheld "share the basename PRD-baz.md"; fullrc1; }
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

FO="PRD-foo.md: changed but undeclared between"
c_notoken_pair() { pe notoken-pair; pk; held0       # no repairs= token ever: no row at either launch
  pheld repair-hash-mismatch "$FO $M1 and $M2"; nofail repair-hash-mismatch "$FO"; fullrc1; }
c_void_row() { pe void-row; pk; held0               # F1's only row names m2, withdrawn (recorded) before r3's launch
  pheld repair-missing "finding F1 of notes/reviews/r1/verdict.txt: no row in notes/missions/$PE_REP"
  pheld repair-hash-mismatch "$FO $M1 and $M2R"; nofail repair-missing "F1"; nofail repair-hash-mismatch "$FO"; fullrc1; }
c_void_row_s3() { pe void-row-s3; pk; rc1           # only the pending entry withdraws m2 (S3)
  pfail repair-missing "finding F1 of notes/reviews/r1/verdict.txt: no row in notes/missions/$PE_REP"
  pfail repair-hash-mismatch "$FO $M1 and $M2R"; noheld "F1"; noheld "$FO"; fullrc1; }
c_live_absent() { pe live-absent; pk; rc1           # the live repairs file deleted; m2's copy holds row 1
  pfail mission-repairs-missing "notes/missions/$PE_REP: absent, unreadable or empty"
  pfail repair-missing "finding F1 of notes/reviews/r1/verdict.txt: no row in notes/missions/$PE_REP"
  pfail repair-hash-mismatch "$FO $M1 and $M2"; noheld "F1"; noheld "$FO"; fullrc1; }
c_own_finding() { pe own-finding; pk; rc1           # F2 of r2, the latest review of bound last m2: not there at its launch
  pfail repair-missing "finding F2 of notes/reviews/r2/verdict.txt: no row in notes/missions/$PE_REP" "(the review about to launch on $M2 follows it)"
  noheld "F2"; full; rc0; }             # the full lint has no review about to launch: no finding
c_own_finding_notoken() { pe own-finding-notoken; pk; rc1
  pheld repair-missing "finding F1 of notes/reviews/r1/verdict.txt: no repairs= token on the Mission: line"
  pfail repair-missing "finding F2 of notes/reviews/r2/verdict.txt: no repairs= token on the Mission: line" "(the review about to launch on $M2 follows it)"
  nofail repair-missing "F1"; noheld "F2"; fullrc1; }

F1R="finding F1 of notes/reviews/r1/verdict.txt"
REP2=notes/missions/drpe-mission.repairs-v2.jsonl
c_rename_rec() { pe rv4-rename-rec; pk; rc1        # repairs= renamed by the pending entry; m3's copy of the old file answers all
  pfail repair-missing "$F1R: no row in $REP2"; pfail repair-hash-mismatch "$FO $M1 and $M2R"
  pfail repair-hash-mismatch "PRD-bar.md: changed but undeclared between $M2R and $M3"
  pfail repair-hash-mismatch "$PE_REP: changed but undeclared between $M2R and $M3"; noheld "F1"; noheld "changed but undeclared"; fullrc1; }
c_rename_void() { pe rename-void; pk; rc1           # the same, F1 unanswered and PRD-foo.md undeclared in the old file too
  pheld repair-missing "$F1R: no row in $REP2"; pheld repair-hash-mismatch "$FO $M1 and $M2R"
  pfail repair-hash-mismatch "PRD-bar.md: changed but undeclared between $M2R and $M3"
  pfail repair-hash-mismatch "$PE_REP: changed but undeclared between $M2R and $M3"; nofail repair-missing "F1"; nofail repair-hash-mismatch "$FO"; fullrc1; }
c_rename_row() { pe rename-row; pk; rc1            # renamed to a file of the same bytes: m2 froze no row of the new file (S2)
  pfail sweep-missing "finding F1 (row 1): sweep lacks"
  pfail "$SI" "manifest $M2: lists no drpe-mission.repairs-v2.jsonl (the repairs file;"; noheld "row 1"; noheld "$M2"; fullrc1; }
c_rename() { pe rv4-rename; pk; rc1                 # repairs= first named by the pending entry: m2's own listed copy answers both
  pfail repair-missing "$F1R: no row in $REP2"; pfail repair-hash-mismatch "$FO $M1 and $M2"
  noheld "F1"; noheld "$FO"; fullrc1; }
c_relaunch_issuer() { pe rv4-relaunch-issuer; pk; held0   # r1's session relaunched on m1 after r2's launch: F1 existed then
  pheld repair-missing "$F1R: no row in notes/missions/$PE_REP (its following review notes/reviews/r2/verdict.txt exists)"
  nofail repair-missing "F1"; fullrc1; }
c_tier3() { pe rv4-tier3; pk; held0                 # m2 bound only by r2's Review: line (role reviewer): launched at 14:00
  pheld repair-missing "$F1R" "(the review about to launch on $M2 follows it)"; nofail repair-missing "F1"; fullrc1; }
c_rereview_own() { pe rv4-rereview-own; pk; held0   # r2 FIX F2 on m2, r2b re-reviews m2 later: F2 existed at m2's latest launch
  pheld repair-missing "finding F2 of notes/reviews/r2/verdict.txt" "(its following review notes/reviews/r2b/verdict.txt exists)"
  nofail repair-missing "F2"; fullrc1; }
c_late_withdrawal() { pe rv4-void-row-s3; pkl; rc1  # the withdrawal of m2 recorded by the linted entry, after r3's launch
  pfail repair-missing "$F1R"; pfail repair-hash-mismatch "$FO $M1 and $M2R"; noheld "F1"; noheld "$FO"; }
F2R="finding F2 of notes/reviews/r2/verdict.txt"
c_resume_own() { pe rv5-resume-own; pk; rc1        # r2's session resumed on m2 after its FIX: F2 is still m2's own latest review's
  pfail repair-missing "$F2R" "(the review about to launch on $M2 follows it)"; noheld "F2"
  pkl; rc1; pfail repair-missing "$F2R"; noheld "F2"; pe rv5-resume-own; full; rc0; }
c_resume_three() { pe rv5-resume-three; pk; rc1    # the same resume, the next review on m3: F2 falls on the pending manifest
  pfail repair-missing "$F2R" "(the review about to launch on $M3 follows it)"; noheld "F2"; }
c_noresume_three() { pe rv5-noresume-three; pk; rc1
  pfail repair-missing "$F2R" "(the review about to launch on $M3 follows it)"; noheld "F2"; }
c_tier3_other() { pe rv5-tier3-other; pk; rc1      # a launch row with m2's id from a session no Review: line names binds nothing
  pfail repair-missing "$F2R"; noheld "F2"; }
c_rep_two() { pe rv5-rep-two; pk; rc1              # two recorded repairs= tokens before r3's launch: the later one's copy answers
  pfail repair-missing "$F1R"; pfail repair-hash-mismatch "$FO $M1 and $M2R"; noheld "F1"; noheld "$FO"; fullrc1; }
c_rep_at_bts() { pe rep-at-bts; pk; rc1            # an entry recorded exactly at r2's launch is not recorded before it
  pfail repair-missing "$F1R: no row in $REP2"; pfail repair-hash-mismatch "$FO $M1 and $M2"; noheld "F1"; noheld "$FO"
  pkl; rc1; pfail repair-missing "$F1R: no row in $REP2"; noheld "F1"; fullrc1; }
c_rename_back() { pe rename-back; pk; rc1          # renamed back to a file m1 and m2 list as a plain member: its change was undeclared
  pfail repair-missing "$F1R: no row in notes/missions/$PE_REP"; pfail repair-hash-mismatch "$FO $M1 and $M2"
  pheld repair-hash-mismatch "$PE_REP: changed but undeclared between $M1 and $M2"; nofail repair-hash-mismatch "$PE_REP"
  noheld "F1"; noheld "$FO"; fullrc1; }
c_prelaunch_rep2() { pe rv5-prelaunch-rep2; pk; rc1  # the new name before r2's launch: the check refuses it (m2 unbound, last)
  pfail "$SI" "manifest $M2: lists no drpe-mission.repairs-v2.jsonl (the repairs file;"; fullrc1; }
c_rename_copy() { pe rv5-rename-copy; pk; rc1      # renamed after r2's launch to a file keeping every row: the same refusal
  pfail "$SI" "manifest $M2: lists no drpe-mission.repairs-v2.jsonl (the repairs file;"; noheld "$M2"; fullrc1; }
c_rename_early() { pe rv5-rename-early; pk; rc1    # rename-rec with the pending header before r3's launch: still not in force
  pfail repair-missing "$F1R: no row in $REP2"; pfail repair-hash-mismatch "$FO $M1 and $M2R"; noheld "F1"; noheld "changed but undeclared"
  pkl; rc1; pfail repair-missing "$F1R: no row in $REP2"; noheld "F1"; noheld "changed but undeclared"; fullrc1; }
c_reuse_b() { pe rv5-reuse-b; pk; rc1              # r1's session is m2's only launcher: nothing dates F1 before m2's launch
  pfail repair-missing "$F1R"; noheld "F1"; fullrc1; }
c_dec_order() { pe rv5-dec-order; pk; held0        # r1's launch row stored after r2's: the times decide (F1 at 11:30, m2 at 14:00)
  pheld repair-missing "$F1R"; nofail repair-missing "F1"; fullrc1; }
c_naive_ts() { pe rv5-naive-ts; pk; rc1            # m2's launch row has a time with no offset: no launch time
  pfail repair-missing "$F1R"; noheld "F1"; fullrc1; }
c_rereview_withdrawal() { pe rereview-withdrawal; pk  # m2's withdrawal recorded between r3's and r3b's launches on m3
  pheld repair-missing "$F1R"; pheld repair-hash-mismatch "$FO $M1 and $M2R"; nofail repair-missing "F1"; nofail repair-hash-mismatch "$FO"
  pe rereview-withdrawal; pkl; held0; pheld repair-missing "$F1R"; pheld repair-hash-mismatch "$FO $M1 and $M2R"; }
c_late_issuer() { pe late-issuer; pk; rc1          # r1 issued F1 at 11:30, after r2's launch on m2 (11:00); r0 on m1 at 10:00
  pfail repair-missing "$F1R"; noheld "F1"; fullrc1; }
c_late_issuer_rereview() { pe late-issuer-rereview; pk  # late-issuer, then r2b re-reviews m2 at 12:00, after F1 existed
  pheld repair-missing "$F1R"; nofail repair-missing "F1"; fullrc1; }
c_pending_early() { pe rv4-pending-early; pk; rc1   # only the pending entry withdraws m2, its header before r3's launch (S3)
  pfail repair-missing "$F1R"; pfail repair-hash-mismatch "$FO $M1 and $M2R"; noheld "F1"; noheld "$FO"; fullrc1; }

red=0
for c in f1_packet f1_prds f1_contract f1_clash f1_dupbase frozen_prds frozen_packet frozen_contract frozen_dupbase \
         frozen_clash dupbase_other clash_other edges edges_member noheader_dupbase matrix_noheader matrix_member mx_member_frozen clash_need \
         late_edited late_edited_row late_deleted late_noid_held late_noid_deleted row_dropped row_dropped_badcopy row_dropped_empty row_dropped_unlisted row_dropped_pair \
         notoken_pair void_row void_row_s3 live_absent own_finding own_finding_notoken \
         rename_rec rename_void rename_row rename relaunch_issuer tier3 rereview_own late_withdrawal pending_early \
         resume_own resume_three noresume_three tier3_other rep_two rep_at_bts rename_back prelaunch_rep2 rename_copy \
         rename_early reuse_b dec_order naive_ts rereview_withdrawal late_issuer late_issuer_rereview; do
  if out=$("c_$c" 2>&1); then echo "ok  $c"; else echo "RED $c: $out"; red=1; fi
done
[ "$red" = 0 ] || fail "held/fail class: RED cells above"
pass "held/fail class: frozen-carried live-header defects and header-independent needs HELD (exit 0); live-only, other-basename and no-frozen-header defects FAIL; edited or deleted bound manifest and rows missing from the live repairs file FAIL; full lint exit 1"
