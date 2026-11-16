#!/usr/bin/env bash
# drsc_launcher_roundtrip.sh — PRD-dream-run-record-review-scope R11: the two-repo
# acceptance the consumer runs on a host that has both the launcher (dotfiles
# .local/bin/fable-launch.sh) and this repository. Outside every tests/drsc_*.sh glob
# and never paired by prefix; the builder does not run it.
#
# Launches an author and a spy reviewer (review.snapshot = a sha256sum manifest, a
# pre-drawn --session-id) through the launcher's FABLE_LAUNCH_TEST=1 seams into a
# temporary decisions log, writes a run note binding both rows, and lints it with
# --decisions. Exit 0 when the lint reports snapshot: verified; 1 on any finding or
# launcher refusal; 2 when FABLE_LAUNCH_BIN is unset or a seam file is missing (a usage
# error, never a pass).
#
# Env: FABLE_LAUNCH_BIN (required: the launcher path); DOTFILES_DIR (default: the
#   repository two levels above the launcher) supplies SKILL_ROUTE_POLICY
#   (.config/skill-routing/policy.json) and ACCOUNT_LANE_POLICY
#   (tests/fixtures/account-lanes/policy.test.json) unless those are set. Everything is
#   written under a mktemp -d (spy claude, synthetic token store, lane state, decisions
#   log); no real credential, log, unit or provider is touched.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$here/../.." && pwd)"
LINT="$REPO/skills/dream/scripts/dream-run-note-lint.sh"
usage() { echo "usage error: $*" >&2; exit 2; }
[ -n "${FABLE_LAUNCH_BIN:-}" ] || usage "FABLE_LAUNCH_BIN is unset (the fable-launch.sh to test)"
[ -x "$FABLE_LAUNCH_BIN" ] || usage "FABLE_LAUNCH_BIN is not executable: $FABLE_LAUNCH_BIN"
DOTFILES_DIR="${DOTFILES_DIR:-$(cd "$(dirname "$(readlink -f "$FABLE_LAUNCH_BIN")")/../.." && pwd)}"
SKILL_ROUTE_POLICY="${SKILL_ROUTE_POLICY:-$DOTFILES_DIR/.config/skill-routing/policy.json}"
ACCOUNT_LANE_POLICY="${ACCOUNT_LANE_POLICY:-$DOTFILES_DIR/tests/fixtures/account-lanes/policy.test.json}"
for f in "$SKILL_ROUTE_POLICY" "$ACCOUNT_LANE_POLICY" "$LINT"; do [ -r "$f" ] || usage "missing seam file: $f"; done
command -v python3 >/dev/null || usage "python3 is required"

T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL drsc_launcher_roundtrip: $*"; exit 1; }
# the launcher's test seams (as dotfiles tests/fable-launch-review_lib.sh): spy claude, synthetic token store, private lanes
mkdir -p "$T/store"
for a in josephsyen:JOSEPH jyen.tech:TECH jyen.pm:PM mcphost.dev:MCP; do printf 'TOKEN-%s-synthetic' "${a#*:}" >"$T/store/${a%%:*}"; done
chmod 600 "$T/store"/*
printf '#!/usr/bin/env bash\necho "spy args=$*" >>"%s/spy.log"\nexit 0\n' "$T" >"$T/claude"; chmod +x "$T/claude"
echo evidence >"$T/ev.md"; printf 'A1300\n' >"$T/ids.txt"
DEC="$T/decisions.jsonl"; : >"$DEC"
export FABLE_RR_DIR="$T/rr" FABLE_LAUNCH_TEST=1 FABLE_TOKEN_STORE="$T/store" FABLE_CLAUDE_BIN="$T/claude"
export ACCOUNT_LANE_STATE="$T/lanes" ACCOUNT_LANE_POLICY ACCOUNT_LANE_TEST=1 ACCOUNT_LANE_NOW=1800000000
export SKILL_ROUTE_POLICY SKILL_ROUTING_DECISIONS="$DEC" SKILL_ROUTE_LEDGER_IDS="$T/ids.txt"
export HOME="$T/fakehome"; mkdir -p "$HOME"
unset ANALYSIS_WIKI_DIR

# the PRD home: two stubs, a manifest whose paths are relative to its own directory
H="$T/home"; mkdir -p "$H/built-prds" "$H/notes/snapshots" "$H/notes/reviews"
cp "$REPO/tests/fixtures/drrec/review-scope/PRD-rs-alpha.md" "$REPO/tests/fixtures/drrec/review-scope/PRD-rs-beta.md" "$H/built-prds/"
(cd "$H/notes/snapshots" && sha256sum ../../built-prds/PRD-rs-alpha.md ../../built-prds/PRD-rs-beta.md >happy.sha256) || fail "sha256sum"
TASK="RT-$$"
req() { # <file> [snapshot]
  python3 - "$1" "$TASK" "file:$T/ev.md" "${2:-}" <<'PY'
import json,sys
out,task,ev,snap=sys.argv[1:]
r={"task_id":task,"skill":"dream","decision_class":"consequential_uncertainty","evidence_refs":["ledger:A1300",ev]}
if snap:
    r["review"]={"reason":"independent_verifier_required","evidence":["ledger:A1300",ev],"snapshot":snap}
json.dump(r,open(out,"w"))
PY
}
SA="$(cat /proc/sys/kernel/random/uuid)"; SR="$(cat /proc/sys/kernel/random/uuid)"
req "$T/author.json"; req "$T/review.json" "$H/notes/snapshots/happy.sha256"
"$FABLE_LAUNCH_BIN" --route-request "$T/author.json" --session-id "$SA" -p x >/dev/null 2>"$T/err.author" || fail "author launch rc=$?: $(cat "$T/err.author")"
"$FABLE_LAUNCH_BIN" --route-request "$T/review.json" --session-id "$SR" -p x >/dev/null 2>"$T/err.review" || fail "review launch rc=$?: $(cat "$T/err.review")"

# the run note: Route = the author's launch row, Review = the reviewer session, verdicts + result capture, matrix
python3 - "$DEC" "$SA" "$SR" "$H" "$REPO" <<'PY' || fail "could not write the run note from the launcher's rows"
import json,sys,shutil,datetime
dec,sa,sr,h,repo=sys.argv[1:]
rows=[json.loads(l) for l in open(dec) if l.strip()]
a=[r for r in rows if r.get("session")==sa and r.get("decision")=="launch"][-1]
v=[r for r in rows if r.get("session")==sr and r.get("decision")=="launch"][-1]
assert a.get("role")=="author" and v.get("role")=="review" and v.get("scope_id"), (a, v)
mx="notes/reviews/2026-11-16T04:05:40-08:00-adversarial.md"
shutil.copy(f"{repo}/tests/fixtures/drrec/verified/home/{mx}", f"{h}/{mx}")
text="rs-alpha APPROVE fable\nrs-beta APPROVE fable"
open(f"{h}/notes/reviews/rt-review.txt","w").write(text+"\n")
json.dump({"type":"result","is_error":False,"session_id":sr,"result":"Review done.\n"+text},open(f"{h}/notes/reviews/rt-review.json","w"))
ts=datetime.datetime.now().astimezone().isoformat(timespec="seconds")
open(f"{h}/notes/dream-log.md","w").write("\n".join([
 "# dream log (roundtrip)","",f"## {ts}  /dream  vision-rs-roundtrip",
 "Contract: /roundtrip/build-contract.md   Hooks: dream.lint","Seeds: roundtrip","Lineage: greenfield",
 "Drafted: PRD-rs-alpha.md, PRD-rs-beta.md   Build order: rs-alpha","Lint: clean   Eligibility: pending scan",
 f"Task: {a['task_id']}   Consumer: hermes",
 f"Route: {a['route']} {a['model']} {a['effort']} session={sa} decision={a['ts']}",
 f"Analysis: wwhtbt=skipped: roundtrip 5whys=skipped: roundtrip adversarial={mx} uncovered=1",
 f"Review: notes/reviews/rt-review.txt reviewer-session={sr} result=notes/reviews/rt-review.json",
 "State: rs-alpha=linted rs-alpha=reviewed:APPROVE rs-beta=linted rs-beta=reviewed:APPROVE",
 "Open questions: none",""]))
PY
js=$("$LINT" "$H/notes/dream-log.md" --last --prd-dir "$H" --decisions "$DEC" --json 2>"$T/lint.err"); rc=$?
snap=$(printf '%s' "$js" | python3 -c 'import sys,json; print(json.load(sys.stdin)["provenance"].get("snapshot"))' 2>/dev/null)
[ "$rc" = 0 ] && [ "$snap" = verified ] || fail "lint rc=$rc snapshot=$snap: $(cat "$T/lint.err") $js"
echo "PASS drsc_launcher_roundtrip: snapshot verified (launcher $FABLE_LAUNCH_BIN)"
