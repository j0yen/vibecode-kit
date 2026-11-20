#!/usr/bin/env bash
# Repair 6 (the PRD author's addendum 4; followon7/dream/requests/source-03415-lint-contract-repairs-addendum-4.md) — a
# Mission: line may carry withdrawn=<manifest>[,<manifest>...]. A withdrawn manifest leaves the continuity check of every
# earlier entry that lists it and this entry's list comparison when (a) its file does not exist, (b) no launch row of the
# decisions source scopes it, (c) it is the last element of the scope= list of the latest earlier entry that lists it,
# (d) this entry's own scope= is the previous entry's list without it, followed only by appended manifests, and (e) no
# repairs row names it as before or after. The original (A1723's 4:16:48 AM entry listing the planned 124000Z freeze,
# never written, and the 4:40:26 AM entry dropping it) is mission-edges-missing and mission-grammar.
# Positive: the 14:00 entry drops W with withdrawn=W: clean; so are the same token on an entry appended after an entry
# that dropped W without it (the A1723 log as written), and an entry after the one that withdrew W (the token is never
# inherited). Negatives (the author's table): W exists; a review launch row scopes W; W is not the last element; the
# rest of the list reordered (each mission-grammar); a repairs row names W as after (repair-scope-mismatch). Further
# negatives: W named as before; a later freeze appended after W; a row scoping W under a --scope-root or through a
# directory link; a decisions line that is no JSON object naming W; no decisions source; no scope= of its own; W still
# listed; a manifest no earlier entry lists; W listed again after its withdrawal and dropped with no token. Over-strict control: the original stays refused (the log is append-only), and so does the earlier dropping
# entry, linted itself, after the token; the installed rule (43d5b39) refuses the positive. Review r23d:
# (e) reads the repairs file of every entry of the Task (M1: one named only by the earlier listing entry; V1: one named
# only by an entry after the withdrawing one); a dangling link at W (V2) and an unreadable folder (L1) refuse; a
# repeated item (V3); a later void token keeps an earlier applying withdrawal (V5); an unparsed line naming W in a form
# other than the token's (V8); a row of any role (V9), a list-valued scope or any field naming W (L2) scopes it; a
# row holding a NUL and a file where W's folder would be leave the token applying. Review r23e: (a) looks W up as written
# and as normalized (M1: `W/`, `W/.` and `W/../mw.sha256` with W written are refused as existing); (e) refuses an earlier
# entry's repairs file that is missing or unreadable, or whose line naming W is no JSON object (M2), and applies with
# the same file clean; a NUL in the token is mission-grammar (L1), never a traceback. Review r23g: (e) also refuses an
# earlier row whose after is no path string ([W], {"path": W}, W followed by a NUL), any line that is no JSON object
# whatever it spells (W with ./ or with its dot escaped, then a comma), and a file that is not UTF-8 (M1, L2). Review r23h:
# (e) also refuses an earlier row with no after (its key spelled After) or neither key (M1), an after that is blank (M1),
# empty (L3, R4) or a lone surrogate (L2), a before that is a list (L3, H4), a JSON line that is a list (L3, H3) and a row
# repeating its after key (L1); a decisions value that is a lone surrogate names nothing, and neither ends in a traceback (L2).
set -uo pipefail
# shellcheck source=tests/dlcr_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/dlcr_lib.sh"
setup_mx
WM=notes/snapshots/mw/mw.sha256
withdrawn_is() { local got; got=$(printf '%s' "$JS" | jget '[[w["entry"], w["manifests"], w["applies"]] for w in d["mission"].get("withdrawn", [])]') \
  || fail "${CASE}: no JSON (rc=$RC): $ERR"; [ "$got" = "$1" ] || fail "${CASE}: mission.withdrawn=$got want $1"; }
T14=2026-11-18T14:00:00-08:00; T1045=2026-11-18T10:45:00-08:00
cx r6-positive; run_mr; clean; withdrawn_is "[[\"$T14\", [\"$WM\"], true]]"
cx r6-appended-later; run_mr; clean; withdrawn_is "[[\"$T14\", [\"$WM\"], true]]"
cx r6-later-entry; run_mr; clean; withdrawn_is "[[\"$T1045\", [\"$WM\"], true]]"
cx r6-original; run_mr; findings_eq '["mission-edges-missing", "mission-grammar"]'
has_fail mission-edges-missing "mw/mw.sha256" "continuity of entry 2026-11-18T10:30:00-08:00"; has_fail mission-grammar "never shortens or reorders"
v=$(printf '%s' "$JS" | jget '"withdrawn" not in d["mission"]'); [ "$v" = true ] || fail "r6-original: mission.withdrawn present without a token"
cx r6-appended-later-original; run_mr; findings_eq '["mission-edges-missing"]'
# the 10:45 entry (the 4:40:26 AM entry as written), linted itself, keeps both findings: the token is never written back
cx r6-appended-later; JS=$(lint --json --entry "$T1045" 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb
has_fail mission-edges-missing "mw/mw.sha256" "continuity of entry 2026-11-18T10:30:00-08:00"; has_fail mission-grammar "never shortens or reorders"
cx r6-exists; run_mr; findings_eq '["mission-grammar"]'; has_fail mission-grammar "withdrawn=$WM" "exists; only a manifest that was never written"
cx r6-scoped; run_mr; has_fail mission-grammar "withdrawn=$WM" "dddddddd-0000-4000-8000-0000000000dd" "scopes it"; has_id mission-edges-missing
cx r6-not-last; run_mr; has_fail mission-grammar "withdrawn=$WM" "is not the last element of the scope= list of entry 2026-11-18T10:30:00-08:00"
cx r6-reordered; run_mr; has_fail mission-grammar "withdrawn=$WM" "without the withdrawn manifests, followed only by appended manifests"
cx r6-repairs-after; run_mr; has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/drmx-mission.repairs.jsonl names it as after"
cx r6-repairs-before; run_mr; has_fail repair-scope-mismatch "withdrawn=$WM" "names it as before"
cx r6-after-w; run_mr; has_fail mission-grammar "withdrawn=$WM" "is not the last element of the scope= list of entry $T1045"
cx r6-scoped-root; run_mr; clean
JS=$(lint --json --scope-root "/a1723-recorded-home=$H" 2>"$T/err"); RC=$?; ERR=$(cat "$T/err"); no_tb
has_fail mission-grammar "withdrawn=$WM" "scopes it"; has_id mission-edges-missing
cx r6-scoped-link; run_mr; has_fail mission-grammar "withdrawn=$WM" "scopes it"; has_id mission-edges-missing
# withdrawn at 10:45, planned again at 10:50 and dropped untokened at 14:00: the 10:45 token covers only entries before it
cx r6-relisted; run_mr; has_fail mission-edges-missing "mw/mw.sha256" "continuity of entry 2026-11-18T10:50:00-08:00"
has_fail mission-grammar "never shortens or reorders"; withdrawn_is "[[\"$T1045\", [\"$WM\"], true]]"
cx r6-malformed-row; run_mr; has_fail mission-grammar "withdrawn=$WM" "which is no JSON object, names it"
cx r6-ungoverned; run_mr_ungov; has_fail mission-grammar "withdrawn=$WM" "no decisions source was read"; has_id mission-edges-missing
cx r6-no-scope; run_mr; has_fail mission-grammar "withdrawn=$WM" "carries no scope= of its own"
cx r6-still-listed; run_mr; has_fail mission-grammar "withdrawn=$WM" "this entry's scope= still lists it"
cx r6-not-listed; run_mr; has_fail mission-grammar "withdrawn=notes/snapshots/mz/mz.sha256" "no earlier entry of this Task lists it"
cx r6-repairs-earlier; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'
has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl names it as after"
cx r6-repairs-earlier-control; run_mr; findings_eq '["mission-edges-missing", "mission-grammar"]'
cx r6-repairs-later; run_mr; withdrawn_is "[[\"$T1045\", [\"$WM\"], false]]"
has_fail mission-edges-missing "continuity of entry 2026-11-18T10:30:00-08:00" "withdrawn= of entry $T1045 does not apply" \
  "row 3 of notes/missions/new.repairs.jsonl names it as after"
cx r6-dangling; run_mr; has_fail mission-grammar "withdrawn=$WM" "exists; only a manifest that was never written"
if [ "$(id -u)" != 0 ]; then             # W written, its folder unreadable: it may exist (review r23d L1)
  cx r6-exists; chmod 000 "$H/notes/snapshots/mw"; JS=$(lint --json 2>"$T/err"); RC=$?; chmod 755 "$H/notes/snapshots/mw"
  ERR=$(cat "$T/err"); no_tb; has_fail mission-grammar "withdrawn=$WM" "cannot be checked (Permission denied), so it may exist"
else
  echo "note: run as root, so the unreadable-folder case (review r23d L1) is not run"
fi
cx r6-repeated; run_mr; has_fail mission-grammar "withdrawn=$WM,$WM" "a withdrawn= item repeats"
cx r6-later-void; run_mr; findings_eq '["mission-grammar"]'; has_fail mission-grammar "mz.sha256: no earlier entry of this Task lists it"
withdrawn_is "[[\"$T1045\", [\"$WM\"], true], [\"$T14\", [\"$WM\", \"notes/snapshots/mz/mz.sha256\"], false]]"
cx r6-dot-token; run_mr; clean; withdrawn_is "[[\"$T14\", [\"./$WM\"], true]]"
cx r6-dot-token-line; run_mr; has_fail mission-grammar "withdrawn=./$WM" "which is no JSON object, names it"
cx r6-scoped-author; run_mr; has_fail mission-grammar "withdrawn=$WM" "role author) scopes it"
cx r6-scoped-list; run_mr; has_fail mission-grammar "withdrawn=$WM" "role review) scopes it"
cx r6-named-row; run_mr; has_fail mission-grammar "withdrawn=$WM" "names it in reasons"
cx r6-named-nested; run_mr; has_fail mission-grammar "withdrawn=$WM" "names it in freeze"
cx r6-nul-row; run_mr; clean; withdrawn_is "[[\"$T14\", [\"$WM\"], true]]"
for c in slash dot dotdot; do                # review r23e M1
  cx "r6-exists-$c"; run_mr; findings_eq '["mission-grammar"]'; has_fail mission-grammar "withdrawn=$WM" "mw/mw.sha256 exists; only a manifest that was never written"
done
cx r6-repairs-earlier-clean; run_mr; clean; withdrawn_is "[[\"$T14\", [\"$WM\"], true]]"     # review r23e M2: the twin of the three below
cx r6-repairs-earlier-comma; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'
has_fail repair-scope-mismatch "withdrawn=$WM" "line 3 of notes/missions/old.repairs.jsonl is no JSON object, so a row naming it cannot be ruled out"
for c in list dict nul; do                 # review r23g M1 and L2: row 3's after is no path string ([W], {"path": W}, W + NUL)
  cx "r6-repairs-earlier-$c"; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'
  has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl: after is no path string"
done
for c in dotted-comma escaped-comma; do    # review r23g M1: W spelled otherwise on a line that is no JSON object
  cx "r6-repairs-earlier-$c"; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'
  has_fail repair-scope-mismatch "withdrawn=$WM" "line 3 of notes/missions/old.repairs.jsonl is no JSON object"
done
cx r6-repairs-earlier-misspelled; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'   # r23h M1
has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl has no after, so a row naming it cannot be ruled out"
cx r6-repairs-earlier-no-keys; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'      # r23h M1
has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl has no before"
has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl has no after"
for c in blank empty surrogate; do         # review r23h M1, L3 (R4) and L2: row 3's after is " ", "" or a lone surrogate
  cx "r6-repairs-earlier-$c"; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'
  has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl: after is no path string"
done
cx r6-repairs-earlier-before-list; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'  # r23h L3 (H4)
has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl: before is no path string"
cx r6-repairs-earlier-array; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'        # r23h L3 (H3)
has_fail repair-scope-mismatch "withdrawn=$WM" "line 3 of notes/missions/old.repairs.jsonl is no JSON object"
cx r6-repairs-earlier-repeated; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'     # r23h L1
has_fail repair-scope-mismatch "withdrawn=$WM" "row 3 of notes/missions/old.repairs.jsonl repeats its after key"
cx r6-surrogate-row; run_mr; clean; withdrawn_is "[[\"$T14\", [\"$WM\"], true]]"   # r23h L2: names nothing, no traceback
cx r6-repairs-earlier-latin1; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'   # r23g L2
has_fail repair-scope-mismatch "withdrawn=$WM" "notes/missions/old.repairs.jsonl cannot be read (not UTF-8)"
cx r6-repairs-earlier-missing; run_mr; findings_eq '["mission-edges-missing", "repair-scope-mismatch", "mission-grammar"]'
has_fail repair-scope-mismatch "withdrawn=$WM" "notes/missions/old.repairs.jsonl cannot be read (No such file or directory)"
if [ "$(id -u)" != 0 ]; then             # the clean file made unreadable: a row naming W cannot be ruled out (review r23e M2)
  cx r6-repairs-earlier-clean; chmod 000 "$H/notes/missions/old.repairs.jsonl"; JS=$(lint --json 2>"$T/err"); RC=$?
  chmod 644 "$H/notes/missions/old.repairs.jsonl"; ERR=$(cat "$T/err"); no_tb
  has_fail repair-scope-mismatch "withdrawn=$WM" "notes/missions/old.repairs.jsonl cannot be read (Permission denied)"
else
  echo "note: run as root, so the unreadable repairs-file case (review r23e M2) is not run"
fi
cx r6-nul-token; run_mr; has_id mission-grammar                         # review r23e L1: a finding, never a traceback
has_fail mission-grammar "withdrawn=$WM" "a NUL character in its value"
cx r6-parent-file; run_mr; clean; withdrawn_is "[[\"$T14\", [\"$WM\"], true]]"
for c in r6-scoped r6-not-last r6-reordered r6-after-w r6-malformed-row r6-not-listed r6-repairs-earlier r6-dangling \
         r6-scoped-author r6-scoped-list r6-named-row r6-named-nested r6-dot-token-line; do
  cx "$c"; run_mr; has_id mission-edges-missing; has_fail mission-grammar "never shortens or reorders"
  v=$(printf '%s' "$JS" | jget 'd["mission"]["withdrawn"][-1]["applies"]'); [ "$v" = false ] || fail "$c: the token applies"
done
today r6-positive; has_fail mission-grammar "withdrawn=$WM" "unknown token"; has_id mission-edges-missing
pass "(review r23e: W/, W/. and W/../mw.sha256 refused as existing; a missing, unreadable or unparsed earlier repairs file refused, its clean twin applies; a NUL token is grammar) a planned freeze never written is withdrawn by the dropping entry, by an entry appended after it, and stays withdrawn for later entries (a later void token keeps it); an existing (also a dangling link or behind an unreadable folder), scoped (any role, a list scope, any field, under a --scope-root, through a link or on an unparsed decisions line), not-last, reordered, repairs-named (by any entry's repairs file), repeated, still-listed or unlisted manifest, no decisions source and no own scope= refused; the original and the earlier dropping entry stay refused; the installed rule refuses the positive"
