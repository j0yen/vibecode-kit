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
       dfcnfx.py --nodrift <lint> <scratch dir> <swarm-decide tree>   (the lint against the close gate's own store, writers and _satisfied)
       dfcnfx.py --ac05 <lint> <scratch dir> <swarm-decide tree>      (AC 5: R3's command on a temp store driven by the close gate's own code)
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

PAGE = "notes/analysis/fx-wwhtbt.md"
P1724 = "2026-11-18-mission-analysis-consistency-wwhtbt.md"
PAGE2 = "notes/analysis/fx2-wwhtbt.md"
PAGE3 = "notes/analysis/fx3-wwhtbt.md"           # review r14b L-b: its Falsifier paragraph runs `timeout 60 python3 -I scripts/kill-fx3.py`
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
    def __init__(self, T, lint):
        self.T = T
        self.lint_path = lint
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
        page2 = ("# Weakest link\n\nNo command here.\n\n# Mechanisms\n\n1. First — ⚙ a — owner A1723 author — state SPEC (A1723)\n\n"
                 "```\n# a shell comment inside a fenced block\n```\n\n2. Second — ⚙ b — owner ctl — state SPEC (A1300)\n")   # review r14 L1
        write(os.path.join(self.home, PAGE2), page2)
        self.page2_sha = sha(page2)
        page3 = ("# Weakest link\n\nThe kill script is a Python file.\n\n**Falsifier.** `timeout 60 python3 -I scripts/kill-fx3.py` prints KILL-FX3 when "
                 "a finding has no row.\n\n# Mechanisms\n\n1. Only one — ⚙ a — owner A1723 author — state SPEC (A1723)\n")      # review r14b L-b
        write(os.path.join(self.home, PAGE3), page3)
        self.page3_sha = sha(page3)
        self.kill3 = "print('KILL-FX3')\n"
        write(os.path.join(self.home, "scripts", "kill-fx3.py"), self.kill3)
        write(os.path.join(self.home, "build-queue", "PRD-fx-c.md"),
              "# PRD-fx-c\n\n## Acceptance criteria\n\n1. P0 — Given fx3-wwhtbt.md#falsifier, When `python3 -I scripts/kill-fx3.py` runs on a record "
              "missing a row, Then it prints `KILL-FX3`.\n")
        write(os.path.join(T, "decoy", "dream-run-note-lint.sh"), "#!/bin/sh\n# a decoy with the lint's name\nexit 0\n", 0o755)    # review r14b F1
        os.makedirs(os.path.join(T, "copy"), exist_ok=True)
        shutil.copyfile(lint, os.path.join(T, "copy", "dream-run-note-lint.sh"))
        os.chmod(os.path.join(T, "copy", "dream-run-note-lint.sh"), 0o755)
        os.makedirs(os.path.join(self.fakehome, "~+"), exist_ok=True)     # review r14c M1 (c): a same-bytes copy where `~+` reads literally, and the decoy
        shutil.copyfile(lint, os.path.join(self.fakehome, "~+", "dream-run-note-lint.sh"))   # bash would run instead (`~+` = $PWD = HOME under _run_check)
        write(os.path.join(self.fakehome, "dream-run-note-lint.sh"), "#!/bin/sh\nexit 0\n", 0o755)
        for d in (os.path.join(self.fakehome, "FOO=x"), os.path.join(T, "eq=dir")):     # review r14d LOW 1: same-bytes copies under `=` directories
            os.makedirs(d, exist_ok=True)
            shutil.copyfile(lint, os.path.join(d, "dream-run-note-lint.sh"))
            os.chmod(os.path.join(d, "dream-run-note-lint.sh"), 0o755)
        write(os.path.join(self.home, "build-queue", "PRD-fx-a.md"),
              "# PRD-fx-a\n\n## Acceptance criteria\n\n"
              "1. P0 — Given %s#falsifier, When `bash scripts/kill-fx.sh` runs on a record missing a row, Then it prints `KILL-FX` "
              "(re-expressed by `bash scripts/rx-fx.sh`).\n"
              "2. P0 — Given %s#mechanism:1, When `tests/fx_ac02.sh` runs its negative control, Then a record without the row exits 1.\n"
              "3. P0 — Given %s#mechanism:1, When a reader looks, Then the row is described in prose only.\n"
              "4. P0 — Given %s#falsifier, When `bash scripts/other-kill.sh` runs, Then it prints OTHER.\n"
              "5. P0 — Given `%s#mechanism:1`, When a reader looks, Then nothing runs.\n"
              "6. P0 — Given %s#falsifier, When `bash scripts/kill-fx.sh` runs on a record missing a row, Then it prints `KILL-FX` "
              "(re-expressed by `bash ../outside-rx.sh`).\n" % (BASE, BASE, BASE, BASE, BASE, BASE))     # AC 6: review r14b L-c
        write(os.path.join(T, "outside-rx.sh"), "#!/bin/sh\necho KILL-FX\n", 0o755)
        os.makedirs(os.path.join(self.repo, "tests"))
        write(os.path.join(self.repo, "tests", "bind.sh"), "# exercises %s#falsifier,mechanism:1,mechanism:2\n" % BASE)
        write(os.path.join(self.repo, "tests", "plain.sh"), "# names no finding\n")
        write(os.path.join(self.repo, "tests", "bind2.sh"), "# exercises fx2-wwhtbt.md#falsifier,mechanism:1,mechanism:2\n")
        write(os.path.join(self.repo, "tests", "bind3.sh"), "# exercises fx3-wwhtbt.md#mechanism:1\n")
        write(os.path.join(self.repo, "t2", "%s#mechanism:2.sh" % BASE), "# a file name that names the finding, inside a tree\n")
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", HOME=self.fakehome)
        for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
            subprocess.run(["git", "-C", self.repo] + c, check=True, env=env, capture_output=True)
        self.commit = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"], capture_output=True, text=True, check=True, env=env).stdout.strip()
        rows = [("rv-ok", TASK, "review"), (AUTHOR, TASK, "author"), (AUTHOR, TASK, "review"), ("rv-norole", TASK, None), ("rv-noline", TASK, "review"),
                ("rv-other", "A9", "review"), ("a-2", TASK, "review"), ("a-2", TASK, "author"), ("rv-x", TASK, "review", "other-skill"),
                ("rv-cited", TASK, "review"), ("rv-citer", TASK, None), ("a-res", TASK, "author"), ("rv-late", TASK, "review"), ("a-res", TASK, "author"),
                ("rv-multi", "A9", "review"), ("a-late", TASK, "author"), ("rv-multi", TASK, "review")]
        with open(self.dec, "w") as f:
            for i, (s, t, role, *sk) in enumerate(rows):
                r = {"ts": "2026-11-19T10:%02d:00-08:00" % i, "decision": "launch", "task_id": t, "skill": sk[0] if sk else "dream", "route": "opus-xhigh",
                     "model": "claude-opus-5-5", "effort": "xhigh", "session": s}
                if role:
                    r["role"] = role
                f.write(json.dumps(r) + "\n")
        for name, text in (("verdict-ok.md", "Review session rv-ok\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-author.md", "Review session %s\naccepts c-res\n## VERDICT: APPROVE\n" % AUTHOR),
                           ("verdict-norole.md", "Review session rv-norole\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-noline.md", "Review session rv-noline\nthe residual is fine, accepts c-res in spirit\n## VERDICT: APPROVE\n"),
                           ("verdict-other.md", "Review session rv-other\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-a2.md", "Review session a-2\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-rvx.md", "Review session rv-x\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-cited.md", "Review session rv-cited\nno acceptance here\n## VERDICT: APPROVE\n"),
                           ("verdict-citer.md", "Review session rv-citer, re-reviewing rv-cited's verdict\naccepts c-res\n## VERDICT: APPROVE\n"),
                           ("verdict-late.md", "Review session rv-late\nThe author is session a-res\naccepts c-late\n## VERDICT: APPROVE\n"),
                           ("verdict-multi.md", "Review session rv-multi\nThe author is session a-late\naccepts c-multi\n## VERDICT: APPROVE\n")):
            write(os.path.join(self.reviews, name), text)
        with open(self.policy, "w") as f:
            json.dump({"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$",
                                    "placeholders": ["none", "n/a", "na", "tbd", "todo", "unknown", "x", "xx"], "min_refs": 1}}, f)
        self.ids = {}

    def home1724(self):
        """Review r14 M5: a home holding the A1724 WWHTBT page copy (no frontmatter falsifier; its weakest-link section cites a fixture generator in
        backticks), the cited generator, and a PRD whose AC 1 runs that generator; the page's eight mechanisms bind by test rows."""
        h = os.path.join(self.T, "home1724")
        if os.path.isdir(h):
            return h
        src = os.path.join(os.path.dirname(os.path.abspath(__file__)), "2026-11-18-mission-analysis-consistency-wwhtbt.md")
        text = open(src, encoding="utf-8").read()
        write(os.path.join(h, "notes", "analysis", P1724), text)
        self.p1724_sha = sha(text)
        gen = "design/gen8-repair/out/work/tools/gen_controls_gen8.rdy.py"
        write(os.path.join(h, gen), "print('KILLX')\n")
        self.gen = (gen, sha(open(os.path.join(h, gen)).read()))
        write(os.path.join(h, "build-queue", "PRD-fx-b.md"), "# PRD-fx-b\n\n## Acceptance criteria\n\n1. P0 — Given %s#falsifier, When `python3 %s` runs, "
              "Then it prints `KILLX`.\n" % (P1724, gen))
        r2 = os.path.join(self.T, "repo1724")
        write(os.path.join(r2, "tests", "bind.sh"), "# exercises %s#%s\n" % (P1724, ",".join("mechanism:%d" % n for n in range(1, 9))))
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t", HOME=self.fakehome)
        for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
            subprocess.run(["git", "-C", r2] + c, check=True, env=env, capture_output=True)
        self.repo1724 = (r2, subprocess.run(["git", "-C", r2, "rev-parse", "HEAD"], capture_output=True, text=True, check=True, env=env).stdout.strip())
        return h

    # ---- the temp canonical store ----
    def canonical(self):
        wd = os.environ.get("DFCN_WM_DECIDE") or shutil.which("wm-decide")
        if not wd:
            raise SystemExit("FAIL dfcnfx: no wm-decide for the temp canonical store (set DFCN_WM_DECIDE to a wm-decide binary)")
        store_home = os.path.join(self.T, "store-home")
        os.makedirs(store_home, exist_ok=True)
        os.makedirs(self.shim_dir, exist_ok=True)
        write(os.path.join(self.shim_dir, "wm-asks"), "#!/bin/sh\nexec env WM_DECIDE_STATE='%s' HOME='%s' '%s' \"$@\"\n" % (self.state, store_home, wd), 0o755)
        rec = os.path.join(self.home, "record.jsonl")
        lintcheck = "bash %s --consumption %s --task {me} --require-closed" % (self.lint_path, rec)
        for key, me, owner, what, chk in (("repair", "A1", "ctl", "repair %s#mechanism:2 (the canonical repair)" % BASE, "true"),
                                          ("succ", "A2", "hermes", "successor S closes-after=row:A1", lintcheck),
                                          ("loose", "A3", "hermes", "a successor without the closes-after text", lintcheck),
                                          ("nolint", "A4", "hermes", "successor closes-after=row:A1 whose check lacks the lint", "true"),
                                          ("prefix", "A5", "hermes", "successor closes-after=row:A13 (another row)", lintcheck)):
            p = subprocess.run([os.path.join(self.shim_dir, "wm-asks"), "asks", "add", "--by", "t-author", "--owner", owner, "--due", "2026-12-31T09:00",
                                "--what", what, "--check", chk.format(me=me)], capture_output=True, text=True)
            got = p.stdout.strip().split()[-1] if p.returncode == 0 and p.stdout.strip() else None
            if got != me:
                raise SystemExit("FAIL dfcnfx: seeding the temp canonical store gave %r for %s, want %s: %s%s" % (got, key, me, p.stdout, p.stderr))
            self.ids[key] = me
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
            f.write(json.dumps(scenario).replace("{RECORD}", os.path.join(self.home, "record.jsonl")).replace("{LINT}", self.lint_path).replace("{T}", self.T))
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

    def lint(self, lint, rows, drop=(), wm_asks=True, task=TASK, require_closed=False, shim=None, home=None, page=PAGE, nopage=False):
        home = home or self.home
        rec = os.path.join(home, "record.jsonl")               # at the home's root: without --prd-home, row paths resolve against the record's directory
        with open(rec, "w") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        path = os.environ.get("PATH", "/usr/bin:/bin")
        if wm_asks:
            path = (shim or self.shim_dir) + os.pathsep + path
        else:
            path = os.pathsep.join(d for d in path.split(os.pathsep) if not os.path.exists(os.path.join(d, "wm-asks")))
        args = ["bash", lint, "--consumption", rec, "--task", task, "--json"] + ([] if nopage else ["--page", page]) + (["--require-closed"] if require_closed else [])
        for flag, val in (("--prd-home", home), ("--reviews", self.reviews), ("--decisions", self.dec)):
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


def case(name, rc, findings, needles=(), drop=(), unconsumed=None, scenario=None, plain=False, task=None, require_closed=None, home=None, nopage=False,
         pending=None, page=None, repairs=None):
    """scenario: the canonical rows come from that scenario (a fake wm-asks), linted for successor A102 with --require-closed unless `plain`.
    home: "1724" lints the A1724 page copy's home. pending: the JSON `pending` list the case expects."""
    def deco(fn):
        CASES[name] = {"fn": fn, "rc": rc, "findings": sorted(findings), "needles": list(needles), "drop": drop, "unconsumed": unconsumed,
                       "scenario": scenario, "plain": plain, "task": task, "require_closed": require_closed, "home": home, "nopage": nopage,
                       "pending": pending, "page": page, "repairs": repairs}
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
case("ac02-valid-pending", 0, [], unconsumed=[], pending=[BASE + "#mechanism:2"])(lambda fx: rows_with(fx, **{"mechanism:2": fx.row(
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
case("ac02-test-path-not-at-the-commit", 1, ["consumption-binding-invalid"], ["row c-m2 (%s#mechanism:2)" % BASE, "key path: tests/absent.sh is not a file in"])(
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

# ---------------------------------------------------------------- review r14 (finding consumption stages 1-2): each fails at 6735eef
case("ac02-r14m1-successor-check-lacks-the-lint", 1, ["consumption-repair-unproven"],
     ["row c-rep (%s#mechanism:2)" % BASE, "successor A4's done-check (or a closes-after row's) does not run dream-run-note-lint.sh"])(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask="A1", owner="ctl", successor="A4")}))
case("ac02-r14m1-closed-repair-without-proof-in-plain-mode", 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, "shows no accept FAIL"],
     plain=True, scenario={"rows": [{"ask_id": "A101", "owner": "ctl", "what": "repair %s#mechanism:2" % BASE, "status": "closed", "check": "true"},
                                    {"ask_id": "A102", "owner": "hermes", "what": "successor S closes-after=row:A101", "status": "open",
                                     "check": "bash {LINT} --consumption {RECORD} --task A102 --require-closed"}],
                           "events": {"A101": [{"op": "accept", "detail": {"result": "PASS", "sha": "a" * 64, "mode": "attested"}}]}})(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask="A101", owner="ctl", successor="A102")}))
case("ac02-r14m2-closes-after-prefix-is-not-the-ask", 1, ["consumption-repair-unbound"], ["row c-rep (%s#mechanism:2)" % BASE, "closes-after=row:A1)"])(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask="A1", owner="ctl", successor="A5")}))
case("ac02-r14m5-a1724-page-names-no-falsifier-command", 1, ["consumption-binding-not-discriminating"], ["row c-fal (%s#falsifier)" % P1724,
     "the page names no falsifier script"], home="1724")(
    lambda fx: [{"id": "c-fal", "page": "notes/analysis/" + P1724, "page_sha256": fx.p1724_sha, "finding": "falsifier", "binding": "requirement",
                 "author_session": AUTHOR, "prd": "PRD-fx-b.md", "ac": 1, "kill": {"script": fx.gen[0], "sha256": fx.gen[1], "string": "KILLX"}}]
    + [{"id": "c-m%d" % n, "page": "notes/analysis/" + P1724, "page_sha256": fx.p1724_sha, "finding": "mechanism:%d" % n, "binding": "test",
        "author_session": AUTHOR, "repo": fx.repo1724[0], "commit": fx.repo1724[1], "path": "tests/bind.sh"} for n in range(1, 9)])
case("ac02-r14l1-a-fenced-comment-does-not-end-the-mechanisms", 1, ["consumption-finding-unbound"], ["fx2-wwhtbt.md#mechanism:2: no binding row"],
     unconsumed=["fx2-wwhtbt.md#mechanism:2"], page=PAGE2)(
    lambda fx: [{"id": "c2-%s" % f.replace(":", "-"), "page": PAGE2, "page_sha256": fx.page2_sha, "finding": f, "binding": "test", "author_session": AUTHOR,
                 "repo": fx.repo, "commit": fx.commit, "path": "tests/bind2.sh"} for f in ("falsifier", "mechanism:1")])
case("ac02-r14l2-ac-whose-only-backticks-name-the-finding", 1, ["consumption-binding-invalid"], ["row c-m1 (%s#mechanism:1)" % BASE, "carries no backticked command"])(
    lambda fx: rows_with(fx, **{"mechanism:1": dict(fx.base()["mechanism:1"], ac=5)}))
case("ac02-r14l3-a-tree-is-no-test-file", 1, ["consumption-binding-invalid"], ["row c-m2 (%s#mechanism:2)" % BASE, "key path: t2 is not a file"])(
    lambda fx: rows_with(fx, **{"mechanism:2": dict(fx.base()["mechanism:2"], path="t2")}))
case("ac02-r14l4-reexpression-outside-the-home", 1, ["consumption-binding-invalid"], ["row c-fal (%s#falsifier)" % BASE, "not under the PRD home"])(
    lambda fx: rows_with(fx, falsifier=dict(fx.base()["falsifier"], ac=6, reexpression={"script": "../outside-rx.sh",
                                                                                  "sha256": sha(open(os.path.join(fx.T, "outside-rx.sh")).read())})))
case("ac02-r14l5-an-empty-record-without-page", 1, ["consumption-grammar"], ["has no row and no --page"], nopage=True)(lambda fx: [])
case("ac02-r14l5-require-closed-with-no-row-for-the-task", 1, ["consumption-repair-unbound"], ["no repair or pending row", "names successor A999"],
     task="A999", require_closed=True)(lambda fx: rows_with(fx))


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
case("ac03-r14m3-review-launch-followed-by-an-author-launch", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by a-2: no review launch row under A1 outside the author lineage"], unconsumed=[BASE + "#mechanism:2"])(
    lambda fx: residual(fx, "a-2"))
case("ac03-r14m3-review-launch-of-another-skill", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by rv-x: no review launch row"], unconsumed=[BASE + "#mechanism:2"])(lambda fx: residual(fx, "rv-x"))
case("ac03-r14m4-a-later-file-citing-the-session-is-not-its-own", 1, ["consumption-residual-unaccepted"],
     ["row c-res (%s#mechanism:2)" % BASE, "accepted_by rv-cited: no verdict file"], unconsumed=[BASE + "#mechanism:2"])(lambda fx: residual(fx, "rv-cited"))
case("ac03-r14bla-a-resumed-author-does-not-take-a-later-reviews-file", 0, [], unconsumed=[])(lambda fx: residual(fx, "rv-late", rid="c-late"))
case("ac03-r14cl1-a-review-launched-earlier-under-another-task-keeps-its-file", 0, [], unconsumed=[])(lambda fx: residual(fx, "rv-multi", rid="c-multi"))
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
            {"ask_id": "A102", "owner": "hermes", "what": "successor S closes-after=row:A101", "status": "open",
             "check": "bash {LINT} --consumption {RECORD} --task A102 --require-closed"}]
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


def scen_check(check):
    """The closed, proved repair A101 of the H5 cases, with successor A102's done-check replaced (review r14b F1)."""
    sc = scen("closed", [PLAIN_ADD] + PROOF + [ev("resolve", verdict_row="V1")])
    sc["rows"][1]["check"] = check
    return sc


LC = "bash {LINT} --consumption {RECORD} --task A102 --require-closed"
F1_REFUSED = (   # review r14b F1: each check could exit 0 without the lint gating it on this record for this successor
    ("or-true-never-gates", LC + " || true", "not one plain command"),
    ("true-or-the-lint", "true || " + LC, "not one plain command"),
    ("an-echo-of-the-lint", "echo " + LC, "its command is not a path to dream-run-note-lint.sh"),
    ("a-comment-after-true", "true # " + LC, "not one plain command"),
    ("a-sequence", "bash {LINT} --task A1; true --consumption {RECORD} --task A102 --require-closed", "not one plain command"),
    ("a-variable", "bash $HOME/../copy/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed", "not one plain command"),
    ("a-relative-decoy-record", "bash {LINT} --consumption home/record.jsonl --task A102 --require-closed", "its --consumption is not"),
    ("page-takes-require-closed", "bash {LINT} --consumption {RECORD} --task A102 --page --require-closed", "it lacks --require-closed"),
    ("a-later-task-overrides", "bash {LINT} --consumption {RECORD} --task A102 --task A1 --require-closed", "its --task is A1, not A102"),
    ("a-later-record-overrides", "bash {LINT} --consumption {RECORD} --consumption {T}/decoy.jsonl --task A102 --require-closed",
     "its --consumption is not"),
    ("a-missing-lint", "bash {T}/nowhere/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed", "is not this lint"),
    ("a-decoy-with-the-lints-name", "bash {T}/decoy/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed", "is not this lint"),
    ("a-bare-name", "dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed", "its command is not a path"),
    ("another-mode", "bash {LINT} --selftest --consumption {RECORD} --task A102 --require-closed", "another mode"),
)
for _n, _chk, _why in F1_REFUSED:
    case("ac02-r14bf1-" + _n, 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, _why], unconsumed=[BASE + "#mechanism:2"],
         scenario=scen_check(_chk), plain=True)(h5_rows)
F1_BOUND = (     # the over-strict side: legitimate forms of the check still bind
    ("timeout-and-a-home-relative-record", "timeout -k 5 60 bash {LINT} --consumption ../home/record.jsonl --task A102 --require-closed --json"),
    ("direct-exec-and-a-tilde-record", "{LINT} --json --consumption ~/../home/record.jsonl --task A102 --require-closed"),
    ("a-copy-with-the-same-bytes", "bash {T}/copy/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed"),
)
for _n, _chk in F1_BOUND:
    case("ac02-r14bf1-ok-" + _n, 0, [], unconsumed=[], scenario=scen_check(_chk), plain=True)(h5_rows)

M1C_REFUSED = (  # review r14c M1: words bash splits differently, a timeout option that runs nothing, a tilde form bash expands elsewhere
    ("nbsp-before-require-closed", "bash {LINT} --consumption {RECORD} --task A102\u00a0--require-closed", "not one plain command"),
    ("vertical-tab-before-require-closed", "bash {LINT} --consumption {RECORD} --task A102\u000b--require-closed", "not one plain command"),
    ("ideographic-space-before-require-closed", "bash {LINT} --consumption {RECORD} --task A102\u3000--require-closed", "not one plain command"),
    ("a-tab-between-words", "bash {LINT} --consumption {RECORD}\t--task A102 --require-closed", "not one plain command"),
    ("timeout-help", "timeout --help 60 " + LC, "its timeout option --help is not"),
    ("timeout-version", "timeout --version 60 " + LC, "its timeout option --version is not"),
    ("timeout-k-without-a-duration", "timeout -k --help 60 " + LC, "its timeout option -k is not"),
    ("tilde-plus", "bash ~+/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed", "a `~` form other than `~/`"),
)
for _n, _chk, _why in M1C_REFUSED:
    case("ac02-r14cm1-" + _n, 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, _why], unconsumed=[BASE + "#mechanism:2"],
         scenario=scen_check(_chk), plain=True)(h5_rows)
case("ac02-r14cm1-a-pending-row-whose-ask-is-closed-with-an-nbsp-check", 1, ["consumption-repair-unproven"],
     ["row c-pen (%s#mechanism:2)" % BASE, "not one plain command"], unconsumed=[BASE + "#mechanism:2"],
     scenario=scen_check("bash {LINT} --consumption {RECORD} --task A102\u00a0--require-closed"), plain=True)(
    lambda fx: rows_with(fx, **{"mechanism:2": fx.row("c-pen", "mechanism:2", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask="A101",
                                                      successor="A102")}))
for _n, _chk in (("timeout-long-options", "timeout --kill-after=5 --signal=TERM --foreground --preserve-status 60 " + LC),
                 ("timeout-short-options", "timeout -k 5 -s KILL -v 60 " + LC),
                 ("two-spaces-between-words", "bash  {LINT} --consumption {RECORD}  --task A102 --require-closed")):
    case("ac02-r14cm1-ok-" + _n, 0, [], unconsumed=[], scenario=scen_check(_chk), plain=True)(h5_rows)
R14D_REFUSED = (  # review r14d: a first word bash reads as an assignment (LOW 1), and the lint run under sh (LOW 2: dash cannot run its bootstrap)
    ("an-assignment-as-the-command-word", "FOO=x/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed",
     "its first word FOO=x/dream-run-note-lint.sh is a shell assignment"),
    ("an-append-assignment-as-the-command-word", "FOO+=x/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed",
     "is a shell assignment"),
    ("sh", "sh {LINT} --consumption {RECORD} --task A102 --require-closed", "it runs the lint under sh"),
    ("bin-sh", "/bin/sh {LINT} --consumption {RECORD} --task A102 --require-closed", "it runs the lint under /bin/sh"),
    ("usr-bin-sh", "/usr/bin/sh {LINT} --consumption {RECORD} --task A102 --require-closed", "it runs the lint under /usr/bin/sh"),
    ("timeout-then-sh", "timeout 60 sh {LINT} --consumption {RECORD} --task A102 --require-closed", "it runs the lint under sh"),
)
for _n, _chk, _why in R14D_REFUSED:
    case("ac02-r14d-" + _n, 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, _why], unconsumed=[BASE + "#mechanism:2"],
         scenario=scen_check(_chk), plain=True)(h5_rows)
for _n, _chk in (("bin-bash", "/bin/bash {LINT} --consumption {RECORD} --task A102 --require-closed"),
                 ("usr-bin-bash", "/usr/bin/bash {LINT} --consumption {RECORD} --task A102 --require-closed"),
                 ("an-equals-sign-inside-an-absolute-path", "{T}/eq=dir/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed"),
                 ("an-equals-sign-after-bash", "bash ~/FOO=x/dream-run-note-lint.sh --consumption {RECORD} --task A102 --require-closed")):
    case("ac02-r14d-ok-" + _n, 0, [], unconsumed=[], scenario=scen_check(_chk), plain=True)(h5_rows)
case("ac02-r14cl2-the-refusal-names-each-checked-row-and-repairs-lists-it", 1, ["consumption-repair-unproven"],
     ["successor A102: its command is not a path to dream-run-note-lint.sh", "closes-after row A101: its command is not a path to dream-run-note-lint.sh"],
     unconsumed=[BASE + "#mechanism:2"], scenario=scen_check("true"), plain=True, repairs=["A101"])(h5_rows)

CANCEL_CLAIM = [INTAKE_ADD] + PROOF + [ev("transition", **{"from": "ready", "to": "cancelled"}), ev("claim", worker="w2", claim="w2@2026-11-19T15:01")]
case("h5p-r14bf2-cancelled-then-a-plain-claim-never-satisfies", 1, ["consumption-repair-unproven"], ["row c-rep (%s#mechanism:2)" % BASE, "intake-cancelled"],
     unconsumed=[BASE + "#mechanism:2"], scenario=scen("open", CANCEL_CLAIM))(h5_rows)
case("h5p-r14bf2-cancelled-then-a-plain-claim-is-refused-in-plain-mode", 1, ["consumption-repair-unproven"],
     ["row c-rep (%s#mechanism:2)" % BASE, "intake-cancelled"], unconsumed=[BASE + "#mechanism:2"], scenario=scen("open", CANCEL_CLAIM), plain=True)(h5_rows)

case("ac02-r14blb-a-falsifier-run-by-python3-with-options", 0, [], unconsumed=[], page=PAGE3)(
    lambda fx: [{"id": "c3-fal", "page": PAGE3, "page_sha256": fx.page3_sha, "finding": "falsifier", "binding": "requirement", "author_session": AUTHOR,
                 "prd": "PRD-fx-c.md", "ac": 1, "kill": {"script": "scripts/kill-fx3.py", "sha256": sha(fx.kill3), "string": "KILL-FX3"}},
                {"id": "c3-m1", "page": PAGE3, "page_sha256": fx.page3_sha, "finding": "mechanism:1", "binding": "test", "author_session": AUTHOR,
                 "repo": fx.repo, "commit": fx.commit, "path": "tests/bind3.sh"}])


def nodrift(lint, T, sd):
    """Chain review 11 R11-F2's no-drift control, driven by the close gate's own store (review r14b F2). Each sequence creates a repair R and a successor
    S (`closes-after=row:R`, whose check runs this lint) and moves R with swarm-decide's own code from the tree sd: asks add/accept/claim/resolve, intake
    submit (new and cancel), claim_task, transition, begin_effect, release_task and the acceptance core, on a temp store. The lint then reads R through
    that tree's own CLI (`wm-asks` = `wm_decide.cli`). For each sequence: the lint's intake state equals R's `state` column ('legacy' = none), its
    predicate equals the close gate's `_satisfied(R)`, and its verdict under --require-closed for S is what the close gate implies: consumed when
    satisfied, `consumption-repair-unproven` when cancelled, `consumption-repair-open` otherwise. A plain-mode run refuses exactly the cancelled ones."""
    sys.path.insert(0, sd)
    state, shome = os.path.join(T, "sd-state"), os.path.join(T, "sd-home")
    os.makedirs(state)
    os.makedirs(shome)
    os.environ.update(WM_DECIDE_STATE=state, HOME=shome)
    from wm_decide import asks, intake, store                    # noqa: E402  (the predicate's one owner, and the store's own writers)
    db = store.connect()
    intake.ensure(db)
    shim = os.path.join(T, "sd-shim")
    write(os.path.join(shim, "wm-asks"), "#!/bin/sh\nexec env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='%s' WM_DECIDE_STATE='%s' HOME='%s' python3 -B -c "
          "'import sys; from wm_decide.cli import main; sys.exit(main(sys.argv[1:]))' \"$@\"\n" % (sd, state, shome), 0o755)
    fx = Fx(T, lint)
    rec = os.path.join(fx.home, "record.jsonl")
    DUE = "2026-12-31T09:00"
    n = [0]

    def rev(a):
        return db.execute("SELECT rev FROM asks WHERE ask_id = ?", (a,)).fetchone()[0]

    def new_repair(intake_row, depends=()):
        n[0] += 1
        chk = "test -f m%d" % n[0]
        what = "repair %s#mechanism:2 (the canonical repair %d)" % (BASE, n[0])
        if intake_row:
            res, _ = intake.submit(db, {"source_event_id": "tg:nd%d" % n[0], "text": what, "request_type": "new", "authorized_by": "hermes"},
                                   {"owner": "ctl", "due": DUE, "what": what, "check": chk, "depends": list(depends)}, trusted=("hermes",))
            return res["ask_id"], n[0]
        return asks.add(db, owner="ctl", due=DUE, what=what, check=chk, actor="t-author"), n[0]

    def successor(r):
        s = asks.next_id(db, "A")
        got = asks.add(db, owner="hermes", due=DUE, what="successor S closes-after=row:%s" % r,
                       check="bash %s --consumption %s --task %s --require-closed" % (lint, rec, s), actor="t-author")
        if got != s:
            raise SystemExit("FAIL no-drift: successor id %s, predicted %s" % (got, s))
        return s

    def prove(r, k):                                              # FAIL, then the file appears, then a run PASS at the same sha
        asks.accept(db, r, actor="t-closer")
        open(os.path.join(shome, "m%d" % k), "w").close()
        asks.accept(db, r, actor="t-closer")

    def verifying(r, pid=None):
        intake.claim_task(db, r, worker="w-nd", expect_rev=rev(r), actor="ctl", pid=pid)
        intake.transition(db, r, "running", expect_rev=rev(r), actor="ctl")
        intake.transition(db, r, "verifying", expect_rev=rev(r), actor="ctl")

    def dead_pid():
        p = subprocess.Popen(["true"])
        p.wait()
        return p.pid

    def cli(*a):
        return subprocess.run([os.path.join(shim, "wm-asks"), *a], capture_output=True, text=True)

    def seq_legacy_open():
        r, k = new_repair(False); s = successor(r); prove(r, k); return r, s

    def seq_legacy_closed():
        r, k = new_repair(False); s = successor(r); prove(r, k)
        rid = db.execute("SELECT row_id FROM asks WHERE ask_id = ?", (r,)).fetchone()[0]
        p = cli("record", "--agent", "r7", "--kind", "verdict", "--model", "deterministic", "--gates", rid, "--what", "decision=%s fixture check passed" % rid,
                "--why", "fixture", "--evidence", "decision=%s fixture check rc 0" % rid, "--reverse-text", "fixture only")
        vid = (p.stdout.strip().split() or [""])[-1]
        asks.resolve(db, r, expect_rev=rev(r), actor="t-closer", evidence="fixture close", verdict_row=vid)
        return r, s

    def seq_ready():
        r, k = new_repair(True); s = successor(r); prove(r, k); return r, s

    def seq_claimed():
        r, k = new_repair(True); s = successor(r); prove(r, k)
        intake.claim_task(db, r, worker="w-nd", expect_rev=rev(r), actor="ctl"); return r, s

    def seq_verifying():
        r, k = new_repair(True); s = successor(r); prove(r, k); verifying(r); return r, s

    def seq_blocked():
        r, k = new_repair(True); s = successor(r); prove(r, k)
        intake.claim_task(db, r, worker="w-nd", expect_rev=rev(r), actor="ctl")
        intake.transition(db, r, "blocked", expect_rev=rev(r), actor="ctl"); return r, s

    def seq_accepted():
        r, k = new_repair(True); s = successor(r); verifying(r); prove(r, k)
        intake._accept_core(db, r, expect_rev=rev(r), actor="r7", evidence="independent readback"); return r, s

    def seq_cancelled_by_transition():
        r, k = new_repair(True); s = successor(r); prove(r, k)
        intake.transition(db, r, "cancelled", expect_rev=rev(r), actor="hermes"); return r, s

    def seq_cancelled_then_plain_claim():
        r, s = seq_cancelled_by_transition()
        asks.claim(db, r, worker="w2", actor="someone"); return r, s

    def seq_cancelled_by_request():
        r, k = new_repair(True); prove(r, k)
        intake.submit(db, {"source_event_id": "tg:ndx%d" % k, "text": "cancel %s" % r, "request_type": "cancel", "authorized_by": "hermes",
                           "target_ask": r, "target_rev": rev(r)}, None, trusted=("hermes",))
        return r, successor(r)

    def seq_plain_claim_on_ready():
        r, s = seq_ready()
        asks.claim(db, r, worker="w3", actor="someone"); return r, s

    def seq_draft():
        d, _ = new_repair(True)
        r, k = new_repair(True, depends=(d,)); s = successor(r); prove(r, k); return r, s

    def seq_enabled():
        d, _ = new_repair(True)
        r, k = new_repair(True, depends=(d,)); s = successor(r); prove(r, k)
        verifying(d)
        intake._accept_core(db, d, expect_rev=rev(d), actor="r7", evidence="independent readback"); return r, s

    def seq_released():
        r, k = new_repair(True); s = successor(r); prove(r, k)
        intake.claim_task(db, r, worker="w-nd", expect_rev=rev(r), actor="ctl", pid=dead_pid())
        intake.release_task(db, r, expect_rev=rev(r), actor="sweeper", evidence="owner gone", stale_after=0); return r, s

    def seq_release_unknown():
        r, k = new_repair(True); s = successor(r); prove(r, k)
        intake.claim_task(db, r, worker="w-nd", expect_rev=rev(r), actor="ctl", pid=dead_pid())
        intake.begin_effect(db, r, idem_key="nd-fx-%d" % k, actor="w-nd")
        intake.release_task(db, r, expect_rev=rev(r), actor="sweeper", evidence="owner gone", stale_after=0); return r, s

    seqs = [seq_legacy_open, seq_legacy_closed, seq_ready, seq_claimed, seq_verifying, seq_blocked, seq_accepted, seq_cancelled_by_transition,
            seq_cancelled_then_plain_claim, seq_cancelled_by_request, seq_plain_claim_on_ready, seq_draft, seq_enabled, seq_released, seq_release_unknown]
    bad = 0
    for fn in seqs:
        name = fn.__name__[4:].replace("_", "-")
        try:
            r, s = fn()
        except Exception as e:                                    # a sequence the store refuses is a broken control, never a pass
            print("FAIL no-drift %s: the store refused the sequence: %s: %s" % (name, type(e).__name__, e))
            bad += 1
            continue
        row = asks._row(db, r)
        st = asks._state(row)
        want_state = None if st in (None, "legacy") else st
        want_sat = bool(asks._satisfied(row))
        rows = rows_with(fx, **{"mechanism:2": fx.row("c-rep", "mechanism:2", "repair", ask=r, owner="ctl", successor=s)})
        rc, d, err = fx.lint(lint, rows, task=s, require_closed=True, shim=shim)
        rep_ = [x for x in (d.get("repairs") or []) if x.get("ask") == r]
        got_state = rep_[0].get("intake_state") if rep_ else "(no repairs entry)"
        got_sat = rep_[0].get("satisfied") if rep_ else None
        want_rc, want_find = (0, []) if want_sat else (1, ["consumption-repair-unproven" if want_state == "cancelled" else "consumption-repair-open"])
        prc, pd, perr = fx.lint(lint, rows, task=TASK, require_closed=False, shim=shim)
        want_prc = 1 if want_state == "cancelled" else 0
        probs = []
        if got_state != want_state:
            probs.append("intake state %r, the store's %r" % (got_state, want_state))
        if got_sat is not want_sat:
            probs.append("predicate %r, the close gate's _satisfied %r" % (got_sat, want_sat))
        if rc != want_rc or sorted(set(d.get("findings") or [])) != want_find:
            probs.append("--require-closed rc %s findings %s, want rc %s findings %s" % (rc, d.get("findings"), want_rc, want_find))
        if prc != want_prc:
            probs.append("plain mode rc %s, want %s" % (prc, want_prc))
        if "Traceback" in err + perr:
            probs.append("traceback")
        print("%s no-drift %s: store state %s section %s _satisfied %s; lint state %s predicate %s, rc %s/%s%s"
              % ("FAIL" if probs else "PASS", name, st, row["section"], want_sat, got_state, got_sat, rc, prc, ("; " + "; ".join(probs)) if probs else ""))
        bad += bool(probs)
    return 1 if bad else 0


def ac05(lint, T, sd):
    """AC 5 (R3, R8; PRD 75ee8ebd): a temp canonical store driven by the close gate's own code from the swarm-decide tree sd (asks add/accept/resolve, intake
    submit/claim/transition and the acceptance core), read by the lint through that tree's own CLI. Each case has its own repair A (finding
    mechanism:1) and successor S1, whose done-check runs this lint on the record for S1 with --require-closed, and its own repair B (mechanism:2) and
    successor S2, bound first: S2's own check is `true` and a row added with `asks add --blocks S2` carries the lint check. R3's command runs for S1
    with A open, closed on a PASS only, FAIL then attested PASS (which the store refuses to close: A stays open), FAIL then run PASS, an intake A accepted (still open) after FAIL then run PASS, an
    intake A cancelled after that proof, S1's check lacking the lint (A proven and closed), for S2 after B's FAIL then run PASS, and without wm-asks:
    exits 1 (consumption-repair-open), 1, 1, 0, 0, 1, 1, 0, 2."""
    sys.path.insert(0, sd)
    state, shome = os.path.join(T, "sd-state"), os.path.join(T, "sd-home")
    os.makedirs(state)
    os.makedirs(shome)
    os.environ.update(WM_DECIDE_STATE=state, HOME=shome)
    from wm_decide import asks, intake, store                    # noqa: E402  (the store's own writers)
    db = store.connect()
    intake.ensure(db)
    shim = os.path.join(T, "sd-shim")
    write(os.path.join(shim, "wm-asks"), "#!/bin/sh\nexec env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH='%s' WM_DECIDE_STATE='%s' HOME='%s' python3 -B -c "
          "'import sys; from wm_decide.cli import main; sys.exit(main(sys.argv[1:]))' \"$@\"\n" % (sd, state, shome), 0o755)
    fx = Fx(T, lint)
    rec = os.path.join(fx.home, "record.jsonl")                   # fx.lint writes each case's rows here before it runs
    DUE = "2026-12-31T09:00"

    def rev(a):
        return db.execute("SELECT rev FROM asks WHERE ask_id = ?", (a,)).fetchone()[0]

    def lintcheck(task):
        return "bash %s --consumption %s --task %s --require-closed" % (lint, rec, task)

    def repair(k, finding, intake_row=False):
        what = "repair %s#%s (AC 5 case %d)" % (BASE, finding, k)
        f = "ac05-%d-%s" % (k, finding.replace(":", ""))
        if intake_row:
            res, _ = intake.submit(db, {"source_event_id": "tg:ac05-%d-%s" % (k, finding), "text": what, "request_type": "new", "authorized_by": "hermes"},
                                   {"owner": "ctl", "due": DUE, "what": what, "check": "test -f " + f, "depends": []}, trusted=("hermes",))
            return res["ask_id"], f
        return asks.add(db, owner="ctl", due=DUE, what=what, check="test -f " + f, actor="t-author"), f

    def s1_of(a, lint_in_check=True):
        s = asks.next_id(db, "A")
        got = asks.add(db, owner="hermes", due=DUE, what="successor S1 closes-after=row:%s" % a, check=lintcheck(s) if lint_in_check else "true",
                       actor="t-author")
        if got != s:
            raise SystemExit("FAIL ac05: successor id %s, predicted %s" % (got, s))
        return s

    def s2_of(b):                                                  # S2 bound first; the row it closes-after carries the lint check
        s2 = asks.add(db, owner="hermes", due=DUE, what="successor S2 closes-after=row:%s" % b, check="true", actor="t-author")
        ob = asks.next_id(db, "A")
        got = asks.add(db, owner="hermes", due=DUE, what="the obligation row S2 closes after", check=lintcheck(s2), actor="t-author", blocks=[s2])
        if got != ob:
            raise SystemExit("FAIL ac05: obligation row id %s, predicted %s" % (got, ob))
        return s2

    def fail_then_run_pass(a, f):
        asks.accept(db, a, actor="t-closer")                       # run mode: the file is missing, FAIL
        open(os.path.join(shome, f), "w").close()
        asks.accept(db, a, actor="t-closer")                       # run mode: PASS at the same sha

    def close(a):
        rid = db.execute("SELECT row_id FROM asks WHERE ask_id = ?", (a,)).fetchone()[0]
        p = subprocess.run([os.path.join(shim, "wm-asks"), "record", "--agent", "r7", "--kind", "verdict", "--model", "deterministic", "--gates", rid,
                            "--what", "decision=%s fixture check passed" % rid, "--why", "fixture", "--evidence", "decision=%s fixture check rc 0" % rid,
                            "--reverse-text", "fixture only"], capture_output=True, text=True)
        vid = (p.stdout.strip().split() or [""])[-1]
        asks.resolve(db, a, expect_rev=rev(a), actor="t-closer", evidence="fixture close", verdict_row=vid)

    def verifying(a):
        intake.claim_task(db, a, worker="w-ac05", expect_rev=rev(a), actor="ctl")
        intake.transition(db, a, "running", expect_rev=rev(a), actor="ctl")
        intake.transition(db, a, "verifying", expect_rev=rev(a), actor="ctl")

    def setup(k, a_intake=False, s1_lint=True):
        a, fa = repair(k, "mechanism:1", a_intake)
        s1 = s1_of(a, s1_lint)
        b, fb = repair(k, "mechanism:2")
        s2 = s2_of(b)
        rows = [fx.base()["falsifier"], fx.row("c-a", "mechanism:1", "repair", ask=a, owner="ctl", successor=s1),
                fx.row("c-b", "mechanism:2", "repair", ask=b, owner="ctl", successor=s2)]
        return a, fa, s1, b, fb, s2, rows

    def c_open(k):
        a, fa, s1, b, fb, s2, rows = setup(k); return rows, s1

    def c_pass_only(k):
        a, fa, s1, b, fb, s2, rows = setup(k)
        open(os.path.join(shome, fa), "w").close()
        asks.accept(db, a, actor="t-closer"); close(a); return rows, s1

    def c_attested(k):                                            # the close gate refuses to close a bound row on an attested PASS (its R4), so A
        a, fa, s1, b, fb, s2, rows = setup(k)                     # stays open; that the lint never takes an attested PASS as the proof of a CLOSED
        asks.accept(db, a, actor="t-closer")                      # repair is h5p-attested-pass-is-no-proof's case
        asks.accept(db, a, actor="t-closer", result="PASS", evidence="a caller attests it")
        try:
            close(a)
        except store.Refused as e:
            if "needs a run PASS" not in str(e):
                raise
        else:
            raise SystemExit("FAIL ac05: the store closed bound row %s on an attested PASS" % a)
        return rows, s1

    def c_run_pass(k):
        a, fa, s1, b, fb, s2, rows = setup(k)
        fail_then_run_pass(a, fa); close(a); return rows, s1

    def c_intake_accepted(k):
        a, fa, s1, b, fb, s2, rows = setup(k, a_intake=True)
        verifying(a); fail_then_run_pass(a, fa)
        intake._accept_core(db, a, expect_rev=rev(a), actor="r7", evidence="independent readback"); return rows, s1

    def c_intake_cancelled(k):
        a, fa, s1, b, fb, s2, rows = setup(k, a_intake=True)
        fail_then_run_pass(a, fa)
        intake.transition(db, a, "cancelled", expect_rev=rev(a), actor="hermes"); return rows, s1

    def c_s1_lacks(k):
        a, fa, s1, b, fb, s2, rows = setup(k, s1_lint=False)
        fail_then_run_pass(a, fa); close(a); return rows, s1

    def c_s2(k):
        a, fa, s1, b, fb, s2, rows = setup(k)
        fail_then_run_pass(b, fb); close(b); return rows, s2

    def c_no_asks(k):
        a, fa, s1, b, fb, s2, rows = setup(k)
        fail_then_run_pass(a, fa); close(a); return rows, s1

    cases = [("a-open", c_open, 1, ["consumption-repair-open"]), ("a-closed-on-a-pass-only", c_pass_only, 1, ["consumption-repair-unproven"]),
             ("a-fail-then-attested-pass-the-store-will-not-close", c_attested, 1, ["consumption-repair-open"]), ("a-fail-then-run-pass", c_run_pass, 0, []),
             ("intake-a-accepted-open-after-its-proof", c_intake_accepted, 0, []),
             ("intake-a-cancelled-after-its-proof", c_intake_cancelled, 1, ["consumption-repair-unproven"]),
             ("s1-check-lacks-the-lint", c_s1_lacks, 1, ["consumption-repair-unproven"]), ("s2-after-b-fail-then-run-pass", c_s2, 0, []),
             ("no-wm-asks", c_no_asks, 2, None)]
    bad, exits = 0, []
    for k, (name, fn, want_rc, want_find) in enumerate(cases, 1):
        try:
            rows, task = fn(k)
        except Exception as e:                                    # a sequence the store refuses is a broken control, never a pass
            print("FAIL ac05-%s: the store refused the sequence: %s: %s" % (name, type(e).__name__, e))
            bad += 1
            exits.append(None)
            continue
        rc, d, err = fx.lint(lint, rows, task=task, require_closed=True, shim=shim, wm_asks=name != "no-wm-asks")
        exits.append(rc)
        probs = []
        if rc != want_rc:
            probs.append("rc %s, want %s" % (rc, want_rc))
        if want_find is not None and sorted(set(d.get("findings") or [])) != want_find:
            probs.append("findings %s, want %s" % (d.get("findings"), want_find))
        if want_rc == 2 and "canonical-unavailable" not in err:
            probs.append("exit 2 without canonical-unavailable")
        if "Traceback" in err:
            probs.append("traceback")
        print("%s ac05-%s: rc %s findings %s%s" % ("FAIL" if probs else "PASS", name, rc, d.get("findings"), ("; " + "; ".join(probs)) if probs else ""))
        bad += bool(probs)
    print("# ac05 exits %s (want 1, 1, 1, 0, 0, 1, 1, 0, 2)" % ", ".join(str(x) for x in exits))
    return 1 if bad else 0


def run(prefix, lint, T):
    fx = Fx(T, lint)
    if not prefix.startswith("h5p"):
        fx.canonical()
    bad = 0
    names = [n for n in CASES if n.startswith(prefix)]
    if not names:
        print("FAIL dfcnfx: no case starts with %s" % prefix)
        return 1
    for n in names:
        c = CASES[n]
        kw = {"drop": c["drop"], "nopage": c["nopage"]}
        if c["scenario"] is not None:
            kw.update(task=TASK if c["plain"] else "A102", require_closed=not c["plain"], shim=fx.fake_canonical(c["scenario"]))
        if c["task"] is not None:
            kw["task"] = c["task"]
        if c["require_closed"] is not None:
            kw["require_closed"] = c["require_closed"]
        if c["home"] == "1724":
            kw.update(home=fx.home1724(), page="notes/analysis/" + P1724)
        if c["page"] is not None:
            kw["page"] = c["page"]
        rc, d, err = fx.lint(lint, c["fn"](fx), **kw)
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
        if c["pending"] is not None and d.get("pending") != c["pending"]:
            probs.append("pending=%s want %s" % (d.get("pending"), c["pending"]))
        if c["repairs"] is not None and [x.get("ask") for x in d.get("repairs") or []] != c["repairs"]:
            probs.append("repairs=%s want asks %s" % (d.get("repairs"), c["repairs"]))
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
    if len(sys.argv) == 5 and sys.argv[1] == "--ac05":
        sys.exit(ac05(sys.argv[2], sys.argv[3], sys.argv[4]))
    print(__doc__.strip().splitlines()[-1], file=sys.stderr)
    sys.exit(2)
