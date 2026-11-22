#!/usr/bin/env python3
"""Fixture builder and driver for the datr tests (PRD-dream-analysis-trigger-record).

A case is one PRD home, a private decisions log and a routing policy under <outdir> (<outdir>/home,
<outdir>/decisions.jsonl, <outdir>/policy.json). Fx-based cases use the lint's own selftest helpers
(Fx, row, mx_file), loaded from skills/dream/scripts/dream-run-note-lint.sh as
tests/fixtures/drmx/mfx.py does, and date the entry under test on the lint's TRIGGER_CUTOVER (R7).
Mission cases copy the checked-in drfc fixture (the base or one variant, as tests/drfc_lib.sh `use`
does), re-date the copy from the fixture's day (2026-11-18, before the cutover) onto the cutover day with
tests/fixtures/redate.py, so its entries are dated after the cutover, and edit its last entry.

Every case states its expected exit, its exact finding-id set and, where the AC asks for more, a
predicate on the --json object. `--run` lints each case's last entry with the lint under test (a
subprocess of the real script: `bash <lint> <log> --last --prd-dir <home> [--decisions <log>] --json`,
private HOME, SKILL_ROUTING_POLICY at the case's policy, working directory a fresh directory that is
neither the home nor the manifest's), and prints one PASS/FAIL line per case.

Usage: dfx.py --list [<prefix>]                 case names and expectations
       dfx.py <case> <outdir>                   build one case
       dfx.py --run <prefix> <lint> [<report>]  build and lint every case of <prefix> (ac02, ac03, ...)
"""
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
LINT = os.path.join(REPO, "skills", "dream", "scripts", "dream-run-note-lint.sh")
DRFC = os.path.join(REPO, "tests", "fixtures", "drfc")
DRFC_DAY = "2026-11-18"                                  # the checked-in drfc fixture's one day (re-dated before the cutover, H1)
REDATE = os.path.join(REPO, "tests", "fixtures", "redate.py")


def lint_helpers(path=LINT):
    src = open(path, encoding="utf-8").read()
    code = src.split("\n#__PYTHON__\n", 1)[1].split("\n#__PYTHON_END__", 1)[0]
    code = code.rsplit("\nsys.exit(main(sys.argv[1:]))", 1)[0]
    ns = {"__name__": "dream_lint_helpers"}
    exec(compile(code, path + ":python", "exec"), ns)
    return ns


H = lint_helpers()
Fx, row, CUT = H["Fx"], H["row"], H["TRIGGER_CUTOVER"]
S_W, S_5, M_REL = H["S_W"], H["S_5"], H["M_REL"]
FXF = H["FX_FINDINGS"]         # finding consumption R5: every page a case binds has its falsifier section (Fx writes the entry's record, R1)
T_TS, OUT_TS, LATE_TS = CUT + "T02:00:00-08:00", CUT + "T00:30:00-08:00", CUT + "T01:00:00-08:00"
DAY_BEFORE_CUT = (datetime.date.fromisoformat(CUT) - datetime.timedelta(days=1)).isoformat()
S_F, S_G, S_R0 = ("bbbbbbbb-0000-4000-8000-0000000000%02d" % i for i in (9, 10, 11))
AN = "Analysis: wwhtbt={w} 5whys={f} adversarial=" + M_REL + " uncovered=1"
POLICY = {"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$", "placeholders": ["none", "n/a", "tbd", "todo", "x"]}}
OUTAGE = "policy file not found"                       # the resolver's own text when the default policy file is missing (skill-route-resolve.py)
POLICY_ERROR = "{}: policy alternates entry 0 names no model (policy error, fail closed)"   # the resolver's policy-error form, per skill
INJECTED = "unknown decision_class '(policy error, fail closed)' for {} (known: plan)"     # R2's infix inside caller text the resolver quotes
FIXABLE = "evidence: placeholder ref refused (fixable request)"
LIVE = "live worker: session 0000 holds task A1 (one analysis per task)"


def sha(b):
    return hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()


CASES = {}


def case(name, rc, findings, check=None, ungov=False, detail=None):
    """detail: a substring one `FAIL <finding>` stderr line must carry (so a case cannot pass for another reason with the same id)."""
    def deco(fn):
        CASES[name] = {"fn": fn, "rc": rc, "findings": findings, "check": check, "ungov": ungov, "detail": detail}
        return fn
    return deco


def policy(out):
    with open(os.path.join(out, "policy.json"), "w", encoding="utf-8") as fh:
        json.dump(POLICY, fh)


def tfx(out, w="ran visions/wwhtbt.md", f="skipped: not a failure seed", failure="Failure: none"):
    """A covered (new-material) entry on the cutover: Task A1's first entry, so State: names foo for the first time."""
    fx = Fx(out)
    fx.ts, fx.failure = T_TS, failure
    fx.entry["Analysis"] = AN.format(w=w, f=f)
    return fx


def earlier(fx, seeds="Seeds: selftest", extra=()):
    """Give the entry an earlier entry of Task A1 that names foo with the same seeds (no new slug, no new seed)."""
    fx.prev_entry = "2026-11-15T00:30:00-08:00"            # before the fixture matrix (M_REL, 01:00), as the selftest's uncovered case
    fx.prev_lines = ["Task: A1   Consumer: hermes", seeds, "State: foo=linted"] + list(extra)
    return fx


def denied(skill, reasons, ts=OUT_TS, task="A1"):
    return row(ts, "denied", task, skill, "opus-xhigh", "claude-opus-5-5", "xhigh", "", reasons=reasons)


def later(skill, ts=LATE_TS, task="A9", session=S_F):
    return row(ts, "launch", task, skill, "opus-xhigh", "claude-opus-5-5", "xhigh", session)


def review_row(ts, session, task="A1"):
    return row(ts, "launch", task, "dream", "opus-xhigh", "claude-opus-5-5", "xhigh", session, role="review")


# ---------------------------------------------------------------- AC 2: R1 triggers x R2 skips
def trig_new_slug(out, w):
    return tfx(out, w=w)


def trig_drafted(out, w):
    fx = earlier(tfx(out, w=w))
    fx.entry["State"] = "State: foo=drafted foo=linted foo=reviewed:APPROVE"
    return fx


def trig_seed(out, w):
    fx = earlier(tfx(out, w=w))
    fx.seeds = "Seeds: selftest ticket:A1-follow-up"
    return fx


def trig_snapshot(out, w):
    """The newest manifest an earlier entry of the Task binds through its reviewer's review.snapshot pins PRD-foo.md at other bytes."""
    fx = earlier(tfx(out, w=w), extra=[f"Review: notes/reviews/r0.txt reviewer-session={S_R0}"])
    fx.files["notes/reviews/r0.txt"] = f"reviewer session {S_R0}\nfoo APPROVE opus\n"
    fx.files["notes/snapshots/s0/s0.sha256"] = f"{sha('# foo stub, as reviewed\n')}  PRD-foo.md\n"
    fx.rows.append(dict(review_row(CUT + "T00:05:00-08:00", S_R0), scope="notes/snapshots/s0/s0.sha256",
                        scope_id=scope_id(fx.files["notes/snapshots/s0/s0.sha256"])))
    return fx


def drfc_mission(out, variant, w):
    """The checked-in drfc mission (Task FC-1), its copy re-dated from DRFC_DAY onto the cutover day (so after the cutover, R7): its last
    entry with the wwhtbt value `w` and a Failure: line."""
    home = os.path.join(out, "home")
    shutil.copytree(os.path.join(DRFC, "home"), home)
    dec = os.path.join(DRFC, "decisions.jsonl")
    if variant != "base":
        shutil.copytree(os.path.join(DRFC, "variants", variant, "home"), home, dirs_exist_ok=True)
        dec = os.path.join(DRFC, "variants", variant, "decisions.jsonl")
    shutil.copy(dec, os.path.join(out, "decisions.jsonl"))
    p = subprocess.run([sys.executable, "-I", REDATE, "--map", f"{DRFC_DAY}={CUT}", "--also", os.path.join(out, "decisions.jsonl"), home],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit("drfc fixture: re-date onto the cutover day failed: " + (p.stderr or p.stdout).strip())
    log = os.path.join(home, "notes", "dream-log.md")
    lines = open(log, encoding="utf-8").read().split("\n")
    last = max(i for i, ln in enumerate(lines) if ln.startswith("## "))
    for i in range(last, len(lines)):
        if lines[i].startswith("Analysis: wwhtbt="):
            rest = lines[i].split(" 5whys=", 1)[1]
            lines[i] = f"Analysis: wwhtbt={w} 5whys={rest}"
            lines.insert(i + 1, "Failure: none")
            break
    else:
        raise SystemExit("drfc fixture: no Analysis: line in the last entry")
    # finding consumption R7: a covered entry's WWHTBT skip counts as an unbound falsifier, which holds the mission's first PRDs, so a re-dated
    # mission whose entries skip WWHTBT stops before `eligible` (the hold itself is dfcn AC 4's case); these cases test the skip, not eligibility
    for i in range(last, len(lines)):
        if lines[i].startswith("State:"):
            lines[i] = "State:" + "".join(" " + t for t in lines[i][len("State:"):].split() if not t.endswith("=eligible"))
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return None


M_OUT, M_LATE = CUT + "T12:00:00-08:00", CUT + "T12:30:00-08:00"      # after every row of the re-dated mission copy


def add_rows(out, rows):
    with open(os.path.join(out, "decisions.jsonl"), "a", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(r) + "\n" for r in rows))


SKIPS = {  # skip kind -> (wwhtbt value, rows to add (Fx cases), rows to add (mission cases), refused?, ungoverned?)
    "outage": (f"skipped: blocked decision={OUT_TS}", [denied("wwhtbt", OUTAGE)], [denied("wwhtbt", OUTAGE, M_OUT, "FC-1")], False, False),
    "outage-later-launch": (f"skipped: blocked decision={OUT_TS}", [denied("wwhtbt", OUTAGE), later("wwhtbt")],
                            [denied("wwhtbt", OUTAGE, M_OUT, "FC-1"), later("wwhtbt", M_LATE)], True, False),
    "fixable": (f"skipped: blocked decision={OUT_TS}", [denied("wwhtbt", FIXABLE)], [denied("wwhtbt", FIXABLE, M_OUT, "FC-1")], True, False),
    "live-worker": (f"skipped: blocked decision={OUT_TS}", [denied("wwhtbt", LIVE)], [denied("wwhtbt", LIVE, M_OUT, "FC-1")], True, False),
    "other-task": (f"skipped: blocked decision={OUT_TS}", [denied("wwhtbt", OUTAGE, task="A9")], [denied("wwhtbt", OUTAGE, M_OUT, "A9")], True, False),
    "free-text": ("skipped: a wiki page would be outside this task's scope", [], [], True, False),
    "no-log": (f"skipped: blocked decision={OUT_TS}", [denied("wwhtbt", OUTAGE)], [denied("wwhtbt", OUTAGE, M_OUT, "FC-1")], True, True),
}
TRIGGERS = {"new-slug": ("new-material", trig_new_slug), "drafted": ("new-material", trig_drafted), "seed": ("new-material", trig_seed),
            "snapshot": ("new-material", trig_snapshot), "mission": ("mission", "base"), "mission-amended": ("mission", "amended")}


def _ac02(trig, skip):
    kind, how = TRIGGERS[trig]
    w, rows_fx, rows_m, refused, ungov = SKIPS[skip]
    if kind == "mission":
        w = w.replace(OUT_TS, M_OUT)

    def build(out):
        if kind == "mission":
            drfc_mission(out, how, w)
            add_rows(out, rows_m)
        else:
            fx = how(out, w)
            fx.rows += rows_fx
            if ungov:
                fx.entry["Route"] = "Route: ungoverned session=%s host=datr-fixture" % H["S_D"]   # today's grammar; a governed Route: with no log exits 2
            fx.build()
        policy(out)
    want = ["analysis-skip-refused"] if refused else []
    chk = f"d['analysis'].get('covered') == {kind!r}"
    return build, (1 if refused else 0), want, chk, ungov


for _t in TRIGGERS:
    for _s in SKIPS:
        if _s == "no-log" and _t in ("mission", "mission-amended", "snapshot"):
            continue          # without a decisions log no review launch row binds a snapshot or a mission chain; the other triggers carry the no-log case
        b, rc, want, chk, ug = _ac02(_t, _s)
        case(f"ac02-{_t}-{_s}", rc, want, chk, ug)(b)


@case("ac02-uncovered-free-text", 0, [], "d['analysis'].get('covered') == 'none'")
def _(out):
    fx = earlier(tfx(out, w="skipped: nothing new to plan"))
    fx.build()
    policy(out)


@case("ac02-uncovered-no-failure-line", 0, [], "d['analysis'].get('covered') == 'none' and d['analysis'].get('failure') is None")
def _(out):
    fx = earlier(tfx(out, w="skipped: nothing new to plan", failure=None))
    fx.build()
    policy(out)


# Follow-up cases from the independent reviews of c2525a2 (code 88ec4f26, security ddf46516, behaviour 96397ae0); each fails at c2525a2
def skip_fx(out, reasons, w=f"skipped: blocked decision={OUT_TS}", rows=()):
    fx = tfx(out, w=w)
    fx.rows += [denied("wwhtbt", reasons)] + list(rows)
    fx.build()
    policy(out)


FREE = "skipped: a wiki page would be outside this task's scope"
case("ac02-outage-resolver-policy-error-form", 0, [])(lambda out: skip_fx(out, POLICY_ERROR.format("wwhtbt")))
case("ac02-outage-infix-in-caller-text", 1, ["analysis-skip-refused"], detail="not a route outage")(lambda out: skip_fx(out, INJECTED.format("wwhtbt")))
case("ac02-outage-policy-missing-caller-env", 1, ["analysis-skip-refused"], detail="not a route outage")(
    lambda out: skip_fx(out, "policy-missing: SKILL_ROUTE_POLICY names no readable file"))
case("ac02-outage-policy-missing-caller-arg", 1, ["analysis-skip-refused"], detail="not a route outage")(
    lambda out: skip_fx(out, "policy-missing: --policy names no readable file"))
# R2 as amended (Hermes H2, 2026-11-19): each of the resolver's own outage texts, whole, is accepted; near misses are not.
for _n, _r in (("policy-is-malformed", "policy is malformed"), ("malformed-policy-json", "malformed policy JSON: JSONDecodeError"),
               ("ledger-lookup-unavailable", "ledger lookup unavailable; cannot verify ledger:A1 (fail closed)"),
               ("require-permission-mode", "wwhtbt: policy require_permission_mode must be a non-empty string (fail closed)")):
    case("ac02-outage-text-" + _n, 0, [])((lambda r: lambda out: skip_fx(out, r))(_r))
for _n, _r in (("policy-missing-other", "policy-missing: datr fixture"), ("malformed-request-json", "malformed request JSON: JSONDecodeError"),
               ("malformed-policy-prefix", "malformed policy: expected object"),
               ("ledger-lookup-extra", "ledger lookup unavailable; cannot verify ledger:A1 (fail closed) after a PATH change"),
               ("require-permission-mode-other-skill", "dream: policy require_permission_mode must be a non-empty string (fail closed)"),
               ("white-space-around", " policy file not found\n"),                                       # review r10 LOW-1: whole, unstripped
               ("ledger-id-outside-grammar", "ledger lookup unavailable; cannot verify ledger:a(b (fail closed)")):   # LOW-2: the resolver's id grammar
    case("ac02-outage-near-miss-" + _n, 1, ["analysis-skip-refused"], detail="not a route outage")((lambda r: lambda out: skip_fx(out, r))(_r))


# R2 as amended for chain review 11 (R11-F5): AC 2 and AC 5 test each R2-accepted text, corroborated and not, and each R2-refused text one by one;
# AC 2 also lints an uncovered entry skipping on each accepted text (uncovered entries keep today's rules).
R2_ACCEPTED = (("policy-file-not-found", "policy file not found"), ("malformed-policy-json", "malformed policy JSON: JSONDecodeError"),
               ("policy-is-malformed", "policy is malformed"), ("policy-error-form", POLICY_ERROR),
               ("require-permission-mode", "{}: policy require_permission_mode must be a non-empty string (fail closed)"),
               ("ledger-lookup-unavailable", "ledger lookup unavailable; cannot verify ledger:A1 (fail closed)"))
R2_REFUSED = (("policy-missing-env", "policy-missing: SKILL_ROUTE_POLICY names no readable file"),
              ("policy-missing-arg", "policy-missing: --policy names no readable file"),
              ("unanchored-policy-error", INJECTED), ("malformed-request-json", "malformed request JSON: JSONDecodeError"))


def uncovered_skip(out, reasons, rows=()):
    fx = earlier(tfx(out, w=f"skipped: blocked decision={OUT_TS}"))
    fx.rows += [denied("wwhtbt", reasons)] + list(rows)
    fx.build()
    policy(out)


for _n, _r in R2_ACCEPTED:
    case("ac02-r2-accepted-%s-corroborated" % _n, 0, [])((lambda r: lambda out: skip_fx(out, r.format("wwhtbt")))(_r))
    case("ac02-r2-accepted-%s-uncorroborated" % _n, 1, ["analysis-skip-refused"], detail="falls between")(
        (lambda r: lambda out: skip_fx(out, r.format("wwhtbt"), rows=[later("wwhtbt")]))(_r))
    case("ac02-r2-accepted-%s-uncovered" % _n, 0, [], "d['analysis'].get('covered') == 'none'")((lambda r: lambda out: uncovered_skip(out, r.format("wwhtbt")))(_r))
    case("ac02-r2-accepted-%s-uncovered-uncorroborated" % _n, 0, [], "d['analysis'].get('covered') == 'none'")(       # review r13 MEDIUM-1
        (lambda r: lambda out: uncovered_skip(out, r.format("wwhtbt"), rows=[later("wwhtbt")]))(_r))
for _n, _r in R2_REFUSED:
    case("ac02-r2-refused-%s" % _n, 1, ["analysis-skip-refused"], detail="not a route outage")((lambda r: lambda out: skip_fx(out, r.format("wwhtbt")))(_r))
    case("ac02-r2-refused-%s-uncovered" % _n, 0, [], "d['analysis'].get('covered') == 'none'")((lambda r: lambda out: uncovered_skip(out, r.format("wwhtbt")))(_r))


@case("ac02-denial-after-header", 1, ["analysis-skip-refused"], detail="is not before the entry header")
def _(out):
    t = CUT + "T03:00:00-08:00"
    fx = tfx(out, w=f"skipped: blocked decision={t}")
    fx.rows += [denied("wwhtbt", OUTAGE, ts=t)]
    fx.build()
    policy(out)


case("ac02-launch-in-the-denial-second", 1, ["analysis-skip-refused"], detail="falls between")(lambda out: skip_fx(out, OUTAGE, rows=[later("wwhtbt", ts=OUT_TS)]))
case("ac02-launch-ts-unreadable", 1, ["analysis-skip-refused"], detail="has no ISO timestamp")(
    lambda out: skip_fx(out, OUTAGE, rows=[later("wwhtbt", ts=CUT + "T01:00:00")]))


@case("ac02-snapshot-unreadable", 1, ["analysis-skip-refused"], "d['analysis'].get('covered') == 'new-material'")
def _(out):
    fx = trig_snapshot(out, FREE)
    fx.files["notes/snapshots/s0/s0.sha256"] = None
    fx.build()
    policy(out)


@case("ac02-snapshot-not-its-scope-id", 1, ["analysis-skip-refused"], "d['analysis'].get('covered') == 'new-material'")
def _(out):
    fx = trig_snapshot(out, FREE)          # the row keeps the reviewed manifest's scope_id; the file now pins today's bytes
    fx.files["notes/snapshots/s0/s0.sha256"] = f"{sha('# foo stub' + chr(10))}  PRD-foo.md\n"
    fx.build()
    policy(out)


@case("ac02-backdated-header-route-after-cutover", 1, ["analysis-skip-refused"], "d['analysis'].get('covered') == 'new-material'")
def _(out):
    fx = tfx(out, w=FREE)
    fx.ts = DAY_BEFORE_CUT + "T23:59:00-08:00"                # the last minute before the cutover day
    dts = CUT + "T00:10:00-08:00"
    fx.entry["Route"] = f"Route: fable-xhigh claude-fable-5-1 xhigh session={H['S_D']} decision={dts}"
    fx.rows.append(row(dts, "launch", "A1", "dream", "fable-xhigh", "claude-fable-5-1", "xhigh", H["S_D"]))
    fx.build()
    policy(out)


@case("ac02-header-without-a-readable-date", 1, ["analysis-skip-refused"], "d['analysis'].get('covered') == 'new-material'")
def _(out):
    fx = tfx(out, w=FREE)
    fx.ts = "2026-0x-25T02:00:00-08:00"          # sorts before the cutover as text, yet names no date: R7 cannot place it before the cutover
    fx.build()
    policy(out)


@case("ac02-header-date-not-zero-padded", 1, ["analysis-skip-refused"], "d['analysis'].get('covered') == 'new-material'")
def _(out):
    fx = tfx(out, w=FREE)
    fx.ts = "2026-1-25T02:00:00-08:00"            # no zero-padded date: R7 cannot place it before the cutover (date never writes this form)
    fx.build()
    policy(out)


@case("ac02-snapshot-row-without-scope-id", 1, ["analysis-skip-refused"], "d['analysis'].get('covered') == 'new-material'")
def _(out):
    fx = trig_snapshot(out, FREE)                # the row has no scope_id, and the file now pins today's bytes
    fx.rows[-1] = {k: v for k, v in fx.rows[-1].items() if k != "scope_id"}
    fx.files["notes/snapshots/s0/s0.sha256"] = f"{sha('# foo stub' + chr(10))}  PRD-foo.md\n"
    fx.build()
    policy(out)


@case("ac02-sloppy-earlier-header-keeps-today", 0, [], "d['analysis'] is not None and 'covered' not in d['analysis']")
def _(out):
    fx = tfx(out, w=FREE)
    fx.ts = "2026-11-12T03:4x-0800"              # a real header form: its date is before the cutover, so today's rules apply
    fx.build()
    policy(out)


Z64 = "0" * 64
case("ac02-uncovered-wwhtbt-reused-extended", 1, ["analysis-grammar"], "d['analysis'].get('covered') == 'none'", detail="wwhtbt value 'reused")(
    lambda out: (lambda fx: (fx.files.__setitem__("visions/wwhtbt.md", f"# wwhtbt page\ntask: A1\nsession: {S_W}\n" + FXF),
                             fx.entry.__setitem__("Analysis", AN.format(w=f"reused visions/wwhtbt.md sha256={Z64} inputs=notes/none.sha256", f="skipped: x")),
                             fx.build(), policy(out)))(earlier(tfx(out, failure=None))))
case("ac02-uncovered-5whys-reused", 1, ["analysis-grammar"], "d['analysis'].get('covered') == 'none'", detail="5whys value 'reused")(
    lambda out: (lambda fx: (fx.build(), policy(out)))(earlier(tfx(out, w="skipped: nothing new to plan", f=f"reused visions/nope.md sha256={Z64}", failure=None))))
case("ac02-uncovered-failure-line-not-read", 0, [], "d['analysis'].get('covered') == 'none' and d['analysis'].get('failure') is None")(
    lambda out: (lambda fx: (fx.build(), policy(out)))(earlier(tfx(out, w="skipped: nothing new to plan", failure="Failure: flaky"))))


# ---------------------------------------------------------------- AC 3: R3 exact reuse
def reuse(out, page_sha=None, edit_page=None, edit_input=None, manifest="ok", seed=False, bound=True, inputs="notes/inputs/manifest.sha256"):
    fx = tfx(out)
    ext = os.path.join(out, "external", "cited.txt")             # an absolute path the page cites, outside the home
    os.makedirs(os.path.dirname(ext), exist_ok=True)
    with open(ext, "w", encoding="utf-8") as fh:
        fh.write("external input\n")
    page = (f"# wwhtbt page\ntask: A1\nsession: {S_W if bound else S_G}\n"
            f"cites file:notes/inputs/a.txt and {ext}, and the directory {out}/external/\n" + FXF)
    fx.files["visions/wwhtbt.md"] = page
    fx.files["notes/inputs/a.txt"] = "input a\n"
    lines = [f"{sha('input a' + chr(10))}  a.txt", f"{sha('external input' + chr(10))}  {ext}"]
    if seed:
        fx.files["notes/seed.md"] = "seed text\n"
        fx.seeds = f"Seeds: file:notes/seed.md sha256={sha('seed text' + chr(10))}"
        if seed == "listed":
            lines.append(f"{sha('seed text' + chr(10))}  ../seed.md")
    if manifest == "omit-cited":
        lines = lines[1:]
    fx.files["notes/inputs/manifest.sha256"] = {"ok": "\n".join(lines) + "\n", "omit-cited": "\n".join(lines) + "\n", "empty": "", "absent": None}[manifest]
    fx.entry["Analysis"] = AN.format(w=f"reused visions/wwhtbt.md sha256={page_sha or sha(page)} inputs={inputs}", f="skipped: not a failure seed")
    fx.build()
    if edit_page:
        with open(os.path.join(fx.home, "visions", "wwhtbt.md"), "a", encoding="utf-8") as fh:
            fh.write("one byte more\n")
        fx.write_consumption()         # the record re-binds the moved page, so only the reuse digest is stale (this AC's rule)
    if edit_input == "home":
        with open(os.path.join(fx.home, "notes", "inputs", "a.txt"), "a", encoding="utf-8") as fh:
            fh.write("moved\n")
    if edit_input == "absolute":
        with open(ext, "a", encoding="utf-8") as fh:
            fh.write("moved\n")
    policy(out)
    return fx


case("ac03-verified", 0, [], "d['analysis']['reuse']['verified'] is True and d['analysis']['covered'] == 'new-material'")(lambda out: reuse(out))
case("ac03-verified-with-seed", 0, [], "d['analysis']['reuse']['verified'] is True")(lambda out: reuse(out, seed="listed"))
case("ac03-page-byte-moved", 1, ["analysis-reuse-stale"], detail="differs from the recorded sha256=")(lambda out: reuse(out, edit_page=True))
case("ac03-home-input-moved", 1, ["analysis-reuse-stale"], detail="sha256sum -c")(lambda out: reuse(out, edit_input="home"))
case("ac03-absolute-input-moved", 1, ["analysis-reuse-stale"], detail="sha256sum -c")(lambda out: reuse(out, edit_input="absolute"))
case("ac03-omits-cited-path", 1, ["analysis-reuse-incomplete"], detail="notes/inputs/a.txt")(lambda out: reuse(out, manifest="omit-cited"))
case("ac03-omits-seed", 1, ["analysis-reuse-incomplete"], detail="notes/seed.md")(lambda out: reuse(out, seed="unlisted"))
case("ac03-manifest-absent", 1, ["analysis-grammar"], detail="absent or empty")(lambda out: reuse(out, manifest="absent"))
case("ac03-manifest-empty", 1, ["analysis-grammar"], detail="absent or empty")(lambda out: reuse(out, manifest="empty"))
case("ac03-manifest-outside-home", 1, ["analysis-grammar"], detail="is not under the PRD home")(lambda out: reuse(out, inputs="../elsewhere.sha256"))
case("ac03-page-unbound", 1, ["analysis-provenance-missing"], "d['analysis']['reuse']['verified'] is False")(lambda out: reuse(out, bound=False))


@case("ac03-no-inputs", 1, ["analysis-grammar"], detail="reused <page> sha256=<64 hex> inputs=<manifest>")
def _(out):
    reuse(out)
    log = os.path.join(out, "home", "notes", "dream-log.md")
    t = open(log, encoding="utf-8").read()
    i = t.index(" inputs=notes/inputs/manifest.sha256")
    t = t[:i] + t[i + len(" inputs=notes/inputs/manifest.sha256"):]
    i = t.index(" sha256=", t.index("wwhtbt=reused"))
    t = t[:i] + t[i + len(" sha256=") + 64:]
    open(log, "w", encoding="utf-8").write(t)


def reuse_cites(out, extra):
    """An exact reuse whose page also cites `extra`, which the manifest does not list."""
    fx = reuse(out)
    p = os.path.join(out, "home", "visions", "wwhtbt.md")
    page = open(p, encoding="utf-8").read() + extra + "\n"
    open(p, "w", encoding="utf-8").write(page)
    fx.write_consumption()             # the record re-binds the edited page (finding consumption R1), as the reuse digest below does
    log = os.path.join(out, "home", "notes", "dream-log.md")
    t = open(log, encoding="utf-8").read()
    i = t.index("sha256=", t.index("wwhtbt=reused")) + len("sha256=")
    open(log, "w", encoding="utf-8").write(t[:i] + sha(page) + t[i + 64:])


case("ac03-omits-home-relative-citations", 1, ["analysis-reuse-incomplete"], detail="Notes/wiki/goal.md")(
    lambda out: reuse_cites(out, "it also reads ~/Notes/wiki/goal.md and $HOME/inputs/b.md"))
case("ac03-cites-a-path-not-on-this-host", 1, ["analysis-reuse-incomplete"], detail="not files on this host")(
    lambda out: reuse_cites(out, "it also reads /var/lib/datr-nowhere/state.db on another host"))


# ---------------------------------------------------------------- AC 4: R4 Failure: line and its floor
PAGE5 = "page visions/5whys.md"


def fail_fx(out, failure, f="skipped: not a failure seed", reviews=(), named=True):
    """reviews: (file under notes/reviews, verdict text, session, task); each session gets a dream review launch row after the Task's previous entry."""
    fx = tfx(out, f=f, failure=failure)
    lines, verdicts = [], []
    for k, (rel, text, sess) in enumerate(reviews):
        fx.files[rel] = text
        r = review_row(CUT + "T01:%02d:00-08:00" % (10 + k), sess)
        if named and rel.endswith(".txt"):         # a Review: line names it: today's scope (R4/R5) and verdict rules apply to it too
            man = f"notes/snapshots/rv{k}/rv{k}.sha256"
            fx.files[man] = f"{sha('# foo stub' + chr(10))}  PRD-foo.md\n"
            r = dict(r, scope=man, scope_id=scope_id(fx.files[man]))
            lines.append(f"Review: {rel} reviewer-session={sess}")
            verdicts += [v[1] for v in (H["verdict_of"](x) for x in text.split("\n")) if v]
        fx.rows.append(r)
    if lines:
        fx.entry["Review"] = lines
        fx.entry["State"] = "State: foo=linted " + " ".join(f"foo=reviewed:{v}" for v in verdicts)   # one token per named verdict (today's rule)
    fx.build()
    policy(out)


def scope_id(text):
    """The row's scope_id: the lint's own canonical scope hash (scope_canon) of a manifest with this text."""
    with tempfile.NamedTemporaryFile("w", suffix=".sha256", delete=False, encoding="utf-8") as fh:
        fh.write(text)
    try:
        return H["scope_canon"](fh.name)[0]
    finally:
        os.unlink(fh.name)


for _c, _f in (("recurring-failure", PAGE5), ("failed-acceptance", PAGE5), ("consequential-obstacle", PAGE5), ("transient", "inline"), ("other", "skipped: not a failure seed")):
    case(f"ac04-class-{_c}", 0, [], f"d['analysis']['failure'] == {{'class': {_c!r}, 'refs': ['ledger:A1']}}")(
        (lambda c, f: lambda out: fail_fx(out, f"Failure: {c} ledger:A1", f=f))(_c, _f))
case("ac04-none", 0, [], "d['analysis']['failure'] == {'class': 'none', 'refs': []}")(lambda out: fail_fx(out, "Failure: none"))
case("ac04-unknown-class", 1, ["failure-grammar"])(lambda out: fail_fx(out, "Failure: flaky ledger:A1"))
case("ac04-class-without-ref", 1, ["failure-grammar"])(lambda out: fail_fx(out, "Failure: other"))
case("ac04-bad-ref", 1, ["failure-grammar"])(lambda out: fail_fx(out, "Failure: other A1-was-red"))
case("ac04-placeholder-ref", 1, ["failure-grammar"])(lambda out: fail_fx(out, "Failure: other file:tbd"))
case("ac04-no-failure-line", 1, ["line-missing"])(lambda out: fail_fx(out, None))
REJ = ("notes/reviews/v-reject.txt", f"reviewer session {S_F}\nfoo REJECT opus\n", S_F)
FIX1 = ("notes/reviews/v-fix-1.txt", f"reviewer session {S_F}\nfoo FIX opus\n", S_F)
FIX2 = ("notes/reviews/v-fix-2.txt", f"reviewer session {S_G}\nfoo FIX opus\n", S_G)
case("ac04-none-beside-reject-named", 1, ["failure-class-mismatch"])(lambda out: fail_fx(out, "Failure: none", reviews=[REJ]))
case("ac04-none-beside-reject-omitted", 1, ["failure-class-mismatch"])(lambda out: fail_fx(out, "Failure: none", reviews=[REJ], named=False))
case("ac04-other-beside-reject", 1, ["failure-class-mismatch"])(lambda out: fail_fx(out, "Failure: other ledger:A1", reviews=[REJ]))
case("ac04-failed-acceptance-beside-reject", 0, [])(lambda out: fail_fx(out, "Failure: failed-acceptance ledger:A1", f=PAGE5, reviews=[REJ]))
case("ac04-first-fix-is-no-floor", 0, [])(lambda out: fail_fx(out, "Failure: none", reviews=[FIX1]))
case("ac04-none-beside-second-fix-named", 1, ["failure-class-mismatch"])(lambda out: fail_fx(out, "Failure: none", reviews=[FIX1, FIX2]))
case("ac04-none-beside-second-fix-omitted", 1, ["failure-class-mismatch"])(lambda out: fail_fx(out, "Failure: none", reviews=[FIX1, FIX2], named=False))
case("ac04-failed-acceptance-beside-second-fix", 1, ["failure-class-mismatch"])(
    lambda out: fail_fx(out, "Failure: failed-acceptance ledger:A1", f=PAGE5, reviews=[FIX1, FIX2]))
case("ac04-recurring-beside-second-fix", 0, [])(lambda out: fail_fx(out, "Failure: recurring-failure ledger:A1", f=PAGE5, reviews=[FIX1, FIX2]))
case("ac04-none-beside-reject-in-result-json", 1, ["failure-class-mismatch"])(lambda out: fail_fx(out, "Failure: none", reviews=[
    ("notes/reviews/r9/result.json", json.dumps({"type": "result", "is_error": False, "session_id": S_F, "result": "foo REJECT opus"}), S_F)], named=False))
case("ac04-unbound-reject-is-no-floor", 0, [])(lambda out: fail_fx(out, "Failure: none", reviews=[
    ("notes/reviews/author-draft.txt", "foo REJECT opus\n", "cccccccc-0000-4000-8000-000000000099")], named=False))


@case("ac04-re-review-names-the-earlier-session", 0, [], "d['analysis']['failure'] == {'class': 'none', 'refs': []}")
def _(out):
    fx = tfx(out, failure="Failure: none")        # S_G's first FIX of foo; its file also names S_F (whose APPROVE it re-reviews)
    fx.files["notes/reviews/r1.txt"] = f"reviewer session {S_F}\nfoo APPROVE opus\n"
    fx.files["notes/reviews/r2.txt"] = f"reviewer session {S_G}\nre-review of notes/reviews/r1.txt (reviewer-session {S_F})\nfoo FIX opus\n"
    fx.rows += [review_row(CUT + "T01:10:00-08:00", S_F), review_row(CUT + "T01:20:00-08:00", S_G)]
    fx.build()
    policy(out)


@case("ac04-two-failure-lines", 1, ["failure-grammar"], detail="2 Failure: lines")
def _(out):
    fx = tfx(out, f=PAGE5, failure="Failure: recurring-failure ledger:A1")
    fx.tail = ["Failure: none"]
    fx.build()
    policy(out)


S_X = "bbbbbbbb-0000-4000-8000-000000000077"
REJ_NAMES_A9 = REJ[1].replace("\n", f"\nsee also the parallel review of A9, session {S_X}\n", 1)   # the REJECT file also names a later review of A9


def reject_names_other_task(out, covered):
    fx = tfx(out, failure="Failure: none") if covered else earlier(tfx(out, w=FREE, failure=None))
    fx.files[REJ[0]] = REJ_NAMES_A9
    fx.rows += [review_row(CUT + "T01:10:00-08:00", S_F), review_row(CUT + "T01:15:00-08:00", S_X, task="A9")]
    fx.build()
    policy(out)


case("ac04-reject-file-also-names-another-task-review", 1, ["failure-class-mismatch"])(lambda out: reject_names_other_task(out, True))
case("ac04-uncovered-reject-file-also-names-another-task-review", 1, ["line-missing"], detail="set the floor failed-acceptance")(
    lambda out: reject_names_other_task(out, False))


def uncovered_floor(out, failure, f="skipped: not a failure seed"):
    fx = earlier(tfx(out, w=FREE, f=f, failure=failure))
    fx.files[REJ[0]] = REJ[1]
    fx.rows.append(review_row(CUT + "T01:10:00-08:00", S_F))
    fx.build()
    policy(out)


case("ac04-uncovered-floor-needs-the-line", 1, ["line-missing"], "d['analysis'].get('covered') == 'none'", detail="set the floor failed-acceptance")(
    lambda out: uncovered_floor(out, None))
case("ac04-uncovered-floor-none", 1, ["failure-class-mismatch"], "d['analysis'].get('covered') == 'none'")(lambda out: uncovered_floor(out, "Failure: none"))
case("ac04-uncovered-floor-met", 0, [], "d['analysis']['failure']['class'] == 'failed-acceptance'")(
    lambda out: uncovered_floor(out, "Failure: failed-acceptance ledger:A1", f=PAGE5))


# ---------------------------------------------------------------- AC 5: R5 5whysandrhyme trigger
FIVE = f"# five whys page\nsession: {S_5}\n" + FXF


def five_fx(out, cls, f, rows=(), refs="ledger:A1", five_other_task=False):
    fx = tfx(out, f=f, failure=f"Failure: {cls} {refs}")
    if five_other_task:                          # the reused page is bound to another task's 5whysandrhyme launch row
        fx.files["visions/5whys-a7.md"] = f"# five whys page of A7\nsession: {S_G}\n" + FXF
        fx.rows.append(row(CUT + "T00:20:00-08:00", "launch", "A7", "5whysandrhyme", "opus-xhigh", "claude-opus-5-5", "xhigh", S_G))
    fx.rows += list(rows)
    fx.build()
    policy(out)


REUSED7 = f"reused visions/5whys-a7.md sha256={sha('# five whys page of A7' + chr(10) + 'session: ' + S_G + chr(10) + FXF)}"
for _c in ("recurring-failure", "failed-acceptance", "consequential-obstacle"):
    k = _c.split("-")[0]
    case(f"ac05-{k}-bound-page", 0, [])((lambda c: lambda out: five_fx(out, c, PAGE5))(_c))
    case(f"ac05-{k}-inline", 1, ["analysis-trigger-unmet"])((lambda c: lambda out: five_fx(out, c, "inline"))(_c))
    case(f"ac05-{k}-skip-corroborated", 0, [])((lambda c: lambda out: five_fx(out, c, f"skipped: blocked decision={OUT_TS}",
                                                                                 [denied("5whysandrhyme", POLICY_ERROR.format("5whysandrhyme"))]))(_c))
    case(f"ac05-{k}-skip-later-launch", 1, ["analysis-trigger-unmet"])((lambda c: lambda out: five_fx(out, c, f"skipped: blocked decision={OUT_TS}",
                                                                                                      [denied("5whysandrhyme", POLICY_ERROR.format("5whysandrhyme")),
                                                                                                       later("5whysandrhyme")]))(_c))
    case(f"ac05-{k}-skip-fixable", 1, ["analysis-trigger-unmet"])((lambda c: lambda out: five_fx(out, c, f"skipped: blocked decision={OUT_TS}",
                                                                                                 [denied("5whysandrhyme", FIXABLE)]))(_c))
    case(f"ac05-{k}-skip-live-worker", 1, ["analysis-trigger-unmet"])((lambda c: lambda out: five_fx(out, c, f"skipped: blocked decision={OUT_TS}",
                                                                                                     [denied("5whysandrhyme", LIVE)]))(_c))
    case(f"ac05-{k}-reuse-cited", 0, [])((lambda c: lambda out: five_fx(out, c, REUSED7, refs="ledger:A1 page:visions/5whys-a7.md", five_other_task=True))(_c))
    case(f"ac05-{k}-reuse-uncited", 1, ["analysis-trigger-unmet"])((lambda c: lambda out: five_fx(out, c, REUSED7, five_other_task=True))(_c))
    case(f"ac05-{k}-unbound-page", 1, ["analysis-page-unbound", "analysis-trigger-unmet"])((lambda c: lambda out: five_fx(out, c, "page visions/5whys-a7.md", five_other_task=True))(_c))
case("ac05-transient-inline", 0, [])(lambda out: five_fx(out, "transient", "inline", refs="run:retry-1"))
case("ac05-transient-skipped-transient", 0, [])(lambda out: five_fx(out, "transient", "skipped: transient", refs="run:retry-1"))
case("ac05-transient-page", 1, ["analysis-trigger-unmet"])(lambda out: five_fx(out, "transient", PAGE5, refs="run:retry-1"))


for _n, _r in R2_ACCEPTED:                       # R11-F5: each R2-accepted text, corroborated and not, and each R2-refused text, on the R5 trigger
    case("ac05-r2-accepted-%s-corroborated" % _n, 0, [])((lambda r: lambda out: five_fx(out, "failed-acceptance", f"skipped: blocked decision={OUT_TS}",
                                                                                          [denied("5whysandrhyme", r.format("5whysandrhyme"))]))(_r))
    case("ac05-r2-accepted-%s-uncorroborated" % _n, 1, ["analysis-trigger-unmet"], detail="falls between")((lambda r: lambda out: five_fx(
        out, "failed-acceptance", f"skipped: blocked decision={OUT_TS}", [denied("5whysandrhyme", r.format("5whysandrhyme")), later("5whysandrhyme")]))(_r))
for _n, _r in R2_REFUSED:
    case("ac05-r2-refused-%s" % _n, 1, ["analysis-trigger-unmet"], detail="not a route outage")((lambda r: lambda out: five_fx(
        out, "failed-acceptance", f"skipped: blocked decision={OUT_TS}", [denied("5whysandrhyme", r.format("5whysandrhyme"))]))(_r))


case("ac05-skip-infix-in-caller-text", 1, ["analysis-trigger-unmet"], detail="not a route outage")(
    lambda out: five_fx(out, "failed-acceptance", f"skipped: blocked decision={OUT_TS}", [denied("5whysandrhyme", INJECTED.format("5whysandrhyme"))]))


def five_reused_below_trigger(out, failure):
    fx = tfx(out, f=REUSED7, failure=failure)
    fx.files["visions/5whys-a7.md"] = f"# five whys page of A7\nsession: {S_G}\n" + FXF
    fx.rows.append(row(CUT + "T00:20:00-08:00", "launch", "A7", "5whysandrhyme", "opus-xhigh", "claude-opus-5-5", "xhigh", S_G))
    fx.build()
    policy(out)


case("ac05-none-takes-today-5whys", 1, ["analysis-grammar"], detail="5whys value 'reused")(lambda out: five_reused_below_trigger(out, "Failure: none"))
case("ac05-other-takes-today-5whys", 1, ["analysis-grammar"], detail="5whys value 'reused")(lambda out: five_reused_below_trigger(out, "Failure: other ledger:A1"))


# ---------------------------------------------------------------- AC 8: notes written as SKILL.md Phases 1-2 say lint clean
@case("ac08-page-under-notes-analysis", 0, [], "d['analysis']['covered'] == 'new-material'")
def _(out):
    fx = tfx(out, w="ran notes/analysis/wwhtbt.md")
    fx.files["notes/analysis/wwhtbt.md"] = f"# wwhtbt page\ntask: A1\nsession: {S_W}\n" + FXF
    fx.build()
    policy(out)


case("ac08-exact-reuse", 0, [], "d['analysis']['reuse']['verified'] is True")(lambda out: reuse(out, seed="listed"))


@case("ac08-recorded-outage-and-trigger-page", 0, [], "d['analysis']['failure']['class'] == 'failed-acceptance'")
def _(out):
    fx = tfx(out, w=f"skipped: blocked decision={OUT_TS}", f=PAGE5, failure="Failure: failed-acceptance ledger:A1 file:notes/reviews/v-reject.txt")
    fx.files["notes/reviews/v-reject.txt"] = f"reviewer session {S_F}\nfoo REJECT opus\n"
    fx.rows += [denied("wwhtbt", OUTAGE), review_row(CUT + "T01:10:00-08:00", S_F)]
    fx.build()
    policy(out)


@case("ac08-transient-inline", 0, [])
def _(out):
    five_fx(out, "transient", "inline", refs="run:retry-1")


# ---------------------------------------------------------------- five-whys page e784471d mechanism 3 (lint part): the R4 floor across the home
FS_S = ["bbbbbbbb-0000-4000-8000-0000000000%02d" % i for i in (12, 13, 14, 15)]
FS_BEFORE = "2026-11-14T2%d:00:00-08:00"                # launched before the Task's previous entry (earlier(): 2026-11-15T00:30)


def fs_floor(out, verdicts, failure, f="skipped: not a failure seed", slug="foo", when=None, task=None):
    """The A1723 home at its 2026-11-21T13:55:32 entry, in small: an uncovered entry of Task A1 whose previous entry came after every review
    session; `verdicts` are those sessions' verdicts of `slug` in launch order (one file each under notes/reviews/, bound by a dream review
    launch row). Before mechanism 3 only sessions launched after the previous entry set the floor, so these set none. `when` and `task`
    give a session's own launch time and Task (by index), for the sessions launched after the entry (the entry is dated T_TS)."""
    fx = earlier(tfx(out, w=FREE, f=f, failure=failure))
    for k, v in enumerate(verdicts):
        lines = "".join(f"{slug} {x} opus\n" for x in (v if isinstance(v, tuple) else (v,)))
        fx.files[f"notes/reviews/fs-{k}.txt"] = f"reviewer session {FS_S[k]}\n{lines}"
        fx.rows.append(review_row((when or {}).get(k, FS_BEFORE % k), FS_S[k], (task or {}).get(k, "A1")))
    fx.build()
    policy(out)


case("fs-four-fix-failure-none", 1, ["failure-class-mismatch"], "d['analysis'].get('covered') == 'none'",
     detail="4 consecutive FIX or REJECT since its last APPROVE")(lambda out: fs_floor(out, ["FIX"] * 4, "Failure: none"))
case("fs-four-fix-needs-the-line", 1, ["line-missing"], detail="set the floor recurring-failure")(lambda out: fs_floor(out, ["FIX"] * 4, None))
case("fs-four-fix-recurring-met", 0, [], "d['analysis']['failure']['class'] == 'recurring-failure'")(
    lambda out: fs_floor(out, ["FIX"] * 4, "Failure: recurring-failure ledger:A1", f=PAGE5))
case("fs-two-fix-failure-none", 1, ["failure-class-mismatch"], detail="2 consecutive FIX or REJECT")(
    lambda out: fs_floor(out, ["FIX", "FIX"], "Failure: none"))
case("fs-one-fix-is-no-floor", 0, [])(lambda out: fs_floor(out, ["FIX"], "Failure: none"))
case("fs-approve-ends-the-streak", 0, [])(lambda out: fs_floor(out, ["FIX", "FIX", "APPROVE"], "Failure: none"))
case("fs-fix-after-approve-is-one", 0, [])(lambda out: fs_floor(out, ["FIX", "APPROVE", "FIX"], "Failure: none"))
case("fs-reject-failure-none", 1, ["failure-class-mismatch"], detail="1 consecutive FIX or REJECT")(
    lambda out: fs_floor(out, ["REJECT"], "Failure: none"))
case("fs-reject-failed-acceptance-met", 0, [], "d['analysis']['failure']['class'] == 'failed-acceptance'")(
    lambda out: fs_floor(out, ["REJECT"], "Failure: failed-acceptance ledger:A1", f=PAGE5))
case("fs-fix-beside-approve-counts-as-fix", 1, ["failure-class-mismatch"], detail="2 consecutive FIX or REJECT")(
    lambda out: fs_floor(out, [("APPROVE", "FIX"), "FIX"], "Failure: none"))
FS_AFTER = CUT + "T03:00:00-08:00"                     # an hour after the entry (T_TS)
case("fs-later-approve-keeps-the-floor", 1, ["failure-class-mismatch"], detail="2 consecutive FIX or REJECT")(
    lambda out: fs_floor(out, ["FIX", "FIX", "APPROVE"], "Failure: none", when={2: FS_AFTER}))
case("fs-later-fix-is-not-in-the-streak", 0, [])(
    lambda out: fs_floor(out, ["FIX", "FIX"], "Failure: none", when={1: FS_AFTER}, task={1: "A9"}))
case("fs-other-slug-is-no-floor", 0, [])(lambda out: fs_floor(out, ["FIX", "FIX"], "Failure: none", slug="bar"))


# ---------------------------------------------------------------- five-whys page e784471d mechanism 2: a round's control reads carry mutant reports
CM_TS, CM_EARLY = "2026-11-21T20:00:00-08:00", "2026-11-21T12:00:00-08:00"      # after and before the page's write time
assert H.get("CONTROL_MUTANTS_SINCE") in (None, "2026-11-21T18:13:00-08:00"), H.get("CONTROL_MUTANTS_SINCE")  # None: a lint before it
S_R1, S_R2 = H["S_R1"], H["S_R2"]
CM_SCRIPT = sha("#!/usr/bin/env python3\n# stand-in for chain review 23's control script\n")
CM_TOOL = sha("#!/usr/bin/env python3\n# stand-in for mechanism 1's mutant runner\n")
CM_R23 = (f"# r23-controls.py controls <prd home> (stand-in for the A1723 chain review 23 repair controls)\n"
          f"#   {CM_SCRIPT}  notes/controls-r13/r23-controls.py\n"
          "OK   unit: the read names the unit it holds\nOK   qualifier: the read names its qualifier\nOK   pairing: five negatives refuse\n")
CM_R27 = (f"# script r27-controls.py sha256 {CM_SCRIPT}\n# r27-controls.py controls <prd home> (stand-in)\n"
          f"#   {CM_SCRIPT}  notes/controls-r13/r27-controls.py (script)\nOK   unit\n")


CM_CERT = "every mutant KILLED; the REVIEW-REQUEST may go out"
CM_META = ("\n## meta-negative: the same mutants against notes/controls-r13/r22-controls.py (stand-in), which must leave survivors\n"
           "r22-controls.py: 2 mutants, 2 SURVIVED -> as required\n    SURVIVED against r22-controls.py: M5 | unit\n"
           "    SURVIVED against r22-controls.py: M8 | qualifier\n")


def cm_report(sha_under_test=CM_SCRIPT, survived=0, summary=True, extra="", cert=CM_CERT):
    """A mechanism-1-shaped report of the stand-in r23 control: M5 and M8 (the page's R24-F1 swaps) KILLED, or M8 SURVIVED;
    `extra` lines go before the summary, then the summary and certificate lines as control-mutants-r27.py writes them."""
    rows = "KILLED   M5 | unit: two identities swapped\n" + ("SURVIVED M8 | qualifier: two identities swapped\n" if survived else
                                                              "KILLED   M8 | qualifier: two identities swapped\n")
    return (f"# script control-mutants.py sha256 {CM_TOOL}\n# control-mutants.py run <prd home> --control notes/controls-r13/r23-controls.py (stand-in)\n"
            f"#   {sha_under_test}  notes/controls-r13/r23-controls.py (the control under test)\n{rows}\n"
            + extra + (f"mutants: 2; KILLED: {2 - survived}; SURVIVED: {survived}\n" if summary else "")
            + (f"certificate: {cert}\n" if cert else ""))


def cm_fx(out, members, prev=None, ts=CM_TS, unlisted=None, declare=None):
    """A mission (the selftest's chain shape) whose Mission: line lists one manifest, notes/snapshots/m1/m.sha256 (reviewed by S_R1), or
    with `prev` two (m0 reviewed by S_R1, then m1 by S_R2); each freezes foo, bar, the matrix and the edges file, and `members` (for m1)
    or `prev` (for m0), {basename: text}, copied into its own directory as a round freeze holds them. `unlisted`: files written into m1's
    directory but not listed; `declare`: names a repairs row declares changed from m0 to m1 (the row, its file listed in m1 and the
    repairs= token, as the selftest's chain() writes them). The entry is a covered one dated `ts`."""
    fx = Fx(out)
    rep_text = None
    if declare:
        rep_text = json.dumps({"finding": None, "class": None, "author_session": H["S_D"], "before": "notes/snapshots/m0/m.sha256",
                               "after": "notes/snapshots/m1/m.sha256", "changed": list(declare), "sweep": ["E1"],
                               "disposition": "amended", "reason": "the control re-run on the repaired bytes"}) + "\n"
        fx.files["notes/missions/selftest.repairs.jsonl"] = rep_text
        members = dict(members, **{"selftest.repairs.jsonl": rep_text})
    fx.ts, fx.failure = ts, "Failure: none"
    fx.entry["Analysis"] = AN.format(w="ran visions/wwhtbt.md", f="skipped: not a failure seed")
    edges = H["mission_edges"](["foo", "bar"], known_only=True)
    fx.files.update({M_REL: H["mx_file"](["foo", "bar"]), "notes/missions/selftest.edges.jsonl": edges})
    mxb = os.path.basename(M_REL)

    def freeze(d, extra):
        fx.files.update({f"{d}/selftest.edges.jsonl": edges, f"{d}/{mxb}": fx.files[M_REL]})
        fx.files.update({f"{d}/{b}": t for b, t in extra.items()})
        text = (f"{sha('# foo stub' + chr(10))}  PRD-foo.md\n{sha('# bar stub' + chr(10))}  PRD-bar.md\n{sha(fx.files[M_REL])}  {mxb}\n"
                f"{sha(edges)}  selftest.edges.jsonl\n" + "".join(f"{sha(t)}  {b}\n" for b, t in extra.items()))
        fx.files[f"{d}/m.sha256"] = text
        return f"{d}/m.sha256", text
    mans = ([freeze("notes/snapshots/m0", prev)] if prev is not None else []) + [freeze("notes/snapshots/m1", members)]
    for b, t in (unlisted or {}).items():
        fx.files[f"notes/snapshots/m1/{b}"] = t
    fx.rows[3] = dict(fx.rows[3], role="author", scope="", scope_id="")
    lines, states = [], []
    for k, ((p, text), s) in enumerate(zip(mans, (S_R1, S_R2))):
        fx.rows[4 + k] = dict(fx.rows[4 + k], role="review", scope=p, scope_id=scope_id(text))
        v = f"foo APPROVE fable\nbar APPROVE fable\nmission=APPROVE {s}\n"
        fx.files[f"notes/reviews/cm{k}.txt"] = v
        fx.files[f"notes/reviews/cm{k}.json"] = json.dumps({"type": "result", "is_error": False, "session_id": s, "result": "Done.\n" + v})
        lines.append(f"Review: notes/reviews/cm{k}.txt reviewer-session={s} result=notes/reviews/cm{k}.json")
        states += ["foo=reviewed:APPROVE", "bar=reviewed:APPROVE"]
    fx.entry["Review"] = lines
    fx.entry["State"] = "State: " + " ".join(states)
    fx.tail = ["Mission: selftest edges=notes/missions/selftest.edges.jsonl scope=" + ",".join(p for p, _ in mans)
               + (" repairs=notes/missions/selftest.repairs.jsonl" if rep_text else "")]
    fx.build()
    policy(out)


CM = "d['mission']['control_mutants']"
case("cm-r23-alone-refused", 1, ["control-mutants-missing"], f"{CM}['missing'] == ['r23-controls.txt']",
     detail="no mutant report there names that script sha256")(lambda out: cm_fx(out, {"r23-controls.txt": CM_R23}))
case("cm-r23-with-killing-report", 0, [],
     f"{CM}['checked'] == [{{'control': 'r23-controls.txt', 'scripts': [['r23-controls.py', {CM_SCRIPT!r}]]}}] and {CM}['missing'] == [] "
     f"and {CM}['survived'] == []")(lambda out: cm_fx(out, {"r23-controls.txt": CM_R23, "r23-control-mutants.txt": cm_report()}))
case("cm-report-survived", 1, ["control-mutant-survived"], f"{CM}['survived'][0]['survived'] == 1", detail="reports SURVIVED: 1 of 2 mutants")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23, "r23-control-mutants.txt": cm_report(survived=1)}))
case("cm-report-without-summary", 1, ["control-mutant-survived"], detail="has no `mutants: N; KILLED: K; SURVIVED: S` summary line")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23, "r23-control-mutants.txt": cm_report(summary=False)}))
case("cm-report-survived-row", 1, ["control-mutant-survived"], f"{CM}['survived'][0]['rows'] == 1", detail="holds 1 SURVIVED row")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23,
                            "r23-control-mutants.txt": cm_report(extra="SURVIVED M12 | pairing: a negative dropped\n")}))
case("cm-report-meta-survivors-are-required", 0, [], f"{CM}['survived'] == []")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23, "r23-control-mutants.txt": cm_report(extra=CM_META)}))
case("cm-report-refusing-certificate", 1, ["control-mutant-survived"], detail="NO REVIEW-REQUEST, NO FREEZE")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23, "r23-control-mutants.txt": cm_report(
        cert="SURVIVED mutants or named mutants not applied; NO REVIEW-REQUEST, NO FREEZE")}))
case("cm-report-of-other-bytes", 1, ["control-mutants-missing"])(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23, "r23-control-mutants.txt": cm_report(sha_under_test=CM_TOOL)}))
case("cm-report-not-listed", 1, ["control-mutants-missing"])(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23}, unlisted={"r23-control-mutants.txt": cm_report()}))
case("cm-script-header-alone", 1, ["control-mutants-missing"], detail="(script r27-controls.py sha256")(
    lambda out: cm_fx(out, {"r27-controls.txt": CM_R27}))
case("cm-script-header-with-report", 0, [], f"{CM}['checked'][0]['scripts'] == [['r27-controls.py', {CM_SCRIPT!r}]]")(
    lambda out: cm_fx(out, {"r27-controls.txt": CM_R27, "r27-control-mutants.txt": cm_report()}))
case("cm-unchanged-since-previous-manifest", 0, [], f"{CM}['checked'] == []")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23}, prev={"r23-controls.txt": CM_R23}))
case("cm-changed-undeclared", 1, ["control-mutants-missing", "repair-hash-mismatch"])(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23 + "OK   one more read\n"}, prev={"r23-controls.txt": CM_R23}))
case("cm-changed-declared-needs-report", 1, ["control-mutants-missing"], f"{CM}['missing'] == ['r23-controls.txt']")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23 + "OK   one more read\n"}, prev={"r23-controls.txt": CM_R23},
                      declare=["r23-controls.txt"]))
case("cm-changed-declared-with-report", 0, [], f"{CM}['checked'][0]['control'] == 'r23-controls.txt'")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23 + "OK   one more read\n", "r23-control-mutants.txt": cm_report()},
                      prev={"r23-controls.txt": CM_R23}, declare=["r23-controls.txt"]))
CM_OTHER = sha("#!/bin/bash\n# stand-in for a control's runner\n")
CM_READ = (f"# read 2026-11-20 9:01:15 AM PST on redbaron; r11-matrix-verify.py sha256 {CM_SCRIPT}\n"
           "negative (pre-fix acceptance-subject): exit=1\n")
CM_TWO = (f"# read 2026-11-21 12:02:09 AM PST on redbaron\n# script m3-sweep-controls.sh sha256 {CM_OTHER}\n"
          f"# script sweep-check-r12.py sha256 {CM_SCRIPT}\nOK   sweep\n")
case("cm-read-form-alone", 1, ["control-mutants-missing"], f"{CM}['checked'] == [{{'control': 'r11-matrix-verify-controls-r22r.txt', "
     f"'scripts': [['r11-matrix-verify.py', {CM_SCRIPT!r}]]}}]", detail="(script r11-matrix-verify.py sha256")(
    lambda out: cm_fx(out, {"r11-matrix-verify-controls-r22r.txt": CM_READ}))
case("cm-read-form-with-report", 0, [], f"{CM}['missing'] == []")(
    lambda out: cm_fx(out, {"r11-matrix-verify-controls-r22r.txt": CM_READ, "r22r-control-mutants.txt": cm_report()}))
case("cm-two-scripts-report-at-either", 0, [], f"len({CM}['checked'][0]['scripts']) == 2 and {CM}['missing'] == []")(
    lambda out: cm_fx(out, {"m3-sweep-controls-r24oc.txt": CM_TWO, "r24oc-control-mutants.txt": cm_report()}))
case("cm-two-scripts-report-elsewhere", 1, ["control-mutants-missing"],
     detail="(script m3-sweep-controls.sh sha256 " + CM_OTHER[:12] + "; sweep-check-r12.py sha256")(
    lambda out: cm_fx(out, {"m3-sweep-controls-r24oc.txt": CM_TWO, "r24oc-control-mutants.txt": cm_report(sha_under_test=CM_TOOL)}))
CM_NAMELESS = f"# read 2026-11-20 12:30:32 AM PST on redbaron; script sha256 {CM_SCRIPT}; mode text\nOK   text\n"
CM_INPUTS = (f"# r23-controls.py controls <prd home> (stand-in)\n#   {CM_SCRIPT}  notes/controls-r13/r23-controls.py\n"
             f"# head followon6/source/work/u2e-repin 4704687eb0687702f03459e6faf126a39ecc000a consumer-run-record-gate.py sha256 {CM_TOOL}\n"
             "OK   unit\n")
case("cm-read-form-nameless-script", 0, [], f"{CM}['checked'][0]['scripts'] == [['(unnamed script)', {CM_SCRIPT!r}]]")(
    lambda out: cm_fx(out, {"r13-text-controls.txt": CM_NAMELESS, "r13-control-mutants.txt": cm_report()}))
case("cm-input-sha-is-not-the-script", 1, ["control-mutants-missing"], f"{CM}['checked'][0]['scripts'] == [['r23-controls.py', {CM_SCRIPT!r}]]")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_INPUTS, "r23-control-mutants.txt": cm_report(sha_under_test=CM_TOOL)}))
case("cm-txt-naming-no-script-refused", 1, ["control-mutants-missing"], f"{CM}['checked'] == [{{'control': 'm1-pairs-controls-r22r.txt', "
     "'scripts': []}]", detail="name no script sha256, so no mutant report can name its control")(
    lambda out: cm_fx(out, {"m1-pairs-controls-r22r.txt": 'read-target {"part": "P2 text"}\n'}))
case("cm-scripts-runners-logs-not-read", 0, [], f"{CM}['checked'] == []")(
    lambda out: cm_fx(out, {"r23-controls.py": "#!/usr/bin/env python3\n# chain review 23 repair controls\n",
                            "run-r22r-controls.sh": "#!/bin/bash\n# runs the r22r controls\n",
                            "run-r22r-controls.log": "r22r-l3-r10f4-working-clone.txt          exit=0\n"}))
case("cm-not-a-control-name", 0, [], f"{CM}['checked'] == []")(
    lambda out: cm_fx(out, {"r23-notes.txt": CM_R23}))
case("cm-before-control-mutants-since", 0, [], "'control_mutants' not in d['mission']")(
    lambda out: cm_fx(out, {"r23-controls.txt": CM_R23}, ts=CM_EARLY))


# ---------------------------------------------------------------- driver
def build(name, out):
    os.makedirs(out, exist_ok=True)
    CASES[name]["fn"](out)


def lint(lint_path, out, ungov, cwd, home_env):
    args = ["bash", lint_path, os.path.join(out, "home", "notes", "dream-log.md"), "--last", "--prd-dir", os.path.join(out, "home"), "--json"]
    if not ungov:
        args[5:5] = []
        args += ["--decisions", os.path.join(out, "decisions.jsonl")]
    env = {k: v for k, v in os.environ.items() if k not in ("SKILL_ROUTING_DECISIONS", "ANALYSIS_WIKI_DIR", "SKILL_ROUTING_POLICY")}
    env.update(HOME=home_env, SKILL_ROUTING_POLICY=os.path.join(out, "policy.json"), GIT_CONFIG_NOSYSTEM="1")
    p = subprocess.run(args, capture_output=True, text=True, env=env, cwd=cwd)
    try:
        d = json.loads(p.stdout)
    except ValueError:
        d = None
    return p.returncode, d, p.stderr


def run(prefix, lint_path, report=None):
    lint_path = os.path.abspath(lint_path)          # the lint runs from another working directory
    top = tempfile.mkdtemp(prefix=f"datr-{prefix}-")
    home_env, cwd = os.path.join(top, "fakehome"), os.path.join(top, "cwd")
    os.makedirs(home_env)
    os.makedirs(cwd)
    names = [n for n in CASES if n.startswith(prefix + "-")]
    lines, bad = [], 0
    for n in names:
        c, out = CASES[n], os.path.join(top, n)
        try:
            build(n, out)
            rc, d, err = lint(lint_path, out, c["ungov"], cwd, home_env)
        except Exception as e:         # a fixture that does not build is a failure of this case, never a pass
            rc, d, err = None, None, f"{type(e).__name__}: {e}"
        got = sorted((d or {}).get("findings") or []) if d else None
        ok = rc == c["rc"] and d is not None and got == sorted(c["findings"])
        why = ""
        if ok and c["check"]:
            try:
                ok = bool(eval(c["check"], {"d": d}))
                why = "" if ok else f"check {c['check']} false: analysis={json.dumps(d.get('analysis'))[:400]}"
            except Exception as e:
                ok, why = False, f"check raised {type(e).__name__}: {e}"
        if ok and c.get("detail") and not any(ln.startswith("FAIL ") and c["detail"] in ln for ln in err.splitlines()):
            ok, why = False, f"no FAIL line carries {c['detail']!r}: stderr={err.strip()[:600]}"
        if not ok and not why:
            why = f"rc={rc} want {c['rc']}; findings={got} want {sorted(c['findings'])}; stderr={err.strip()[:600]}"
        bad += 0 if ok else 1
        lines.append(f"{'PASS' if ok else 'FAIL'} {n}" + (f": {why}" if why else ""))
    text = "".join(x + "\n" for x in lines) + f"# {prefix}: {len(names)} cases, {len(names) - bad} pass, {bad} fail (lint {lint_path})\n"
    sys.stdout.write(text)
    if report:
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(text)
    shutil.rmtree(top, ignore_errors=True)
    return 1 if bad or not names else 0


if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] == "--list":
        for n, c in CASES.items():
            if len(a) < 2 or n.startswith(a[1] + "-"):
                print(f"{n}\t{c['rc']}\t{json.dumps(c['findings'])}\t{c['check'] or '-'}\t{'ungoverned' if c['ungov'] else 'governed'}")
        sys.exit(0)
    if a and a[0] == "--run" and len(a) in (3, 4):
        sys.exit(run(a[1], a[2], a[3] if len(a) == 4 else None))
    if len(a) == 2 and a[0] in CASES:
        build(a[0], a[1])
        sys.exit(0)
    sys.exit(__doc__)
