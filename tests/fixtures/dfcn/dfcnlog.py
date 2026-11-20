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
import re
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


def ledger(fx, n_rows, names="wwhtbt.md#mechanism:2", ask_check="true"):
    """A temp canonical store (the real wm-decide behind a wm-asks shim) with, per name in `names` (one or a list), an ask naming it (its done-check
    `ask_check`) and its successor, whose done-check runs this lint on this entry's record for that successor with --require-closed (R3): A1/A2, then
    A3/A4, ..."""
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
        seeds += [(a, "ctl", "repair %s (pending)" % nm, ask_check),
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
case("ac04-overdue-pending-whose-successor-is-gated-holds-no-slug", 1, ["consumption-pending-overdue"], [], "row c-m2")(
    lambda fx: ledger(swap(fx, 2, pending(due="2020-01-01T00:00:00+00:00")), 2))
case("ac04-overdue-pending-whose-successor-is-not-gated-holds-every-slug", 1, ["consumption-blocked", "consumption-pending-overdue"], ["x", "y"],
     "slug y=eligible while held by row c-m2")(
    lambda fx: (swap(fx, 2, pending(due="2020-01-01T00:00:00+00:00")), setattr(fx, "no_asks", True), fx)[-1])
case("ac04-overdue-pending-naming-x-holds-x", 1, ["consumption-blocked", "consumption-pending-overdue"], ["x"], "slug x=eligible while held by row c-m2")(
    lambda fx: swap(fx, 2, pending(prd="PRD-x.md", due="2020-01-01T00:00:00+00:00")))


# review r15 M1: a row whose successor's ledger gate is not verified, or whose prd is none of the run's, holds every State: slug
case("ac04-a-repair-row-whose-successor-is-not-in-the-ledger-holds-every-slug", 1, ["consumption-blocked", "consumption-repair-unbound"], ["x", "y"],
     "slug x=eligible while held by row c-m2")(
    lambda fx: ledger(swap(fx, 2, crow("c-m2", "mechanism:2", "repair", owner="ctl", ask="A1", successor="A777")), 2))
case("ac04-a-repair-row-without-wm-asks-holds-every-slug", 1, ["canonical-unavailable", "consumption-blocked"], ["x", "y"],
     "slug x=eligible while held by row c-m2")(
    lambda fx: (swap(fx, 2, crow("c-m2", "mechanism:2", "repair", owner="ctl", ask="A1", successor="A2")), setattr(fx, "no_asks", True), fx)[-1])
case("ac04-an-earlier-repair-row-whose-successor-is-not-in-the-ledger-holds-every-slug", 1, ["consumption-blocked"], ["x", "y"],
     f"held by entry {PREV_TS}: row e-m1")(
    lambda fx: ledger(earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "repair", PG2, owner="ctl", ask="A1", successor="A777"))), 2,
                      names="old-wwhtbt.md#mechanism:1"))
case("ac04-a-row-naming-a-prd-outside-the-run-holds-every-slug", 1, ["consumption-blocked", "consumption-residual-unaccepted"], ["x", "y", "zzz"],
     "slug x=eligible while held by row c-m1")(
    lambda fx: swap(fx, 1, crow("c-m1", "mechanism:1", "residual", owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody", prd="PRD-zzz.md")))


def cycle(fx):
    """x and y each Depends-on the other: no member is first (review r15 M2)."""
    fx.files["build-queue/PRD-x.md"] = PRD_X.replace("- Depends-on: none", "- Depends-on: PRD-y.md")
    return fx


def lived(fx):
    """visions/old-wwhtbt.md after its mechanism 1 went LIVE: its findings are the falsifier and mechanism 2 (review r15 M3)."""
    fx.files[PG2] = page().replace("1. First — state SPEC", "1. First — state LIVE")
    return fx


def at(r, text):
    return dict(r, page_sha256=sha(text))


case("ac04-a-depends-on-cycle-wwhtbt-skip-holds-every-member", 1, ["consumption-blocked"], ["x", "y"], "a covered entry's WWHTBT skip")(
    lambda fx: wwhtbt_skip(cycle(fx)))
case("ac04-a-depends-on-cycle-unbound-falsifier-holds-every-member", 1, ["consumption-blocked", "consumption-finding-unbound"], ["x", "y"],
     "wwhtbt.md#falsifier unbound")(
    lambda fx: swap(cycle(fx), 0, None))
# review r15 M3: an earlier row for a finding the page no longer has is lifted by a later record binding the page whole at its current bytes
case("ac04-an-earlier-finding-the-page-no-longer-has-is-lifted", 0, [], [])(
    lambda fx: (earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody",
                                                    prd="PRD-x.md"))),
                lived(fx),
                setattr(fx, "cons_rows", fx.cons_rows + [at(test_fal(fx, PG2, "n-fal"), fx.files[PG2]), at(mech(fx, 2, PG2, "n-m2"), fx.files[PG2])]),
                fx)[-1])
case("ac04-an-earlier-finding-still-on-the-page-is-not-lifted-by-a-partial-record", 1, ["consumption-blocked", "consumption-finding-unbound"],
     ["x", "y"], f"held by entry {PREV_TS}: row e-m1")(
    lambda fx: (earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"], accepted_by="rv-nobody",
                                                    prd="PRD-x.md"))),
                setattr(fx, "cons_rows", fx.cons_rows + [test_fal(fx, PG2, "n-fal"), mech(fx, 2, PG2, "n-m2")]),
                fx)[-1])
# review r15 L2: a Task: line short of the full grammar (line-missing; the route row's task_id A1 then differs from the note's, route-provenance-mismatch)
# still names the Task its earlier records are read by, as entry_task reads every earlier entry; a line naming no Task holds every State: slug
def task_line(line):
    """An earlier record of Task A1 holds x; the last entry's Task: line is `line` (None: no Task: line)."""
    return lambda fx: (earlier(fx, rows=old_rows(fx, crow("e-m1", "mechanism:1", "residual", PG2, owner="ctl", evidence=["ledger:A1"],
                                                          accepted_by="rv-nobody", prd="PRD-x.md"))),
                       fx.entry.pop("Task") if line is None else fx.entry.__setitem__("Task", line), fx)[-1]


case("ac04-a-task-line-short-of-the-grammar-keeps-its-earlier-holds", 1, ["consumption-blocked", "line-missing", "route-provenance-mismatch"], ["x"],
     f"held by entry {PREV_TS}: row e-m1")(task_line("Task: A1 Consumer:hermes"))
case("ac04-an-unreadable-task-line-holds-every-slug", 1, ["consumption-blocked", "line-missing", "route-provenance-mismatch"], ["x", "y"],
     "the entry's Task: line cannot be read")(task_line("Task:A1   Consumer: hermes"))


# review r15b LOW 1: a closed successor's done-check holds nothing, so a pending row whose successor is closed holds every State: slug. The temp store
# closes a successor on an attested PASS (the installed store) or refuses to (a close gate, swarm-decide cf0d111: the successor needs a run PASS); each
# case reads the successor's resulting status and states the expectation for it (fx.expect): closed, every slug held; still open, its gate holds it.
def wa(fx, *args):
    p = subprocess.run([os.path.join(fx.root, "shim", "wm-asks")] + list(args), capture_output=True, text=True)
    return p.stdout + p.stderr


def status(fx, ids):
    return {x["ask_id"]: x["status"] for x in json.loads(wa(fx, "asks", "query", "--ids", ids, "--status", "all", "--json"))}


def flag(fx, ask="A1"):
    return os.path.join(fx.root, "flag-" + ask)


def close(fx, ask, how):
    """Close `ask` through the store's own writers: `prove` a run FAIL then a run PASS at one sha (its check `test -e <flag>`, the flag made between
    the runs), `attest` an attested PASS."""
    d = [w for w in wa(fx, "record", "--agent", "ctl", "--kind", "other", "--what", "d", "--why", "t", "--evidence", "ledger:x", "--reverse-text",
                       "none").split() if w.startswith("d-")][0]
    v = [w for w in wa(fx, "record", "--agent", "fable-regrader", "--kind", "verdict", "--gates", d, "--model", "deterministic", "--what", "v", "--why",
                       "t", "--evidence", "ledger:x", "--reverse-text", "none").split() if w.startswith("d-")][-1]
    if how == "prove":
        wa(fx, "asks", "accept", ask, "--by", "r7")
        open(flag(fx, ask), "w").close()
        wa(fx, "asks", "accept", ask, "--by", "r7")
    else:
        wa(fx, "asks", "accept", ask, "--by", "r7", "--result", "PASS", "--evidence", "ledger:outside")
    rev = str(json.loads(wa(fx, "asks", "query", "--ids", ask, "--status", "all", "--json"))[0]["rev"])     # the row's rev after its accepts
    wa(fx, "asks", "resolve", ask, "--by", "r7", "--evidence", "ledger:x", "--expect-rev", rev, "--verdict-row", v)
    return fx


def closed_successor(fx, ask_too, held, findings, needle):
    if ask_too:
        close(fx, "A1", "prove")
    close(fx, "A2", "attest")
    if status(fx, "A2")["A2"] != "closed":       # the store refused the bypass: the open successor's gate holds the row
        fx.expect = {"rc": 1 if "consumption-pending-overdue" in findings else 0,
                     "findings": sorted({"consumption-pending-overdue"} & set(findings)), "held": [], "needle": None}
    else:
        fx.expect = {"rc": 1, "findings": sorted(findings), "held": sorted(held), "needle": needle}
    return fx


case("ac04-a-pending-row-whose-successor-is-closed-holds-every-slug", 1, ["consumption-blocked", "consumption-repair-unproven"], ["x", "y"])(
    lambda fx: closed_successor(ledger(swap(fx, 2, pending()), 2, ask_check="test -e " + flag(fx)), True, ["x", "y"],
                                ["consumption-blocked", "consumption-repair-unproven"], "slug x=eligible while held by row c-m2"))
case("ac04-a-pending-row-whose-ask-is-open-and-successor-closed-holds-every-slug", 1, ["consumption-blocked", "consumption-repair-unproven"], ["x", "y"])(
    lambda fx: closed_successor(ledger(swap(fx, 2, pending()), 2), False, ["x", "y"], ["consumption-blocked", "consumption-repair-unproven"],
                                "successor A2 is closed"))
case("ac04-an-overdue-pending-row-whose-successor-is-closed-holds-every-slug", 1, ["consumption-blocked", "consumption-pending-overdue"], ["x", "y"])(
    lambda fx: closed_successor(ledger(swap(fx, 2, pending(due="2020-01-01T00:00:00+00:00")), 2, ask_check="test -e " + flag(fx)), True, ["x", "y"],
                                ["consumption-blocked", "consumption-pending-overdue"], "slug x=eligible while held by row c-m2"))
# ... while a repair proved (an accept FAIL then a run PASS) whose successor then closed is consumed: over-strict control
def proved_repair(fx):
    """A repair proved by a run FAIL then a run PASS at one sha, its successor then closed (on an attested PASS where the store allows it): consumed.
    A store that writes no accept `mode` (the installed wm-decide before swarm-decide cf0d111, the mode-field install order) cannot show a run PASS,
    so there the repair stays unproven and holds every slug, as R3 fails closed."""
    ledger(swap(fx, 2, crow("c-m2", "mechanism:2", "repair", owner="ctl", ask="A1", successor="A2")), 2, ask_check="test -e " + flag(fx))
    close(fx, "A1", "prove")
    close(fx, "A2", "attest")
    runs = [json.loads(e["detail"]) for e in json.loads(wa(fx, "asks", "events", "A1", "--json")) if e.get("op") == "accept"]
    if not any(isinstance(d, dict) and d.get("mode") == "run" for d in runs):
        fx.expect = {"rc": 1, "findings": ["consumption-blocked", "consumption-repair-unproven"], "held": ["x", "y"],
                     "needle": "shows no accept FAIL followed by a run PASS"}
    return fx


case("ac04-a-proved-repair-whose-successor-closed-is-consumed", 0, [], [])(proved_repair)


# review r15c M1: the route a bound successor closes by without its done-check running. On a store with the intake (swarm-decide cf0d111), the
# successor is created through `intake submit`, the repair ask closes through the full close gate (a run FAIL, a run PASS at one sha, a verdict gating
# the ask's own row_id), and the successor is then intake-cancelled (allowed once the ask it closes after is satisfied): it reads closed and its check
# never runs again, so the pending row holds every State: slug. Each case reads what the store did and states the expectation for it (fx.expect).
def intake_successor(fx):
    """A1 by `asks add` (the repair ask, its check `test -e <flag>`); A2, its successor (closes-after=row:A1, its check this lint with
    --require-closed), through `intake submit`."""
    ledger(fx, 2, names=[], ask_check="test -e " + flag(fx))          # the shim and the temp store only
    rec = os.path.join(fx.home, fx.CONS_REL)
    wa(fx, "asks", "add", "--by", "t-author", "--owner", "ctl", "--due", "2099-12-31T09:00", "--what", "repair wwhtbt.md#mechanism:2 (pending)",
       "--check", "test -e " + flag(fx))
    env = {"authorized_by": "hermes", "text": "successor", "request_type": "new"}
    ch = {"owner": "hermes", "due": "2099-12-31T09:00", "what": "successor closes-after=row:A1",
          "check": f"bash {fx.lint} --consumption {rec} --task A2 --require-closed", "depends": []}
    wa(fx, "intake", "submit", "--envelope", json.dumps(env), "--change", json.dumps(ch))
    return fx


def close_through_gate(fx, ask):
    """Close `ask` through the close gate: a run FAIL, the flag, a run PASS at one sha, a verdict gating the ask's own row_id, resolve."""
    wa(fx, "asks", "accept", ask, "--by", "r7")
    open(flag(fx, ask), "w").close()
    wa(fx, "asks", "accept", ask, "--by", "r7")
    row = json.loads(wa(fx, "asks", "query", "--ids", ask, "--status", "all", "--json"))[0]
    v = [w for w in wa(fx, "record", "--agent", "fable-regrader", "--kind", "verdict", "--gates", str(row.get("row_id")), "--model", "deterministic",
                       "--what", "v", "--why", "t", "--evidence", "ledger:x", "--reverse-text", "none").split() if w.startswith("d-")]
    rev = str(json.loads(wa(fx, "asks", "query", "--ids", ask, "--status", "all", "--json"))[0]["rev"])
    wa(fx, "asks", "resolve", ask, "--by", "r7", "--evidence", "ledger:x", "--expect-rev", rev, "--verdict-row", v[-1] if v else "none")


def cancelled_successor(fx, overdue):
    intake_successor(fx)
    close_through_gate(fx, "A1")
    q = json.loads(wa(fx, "asks", "query", "--ids", "A2", "--status", "all", "--json") or "[]")
    said = ""
    if q:
        env = {"authorized_by": "hermes", "text": "cancel successor", "request_type": "cancel", "target_ask": "A2", "target_rev": q[0]["rev"]}
        said = wa(fx, "intake", "submit", "--envelope", json.dumps(env), "--change", "{}")
    try:
        ev = json.loads(wa(fx, "asks", "events", "A2", "--json") or "[]")
    except ValueError:
        ev = []
    if any(isinstance(e, dict) and e.get("op") == "cancel" for e in ev):        # cancelled: its check never runs, every slug held
        fx.expect = {"rc": 1, "findings": ["consumption-blocked", "consumption-pending-overdue" if overdue else "consumption-repair-unproven"],
                     "held": ["x", "y"], "needle": "slug x=eligible while held by row c-m2"}
        return fx
    # the store refused the cancel: the open successor's gate holds the row. That stands only for a store that refuses with A1 closed and names the
    # close gate's R5 peer A1 (review r15d L1): a store that left A1 open (close_through_gate no longer closing it) would pass this case untested
    a1 = status(fx, "A1").get("A1")
    if a1 != "closed" or not re.search(r"\brefused\b.*\bA1\b", said):
        raise SystemExit("FAIL dfcnlog: the store took no cancel of A2, and its refusal is not the R5 one with A1 closed (A1 %s; intake said %r)"
                         % (a1, said.strip()[:300]))
    fx.expect = {"rc": 1 if overdue else 0, "findings": ["consumption-pending-overdue"] if overdue else [], "held": [], "needle": None}
    return fx


case("ac04-a-pending-row-whose-successor-is-intake-cancelled-holds-every-slug", 1, ["consumption-blocked", "consumption-repair-unproven"], ["x", "y"])(
    lambda fx: cancelled_successor(swap(fx, 2, pending()), False))
case("ac04-an-overdue-pending-row-whose-successor-is-intake-cancelled-holds-every-slug", 1, ["consumption-blocked", "consumption-pending-overdue"],
     ["x", "y"])(lambda fx: cancelled_successor(swap(fx, 2, pending(due="2020-01-01T00:00:00+00:00")), True))
# review r15b LOW 2: a note with no readable Task (no Task: line, a lowercase or an indented one) holds every State: slug
case("ac04-a-note-with-no-task-line-holds-every-slug", 1, ["consumption-blocked", "line-missing", "route-provenance-mismatch"], ["x", "y"],
     "the entry's Task: line cannot be read")(task_line(None))
case("ac04-a-lowercase-task-line-holds-every-slug", 1, ["consumption-blocked", "line-missing", "route-provenance-mismatch"], ["x", "y"],
     "the entry's Task: line cannot be read")(task_line("task: A1   Consumer: hermes"))
case("ac04-an-indented-task-line-holds-every-slug", 1, ["consumption-blocked", "line-missing", "route-provenance-mismatch"], ["x", "y"],
     "the entry's Task: line cannot be read")(task_line(" Task: A1   Consumer: hermes"))
# review r15b LOW 3: a valid pending row naming a PRD of the home outside the run holds that PRD alone
PRD_W = "# w\n\n- Depends-on: none\n\n## Acceptance criteria\n\n1. P0 — Given wwhtbt.md#mechanism:2, When `tests/w.sh` runs, Then it exits 0.\n"
case("ac04-a-valid-pending-row-naming-a-later-slice-holds-it-alone", 0, [], ["w"])(
    lambda fx: (fx.files.__setitem__("build-queue/PRD-w.md", PRD_W), ledger(swap(fx, 2, pending(prd="PRD-w.md")), 2))[-1])
# review r15b LOW 4: a cycle with a member the home lacks leaves no first PRD: every member is held
case("ac04-a-cycle-with-an-unknown-member-holds-every-member", 1, ["adversarial-slug-missing", "consumption-blocked", "consumption-finding-unbound",
                                                                   "state-grammar"],
     ["x", "y", "z"], "wwhtbt.md#falsifier unbound")(
    lambda fx: (fx.entry.__setitem__("State", fx.entry["State"] + " z=eligible"), swap(cycle(fx), 0, None))[-1])

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
case("ac04-a-falsifier-on-ac-1-of-y-which-depends-on-x", 1, ["consumption-blocked", "falsifier-not-first"], ["x", "y"], "PRD-y.md AC 1 is not AC 1 of a first PRD")(
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
        c = dict(c, **getattr(fx, "expect", None) or {})
        fx.build()
        with open(os.path.join(out, "policy.json"), "w", encoding="utf-8") as fh:
            json.dump(POLICY, fh)
        fake = os.path.join(out, "fakehome")
        os.makedirs(fake, exist_ok=True)
        dirs = os.environ.get("PATH", "/usr/bin:/bin").split(os.pathsep)
        if getattr(fx, "no_asks", False):                # as the lint's selftest fx_env: a PATH without any wm-asks (canonical-unavailable)
            dirs = [d for d in dirs if not os.path.exists(os.path.join(d, "wm-asks"))]
        path = os.pathsep.join(([fx.path] if fx.path else []) + dirs)
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
