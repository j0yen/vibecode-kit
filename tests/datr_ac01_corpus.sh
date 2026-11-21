#!/usr/bin/env bash
# AC1 (R1, R2) — read-only copies of the 20 governed entries of carbon's four Dream logs (DATR_REAL_LOGS, the
# A1723 continuation's carbon read CR6 of 2026-11-19, pinned by its SHA256SUMS), each re-dated to the cutover: every covered entry whose
# wwhtbt=skipped is free text exits 1 with analysis-skip-refused, and the same entry rewritten to
# `wwhtbt=ran <page>`, the page bound to a wwhtbt launch row of the entry's Task (its first lines name
# the row's session), stays covered, reports that page bound (provenance.wwhtbt = boundary) and gives no
# analysis-skip-refused and no other finding on its wwhtbt value. The rewritten run is compared with a
# baseline run of the same entry carrying a value R2 accepts (a corroborated blocked skip): any finding id
# it adds counts, whatever its message says. An entry with Task: none, or with no well-formed Task: line
# of its own (read as the lint reads it), has no launch row of its Task to bind, so it is counted apart
# (task_none). Other findings of an entry linted away from its home are not this AC's.
# DATR_REAL_ENTRIES (default 20) and DATR_REAL_REFUSED (default 18) are the governed entries and the covered
# free-text skips the corpus must give, both counted on CR6 independently of the lint (the other 2 entries already
# ran a WWHTBT page and are outside the skip population); set both for another corpus.
# Without DATR_REAL_LOGS: exit 2.
set -uo pipefail
. "$(dirname "${BASH_SOURCE[0]}")/datr_lib.sh"
[ -n "${DATR_REAL_LOGS:-}" ] || { echo "UNDECIDED $(basename "$0"): needs DATR_REAL_LOGS (carbon read CR6)"; exit 2; }
(cd "$DATR_REAL_LOGS" && sha256sum -c --quiet SHA256SUMS) || fail "DATR_REAL_LOGS copies do not match their SHA256SUMS"
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT; mkdir -p "$T/fakehome"; export HOME="$T/fakehome"; unset SKILL_ROUTING_DECISIONS
out=$(python3 -I - "$LINT" "$DATR_REAL_LOGS" "$T" <<'PY'
import collections, json, os, re, subprocess, sys
lint, logs, top = sys.argv[1:4]
src = open(lint, encoding="utf-8").read()
cut = re.search(r'^TRIGGER_CUTOVER = "(\d{4}-\d\d-\d\d)"', src, re.M).group(1)
ts_new = cut + "T02:00:00-08:00"
SID = "dddddddd-0000-4000-8000-000000000001"
pol = os.path.join(top, "policy.json")
json.dump({"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$", "placeholders": ["none", "tbd"]}}, open(pol, "w"))
env = dict(os.environ, HOME=os.path.join(top, "fakehome"), SKILL_ROUTING_POLICY=pol)
# finding consumption R1: the `ran` rewrite binds a page, so it carries a Consumption: line and a record binding the page's one finding (its falsifier)
# by a `test` row in a scratch repository, so the rewrite adds nothing but the wwhtbt value
import hashlib
PAGE = f"# wwhtbt page\nsession: {SID}\n" + "\n# Weakest link\n\nThe corpus page's weakest link.\n\n# Mechanisms\n\n1. corpus mechanism — state LIVE\n"
repo = os.path.join(top, "cons-repo")
os.makedirs(os.path.join(repo, "tests"))
open(os.path.join(repo, "tests", "cons.sh"), "w").write("# binds datr-wwhtbt.md#falsifier\n")
genv = dict(env, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
    subprocess.run(["git", "-C", repo] + c, check=True, capture_output=True, env=genv)
COMMIT = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, env=genv).stdout.strip()
RECORD = json.dumps({"id": "ac01-c1", "page": "notes/analysis/datr-wwhtbt.md", "page_sha256": hashlib.sha256(PAGE.encode()).hexdigest(),
                     "finding": "falsifier", "binding": "test", "author_session": SID, "repo": repo, "commit": COMMIT, "path": "tests/cons.sh"}) + "\n"
n = cov = bad = refused = cleared = task_none = 0
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
        is_cov, base, base_ids = False, collections.Counter(), set()
        tl = [l for l in body.splitlines() if l.startswith("Task:")]    # as the lint reads it (entry_task): the entry's own last Task: line,
        mt = re.match(r"^Task:\s+(\S+)\s+Consumer:", tl[-1]) if tl else None   # none when that line is malformed
        task = mt.group(1) if mt else "none"                            # none of its own: no launch row of its Task to bind
        for variant in ("as-is", "blocked", "ran"):
            if variant == "blocked" and not (a and is_cov):    # the baseline is needed only for an entry the rewrite is checked on
                continue
            b = body
            if variant == "ran":
                b = re.sub(r"wwhtbt=skipped(?::)? .*? 5whys=", "wwhtbt=ran notes/analysis/datr-wwhtbt.md 5whys=", body, count=1, flags=re.M)
                b = b.rstrip("\n") + "\nConsumption: notes/consumption/datr-ac01.jsonl\n"
            elif variant == "blocked":                          # the same entry with a value R2 accepts: a corroborated route outage
                b = re.sub(r"wwhtbt=skipped(?::)? .*? 5whys=", f"wwhtbt=skipped: blocked decision={cut}T00:10:00-08:00 5whys=", body, count=1, flags=re.M)
            home = os.path.join(top, f"{name}-{k}-{variant}")
            os.makedirs(os.path.join(home, "notes", "analysis"), exist_ok=True)
            with open(os.path.join(home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
                fh.write(text[:m.start()] + f"## {ts_new}  /dream  vision-datr-ac01\n" + b)
            with open(os.path.join(home, "notes", "analysis", "datr-wwhtbt.md"), "w", encoding="utf-8") as fh:
                fh.write(PAGE)
            os.makedirs(os.path.join(home, "notes", "consumption"), exist_ok=True)
            with open(os.path.join(home, "notes", "consumption", "datr-ac01.jsonl"), "w", encoding="utf-8") as fh:
                fh.write(RECORD)
            dec = os.path.join(home, "decisions.jsonl")
            with open(dec, "w", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": cut + "T00:05:00-08:00", "decision": "launch", "task_id": task, "skill": "wwhtbt", "route": "opus-xhigh",
                                     "model": "claude-opus-5-5", "effort": "xhigh", "account": "x", "session": SID, "resume": False, "reasons": "datr-ac01"}) + "\n")
                if variant == "blocked":                        # the denial it names; no wwhtbt launch row falls between it and the header
                    fh.write(json.dumps({"ts": cut + "T00:10:00-08:00", "decision": "denied", "task_id": task, "skill": "wwhtbt", "route": "opus-xhigh",
                                         "model": "claude-opus-5-5", "effort": "xhigh", "account": "x", "session": None, "resume": False,
                                         "reasons": "policy file not found"}) + "\n")
            p = subprocess.run(["bash", lint, os.path.join(home, "notes", "dream-log.md"), "--entry", ts_new, "--prd-dir", home, "--decisions", dec, "--json"],
                               capture_output=True, text=True, env=env, cwd=top)
            try:
                d = json.loads(p.stdout)
            except ValueError:
                d = None
            if not isinstance(d, dict):                         # a crash or a non-JSON answer is a failure, never a skipped check
                bad += 1; print(f"FAIL {name} entry {m.group(1)} ({variant}): no JSON result: rc={p.returncode} {p.stderr.strip()[-160:]!r}")
                continue
            fid = d.get("findings") or []
            covered = (d.get("analysis") or {}).get("covered")
            ids = collections.Counter(re.findall(r"^FAIL ([\w-]+):", p.stderr, re.M))
            if variant == "blocked":                            # the baseline the rewritten run is compared with (nothing is asserted on it)
                base = ids - collections.Counter({"analysis-skip-refused": ids["analysis-skip-refused"]})
                base_ids = set(fid) - {"analysis-skip-refused"}
            elif variant == "as-is":
                is_cov = covered not in (None, "none")
                cov += 1 if is_cov else 0
                if is_cov and a:
                    if p.returncode == 1 and "analysis-skip-refused" in fid:
                        refused += 1
                    else:
                        bad += 1; print(f"FAIL {name} entry {m.group(1)}: covered ({covered}) free-text skip: rc={p.returncode} findings={fid}")
            elif a and is_cov:    # variant ran: only a covered free-text skip is rewritten; an entry that already ran a page is not this AC's
                # every finding on the wwhtbt value names it ("<id>: wwhtbt..."), whichever check raises it
                errs = [l for l in p.stderr.splitlines() if l.startswith("FAIL analysis-skip-refused") or re.match(r"FAIL [\w-]+: wwhtbt\b", l)]
                # the two runs differ only in the wwhtbt value, so every finding the rewritten run adds is about that value, whatever its message says
                added = ids - base
                added_json = set(fid) - base_ids                # the JSON findings too, in case a finding is not printed
                if task == "none":
                    added.pop("task-none-ran", None)
                    added_json.discard("task-none-ran")
                errs += [f"added {k} x{v}" for k, v in sorted(added.items())] + [f"added {k} (json)" for k in sorted(added_json - set(added))]
                bound = (d.get("provenance") or {}).get("wwhtbt")
                if covered in (None, "none"):                   # the rewrite touches no R1 trigger, so the entry stays covered
                    bad += 1; print(f"FAIL {name} entry {m.group(1)} rewritten to ran: covered={covered!r}")
                elif task == "none":                            # no launch row of its Task to bind: only task-none-ran may refuse the value
                    if [l for l in errs if not l.startswith("FAIL task-none-ran:")] or "analysis-skip-refused" in fid:
                        bad += 1; print(f"FAIL {name} entry {m.group(1)} (Task: none) rewritten to ran: {errs[:2] or fid}")
                    else:
                        task_none += 1
                elif errs or "analysis-skip-refused" in fid or bound != "boundary":
                    bad += 1; print(f"FAIL {name} entry {m.group(1)} rewritten to ran: provenance.wwhtbt={bound!r} {errs[:2] or fid}")
                else:
                    cleared += 1
if cleared + task_none != refused:                      # AC 1: every refused entry clears once rewritten to ran
    bad += 1; print(f"FAIL {refused} covered free-text skips refused but {cleared} cleared (+{task_none} Task: none) once rewritten to ran")
if not refused:                                         # nothing shown: AC 1 needs at least one covered free-text skip
    bad += 1; print("FAIL no covered entry with a free-text wwhtbt=skipped was refused")
want = os.environ.get("DATR_REAL_REFUSED", "18")
if str(refused) != want:
    bad += 1; print(f"FAIL refused {refused} covered free-text skips, want DATR_REAL_REFUSED={want}")
print(f"entries={n} covered={cov} refused={refused} cleared={cleared} task_none={task_none} bad={bad}")
sys.exit(1 if bad else 0)
PY
); rc=$?
printf '%s\n' "$out" | tail -1
[ "$rc" = 0 ] || fail "$(printf '%s\n' "$out" | head -10)"
[ "$(printf '%s\n' "$out" | tail -1 | sed -n 's/^entries=\([0-9]*\).*/\1/p')" = "${DATR_REAL_ENTRIES:-20}" ] || fail "want ${DATR_REAL_ENTRIES:-20} governed entries: $(printf '%s\n' "$out" | tail -1)"
pass "$(printf '%s\n' "$out" | tail -1)"
