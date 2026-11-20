#!/usr/bin/env python3
"""Cases of PRD-dream-finding-consumption AC 2 (R3 bindings) and AC 3 (R3 residual acceptance, R4 receipts, R8 context), linted in check mode.

The fixture: one synthetic WWHTBT page `notes/analysis/fx-wwhtbt.md` (frontmatter falsifier `scripts/kill-fx.sh` with its digest, a `# Weakest link`
section, and three `# Mechanisms` items: SPEC, SPEC and LIVE, so the findings needing a row are `falsifier`, `mechanism:1` and `mechanism:2`); a PRD home
with `build-queue/PRD-fx-a.md` (AC 1 binds the falsifier with the kill script and string, AC 2 binds mechanism 1 with a `tests/` path, AC 3 names
mechanism 1 with no command, AC 4 names the falsifier with another script); a scratch git repo whose `tests/bind.sh` names all three findings; a
decisions log with review, author-lineage, role-less and other-Task launch rows; a reviews directory of verdict files; the routing policy's evidence
rule; and a temp canonical store behind a `wm-asks` shim: the wm-decide named by DFCN_WM_DECIDE (else the one on PATH) with its own WM_DECIDE_STATE
and HOME, so no case reads or writes a real ledger.

The base record binds every finding validly (falsifier: requirement AC 1 with kill and reexpression; mechanism 1: requirement AC 2 with its control;
mechanism 2: a test row) and lints to exit 0. Each case replaces or adds rows and states its exact exit, its exact finding-id set, and the texts one
FAIL line must carry (the row id, the key and `<page basename>#<finding>`).

Usage: dfcnfx.py --run <prefix> <lint> <scratch dir>   (exit 0 when every case of the prefix passes; one PASS or FAIL line per case)
       dfcnfx.py --nodrift <lint> <scratch dir> <swarm-decide tree>   (the lint's repair predicate against the close gate's own _satisfied)
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

PAGE = "notes/analysis/fx-wwhtbt.md"
BASE = "fx-wwhtbt.md"
AUTHOR = "a-1"
TASK = "A1"


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


def write(p, text, mode=0o644):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(p, mode)


class Fx:
    def __init__(self, T):
        self.T = T
        self.home = os.path.join(T, "home")
        self.repo = os.path.join(T, "repo")
        self.reviews = os.path.join(T, "reviews")
        self.dec = os.path.join(T, "decisions.jsonl")
        self.policy = os.path.join(T, "policy.json")
        self.fakehome = os.path.join(T, "fakehome")
        self.shim_dir = os.path.join(T, "shim")
        self.state = os.path.join(T, "canonical")
        os.makedirs(self.fakehome, exist_ok=True)
        self.kill = "#!/bin/sh\n# the fixture falsifier: prints KILL-FX when a finding has no row\necho KILL-FX\n"
        write(os.path.join(self.home, "scripts", "kill-fx.sh"), self.kill, 0o755)
        write(os.path.join(self.home, "scripts", "rx-fx.sh"), "#!/bin/sh\n# re-expression of the falsifier\necho KILL-FX\n", 0o755)
        write(os.path.join(self.home, "scripts", "other-kill.sh"), "#!/bin/sh\necho OTHER\n", 0o755)
        page = ("---\nfalsifier: scripts/kill-fx.sh sha256=%s\n---\n# Question\n\nDoes every finding of a bound page reach a binding row?\n\n"
                "# Weakest link\n\nThe fixture falsifier `bash scripts/kill-fx.sh` prints KILL-FX when a finding has no row.\n\n"
                "# Mechanisms\n\n1. Row per finding — ⚙ lint — owner A1723 author — state SPEC (A1723)\n"
                "2. Canonical repair — ⚙ wm-asks — owner ctl — state SPEC (A1300)\n3. Already live — ⚙ x — owner hermes — state LIVE\n"
                % sha(self.kill))
        write(os.path.join(self.home, PAGE), page)
        self.page_sha = sha(page)
        write(os.path.join(self.home, "build-queue", "PRD-fx-a.md"),
              "# PRD-fx-a\n\n## Acceptance criteria\n\n"
              "1. P0 — Given %s#falsifier, When `bash scripts/kill-fx.sh` runs on a record missing a row, Then it prints `KILL-FX` "
              "(re-expressed by `bash scripts/rx-fx.sh`).\n"
              "2. P0 — Given %s#mechanism:1, When `tests/fx_ac02.sh` runs its negative control, Then a record without the row exits 1.\n"
              "3. P0 — Given %s#mechanism:1, When a reader looks, Then the row is described in prose only.\n"
              "4. P0 — Given %s#falsifier, When `bash scripts/other-kill.sh` runs, Then it prints OTHER.\n" % (BASE, BASE, BASE, BASE))
        os.makedirs(os.path.join(self.repo, "tests"))
        write(os.path.join(self.repo, "tests", "bind.sh"), "# exercises %s#falsifier,mechanism:1,mechanism:2\n" % BASE)
        write(os.path.join(self.repo, "tests", "plain.sh"), "# names no finding\n")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", HOME=self.fakehome)
        for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
            subprocess.run(["git", "-C", self.repo] + c, check=True, env=env, capture_output=True)
        self.commit = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=True, env=env).stdout.strip()
        rows = [("rv-ok", TASK, "review"), (AUTHOR, TASK, "author"), (AUTHOR, TASK, "review"), ("rv-norole", TASK, None), ("rv-noline", TASK, "review"),
                ("rv-other", "A9", "review")]
        with open(self.dec, "w") as f:
            for i, (s, t, role) in enumerate(rows):
                r = {"ts": "2026-11-19T10:%02d:00-08:00" % i, "decision": "launch", "task_id": t, "skill": "dream", "route": "opus-xhigh",
                     "model": "claude-opus-5-5", "effort": "xhigh", "session": s}
                if role:
                    r["role"] = role
                f.write(json.dumps(r) + "\n")
        for name, text in (("verdict-ok.md", "Review session rv-ok\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-author.md", "Review session %s\naccepts c-res\n## VERDICT: APPROVE\n" % AUTHOR),
                           ("verdict-norole.md", "Review session rv-norole\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-noline.md", "Review session rv-noline\nthe residual is fine, accepts c-res in spirit\n## VERDICT: APPROVE\n"),
                           ("verdict-other.md", "Review session rv-other\naccepts c-res\n## VERDICT: APPROVE\n")):
            write(os.path.join(self.reviews, name), text)
        with open(self.policy, "w") as f:
            json.dump({"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$",
                                    "placeholders": ["none", "n/a", "na", "tbd", "todo", "unknown", "x", "xx"], "min_refs": 1}}, f)
        self.ids = {}

    # ---- the temp canonical store ----
    def canonical(self):
        wd = os.environ.get("DFCN_WM_DECIDE") or shutil.which("wm-decide")
        if not wd:
            raise SystemExit("FAIL dfcnfx: no wm-decide for the temp canonical store (set DFCN_WM_DECIDE to a wm-decide binary)")
        store_home = os.path.join(self.T, "store-home")
        os.makedirs(store_home, exist_ok=True)
        os.makedirs(self.shim_dir, exist_ok=True)
        write(os.path.join(self.shim_dir, "wm-asks"), "#!/bin/sh\nexec env WM_DECIDE_STATE='%s' HOME='%s' '%s' \"$@\"\n" % (self.state, store_home, wd), 0o755)
        for key, owner, what in (("repair", "ctl", "repair %s#mechanism:2 (the canonical repair)" % BASE),
                                 ("succ", "hermes", "successor S closes-after=row:{repair}"),
                                 ("loose", "hermes", "a successor without the closes-after text")):
            p = subprocess.run([os.path.join(self.shim_dir, "wm-asks"), "asks", "add", "--by", "t-author", "--owner", owner, "--due", "2026-12-31T09:00",
                                "--what", what.format(**self.ids), "--check", "true"], capture_output=True, text=True)
            if p.returncode != 0:
                raise SystemExit("FAIL dfcnfx: seeding the temp canonical store: %s%s" % (p.stdout, p.stderr))
            self.ids[key] = p.stdout.strip().split()[-1]
        return self.ids

    # ---- rows ----
    def row(self, rid, finding, binding, **kw):
        r = {"id": rid, "page": PAGE, "page_sha256": self.page_sha, "finding": finding, "binding": binding, "author_session": AUTHOR}
        r.update(kw)
        return r

    def base(self):
        return {"falsifier": self.row("c-fal", "falsifier", "requirement", prd="PRD-fx-a.md", ac=1,
                                      kill={"script": "scripts/kill-fx.sh", "sha256": sha(self.kill), "string": "KILL-FX"},
                                      reexpression={"script": "scripts/rx-fx.sh", "sha256": sha(open(os.path.join(self.home, "scripts", "rx-fx.sh")).read())}),
                "mechanism:1": self.row("c-m1", "mechanism:1", "requirement", prd="PRD-fx-a.md", ac=2,
                                        control="the negative control: a record without the row exits 1"),
                "mechanism:2": self.row("c-m2", "mechanism:2", "test", repo=self.repo, commit=self.commit, path="tests/bind.sh")}

    def fake_canonical(self, scenario):
        """A `wm-asks` that answers `asks query --ids` and `asks events <id>` from a scenario file, in the shapes the real CLI prints (query: the row
        keys of `asks query --json`; events: op plus a JSON-text detail). Used where the real intake path needs a root-owned policy (acceptance)."""
        d = os.path.join(self.T, "fake-shim")
        os.makedirs(d, exist_ok=True)
        sc = os.path.join(self.T, "scenario.json")
        with open(sc, "w") as f:
            json.dump(scenario, f)
        write(os.path.join(d, "wm-asks"), """#!/usr/bin/env python3
import json, sys
sc = json.load(open(%r))
a = sys.argv[1:]
if a[:2] == ["asks", "query"] and "--ids" in a:
    ids = a[a.index("--ids") + 1].split(",")
    print(json.dumps([r for r in sc["rows"] if r["ask_id"] in ids]))
elif a[:2] == ["asks", "events"]:
    print(json.dumps([dict(e, detail=json.dumps(e["detail"])) for e in sc["events"].get(a[2], [])]))
else:
    sys.exit("fake wm-asks: unexpected %%s" %% a)
""" % sc, 0o755)
        return d

    def lint(self, lint, rows, drop=(), wm_asks=True, task=TASK, require_closed=False, shim=None):
        rec = os.path.join(self.home, "record.jsonl")          # at the home's root: without --prd-home, row paths resolve against the record's directory
        with open(rec, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        path = os.environ.get("PATH", "/usr/bin:/bin")
        if wm_asks:
            path = (shim or self.shim_dir) + os.pathsep + path
        else:
            path = os.pathsep.join(d for d in path.split(os.pathsep) if not os.path.exists(os.path.join(d, "wm-asks")))
        args = ["bash", lint, "--consumption", rec, "--task", task, "--page", PAGE, "--json"] + (["--require-closed"] if require_closed else [])
        for flag, val in (("--prd-home", self.home), ("--reviews", self.reviews), ("--decisions", self.dec)):
            if flag not in drop:
                args += [flag, val]
        env = dict(os.environ, HOME=self.fakehome, PATH=path, SKILL_ROUTING_POLICY=self.policy)
        env.pop("SKILL_ROUTING_DECISIONS", None)
        p = subprocess.run(args, capture_output=True, text=True, env=env, cwd=self.T)
        try:
            d = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
        except ValueError:
            d = {}
        return p.returncode, d, p.stderr


CASES = {}


def case(name, rc, findings, needles=(), drop=(), unconsumed=None, scenario=None):
    def deco(fn):
        CASES[name] = {"fn": fn, "rc": rc, "findings": sorted(findings), "needles": list(needles), "drop": drop, "unconsumed": unconsumed,
                       "scenario": scenario}
        return fn
    return deco


def rows_with(fx, **repl):
    b = fx.base()
    b.update(repl)
    return list(b.values())


# ---------------------------------------------------------------- AC 2: one row per binding kind, valid and invalid
case("ac02-valid-requirement-and-test", 0, [], unconsumed=[])(lambda fx: rows_with(fx))
case("ac02-valid-repair", 0, [], unconsumed=[])(lambda fx: rows_with(fx, **{"mechanism:2": fx.row(
    "c-rep", "mechanism:2", "repair", ask=fx.ids["repair"], owner="ctl", successor=fx.ids["succ"])}))
case("ac02-valid-pending", 0, [], unconsumed=[])(lambda fx: rows_with(fx, **{"mechanism:2": fx.row(
    "c-pen", "mechanism:2", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask=fx.ids["repair"], successor=fx.ids["succ"])}))
case("ac02-valid-residual", 0, [], unconsumed=[])(lambda fx: rows_with(fx, **{"mechanism:2": fx.row(
    "c-res", "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by="rv-ok")}))
case("ac02-valid-part-residual-beside-a-binding", 0, [], unconsumed=[])(lambda fx: rows_with(fx) + [fx.row(
    "c-res", "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by="rv-ok", part="the documentation half")])
case("ac02-ac-absent", 1, ["consumption-binding-invalid"], ["row c-m1 (%s#mechanism:1)" % BASE, "key ac: PRD-fx-a.md has no AC 9"])(
    lambda fx: rows_with(fx, **{"mechanism:1": dict(fx.base()["mechanism:1"], ac=9)}))
case("ac02-ac-commandless", 1, ["consumption-binding-invalid"], ["row c-m1 (%s#mechanism:1)" % BASE, "key ac: AC 3 of PRD-fx-a.md carries no backticked command"])(
    lambda fx: rows_with(fx, **{"mechanism:1": dict(fx.base()["mechanism:1"], ac=3)}))
case("ac02-falsifier-ac-without-its-script-and-kill-string", 1, ["consumption-binding-not-discriminating"],
     ["row c-fal (%s#falsifier)" % BASE, "key kill: AC 4 of PRD-fx-a.md does not carry the script's basename and the kill string"])(
    lambda fx: rows_with(fx, falsifier=dict(fx.base()["falsifier"], ac=4, reexpression=None)))
case("ac02-falsifier-without-kill", 1, ["consumption-binding-not-discriminating"], ["row c-fal (%s#falsifier)" % BASE, "kill = {script, sha256, string}"])(
    lambda fx: rows_with(fx, falsifier={k: v for k, v in fx.base()["falsifier"].items() if k != "kill"}))
case("ac02-kill-script-not-the-pages-own", 1, ["consumption-binding-invalid"],
     ["row c-fal (%s#falsifier)" % BASE, "key kill: scripts/other-kill.sh is not the page's own falsifier scripts/kill-fx.sh"])(
    lambda fx: rows_with(fx, falsifier=dict(fx.base()["falsifier"], kill={"script": "scripts/other-kill.sh", "string": "OTHER",
                                                                          "sha256": sha(open(os.path.join(fx.home, "scripts", "other-kill.sh")).read())})))
case("ac02-mechanism-without-control", 1, ["consumption-binding-not-discriminating"], ["row c-m1 (%s#mechanism:1)" % BASE, "needs the control"])(
    lambda fx: rows_with(fx, **{"mechanism:1": {k: v for k, v in fx.base()["mechanism:1"].items() if k != "control"}}))
case("ac02-test-without-commit", 1, ["consumption-binding-invalid"], ["row c-m2 (%s#mechanism:2)" % BASE, "missing commit"])(
    lambda fx: rows_with(fx, **{"mechanism:2": {k: v for k, v in fx.base()["mechanism:2"].items() if k != "commit"}}))
case("ac02-test-without-path", 1, ["consumption-binding-invalid"], ["row c-m2 (%s#mechanism:2)" % BASE, "missing path"])(
    lambda fx: rows_with(fx, **{"mechanism:2": {k: v for k, v in fx.base()["mechanism:2"].items() if k != "path"}}))
case("ac02-test-path-not-at-the-commit", 1, ["consumption-binding-invalid"], ["row c-m2 (%s#mechanism:2)" % BASE, "key path: tests/absent.sh is not in"])(
    lambda fx: rows_with(fx, **{"mechanism:2": dict(fx.base()["mechanism:2"], path="tests/absent.sh")}))
case("ac02-test-blob-names-no-finding", 1, ["consumption-binding-invalid"], ["row c-m2 (%s#mechanism:2)" % BASE, "key path: tests/plain.sh does not name"])(
    lambda fx: rows_with(fx, **{"mechanism:2": dict(fx.base()["mechanism:2"], path="tests/plain.sh")}))
case("ac02-repair-unbound-successor", 1, ["consumption-repair-unbound"], ["row c-rep (%s#mechanism:2)" % BASE, "closes-after=row:"])(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask=fx.ids["repair"], owner="ctl", successor=fx.ids["loose"])}))
case("ac02-repair-wrong-owner", 1, ["consumption-repair-unbound"], ["row c-rep (%s#mechanism:2)" % BASE, "owner hermes"])(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask=fx.ids["repair"], owner="hermes", successor=fx.ids["succ"])}))
case("ac02-pending-overdue", 1, ["consumption-pending-overdue"], ["row c-pen (%s#mechanism:2)" % BASE, "due 2020-01-01T00:00:00+00:00 has passed"])(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-pen", "mechanism:2", "pending", owner="ctl", due="2020-01-01T00:00:00+00:00",
                                                       ask=fx.ids["repair"], successor=fx.ids["succ"])}))
case("ac02-second-unparted-row-beside-a-binding", 1, ["consumption-grammar"], ["%s#mechanism:2: rows c-m2,c-res bind it" % BASE])(
    lambda fx: rows_with(fx) + [fx.row("c-res", "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by="rv-ok")])
case("ac02-part-residual-unaccepted-beside-a-binding", 1, ["consumption-residual-unaccepted"], ["row c-res2 (%s#mechanism:2)" % BASE, "accepted_by rv-noline"])(
    lambda fx: rows_with(fx) + [fx.row("c-res2", "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by="rv-noline",
                                       part="the documentation half")])

# ---------------------------------------------------------------- AC 3: residual acceptance, receipts, check-mode context


def residual(fx, acc, rid="c-res"):
    return rows_with(fx, **{"mechanism:2": fx.row(rid, "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by=acc)})


case("ac03-residual-accepted-by-an-independent-review", 0, [], unconsumed=[])(lambda fx: residual(fx, "rv-ok"))
case("ac03-residual-accepted-by-the-author-lineage", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by %s: no review launch row under A1 outside the author lineage" % AUTHOR],
     unconsumed=[BASE + "#mechanism:2"])(lambda fx: residual(fx, AUTHOR))
case("ac03-residual-accepted-by-a-role-less-session", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by rv-norole: no review launch row"], unconsumed=[BASE + "#mechanism:2"])(lambda fx: residual(fx, "rv-norole"))
case("ac03-residual-review-of-another-task", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by rv-other: no review launch row under A1"], unconsumed=[BASE + "#mechanism:2"])(lambda fx: residual(fx, "rv-other"))
case("ac03-residual-without-an-accepts-line", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by rv-noline: no verdict file", "holds `accepts c-res`"], unconsumed=[BASE + "#mechanism:2"])(
    lambda fx: residual(fx, "rv-noline"))
case("ac03-residual-with-a-placeholder-ref", 1, ["consumption-binding-invalid"], ["row c-res (%s#mechanism:2)" % BASE, "key evidence"])(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-res", "mechanism:2", "residual", owner="hermes", evidence=["ledger:tbd"], accepted_by="rv-ok")}))
case("ac03-receipt-only-session", 1, ["consumption-receipt-only"], ["row 'c-rcpt'", "its only target is a receipt (session)"])(
    lambda fx: rows_with(fx) + [{"id": "c-rcpt", "binding": "test", "session": "s-1"}])
case("ac03-receipt-only-run-id", 1, ["consumption-receipt-only"], ["row 'c-rcpt'", "its only target is a receipt (run_id)"])(
    lambda fx: rows_with(fx) + [{"id": "c-rcpt", "binding": "requirement", "run_id": "run-1"}])
case("ac03-receipt-only-report", 1, ["consumption-receipt-only"], ["row 'c-rcpt'", "binding 'report' is none of"])(
    lambda fx: rows_with(fx) + [{"id": "c-rcpt", "binding": "report", "report": "notes/report.md"}])
case("ac03-check-mode-without-reviews", 1, ["consumption-context-missing"], ["row c-res (%s#mechanism:2)" % BASE, "a residual row needs --reviews"],
     drop=("--reviews",))(lambda fx: residual(fx, "rv-ok"))
case("ac03-check-mode-without-prd-home", 1, ["consumption-context-missing"], ["row c-fal (%s#falsifier)" % BASE, "a requirement row needs --prd-home"],
     drop=("--prd-home",))(lambda fx: rows_with(fx))


# ---------------------------------------------------------------- Hermes H5 reading 6 in --require-closed (chain review 11 R11-F2; CR7 3:23 PM)
# The close gate's predicate: a repair is satisfied when its ask is closed or currently intake-accepted, never when intake-cancelled; its proof is an
# accept FAIL followed by a run-mode PASS at one sha, read from the ask's own events whichever kind of row it is.
X, Y = "a" * 64, "b" * 64


def ev(op, **d):
    return {"op": op, "detail": d, "actor": "t", "ts": "2026-11-19T15:00:00-08:00"}


PROOF = [ev("accept", result="FAIL", sha=X, mode="run", exit=1), ev("accept", result="PASS", sha=X, mode="run", exit=0)]
INTAKE_ADD = ev("add", owner="ctl", due="2026-12-31T09:00", state="ready")
PLAIN_ADD = ev("add", owner="ctl", due="2026-12-31T09:00")


def scen(status, events):
    rows = [{"ask_id": "A101", "owner": "ctl", "what": "repair %s#mechanism:2 (the canonical repair)" % BASE, "status": status, "check": "true"},
            {"ask_id": "A102", "owner": "hermes", "what": "successor S closes-after=row:A101", "status": "open", "check": "true"}]
    return {"rows": rows, "events": {"A101": events}}


H5_STATES = {   # name -> (scenario, close gate row {section, state} for the no-drift comparison)
    "closed": (scen("closed", [PLAIN_ADD] + PROOF + [ev("resolve", verdict_row="V1")]), {"section": "closed", "state": None}),
    "intake-accepted-open": (scen("open", [INTAKE_ADD, ev("claim", worker="w"), ev("transition", to="running"), ev("transition", to="verifying")] + PROOF
                                  + [ev("accepted", evidence="readback")]), {"section": "open", "state": "accepted"}),
    "intake-cancelled": (scen("closed", [INTAKE_ADD] + PROOF + [ev("cancel", event_id="tg:x")]), {"section": "closed", "state": "cancelled"}),
    "open": (scen("open", [INTAKE_ADD] + PROOF), {"section": "open", "state": "ready"}),
}


def h5_rows(fx):
    return rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask="A101", owner="ctl", successor="A102")})


case("h5p-closed-repair-with-its-proof", 0, [], unconsumed=[], scenario=H5_STATES["closed"][0])(h5_rows)
case("h5p-intake-accepted-open-repair-with-its-proof", 0, [], unconsumed=[], scenario=H5_STATES["intake-accepted-open"][0])(h5_rows)
case("h5p-intake-cancelled-repair-never-satisfies", 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, "intake-cancelled"],
     unconsumed=[BASE + "#mechanism:2"], scenario=H5_STATES["intake-cancelled"][0])(h5_rows)
case("h5p-open-repair-waits", 1, ["consumption-repair-open"], ["row c-rep (%s#mechanism:2)" % BASE, "neither closed nor intake-accepted"],
     unconsumed=[BASE + "#mechanism:2"], scenario=H5_STATES["open"][0])(h5_rows)
case("h5p-different-check-pass-is-no-proof", 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, "no accept FAIL followed by a run PASS"],
     unconsumed=[BASE + "#mechanism:2"], scenario=scen("closed", [PLAIN_ADD, ev("accept", result="FAIL", sha=X, mode="run"),
                                                                  ev("accept", result="PASS", sha=Y, mode="run")]))(h5_rows)
case("h5p-attested-pass-is-no-proof", 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE],
     unconsumed=[BASE + "#mechanism:2"], scenario=scen("closed", [PLAIN_ADD, ev("accept", result="FAIL", sha=X, mode="run"),
                                                                  ev("accept", result="PASS", sha=X, mode="attested")]))(h5_rows)
case("h5p-an-unrelated-asks-pass-is-no-proof", 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE],
     unconsumed=[BASE + "#mechanism:2"], scenario=dict(scen("closed", [PLAIN_ADD, ev("accept", result="FAIL", sha=X, mode="run")]),
                                                       events={"A101": [PLAIN_ADD, ev("accept", result="FAIL", sha=X, mode="run")], "A103": PROOF}))(h5_rows)


def nodrift(lint, T, sd):
    """Chain review 11 R11-F2: the lint's reading of a repair's state equals the close gate's own `_satisfied` (imported from the swarm-decide tree sd)
    on closed, intake-accepted-but-open, intake-cancelled and open rows, each carrying a valid proof."""
    sys.path.insert(0, sd)
    from wm_decide import asks as close_gate          # noqa: E402  (the predicate's one owner)
    fx = Fx(T)
    bad = 0
    for name, (sc, row) in H5_STATES.items():
        want = bool(close_gate._satisfied(row))
        rc, d, err = fx.lint(lint, h5_rows(fx), task="A102", require_closed=True, shim=fx.fake_canonical(sc))
        got = rc == 0
        print("%s no-drift %s: close gate _satisfied=%s, lint consumed=%s (rc %s)" % ("PASS" if got == want else "FAIL", name, want, got, rc))
        bad += got != want
    return 1 if bad else 0


def run(prefix, lint, T):
    fx = Fx(T)
    if not prefix.startswith("h5p"):
        fx.canonical()
    bad = 0
    names = [n for n in CASES if n.startswith(prefix)]
    if not names:
        print("FAIL dfcnfx: no case starts with %s" % prefix)
        return 1
    for n in names:
        c = CASES[n]
        if c["scenario"] is not None:
            rc, d, err = fx.lint(lint, c["fn"](fx), drop=c["drop"], task="A102", require_closed=True, shim=fx.fake_canonical(c["scenario"]))
        else:
            rc, d, err = fx.lint(lint, c["fn"](fx), drop=c["drop"])
        fails = [l for l in err.splitlines() if l.startswith("FAIL ")]
        probs = []
        if rc != c["rc"]:
            probs.append("rc=%s want %s" % (rc, c["rc"]))
        if sorted(set(d.get("findings") or [])) != c["findings"]:
            probs.append("findings=%s want %s" % (sorted(set(d.get("findings") or [])), c["findings"]))
        for nd in c["needles"]:
            if not any(nd in l for l in fails):
                probs.append("no FAIL line carries %r" % nd)
        if c["unconsumed"] is not None and d.get("unconsumed") != c["unconsumed"]:
            probs.append("unconsumed=%s want %s" % (d.get("unconsumed"), c["unconsumed"]))
        if "Traceback" in err:
            probs.append("traceback")
        if probs:
            bad += 1
            print("FAIL %s: %s; stderr=%s" % (n, "; ".join(probs), " | ".join(err.strip().splitlines()[:6])))
        else:
            print("PASS %s" % n)
    print("# %s: %d cases, %d pass, %d fail" % (prefix, len(names), len(names) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--run":
        sys.exit(run(sys.argv[2], sys.argv[3], sys.argv[4]))
    if len(sys.argv) == 5 and sys.argv[1] == "--nodrift":
        sys.exit(nodrift(sys.argv[2], sys.argv[3], sys.argv[4]))
    print(__doc__.strip().splitlines()[-1], file=sys.stderr)
    sys.exit(2)
