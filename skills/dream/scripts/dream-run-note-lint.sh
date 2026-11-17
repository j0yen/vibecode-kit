#!/usr/bin/env bash
# dream-run-note-lint.sh — check a /dream run note (Phase 4) against the files the
# governed workflow writes, and a Phase 3 adversarial matrix against its grammar.
# See PRD-dream-run-record.
#
# Usage:
#   dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] [--json]
#                          [--prd-dir <dir>] [--decisions <path>]
#   dream-run-note-lint.sh --matrix <path> --states <slug=value ...> [--json]
#   dream-run-note-lint.sh --scope-id <manifest>
#   dream-run-note-lint.sh --edges <edges.jsonl> [--prds <PRD basename ...>] [--json]
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
#   Mission: <name> edges=<path> [scope=<p>[,<p>...]] [repairs=<path>]   (optional sixth kind)
# Paths are relative to the PRD home (--prd-dir; default: the log's parent's parent)
# or absolute.
#
# Provenance source: the skill-routing decisions log that fable-launch.sh `dec_row`
# appends (--decisions; default $SKILL_ROUTING_DECISIONS, the launcher's own override,
# else ~/.local/state/skill-routing/decisions.jsonl). Rows are addressed by
# (session, ts); fields read by name: ts decision task_id skill route model effort
# session role scope scope_id; extra fields tolerated; an absent compared field is unequal and named; a
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
#   review-scope-mismatch review-snapshot-stale
#   mission-grammar mission-edges-missing edge-grammar edge-unexplained edge-unknown-unowned
#   edge-node-unlisted mission-prd-unlisted
#
# Mission (PRD-dream-mission-edge-map): opt-in. A Mission: line names the mission's edge map
# (notes/missions/<name>.edges.jsonl: a header {mission, outcome, invariants, prds, external,
# [packet], [single_component]} then one edge per line with id, the eight fields producer
# consumer command trigger authority effect_id recovery_owner postcondition, status
# known|external|unknown and, for unknown, an owner). A later entry of the same Task: inherits
# the tokens it omits and must carry the line while its State: names a member of the mission
# (live header, every scope= manifest's frozen edges copy, earlier State: slugs). Without a
# Mission: line anywhere in the log nothing here runs; the JSON carries `mission: null` and
# `provenance.mission: none`. --edges lints one edges file and reads nothing else.
#
# Review scope (PRD-dream-run-record-review-scope): a Review: session's latest launch row
# for the note's task binds by its `role`: absent = legacy (today's checks only), review =
# its `scope` manifest (absolute, or relative to the PRD home) must canonicalize to its
# `scope_id`, list every verdict slug's PRD-<slug>.md, and hold the digest of each APPROVE
# slug's current PRD file; anything else fails. The canonical scope text is the
# launcher's (fable-launch.sh R4): every line `<sha256>  <basename>`, bytewise sorted and
# de-duplicated, newline-terminated, under the shared line rule; --scope-id prints its
# sha256 (exit 0) or the review-scope-mismatch detail (exit 1) and reads nothing else.
#
# Superseded pins (gate fix, A1723 prerequisite): on an entry with one `Mission:` line
# carrying one `scope=<manifest>[,<manifest>...]` token, a listed (chain) review's stale
# APPROVE pin on a slug is not checked, and is named in its `reviews[].superseded`, only when
# the latest-launched bound review of the task is a later listed review of another session
# that APPROVEs the slug's current bytes, is result-bound and carries one
# `mission=APPROVE <session>` line. Otherwise the pin is checked as before; never a new finding.
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
import os, re, sys, json, subprocess, tempfile, shutil, datetime, hashlib

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
KINDS = ["Task", "Route", "Analysis", "Review", "State", "Mission"]   # Mission: optional (edge-map R1)
HEADER_RE = re.compile(r"^## (\S+)  /dream  vision-")
# Review scope (R4): the line rule over bytes (the bytes \s class is POSIX [:space:] in
# the C locale) and the PRD basename the repeat rule counts.
SCOPE_LINE_RE = re.compile(rb"[0-9a-f]{64}  [^\s]+")
PRD_BASENAME_RE = re.compile(rb"PRD-[a-z0-9-]+\.md")
PRD_DIRS = ("build-queue", "built-prds", "parked")
PAGE_LINES = 40


class Exit2(Exception):
    pass


def usage(msg):
    raise Exit2(msg + " (usage: dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] "
                "[--json] [--prd-dir <dir>] [--decisions <path>] | --matrix <path> --states "
                "<slug=value ...> [--json] | --scope-id <manifest> | --edges <path> [--prds <PRD basename ...>] [--json] "
                "| --selftest)")


class ScopeError(Exception):
    pass


def bshow(b):
    """A path or basename for a detail line: bytes compared as bytes, printed this way."""
    return b.decode("utf-8", "backslashreplace")


def scope_canon(path):
    """R4: (scope_id, {basename: digest}) of a sha256sum manifest, all over bytes.
    Raises ScopeError(detail) for an unreadable manifest, the line rule or prd-repeat."""
    shown = bshow(os.fsencode(path))
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as e:
        raise ScopeError(f"scope {shown}: line 0: unreadable ({e.strerror})")
    if not data:
        raise ScopeError(f"scope {shown}: line 0: line-rule: empty manifest")
    if not data.endswith(b"\n"):
        raise ScopeError(f"scope {shown}: line 0: line-rule: no final LF")
    lines = data[:-1].split(b"\n")
    for i, ln in enumerate(lines, 1):
        if not SCOPE_LINE_RE.fullmatch(ln):
            raise ScopeError(f"scope {shown}: line {i}: line-rule: not '<sha256>  <path>' "
                             "(^[0-9a-f]{64}  [^[:space:]]+$ under LC_ALL=C)")
    canon = sorted({h + b"  " + p.rsplit(b"/", 1)[-1] + b"\n" for h, p in (ln.split(b"  ", 1) for ln in lines)})
    digests, seen = {}, {}
    for c in canon:
        h, base = c[:64], c[66:-1]
        digests.setdefault(base, h.decode("ascii"))
        if PRD_BASENAME_RE.fullmatch(base):
            seen[base] = seen.get(base, 0) + 1
    rep = sorted(b for b, n in seen.items() if n > 1)
    if rep:
        raise ScopeError(f"scope {shown}: prd-repeat: {bshow(rep[0])} listed with two digests")
    return hashlib.sha256(b"".join(canon)).hexdigest(), digests


def check_scope(L, rv, row, vlines, last, home, resolve):
    """R4 and R5 for a reviewer row with role review: the manifest canonicalizes to the
    row's scope_id and lists every verdict slug; each APPROVE slug's current PRD file
    hashes to the manifest's digest. Returns True when every check passed."""
    who = f"{rv['file']}: reviewer-session {rv['session']}"
    ok = True
    sid = row.get("scope_id")
    if not isinstance(sid, str) or not sid:
        L.fail("review-scope-mismatch", f"{who}: the row's scope_id is empty or absent")
        ok = False
    scope = row.get("scope")
    if not isinstance(scope, str):
        L.fail("review-scope-mismatch", f"{who}: the row's scope is absent or not a path")
        return False
    full = resolve(scope)
    try:
        got, digests = scope_canon(full)
    except ScopeError as e:
        L.fail("review-scope-mismatch", f"{who}: {e}")
        return False
    if ok and got != sid:
        L.fail("review-scope-mismatch", f"{who}: scope {full} canonicalizes to {got}, the row's scope_id is {sid}")
        ok = False
    for slug in dict.fromkeys(v[0] for v in vlines):
        if b"PRD-" + slug.encode() + b".md" not in digests:
            L.fail("review-scope-mismatch", f"{who}: slug {slug}: PRD-{slug}.md is not among the basenames of scope {full}")
            ok = False
    return check_snapshot(L, who, full, digests, last, home) and ok


def check_snapshot(L, who, full, digests, last, home):
    """R5: an APPROVE (the slug's last verdict in this file) binds to the manifest's digest
    of PRD-<slug>.md; the current file is the first of build-queue/, built-prds/, parked/
    holding it, hashed over raw bytes. FIX and REJECT are not pinned; an absent PRD file is
    left to state-grammar / review-verdict-mismatch; an unreadable one is never a pass."""
    ok = True
    for slug, verdict in last.items():
        want = digests.get(b"PRD-" + slug.encode() + b".md")
        if verdict != "APPROVE" or want is None:
            continue
        cur = next((os.path.join(home, d, f"PRD-{slug}.md") for d in PRD_DIRS
                    if os.path.isfile(os.path.join(home, d, f"PRD-{slug}.md"))), None)
        if cur is None:
            continue
        try:
            with open(cur, "rb") as fh:
                got = hashlib.sha256(fh.read()).hexdigest()
        except OSError as e:
            L.fail("review-snapshot-stale", f"{who}: slug {slug}: {cur} unreadable ({e.strerror}); its APPROVE binds to nothing")
            ok = False
            continue
        if got != want:
            L.fail("review-snapshot-stale",
                   f"{who}: slug {slug}: {cur} sha256 {got[:12]} differs from the snapshot's {want[:12]} (scope {full}); "
                   "the APPROVE was given on other bytes")
            ok = False
    return ok


def mission_scope(lines):
    """Gate fix G1: the items of the entry's one `Mission:` line's one `scope=<p1>[,<p2>...]`
    token, or None (rule inactive): zero or several Mission: lines, no or several scope=
    tokens, an empty item. Nothing else on the line is read."""
    ms = [ln for ln in lines if ln.startswith("Mission:")]
    if len(ms) != 1:
        return None
    toks = [t for t in ms[0].split() if t.startswith("scope=")]
    if len(toks) != 1:
        return None
    items = toks[0][len("scope="):].split(",")
    return items if all(items) else None


def supersede(entry_lines, reviews, rows, task, governed, rsess, home, resolve):
    """Gate fix G1-G6 (A1723 prerequisite): {Review line index K: {slug: J session}} for each
    chain review K whose stale APPROVE pin on a slug the latest-launched chain review J
    re-approved on the slug's current bytes. Pure reads, finding-free (borrowed checks run
    on a scratch Lint), never raises: an exception makes its condition false. {} when the
    rule is inactive. The bound-review test repeats the reviews loop's own (rrow)."""
    try:
        items = mission_scope(entry_lines)
        if items is None or not governed or task is None:
            return {}
        try:
            ids = [scope_canon(resolve(p))[0] for p in items]           # G2
        except (ScopeError, OSError):
            return {}

        def launch(r):
            return r.get("decision") == "launch" and r.get("skill") == "dream" and r.get("task_id") == task

        def ts(r):
            t = r.get("ts")
            return parse_iso(t) if isinstance(t, str) else None

        def chain(row):                                                   # G3
            return any(row.get("scope_id") == x for x in ids)

        def pins(row):
            """{basename: digest} of the row's manifest when it canonicalizes to the row's scope_id."""
            scope, sid = row.get("scope"), row.get("scope_id")
            if not isinstance(scope, str) or not isinstance(sid, str):
                return None
            got, digests = scope_canon(resolve(scope))
            return digests if got == sid else None

        def current(slug):
            cur = next((os.path.join(home, d, f"PRD-{slug}.md") for d in PRD_DIRS
                        if os.path.isfile(os.path.join(home, d, f"PRD-{slug}.md"))), None)
            if cur is None:
                return None
            with open(cur, "rb") as fh:
                return hashlib.sha256(fh.read()).hexdigest()

        bound, files = {}, {}       # index -> (rv, row); index -> (verdict path, vlines, last)
        for i, rv in enumerate(reviews):
            if rv["session"] == "none" or (rsess is not None and rv["session"] == rsess):
                continue
            m4 = [r for r in rows if r.get("session") == rv["session"] and launch(r)]
            if not m4:
                continue
            role_review = m4[-1].get("role") == "review"
            if not role_review:
                continue
            bound[i] = (rv, m4[-1])
            try:
                full = resolve(rv["file"])
                if os.path.isfile(full) and os.access(full, os.R_OK):
                    vlines = [v for v in (verdict_of(x) for x in read_text(full).split("\n")) if v]
                    last = {}
                    for slug, verdict, _ in vlines:
                        last.pop(slug, None)
                        last[slug] = verdict
                    files[i] = (full, vlines, last)
            except Exception:
                pass
        jof = {}                    # G5: slug -> greatest bound index whose readable file names it
        for i in sorted(files):
            for slug in files[i][2]:
                jof[slug] = i

        def by(k, s):
            """G6 for K = Review line k and slug s: J's session, or None (the pin stays)."""
            krv, krow = bound[k]
            prd = b"PRD-" + s.encode() + b".md"
            if not (chain(krow) and files[k][2].get(s) == "APPROVE"):                # G6.1
                return None
            cur = current(s)
            kpins = pins(krow)
            if not (kpins is not None and cur is not None and kpins.get(prd) not in (None, cur)):  # G6.2
                return None
            j = jof.get(s)
            if j is None:                                                          # G6.3 J(s) exists
                return None
            jrv, jrow = bound[j]
            if not chain(jrow):                                                    # G6.3 J(s) listed
                return None
            if not j > k:                                                          # G6.3 index
                return None
            if jrv["session"] == krv["session"]:                                   # G6.3 session
                return None
            if not files[j][2].get(s) == "APPROVE":                                # G6.4
                return None
            kt, jt = ts(krow), ts(jrow)
            if not (kt is not None and jt is not None and jt > kt):               # G6.5
                return None
            if not (jt is not None and all(ts(r) is not None and ts(r) < jt for r in rows if launch(r)
                                           and r.get("role") != "author" and r.get("session") != jrv["session"])):  # G6.6
                return None
            if any(launch(r) and r.get("role") == "author" and r.get("session") == jrv["session"] for r in rows):  # G6.7
                return None
            jpins = pins(jrow)
            if not (jpins is not None and cur is not None and jpins.get(prd) == cur):  # G6.8
                return None
            scratch = Lint()
            if not (jrv["result"] and check_result(scratch, jrv, resolve(jrv["result"]), files[j][1]) == "checked"
                    and not scratch.findings):                                     # G6.9
                return None
            want = f"mission=APPROVE {jrv['session']}"
            fm = [t for t in (norm_line(x) for x in read_text(files[j][0]).split("\n")) if t.startswith("mission=")]
            if not (len(fm) == 1 and fm[0] == want):                               # G6.10 file
                return None
            res = str(json.loads(read_text(resolve(jrv["result"])))["result"])
            rm = [t for t in (" ".join(norm_line(x).split()) for x in res.split("\n")) if t.startswith("mission=")]
            if not (len(rm) == 1 and rm[0] == want):                               # G6.10 result
                return None
            return jrv["session"]

        out = {}
        for k in bound:
            if k not in files:
                continue
            for s in files[k][2]:
                try:
                    j = by(k, s)
                except Exception:
                    j = None
                if j is not None:
                    out.setdefault(k, {})[s] = j
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------- mission (PRD-dream-mission-edge-map)
# Opt-in: only an entry carrying a `Mission:` line, or one whose earlier same-Task entry of
# the log carries one, takes this path; a log with no Mission: line is unchanged.
EDGE_FIELDS = ("producer", "consumer", "command", "trigger", "authority", "effect_id",
               "recovery_owner", "postcondition")
EDGE_STATUS = ("known", "external", "unknown")
REQUIRED_BY_STATUS = {"known": EDGE_FIELDS, "external": EDGE_FIELDS, "unknown": ()}
MISSION_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MISSION_KEYS = ("edges", "scope", "repairs")
EDGE_KEYS = ("id", "status", "producer", "consumer")


def parse_mission_line(line):
    """R1 grammar of one `Mission: <name> edges=<p> [scope=<p>[,<p>...]] [repairs=<p>]` line:
    (name or None, {key: value; scope a list}, [(token, why)])."""
    toks = line[len("Mission:"):].split()
    probs, keys, name = [], {}, None
    if not toks:
        return None, keys, [("Mission:", "no mission name")]
    rest = toks
    k0 = toks[0].split("=", 1)[0]
    if "=" in toks[0] and k0 in MISSION_KEYS:
        probs.append((toks[0], "no mission name before the key=value tokens"))
    else:
        if MISSION_NAME_RE.fullmatch(toks[0]):
            name = toks[0]
        else:
            probs.append((toks[0], "name outside ^[a-z0-9][a-z0-9._-]*$"))
        rest = toks[1:]
    for t in rest:
        k, eq, v = t.partition("=")
        if not eq or k not in MISSION_KEYS:
            probs.append((t, "unknown token (only edges=, scope= and repairs= follow the name)"))
        elif k in keys:
            probs.append((t, f"a second {k}= token"))
        elif not v:
            probs.append((t, "empty value"))
        elif k == "scope":
            items = v.split(",")
            if not all(items):
                probs.append((t, "an empty scope= item"))
            else:
                keys[k] = items
        else:
            keys[k] = v
    return name, keys, probs


def read_edges(path, shown, name=None):
    """R2 and R3 over one edges file, read once (a linear pass): (header or None, [edge],
    [(finding id, detail)]). `name` is the Mission: line's name the header must equal (None in
    --edges mode). Extra keys are tolerated and ignored."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as e:
        return None, [], [("mission-edges-missing", f"{shown}: absent or unreadable ({e.strerror})")]
    text = data.decode("utf-8", "replace")
    if not text.strip():
        return None, [], [("mission-edges-missing", f"{shown}: empty file")]
    lines = text.split("\n")
    try:
        h = json.loads(lines[0])
    except ValueError:
        h = None
    if not isinstance(h, dict) or any(k in h for k in EDGE_KEYS):
        return None, [], [("mission-edges-missing", f"{shown}: line 1 is not the header object")]
    probs = []

    def bad(n, field, why):
        probs.append(("edge-grammar", f"{shown}: line {n}: field {field}: {why}"))

    def nonempty(v):
        return isinstance(v, str) and bool(v.strip())

    m = h.get("mission")
    if not nonempty(m):
        bad(1, "mission", "absent or empty")
    elif name is not None and m != name:
        bad(1, "mission", f"'{m}' is not the Mission: line's name '{name}'")
    if not nonempty(h.get("outcome")):
        bad(1, "outcome", "absent or empty")
    inv = h.get("invariants")
    if not isinstance(inv, list) or not inv or not all(nonempty(x) for x in inv):
        bad(1, "invariants", "not a non-empty list of non-empty strings")
    prds = h.get("prds")
    if not isinstance(prds, list) or not prds:
        bad(1, "prds", "not a non-empty list of PRD-<slug>.md basenames")
        prds = []
    else:
        okp = [x for x in prds if isinstance(x, str) and PRD_BASENAME_RE.fullmatch(x.encode())]
        if len(okp) != len(prds):
            bad(1, "prds", "a member is not a PRD-<slug>.md basename")
        if len(set(okp)) != len(okp):
            bad(1, "prds", "a member repeats")
        prds = okp
    ext = h.get("external")
    names = []
    if not isinstance(ext, list):
        bad(1, "external", "absent or not a list")
        ext = []
    for i, x in enumerate(ext):
        if isinstance(x, dict):
            c = x.get("contract")
            cs = c if isinstance(c, list) else [c]
            if not nonempty(x.get("name")) or not cs or not all(nonempty(y) for y in cs):
                bad(1, "external", f"entry {i + 1} is not {{name, contract: <path> | [<path>...]}}")
                continue
            names.append(x["name"])
        elif nonempty(x):
            names.append(x)
        else:
            bad(1, "external", f"entry {i + 1} is neither a name nor {{name, contract}}")
    if len(set(names)) != len(names):
        bad(1, "external", "a name repeats")
    pk = h.get("packet")
    if pk is not None and (not isinstance(pk, list) or not all(nonempty(y) and "/" not in y for y in pk)):
        bad(1, "packet", "not a list of basenames")
    sc = h.get("single_component")
    if sc is not None:
        if not nonempty(sc):
            bad(1, "single_component", "not a non-empty reason string")
        elif len(prds) != 1:
            bad(1, "single_component", f"beside {len(prds)} prds members (admitted with one)")
    prset, exts = set(prds), set(names)
    edges, seen, nlines = [], set(), 0
    for n, ln in enumerate(lines[1:], 2):
        if not ln.strip():
            continue
        nlines += 1
        try:
            e = json.loads(ln)
        except ValueError:
            e = None
        if not isinstance(e, dict):
            bad(n, "(not a JSON object)", "an edge line must be one JSON object")
            continue
        eid = e.get("id")
        if not nonempty(eid):
            bad(n, "id", "absent or empty")
            continue
        if eid in seen:
            bad(n, "id", f"{eid} repeats an earlier edge id")
            continue
        seen.add(eid)
        st = e.get("status")
        if st not in EDGE_STATUS:
            bad(n, "status", f"edge {eid}: {st!r} is not known, external or unknown")
            continue
        vals = {}
        for f in EDGE_FIELDS:
            v = e.get(f)
            if v is not None and not isinstance(v, str):
                bad(n, f, f"edge {eid}: not a string")
                v = None
            vals[f] = (v or "").strip()
        edges.append({"id": eid, "status": st, "line": n, **vals})
        for f in REQUIRED_BY_STATUS[st]:
            if not vals[f]:
                probs.append(("edge-unexplained", f"{shown}: edge {eid}: {f} is empty (status {st})"))
                break
            if f in ("producer", "consumer") and vals[f] == "UNKNOWN":
                probs.append(("edge-unexplained", f"{shown}: edge {eid}: {f} is UNKNOWN (status {st})"))
                break
        if st == "external" and not any(vals[f].startswith("external:") for f in ("producer", "consumer")):
            bad(n, "status", f"edge {eid}: status external without an external:<name> endpoint")
        if st == "unknown" and not nonempty(e.get("owner")):
            probs.append(("edge-unknown-unowned", f"{shown}: edge {eid}: status unknown without an owner"))
        for f in ("producer", "consumer"):
            v = vals[f]
            if not v or v == "UNKNOWN" or v in prset or (v.startswith("external:") and v[9:] in exts):
                continue
            probs.append(("edge-node-unlisted",
                          f"{shown}: edge {eid}: {f} {v} is neither a prds member nor a declared external:<name>"))
    if not nlines:
        probs.append(("mission-edges-missing", f"{shown}: no edge line after the header"))
    hd = {"mission": m, "prds": prds, "external": ext, "external_names": names,
          "packet": pk if isinstance(pk, list) else [], "single_component": sc if nonempty(sc) else None}
    return hd, edges, probs


def edge_counts(edges):
    c = {"total": len(edges), "known": 0, "external": 0, "unknown": 0}
    for e in edges:
        c[e["status"]] += 1
    return c


def entry_task(e):
    """The Task: id of one log entry (its last Task: line), or None."""
    t = None
    for ln in e["lines"]:
        if ln.startswith("Task:"):
            m = re.match(r"^Task:\s+(\S+)\s+Consumer:", ln)
            t = m.group(1) if m else None
    return t


def entry_state_slugs(e):
    """The slugs of one log entry's last State: line (grammar-valid tokens)."""
    s = None
    for ln in e["lines"]:
        if ln.startswith("State:"):
            s = ln
    if s is None:
        return []
    out = []
    for t in s[len("State:"):].split():
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)=(\S+)$", t)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def frozen_edges_copy(manifest_full, edges_base):
    """The edges copy frozen beside a manifest: (copy path, {basename: digest} or None, error
    detail or None). The manifest's line whose basename is edges_base names a copy in the
    manifest's own directory, which must hash to the listed digest."""
    copy = os.path.join(os.path.dirname(manifest_full), edges_base or "")
    try:
        _, digests = scope_canon(manifest_full)
    except ScopeError as e:
        return copy, None, f"manifest {manifest_full} unreadable or malformed ({e})"
    want = digests.get((edges_base or "").encode())
    if not edges_base or want is None:
        return copy, digests, f"manifest {manifest_full} lists no edges basename {edges_base or '(no edges=)'}"
    try:
        with open(copy, "rb") as fh:
            got = hashlib.sha256(fh.read()).hexdigest()
    except OSError as e:
        return copy, digests, f"frozen copy {copy} absent or unreadable ({e.strerror}; manifest {manifest_full})"
    if got != want:
        return copy, digests, f"frozen copy {copy} sha256 {got[:12]} differs from manifest {manifest_full}'s {want[:12]}"
    return copy, digests, None


def mission_record(L, entries, ei, task, states, resolve):
    """Edge-map R1-R5 for entry ei: the Mission: line, its inheritance and continuity across
    same-Task entries, the edges file and the State slugs. Returns None when neither this
    entry nor an earlier same-Task entry carries the line, else a dict (`line` False when only
    the continuity rule applied)."""
    entry = entries[ei]
    mls = [ln.rstrip() for ln in entry["lines"] if ln.startswith("Mission:")]
    earlier = []
    if task is not None:
        prev = {}
        for e in entries[:ei]:
            if entry_task(e) != task:
                continue
            el = [ln.rstrip() for ln in e["lines"] if ln.startswith("Mission:")]
            if not el:
                continue
            nm, toks, _ = parse_mission_line(el[0])
            eff = dict(prev)
            for k, v in toks.items():
                eff[k] = (v, e["ts"])
            prev = eff
            earlier.append({"ts": e["ts"], "name": nm, "eff": eff, "slugs": entry_state_slugs(e)})
    if not mls and not earlier:
        return None
    reported = set()

    def miss(detail, key):
        if key not in reported:
            reported.add(key)
            L.fail("mission-edges-missing", detail)

    # continuity set (R1): live headers + frozen copies of every earlier scope= manifest + earlier State slugs
    cont = set()
    for x in earlier:
        ep = x["eff"].get("edges")
        if ep:
            hd, _, pr = read_edges(resolve(ep[0]), ep[0])
            if hd is not None:
                cont |= set(hd["prds"])
            elif not mls:
                for fid, d in pr:
                    if fid == "mission-edges-missing":
                        miss(d, resolve(ep[0]))
        base = os.path.basename(ep[0]) if ep else None
        for mp in (x["eff"].get("scope") or ([], None))[0]:
            mfull = resolve(mp)
            copy, _, err = frozen_edges_copy(mfull, base)
            if err:
                miss(f"{copy}: {err} (continuity of entry {x['ts']})", copy)
                continue
            hd, _, _ = read_edges(copy, copy)
            if hd is None:
                miss(f"{copy}: the frozen edges copy has no header (continuity of entry {x['ts']})", copy)
                continue
            cont |= set(hd["prds"])
        cont |= {f"PRD-{s}.md" for s in x["slugs"]}
    last = earlier[-1] if earlier else None
    members = [s for s in states if f"PRD-{s}.md" in cont]
    rec = {"line": bool(mls), "name": None, "edges": None, "scope": [], "repairs": None, "inherited_from": None,
           "header": None, "edge_list": [], "earlier": earlier, "cont": cont}
    if not mls:
        if members:
            L.fail("mission-grammar", f"entry {last['ts']} carries 'Mission: {last['name']}'; this entry's State: names "
                                      f"{', '.join(members)} (a member of that mission) and carries no Mission: line")
        return rec
    if len(mls) > 1:
        L.fail("mission-grammar", f"'Mission:': {len(mls)} Mission: lines in one entry; one is allowed")
        return rec
    name, toks, probs = parse_mission_line(mls[0])
    for t, why in probs:
        L.fail("mission-grammar", f"token '{t}': {why}")
    rec["name"] = name
    if members and last is not None and name != last["name"]:
        L.fail("mission-grammar", f"entry {last['ts']} carries 'Mission: {last['name']}'; this entry's State: names "
                                  f"{', '.join(members)} under 'Mission: {name}'")
    src = []
    eff = dict(toks)
    if last is not None:
        for k in MISSION_KEYS:
            if k not in eff and k in last["eff"]:
                eff[k] = last["eff"][k][0]
                src.append(last["eff"][k][1])
        pe = last["eff"].get("edges")
        if "edges" in toks and pe and os.path.normpath(resolve(toks["edges"])) != os.path.normpath(resolve(pe[0])):
            L.fail("mission-grammar", f"token 'edges={toks['edges']}': entry {pe[1]} names edges={pe[0]}; "
                                      "one mission keeps one edge map")
    rec["inherited_from"] = max(src, key=lambda t: [x["ts"] for x in earlier].index(t)) if src else None
    rec["edges"], rec["scope"], rec["repairs"] = eff.get("edges"), eff.get("scope") or [], eff.get("repairs")
    if not rec["edges"]:
        L.fail("mission-grammar", "token 'edges=': absent and none inherited from an earlier same-Task entry")
        return rec
    hd, edges, pr = read_edges(resolve(rec["edges"]), rec["edges"], name)
    for fid, d in pr:
        L.fail(fid, d)
    rec["header"], rec["edge_list"] = hd, edges
    if hd is not None:
        for s in states:
            if f"PRD-{s}.md" not in hd["prds"]:
                L.fail("mission-prd-unlisted", f"slug {s}: PRD-{s}.md is not in the prds of {rec['edges']}")
    return rec


def mission_json(rec):
    """R5 JSON block (None without a Mission: line in this entry)."""
    if rec is None or not rec["line"]:
        return None
    hd, edges = rec["header"], rec["edge_list"]
    return {"name": rec["name"], "edges_file": rec["edges"], "scope": list(rec["scope"]), "repairs": rec["repairs"],
            "inherited_from": rec["inherited_from"], "single_component": hd["single_component"] if hd else None,
            "prds": len(hd["prds"]) if hd else 0, "edges": edge_counts(edges),
            "unknown_edges": [e["id"] for e in edges if e["status"] == "unknown"]}


def edges_mode(a):
    """R6 --edges: R2 and R3 (and R4 against --prds) over one file; reads nothing else."""
    L = Lint()
    path = a["edges"]
    hd, edges, pr = read_edges(path, path, None)
    for fid, d in pr:
        L.fail(fid, d)
    if hd is not None:
        for b in a["prds"] or []:
            if b not in hd["prds"]:
                L.fail("mission-prd-unlisted", f"{b} is not in the prds of {path}")
    c = edge_counts(edges)
    block = {"name": hd["mission"] if hd else None, "edges_file": path, "scope": [], "repairs": None,
             "inherited_from": None, "single_component": hd["single_component"] if hd else None,
             "prds": len(hd["prds"]) if hd else 0, "edges": c,
             "unknown_edges": [e["id"] for e in edges if e["status"] == "unknown"]}
    obj = {"ts": None, "task": None, "consumer": None, "exit": 1 if L.findings else 0, "findings": L.ids(),
           "decisions_malformed": 0, "trust": "same-uid", "route": None, "analysis": None, "adversarial": None,
           "reviews": None, "states": None, "provenance": None, "mission": block}
    return L, obj, f"OK edges {path} known={c['known']} external={c['external']} unknown={c['unknown']}"


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
         "decisions": None, "matrix": None, "states": None, "selftest": False, "scope_id": None,
         "edges": None, "prds": None}
    i = 0
    while i < len(argv):
        x = argv[i]
        if x == "--json":
            a["json"] = True
        elif x == "--last":
            a["mode"] = "last"
        elif x == "--selftest":
            a["selftest"] = True
        elif x in ("--entry", "--prd-dir", "--decisions", "--matrix", "--scope-id", "--edges"):
            if i + 1 >= len(argv):
                usage(f"{x} needs a value")
            key = {"--entry": "entry", "--prd-dir": "prd_dir", "--decisions": "decisions", "--matrix": "matrix",
                   "--scope-id": "scope_id", "--edges": "edges"}[x]
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
        elif x == "--prds":
            vals = []
            while i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                vals.extend(argv[i + 1].split())
                i += 1
            a["prds"] = vals
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
        elif k not in lines and k != "Mission":     # Mission: is optional (edge-map R1)
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

    # ---- mission record (PRD-dream-mission-edge-map): after the State parse, before provenance
    mrec = None
    if any(ln.startswith("Mission:") for e in entries[:ei + 1] for ln in e["lines"]):
        mrec = mission_record(L, entries, ei, task, list(states), resolve)

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
            "reviews": None, "states": "self", "persisted": "none", "snapshot": None}

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
                if "role" in r and r["role"] != "author":     # an absent role is legacy
                    bad.append(f"role={r['role']} (note author)")
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
        prov["snapshot"] = "none"
        if reviewed_slugs:
            L.fail("review-self", f"Review: none beside reviewed: state for {', '.join(reviewed_slugs)}")
    elif review_grammar_ok and reviews:
        rsess = route["session"] if route else None
        sup = supersede(entry["lines"], reviews, rows, task, governed, rsess, home, resolve)
        for i, rv in enumerate(reviews):
            label = "self"
            rrow = None              # the reviewer's latest launch row (m4[-1]) when its role is review
            rv["snapshot"] = "self"
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
                else:
                    latest = m4[-1]      # file order: the launcher's R5 reads the same row
                    rv["role"], rv["scope_id"] = latest.get("role"), latest.get("scope_id")
                    if "role" not in latest:
                        rv["snapshot"] = "legacy"
                    elif latest["role"] == "review":
                        rrow = latest
                    else:
                        L.fail("review-provenance-missing",
                               f"reviewer-session {rv['session']}: latest launch row with skill=dream task_id={task} "
                               f"has role={latest['role']}, not review (first failing field: role)")
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
            if rrow is not None:
                gone = sup.get(i, {})       # superseded pins skip check_snapshot only (G4, G7)
                if gone:
                    rv["superseded"] = [{"slug": s, "by": gone[s]} for s in last if s in gone]
                pinned = {s: v for s, v in last.items() if s not in gone}
                rv["snapshot"] = "verified" if check_scope(L, rv, rrow, vlines, pinned, home, resolve) else "self"
            for slug, verdict in last.items():
                seq.setdefault(slug, []).append(verdict)
            if rv["result"]:
                label = check_result(L, rv, resolve(rv["result"]), vlines)
            labels.append(label)
        prov["reviews"] = "checked" if labels and all(x == "checked" for x in labels) else "self"
        snaps = [rv["snapshot"] for rv in reviews]
        if all(x == "verified" for x in snaps):
            prov["snapshot"] = "verified"
        elif all(x in ("verified", "legacy") for x in snaps):
            prov["snapshot"] = "legacy"     # reported, never used to pass a failing check
        else:
            prov["snapshot"] = "self"
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
    if prov["snapshot"] is None:
        prov["snapshot"] = "none" if prov["reviews"] == "none" else "self"

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
        "reviews": [dict({"file": r["file"], "session": r["session"], "result": r["result"],
                          "role": r.get("role"), "scope_id": r.get("scope_id")},
                         **({"superseded": r["superseded"]} if r.get("superseded") else {})) for r in reviews],
        "states": states,
        "provenance": prov,
        "mission": mission_json(mrec),
    }
    prov["mission"] = "none" if obj["mission"] is None else "self"
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


def scope_id_mode(path):
    """--scope-id: the canonical scope text's sha256 (exit 0) or the
    review-scope-mismatch detail (exit 1), both on stdout."""
    try:
        sid, _ = scope_canon(path)
    except ScopeError as e:
        print(f"FAIL review-scope-mismatch: {e}")
        return 1
    print(sid)
    return 0


def main(argv):
    try:
        a = parse_args(argv)
        if a["selftest"]:
            return selftest()
        if a["scope_id"] is not None:
            if any(a[k] not in (None, False) for k in ("log", "entry", "prd_dir", "decisions", "matrix", "states", "json",
                                                       "edges", "prds")):
                usage("--scope-id takes one manifest path and nothing else")
            return scope_id_mode(a["scope_id"])
        if a["edges"] is not None or a["prds"] is not None:
            if a["edges"] is None or any(a[k] not in (None, False) for k in
                                         ("log", "entry", "prd_dir", "decisions", "matrix", "states", "scope_id")):
                usage("--edges takes one edges file, --prds <PRD basename ...> and --json, without a log, "
                      "--matrix or --scope-id")
            L, obj, ok = edges_mode(a)
        elif a["matrix"] is not None or a["states"] is not None:
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


def mission_edges(slugs, mutate=None):
    """A selftest edges file (edge-map R2): header over PRD-<slug>.md for slugs, one known edge
    slugs[0] -> slugs[1], one external edge to hermes, one owned unknown edge."""
    f8 = lambda p, c, x: {"producer": p, "consumer": c, "command": x + " command", "trigger": x + " trigger",
                          "authority": x + " authority", "effect_id": x + " effect", "recovery_owner": x + " owner",
                          "postcondition": x + " postcondition"}
    pr = [f"PRD-{s}.md" for s in slugs]
    h = {"mission": "selftest", "outcome": "selftest outcome", "invariants": ["one invariant"], "prds": pr,
         "external": ["hermes"]}
    es = [dict(id="E1", status="known", **f8(pr[0], pr[-1], "E1")),
          dict(id="E2", status="external", **f8(pr[-1], "external:hermes", "E2")),
          dict(id="E3", status="unknown", producer=pr[0], consumer="UNKNOWN", owner="selftest author")]
    if mutate:
        mutate(h, es)
    return "".join(json.dumps(x) + "\n" for x in [h] + es)


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
        self.tail = []               # lines after the five record lines (a Mission: line)
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
        lines += self.tail + ["Open questions: none", ""]
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

    # review scope: the reviewer row (S_R1) carries role review and a snapshot of PRD-foo.md
    def scoped(fx, foo_now="# foo stub\n", scope_id=None):
        dig = hashlib.sha256(b"# foo stub\n").hexdigest()
        fx.files["notes/snapshots/s.sha256"] = f"{dig}  ../../built-prds/PRD-foo.md\n"
        fx.files["built-prds/PRD-foo.md"] = foo_now
        sid = scope_id if scope_id is not None else hashlib.sha256(f"{dig}  PRD-foo.md\n".encode()).hexdigest()
        fx.rows[3] = dict(fx.rows[3], role="author", scope="", scope_id="")
        fx.rows[4] = dict(fx.rows[4], role="review", scope="notes/snapshots/s.sha256", scope_id=sid)
        return fx
    passes("snapshot-verified", scoped(new()), lambda d: expect(
        d["provenance"]["snapshot"] == "verified" and d["reviews"][0]["role"] == "review", (d["provenance"], d["reviews"])))
    passes("snapshot-legacy", new(), lambda d: expect(
        d["provenance"]["snapshot"] == "legacy" and d["reviews"][0]["role"] is None, (d["provenance"], d["reviews"])))

    # superseded chain-review pins (gate fix G1-G7): S_R1 on m1 APPROVEs foo, foo is edited,
    # S_R2 on m2 (launched later, result=, mission=APPROVE) re-APPROVEs foo on the new bytes
    def chain(fx, slugs=("foo",)):
        old, new, bar = b"# foo stub\n", b"# foo stub, edited\n", b"# bar stub\n"
        h = lambda b: hashlib.sha256(b).hexdigest()
        sid = lambda t: h("".join(sorted(set(t.splitlines(True)))).encode())
        m1 = f"{h(old)}  PRD-foo.md\n{h(bar)}  PRD-bar.md\n"
        m2 = f"{h(new)}  PRD-foo.md\n{h(bar)}  PRD-bar.md\n"
        fx.files.update({"notes/snapshots/m1.sha256": m1, "notes/snapshots/m2.sha256": m2,
                         "built-prds/PRD-foo.md": new.decode(), M_REL: mx_file(["foo", "bar"])})
        fx.rows[3] = dict(fx.rows[3], role="author", scope="", scope_id="")
        fx.rows[4] = dict(fx.rows[4], role="review", scope="notes/snapshots/m1.sha256", scope_id=sid(m1))
        fx.rows[5] = dict(fx.rows[5], role="review", scope="notes/snapshots/m2.sha256", scope_id=sid(m2))
        v1 = "".join(f"{x} APPROVE fable\n" for x in slugs)
        v2 = v1 + f"mission=APPROVE {S_R2}\n"
        fx.files["notes/reviews/r1.txt"], fx.files["notes/reviews/r2.txt"] = v1, v2
        result_json(fx, "notes/reviews/r1.json", S_R1, "Done.\n" + v1)
        result_json(fx, "notes/reviews/r2.json", S_R2, "Done.\n" + v2)
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json",
                              f"Review: notes/reviews/r2.txt reviewer-session={S_R2} result=notes/reviews/r2.json"]
        fx.entry["State"] = "State: " + " ".join(f"{x}=reviewed:APPROVE {x}=reviewed:APPROVE" for x in slugs)
        fx.files["notes/missions/selftest.edges.jsonl"] = mission_edges(["foo", "bar"])
        fx.tail = ["Mission: selftest edges=notes/missions/selftest.edges.jsonl "
                   "scope=notes/snapshots/m1.sha256,notes/snapshots/m2.sha256"]
        return fx
    passes("drsp-p1-superseded", chain(new()), lambda d: expect(
        d["provenance"]["snapshot"] == "verified" and d["reviews"][0].get("superseded") == [{"slug": "foo", "by": S_R2}]
        and "superseded" not in d["reviews"][1], (d["provenance"], d["reviews"])))
    passes("drsp-p4-b-not-superseded", chain(new(), ("foo", "bar")), lambda d: expect(
        d["reviews"][0].get("superseded") == [{"slug": "foo", "by": S_R2}], d["reviews"]))
    stale_r1 = ["notes/reviews/r1.txt", S_R1, "slug foo"]
    fx = chain(new()); fx.files["notes/reviews/r2.txt"] = f"foo FIX fable\nmission=APPROVE {S_R2}\n"
    result_json(fx, "notes/reviews/r2.json", S_R2, f"foo FIX fable\nmission=APPROVE {S_R2}")
    fx.entry["State"] = "State: foo=reviewed:APPROVE foo=reviewed:FIX"
    refuse("drsp-kb1-j-fix", fx, "review-snapshot-stale", stale_r1)
    fx = chain(new()); fx.rows[5] = dict(fx.rows[5], ts="2026-11-15T01:20:00-08:00")
    refuse("drsp-kb4-j-launched-before-k", fx, "review-snapshot-stale", stale_r1)
    fx = chain(new()); fx.tail = []
    refuse("drsp-kb5-no-mission", fx, "review-snapshot-stale", stale_r1)
    fx = chain(new()); fx.rows[5] = {k: v for k, v in fx.rows[5].items() if k != "role"}
    refuse("drsp-kb6-j-legacy", fx, "review-snapshot-stale", stale_r1)
    fx = chain(new()); s_x = "bbbbbbbb-0000-4000-8000-000000000006"
    fx.files["notes/snapshots/m3.sha256"] = fx.files["notes/snapshots/m2.sha256"] + "0" * 64 + "  notes.md\n"
    fx.rows.append(dict(fx.rows[5], ts="2026-11-15T01:50:00-08:00", session=s_x, scope="notes/snapshots/m3.sha256",
                        scope_id=hashlib.sha256("".join(sorted(fx.files["notes/snapshots/m3.sha256"].splitlines(True))).encode()).hexdigest()))
    fx.files["notes/reviews/r3.txt"] = "foo FIX fable\n"
    fx.entry["Review"].append(f"Review: notes/reviews/r3.txt reviewer-session={s_x}")
    fx.entry["State"] = "State: foo=reviewed:APPROVE foo=reviewed:APPROVE foo=reviewed:FIX"
    refuse("drsp-kb11-unlisted-x-fix-after-j", fx, "review-snapshot-stale", stale_r1)
    fx = chain(new()); fx.entry["Review"][1] = f"Review: notes/reviews/r2.txt reviewer-session={S_R2}"
    refuse("drsp-kb13-j-no-result", fx, "review-snapshot-stale", stale_r1)

    # mission edge map (PRD-dream-mission-edge-map): one passing fixture, one refusal per new id
    def edged(fx, mutate=None, state=None):
        fx.files["notes/missions/selftest.edges.jsonl"] = mission_edges(["foo", "bar"], mutate)
        fx.entry["Mission"] = "Mission: selftest edges=notes/missions/selftest.edges.jsonl"
        if state:
            fx.entry["State"] = state
        return fx
    passes("drei-mission", edged(new()), lambda d: expect(
        d["mission"]["edges"] == {"total": 3, "known": 1, "external": 1, "unknown": 1}
        and d["mission"]["unknown_edges"] == ["E3"] and d["provenance"]["mission"] == "self", d.get("mission")))
    fx = edged(new()); fx.entry["Mission"] = "Mission: selftest"
    refuse("drei-no-edges", fx, "mission-grammar", ["edges="])
    fx = edged(new()); fx.entry["Mission"] = "Mission: selftest edges=notes/missions/none.edges.jsonl"
    refuse("drei-absent", fx, "mission-edges-missing", ["none.edges.jsonl"])
    refuse("drei-bad-status", edged(new(), lambda h, es: es[0].update(status="maybe")), "edge-grammar", ["line 2", "status"])
    refuse("drei-empty-trigger", edged(new(), lambda h, es: es[0].update(trigger="")), "edge-unexplained", ["edge E1: trigger"])
    refuse("drei-no-owner", edged(new(), lambda h, es: es[2].pop("owner")), "edge-unknown-unowned", ["edge E3"])
    refuse("drei-unlisted-consumer", edged(new(), lambda h, es: es[0].update(consumer="PRD-qux.md")),
           "edge-node-unlisted", ["edge E1", "PRD-qux.md"])
    fx = edged(new(), state="State: foo=reviewed:APPROVE qux=linted")
    fx.files["built-prds/PRD-qux.md"] = "# qux stub\n"
    fx.files[M_REL] = mx_file(["foo", "qux"])
    refuse("drei-state-outside", fx, "mission-prd-unlisted", ["slug qux"])

    # ---------- refusal fixtures, each exactly [id]
    refuse("scope-id", scoped(new(), scope_id="0" * 64), "review-scope-mismatch", ["notes/snapshots/s.sha256", "0" * 64])
    refuse("edited-after-approve", scoped(new(), foo_now="# foo stub, edited\n"), "review-snapshot-stale", ["slug foo"])
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
