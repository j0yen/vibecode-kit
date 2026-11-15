#!/usr/bin/env bash
# dream-run-note-lint.sh — check a /dream run note (Phase 4) against the files the
# governed workflow writes, and a Phase 3 adversarial matrix against its grammar.
# See PRD-dream-run-record.
#
# Usage:
#   dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] [--json]
#                          [--prd-dir <dir>] [--decisions <path>]
#   dream-run-note-lint.sh --matrix <path> --states <slug=value ...> [--json]
#   dream-run-note-lint.sh --selftest
#
# The entry is the last `## <ts>  /dream  vision-...` block (--last, the default) or
# the one whose header ts equals --entry. Its five line kinds:
#   Task: <canonical id | none>   Consumer: <name | none>
#   Route: <route> <model_id> <effort> session=<id> decision=<decisions.jsonl ts>
#   Route: ungoverned session=<id> host=<hostname>
#   Analysis: wwhtbt=<ran <path>|reused <path>|skipped: <r>> 5whys=<page <path>|inline|skipped: <r>>
#             adversarial=<<path> uncovered=<n>|skipped: <r>>          (one line)
#   Review: <verdict file> reviewer-session=<id> [result=<json>]   (one per reviewer) | Review: none
#   State: <slug>=<value> ...   (a slug repeats once per state reached, in order)
# Paths are relative to the PRD home (--prd-dir; default: the log's parent's parent)
# or absolute.
#
# Provenance source: the skill-routing decisions log that fable-launch.sh `dec_row`
# appends (--decisions; default $SKILL_ROUTING_DECISIONS, the launcher's own override,
# else ~/.local/state/skill-routing/decisions.jsonl). Rows are addressed by
# (session, ts); fields read by name: ts decision task_id skill route model effort
# session; extra fields tolerated; an absent compared field is unequal and named; a
# line that is not JSON is skipped and counted (decisions_malformed). Trust: the log,
# result JSONs and pages are files the same Unix user can write, so `boundary` means
# consistent with the launcher's record on this host, never authenticated
# (`trust: same-uid` in every JSON object).
#
# Output: `OK <ts>` (`OK <ts> persisted=shape-only` when the PRD home is not a git
# repository and a persisted: sha was shape-checked only) and exit 0; one
# `FAIL <id>: <detail>` line per finding and exit 1; `ERROR <why>` on stderr and exit
# 2 for an empty, missing or unreadable log, an unknown entry, an empty or unreadable
# decisions log, or (no decisions log on this host and none given) an entry with a
# claim only a decisions row can check. --json prints the one-line JSON object on
# stdout on exit 0 and 1 (the text lines go to stderr), never on exit 2.
#
# Finding ids: line-missing route-grammar analysis-grammar review-grammar
#   state-grammar analysis-page-missing persisted-sha-missing review-file-missing
#   review-verdict-mismatch route-provenance-mismatch route-provenance-ambiguous
#   route-ungoverned-on-governed-host task-none-governed-route
#   analysis-provenance-missing analysis-page-unbound task-none-ran review-self
#   review-provenance-missing review-result-mismatch adversarial-missing
#   adversarial-slug-missing adversarial-family-missing adversarial-case-missing
#
# Env seams: SKILL_ROUTING_DECISIONS (default decisions path, as fable-launch.sh),
#   ANALYSIS_WIKI_DIR (gated wiki root for reused pages; default ~/Notes/wiki, whose
#   decisions/ and answers/ analysis-page-gate.sh protects).
# Read-only: reads the log, pages, verdict files, result JSONs, the decisions log and
# `git cat-file -e` in the PRD home; writes nothing (--selftest writes only under a
# temporary directory and runs with HOME set to it).
# Needs bash and python3 (stdlib only), as build-skill's dream-persist.sh does.

set -uo pipefail
command -v python3 >/dev/null 2>&1 || { echo "ERROR python3 is required" >&2; exit 2; }
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
exec python3 -I -c '
import sys
src = open(sys.argv[1], encoding="utf-8").read()
code = src.split("\n#__PYTHON__\n", 1)[1].split("\n#__PYTHON_END__", 1)[0]
sys.argv = sys.argv[1:]
exec(compile(code, sys.argv[0] + ":python", "exec"))
' "$SELF" "$@"
exit 2
# The Python below sits in a no-op heredoc so the file stays valid bash (bash -n, shellcheck).
: <<'#__PYTHON_END__'
#__PYTHON__
import os, re, sys, json, subprocess, tempfile, shutil, datetime

# State vocabulary: the DREAMCA1 persist distinctions. When A1301's run state machine
# (explore -> draft -> validated -> reviewed -> admitted) lands, this array is replaced
# by its names and the mapping retires: draft = drafted, validated = linted,
# reviewed = reviewed:<V>, admitted = persisted and eligible. One vocabulary until then.
STATE_VALUES = ["drafted", "linted", "reviewed:APPROVE", "reviewed:FIX", "reviewed:REJECT",
                "persisted:<sha>", "pending-scan", "eligible", "ineligible"]
VERDICTS = ("APPROVE", "FIX", "REJECT")
# Six case families of the Hermes adapter's references/adversarial-planning-pass.md.
FAMILIES = ["Identity and provenance", "Boundary environment", "Evidence interpretation",
            "Alternative bypasses and ordering", "Falsifier quality",
            "Whole-scope coverage and handoff"]
BYPASS = "Alternative bypasses and ordering"
COLUMNS = ["invariant", "still-broken implementation", "counterexample",
           "discriminating check", "evidence"]
KINDS = ["Task", "Route", "Analysis", "Review", "State"]
HEADER_RE = re.compile(r"^## (\S+)  /dream  vision-")
PAGE_LINES = 40


class Exit2(Exception):
    pass


def usage(msg):
    raise Exit2(msg + " (usage: dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] "
                "[--json] [--prd-dir <dir>] [--decisions <path>] | --matrix <path> --states "
                "<slug=value ...> [--json] | --selftest)")


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()


def norm_line(line):
    """One pair of backticks around the whole line stripped, whitespace trimmed."""
    t = line.strip()
    if len(t) >= 2 and t.startswith("`") and t.endswith("`") and not t.startswith("``"):
        t = t[1:-1].strip()
    return t


def verdict_of(line):
    """(slug, verdict, normalized line) when the line is a verdict line, else None.
    Grammar as dream-persist.sh parses it: `<slug> APPROVE|FIX|REJECT <reviewer>`,
    `#` comments and blanks ignored."""
    t = norm_line(line)
    if not t or t.startswith("#"):
        return None
    p = t.split()
    if len(p) < 3 or p[1] not in VERDICTS:
        return None
    return p[0], p[1], " ".join(p)


def parse_iso(s):
    try:
        t = s.replace("Z", "+00:00")
        m = re.match(r"^(.*[T ]\d\d:\d\d(?::\d\d(?:\.\d+)?)?)([+-]\d\d)(\d\d)$", t)
        if m:
            t = m.group(1) + m.group(2) + ":" + m.group(3)
        d = datetime.datetime.fromisoformat(t)
        return d if d.tzinfo else None
    except (ValueError, TypeError):
        return None


class Lint:
    def __init__(self):
        self.findings = []   # (id, detail)

    def fail(self, fid, detail):
        self.findings.append((fid, detail))

    def ids(self):
        out = []
        for fid, _ in self.findings:
            if fid not in out:
                out.append(fid)
        return out


# ---------------------------------------------------------------- matrix (R10)
def lint_matrix(L, path, shown, slugs):
    """Structural checks of the adversarial matrix. Returns the ## Uncovered count
    (None when that section is absent or the file is missing)."""
    if not os.path.isfile(path):
        L.fail("adversarial-missing", f"matrix file {shown} does not exist")
        return None
    try:
        lines = read_text(path).split("\n")
    except OSError as e:
        L.fail("adversarial-missing", f"matrix file {shown} unreadable: {e.strerror}")
        return None
    sections = {}       # slug -> list of lines (first section per slug)
    uncovered = None    # list of lines under the first ## Uncovered
    cur = None
    for ln in lines:
        s = ln.rstrip()
        if s.startswith("## "):
            m = re.match(r"^## PRD-(\S+)$", s)
            if m:
                slug = m.group(1)
                if slug in sections:
                    cur = None          # a second section for one slug is ignored
                else:
                    sections[slug] = []
                    cur = sections[slug]
            elif s == "## Uncovered":
                if uncovered is None:
                    uncovered = []
                    cur = uncovered
                else:
                    cur = None
            else:
                cur = None              # an ignored ## heading: its text belongs to no section
            continue
        if cur is not None:
            cur.append(ln)
    for slug in slugs:
        if slug not in sections:
            L.fail("adversarial-slug-missing", f"{shown}: no '## PRD-{slug}' section for State slug {slug}")
            continue
        lint_section(L, shown, slug, sections[slug])
    if uncovered is None:
        L.fail("adversarial-missing", f"{shown}: no '## Uncovered' section")
        return None
    content = [x.strip() for x in uncovered if x.strip()]
    items = [x for x in content if re.match(r"^([-*+]|\d+[.)])\s+\S", x)]
    bare = [re.sub(r"^([-*+]|\d+[.)])\s+", "", x).strip().lower() for x in content]
    if bare == ["none"]:
        return 0
    return len(items)


def split_cells(row):
    t = row.strip()
    if t.startswith("|"):
        t = t[1:]
    if t.endswith("|"):
        t = t[:-1]
    return [c.strip() for c in t.split("|")]


def cell_norm(c):
    return re.sub(r"[`*]", "", c).strip().lower()


def lint_section(L, shown, slug, body):
    fams = {}        # family (canonical) -> block lines (first heading only)
    cur = None
    names = {f.lower(): f for f in FAMILIES}
    for ln in body:
        s = ln.rstrip()
        if s.startswith("###"):
            m = re.match(r"^### (.+)$", s)
            key = m.group(1).strip().lower() if m else None
            if key in names and names[key] not in fams:
                fams[names[key]] = []
                cur = fams[names[key]]
            else:
                cur = None
            continue
        if cur is not None:
            cur.append(ln)
    for fam in FAMILIES:
        if fam not in fams:
            L.fail("adversarial-family-missing", f"{shown}: slug={slug} family='{fam}' has no '### {fam}' heading")
            continue
        block = [x for x in fams[fam] if x.strip()]
        table = [x for x in block if x.strip().startswith("|")]
        if table:
            header = [cell_norm(c) for c in split_cells(table[0])]
            missing = [c for c in COLUMNS if c not in header]
            if missing:
                L.fail("adversarial-missing", f"{shown}: slug={slug} family='{fam}' table header {missing[0]} absent (header {missing[0]})")
                continue
            if fam == BYPASS:
                inv = header.index("invariant")
                cells = []
                for row in table[1:]:
                    cs = split_cells(row)
                    if all(re.match(r"^:?-+:?$", c.strip()) for c in cs if c.strip()):
                        continue
                    if inv < len(cs):
                        cells.append(cell_norm(cs[inv]))
                if not any(c.startswith("unconditional fallback:") for c in cells):
                    L.fail("adversarial-case-missing", f"unconditional-fallback ({shown}: slug={slug}: no '{BYPASS}' invariant cell begins 'unconditional fallback:')")
                if not any(c.startswith("conditional fallback:") for c in cells):
                    L.fail("adversarial-case-missing", f"conditional-fallback ({shown}: slug={slug}: no '{BYPASS}' invariant cell begins 'conditional fallback:')")
        elif len(block) == 1 and re.match(r"^n/a:\s*\S", block[0].strip()):
            pass
        else:
            L.fail("adversarial-family-missing", f"{shown}: slug={slug} family='{fam}' heading has neither a table nor one 'n/a: <reason>' line")


# ---------------------------------------------------------------- log entry parse
def parse_args(argv):
    a = {"log": None, "mode": "last", "entry": None, "json": False, "prd_dir": None,
         "decisions": None, "matrix": None, "states": None, "selftest": False}
    i = 0
    while i < len(argv):
        x = argv[i]
        if x == "--json":
            a["json"] = True
        elif x == "--last":
            a["mode"] = "last"
        elif x == "--selftest":
            a["selftest"] = True
        elif x in ("--entry", "--prd-dir", "--decisions", "--matrix"):
            if i + 1 >= len(argv):
                usage(f"{x} needs a value")
            key = {"--entry": "entry", "--prd-dir": "prd_dir", "--decisions": "decisions", "--matrix": "matrix"}[x]
            a[key] = argv[i + 1]
            if x == "--entry":
                a["mode"] = "entry"
            i += 1
        elif x == "--states":
            vals = []
            while i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                vals.extend(argv[i + 1].split())
                i += 1
            a["states"] = vals
        elif x.startswith("--"):
            usage(f"unknown option {x}")
        elif a["log"] is None:
            a["log"] = x
        else:
            usage(f"unexpected argument {x}")
        i += 1
    return a


def find_entries(text):
    lines = text.split("\n")
    out = []
    cur = None
    for ln in lines:
        m = HEADER_RE.match(ln)
        if m:
            cur = {"ts": m.group(1), "lines": []}
            out.append(cur)
            continue
        if ln.startswith("## "):
            cur = None
            continue
        if cur is not None:
            cur["lines"].append(ln)
    return out


def load_decisions(path):
    rows, bad = [], 0
    for ln in read_text(path).splitlines():
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            bad += 1
            continue
        if isinstance(r, dict):
            rows.append(r)
        else:
            bad += 1
    return rows, bad


def parse_analysis(s):
    """Return dict with keys wwhtbt, fivewhys, adversarial -> (kind, value, extra) or None
    per part, plus a list of grammar problems."""
    probs = []
    out = {"wwhtbt": None, "fivewhys": None, "adversarial": None}
    m = re.match(r"^Analysis:\s+wwhtbt=(.*?)\s+5whys=(.*?)\s+adversarial=(.*)$", s.rstrip())
    if not m:
        return out, ["Analysis line is not 'wwhtbt=... 5whys=... adversarial=...'"]
    w, f, adv = (x.strip() for x in m.groups())
    mm = re.match(r"^(ran|reused)\s+(\S+)$", w)
    if mm:
        out["wwhtbt"] = (mm.group(1), mm.group(2))
    elif re.match(r"^skipped:\s*\S", w):
        out["wwhtbt"] = ("skipped", re.sub(r"^skipped:\s*", "", w))
    else:
        probs.append(f"wwhtbt value '{w}'")
    mm = re.match(r"^page\s+(\S+)$", f)
    if mm:
        out["fivewhys"] = ("page", mm.group(1))
    elif f == "inline":
        out["fivewhys"] = ("inline", None)
    elif re.match(r"^skipped:\s*\S", f):
        out["fivewhys"] = ("skipped", re.sub(r"^skipped:\s*", "", f))
    else:
        probs.append(f"5whys value '{f}'")
    mm = re.match(r"^(\S+)\s+uncovered=(\d+)$", adv)
    if mm and not adv.startswith("skipped:"):
        out["adversarial"] = ("matrix", mm.group(1), int(mm.group(2)))
    elif re.match(r"^skipped:\s*\S", adv):
        out["adversarial"] = ("skipped", re.sub(r"^skipped:\s*", "", adv), None)
    else:
        probs.append(f"adversarial value '{adv}'")
    return out, probs


def default_decisions():
    p = os.environ.get("SKILL_ROUTING_DECISIONS")
    if p:
        return p
    return os.path.join(os.path.expanduser("~"), ".local", "state", "skill-routing", "decisions.jsonl")


def in_git_home(home):
    try:
        top = subprocess.run(["git", "-C", home, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return top.returncode == 0 and os.path.realpath(top.stdout.strip()) == os.path.realpath(home)


def git_has(home, sha):
    try:
        r = subprocess.run(["git", "-C", home, "cat-file", "-e", sha + "^{object}"],
                           capture_output=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return r.returncode == 0


def first_lines(path, n=PAGE_LINES):
    try:
        return "\n".join(read_text(path).split("\n")[:n])
    except OSError:
        return ""


# ---------------------------------------------------------------- the log check
def lint_log(a):
    log = a["log"]
    if log is None:
        usage("no dream-log path given")
    if not os.path.isfile(log) or not os.access(log, os.R_OK):
        raise Exit2(f"log missing or unreadable: {log}")
    text = read_text(log)
    if not text.strip():
        raise Exit2(f"log is empty: {log}")
    entries = find_entries(text)
    if not entries:
        raise Exit2(f"no '## <ts>  /dream  vision-' entry in {log}")
    if a["mode"] == "entry":
        idx = [i for i, e in enumerate(entries) if e["ts"] == a["entry"]]
        if not idx:
            raise Exit2(f"unknown entry {a['entry']} in {log}")
        ei = idx[-1]
    else:
        ei = len(entries) - 1
    entry = entries[ei]
    prev_ts = entries[ei - 1]["ts"] if ei > 0 else None
    home = a["prd_dir"] or os.path.dirname(os.path.dirname(os.path.abspath(log)))

    # decisions source
    rows, malformed, governed, dec_path = None, 0, False, None
    if a["decisions"] is not None:
        dec_path = a["decisions"]
        if not os.path.isfile(dec_path) or not os.access(dec_path, os.R_OK):
            raise Exit2(f"decisions log missing or unreadable: {dec_path}")
        governed = True
    else:
        dp = default_decisions()
        if os.path.exists(dp):
            if not os.path.isfile(dp) or not os.access(dp, os.R_OK):
                raise Exit2(f"decisions log unreadable: {dp}")
            dec_path, governed = dp, True
    if governed:
        if not read_text(dec_path).strip():
            raise Exit2(f"decisions log is empty: {dec_path}")
        rows, malformed = load_decisions(dec_path)
    default_dp = default_decisions()

    def resolve(p):
        return p if os.path.isabs(p) else os.path.join(home, p)

    L = Lint()
    lines = {}
    reviews_raw = []
    for ln in entry["lines"]:
        for k in KINDS:
            if ln.startswith(k + ":"):
                if k == "Review":
                    reviews_raw.append(ln.rstrip())
                else:
                    lines[k] = ln.rstrip()
    for k in KINDS:
        if k == "Review":
            if not reviews_raw:
                L.fail("line-missing", "Review")
        elif k not in lines:
            L.fail("line-missing", k)

    # Task
    task, consumer = None, None
    if "Task" in lines:
        m = re.match(r"^Task:\s+(\S+)\s+Consumer:\s+(\S.*?)\s*$", lines["Task"])
        if m:
            task, consumer = m.group(1), m.group(2)
        else:
            L.fail("line-missing", "Task (the line lacks '<id | none>   Consumer: <name | none>')")
    task_none = task == "none"

    # Route
    route = None
    if "Route" in lines:
        s = lines["Route"]
        mu = re.match(r"^Route:\s+ungoverned\s+session=(\S+)\s+host=(\S+)$", s)
        mg = re.match(r"^Route:\s+(\S+)\s+(\S+)\s+(\S+)\s+session=(\S+)\s+decision=(\S+)$", s)
        if mu:
            route = {"route": "ungoverned", "model_id": None, "effort": None,
                     "session": mu.group(1), "decision": None, "host": mu.group(2)}
        elif mg and mg.group(1) != "ungoverned":
            route = {"route": mg.group(1), "model_id": mg.group(2), "effort": mg.group(3),
                     "session": mg.group(4), "decision": mg.group(5)}
        else:
            L.fail("route-grammar", f"'{s}'")

    # Analysis
    an = {"wwhtbt": None, "fivewhys": None, "adversarial": None}
    if "Analysis" in lines:
        an, probs = parse_analysis(lines["Analysis"])
        for p in probs:
            L.fail("analysis-grammar", p)

    # Review
    reviews = []   # dicts: file, session, result
    review_none = False
    review_grammar_ok = True
    seen_paths = set()
    for s in reviews_raw:
        if re.match(r"^Review:\s+none\s*$", s):
            if review_none or len(reviews_raw) > 1:
                L.fail("review-grammar", "'Review: none' must be the only Review: line")
                review_grammar_ok = False
            review_none = True
            continue
        m = re.match(r"^Review:\s+(\S+)\s+reviewer-session=(\S+)(?:\s+result=(\S+))?\s*$", s)
        if not m:
            L.fail("review-grammar", f"'{s}'")
            review_grammar_ok = False
            continue
        if m.group(1) in seen_paths:
            L.fail("review-grammar", f"two Review: lines name one file path {m.group(1)}")
            review_grammar_ok = False
            continue
        seen_paths.add(m.group(1))
        reviews.append({"file": m.group(1), "session": m.group(2), "result": m.group(3)})
    if review_none and reviews:
        review_grammar_ok = False

    # State
    states = {}
    state_ok = True
    if "State" in lines:
        toks = lines["State"][len("State:"):].split()
        if not toks:
            L.fail("state-grammar", "State: line carries no <slug>=<value> token")
            state_ok = False
        for t in toks:
            m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)=(\S+)$", t)
            if not m:
                L.fail("state-grammar", f"token '{t}'")
                state_ok = False
                continue
            slug, val = m.groups()
            states.setdefault(slug, [])
            if val.startswith("persisted:"):
                states[slug].append(val)
                continue
            if val not in STATE_VALUES:
                L.fail("state-grammar", f"{slug}={val}: value not in {' '.join(STATE_VALUES)}")
                state_ok = False
                continue
            states[slug].append(val)
        for slug in states:
            if not any(os.path.isfile(os.path.join(home, d, f"PRD-{slug}.md"))
                       for d in ("build-queue", "built-prds", "parked")):
                L.fail("state-grammar", f"slug {slug}: no PRD-{slug}.md under {home}/{{build-queue,built-prds,parked}}")
                state_ok = False

    # ---- ungoverned host: claims only a row can check
    if not governed:
        need = []
        if route and route["route"] != "ungoverned" and not task_none:
            need.append("a governed Route: line")
        w = an.get("wwhtbt")
        if w and w[0] == "ran" and not task_none:
            need.append("wwhtbt=ran")
        f = an.get("fivewhys")
        if f and f[0] == "page" and not task_none:
            need.append("5whys=page")
        if w and w[0] == "reused" and not gated_path(resolve(w[1])):
            need.append("wwhtbt=reused outside the gated wiki paths")
        if need:
            raise Exit2(f"no decisions log at {default_dp} (and no --decisions); cannot check: {', '.join(need)}")

    prov = {"route": None, "wwhtbt": None, "fivewhys": None, "adversarial": "self",
            "reviews": None, "states": "self", "persisted": "none"}

    # ---- route provenance (R8 a)
    if route:
        if route["route"] == "ungoverned":
            prov["route"] = "ungoverned"
            if governed:
                L.fail("route-ungoverned-on-governed-host",
                       f"Route: ungoverned while the decisions log {dec_path} exists on this host")
        elif task_none:
            prov["route"] = "self"
            L.fail("task-none-governed-route", "Task: none admits only Route: ungoverned")
        else:
            prov["route"] = "self"
            hits = [r for r in rows if r.get("session") == route["session"] and r.get("ts") == route["decision"]]
            if not hits:
                L.fail("route-provenance-mismatch",
                       f"decision: no decisions row with session={route['session']} ts={route['decision']}")
            elif len(hits) > 1:
                L.fail("route-provenance-ambiguous",
                       f"{len(hits)} decisions rows with session={route['session']} ts={route['decision']}")
            else:
                r = hits[0]
                want = [("decision", "launch"), ("skill", "dream"), ("task_id", task),
                        ("route", route["route"]), ("model", route["model_id"]), ("effort", route["effort"])]
                bad = []
                for k, v in want:
                    if k not in r:
                        bad.append(f"{k}=<absent> (note {v})")
                    elif r[k] != v:
                        bad.append(f"{k}={r[k]} (note {v})")
                if bad:
                    L.fail("route-provenance-mismatch", f"row {route['decision']}: " + "; ".join(bad))
                else:
                    prov["route"] = "boundary"

    # ---- analysis provenance (R8 b, c)
    def launch_rows(skill, tid):
        return [r for r in rows if r.get("decision") == "launch" and r.get("skill") == skill
                and r.get("task_id") == tid]

    def check_ran(label, skill, path):
        full = resolve(path)
        if not os.path.isfile(full):
            L.fail("analysis-page-missing", f"{label}: page {path} does not exist")
            return "self"
        if task_none:
            L.fail("task-none-ran", f"{label}: Task: none records reused or skipped:, never a run ({path})")
            return "self"
        if task is None:
            return "self"
        cand = launch_rows(skill, task)
        if not cand:
            L.fail("analysis-provenance-missing", f"{label}: no launch row with skill={skill} task_id={task}")
            return "self"
        head = first_lines(full)
        if not any(r.get("session") and r["session"] in head for r in cand):
            L.fail("analysis-page-unbound",
                   f"{label}: {path} first {PAGE_LINES} lines name no session of the {skill} launch rows for {task} "
                   f"({', '.join(str(r.get('session')) for r in cand)})")
            return "self"
        return "boundary"

    w = an.get("wwhtbt")
    if w:
        if w[0] == "ran":
            prov["wwhtbt"] = check_ran("wwhtbt", "wwhtbt", w[1])
        elif w[0] == "reused":
            full = resolve(w[1])
            if not os.path.isfile(full):
                L.fail("analysis-page-missing", f"wwhtbt: page {w[1]} does not exist")
                prov["wwhtbt"] = "self"
            elif gated_path(full):
                prov["wwhtbt"] = "gated"
            else:
                head = first_lines(full)
                ok = False
                for tid in dict.fromkeys(re.findall(r"\bA\d+\b", head)):
                    if any(r.get("session") and r["session"] in head for r in launch_rows("wwhtbt", tid)):
                        ok = True
                        break
                if ok:
                    prov["wwhtbt"] = "boundary"
                else:
                    prov["wwhtbt"] = "self"
                    L.fail("analysis-provenance-missing",
                           f"wwhtbt: reused page {w[1]} is outside the gated wiki paths and its first {PAGE_LINES} "
                           f"lines name no task id whose wwhtbt launch row's session they also name")
        else:
            prov["wwhtbt"] = "self"
    f = an.get("fivewhys")
    if f:
        prov["fivewhys"] = check_ran("5whys", "5whysandrhyme", f[1]) if f[0] == "page" else "self"

    # ---- adversarial matrix (R10)
    adv = an.get("adversarial")
    has_review = bool(reviews) or (bool(reviews_raw) and not review_none)
    if adv:
        if adv[0] == "skipped":
            if has_review:
                L.fail("adversarial-missing", "adversarial=skipped: beside a Review: line other than none")
        else:
            mpath = resolve(adv[1])
            n = lint_matrix(L, mpath, adv[1], list(states))
            if n is not None and n != adv[2]:
                L.fail("analysis-grammar", f"uncovered={adv[2]} but '## Uncovered' in {adv[1]} lists {n}")
            mm = re.match(r"^(.+)-adversarial\.md$", os.path.basename(adv[1]))
            if mm and prev_ts and os.path.isfile(mpath):
                mt, pt = parse_iso(mm.group(1)), parse_iso(prev_ts)
                if mt and pt and mt <= pt:
                    L.fail("analysis-grammar",
                           f"matrix {adv[1]} is not later than the previous entry {prev_ts} (an earlier run's matrix)")

    # ---- reviews (R8 d, R9) and verdict binding
    reviewed_slugs = [s for s, v in states.items() if any(x.startswith("reviewed:") for x in v)]
    labels = []
    files_ok = True
    seq = {}
    if review_none and not reviews:
        prov["reviews"] = "none"
        if reviewed_slugs:
            L.fail("review-self", f"Review: none beside reviewed: state for {', '.join(reviewed_slugs)}")
    elif review_grammar_ok and reviews:
        rsess = route["session"] if route else None
        for rv in reviews:
            label = "self"
            if rv["session"] == "none":
                L.fail("review-self", f"{rv['file']}: reviewer-session=none")
            elif rsess is not None and rv["session"] == rsess:
                L.fail("review-self", f"{rv['file']}: reviewer-session {rv['session']} is the Route session")
            elif governed and task is not None:
                mine = [r for r in rows if r.get("session") == rv["session"]]
                field = None
                if not mine:
                    field = "session"
                else:
                    m2 = [r for r in mine if r.get("decision") == "launch"]
                    m3 = [r for r in m2 if r.get("skill") == "dream"]
                    m4 = [r for r in m3 if r.get("task_id") == task]
                    field = None if m4 else ("decision" if not m2 else "skill" if not m3 else "task_id")
                if field:
                    L.fail("review-provenance-missing",
                           f"reviewer-session {rv['session']}: no launch row with skill=dream task_id={task} (first failing field: {field})")
            full = resolve(rv["file"])
            if not os.path.isfile(full) or not os.access(full, os.R_OK):
                L.fail("review-file-missing", f"{rv['file']} does not exist or is unreadable")
                files_ok = False
                labels.append("self")
                continue
            vlines = [v for v in (verdict_of(x) for x in read_text(full).split("\n")) if v]
            last = {}
            for slug, verdict, _ in vlines:
                last.pop(slug, None)
                last[slug] = verdict
            for slug, verdict in last.items():
                seq.setdefault(slug, []).append(verdict)
            if rv["result"]:
                label = check_result(L, rv, resolve(rv["result"]), vlines)
            labels.append(label)
        prov["reviews"] = "checked" if labels and all(x == "checked" for x in labels) else "self"
        if files_ok and state_ok:
            for slug, vs in seq.items():
                want = ["reviewed:" + v for v in vs]
                carried = [x for x in states.get(slug, []) if x.startswith("reviewed:")]
                if carried != want:
                    tokens = " ".join(states[slug]) if slug in states else "absent"
                    extra = [x for x in carried if carried.count(x) > want.count(x)]
                    why = []
                    if extra:
                        why.append("token(s) no file bears: " + " ".join(dict.fromkeys(extra)))
                    if sorted(carried) == sorted(want):
                        why.append("order differs from Review: line order")
                    L.fail("review-verdict-mismatch",
                           f"slug={slug} files={' '.join(vs)} state={tokens}" + (f" ({'; '.join(why)})" if why else ""))
            for slug in reviewed_slugs:
                if slug not in seq:
                    L.fail("review-verdict-mismatch",
                           f"slug={slug} files=none state={' '.join(states[slug])} (no Review: file names {slug})")
    else:
        prov["reviews"] = "self" if reviews_raw else None

    # ---- persisted (R3)
    shas = [(s, v[len("persisted:"):]) for s, vs in states.items() for v in vs if v.startswith("persisted:")]
    if shas:
        bad = [(s, h) for s, h in shas if not re.match(r"^[0-9a-fA-F]{7,40}$", h)]
        for s, h in bad:
            L.fail("persisted-sha-missing", f"{s}=persisted:{h}: not a 7-40 hex sha")
        if in_git_home(home):
            missing = [(s, h) for s, h in shas if (s, h) not in bad and not git_has(home, h)]
            for s, h in missing:
                L.fail("persisted-sha-missing", f"{s}=persisted:{h}: no such object in {home}")
            prov["persisted"] = "verified" if not bad and not missing else "shape-only"
        else:
            prov["persisted"] = "shape-only"

    for k in ("route", "wwhtbt", "fivewhys"):
        if prov[k] is None:
            prov[k] = "self"
    if prov["reviews"] is None:
        prov["reviews"] = "none"

    def akind(v):
        if v is None:
            return None
        kind = {"page": "ran"}.get(v[0], v[0])
        return {"kind": kind, "value": v[1]}

    obj = {
        "ts": entry["ts"], "task": task, "consumer": consumer,
        "exit": 1 if L.findings else 0, "findings": L.ids(),
        "decisions_malformed": malformed, "trust": "same-uid",
        "route": None if route is None else {k: route[k] for k in ("route", "model_id", "effort", "session", "decision")},
        "analysis": {"wwhtbt": akind(an.get("wwhtbt")), "fivewhys": akind(an.get("fivewhys"))},
        "adversarial": None if adv is None else {"kind": adv[0], "value": adv[1], "uncovered": adv[2]},
        "reviews": [{"file": r["file"], "session": r["session"], "result": r["result"]} for r in reviews],
        "states": states,
        "provenance": prov,
    }
    ok_line = f"OK {entry['ts']}" + (" persisted=shape-only" if prov["persisted"] == "shape-only" else "")
    return L, obj, ok_line


def gated_path(full):
    root = os.environ.get("ANALYSIS_WIKI_DIR") or os.path.join(os.path.expanduser("~"), "Notes", "wiki")
    rp = os.path.realpath(full)
    for sub in ("decisions", "answers"):
        base = os.path.realpath(os.path.join(root, sub))
        if rp.startswith(base + os.sep):
            return True
    return False


def check_result(L, rv, path, vlines):
    """R9: result JSON's session_id equals reviewer-session; file verdict lines and
    result verdict lines agree in both directions after one normalization. Returns the
    line's label: checked (verified and at least one verdict line compared), else self."""
    shown = rv["file"]
    try:
        d = json.loads(read_text(path))
    except (OSError, ValueError):
        L.fail("review-result-mismatch", f"{shown}: result {rv['result']} missing or not JSON")
        return "self"
    if not isinstance(d, dict):
        L.fail("review-result-mismatch", f"{shown}: result {rv['result']} is not a JSON object")
        return "self"
    absent = [k for k in ("session_id", "result") if k not in d]
    if absent:
        L.fail("review-result-mismatch", f"{shown}: result {rv['result']} lacks {' '.join(absent)}")
        return "self"
    bad = []
    if d["session_id"] != rv["session"]:
        bad.append(f"session_id={d['session_id']} (reviewer-session {rv['session']})")
    rset = {" ".join(norm_line(x).split()) for x in str(d["result"]).split("\n")}
    fset = {v[2] for v in vlines}
    for v in vlines:
        if v[2] not in rset:
            bad.append(f"file-not-in-result: {v[2]}")
    for x in str(d["result"]).split("\n"):
        v = verdict_of(x)
        if v and v[2] not in fset:
            bad.append(f"result-not-in-file: {v[2]}")
    if bad:
        L.fail("review-result-mismatch", f"{shown}: " + "; ".join(dict.fromkeys(bad)))
        return "self"
    return "checked" if vlines else "self"


def lint_matrix_mode(a):
    L = Lint()
    states = {}
    for t in a["states"] or []:
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)=(\S+)$", t)
        if not m:
            L.fail("state-grammar", f"token '{t}'")
            continue
        slug, val = m.groups()
        if not (val in STATE_VALUES or val.startswith("persisted:")):
            L.fail("state-grammar", f"{slug}={val}: value not in {' '.join(STATE_VALUES)}")
        states.setdefault(slug, []).append(val)
    if not states and not L.findings:
        usage("--states needs at least one <slug>=<value>")
    n = lint_matrix(L, a["matrix"], a["matrix"], list(states))
    obj = {"ts": None, "task": None, "consumer": None, "exit": 1 if L.findings else 0,
           "findings": L.ids(), "decisions_malformed": 0, "trust": "same-uid", "route": None,
           "analysis": {"wwhtbt": None, "fivewhys": None},
           "adversarial": {"kind": "matrix", "value": a["matrix"], "uncovered": n},
           "reviews": [], "states": states,
           "provenance": {"route": None, "wwhtbt": None, "fivewhys": None, "adversarial": "self",
                          "reviews": None, "states": "self", "persisted": "none"}}
    return L, obj, f"OK matrix {a['matrix']} uncovered={n}"


def main(argv):
    try:
        a = parse_args(argv)
        if a["selftest"]:
            return selftest()
        if a["matrix"] is not None or a["states"] is not None:
            if a["matrix"] is None or a["states"] is None or a["log"] is not None:
                usage("--matrix and --states go together, without a log")
            L, obj, ok = lint_matrix_mode(a)
        else:
            L, obj, ok = lint_log(a)
    except Exit2 as e:
        print(f"ERROR {e}", file=sys.stderr)
        return 2
    text = [f"FAIL {fid}: {d}" for fid, d in L.findings] or [ok]
    out = sys.stderr if a["json"] else sys.stdout
    for t in text:
        print(t, file=out)
    if a["json"]:
        print(json.dumps(obj, separators=(",", ":")))
    return 1 if L.findings else 0


# ---------------------------------------------------------------- selftest (R7)
S_D, S_W, S_R1, S_R2, S_5 = (f"bbbbbbbb-0000-4000-8000-00000000000{i}" for i in range(1, 6))
D_TS = "2026-11-15T00:10:00-08:00"
E_TS = "2026-11-15T02:00:00-08:00"
M_REL = "notes/reviews/2026-11-15T01:00:00-08:00-adversarial.md"
TABLE_HEAD = "| invariant | still-broken implementation | counterexample | discriminating check | evidence |\n|---|---|---|---|---|\n"


def mx_section(slug, drop=None, bypass_rows=None, falsifier_inv="AC4", demote=None, header_drop=None, bypass_na=False):
    out = [f"## PRD-{slug}", ""]
    for fam in FAMILIES:
        if fam == drop:
            continue
        head = TABLE_HEAD
        if header_drop and fam == "Evidence interpretation":
            head = head.replace(" " + header_drop + " |", " notes |")
        out.append(f"{'Note on ' + fam + ':' if fam == demote else '### ' + fam}")
        if fam == "Boundary environment":
            out.append("n/a: no host boundary in this fixture")
        elif fam == BYPASS:
            if bypass_na:
                out[-1:] = [out[-1], "n/a: no fallback path exists"]
            else:
                rows = bypass_rows if bypass_rows is not None else [
                    "| unconditional fallback: R3 | always reads legacy | legacy beside fresh | fixture AC | planned |",
                    "| conditional fallback: R3 | legacy when none fresh | no fresh marker | uncovered | open, Hermes |"]
                out.append(head.rstrip("\n"))
                out.extend(rows)
        elif fam == "Falsifier quality":
            out.append(head.rstrip("\n"))
            out.append(f"| {falsifier_inv} | passes vacuously | empty fixture | known-bad | planned |")
        else:
            out.append(head.rstrip("\n"))
            out.append("| R1 | weak check | counterexample | fixture AC | planned |")
        out.append("")
    return "\n".join(out) + "\n"


def mx_file(slugs, uncovered="- conditional fallback: R3 (owner Hermes)", sections=None, pre=None, between=""):
    pre = pre if pre is not None else "# Adversarial matrix (selftest)\n\n"
    body = sections if sections is not None else "".join(mx_section(s) for s in slugs)
    return pre + body + between + "## Uncovered\n" + uncovered + "\n"


def row(ts, decision, task, skill, route, model, effort, session, **kw):
    r = {"ts": ts, "decision": decision, "task_id": task, "skill": skill, "route": route,
         "model": model, "effort": effort, "account": "lane-x", "session": session,
         "resume": False, "reasons": "selftest"}
    r.update(kw)
    return r


def base_rows():
    return [row("2026-11-15T00:05:00-08:00", "launch", "A1", "wwhtbt", "fable-high", "claude-fable-5-1", "high", S_W),
            row("2026-11-15T00:06:00-08:00", "denied", "A1", "wwhtbt", "fable-high", "claude-fable-5-1", "high", ""),
            row("2026-11-15T00:07:00-08:00", "launch", "A1", "5whysandrhyme", "fable-high", "claude-fable-5-1", "high", S_5),
            row(D_TS, "launch", "A1", "dream", "fable-xhigh", "claude-fable-5-1", "xhigh", S_D),
            row("2026-11-15T01:30:00-08:00", "launch", "A1", "dream", "fable-xhigh", "claude-fable-5-1", "xhigh", S_R1),
            row("2026-11-15T01:40:00-08:00", "launch", "A1", "dream", "fable-xhigh", "claude-fable-5-1", "xhigh", S_R2)]


class Fx:
    """One fixture: a PRD home, a decisions log and an entry, all in a temp dir."""

    def __init__(self, root):
        self.root = root
        self.home = os.path.join(root, "home")
        self.dec = os.path.join(root, "decisions.jsonl")
        self.rows = base_rows()
        self.dec_extra = ""          # raw text appended to the decisions file
        self.write_dec = True
        self.entry = {
            "Task": "Task: A1   Consumer: hermes",
            "Route": f"Route: fable-xhigh claude-fable-5-1 xhigh session={S_D} decision={D_TS}",
            "Analysis": f"Analysis: wwhtbt=ran visions/wwhtbt.md 5whys=skipped: not a failure seed adversarial={M_REL} uncovered=1",
            "Review": [f"Review: notes/reviews/r1.txt reviewer-session={S_R1}"],
            "State": "State: foo=linted foo=reviewed:APPROVE",
        }
        self.files = {
            "built-prds/PRD-foo.md": "# foo stub\n", "built-prds/PRD-bar.md": "# bar stub\n",
            "visions/wwhtbt.md": f"# wwhtbt page\nanswered_by: fable\nsession: {S_W}\n",
            "visions/5whys.md": f"# five whys page\nsession: {S_5}\n",
            "notes/reviews/r1.txt": "foo APPROVE fable\n",
            M_REL: mx_file(["foo"]),
        }
        self.prev_entry = None
        self.git = False
        self.mtimes = {}

    def build(self):
        os.makedirs(self.home, exist_ok=True)
        for rel, txt in self.files.items():
            if txt is None:
                continue
            p = os.path.join(self.home, rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(txt)
        for rel, t in self.mtimes.items():
            os.utime(os.path.join(self.home, rel), (t, t))
        if self.write_dec:
            with open(self.dec, "w", encoding="utf-8") as fh:
                fh.write("".join(json.dumps(r) + "\n" for r in self.rows) + self.dec_extra)
        lines = ["# dream log (selftest)", ""]
        if self.prev_entry:
            lines += [f"## {self.prev_entry}  /dream  vision-earlier", "Contract: x", ""]
        lines += [f"## {E_TS}  /dream  vision-selftest", "Contract: /x/build-contract.md   Hooks: dream.lint",
                  "Seeds: selftest", "Lineage: greenfield", "Drafted: PRD-foo.md   Build order: foo",
                  "Lint: clean   Eligibility: pending scan"]
        for k in KINDS:
            v = self.entry.get(k)
            if v is None:
                continue
            lines += v if isinstance(v, list) else [v]
        lines += ["Open questions: none", ""]
        os.makedirs(os.path.join(self.home, "notes"), exist_ok=True)
        with open(os.path.join(self.home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return self

    def git_commit(self):
        env = dict(os.environ, GIT_AUTHOR_NAME="selftest", GIT_AUTHOR_EMAIL="selftest@invalid",
                   GIT_COMMITTER_NAME="selftest", GIT_COMMITTER_EMAIL="selftest@invalid")
        for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "selftest"]):
            subprocess.run(["git", "-C", self.home] + c, check=True, capture_output=True, env=env)
        return subprocess.run(["git", "-C", self.home, "rev-parse", "HEAD"], check=True,
                              capture_output=True, text=True).stdout.strip()


def selftest():
    script = os.path.abspath(sys.argv[0])
    top = tempfile.mkdtemp(prefix="drrec-selftest-")
    env = {k: v for k, v in os.environ.items() if k not in ("SKILL_ROUTING_DECISIONS", "ANALYSIS_WIKI_DIR")}
    env["HOME"] = top
    env["GIT_CONFIG_NOSYSTEM"] = "1"
    results = []
    counter = [0]

    def new():
        counter[0] += 1
        return Fx(os.path.join(top, f"fx{counter[0]:03d}"))

    def run(fx, *extra, decisions=True, js=True):
        args = [script, os.path.join(fx.home, "notes", "dream-log.md"), "--last", "--prd-dir", fx.home]
        if decisions:
            args += ["--decisions", fx.dec]
        if js:
            args.append("--json")
        args += list(extra)
        p = subprocess.run(["bash"] + args, capture_output=True, text=True, env=env, timeout=120)
        d = None
        if js and p.stdout.strip():
            try:
                d = json.loads(p.stdout)
            except ValueError:
                d = None
        return p.returncode, d, p.stdout, p.stderr

    def check(name, cond, info=""):
        results.append((name, bool(cond), info))

    def refuse(name, fx, fid, detail_has=(), decisions=True):
        fx.build()
        rc, d, out, err = run(fx, decisions=decisions)
        ok = rc == 1 and d is not None and d.get("findings") == [fid] and d.get("exit") == 1
        for s in detail_has:
            ok = ok and any(s in ln for ln in err.splitlines() if ln.startswith("FAIL " + fid))
        check(f"refuse:{fid}:{name}", ok, f"rc={rc} findings={d and d.get('findings')} err={err.strip()[:400]}")

    def passes(name, fx, extra_check=None, decisions=True):
        fx.build()
        rc, d, out, err = run(fx, decisions=decisions)
        ok = rc == 0 and d is not None and d.get("exit") == 0 and d.get("findings") == []
        info = f"rc={rc} err={err.strip()[:400]}"
        if ok and extra_check:
            try:
                extra_check(d)
            except AssertionError as e:
                ok, info = False, f"assert: {e} json={json.dumps(d)[:600]}"
        check(f"pass:{name}", ok, info)

    def expect(cond, info):
        if not cond:
            raise AssertionError(info)

    def result_json(fx, rel, session, text):
        fx.files[rel] = json.dumps({"type": "result", "is_error": False, "session_id": session, "result": text})

    # ---------- passing fixtures
    fx = new()
    fx.dec_extra = "this line is not JSON\n"
    fx.entry["State"] = "State: foo=reviewed:APPROVE foo=persisted:SHA"
    fx.build()
    sha = fx.git_commit()
    with open(os.path.join(fx.home, "notes", "dream-log.md"), encoding="utf-8") as fh:
        t = fh.read().replace("persisted:SHA", "persisted:" + sha)
    with open(os.path.join(fx.home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
        fh.write(t)
    rc, d, out, err = run(fx)

    def a1(d):
        assert d["decisions_malformed"] == 1, d["decisions_malformed"]
        assert d["states"]["foo"] == ["reviewed:APPROVE", "persisted:" + sha], d["states"]
        assert d["provenance"]["persisted"] == "verified", d["provenance"]
    try:
        assert rc == 0 and d and d["findings"] == []
        a1(d)
        check("pass:malformed-row-persisted-verified", True)
    except (AssertionError, TypeError, KeyError) as e:
        check("pass:malformed-row-persisted-verified", False, f"rc={rc} {e} err={err.strip()[:300]}")
    # same entry, PRD home not a repository: shape-only, text and JSON
    shutil.rmtree(os.path.join(fx.home, ".git"))
    rc, d, out, err = run(fx)
    rc2, _, out2, _ = run(fx, js=False)
    check("pass:persisted-shape-only", rc == 0 and d and d["provenance"]["persisted"] == "shape-only"
          and rc2 == 0 and out2.strip() == f"OK {E_TS} persisted=shape-only",
          f"rc={rc} rc2={rc2} out2={out2.strip()} err={err.strip()[:300]}")

    # checked twins: backticks on one side only, each way
    for nm, ftxt, rtxt in (("checked-file-backticked", "`foo APPROVE fable`\n", "Review done.\nfoo APPROVE fable"),
                           ("checked-result-backticked", "foo APPROVE fable\n", "Review done.\n`foo APPROVE fable`")):
        fx = new()
        fx.files["notes/reviews/r1.txt"] = ftxt
        result_json(fx, "notes/reviews/r1.json", S_R1, rtxt)
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
        passes(nm, fx, lambda d: expect(d["provenance"]["reviews"] == "checked", d["provenance"]))

    # two files: foo FIX + bar APPROVE, then foo APPROVE (spec-literal order and interleaved order)
    for nm, st in (("two-files-sequence", "foo=reviewed:FIX foo=reviewed:APPROVE foo=persisted:abc1234 bar=reviewed:APPROVE bar=persisted:abc1234"),
                   ("two-files-interleaved", "foo=reviewed:FIX foo=persisted:abc1234 foo=reviewed:APPROVE bar=reviewed:APPROVE bar=persisted:abc1234")):
        fx = new()
        fx.files["notes/reviews/r1.txt"] = "foo FIX fable\nbar APPROVE fable\n"
        fx.files["notes/reviews/r2.txt"] = "foo APPROVE fable\n"
        fx.files[M_REL] = mx_file(["foo", "bar"])
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1}",
                              f"Review: notes/reviews/r2.txt reviewer-session={S_R2}"]
        fx.entry["State"] = "State: " + st
        want = {}
        for tok in st.split():
            s, v = tok.split("=", 1)
            want.setdefault(s, []).append(v)
        passes(nm, fx, lambda d, w=want: expect(d["states"] == w, d["states"]))
    # one file, foo FIX then foo APPROVE: the last line per slug binds
    fx = new()
    fx.files["notes/reviews/r1.txt"] = "foo FIX fable\nfoo APPROVE fable\n"
    fx.entry["State"] = "State: foo=reviewed:APPROVE"
    passes("one-file-last-line-binds", fx)
    # repeated equal verdicts (advisory vii twin): two FIX files, two tokens
    fx = new()
    fx.files["notes/reviews/r1.txt"] = "foo FIX fable\n"
    fx.files["notes/reviews/r2.txt"] = "foo FIX fable\n"
    fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1}",
                          f"Review: notes/reviews/r2.txt reviewer-session={S_R2}"]
    fx.entry["State"] = "State: foo=reviewed:FIX foo=reviewed:FIX"
    passes("repeated-equal-verdicts", fx)
    # (ii) twin: a push after a FIX verdict
    fx = new()
    fx.files["notes/reviews/r1.txt"] = "`foo FIX fable`\n"
    fx.entry["State"] = "State: foo=reviewed:FIX foo=persisted:abc1234"
    passes("fix-then-persisted", fx)
    # 5whys=page with its row: kind ran
    fx = new()
    fx.entry["Analysis"] = f"Analysis: wwhtbt=ran visions/wwhtbt.md 5whys=page visions/5whys.md adversarial={M_REL} uncovered=1"
    passes("fivewhys-page-kind-ran", fx, lambda d: expect(
        d["analysis"]["fivewhys"] == {"kind": "ran", "value": "visions/5whys.md"}
        and d["provenance"]["fivewhys"] == "boundary", d["analysis"]))
    # bypass family written as heading + n/a
    fx = new()
    fx.files[M_REL] = mx_file(["foo"], sections=mx_section("foo", bypass_na=True))
    passes("bypass-family-na", fx)
    # empty verdict file beside a decorated (non-grammar) verdict in result: line labelled self
    fx = new()
    fx.files["notes/reviews/r1.txt"] = "# extractor found no verdict line\n"
    result_json(fx, "notes/reviews/r1.json", S_R1, "Findings below.\n- foo FIX fable")
    fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
    fx.entry["State"] = "State: foo=linted"
    passes("empty-file-decorated-result-self", fx, lambda d: expect(d["provenance"]["reviews"] == "self", d["provenance"]))
    # ungoverned host: no decisions file, Route ungoverned, a Review line, no ran
    fx = new()
    fx.write_dec = False
    fx.entry["Route"] = f"Route: ungoverned session={S_D} host=build-host"
    fx.entry["Analysis"] = f"Analysis: wwhtbt=skipped: amendment 5whys=inline adversarial={M_REL} uncovered=1"
    passes("ungoverned-host-review-self", fx, lambda d: expect(
        d["provenance"]["reviews"] == "self" and d["provenance"]["route"] == "ungoverned", d["provenance"]),
        decisions=False)

    # ---------- refusal fixtures, each exactly [id]
    fx = new(); fx.entry["Route"] = None
    refuse("no-route", fx, "line-missing", ["Route"])
    fx = new(); fx.entry["Route"] = f"Route: fable-xhigh session={S_D}"
    refuse("short-route", fx, "route-grammar")
    fx = new(); fx.entry["Analysis"] = f"Analysis: wwhtbt=ran visions/wwhtbt.md 5whys=skipped: x adversarial={M_REL} uncovered=0"
    fx.files[M_REL] = mx_file(["foo"], uncovered="- one\n- two")
    refuse("uncovered-count", fx, "analysis-grammar")
    fx = new(); fx.prev_entry = "2026-11-15T01:30:00-08:00"
    refuse("matrix-older-than-previous-entry", fx, "analysis-grammar", ["not later"])
    fx = new(); fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1}",
                                      f"Review: notes/reviews/r1.txt reviewer-session={S_R2}"]
    refuse("duplicate-path", fx, "review-grammar", ["notes/reviews/r1.txt"])
    fx = new(); fx.entry["State"] = "State: foo=approved"
    refuse("unknown-value", fx, "state-grammar")
    fx = new(); fx.entry["State"] = "State: foo=reviewed:APPROVE qux=linted"
    fx.files[M_REL] = mx_file(["foo", "qux"])
    refuse("slug-without-prd-file", fx, "state-grammar", ["qux"])
    fx = new(); fx.entry["Analysis"] = f"Analysis: wwhtbt=ran visions/none.md 5whys=skipped: x adversarial={M_REL} uncovered=1"
    refuse("page", fx, "analysis-page-missing", ["visions/none.md"])
    fx = new(); fx.entry["State"] = "State: foo=reviewed:APPROVE foo=persisted:SHA"
    fx.build(); fx.git_commit()
    fx.entry["State"] = "State: foo=reviewed:APPROVE foo=persisted:deadbee"
    fx.files = {}
    refuse("absent-object", fx, "persisted-sha-missing", ["deadbee"])
    fx = new(); fx.entry["State"] = "State: foo=reviewed:APPROVE foo=persisted:zz12"
    refuse("bad-shape", fx, "persisted-sha-missing")
    fx = new(); fx.entry["Review"] = [f"Review: notes/reviews/gone.txt reviewer-session={S_R1}"]
    refuse("file", fx, "review-file-missing", ["gone.txt"])

    def two(fx, f1, f2, st, names=("r1.txt", "r2.txt")):
        fx.files["notes/reviews/" + names[0]] = f1
        fx.files["notes/reviews/" + names[1]] = f2
        fx.entry["Review"] = [f"Review: notes/reviews/{names[0]} reviewer-session={S_R1}",
                              f"Review: notes/reviews/{names[1]} reviewer-session={S_R2}"]
        fx.entry["State"] = "State: " + st
        return fx
    # (i) APPROVE earlier, FIX later, only the APPROVE recorded
    refuse("i-first-file-only", two(new(), "foo APPROVE fable\n", "foo FIX fable\n", "foo=reviewed:APPROVE"),
           "review-verdict-mismatch", ["files=APPROVE FIX"])
    # (ii) FIX in backticks beside linted only
    fx = new(); fx.files["notes/reviews/r1.txt"] = "`foo FIX fable`\n"; fx.entry["State"] = "State: foo=linted"
    refuse("ii-linted-only", fx, "review-verdict-mismatch", ["slug=foo", "linted"])
    # (iii) one FIX file beside FIX then APPROVE: the APPROVE no file bears
    fx = new(); fx.files["notes/reviews/r1.txt"] = "foo FIX fable\n"
    fx.entry["State"] = "State: foo=reviewed:FIX foo=reviewed:APPROVE"
    refuse("iii-unbacked-token", fx, "review-verdict-mismatch", ["reviewed:APPROVE", "no file bears"])
    # (iv) FIX file first line (path sorts after, written after... mtime older for APPROVE), wrong order
    fx = two(new(), "foo FIX fable\n", "foo APPROVE fable\n", "foo=reviewed:APPROVE foo=reviewed:FIX",
             names=("z-fix.txt", "a-approve.txt"))
    fx.mtimes = {"notes/reviews/a-approve.txt": 1_700_000_000, "notes/reviews/z-fix.txt": 1_700_000_100}
    refuse("iv-order", fx, "review-verdict-mismatch", ["files=FIX APPROVE", "state=reviewed:APPROVE reviewed:FIX"])
    # (v) bar right, foo named by a file and absent from State
    fx = two(new(), "bar APPROVE fable\n", "foo FIX fable\n", "bar=reviewed:APPROVE")
    fx.files[M_REL] = mx_file(["bar"])
    refuse("v-absent", fx, "review-verdict-mismatch", ["slug=foo", "absent"])
    # (vi) foo reviewed:APPROVE with no file naming foo; bar carries its file's verdict
    fx = two(new(), "bar FIX fable\n", "bar APPROVE fable\n", "foo=reviewed:APPROVE bar=reviewed:FIX bar=reviewed:APPROVE")
    fx.files[M_REL] = mx_file(["foo", "bar"])
    refuse("vi-token-without-file", fx, "review-verdict-mismatch", ["slug=foo", "files=none"])
    # (vii) two FIX files beside one FIX token
    refuse("vii-repeated-collapsed", two(new(), "foo FIX fable\n", "foo FIX fable\n", "foo=reviewed:FIX"),
           "review-verdict-mismatch", ["files=FIX FIX"])
    # R9 (i) prose-only occurrence in result
    fx = new(); fx.files["notes/reviews/r1.txt"] = "foo FIX fable\n"; fx.entry["State"] = "State: foo=reviewed:FIX"
    result_json(fx, "notes/reviews/r1.json", S_R1, "I would mark foo FIX fable here after reading.")
    fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
    refuse("r9-i-file-not-in-result", fx, "review-result-mismatch", ["file-not-in-result"])
    # R9 (ii) round 2's shape: empty file, result holds a backticked verdict line
    fx = new(); fx.files["notes/reviews/r1.txt"] = ""; fx.entry["State"] = "State: foo=linted"
    result_json(fx, "notes/reviews/r1.json", S_R1, "Done.\n`foo FIX fable`")
    fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
    refuse("r9-ii-result-not-in-file", fx, "review-result-mismatch", ["result-not-in-file"])
    # R9 (iii) session_id differs
    fx = new()
    result_json(fx, "notes/reviews/r1.json", S_R2, "foo APPROVE fable")
    fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
    refuse("r9-iii-session", fx, "review-result-mismatch", ["session_id"])
    # R9 advisory: missing / not JSON / lacking a field
    for nm, content, has in (("missing", None, "missing"), ("not-json", "{oops", "not JSON"),
                             ("no-result-field", json.dumps({"session_id": S_R1}), "lacks result")):
        fx = new()
        fx.files["notes/reviews/r1.json"] = content
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
        refuse("r9-" + nm, fx, "review-result-mismatch", [has])
    # route provenance
    fx = new(); fx.rows[3] = dict(fx.rows[3], route="sonnet-medium", effort="medium", task_id="A2")
    refuse("fields", fx, "route-provenance-mismatch", ["route=sonnet-medium", "effort=medium", "task_id=A2"])
    fx = new(); fx.rows[3] = dict(fx.rows[3], skill="wwhtbt")
    refuse("wwhtbt-row", fx, "route-provenance-mismatch", ["skill="])
    fx = new(); fx.rows[3] = {k: v for k, v in fx.rows[3].items() if k != "task_id"}
    refuse("no-task_id", fx, "route-provenance-mismatch", ["task_id=<absent>"])
    fx = new(); fx.rows.append(dict(fx.rows[3], account="lane-z"))
    refuse("two-rows", fx, "route-provenance-ambiguous")
    fx = new(); fx.entry["Route"] = f"Route: ungoverned session={S_D} host=carbon"
    refuse("ungoverned-route", fx, "route-ungoverned-on-governed-host")
    fx = new(); fx.entry["Task"] = "Task: none   Consumer: none"
    fx.entry["Analysis"] = "Analysis: wwhtbt=skipped: amendment 5whys=skipped: x adversarial=skipped: no review"
    fx.entry["Review"] = ["Review: none"]; fx.entry["State"] = "State: foo=linted"
    refuse("task-none", fx, "task-none-governed-route")
    # analysis provenance
    fx = new(); fx.rows = [r for r in fx.rows if not (r["skill"] == "wwhtbt" and r["decision"] == "launch")]
    refuse("denied-only", fx, "analysis-provenance-missing", ["wwhtbt", "A1"])
    fx = new(); fx.files["visions/wwhtbt.md"] = "# page without its session\n"
    refuse("no-session", fx, "analysis-page-unbound")
    fx = new(); fx.files["visions/old.md"] = f"# old page\ntask: A9\nsession: {S_W}\n"
    fx.entry["Analysis"] = f"Analysis: wwhtbt=reused visions/old.md 5whys=skipped: x adversarial={M_REL} uncovered=1"
    refuse("reused-no-row", fx, "analysis-provenance-missing")
    fx = new(); fx.write_dec = False
    fx.entry["Task"] = "Task: none   Consumer: none"
    fx.entry["Route"] = f"Route: ungoverned session={S_D} host=build-host"
    refuse("ran", fx, "task-none-ran", decisions=False)
    # review self / provenance
    fx = new(); fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_D}"]
    refuse("drafter-reviews", fx, "review-self")
    fx = new(); fx.entry["Review"] = ["Review: none"]
    fx.entry["Analysis"] = f"Analysis: wwhtbt=ran visions/wwhtbt.md 5whys=skipped: x adversarial={M_REL} uncovered=1"
    refuse("review-none-beside-reviewed", fx, "review-self")
    fx = new(); fx.rows[4] = dict(fx.rows[4], skill="wwhtbt")
    refuse("reviewer-wwhtbt-row", fx, "review-provenance-missing", [S_R1, "skill"])
    fx = new(); fx.rows[4] = dict(fx.rows[4], task_id="A2")
    refuse("reviewer-other-task", fx, "review-provenance-missing", [S_R1, "task_id"])
    # matrix
    fx = new(); fx.files["notes/reviews/r1.txt"] = "foo FIX fable\n"; fx.entry["State"] = "State: foo=reviewed:FIX"
    fx.entry["Analysis"] = "Analysis: wwhtbt=ran visions/wwhtbt.md 5whys=skipped: x adversarial=skipped: x"
    refuse("skipped-beside-fix", fx, "adversarial-missing")
    fx = new(); fx.files["notes/reviews/r1.txt"] = "# no verdict line\n"; fx.entry["State"] = "State: foo=linted"
    fx.entry["Analysis"] = "Analysis: wwhtbt=ran visions/wwhtbt.md 5whys=skipped: x adversarial=skipped: x"
    refuse("skipped-beside-empty-review", fx, "adversarial-missing")
    fx = new(); fx.files[M_REL] = mx_file(["foo"], sections=mx_section("foo", header_drop="evidence"))
    refuse("header", fx, "adversarial-missing", ["header evidence"])
    fx = new(); fx.files[M_REL] = None
    refuse("file", fx, "adversarial-missing", [M_REL])
    fx = new(); fx.entry["State"] = "State: foo=reviewed:APPROVE bar=linted"
    refuse("bar", fx, "adversarial-slug-missing", ["bar"])
    fx = new(); fx.entry["State"] = "State: foo=reviewed:APPROVE bar=linted"
    pre = "# matrix\n\nFamilies: " + "; ".join(FAMILIES) + ".\n\n"
    fx.files[M_REL] = mx_file(["foo", "bar"], pre=pre,
                              sections=mx_section("foo", demote="Falsifier quality") + mx_section("bar"))
    refuse("first-section", fx, "adversarial-family-missing", ["slug=foo", "Falsifier quality"])
    fx = new()
    notes = "## Notes\n\n### Falsifier quality\n" + TABLE_HEAD + "| AC4 | x | y | z | w |\n\n"
    fx.files[M_REL] = mx_file(["foo"], sections=mx_section("foo", drop="Falsifier quality"), between=notes)
    refuse("notes-heading", fx, "adversarial-family-missing", ["slug=foo", "Falsifier quality"])
    fx = new()
    fx.files[M_REL] = mx_file(["foo"], pre="# matrix\n\nThe conditional case is below.\n\n", sections=mx_section(
        "foo", bypass_rows=["| unconditional fallback: R3 | always legacy | x | y | z |",
                            "| R3 legacy read | legacy when none fresh | x | uncovered | z |"],
        falsifier_inv="conditional fallback: AC4"))
    refuse("full-prefix-later-family", fx, "adversarial-case-missing", ["conditional-fallback"])

    # ---------- exit 2 fixtures (no JSON)
    def exit2(name, args, has):
        p = subprocess.run(["bash", script] + args + ["--json"], capture_output=True, text=True, env=env, timeout=120)
        check(f"exit2:{name}", p.returncode == 2 and not p.stdout.strip() and has in p.stderr,
              f"rc={p.returncode} out={p.stdout[:200]} err={p.stderr.strip()[:300]}")
    fx = new().build()
    empty = os.path.join(fx.root, "empty.md")
    open(empty, "w").close()
    exit2("empty-log", [empty, "--decisions", fx.dec], empty)
    exit2("missing-log", [os.path.join(fx.root, "nope.md")], "nope.md")
    exit2("missing-decisions", [os.path.join(fx.home, "notes", "dream-log.md"), "--decisions",
                                os.path.join(fx.root, "nodec.jsonl")], "nodec.jsonl")
    exit2("unknown-entry", [os.path.join(fx.home, "notes", "dream-log.md"), "--entry", "1999-01-01T00:00:00Z",
                            "--decisions", fx.dec], "1999-01-01")
    fx = new(); fx.write_dec = False; fx.build()
    exit2("ungoverned-ran", [os.path.join(fx.home, "notes", "dream-log.md"), "--prd-dir", fx.home],
          os.path.join(top, ".local", "state", "skill-routing", "decisions.jsonl"))

    # ---------- --matrix mode
    fx = new().build()
    mp = os.path.join(fx.home, M_REL)
    p = subprocess.run(["bash", script, "--matrix", mp, "--states", "foo=linted", "--json"],
                       capture_output=True, text=True, env=env, timeout=120)
    check("pass:matrix-mode", p.returncode == 0 and json.loads(p.stdout or "{}").get("adversarial", {}).get("uncovered") == 1,
          f"rc={p.returncode} err={p.stderr.strip()[:300]}")
    p = subprocess.run(["bash", script, "--matrix", mp, "--states", "foo=linted bar=linted", "--json"],
                       capture_output=True, text=True, env=env, timeout=120)
    check("refuse:matrix-mode-slug", p.returncode == 1 and json.loads(p.stdout or "{}").get("findings") == ["adversarial-slug-missing"],
          f"rc={p.returncode} out={p.stdout[:300]}")

    bad = 0
    for name, ok, info in results:
        if ok:
            print(f"PASS {name}")
        else:
            bad += 1
            print(f"FAIL {name}: {info}")
    leftovers = [x for x in os.listdir(top) if not x.startswith("fx")]
    shutil.rmtree(top, ignore_errors=True)
    if leftovers:
        print(f"FAIL selftest wrote outside its fixtures under HOME: {leftovers}")
        bad += 1
    print(f"selftest: {len(results) - bad + (1 if leftovers else 0)}/{len(results)} passed" if not bad
          else f"selftest: {bad} failed of {len(results)}")
    return 1 if bad else 0


sys.exit(main(sys.argv[1:]))
#__PYTHON_END__
