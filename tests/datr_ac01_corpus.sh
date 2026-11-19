#!/usr/bin/env bash
# AC1 (R1, R2) — read-only copies of the 21 governed entries of the four Dream logs (DATR_REAL_LOGS, the
# A1723 continuation's carbon read CR6), each re-dated to the cutover: every covered entry whose
# wwhtbt=skipped is free text exits 1 with analysis-skip-refused, and the same entry rewritten to
# `wwhtbt=ran <page>`, the page bound to a wwhtbt launch row of the entry's Task (its first lines name
# the row's session), no longer gives analysis-skip-refused or a wwhtbt provenance finding. Other
# findings of an entry linted away from its home are not this AC's. Without DATR_REAL_LOGS: exit 2.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
[ -n "${DATR_REAL_LOGS:-}" ] || { echo "UNDECIDED $(basename "$0"): needs DATR_REAL_LOGS (carbon read CR6)"; exit 2; }
(cd "$DATR_REAL_LOGS" && sha256sum -c --quiet SHA256SUMS) || fail "DATR_REAL_LOGS copies do not match their SHA256SUMS"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
out=$(python3 -I - "$LINT" "$DATR_REAL_LOGS" "$T" <<'PY'
import json, os, re, subprocess, sys
lint, logs, top = sys.argv[1:4]
src = open(lint, encoding="utf-8").read()
cut = re.search(r'^TRIGGER_CUTOVER = "(\d{4}-\d\d-\d\d)"', src, re.M).group(1)
ts_new = cut + "T02:00:00-08:00"
SID = "dddddddd-0000-4000-8000-000000000001"
pol = os.path.join(top, "policy.json")
json.dump({"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$", "placeholders": ["none", "tbd"]}}, open(pol, "w"))
env = dict(os.environ, HOME=os.path.join(top, "fakehome"), SKILL_ROUTING_POLICY=pol)
n = cov = bad = refused = cleared = 0
for name in sorted(os.listdir(logs)):
    if not name.endswith(".md"):
        continue
    text = open(os.path.join(logs, name), encoding="utf-8").read()
    heads = [m for m in re.finditer(r"^## (\S+)  /dream  vision-.*$", text, re.M)]
    for k, m in enumerate(heads):
        body = text[m.end():heads[k + 1].start() if k + 1 < len(heads) else len(text)]
        a = re.search(r"^Analysis: wwhtbt=skipped(?::)? .*$", body, re.M)
        if not re.search(r"^Analysis:", body, re.M):
            continue
        n += 1
        task = (re.search(r"^Task:\s+(\S+)", body, re.M) or re.search(r"^Task:\s+(\S+)", text[:m.start()], re.M) or [None, "none"])[1]
        for variant in ("as-is", "ran"):
            b = body
            if variant == "ran":
                b = re.sub(r"wwhtbt=skipped(?::)? .*? 5whys=", "wwhtbt=ran notes/analysis/datr-wwhtbt.md 5whys=", body, count=1, flags=re.M)
            home = os.path.join(top, f"{name}-{k}-{variant}")
            os.makedirs(os.path.join(home, "notes", "analysis"), exist_ok=True)
            with open(os.path.join(home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
                fh.write(text[:m.start()] + f"## {ts_new}  /dream  vision-datr-ac01\n" + b)
            with open(os.path.join(home, "notes", "analysis", "datr-wwhtbt.md"), "w", encoding="utf-8") as fh:
                fh.write(f"# wwhtbt page\nsession: {SID}\n")
            dec = os.path.join(home, "decisions.jsonl")
            with open(dec, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": cut + "T00:05:00-08:00", "decision": "launch", "task_id": task, "skill": "wwhtbt", "route": "opus-xhigh",
                                     "model": "claude-opus-5-5", "effort": "xhigh", "account": "x", "session": SID, "resume": False, "reasons": "datr-ac01"}) + "\n")
            p = subprocess.run(["bash", lint, os.path.join(home, "notes", "dream-log.md"), "--entry", ts_new, "--prd-dir", home, "--decisions", dec, "--json"],
                               capture_output=True, text=True, env=env, cwd=top, timeout=300)
            try:
                d = json.loads(p.stdout)
            except ValueError:
                d = {}
            fid = d.get("findings") or []
            covered = (d.get("analysis") or {}).get("covered")
            if variant == "as-is":
                is_cov = covered not in (None, "none")
                cov += 1 if is_cov else 0
                if is_cov and a:
                    if p.returncode == 1 and "analysis-skip-refused" in fid:
                        refused += 1
                    else:
                        bad += 1; print(f"FAIL {name} entry {m.group(1)}: covered ({covered}) free-text skip: rc={p.returncode} findings={fid}")
            elif a and covered not in (None, "none"):    # only a free-text skip is rewritten; an entry that already ran a page is not this AC's
                errs = [l for l in p.stderr.splitlines() if l.startswith(("FAIL analysis-skip-refused", "FAIL analysis-provenance-missing: wwhtbt", "FAIL analysis-page-unbound: wwhtbt"))]
                if errs:
                    bad += 1; print(f"FAIL {name} entry {m.group(1)} rewritten to ran: {errs[:2]}")
                elif a:
                    cleared += 1
print(f"entries={n} covered={cov} refused={refused} cleared={cleared} bad={bad}")
sys.exit(1 if bad else 0)
PY
); rc=$?
printf '%s\n' "$out" | tail -1
[ "$rc" = 0 ] || fail "$(printf '%s\n' "$out" | head -10)"
[ "$(printf '%s\n' "$out" | tail -1 | sed -n 's/^entries=\([0-9]*\).*/\1/p')" = "${DATR_REAL_ENTRIES:-21}" ] || fail "want ${DATR_REAL_ENTRIES:-21} governed entries: $(printf '%s\n' "$out" | tail -1)"
pass "$(printf '%s\n' "$out" | tail -1)"
