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
# entry, linted itself, after the token; the installed rule (43d5b39) refuses the positive.
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
for c in r6-scoped r6-not-last r6-reordered r6-after-w r6-malformed-row r6-not-listed; do
  cx "$c"; run_mr; has_id mission-edges-missing; has_fail mission-grammar "never shortens or reorders"
  v=$(printf '%s' "$JS" | jget 'd["mission"]["withdrawn"][-1]["applies"]'); [ "$v" = false ] || fail "$c: the token applies"
done
today r6-positive; has_fail mission-grammar "withdrawn=$WM" "unknown token"; has_id mission-edges-missing
pass "a planned freeze never written is withdrawn by the dropping entry, by an entry appended after it, and stays withdrawn for later entries; an existing, scoped (also under a --scope-root or on an unparsed decisions line), not-last, reordered, repairs-named, still-listed or unlisted manifest, no decisions source and no own scope= refused; the original and the earlier dropping entry stay refused; the installed rule refuses the positive"
