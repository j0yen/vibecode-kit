#!/usr/bin/env python3
"""Cases of PRD-dream-finding-consumption AC 4 (R7 hold scope, R6 placement, R1's record line) and AC 3's authoring half (R3 residual acceptance,
R4 receipts), linted the way Hermes' case-11 gate lints a run: `bash <lint> <home>/notes/dream-log.md --last --prd-dir <home> --decisions <log>
--json` (the gate's `--last --json`, with this case's home and decisions log).

A case is a PRD home built with the lint's own selftest helpers (Fx, row, mx_file; loaded from the lint the way tests/fixtures/datr/dfx.py loads
them). Its last entry is dated on the cutover (R9) and, as Task A1's first entry, covered (new slugs x and y), with:
- build-queue/PRD-x.md (Depends-on none) and build-queue/PRD-y.md (Depends-on PRD-x.md), so PRD-x.md is the run's only first PRD;
- State x and y reviewed APPROVE, and eligible for AC 4 (linted only for AC 3, so no hold blocks there);
- the page visions/wwhtbt.md: falsifier `bash scripts/kill-x.sh` and two SPEC mechanisms;
- a consumption record whose base rows bind all three: the falsifier by requirement AC 1 of PRD-x.md with its kill script, the mechanisms by `test`
  rows in a scratch repository.
A case replaces rows, adds an earlier entry of a Task with its own record, or changes the Analysis: or Failure: line. It states its exact exit, its
exact finding-id set, the exact `consumption.held` slugs and a text one FAIL line carries. Pending rows read the canonical ledger from a temp store
behind a `wm-asks` shim (the wm-decide named by DFCN_WM_DECIDE, else the one on PATH), as tests/fixtures/dfcn/dfcnfx.py's canonical() does.

Usage: dfcnlog.py --run <prefix> <lint> <scratch dir>   (exit 0 when every case of the prefix passes; one PASS or FAIL line per case)
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LINT_SRC = os.path.join(REPO, "skills", "dream", "scripts", "dream-run-note-lint.sh")


def lint_helpers(path=LINT_SRC):
    src = open(path, encoding="utf-8").read()
    code = src.split("\n#__PYTHON__\n", 1)[1].split("\n#__PYTHON_END__", 1)[0]
    code = code.rsplit("\nsys.exit(main(sys.argv[1:]))", 1)[0]
    ns = {"__name__": "dream_lint_helpers"}
    exec(compile(code, path + ":python", "exec"), ns)
    return ns


H = lint_helpers()
Fx, row, mx_file, CUT = H["Fx"], H["row"], H["mx_file"], H["TRIGGER_CUTOVER"]
S_W, S_D, S_5, M_REL, FXF = H["S_W"], H["S_D"], H["S_5"], H["M_REL"], H["FX_FINDINGS"]
T_TS, PREV_TS, OUT_TS = CUT + "T02:00:00-08:00", CUT + "T01:30:00-08:00", CUT + "T00:30:00-08:00"
PG, PG2, BASE = "visions/wwhtbt.md", "visions/old-wwhtbt.md", "wwhtbt.md"
M_NEW = f"notes/reviews/{CUT}T01:45:00-08:00-adversarial.md"   # the last entry's matrix: later than an earlier entry of the cutover day (PREV_TS)
KILL = "#!/bin/sh\necho KILL-X\n"
POLICY = {"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$", "placeholders": ["none", "n/a", "tbd", "todo", "x"]}}
OUTAGE = "policy file not found"                # the resolver's own text when the default policy file is missing (trigger-record R2 accepts it)
PRD_X = ("# x\n\n- Depends-on: none\n\n## Acceptance criteria\n\n"
         "1. P0 — Given wwhtbt.md#falsifier, When `bash scripts/kill-x.sh` runs on a record missing a row, Then it prints `KILL-X`.\n"
         "2. P0 — Given wwhtbt.md#mechanism:1, When `tests/x_ac02.sh` runs its negative control, Then a record without the row exits 1.\n"
         "3. P0 — Given wwhtbt.md#falsifier, When `bash scripts/kill-x.sh` runs, Then it prints `KILL-X`.\n")
PRD_Y = ("# y\n\n- Depends-on: PRD-x.md\n\n## Acceptance criteria\n\n"
         "1. P0 — Given wwhtbt.md#falsifier, When `bash scripts/kill-x.sh` runs, Then it prints `KILL-X`.\n")
REVIEWERS = [("rv-ok", "A1", "review"), ("rv-norole", "A1", None), ("rv-noline", "A1", "review"), ("rv-other", "A9", "review")]
VERDICTS = {"v-ok.md": "Review session rv-ok\naccepts c-res\n", "v-author.md": f"Review session {S_D}\naccepts c-res\n",
            "v-norole.md": "Review session rv-norole\naccepts c-res\n", "v-noline.md": "Review session rv-noline\nthe residual is fine, accepts c-res in spirit\n",
            "v-other.md": "Review session rv-other\naccepts c-res\n"}


def sha(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


def page(sess=S_W):
    return (f"# wwhtbt page\nanswered_by: fable\nsession: {sess}\n\n# Weakest link\n\nThe falsifier `bash scripts/kill-x.sh` prints KILL-X when a "
            "finding has no row.\n\n# Mechanisms\n\n1. First — state SPEC\n2. Second — state SPEC\n")


def crow(rid, finding, binding, pg=PG, **kw):
    r = {"id": rid, "page": pg, "page_sha256": sha(page()), "finding": finding, "binding": binding, "author_session": S_D}
    r.update(kw)
    return r


def fal(prd="PRD-x.md", ac=1, pg=PG, rid="c-fal"):
    return crow(rid, "falsifier", "requirement", pg, prd=prd, ac=ac, kill={"script": "scripts/kill-x.sh", "sha256": sha(KILL), "string": "KILL-X"})


def mech(fx, n, pg=PG, rid=None):
    return crow(rid or f"c-m{n}", f"mechanism:{n}", "test", pg, repo=fx.repo, commit=fx.commit, path="tests/cons.sh")


def test_fal(fx, pg=PG, rid="c-fal"):
    return crow(rid, "falsifier", "test", pg, repo=fx.repo, commit=fx.commit, path="tests/cons.sh")


def base(out, eligible=True):
    fx = Fx(out)
    fx.ts, fx.failure = T_TS, "Failure: none"
    fx.files.update({"build-queue/PRD-x.md": PRD_X, "build-queue/PRD-y.md": PRD_Y, PG: page(), PG2: page(), "scripts/kill-x.sh": KILL,
                     "notes/reviews/r1.txt": "x APPROVE fable\ny APPROVE fable\n", M_REL: mx_file(["x", "y"]), M_NEW: mx_file(["x", "y"])})
    el = " x=eligible y=eligible" if eligible else ""
    fx.entry["State"] = "State: x=linted x=reviewed:APPROVE y=linted y=reviewed:APPROVE" + el
    fx.entry["Analysis"] = f"Analysis: wwhtbt=ran {PG} 5whys=skipped: not a failure seed adversarial={M_NEW} uncovered=1"
    fx.repo, fx.commit = fx.cons_repo("# binds wwhtbt.md#falsifier,mechanism:1,mechanism:2\n# binds old-wwhtbt.md#falsifier,mechanism:1,mechanism:2\n"
                                      "# binds 5whys.md#falsifier\n")
    fx.cons_rows = [fal(), mech(fx, 1), mech(fx, 2)]
    for s, t, role in REVIEWERS:
        fx.rows.append(row("2026-11-15T01:50:00-08:00", "launch", t, "dream", "opus-xhigh", "claude-opus-5-5", "xhigh", s, **({"role": role} if role else {})))
    for name, text in VERDICTS.items():
        fx.files["notes/reviews/" + name] = text
    fx.store = None
    return fx


def swap(fx, n, r):
    """Replace the base row of mechanism n (0 = the falsifier) with r (None drops it)."""
    rows = list(fx.cons_rows)
    rows[n] = r
    fx.cons_rows = [x for x in rows if x is not None]
    return fx


def earlier(fx, task="A1", analysis=None, rows=None, extra=()):
    """An earlier entry of `task` on the cutover day, before the last one: Analysis binding visions/old-wwhtbt.md unless `analysis`, and its own record
    (notes/consumption/earlier.jsonl) when `rows` is given."""
    fx.prev_entry = PREV_TS
    fx.prev_lines = [f"Task: {task}   Consumer: hermes", "Seeds: selftest",
                     analysis or f"Analysis: wwhtbt=ran {PG2} 5whys=skipped: not a failure seed adversarial={M_REL} uncovered=1",
                     "State: x=linted y=linted"] + list(extra)
    if rows is not None:
        fx.prev_lines.append("Consumption: notes/consumption/earlier.jsonl")
        fx.files["notes/consumption/earlier.jsonl"] = "".join(json.dumps(r) + "\n" for r in rows)
    return fx


def old_rows(fx, m1):
    """The earlier record: old-wwhtbt.md's falsifier and mechanism 2 bound, mechanism 1 bound by `m1`."""
    return [test_fal(fx, PG2, "e-fal"), m1, mech(fx, 2, PG2, "e-m2")]


def ledger(fx, n_rows, names="wwhtbt.md#mechanism:2"):
    """A temp canonical store (the real wm-decide behind a wm-asks shim) with, per name in `names` (one or a list), an ask naming it and its
    successor, whose done-check runs this lint on this entry's record for that successor with --require-closed (R3): A1/A2, then A3/A4, ..."""
    wd = os.environ.get("DFCN_WM_DECIDE") or shutil.which("wm-decide")
    if not wd:
        raise SystemExit("FAIL dfcnlog: no wm-decide for the temp canonical store (set DFCN_WM_DECIDE to a wm-decide binary)")
    shim, state, shome = (os.path.join(fx.root, d) for d in ("shim", "canonical", "store-home"))
    for d in (shim, shome):
        os.makedirs(d, exist_ok=True)
    with open(os.path.join(shim, "wm-asks"), "w", encoding="utf-8") as fh:
        fh.write("#!/bin/sh\nexec env WM_DECIDE_STATE='%s' HOME='%s' '%s' \"$@\"\n" % (state, shome, wd))
    os.chmod(os.path.join(shim, "wm-asks"), 0o755)
    rec = os.path.join(fx.home, fx.CONS_REL)
    seeds = []
    for i, nm in enumerate([names] if isinstance(names, str) else names):
        a, sc = "A%d" % (2 * i + 1), "A%d" % (2 * i + 2)
        seeds += [(a, "ctl", "repair %s (pending)" % nm, "true"),
                  (sc, "hermes", "successor closes-after=row:%s" % a, f"bash {fx.lint} --consumption {rec} --task {sc} --require-closed")]
    for me, owner, what, chk in seeds:
        p = subprocess.run([os.path.join(shim, "wm-asks"), "asks", "add", "--by", "t-author", "--owner", owner, "--due", "2099-12-31T09:00",
                            "--what", what, "--check", chk], capture_output=True, text=True)
        got = p.stdout.strip().split()[-1] if p.returncode == 0 and p.stdout.strip() else None
        if got != me:
            raise SystemExit("FAIL dfcnlog: seeding the temp store gave %r, want %s: %s%s" % (got, me, p.stdout, p.stderr))
    fx.path = shim
    return fx


def pending(prd=None, due="2099-01-01T00:00:00+00:00"):
    return crow("c-m2", "mechanism:2", "pending", owner="ctl", due=due, ask="A1", successor="A2", **({"prd": prd} if prd else {}))


def denied(skill, ts=OUT_TS):
    return row(ts, "denied", "A1", skill, "opus-xhigh", "claude-opus-5-5", "xhigh", "", reasons=OUTAGE)


CASES = {}


def case(name, rc, findings, held, needle=None):
    def deco(fn):
        CASES[name] = {"fn": fn, "rc": rc, "findings": sorted(findings), "held": sorted(held), "needle": needle}
        return fn
    return deco


# ---------------------------------------------------------------- AC 4: R7 hold scope (x and y eligible), R6 placement, R1's line
case("ac04-all-consumed-holds-nothing", 0, [], [])(lambda fx: fx)
case("ac04-unconsumed-row-names-x", 1, ["consumption-blocked", "consumption-residual-unaccepted"], ["x"], "slug x=eligible while held by row c-m1")(
    lambda fx: swap(fx, 1, crow("c-m1", "mechanism:1", "residual", owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody", prd="PRD-x.md")))
case("ac04-unconsumed-row-names-x-in-an-earlier-entry", 1, ["consumption-blocked"], ["x"], f"held by entry {PREV_TS}: row e-m1")(
    lambda fx: earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody",
                                                   prd="PRD-x.md"))))
case("ac04-earlier-row-lifted-by-this-record-binding-it", 0, [], [])(
    lambda fx: (earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody",
                                                    prd="PRD-x.md"))),
                setattr(fx, "cons_rows", fx.cons_rows + [test_fal(fx, PG2, "n-fal"), mech(fx, 1, PG2, "n-m1"), mech(fx, 2, PG2, "n-m2")]), fx)[-1])
case("ac04-earlier-row-not-lifted-by-a-pending-row", 1, ["consumption-blocked"], ["x"], f"held by entry {PREV_TS}: row e-m1")(
    lambda fx: (earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody",
                                                    prd="PRD-x.md"))),
                setattr(fx, "cons_rows", fx.cons_rows + [test_fal(fx, PG2, "n-fal"), dict(pending(), id="n-m1", page=PG2, finding="mechanism:1"),
                                                         mech(fx, 2, PG2, "n-m2")]),
                ledger(fx, 2, names="old-wwhtbt.md#mechanism:1"))[-1])
case("ac04-an-earlier-row-of-another-task-holds-nothing", 0, [], [])(
    lambda fx: earlier(fx, task="A9", rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"],
                                                             accepted_by="rv-nobody", prd="PRD-x.md"))))
case("ac04-pending-with-ask-and-successor-holds-no-slug", 0, [], [])(lambda fx: ledger(swap(fx, 2, pending()), 2))
case("ac04-pending-naming-x-holds-x", 1, ["consumption-blocked"], ["x"], "row c-m2 (wwhtbt.md#mechanism:2) pending")(
    lambda fx: ledger(swap(fx, 2, pending(prd="PRD-x.md")), 2))
case("ac04-unconsumed-row-naming-neither-holds-every-slug", 1, ["consumption-binding-invalid", "consumption-blocked"], ["x", "y"],
     "slug y=eligible while held by row c-m2")(
    lambda fx: swap(fx, 2, crow("c-m2", "mechanism:2", "test", repo=fx.repo, commit=fx.commit, path="tests/missing.sh")))
case("ac04-overdue-pending-with-a-successor-holds-no-slug", 1, ["consumption-pending-overdue"], [], "row c-m2")(
    lambda fx: swap(fx, 2, pending(due="2020-01-01T00:00:00+00:00")))
case("ac04-overdue-pending-naming-x-holds-x", 1, ["consumption-blocked", "consumption-pending-overdue"], ["x"], "slug x=eligible while held by row c-m2")(
    lambda fx: swap(fx, 2, pending(prd="PRD-x.md", due="2020-01-01T00:00:00+00:00")))


def wwhtbt_skip(fx):
    fx.entry["Analysis"] = f"Analysis: wwhtbt=skipped: blocked decision={OUT_TS} 5whys=skipped: not a failure seed adversarial={M_NEW} uncovered=1"
    fx.rows.append(denied("wwhtbt"))
    fx.cons_rows, fx.consume = None, False
    return fx


case("ac04-a-wwhtbt-skip-holds-the-first-prd", 1, ["consumption-blocked"], ["x"], "a covered entry's WWHTBT skip")(wwhtbt_skip)
case("ac04-an-earlier-wwhtbt-skip-is-lifted-by-a-later-ran", 0, [], [])(
    lambda fx: (fx.rows.append(denied("wwhtbt")),
                earlier(fx, analysis=f"Analysis: wwhtbt=skipped: blocked decision={OUT_TS} 5whys=skipped: x adversarial={M_REL} uncovered=1"))[-1])


def trigger_skip(fx):
    fx.failure = "Failure: recurring-failure ledger:A1"
    fx.entry["Analysis"] = f"Analysis: wwhtbt=ran {PG} 5whys=skipped: blocked decision={OUT_TS} adversarial={M_NEW} uncovered=1"
    fx.rows.append(denied("5whysandrhyme"))
    return fx


case("ac04-a-trigger-class-5whys-skip-holds-every-slug", 1, ["consumption-blocked"], ["x", "y"], "a 5whys skip under a trigger-class Failure:")(trigger_skip)
case("ac04-an-earlier-trigger-class-5whys-skip-is-lifted-by-a-later-page", 0, [], [])(
    lambda fx: (fx.rows.append(denied("5whysandrhyme")),
                fx.entry.__setitem__("Analysis", f"Analysis: wwhtbt=ran {PG} 5whys=page visions/5whys.md adversarial={M_NEW} uncovered=1"),
                setattr(fx, "cons_rows", fx.cons_rows + [crow("c-5", "falsifier", "test", "visions/5whys.md", page_sha256=sha(f"# five whys page\nsession: {S_5}\n" + FXF),
                                                             repo=fx.repo, commit=fx.commit, path="tests/cons.sh")]),
                earlier(fx, analysis=f"Analysis: wwhtbt=ran {PG2} 5whys=skipped: blocked decision={OUT_TS} adversarial={M_REL} uncovered=1",
                        rows=old_rows(fx, mech(fx, 1, PG2, "e-m1")), extra=["Failure: recurring-failure ledger:A1"]))[-1])
case("ac04-a-falsifier-on-ac-3", 1, ["consumption-blocked", "falsifier-not-first"], ["x"], "row c-fal (wwhtbt.md#falsifier): PRD-x.md AC 3")(
    lambda fx: swap(fx, 0, fal(ac=3)))
case("ac04-a-falsifier-on-ac-1-of-y-which-depends-on-x", 1, ["consumption-blocked", "falsifier-not-first"], ["y"], "PRD-y.md AC 1 is not AC 1 of a first PRD")(
    lambda fx: swap(fx, 0, fal(prd="PRD-y.md")))
case("ac04-an-unbound-falsifier-holds-the-first-prd", 1, ["consumption-blocked", "consumption-finding-unbound"], ["x"], "wwhtbt.md#falsifier unbound")(
    lambda fx: swap(fx, 0, None))
case("ac04-an-unbound-mechanism-holds-every-slug", 1, ["consumption-blocked", "consumption-finding-unbound"], ["x", "y"], "wwhtbt.md#mechanism:1 unbound")(
    lambda fx: swap(fx, 1, None))
case("ac04-no-record-line", 1, ["consumption-blocked", "consumption-missing"], ["x", "y"], "binds visions/wwhtbt.md")(
    lambda fx: (setattr(fx, "cons_line", ""), fx)[-1])


def open_before(fx, covered):
    """An earlier record of Task A1 still has an unconsumed row (a residual naming PRD-y.md, unaccepted). The last entry binds no page (its WWHTBT skip
    is corroborated) and has no Consumption: line; it is covered when its State: carries a drafted token (R1 asks a line of it), else uncovered."""
    wwhtbt_skip(fx)
    fx.entry["State"] = "State: " + ("x=drafted " if covered else "") + "x=linted x=reviewed:APPROVE y=linted y=reviewed:APPROVE"
    if not covered:
        fx.entry["Analysis"] = f"Analysis: wwhtbt=skipped: nothing new 5whys=skipped: not a failure seed adversarial={M_NEW} uncovered=1"
    return earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody",
                                              prd="PRD-y.md")))


case("ac04-a-covered-entry-after-an-open-earlier-record-needs-the-line", 1, ["consumption-missing"], ["x", "y"],
     "a covered entry while an earlier record of Task A1 still has unconsumed rows")(lambda fx: open_before(fx, True))
case("ac04-an-uncovered-entry-after-an-open-earlier-record-needs-no-line", 0, [], ["y"])(lambda fx: open_before(fx, False))


# ---------------------------------------------------------------- AC 3, authoring half: R3 residual acceptance and R4 receipts on a run note
def residual(fx, acc):
    return swap(fx, 2, crow("c-res", "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by=acc))


case("ac03a-residual-accepted-by-an-independent-review", 0, [], [])(lambda fx: residual(fx, "rv-ok"))
case("ac03a-residual-accepted-by-the-author-lineage", 1, ["consumption-residual-unaccepted"], ["x", "y"], f"accepted_by {S_D}")(
    lambda fx: residual(fx, S_D))
case("ac03a-residual-accepted-by-a-role-less-session", 1, ["consumption-residual-unaccepted"], ["x", "y"], "accepted_by rv-norole")(
    lambda fx: residual(fx, "rv-norole"))
case("ac03a-residual-review-of-another-task", 1, ["consumption-residual-unaccepted"], ["x", "y"], "accepted_by rv-other")(
    lambda fx: residual(fx, "rv-other"))
case("ac03a-residual-without-an-accepts-line", 1, ["consumption-residual-unaccepted"], ["x", "y"], "holds `accepts c-res`")(
    lambda fx: residual(fx, "rv-noline"))
case("ac03a-receipt-only-session", 1, ["consumption-receipt-only"], ["x", "y"], "its only target is a receipt (session)")(
    lambda fx: (setattr(fx, "cons_rows", fx.cons_rows + [{"id": "c-rcpt", "binding": "test", "session": "s-1"}]), fx)[-1])
case("ac03a-receipt-only-run-id", 1, ["consumption-receipt-only"], ["x", "y"], "its only target is a receipt (run_id)")(
    lambda fx: (setattr(fx, "cons_rows", fx.cons_rows + [{"id": "c-rcpt", "binding": "requirement", "run_id": "run-1"}]), fx)[-1])
case("ac03a-receipt-only-report", 1, ["consumption-receipt-only"], ["x", "y"], "binding 'report' is none of")(
    lambda fx: (setattr(fx, "cons_rows", fx.cons_rows + [{"id": "c-rcpt", "binding": "report", "report": "notes/report.md"}]), fx)[-1])


# ---------------------------------------------------------------- AC 8: notes written as SKILL.md Phase 4 says lint clean
def page4():
    return page().replace("2. Second — state SPEC\n", "2. Second — state SPEC\n3. Third — state SPEC\n4. Fourth — state SPEC\n")


def five_bindings(fx):
    """A note binding a page whose record sits where Phase 4 puts it (notes/consumption/<ISO-ts>-<slug>.jsonl) and uses each of the five bindings:
    the falsifier on AC 1 of the first PRD, a test, a residual accepted by an independent review, an open repair and a pending row (both bound in a
    temp store, their successors' done-checks running this lint on the record)."""
    fx.CONS_REL = "notes/consumption/%s-selftest.jsonl" % T_TS
    fx.files[PG] = page4()
    h4 = sha(page4())
    fx.repo, fx.commit = fx.cons_repo("# binds wwhtbt.md#falsifier,mechanism:1,mechanism:2,mechanism:3,mechanism:4\n")
    fx.cons_rows = [dict(fal(), page_sha256=h4), dict(mech(fx, 1), page_sha256=h4),
                    crow("c-res", "mechanism:2", "residual", owner="hermes", evidence=["ledger:A1723"], accepted_by="rv-ok", page_sha256=h4),
                    crow("c-rep", "mechanism:3", "repair", ask="A1", owner="ctl", successor="A2", page_sha256=h4),
                    crow("c-pen", "mechanism:4", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask="A3", successor="A4", page_sha256=h4)]
    return ledger(fx, 5, names=["wwhtbt.md#mechanism:3", "wwhtbt.md#mechanism:4"])


case("ac08-a-note-with-the-five-bindings-lints-clean", 0, [], [])(five_bindings)
case("ac08-a-note-binding-no-page-needs-no-line", 0, [], ["x"])(wwhtbt_skip)


def run(prefix, lint, T):
    lint = os.path.abspath(lint)
    names = [n for n in CASES if n.startswith(prefix)]
    if not names:
        print("FAIL dfcnlog: no case starts with %s" % prefix)
        return 1
    bad = 0
    for i, n in enumerate(names):
        c = CASES[n]
        out = os.path.join(T, "c%02d" % i)
        fx = base(out, eligible=n.startswith("ac04"))
        fx.lint = lint
        fx = c["fn"](fx)
        fx.build()
        with open(os.path.join(out, "policy.json"), "w", encoding="utf-8") as fh:
            json.dump(POLICY, fh)
        fake = os.path.join(out, "fakehome")
        os.makedirs(fake, exist_ok=True)
        path = os.environ.get("PATH", "/usr/bin:/bin")
        if fx.path:
            path = fx.path + os.pathsep + path
        env = dict(os.environ, HOME=fake, PATH=path, SKILL_ROUTING_POLICY=os.path.join(out, "policy.json"))
        env.pop("SKILL_ROUTING_DECISIONS", None)
        p = subprocess.run(["bash", lint, os.path.join(fx.home, "notes", "dream-log.md"), "--last", "--prd-dir", fx.home, "--decisions", fx.dec, "--json"],
                           capture_output=True, text=True, env=env, cwd=out, timeout=600)
        try:
            d = json.loads(p.stdout) if p.stdout.strip() else {}
        except ValueError:
            d = {}
        held = sorted(h.get("slug") for h in ((d.get("consumption") or {}).get("held") or []))
        fails = [l for l in p.stderr.splitlines() if l.startswith("FAIL ")]
        probs = []
        if p.returncode != c["rc"]:
            probs.append("rc=%s want %s" % (p.returncode, c["rc"]))
        if sorted(set(d.get("findings") or [])) != c["findings"]:
            probs.append("findings=%s want %s" % (sorted(set(d.get("findings") or [])), c["findings"]))
        if held != c["held"]:
            probs.append("held=%s want %s" % (held, c["held"]))
        if c["needle"] and not any(c["needle"] in l for l in fails):
            probs.append("no FAIL line carries %r" % c["needle"])
        if "Traceback" in p.stderr:
            probs.append("traceback")
        if probs:
            bad += 1
            print("FAIL %s: %s; stderr=%s" % (n, "; ".join(probs), " | ".join(p.stderr.strip().splitlines()[:6])))
        else:
            print("PASS %s" % n)
    print("# %s: %d cases, %d pass, %d fail" % (prefix, len(names), len(names) - bad, bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "--run":
        sys.exit(run(sys.argv[2], sys.argv[3], sys.argv[4]))
    print(__doc__.strip().splitlines()[-1], file=sys.stderr)
    sys.exit(2)
