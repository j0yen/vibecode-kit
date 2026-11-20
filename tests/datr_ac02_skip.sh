#!/usr/bin/env bash
# AC2 (R1, R2) — entries covered by each R1 trigger (a State: slug no earlier entry of the Task names, a
# drafted token, a new Seeds: token, a PRD whose bytes moved from the newest review.snapshot an earlier
# entry binds, and the checked-in drfc mission with and without its amended repairs row) and one not,
# each skipping on a corroborated outage, an outage followed by a wwhtbt launch, a fixable request, a
# live-worker denial, another task's denial, free text and no decisions log: covered entries accept only
# the corroborated outage (the rest exit 1 with exactly analysis-skip-refused); the uncovered entry keeps
# today's result: exit 0, covered none, and its text output byte-identical to the Cited-tree lint's.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
cases ac02
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome" "$T/cwd"; base_lint "$T/base.sh"
uncov=(ac02-uncovered-free-text ac02-uncovered-no-failure-line)
mapfile -t -O 2 uncov < <(python3 -I -c 'import importlib.util,sys; s=importlib.util.spec_from_file_location("d",sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); [print(n) for n in m.CASES if n.startswith("ac02-r2-") and "-uncovered" in n]' "$DFX")
[ "${#uncov[@]}" -ge 18 ] || fail "only ${#uncov[@]} uncovered cases found for the 43d5b39 comparison"
for c in "${uncov[@]}"; do
  python3 -I "$DFX" "$c" "$T/$c" || fail "fixture $c did not build"
  args=("$T/$c/home/notes/dream-log.md" --last --prd-dir "$T/$c/home" --decisions "$T/$c/decisions.jsonl")
  (cd "$T/cwd" && HOME="$T/fakehome" SKILL_ROUTING_POLICY="$T/$c/policy.json" bash "$T/base.sh" "${args[@]}" > "$T/o.out" 2> "$T/o.err"); ro=$?
  (cd "$T/cwd" && HOME="$T/fakehome" SKILL_ROUTING_POLICY="$T/$c/policy.json" "$LINT" "${args[@]}" > "$T/n.out" 2> "$T/n.err"); rn=$?
  [ "$ro" = "$rn" ] && cmp -s "$T/o.out" "$T/n.out" && cmp -s "$T/o.err" "$T/n.err" \
    || fail "$c: uncovered entry differs from 43d5b39 (exit $ro/$rn): $(diff "$T/o.out" "$T/n.out" | head -3) $(diff "$T/o.err" "$T/n.err" | head -3)"
done
pass "$CASES_PASSED cases; the ${#uncov[@]} uncovered entries lint as at 43d5b39"
