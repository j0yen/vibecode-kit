#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 6 (R9) — every fixture checked in at 43d5b39 (through tests/fixtures/drmx/compat.py, as datr_ac06_compat.sh runs
# it: drrec home and verified, drei, drsp, and drmr and drfc with every variant; every entry and --last, text and --json; the dated families
# re-dated before the cutover) and a pre-cutover copy of each Analysis: entry of carbon's four real Dream logs (CR6, at their own dates) lint
# byte-identically (stdout, stderr, exit) with the Cited-tree lint and this one; and each of those real entries that binds no page, re-dated onto
# the cutover day (so R1-R7 apply), gives no consumption-missing: no entry without a bound page needs `Consumption:`. The real entries come from
# DATR_REAL_LOGS (read-only copies with their SHA256SUMS, the A1723 continuation's carbon read CR6); without it the test decides only the fixture
# half and exits 2. Both lints read the same decisions log: the CR6 copy when it brought one, else one well-formed row of an unrelated skill.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"            # LINT, base_lint (43d5b39 read by git at run time), fail, pass, here
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
base_lint "$T/base.sh"
python3 -I "$here/fixtures/drmx/compat.py" "$here/fixtures" "$T/base.sh" "$LINT" "$T/compat.tsv" False > "$T/compat.out" 2>&1 \
  || fail "fixtures: $(head -1 "$T/compat.tsv" | sed 's/^# //'); first: $(sed -n '2,4p' "$T/compat.tsv" | cut -f1-4 | tr '\n' ' ')"
[ -n "${DATR_REAL_LOGS:-}" ] || { echo "UNDECIDED $(basename "$0"): fixtures byte-identical ($(cat "$T/compat.out")); the real entries need DATR_REAL_LOGS (carbon read CR6)"; exit 2; }
(cd "$DATR_REAL_LOGS" && sha256sum -c --quiet SHA256SUMS) || fail "DATR_REAL_LOGS copies do not match their SHA256SUMS"
dec="$DATR_REAL_LOGS/decisions.jsonl"
if [ ! -f "$dec" ]; then
  dec="$T/dec.jsonl"
  printf '%s\n' '{"ts": "2026-01-01T00:00:00-08:00", "decision": "launch", "task_id": "none", "skill": "dfcn-unrelated", "route": "-", "model": "-", "effort": "-", "account": "-", "session": "00000000-0000-4000-8000-000000000000", "resume": false, "reasons": "dfcn ac06 fixture row"}' > "$dec"
fi
n=0; reached=0
for log in "$DATR_REAL_LOGS"/*.md; do
  rm -rf "$T/h"; mkdir -p "$T/h/notes"; cp "$log" "$T/h/notes/dream-log.md"
  while IFS= read -r ts; do
    for js in "" --json; do
      bash "$T/base.sh" "$T/h/notes/dream-log.md" --entry "$ts" --prd-dir "$T/h" --decisions "$dec" $js > "$T/o.out" 2> "$T/o.err"; ro=$?
      bash "$LINT" "$T/h/notes/dream-log.md" --entry "$ts" --prd-dir "$T/h" --decisions "$dec" $js > "$T/n.out" 2> "$T/n.err"; rn=$?
      [ "$ro" = "$rn" ] && cmp -s "$T/o.out" "$T/n.out" && cmp -s "$T/o.err" "$T/n.err" || fail "$(basename "$log") $ts ${js:-text}: differs (exit $ro/$rn)"
      [ "$rn" = 2 ] || reached=$((reached+1))
    done
    n=$((n+1))
  done < <(python3 -I - "$T/h/notes/dream-log.md" <<'PY'
import re, sys
t = open(sys.argv[1], encoding="utf-8").read()
for m in re.finditer(r"^## (\S+)  /dream  vision-[^\n]*\n((?:(?!## ).*\n?)*)", t, re.M):
    if re.search(r"^Analysis:", m.group(2), re.M):
        print(m.group(1))
PY
)
done
[ "$n" = "${DATR_REAL_ENTRIES:-20}" ] || fail "linted $n governed real entries, want ${DATR_REAL_ENTRIES:-20}"
[ "$reached" -gt 0 ] || fail "every real-entry run exited 2 before the entry checks; the comparison decided nothing"
# R1: a real entry that binds no page, re-dated onto the cutover day, needs no Consumption: line
out=$(python3 -I - "$LINT" "$DATR_REAL_LOGS" "$T" "$dec" <<'PY'
import json, os, re, subprocess, sys
lint, logs, top, dec = sys.argv[1:5]
cut = re.search(r'^TRIGGER_CUTOVER = "(\d{4}-\d\d-\d\d)"', open(lint, encoding="utf-8").read(), re.M).group(1)
ts_new = cut + "T02:00:00-08:00"
env = dict(os.environ, HOME=os.path.join(top, "fakehome"))
nopage = bad = 0
for name in sorted(os.listdir(logs)):
    if not name.endswith(".md"):
        continue
    text = open(os.path.join(logs, name), encoding="utf-8").read()
    heads = list(re.finditer(r"^## (\S+)  /dream  vision-.*$", text, re.M))
    for k, m in enumerate(heads):
        body = text[m.end():heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        a = re.search(r"^Analysis: wwhtbt=(.*?) 5whys=(.*?) adversarial=", body, re.M)
        if not a:
            continue
        if re.match(r"(ran|reused) ", a.group(1)) or re.match(r"(page|reused) ", a.group(2)):
            continue                                    # binds a page: R1 asks a Consumption: line of it (not this half)
        nopage += 1
        home = os.path.join(top, "r1-%s-%d" % (name, k))
        os.makedirs(os.path.join(home, "notes"), exist_ok=True)
        with open(os.path.join(home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
            fh.write(text[:m.start()] + "## %s  /dream  vision-dfcn-ac06\n" % ts_new + body)
        p = subprocess.run(["bash", lint, os.path.join(home, "notes", "dream-log.md"), "--entry", ts_new, "--prd-dir", home, "--decisions", dec, "--json"],
                           capture_output=True, text=True, env=env, cwd=top)
        try:
            d = json.loads(p.stdout)
        except ValueError:
            d = None
        if not isinstance(d, dict):
            bad += 1; print("FAIL %s %s re-dated: no JSON (rc %s) %r" % (name, m.group(1), p.returncode, p.stderr.strip()[-160:])); continue
        if "consumption-missing" in (d.get("findings") or []) or "FAIL consumption-missing" in p.stderr:
            bad += 1; print("FAIL %s %s re-dated binds no page but gives consumption-missing" % (name, m.group(1)))
        if not isinstance(d.get("consumption"), dict):
            bad += 1; print("FAIL %s %s re-dated: no consumption object (R1-R7 did not apply after the cutover)" % (name, m.group(1)))
print("NOPAGE %d BAD %d" % (nopage, bad))
sys.exit(1 if bad else 0)
PY
) || fail "$(printf '%s\n' "$out" | grep '^FAIL' | head -5)"
np=$(printf '%s\n' "$out" | sed -n 's/^NOPAGE \([0-9]*\) .*/\1/p')
[ "${np:-0}" -gt 0 ] || fail "no real entry without a bound page to re-date"
pass "fixtures byte-identical; $n real entries byte-identical at their own dates ($reached of $((2*n)) lint pairs past the decisions step); $np real entries without a bound page need no Consumption: after the cutover (decisions: $dec)"
