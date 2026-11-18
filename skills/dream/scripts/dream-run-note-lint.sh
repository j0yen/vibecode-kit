#!/usr/bin/env bash
# dream-run-note-lint.sh — check a /dream run note (Phase 4) against the files the
# governed workflow writes, and a Phase 3 adversarial matrix against its grammar.
# See PRD-dream-run-record.
#
# Usage:
#   dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] [--json]
#                          [--prd-dir <dir>] [--decisions <path>]
#   dream-run-note-lint.sh <dream-log.md> --last --packet-only [--pending <file>] [--json] [...]
#   dream-run-note-lint.sh --matrix <path> --states <slug=value ...> [--json]
#   dream-run-note-lint.sh --scope-id <manifest>
#   dream-run-note-lint.sh --edges <edges.jsonl> [--prds <PRD basename ...>] [--json]
#   dream-run-note-lint.sh --selftest
#
# The entry is the last `## <ts>  /dream  vision-...` block (--last, the default) or
# the one whose header ts equals --entry. Its six line kinds (Mission: optional):
#   Task: <canonical id | none>   Consumer: <name | none>
#   Route: <route> <model_id> <effort> session=<id> decision=<decisions.jsonl ts>
#   Route: ungoverned session=<id> host=<hostname>
#   Analysis: wwhtbt=<ran <path>|reused <path>|skipped: <r>> 5whys=<page <path>|inline|skipped: <r>>
#             adversarial=<<path> uncovered=<n>|skipped: <r>>          (one line)
#   Review: <verdict file> reviewer-session=<id> [result=<json>]   (one per reviewer) | Review: none
#   State: <slug>=<value> ...   (a slug repeats once per state reached, in order)
#   Mission: <name> edges=<path> [scope=<p>[,<p>...]] [repairs=<path>] [withdrawn=<p>[,<p>...]]
#                                                                        (optional sixth kind)
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
#   mission-scope-mismatch mission-scope-incomplete mission-review-missing
#   mission-verdict-missing mission-finding-incomplete mission-snapshot-stale
#   mission-approval-blocked mission-withdrawn-bound
#   repair-grammar mission-repairs-missing repair-duplicate repair-missing repair-class-mismatch
#   sweep-missing repair-author-mismatch repair-hash-mismatch repair-scope-mismatch
#   affected-consumer-unreviewed repair-declined-unaccepted
#
# Mission (PRD-dream-mission-edge-map): opt-in. A Mission: line names the mission's edge map
# (notes/missions/<name>.edges.jsonl: a header {mission, outcome, invariants, prds, external,
# [packet], [matrix], [single_component]} then one edge per line with id, the eight fields producer
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
# Mission chain review (PRD-dream-mission-chain-review): only on a Mission: line carrying
# scope=<manifest>[,<manifest>...] (freeze order). Each manifest must canonicalize, hold its
# own frozen edges copy, matrix (the one its frozen header's `matrix` names, else the adversarial=
# matrix of the entry that first lists it: PRD-dream-matrix-per-manifest) and every member its frozen header names (R1); the chain
# reviews are the Review: lines whose bound review row carries a listed scope id, at least one
# on a governed host, listed in manifest then launch order (R2); a chain review's file and
# result= capture carry one `mission=<VERDICT> <own session>` line and a
# `findings=<sha256|none>` line binding <file>.findings.jsonl (R3, R4). Only the latest chain
# review naming a slug pins it; an earlier APPROVE that would now be stale is named in
# reviews[].superseded (R5); under mission=APPROVE every packet file must still match its
# manifest digest. A member reaching `eligible` while it is dependent is mission-approval-blocked
# (R6): an endpoint of an unknown edge; a member named in a finding of the last chain review, and
# each one-hop edge neighbour of it in either direction over that review's frozen edges copy; a
# FIX, REJECT or absent per-PRD verdict; and, as blanket holds, every member while no chain
# review binds, none binds to the last manifest, that manifest's latest-launched review is on no
# Review: line, or the line carries no scope=.
#
# Failure-class sweep (PRD-dream-failure-class-sweep): with repairs=<path> on the Mission: line,
# a chain-review finding followed by a later chain review, or a digest moving between two
# listed manifests. Each repairs row {finding, class, author_session, before, after, changed,
# sweep, disposition} is checked for grammar and duplicates (R1), every finding with a following
# review has a row and a decline a later reviewer's advisory accepts row (R2), its class and its
# sweep over the edges incident to the finding at the before copy (R3), its author lineage (R4),
# before/after as consecutive listed manifests whose digests moved as declared, and every moved
# digest declared (R5), each consumer of a changed producer at its after digest in a later
# review's manifest (R6); changed members and their consumers are held until the mission's final
# APPROVE, an unaccepted decline's until acceptance (R7). JSON: mission.repairs (R8), whose
# `file` keeps the repairs= path the edge-map JSON carried; null when nothing here applies.
#
# Pre-launch packet check (PRD-dream-packet-errors-while-repairable): --packet-only reports only the
# packet-error ids (PACKET_IDS) over every listed manifest of the last entry, or, with --pending
# <file>, of the pending entry in the file checked as if appended (a missing, empty or entry-less
# note is one whose only entry is the pending one). The review about to launch counts as the
# following review (repair-missing) and as a Review: line (adversarial-missing). An error on a
# manifest a review launch of the task bound (role review, by scope path or scope id) is held
# (`HELD <id>:`, held_packet_errors, exit 0) when its own frozen copies, the state when its review
# launched, carry it: a live edges header error only when the frozen header raises the same defect
# (the edges file and the matrix: when the manifest lacks them, unless a pending adversarial= names
# the matrix); a row error only when every row it names is byte-identical at its row number in the
# digest-matching repairs copy beside the latest bound manifest, and an error a missing row raises
# only when the copy there of the repairs file in force at that manifest's latest launch (by every
# row binding it; the latest repairs= recorded before it, else the current one), read as at that
# launch, lacks the row too (a mission with no repairs= token froze none; a copy row naming a manifest
# whose withdrawal was recorded before that launch answers nothing; a finding counts only if its review
# first launched on its manifest before it; a pair only if no manifest between them was withdrawn
# later); none on a manifest edited or deleted after its launch. An
# error naming no manifest, an unbound manifest or a new row, or raised only by a pending token, sets
# the exit (`FAIL <id>:`, packet_errors). --pending also exits 1 with
# `PENDING <line|slug|digest>: <detail>` (no id) for a missing Task:/Mission:/Analysis:/State: line,
# an Analysis: grammar or recency failure, a Review: file slug the State: omits, and (also without
# --pending) a live edges, repairs or matrix file differing from the unbound last manifest's digest;
# the matrix rules also read the last manifest's frozen header prds. `OK packet <ts>` otherwise.
# withdrawn= (inherited when omitted) drops an unbound manifest from every check, voids the repairs
# rows naming it and is listed under mission.withdrawn {path, scope_id, reason, voided_rows}, the
# reason recomputed by a packet-only pass over the entry that first withdrew it; a bound manifest is
# mission-withdrawn-bound and stays. No withdrawn= and no --packet-only: output unchanged.
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
                "[--json] [--prd-dir <dir>] [--decisions <path>] | <dream-log.md> --last --packet-only "
                "[--pending <file>] [--json] [--prd-dir <dir>] [--decisions <path>] | --matrix <path> --states "
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


# ---------------------------------------------------------------- mission (PRD-dream-mission-edge-map)
# Opt-in: only an entry carrying a `Mission:` line, or one whose earlier same-Task entry of
# the log carries one, takes this path; a log with no Mission: line is unchanged.
EDGE_FIELDS = ("producer", "consumer", "command", "trigger", "authority", "effect_id",
               "recovery_owner", "postcondition")
EDGE_STATUS = ("known", "external", "unknown")
REQUIRED_BY_STATUS = {"known": EDGE_FIELDS, "external": EDGE_FIELDS, "unknown": ()}
MISSION_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
MISSION_KEYS = ("edges", "scope", "repairs", "withdrawn")    # withdrawn=: PRD-dream-packet-errors-while-repairable R2
LIST_KEYS = ("scope", "withdrawn")
EDGE_KEYS = ("id", "status", "producer", "consumer")


def parse_mission_line(line):
    """R1 grammar of one `Mission: <name> edges=<p> [scope=<p>[,<p>...]] [repairs=<p>]
    [withdrawn=<p>[,<p>...]]` line: (name or None, {key: value; scope and withdrawn lists}, [(token, why)])."""
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
        elif k in LIST_KEYS:
            items = v.split(",")
            if not all(items):
                probs.append((t, f"an empty {k}= item"))
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
    # PRD-dream-matrix-per-manifest R1: the optional `matrix`, the basename of the adversarial
    # matrix current at this freeze; never a PRD, packet, edges-file or contract basename
    mxv = None
    if "matrix" in h:
        mx = h["matrix"]
        others = [("prds", set(prds)), ("packet", set(y for y in pk if isinstance(y, str)) if isinstance(pk, list) else set()),
                  ("edges file", {os.path.basename(path)}),
                  ("external contract", {os.path.basename(y) for x in ext if isinstance(x, dict)
                                         for y in (x.get("contract") if isinstance(x.get("contract"), list) else [x.get("contract")])
                                         if isinstance(y, str)})]
        if not isinstance(mx, str) or not mx.strip():
            bad(1, "matrix", "not a non-empty basename string")
        elif "/" in mx or mx != mx.strip() or mx in (".", ".."):
            bad(1, "matrix", f"'{mx}' is a path, not a basename")
        elif not mx.endswith(".md"):
            bad(1, "matrix", f"'{mx}' is not a basename ending .md")
        elif any(mx in v for _, v in others):
            kind = next(k for k, v in others if mx in v)
            bad(1, "matrix", f"'{mx}' is the basename of {'an' if kind[0] in 'aeiou' else 'a'} {kind} member of this "
                             "header (a PRD or the vision cannot stand in for the matrix)")
        else:
            mxv = mx
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
          "packet": pk if isinstance(pk, list) else [], "single_component": sc if nonempty(sc) else None,
          "matrix": mxv}
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


def entry_matrix(e):
    """The matrix path of one log entry's last Analysis: line (None for skipped: or no line)."""
    a = None
    for ln in e["lines"]:
        if ln.startswith("Analysis:"):
            a = ln
    if a is None:
        return None
    v = parse_analysis(a)[0]["adversarial"]
    return v[1] if v and v[0] == "matrix" else None


def manifest_matrix(m, mrec, adv, states, resolve):
    """PRD-dream-matrix-per-manifest R2: (matrix basename or None, the rule that named it, the State
    slugs of the entry that first lists the manifest in scope=). The frozen header's `matrix`, else
    the adversarial= matrix of that entry when it names one, else of the next entry of the mission
    that does (the linted entry last), else none."""
    seq = [((x["eff"].get("scope") or ([], None))[0], x.get("adv"), x["slugs"]) for x in mrec["earlier"]]
    seq.append((mrec["scope"], adv[1] if adv and adv[0] == "matrix" else None, list(states)))
    n = os.path.normpath(m["full"])
    first = next((i for i, (sc, _, _) in enumerate(seq) if any(os.path.normpath(resolve(p)) == n for p in sc)), len(seq) - 1)
    fh = m["frozen"]
    if fh and fh.get("matrix"):
        return fh["matrix"], "matrix named by the frozen edges header", seq[first][2], False
    src = next((i for i, (_, a, _) in enumerate(seq) if i >= first and a), None)
    mx = seq[src][1] if src is not None else None
    # the fourth value: the name comes from the linted entry's own adversarial= (a pending token in --pending)
    return ((os.path.basename(mx) if mx else None), "matrix named by adversarial= (the header names none)", seq[first][2],
            src == len(seq) - 1)


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


def mission_record(L, entries, ei, task, states, resolve, opts=None):
    """Edge-map R1-R5 for entry ei: the Mission: line, its inheritance and continuity across
    same-Task entries, the edges file and the State slugs. Returns None when neither this
    entry nor an earlier same-Task entry carries the line, else a dict (`line` False when only
    the continuity rule applied). opts (PRD-dream-packet-errors-while-repairable): `wbound`, a
    function naming the review launch that binds a manifest path ((session, why) or None; absent
    on a host with no decisions log), and `passA`, the normalized path of a withdrawn manifest
    whose reason is being recomputed (scope= cut after it, it is not withdrawn)."""
    opts = opts or {}

    def norm(p):
        return os.path.normpath(resolve(p))
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
            earlier.append({"ts": e["ts"], "name": nm, "eff": eff, "slugs": entry_state_slugs(e), "adv": entry_matrix(e)})
    if not mls and not earlier:
        return None
    # packet-errors R2/R3: the effective withdrawn= list (this line's, else inherited), a bound
    # manifest refused (never applied), a present list that drops an inherited path refused; the
    # applied set is skipped by the continuity pass, scope=, repairs pairing and binding
    wtok = parse_mission_line(mls[0])[1].get("withdrawn") if len(mls) == 1 else None
    winh = earlier[-1]["eff"].get("withdrawn") if earlier else None
    winh_l, winh_ts = (winh[0], winh[1]) if winh else ([], None)
    present = {norm(p) for p in wtok or []}
    wlist = list(dict.fromkeys(list(wtok or []) + [p for p in winh_l if norm(p) not in present]))
    if wtok is not None:
        for p in winh_l:
            if norm(p) not in present:
                L.fail("mission-scope-mismatch", f"token 'withdrawn={','.join(wtok)}': drops {p}, inherited from entry "
                                                 f"{winh_ts} (a present withdrawn= carries every inherited path)",
                       man=[p], pend=True)
    wapplied = []
    for p in wlist:
        if opts.get("passA") and norm(p) == opts["passA"]:
            continue
        hit = opts["wbound"](p) if opts.get("wbound") else None
        if hit:
            L.fail("mission-withdrawn-bound", f"withdrawn={p}: manifest {p} is bound to a review (session {hit[0]}"
                                              + (f"; {hit[1]}" if hit[1] else "") + "); a manifest is withdrawable only "
                                              "while no review launch has touched it", man=[p], pend=True)
        else:
            wapplied.append(p)
    wset = {norm(p) for p in wapplied}
    # packet-errors R1/S3: the timestamp of the entry that first recorded each applied withdrawal; a
    # withdrawal only the pending entry carries has none
    wsince = {}
    for p in wapplied:
        wsince[norm(p)] = next((x["ts"] for x in earlier if any(norm(q) == norm(p) for q in (x["eff"].get("withdrawn") or ([], None))[0])),
                               None if opts.get("psem") else entry["ts"])
    reported = set()

    def miss(detail, key, mp=None):
        if key not in reported:
            reported.add(key)
            L.fail("mission-edges-missing", detail, man=[mp] if mp else None)

    # continuity set (R1): live headers + frozen copies of every earlier scope= manifest + earlier State slugs
    cont, by_name = set(), {}
    for x in earlier:
        before = set(cont)
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
            if norm(mp) in wset:
                continue
            mfull = resolve(mp)
            copy, _, err = frozen_edges_copy(mfull, base)
            if err:
                miss(f"{copy}: {err} (continuity of entry {x['ts']})", copy, mp)
                continue
            hd, _, _ = read_edges(copy, copy)
            if hd is None:
                miss(f"{copy}: the frozen edges copy has no header (continuity of entry {x['ts']})", copy, mp)
                continue
            cont |= set(hd["prds"])
        cont |= {f"PRD-{s}.md" for s in x["slugs"]}
        by_name.setdefault(x["name"], set()).update(cont - before, {f"PRD-{s}.md" for s in x["slugs"]})
        if ep:
            hd0, _, _ = read_edges(resolve(ep[0]), ep[0])
            by_name[x["name"]].update(hd0["prds"] if hd0 else [])
    last = earlier[-1] if earlier else None
    members = [s for s in states if f"PRD-{s}.md" in cont]
    rec = {"line": bool(mls), "name": None, "edges": None, "scope": [], "repairs": None, "inherited_from": None,
           "header": None, "edge_list": [], "earlier": earlier, "cont": cont,
           "withdrawn": wapplied if wlist else None, "wset": wset, "wsince": wsince, "dropset": set(), "opts": opts}
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
        ps = last["eff"].get("scope")
        if "scope" in toks and ps and [os.path.normpath(resolve(x)) for x in toks["scope"][:len(ps[0])]] != \
                [os.path.normpath(resolve(x)) for x in ps[0]]:
            L.fail("mission-grammar", f"token 'scope={','.join(toks['scope'])}': does not begin with the scope= list "
                                      f"entry {last['ts']} carries or inherits ({','.join(ps[0])}); a later entry "
                                      "extends the list, never shortens or reorders it")
    rec["inherited_from"] = max(src, key=lambda t: [x["ts"] for x in earlier].index(t)) if src else None
    rec["edges"], rec["scope"], rec["repairs"] = eff.get("edges"), eff.get("scope") or [], eff.get("repairs")
    if opts.get("passA"):           # the reason pass: scope= as it stood when the withdrawn manifest was last
        cut = next((i for i, p in enumerate(rec["scope"]) if norm(p) == opts["passA"]), None)
        if cut is not None:
            rec["dropset"] = {norm(p) for p in rec["scope"][cut + 1:]} - {opts["passA"]}
            rec["scope"] = rec["scope"][:cut + 1]
            wapplied = [p for p in wapplied if any(norm(p) == norm(x) for x in rec["scope"])]
            rec["wset"] = wset = {norm(p) for p in wapplied}
            rec["withdrawn"] = wapplied if wlist else None
    for p in wapplied:              # packet-errors R2: an applied path is listed once in scope=
        n_ = sum(1 for x in rec["scope"] if norm(x) == norm(p))
        if n_ == 0:
            L.fail("mission-scope-mismatch", f"token 'withdrawn=': {p} is not a listed scope= manifest", man=[p], pend=True)
        elif n_ > 1:
            L.fail("mission-scope-mismatch", f"scope=: {p} is listed again after its withdrawal (a second occurrence "
                                             "of a withdrawn path)", man=[p], pend=True)
    if not rec["edges"]:
        L.fail("mission-grammar", "token 'edges=': absent and none inherited from an earlier same-Task entry")
        return rec
    hd, edges, pr = read_edges(resolve(rec["edges"]), rec["edges"], name)
    for fid, d in pr:
        L.fail(fid, d)
    rec["header"], rec["edge_list"] = hd, edges
    if hd is not None and hd["single_component"] and len(by_name.get(name, set())) > 1:
        L.fail("edge-grammar", f"{rec['edges']}: line 1: field single_component: an earlier entry of this Task "
                               f"carries Mission: {name} with {len(by_name[name])} prds members")
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
            "unknown_edges": [e["id"] for e in edges if e["status"] == "unknown"],
            **({"withdrawn": rec["wrecs"]} if rec.get("wrecs") is not None else {})}


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


# ---------------------------------------------------------------- mission (PRD-dream-mission-chain-review)
FINDING_CLASSES = ("provenance", "missing-producer-runner", "authority-bypass", "unreachable-transition",
                   "semantic-incompatibility", "false-green-acceptance")
MISSION_LINE_RE = re.compile(r"^mission=(APPROVE|FIX|REJECT)\s+(\S+)\s*$")
FINDINGS_LINE_RE = re.compile(r"^findings=(none|[0-9a-f]{64})\s*$")
# R3: a chain review launched before this time whose capture carries no findings= line is
# reported sidecar_bound false, not refused; a findings= line present is compared whatever
# the launch time. Set by the installing commit (A1723), the way KINDS is versioned.
SIDECAR_BINDING_SINCE = "2026-11-16T20:00:00-08:00"
MISSION_IDS = ("mission-grammar", "mission-edges-missing", "edge-grammar", "edge-unexplained",
               "edge-unknown-unowned", "edge-node-unlisted", "mission-prd-unlisted",
               "mission-scope-mismatch", "mission-scope-incomplete", "mission-review-missing",
               "mission-verdict-missing", "mission-finding-incomplete", "mission-snapshot-stale",
               "mission-approval-blocked", "mission-withdrawn-bound")
# PRD-dream-packet-errors-while-repairable R1: the ids --packet-only reports
PACKET_IDS = ("mission-grammar", "mission-edges-missing", "mission-scope-mismatch", "mission-scope-incomplete",
              "mission-withdrawn-bound", "edge-grammar", "edge-unexplained", "edge-unknown-unowned", "edge-node-unlisted",
              "mission-prd-unlisted", "repair-grammar", "mission-repairs-missing", "repair-duplicate", "repair-missing",
              "repair-class-mismatch", "sweep-missing", "repair-author-mismatch", "repair-hash-mismatch",
              "repair-scope-mismatch", "adversarial-missing", "adversarial-slug-missing", "adversarial-family-missing",
              "adversarial-case-missing")


def launch_ts(row):
    t = row.get("ts")
    return parse_iso(t) if isinstance(t, str) else None


def file_sha(path):
    try:
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()
    except OSError:
        return None


def first_holder(home, dirs, base):
    return next((os.path.join(home, d, base) for d in dirs if os.path.isfile(os.path.join(home, d, base))), None)


def bind_reviews(reviews, rows, task, governed, rsess, resolve):
    """The base loop's bound reviews (rrow = m4[-1] with role review), computed once before it,
    with each readable verdict file's verdict lines and last verdict per slug. Pure reads."""
    out = []
    if not governed or task is None:
        return out
    for i, rv in enumerate(reviews):
        if rv["session"] == "none" or (rsess is not None and rv["session"] == rsess):
            continue
        m4 = [r for r in rows if r.get("session") == rv["session"] and r.get("decision") == "launch"
              and r.get("skill") == "dream" and r.get("task_id") == task]
        if not m4 or m4[-1].get("role") != "review":
            continue
        full = resolve(rv["file"])
        vlines, last, text = [], {}, None
        if os.path.isfile(full) and os.access(full, os.R_OK):
            text = read_text(full)
            vlines = [v for v in (verdict_of(x) for x in text.split("\n")) if v]
            for slug, verdict, _ in vlines:
                last.pop(slug, None)
                last[slug] = verdict
        out.append({"i": i, "rv": rv, "row": m4[-1], "full": full, "text": text, "vlines": vlines, "last": last})
    return out


def mission_scopes(L, mrec, resolve):
    """R1 canonicalization of every listed manifest: [{path, full, id, digests}] (id None when
    unreadable or malformed, reported mission-scope-mismatch)."""
    mans = []
    wset = mrec.get("wset") or set()
    for p in mrec["scope"]:
        full = resolve(p)
        if os.path.normpath(full) in wset:      # packet-errors R2: a withdrawn manifest is out of every check
            continue
        try:
            sid, digests = scope_canon(full)
        except ScopeError as e:
            L.fail("mission-scope-mismatch", f"manifest {p}: {e}", man=[p])
            sid, digests = None, {}
        mans.append({"path": p, "full": full, "id": sid,
                     "names": {k.decode("utf-8", "backslashreplace"): v for k, v in digests.items()},
                     "frozen": None, "frozen_edges": []})
    for w in mrec.get("withdrawn") or []:       # a replacement with the withdrawn manifest's scope id
        try:
            wid = scope_canon(resolve(w))[0]
        except ScopeError:
            continue
        for m in mans:
            if m["id"] == wid:
                L.fail("mission-scope-mismatch", f"manifest {m['path']}: canonicalizes to {wid}, the scope id of withdrawn "
                                                 f"manifest {w} (binding is keyed by scope id; a defective packet is not "
                                                 "replaced by itself)", man=[m["path"], w], pend=True)
    return mans


def chain_of(bound, mans):
    """R2: the bound reviews whose row scope_id equals a listed mission scope id, in Review:
    line order, each with the first listed index it matched."""
    ids = [m["id"] for m in mans]
    out = []
    for b in bound:
        sid = b["row"].get("scope_id")
        if isinstance(sid, str) and sid in ids:
            out.append(dict(b, idx=ids.index(sid)))
    return out


def superseded_pins(chain, home, resolve):
    """R5 (A01): on a note whose Mission: line carries scope=, PR #9's per-review pin applies to
    a slug only in the latest chain review (Review: line order) whose file names it. Returns
    ({Review line index: set of slugs not pinned}, {Review line index: {slug: superseding
    session}} for the APPROVE pins that would have been stale)."""
    skip, report = {}, {}
    for p, k in enumerate(chain):
        for s, v in k["last"].items():
            later = [j for j in chain[p + 1:] if s in j["last"]]
            if not later:
                continue
            skip.setdefault(k["i"], set()).add(s)
            if v != "APPROVE":
                continue
            scope = k["row"].get("scope")
            try:
                _, dg = scope_canon(resolve(scope)) if isinstance(scope, str) else (None, {})
            except ScopeError:
                dg = {}
            want = dg.get(b"PRD-" + s.encode() + b".md")
            cur = first_holder(home, PRD_DIRS, f"PRD-{s}.md")
            got = file_sha(cur) if cur else None
            if want is not None and got is not None and got != want:
                report.setdefault(k["i"], {})[s] = later[-1]["rv"]["session"]
    return skip, report


def header_contracts(hd):
    """(name, contract path) pairs of an edges header's external entries."""
    out = []
    for x in hd["external"]:
        if isinstance(x, dict):
            c = x.get("contract")
            for y in (c if isinstance(c, list) else [c]):
                if isinstance(y, str) and y.strip():
                    out.append((x.get("name"), y))
    return out


def chain_review(L, mrec, mans, chain, rows, governed, task, adv, states, reviews, home, resolve):
    """PRD-dream-mission-chain-review R1-R4, R5 (mission pin), R6 and the R8 JSON fields for
    an entry whose Mission: line carries (or inherits) scope=. Returns the mission JSON fields
    and the dependent map {PRD basename: [reasons]}."""
    hd = mrec["header"]
    eb = os.path.basename(mrec["edges"]) if mrec["edges"] else None
    mxb = os.path.basename(adv[1]) if adv and adv[0] == "matrix" else None
    last = len(mans) - 1
    seen = set()

    psem = bool((mrec.get("opts") or {}).get("psem"))

    def once(fid, detail, **kw):
        if detail not in seen:
            seen.add(detail)
            L.fail(fid, detail, **kw)

    # R1 per manifest: its frozen edges copy, completeness against that header (the last also
    # against the live header) and contract basenames
    for k, m in enumerate(mans):
        if m["id"] is None:
            continue
        mp = [m["path"]]
        copy, _, err = frozen_edges_copy(m["full"], eb)
        if err:
            once("mission-scope-mismatch", f"manifest {m['path']}: {err}", man=mp)
        else:
            fh, fe, fpr = read_edges(copy, copy)
            if fh is None:
                once("mission-scope-mismatch", f"manifest {m['path']}: frozen edges copy {copy} has no header", man=mp)
            for fid, d in fpr:      # matrix-per-manifest R1 on a frozen header (its other fields stay unread here)
                if fid == "edge-grammar" and ": field matrix: " in d:
                    once("edge-grammar", f"manifest {m['path']}: {d}", man=mp)
            m["frozen"], m["frozen_edges"] = fh, fe
        mxm, mxl, mslugs, mxp = manifest_matrix(m, mrec, adv, states, resolve)
        m["matrix"] = mxm
        heads = ([("frozen", m["frozen"])] if m["frozen"] else []) + ([("live", hd)] if k == last and hd else [])
        # packet-errors R1: the defects the manifest's frozen evaluation carries (its state when its review
        # launched): those its frozen header raises, and the needs no header supplies (the edges file, and
        # the matrix unless the pending entry's own adversarial= names it, S3: the pending clause is read
        # first, so such a frozen line records no key). A live-header error is held only when it states
        # one of them.
        carried = {("need", eb)} | ({("need", mxm)} if not (psem and mxp) else set())

        def fresh(label, key):          # True: a live-header defect the frozen evaluation lacks (sets the exit)
            if label == "frozen":
                carried.add(key)
            return label == "live" and key not in carried
        for hi, (label, h) in enumerate(heads):
            cons = header_contracts(h)
            byb = {}
            for nm, cp in cons:
                byb.setdefault(os.path.basename(cp), []).append(cp)
            for b, cps in byb.items():
                if len(set(cps)) > 1:
                    once("mission-scope-mismatch", f"manifest {m['path']}: {label} edges header: contract paths "
                                                   f"{' and '.join(sorted(set(cps)))} share the basename {b}",
                         man=mp, pend=fresh(label, ("dup", b)))
                if b in h["prds"] or b in h["packet"]:
                    once("mission-scope-mismatch", f"manifest {m['path']}: {label} edges header: contract path "
                                                   f"{cps[0]} and the member {b} share the basename {b}",
                         man=mp, pend=fresh(label, ("clash", b)))
            need = [(b, "prds member") for b in h["prds"]] + [(b, "packet member") for b in h["packet"]]
            need += ([(mxm, None)] if mxm and hi == 0 else []) + ([(eb, "edges file")] if eb else [])
            need += [(os.path.basename(cp), f"external {nm} contract copy") for nm, cp in cons]
            for b, kind in need:
                if b not in m["names"]:
                    once("mission-scope-incomplete", f"manifest {m['path']}: lists no {b} ({mxl})" if kind is None else
                         f"manifest {m['path']}: lists no {b} ({kind} of the {label} edges header)",
                         man=mp, pend=(psem and kind is None and mxp) or fresh(label, ("need", b)))
        # matrix-per-manifest R3: the last manifest's frozen header, and the live header, name the
        # note's adversarial= matrix
        for label, h in (heads if k == last else []):
            if h.get("matrix") and h["matrix"] != mxb:
                where = f"manifest {m['path']}: frozen edges header" if label == "frozen" else f"{mrec['edges']}: live edges header"
                once("mission-scope-mismatch", f"{where} names matrix {h['matrix']}; the note's adversarial= names "
                                               f"{mxb or 'no matrix (adversarial=skipped:)'}",
                     man=mp if label == "frozen" else None, pend=psem)
        # matrix-per-manifest R5b: the matrix a header names is the copy beside the manifest, at its
        # listed digest, and passes the matrix grammar for the first-listing entry's State slugs
        # that are prds members of this header (a legacy header keeps the basename-only check)
        fhd = m["frozen"]
        if fhd and fhd.get("matrix") and mxm in m["names"]:
            cp = os.path.join(os.path.dirname(m["full"]), mxm)
            got = file_sha(cp)
            if got is None:
                once("adversarial-missing", f"manifest {m['path']}: matrix copy {cp} absent or unreadable "
                                            f"(the frozen edges header names {mxm})", man=mp)
            elif got != m["names"][mxm]:
                once("adversarial-missing", f"manifest {m['path']}: matrix copy {cp} sha256 {got[:12]} differs from "
                                            f"the manifest's {m['names'][mxm][:12]}", man=mp)
            else:
                sub = Lint()
                sl = [s for s in dict.fromkeys(mslugs) if f"PRD-{s}.md" in fhd["prds"]]
                # packet-errors R1 (--pending): the last manifest's review gives every header prds member a verdict
                hx = [b[len("PRD-"):-len(".md")] for b in fhd["prds"]] if psem and k == last else []
                lint_matrix(sub, cp, cp, sl, extra=[s for s in hx if s not in sl])
                for fid, d in sub.findings:
                    once(fid, f"manifest {m['path']}: {d}", man=mp)
    ids = [m["id"] for m in mans]
    # R2: binding, line order against manifest index, launch order within one index
    if not chain and governed and task is not None:
        vals = sorted({str(r.get("scope_id")) for r in rows if r.get("decision") == "launch" and r.get("skill") == "dream"
                       and r.get("task_id") == task and r.get("role") == "review"})
        L.fail("mission-review-missing", f"no Review: line binds to a listed mission scope id (listed "
                                         f"{', '.join(str(x) for x in ids)}; reviewer rows' scope_id {', '.join(vals) or 'none'})")
    order_ok = True
    for p in range(1, len(chain)):
        a, b = chain[p - 1], chain[p]
        if b["idx"] < a["idx"]:
            order_ok = False
            L.fail("mission-review-missing", f"{b['rv']['file']}: bound to manifest {b['idx'] + 1} ({mans[b['idx']]['path']}) "
                                             f"but listed after {a['rv']['file']}, bound to manifest {a['idx'] + 1}")
        elif b["idx"] == a["idx"]:
            ta, tb = launch_ts(a["row"]), launch_ts(b["row"])
            if ta is None or tb is None or tb < ta:
                order_ok = False
                L.fail("mission-review-missing", f"{a['rv']['file']} (launched {a['row'].get('ts')}) is listed before "
                                                 f"{b['rv']['file']} (launched {b['row'].get('ts')}) on manifest {a['idx'] + 1}; "
                                                 "chain reviews of one manifest are listed in launch order")
    # R3 verdict lines and the sidecar binding; R4 the findings sidecar
    since = parse_iso(SIDECAR_BINDING_SINCE)
    ids_seen = {}
    for c in chain:
        f, res = c["rv"]["file"], c["rv"]["result"]
        c["verdict"], c["findings"], c["advisory"], c["sidecar_bound"] = None, [], [], False
        c["named"] = []         # every non-advisory row naming an id, well-formed or not (the sweep's R1)
        fl = [norm_line(x) for x in (c["text"] or "").split("\n")]
        ml = [" ".join(t.split()) for t in fl if t.startswith("mission=")]
        mm = MISSION_LINE_RE.fullmatch(ml[0]) if len(ml) == 1 else None
        fv = mm.group(1) if mm and mm.group(2) == c["rv"]["session"] else None
        if fv is None:
            L.fail("mission-verdict-missing", f"{f}: {len(ml)} mission= line(s); exactly one 'mission=<APPROVE|FIX|REJECT> "
                                              f"{c['rv']['session']}' is required")
        cap = None
        if not res:
            L.fail("mission-verdict-missing", f"{f}: no result= capture on its Review: line")
        else:
            try:
                d = json.loads(read_text(resolve(res)))
                cap = str(d["result"]) if isinstance(d, dict) and "result" in d else None
            except (OSError, ValueError):
                cap = None
            if cap is None:
                L.fail("mission-verdict-missing", f"{f}: result {res} unreadable or holds no result text")
        rl = [" ".join(norm_line(x).split()) for x in cap.split("\n")] if cap is not None else []
        if mm and mm.group(2) == c["rv"]["session"] and cap is not None:
            rm = [t for t in rl if t.startswith("mission=")]
            if rm != [ml[0]]:
                L.fail("mission-verdict-missing", f"{f}: result {res} carries {rm or 'no mission= line'}, the file '{ml[0]}'")
            else:
                c["verdict"] = mm.group(1)
        sc = f + ".findings.jsonl"
        scfull = resolve(c["rv"]["file"]) + ".findings.jsonl"
        unreadable = None       # only a missing sidecar is absent (findings=none); any other read error is not
        try:
            with open(scfull, "rb") as fh:
                sbytes = fh.read()
        except FileNotFoundError:
            sbytes = None
        except OSError as e:
            sbytes, unreadable = None, e.strerror or type(e).__name__
            L.fail("mission-finding-incomplete", f"{sc}: unreadable ({unreadable}); only a missing sidecar counts as absent")
        fx = [t for t in rl if t.startswith("findings=")]
        read = sbytes
        if not fx:
            lt = launch_ts(c["row"])
            if not (lt is not None and since is not None and lt < since):
                L.fail("mission-finding-incomplete", f"{f}: result {res or '(no result=)'}: no findings= line "
                                                     f"(launched {c['row'].get('ts')}, not before {SIDECAR_BINDING_SINCE})")
        elif len(fx) > 1 or not FINDINGS_LINE_RE.fullmatch(fx[0]):
            L.fail("mission-finding-incomplete", f"{f}: result {res}: {len(fx)} findings= line(s); exactly one "
                                                 "'findings=<none|sha256>' is required")
        elif unreadable is None:    # an unreadable sidecar binds to no findings= line (refused above)
            want = fx[0][len("findings="):].strip()
            got = "none" if sbytes is None else hashlib.sha256(sbytes).hexdigest()
            if want == got:
                c["sidecar_bound"] = True
            else:
                read = None          # a sidecar that differs from a carried digest is read by nothing
                L.fail("mission-finding-incomplete", f"{f}: result {res}: findings={want} but the sidecar {sc} is "
                                                     f"{'absent' if sbytes is None else 'sha256 ' + got}")
        rows_sc = []
        if read is not None:
            for n, ln in enumerate(read.decode("utf-8", "replace").split("\n"), 1):
                if ln.strip():
                    try:
                        rows_sc.append((n, json.loads(ln)))
                    except ValueError:
                        rows_sc.append((n, None))
        if fv in ("FIX", "REJECT") and not rows_sc and (read is not None or sbytes is None):
            L.fail("mission-finding-incomplete", f"{sc}: absent, unreadable or empty under mission={fv}")
        fh = mans[c["idx"]]["frozen"] or hd
        prset = set(fh["prds"]) if fh else set()
        exts = set(fh["external_names"]) if fh else set()
        mine = set()
        for n, r in rows_sc:
            def bad(field, why, n=n):
                L.fail("mission-finding-incomplete", f"{sc}: row {n}: field {field}: {why}")
            if not isinstance(r, dict):
                bad("(not a JSON object)", "each sidecar row is one JSON object")
                continue
            ok = True
            adv_row = "accepts" in r
            rid = r.get("id")
            if not isinstance(rid, str) or not rid.strip():
                bad("id", "absent or empty")
                ok = False
            elif rid in mine:
                bad("id", f"{rid} repeats in this sidecar")
                ok = False
            else:
                mine.add(rid)
                if rid in ids_seen:
                    L.fail("mission-finding-incomplete", f"finding id {rid} in {ids_seen[rid]} and {sc}: an id names its "
                                                         "issuing review; a re-raised finding takes a new id")
                    ok = False
            cls = r.get("class")
            if cls not in FINDING_CLASSES:
                bad("class", f"{cls!r} is not one of {', '.join(FINDING_CLASSES)}")
                ok = False
            elif adv_row and cls != "provenance":
                bad("class", "an advisory accepts row is class provenance")
                ok = False
            for k in ("counterexample", "correction", "control"):
                if not (isinstance(r.get(k), str) and r[k].strip()):
                    bad(k, "absent or empty")
                    ok = False
            pr, co = r.get("prds"), r.get("consumers")
            if not isinstance(pr, list) or (not adv_row and not pr) or not all(x in prset for x in pr):
                bad("prds", "not a non-empty list of mission prds members" if not adv_row else "not a list of mission prds members")
                ok = False
            if (not isinstance(co, list) or not all(x in prset or (isinstance(x, str) and x.startswith("external:")
                                                                    and x[9:] in exts) for x in co)
                    or (not co and not adv_row and cls != "provenance")):
                bad("consumers", "not a list of prds members or declared external:<name> (empty only for class provenance)")
                ok = False
            if adv_row:
                ac = r.get("accepts")
                if not isinstance(ac, list) or not ac or not all(isinstance(x, str) and x.strip() for x in ac):
                    bad("accepts", "not a non-empty list of finding ids")
                    ok = False
            if isinstance(rid, str) and rid.strip() and rid not in ids_seen:
                ids_seen[rid] = sc
                if not adv_row:
                    c["named"].append(r)
            if ok:
                (c["advisory"] if adv_row else c["findings"]).append(r)
    # the mission verdict: the last chain review, in line (launch) order, of the last listed manifest
    vr = None
    if order_ok and chain and chain[-1]["idx"] == last:
        vr = chain[-1]
    verdict = vr["verdict"] if vr else None
    # R5: the whole packet pinned on mission=APPROVE
    if verdict == "APPROVE":
        names = mans[vr["idx"]]["names"]
        files = []
        for b in (hd["prds"] if hd else []):
            files.append((b, first_holder(home, PRD_DIRS, b), True))
        for tok in ("edges", "repairs"):
            if mrec[tok]:
                files.append((os.path.basename(mrec[tok]), resolve(mrec[tok]), True))
        if mxb:
            files.append((mxb, resolve(adv[1]), True))
        for b in (hd["packet"] if hd else []):
            hold_ = first_holder(home, ("visions", os.path.join("notes", "missions"), os.path.join("notes", "reviews")), b)
            if hold_:
                files.append((b, hold_, False))
        for b, path, _ in files:
            want = names.get(b)
            got = file_sha(path) if path else None
            if got is None:
                L.fail("mission-snapshot-stale", f"{b}: absent or unreadable (manifest {mans[vr['idx']]['path']} "
                                                 f"digest {want or 'none'})")
            elif want is None:
                L.fail("mission-snapshot-stale", f"{b}: current {got}; manifest {mans[vr['idx']]['path']} lists no digest")
            elif got != want:
                L.fail("mission-snapshot-stale", f"{b}: current {got} differs from manifest {mans[vr['idx']]['path']}'s {want}")
    # R8: unlisted review sessions (a report), the latest-launched of the last manifest (R6)
    named = {rv["session"] for rv in reviews}
    rrows = [r for r in rows or [] if r.get("decision") == "launch" and r.get("skill") == "dream"
             and r.get("task_id") == task and r.get("role") == "review"] if governed else []
    unlisted = [{"session": r.get("session"), "scope_index": ids.index(r.get("scope_id")),
                 "launch_ts": r.get("ts")} for r in rrows
                if r.get("scope_id") in ids and r.get("scope_id") is not None and r.get("session") not in named]
    lrows = [r for r in rrows if ids and ids[-1] is not None and r.get("scope_id") == ids[-1]]
    latest = None
    if lrows:
        unparsed = [r for r in lrows if launch_ts(r) is None]
        latest = unparsed[-1] if unparsed else max(lrows, key=launch_ts)
    # R6: the dependent set
    prds = hd["prds"] if hd else []
    deps = {}

    def hold(b, reason):
        if b in prds and reason not in deps.setdefault(b, []):
            deps[b].append(reason)
    blanket = None
    if not chain:
        blanket = "no bound chain review"
    elif vr is None:
        blanket = "no chain review of the last manifest"
    elif latest is not None and latest.get("session") not in named:
        blanket = f"unlisted later review {latest.get('session')}"
    if blanket:
        for b in prds:
            hold(b, blanket)
    for e in mrec["edge_list"]:
        if e["status"] == "unknown":
            hold(e["producer"], f"unknown edge {e['id']}")
            hold(e["consumer"], f"unknown edge {e['id']}")
    if chain:
        lc = chain[-1]
        for r in lc["findings"]:
            nm = [x for x in r["prds"] + r["consumers"] if x in prds]
            for b in nm:
                hold(b, f"finding {r['id']}")
            for e in mans[lc["idx"]]["frozen_edges"]:
                if e["status"] in ("known", "external"):
                    if e["producer"] in nm:
                        hold(e["consumer"], f"finding {r['id']}, edge {e['id']}")
                    if e["consumer"] in nm:
                        hold(e["producer"], f"finding {r['id']}, edge {e['id']}")
    for b in prds:
        slug = b[len("PRD-"):-len(".md")]
        v = next((c["last"][slug] for c in reversed(chain) if slug in c["last"]), None)
        if v is None:
            hold(b, "no per-PRD verdict")
        elif v in ("FIX", "REJECT"):
            hold(b, f"per-PRD verdict {v}")
    fields = {"scope_ids": ids, "scope_id": ids[-1] if ids else None,
              "chain_reviews": [{"session": c["rv"]["session"], "verdict": c["verdict"] if order_ok else None,
                                 "file": c["rv"]["file"], "scope_id": ids[c["idx"]], "scope_index": c["idx"],
                                 "launch_ts": c["row"].get("ts"), "sidecar_bound": c["sidecar_bound"]} for c in chain],
              "verdict": verdict, "findings": len(vr["findings"]) if vr else 0,
              "unlisted_review_sessions": unlisted}
    return fields, deps, vr


def approval(L, mrec, deps, verdict, states):
    """R6 refusals: mission=APPROVE beside an unknown edge; a dependent slug reaching eligible."""
    unk = [e["id"] for e in mrec["edge_list"] if e["status"] == "unknown"]
    if verdict == "APPROVE" and unk:
        L.fail("mission-approval-blocked", f"mission=APPROVE beside unknown edge(s) {', '.join(unk)} of {mrec['edges']}")
    for s, vals in states.items():
        b = f"PRD-{s}.md"
        if "eligible" in vals and b in deps:
            L.fail("mission-approval-blocked", f"slug {s}=eligible: dependent ({'; '.join(deps[b])})")


SWEEP_IDS = ("repair-grammar", "mission-repairs-missing", "repair-duplicate", "repair-missing",
             "repair-class-mismatch", "sweep-missing", "repair-author-mismatch", "repair-hash-mismatch",
             "repair-scope-mismatch", "affected-consumer-unreviewed", "repair-declined-unaccepted")
REPAIR_FIELDS = ("finding", "class", "author_session", "before", "after", "changed", "sweep", "disposition")
DISPOSITIONS = ("repaired", "declined", "amended")


def names_of(f, *keys):
    """The string members of a sidecar row's prds and consumers lists (or of the named keys);
    a malformed row (chain-review R4 refuses it on its own) contributes what it names."""
    out = []
    for k in keys or ("prds", "consumers"):
        v = f.get(k)
        out += [x for x in v if isinstance(x, str)] if isinstance(v, list) else []
    return out


def repair_sweep(L, mrec, mans, chain, bound, rows, governed, task, entries, ei, route, vr, deps, home, resolve):
    """PRD-dream-failure-class-sweep R1-R8 for an entry whose Mission: line carries scope=.
    Returns the mission.repairs JSON object, or None when nothing here applies (no repairs=,
    no chain-review finding followed by a later chain review, no digest moving between two
    listed manifests: the JSON then equals the previous PRD's). Adds R7's holds to deps."""
    tok = mrec["repairs"]
    rbase = os.path.basename(tok) if tok else None
    hd = mrec["header"]
    ids = [m["id"] for m in mans]
    # R1/R2: a finding is a non-advisory sidecar row naming an id, its issuing review the first
    # sidecar holding the id (chain-review R4 refuses a re-use, and a malformed row on its own)
    need = [(p, f) for p, c in enumerate(chain) if p + 1 < len(chain) for f in c["named"]]
    opts = mrec.get("opts") or {}
    pkt = bool(opts.get("pkt"))
    # packet-errors R1: the review about to launch follows the latest listed review (checked beside need,
    # never changing which path the full lint takes)
    ext = [(len(chain) - 1, f) for f in chain[-1]["named"]] if pkt and chain and mans else []

    def fol_of(p):
        """(detail suffix, the manifest the following review reads) for a finding of chain[p]."""
        if p + 1 < len(chain):
            return None, mans[chain[p + 1]["idx"]]["path"]
        return f"the review about to launch on {mans[-1]['path']} follows it", mans[-1]["path"]
    wset, dropset, voided = mrec.get("wset") or set(), mrec.get("dropset") or set(), {}
    mrec["voided"] = voided

    def moved():
        for k in range(len(mans) - 1):
            a, b = mans[k], mans[k + 1]
            if a["id"] is not None and b["id"] is not None:
                if any(n in b["names"] and b["names"][n] != dg for n, dg in a["names"].items() if n != rbase):
                    return True
        return False
    def no_token(pairs):
        for p, f in pairs:
            sfx, fm = fol_of(p)
            L.fail("repair-missing", f"finding {f['id']} of {chain[p]['rv']['file']}: no repairs= token on the "
                                     "Mission: line (carried or inherited)" + (f" ({sfx})" if sfx else ""), man=[fm],
                   absent=("finding", f["id"], chain[p]["row"]))
    if not tok and not need and not moved():
        no_token(ext)
        return None
    out = {"file": tok, "rows": 0, "repaired": 0, "declined": [], "amended": [], "pending_after": False,
           "changed": [], "swept_edges": 0, "edges_added": [], "edges_removed": []}
    if not tok and need:                 # R2 (r4 F27): the check never waits for the token
        no_token(need + ext)
        return out
    issuer = {f["id"]: p for p, c in enumerate(chain) for f in c["named"]}
    fobj = {f["id"]: f for c in chain for f in c["named"]}
    prds = set(hd["prds"]) if hd else set()

    def man_index(p):
        if not isinstance(p, str) or not p.strip():
            return None
        n = os.path.normpath(resolve(p))
        return next((k for k, m in enumerate(mans) if os.path.normpath(m["full"]) == n), None)

    # R1: the file and its rows
    recs = []
    if tok:
        try:
            with open(resolve(tok), "rb") as fh:
                text = fh.read().decode("utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
        if text is None or not text.strip():
            L.fail("mission-repairs-missing", f"{tok}: absent, unreadable or empty (repairs= on the Mission: line)")
            text = ""
        for n, ln in enumerate(text.split("\n"), 1):
            if not ln.strip():
                continue
            try:
                r = json.loads(ln)
            except ValueError:
                r = None
            if not isinstance(r, dict):
                L.fail("repair-grammar", f"{tok}: row {n}: not a JSON object", rows=[n])
                continue
            ends = [os.path.normpath(resolve(r[k])) for k in ("before", "after") if isinstance(r.get(k), str) and r[k].strip()]
            if any(e in dropset for e in ends):     # the reason pass: a row of a later manifest did not exist yet
                continue
            if any(e in wset for e in ends):        # packet-errors R2: a row naming a withdrawn manifest is void
                for e in dict.fromkeys(x for x in ends if x in wset):
                    voided.setdefault(e, []).append(n)
                continue
            ok = True

            def bad(field, why, n=n):
                L.fail("repair-grammar", f"{tok}: row {n}: field {field}: {why}", rows=[n])
            for k in REPAIR_FIELDS:
                if k not in r:
                    bad(k, "missing")
                    ok = False
            disp = r.get("disposition")
            if "disposition" in r and disp not in DISPOSITIONS:
                bad("disposition", f"{disp!r} is not one of {', '.join(DISPOSITIONS)}")
                ok = False
            fid, cls = r.get("finding"), r.get("class")
            for k in ("author_session", "before", "after"):
                if k in r and not (isinstance(r[k], str) and r[k].strip()):
                    bad(k, "not a non-empty string")
                    ok = False
            for k in ("changed", "sweep"):
                if k in r and not (isinstance(r[k], list) and all(isinstance(x, str) and x.strip() for x in r[k])):
                    bad(k, "not a list of names")
                    ok = False
            reason = r.get("reason")
            if disp in ("declined", "amended") and not (isinstance(reason, str) and reason.strip()):
                bad("reason", f"a {disp} row needs a non-empty reason")
                ok = False
            if disp == "amended":
                if fid is not None or cls is not None:
                    bad("finding", "an amended row answers no finding: finding and class are null")
                    ok = False
                if isinstance(r.get("changed"), list) and not r["changed"]:
                    bad("changed", "an amended row names what moved")
                    ok = False
            elif "finding" in r:
                # on an ungoverned host no chain review binds (chain-review R2): an id is undecidable there
                if not (isinstance(fid, str) and fid.strip()) or (governed and fid not in fobj):
                    bad("finding", f"{fid!r} is no finding id of this note's chain-review sidecars")
                    ok = False
                if "class" in r and cls not in FINDING_CLASSES:
                    bad("class", f"{cls!r} is not one of {', '.join(FINDING_CLASSES)}")
                    ok = False
                ch = r.get("changed")
                if ok and fid in fobj and disp == "repaired" and cls != "provenance" and isinstance(ch, list):
                    f = fobj[fid]
                    allowed = {x for x in names_of(f) if x in prds}
                    names = {x[len("external:"):] for x in names_of(f, "consumers") if x.startswith("external:")}
                    allowed |= {os.path.basename(cp) for nm, cp in (header_contracts(hd) if hd else []) if nm in names}
                    if not ch:
                        L.fail("repair-grammar", f"{tok}: row {n}: finding {fid}: changed is empty on a repaired {cls} "
                                                 "row (a repair that changes no bytes is declined with a reason)", rows=[n])
                        ok = False
                    elif not set(ch) & allowed:
                        L.fail("repair-grammar", f"{tok}: row {n}: finding {fid}: changed names none of "
                                                 f"{', '.join(sorted(allowed))} (the PRDs and contract the finding names)",
                               rows=[n])
                        ok = False
            recs.append({"n": n, "r": r, "ok": ok, "fid": fid if isinstance(fid, str) else None, "disp": disp,
                         "bi": man_index(r.get("before")), "ai": man_index(r.get("after")),
                         "changed": [x for x in r.get("changed") or [] if isinstance(x, str)] if isinstance(r.get("changed"), list) else [],
                         "sweep": [x for x in r.get("sweep") or [] if isinstance(x, str)] if isinstance(r.get("sweep"), list) else []})
    out["rows"] = len(recs)
    out["repaired"] = sum(1 for x in recs if x["disp"] == "repaired")
    # duplicates (R1): one row per finding, or one declined followed by one repaired
    byf = {}
    for x in recs:
        if x["fid"] is not None and x["disp"] in ("repaired", "declined"):
            byf.setdefault(x["fid"], []).append(x)
    for fid, xs in byf.items():
        seq = [x["disp"] for x in xs]
        if seq not in (["repaired"], ["declined"], ["declined", "repaired"]):
            L.fail("repair-duplicate", f"finding {fid}: rows {', '.join(str(x['n']) for x in xs)} ({', '.join(seq)}); "
                                       "one row, or one declined row followed by one repaired row", rows=[x["n"] for x in xs])
    ams = [x for x in recs if x["disp"] == "amended"]
    for i, x in enumerate(ams):
        for y in ams[i + 1:]:
            if (x["r"].get("before"), x["r"].get("after")) == (y["r"].get("before"), y["r"].get("after")):
                for b in sorted(set(x["changed"]) & set(y["changed"])):
                    L.fail("repair-duplicate", f"amended rows {x['n']} and {y['n']} of ({x['r'].get('before')}, "
                                               f"{x['r'].get('after')}) both name {b}", rows=[x["n"], y["n"]])
    sup = {fid for fid, xs in byf.items() if [x["disp"] for x in xs] == ["declined", "repaired"]}
    # R1: the repairs file is listed in every manifest later than any row's before
    bis = [x["bi"] for x in recs if x["bi"] is not None]
    if tok and bis:
        for k in range(min(bis) + 1, len(mans)):
            if mans[k]["id"] is not None and rbase not in mans[k]["names"]:
                L.fail("mission-scope-incomplete", f"manifest {mans[k]['path']}: lists no {rbase} (the repairs file; "
                                                   f"a row's before is {mans[min(bis)]['path']})",
                       man=[mans[k]["path"]], rows=[x["n"] for x in recs if x["bi"] is not None and x["bi"] < k])
    # R2: rows required, declines accepted
    named = {x["fid"] for x in recs if x["fid"] is not None}     # a malformed row still names its finding
    if not tok:
        no_token([(p, f) for p, f in ext if f["id"] not in named])
    for p, f in need + (ext if tok else []):
        if f["id"] not in named:
            sfx, fm = fol_of(p)
            L.fail("repair-missing", f"finding {f['id']} of {chain[p]['rv']['file']}: no row in {tok} "
                                     + (f"({sfx})" if sfx else f"(its following review {chain[p + 1]['rv']['file']} exists)"),
                   man=[fm], absent=("finding", f["id"], chain[p]["row"]))
    accepted = {}
    for fid, xs in byf.items():
        if xs[0]["disp"] != "declined" or fid in sup or fid not in issuer:
            continue
        by = next((c["rv"]["session"] for c in chain[issuer[fid] + 1:] for a in c["advisory"]
                   if fid in a.get("accepts", [])), None)
        accepted[fid] = by
        if by is None:
            L.fail("repair-declined-unaccepted", f"finding {fid}: declined in {tok} row {xs[0]['n']}; no later chain "
                                                 f"review's sidecar holds an advisory row accepting it (last chain "
                                                 f"review {chain[-1]['rv']['file'] if chain else 'none'})")
    out["declined"] = [{"finding": fid, "reason": xs[0]["r"].get("reason"), "accepted_by": accepted.get(fid),
                        "superseded": fid in sup} for fid, xs in byf.items() if xs[0]["disp"] == "declined"]
    out["amended"] = [{"reason": x["r"].get("reason"), "changed": x["changed"], "before": x["r"].get("before"),
                       "after": x["r"].get("after")} for x in ams]
    # R4: the author lineage
    if governed:
        admitted = {r.get("session") for r in rows or [] if r.get("decision") == "launch" and r.get("skill") == "dream"
                    and r.get("task_id") == task and r.get("role", "author") == "author"}
    else:
        admitted = {route["session"]} if route else set()
        for e in entries[:ei]:
            if task is not None and entry_task(e) == task:
                for ln in e["lines"]:
                    mm = re.match(r"^Route:.*\bsession=(\S+)", ln)
                    if ln.startswith("Route:") and mm:
                        admitted.add(mm.group(1))
    canon = {}

    def canon_of(x, field):
        p = x["r"].get(field)
        if p not in canon:
            try:
                canon[p] = scope_canon(resolve(p))
            except ScopeError as e:
                canon[p] = e
        c = canon[p]
        if isinstance(c, ScopeError):
            L.fail("repair-hash-mismatch", f"row {x['n']}: {field} {p}: {c}", rows=[x["n"]])
            return None
        return c[0], {k.decode("utf-8", "backslashreplace"): v for k, v in c[1].items()}
    added, removed, swept, aff_of = set(), set(), set(), {}
    for x in recs:
        r, n, fid = x["r"], x["n"], x["fid"]
        swept |= set(x["sweep"])
        a_s = r.get("author_session")      # each check reads only its own fields (refusals stay independent)
        if isinstance(a_s, str) and a_s.strip() and a_s not in admitted:
            L.fail("repair-author-mismatch", f"row {n}: author_session {a_s} is not an author of Task {task} "
                                             f"(admitted: {', '.join(sorted(s for s in admitted if s)) or 'none'})", rows=[n])
        bi, ai = x["bi"], x["ai"]
        bcopy = mans[bi]["frozen_edges"] if bi is not None else []
        bhead = (mans[bi]["frozen"] if bi is not None else None) or hd
        bprds = set(bhead["prds"]) if bhead else prds
        # R3: class and sweep (affected graph at the before digest)
        if x["disp"] == "amended":
            aff, cls = set(x["changed"]) & bprds, None
        elif fid in fobj and x["disp"] in ("repaired", "declined"):
            f = fobj[fid]
            aff, cls = set(names_of(f)), r.get("class")
            if cls != f.get("class"):
                L.fail("repair-class-mismatch", f"finding {fid}: row {n} class {cls}, the finding's {f.get('class')}", rows=[n])
        else:
            aff, cls = None, None
        if aff is not None and cls != "provenance" and bi is not None:
            want = [e["id"] for e in bcopy if e["producer"] in aff or e["consumer"] in aff]
            miss = [e for e in want if e not in x["sweep"]]
            if miss:
                L.fail("sweep-missing", f"{'finding ' + fid if fid else 'amended row'} (row {n}): sweep lacks "
                                        f"{', '.join(miss)} (incident to {', '.join(sorted(aff))})", rows=[n])
        if bi is not None and ai is not None:
            ea = {e["id"] for e in mans[ai]["frozen_edges"]}
            eb_ = {e["id"] for e in bcopy}
            added |= ea - eb_
            removed |= eb_ - ea
        # R5: before/after binding, the following review, the changed digests
        if not all(isinstance(r.get(k), str) and r[k].strip() for k in ("before", "after")) or x["disp"] not in DISPOSITIONS:
            continue
        if x["disp"] == "amended":
            anchor = None
            fol = next((c for c in chain if ai is not None and c["idx"] >= ai), None)
        elif fid in issuer:
            anchor = issuer[fid]
            fol = chain[anchor + 1] if anchor + 1 < len(chain) else None
        else:                               # no issuing review (ungoverned host, or an unknown id: R1)
            anchor, fol = None, None
        cb, ca = canon_of(x, "before"), canon_of(x, "after")
        if bi is None:
            L.fail("repair-scope-mismatch", f"row {n}: before {r['before']} is not a listed scope= manifest", rows=[n])
        elif anchor is not None and cb is not None:
            iss = chain[anchor]
            okids = ([ids[c["idx"]] for c in chain[anchor + 1:]] if x["disp"] == "repaired" and fid in sup
                     else [ids[iss["idx"]]])
            if cb[0] not in okids:
                L.fail("repair-scope-mismatch", f"row {n} (finding {fid}): before {r['before']} canonicalizes to {cb[0]}; "
                                                f"the issuing review {iss['rv']['file']} is bound to {ids[iss['idx']]}", rows=[n])
        same_ok = x["disp"] == "declined" and ai is not None and ai == bi and fol is not None and fol["idx"] == ai
        if bi is not None and (ai is None or not (ai == bi + 1 or same_ok)):
            L.fail("repair-scope-mismatch", f"row {n}: after {r['after']} is not the listed scope= manifest following "
                                            f"before {r['before']}", rows=[n])
        elif fol is None:
            out["pending_after"] = True
        elif ai is not None and fol["idx"] < ai:
            L.fail("repair-scope-mismatch", f"row {n}: its following review {fol['rv']['file']} is bound to "
                                            f"{ids[fol['idx']]}, earlier than after {r['after']} ({ids[ai]})", rows=[n])
        if cb is not None and ca is not None and not (same_ok and not x["changed"]):
            mxo = mans[bi].get("matrix") if bi is not None else None
            mxn = mans[ai].get("matrix") if ai is not None else None
            for b in x["changed"]:
                if mxo != mxn and b in (mxo, mxn):     # matrix-per-manifest R4: old against before, new against after
                    if b == mxo and b not in cb[1]:
                        L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from before {r['before']}",
                               rows=[n])
                    elif b == mxn and b not in ca[1]:
                        L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from after {r['after']}",
                               rows=[n])
                    continue
                if b not in cb[1]:
                    L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from before {r['before']}", rows=[n])
                elif b not in ca[1]:
                    L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from after {r['after']}", rows=[n])
                elif cb[1][b] == ca[1][b]:
                    L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, digests equal in {r['before']} "
                                                   f"and {r['after']}", rows=[n])
        # R6: affected consumers in a later review's manifest (once the following review exists)
        cons = [(b, e["consumer"], e["id"]) for b in x["changed"] for e in bcopy
                if e["producer"] == b and e["consumer"] in bprds]
        aff_of[n] = {c for _, c, _ in cons}
        if fol is not None and ai is not None and fol["idx"] >= ai:
            t = fol["idx"] if fol["idx"] > ai else ai
            later = [b for b in bound if (b["i"] > chain[anchor]["i"] if anchor is not None else b["i"] >= fol["i"])]
            for b, c, eid in cons:
                want = mans[t]["names"].get(c)
                if want is None:            # absent from that manifest: the consumer's current bytes
                    cur = first_holder(home, PRD_DIRS, c)
                    want = file_sha(cur) if cur else None
                hit = False
                for rv in later:
                    sid = rv["row"].get("scope_id")
                    if want is None:
                        break
                    if isinstance(sid, str) and sid in ids:     # a chain review: its listed manifest (R2)
                        dg = mans[ids.index(sid)]["names"]
                    else:
                        sc = rv["row"].get("scope")
                        try:
                            dg = {k.decode("utf-8", "backslashreplace"): v for k, v in scope_canon(resolve(sc))[1].items()} \
                                if isinstance(sc, str) else {}
                        except ScopeError:
                            dg = {}
                    if dg.get(c) == want:
                        hit = True
                        break
                if not hit:
                    L.fail("affected-consumer-unreviewed", f"row {n}: changed {b} produces {c} over edge {eid}: no "
                                                           f"Review: row later than the finding's review lists {c} at "
                                                           f"{want or 'its after digest'}")
    # R5: the complement over every consecutive pair of listed manifests
    for k in range(len(mans) - 1):
        a, b = mans[k], mans[k + 1]
        if a["id"] is None or b["id"] is None:
            continue
        decl = set()
        for x in recs:
            if x["bi"] == k and x["ai"] == k + 1:
                decl |= set(x["changed"])
        mxr = {a.get("matrix"), b.get("matrix")} - {None} if a.get("matrix") != b.get("matrix") else set()
        for nm in sorted(set(a["names"]) & set(b["names"])):
            if nm != rbase and nm not in mxr and a["names"][nm] != b["names"][nm] and nm not in decl:
                L.fail("repair-hash-mismatch", f"{nm}: changed but undeclared between {a['path']} and {b['path']}",
                       man=[a["path"], b["path"]], absent=("pair", a["path"], b["path"], nm))
        # the repairs file is exempt only for a pair whose rows it holds (writing them is what moves it)
        if rbase in a["names"] and rbase in b["names"] and a["names"][rbase] != b["names"][rbase] \
                and not any(x["bi"] == k and x["ai"] == k + 1 for x in recs):
            L.fail("repair-hash-mismatch", f"{rbase}: changed but undeclared between {a['path']} and {b['path']} "
                                           "(no row names this pair; the repairs file is exempt only for a pair whose rows it holds)",
                   man=[a["path"], b["path"]], absent=("pair", a["path"], b["path"], None))
    # R7: holds, released by the mission's final APPROVE (repaired, amended) or by acceptance (declined)
    pos = {id(c): p for p, c in enumerate(chain)}

    def hold(b, reason):
        if b in prds and reason not in deps.setdefault(b, []):
            deps[b].append(reason)
    for x in recs:
        if x["disp"] in ("repaired", "amended"):
            if x["disp"] == "repaired" and x["fid"] in fobj:
                rel = vr is not None and vr["verdict"] == "APPROVE" and pos[id(vr)] > issuer[x["fid"]]
                why = f"repair {x['fid']} (row {x['n']})"
            else:
                rel = vr is not None and vr["verdict"] == "APPROVE" and x["ai"] is not None and vr["idx"] >= x["ai"]
                why = f"amended row {x['n']}"
            if not rel:
                for b in set(x["changed"]) | aff_of.get(x["n"], set()):
                    hold(b, why)
        elif x["disp"] == "declined" and x["fid"] in fobj and x["fid"] not in sup and accepted.get(x["fid"]) is None:
            f = fobj[x["fid"]]
            base = {y for y in names_of(f) if y in prds}
            nm = set(base)
            for e in mans[chain[issuer[x["fid"]]]["idx"]]["frozen_edges"]:
                if e["status"] in ("known", "external"):
                    if e["producer"] in base:
                        nm.add(e["consumer"])
                    if e["consumer"] in base:
                        nm.add(e["producer"])
            for b in nm:
                hold(b, f"declined {x['fid']} (row {x['n']})")
    out["changed"] = sorted({b for x in recs for b in x["changed"]})
    out["swept_edges"] = len(swept)
    out["edges_added"], out["edges_removed"] = sorted(added), sorted(removed)
    return out


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
        self.meta = []       # per finding: the manifests and repairs rows it names, whether it sets the
                             # exit whatever binds (a pending token or a defect no frozen copy carries
                             # introduced it), and the repairs row whose absence raised it (read by
                             # --packet-only; output never shows it)

    def fail(self, fid, detail, man=None, rows=None, pend=False, absent=None):
        self.findings.append((fid, detail))
        self.meta.append({"man": list(man or []), "rows": list(rows or []), "pend": bool(pend), "absent": absent})

    def ids(self):
        out = []
        for fid, _ in self.findings:
            if fid not in out:
                out.append(fid)
        return out


# ---------------------------------------------------------------- matrix (R10)
def lint_matrix(L, path, shown, slugs, extra=()):
    """Structural checks of the adversarial matrix. Returns the ## Uncovered count
    (None when that section is absent or the file is missing). `extra`: header prds members
    (slugs) the matrix also covers before a review launches (--packet-only --pending)."""
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
    for slug in extra:      # R1 names the missing section only; a present section's tables are read at Phase 4
        if slug not in sections:
            L.fail("adversarial-slug-missing", f"{shown}: no '## PRD-{slug}' section for header prds member {slug} "
                                               "(the review about to launch gives it a verdict)")
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
         "edges": None, "prds": None, "packet": False, "pending": None}
    i = 0
    while i < len(argv):
        x = argv[i]
        if x == "--json":
            a["json"] = True
        elif x == "--last":
            a["mode"] = "last"
        elif x == "--selftest":
            a["selftest"] = True
        elif x == "--packet-only":
            a["packet"] = True
        elif x in ("--entry", "--prd-dir", "--decisions", "--matrix", "--scope-id", "--edges", "--pending"):
            if i + 1 >= len(argv):
                usage(f"{x} needs a value")
            key = {"--entry": "entry", "--prd-dir": "prd_dir", "--decisions": "decisions", "--matrix": "matrix",
                   "--scope-id": "scope_id", "--edges": "edges", "--pending": "pending"}[x]
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
    pkt = bool(a.get("packet") or a.get("_passA"))     # PRD-dream-packet-errors-while-repairable
    psem = a.get("pending") is not None or bool(a.get("_passA"))
    if a.get("pending") is not None:
        # R1: the pending entry is checked as if appended; a missing, empty or entry-less note is a
        # note whose only entry is the pending one, a path that exists but cannot be read exits 2
        if not os.path.lexists(log):
            text = ""
        elif not os.path.isfile(log) or not os.access(log, os.R_OK):
            raise Exit2(f"log unreadable: {log}")
        else:
            text = read_text(log)
        entries = find_entries(text) if text.strip() else []
        pp = a["pending"]
        if not os.path.isfile(pp) or not os.access(pp, os.R_OK):
            raise Exit2(f"pending entry file missing or unreadable: {pp}")
        ptext = read_text(pp)
        if not ptext.strip():
            raise Exit2(f"pending entry file is empty: {pp}")
        pes = find_entries(ptext)
        if len(pes) > 1:
            raise Exit2(f"pending entry file {pp} holds {len(pes)} entries; one is allowed")
        entries.append(pes[0] if pes else {"ts": "pending", "lines": ptext.split("\n")})
    else:
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
    if a.get("_passA_ei") is not None:      # the reason pass lints the entry that first withdrew the manifest
        ei = a["_passA_ei"]
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
    rrows_all = [r for r in rows or [] if r.get("decision") == "launch" and r.get("task_id") == task
                 and r.get("role") == "review"] if governed and task is not None else []

    def launch_binds(p, sid, by_path=True):
        """packet-errors R3: the review launch row of this task that touched a manifest (path, then scope id)."""
        n = os.path.normpath(resolve(p))
        for r in rrows_all if by_path else []:
            sc = r.get("scope")
            if isinstance(sc, str) and sc and os.path.normpath(resolve(sc)) == n:
                return r
        for r in rrows_all if sid else []:
            if r.get("scope_id") == sid:
                return r
        for rv in reviews if sid else []:      # a Review: line's reviewer row carrying the scope id
            for r in rows or []:
                if r.get("session") == rv["session"] and r.get("decision") == "launch" and r.get("task_id") == task \
                        and r.get("scope_id") == sid:
                    return r
        return None

    def binding_rows(p, sid):
        """packet-errors R1: the launch rows of this task that bind a manifest as it stands, by every tier
        launch_binds accepts: review launch rows carrying its scope id or naming its path on a row with no scope
        id, and a Review: line's reviewer launch row carrying its scope id."""
        n = os.path.normpath(resolve(p))
        out = [r for r in rrows_all if (sid and r.get("scope_id") == sid) or (
            not (isinstance(r.get("scope_id"), str) and r["scope_id"]) and isinstance(r.get("scope"), str) and r["scope"]
            and os.path.normpath(resolve(r["scope"])) == n)]
        sess = {rv["session"] for rv in reviews}
        return out + [r for r in rows or [] if sid and r.get("session") in sess and r.get("decision") == "launch"
                      and r.get("task_id") == task and r.get("scope_id") == sid and all(r is not x for x in out)]

    def wbound(p):
        try:
            sid = scope_canon(resolve(p))[0]
            why = None
        except ScopeError as e:
            sid, why = None, f"it no longer canonicalizes: {e}"
        r = launch_binds(p, sid)
        if r is not None:
            return str(r.get("session")), why
        return ("none", why) if why else None
    if any(ln.startswith("Mission:") for e in entries[:ei + 1] for ln in e["lines"]):
        mopts = {"pkt": pkt, "psem": psem, "wbound": wbound if governed and task is not None else None}
        if a.get("_passA"):
            mopts["passA"] = a["_passA"]
        mrec = mission_record(L, entries, ei, task, list(states), resolve, mopts)

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
    # packet-errors R1 (--pending): the prds members of the last listed, non-withdrawn manifest's frozen
    # edges header, each of which the review about to launch gives a verdict
    hx = []
    if psem and mrec and mrec["line"] and mrec["scope"] and mrec["edges"]:
        live = [p for p in mrec["scope"] if os.path.normpath(resolve(p)) not in (mrec.get("wset") or set())]
        if live:
            copy, _, err = frozen_edges_copy(resolve(live[-1]), os.path.basename(mrec["edges"]))
            fh0 = None if err else read_edges(copy, copy)[0]
            hx = [b[len("PRD-"):-len(".md")] for b in fh0["prds"]] if fh0 else []
    if adv:
        if adv[0] == "skipped":
            if has_review:
                L.fail("adversarial-missing", "adversarial=skipped: beside a Review: line other than none")
            elif pkt:
                L.fail("adversarial-missing", "adversarial=skipped: beside the review about to launch (a pre-launch "
                                              "run counts it as a Review: line other than none)")
        else:
            mpath = resolve(adv[1])
            n = lint_matrix(L, mpath, adv[1], list(states), extra=[s for s in hx if s not in states])
            if n is not None and n != adv[2]:
                L.fail("analysis-grammar", f"uncovered={adv[2]} but '## Uncovered' in {adv[1]} lists {n}")
            mm = re.match(r"^(.+)-adversarial\.md$", os.path.basename(adv[1]))
            if mm and prev_ts and os.path.isfile(mpath):
                mt, pt = parse_iso(mm.group(1)), parse_iso(prev_ts)
                if mt and pt and mt <= pt:
                    L.fail("analysis-grammar",
                           f"matrix {adv[1]} is not later than the previous entry {prev_ts} (an earlier run's matrix)")

    # ---- mission chain review (PRD-dream-mission-chain-review): active when the Mission: line carries scope=
    chain_on = bool(mrec and mrec["line"] and mrec["scope"])
    mans, chain, skip, report, bound = [], [], {}, {}, []

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
        if chain_on:                # R1 manifests, R2 chain reviews, R5 superseded pins (replaces the gate fix)
            mans = mission_scopes(L, mrec, resolve)
            bound = bind_reviews(reviews, rows, task, governed, rsess, resolve)
            chain = chain_of(bound, mans)
            skip, report = superseded_pins(chain, home, resolve)
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
                gone = skip.get(i, set())   # R5: a slug a later chain review names is not pinned here
                if report.get(i):
                    rv["superseded"] = [{"slug": s, "by": report[i][s]} for s in last if s in report[i]]
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

    # ---- mission chain review R1-R6 and the hold (PRD-dream-mission-chain-review)
    mfields, deps, vr = None, {}, None
    if mrec and mrec["line"] and (chain_on or mrec["header"] is not None):
        if chain_on:
            if not mans:            # the reviews loop did not run (Review: none or a grammar refusal)
                mans = mission_scopes(L, mrec, resolve)
            mfields, deps, vr = chain_review(L, mrec, mans, chain, rows, governed, task, adv, states, reviews, home, resolve)
            # PRD-dream-failure-class-sweep R1-R8: repairs between chain reviews, their holds
            repairs = repair_sweep(L, mrec, mans, chain, bound, rows, governed, task, entries, ei, route, vr, deps,
                                   home, resolve)
            if repairs is not None:
                mfields["repairs"] = repairs
        else:                       # R9: Mission: without scope= is a pre-freeze record
            for b in mrec["header"]["prds"]:
                deps[b] = ["no mission scope"]
            for e in mrec["edge_list"]:
                if e["status"] == "unknown":
                    for b in (e["producer"], e["consumer"]):
                        if b in deps and f"unknown edge {e['id']}" not in deps[b]:
                            deps[b].append(f"unknown edge {e['id']}")
            mfields = {"scope_ids": [], "scope_id": None, "chain_reviews": [], "verdict": None, "findings": 0,
                       "unlisted_review_sessions": []}
        approval(L, mrec, deps, mfields["verdict"], states)

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

    def norm(p):
        return os.path.normpath(resolve(p))

    # packet-errors R4: each applied withdrawal's record; `reason` is recomputed by a packet-only pass
    # over the same-Task entry that first withdrew it, with scope= cut after the manifest (rows of later
    # manifests dropped): the first packet error naming it or a row it voids
    if mrec and mrec.get("withdrawn") is not None and not a.get("_passA"):
        wrecs = []
        for p in mrec["withdrawn"]:
            first = ei
            for j, e in enumerate(entries[:ei + 1]):
                ml = [ln.rstrip() for ln in e["lines"] if ln.startswith("Mission:")]
                if entry_task(e) == task and len(ml) == 1 and \
                        any(norm(x) == norm(p) for x in parse_mission_line(ml[0])[1].get("withdrawn") or []):
                    first = j
                    break
            try:
                wid = scope_canon(resolve(p))[0]
            except ScopeError:
                wid = None
            vn = (mrec.get("voided") or {}).get(norm(p), [])
            try:
                LA = lint_log(dict(a, _passA=norm(p), _passA_ei=first))[0]
            except Exit2:
                LA = None
            reason = "none"
            for (fid, _), mt in zip(LA.findings, LA.meta) if LA else []:
                if fid in PACKET_IDS and (any(norm(x) == norm(p) for x in mt["man"]) or set(mt["rows"]) & set(vn)):
                    reason = fid
                    break
            wrecs.append({"path": p, "scope_id": wid, "reason": reason, "voided_rows": vn})
        mrec["wrecs"] = wrecs

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
    if obj["mission"] is not None and mfields is not None:
        prds = mrec["header"]["prds"] if mrec["header"] else []
        obj["mission"].update(mfields)
        obj["mission"]["dependent_slugs"] = [{"slug": b[len("PRD-"):-len(".md")], "reason": "; ".join(deps[b])}
                                             for b in prds if b in deps]
        # R8: verified when a chain review binds, the mission verdict is APPROVE and no mission finding fired
        if vr is not None and mfields["verdict"] == "APPROVE" and not any(f in MISSION_IDS + SWEEP_IDS for f, _ in L.findings):
            prov["mission"] = "verified"
    if a.get("packet") and not a.get("_passA"):
        return L, packet_result(a, L, obj, entry, task, malformed, lines, reviews, states, mrec, mans, adv, psem,
                                launch_binds, binding_rows, resolve), None
    ok_line = f"OK {entry['ts']}" + (" persisted=shape-only" if prov["persisted"] == "shape-only" else "")
    return L, obj, ok_line


def packet_result(a, L, obj, entry, task, malformed, lines, reviews, states, mrec, mans, adv, psem, launch_binds,
                  binding_rows, resolve):
    """PRD-dream-packet-errors-while-repairable R1: the --packet-only object. Packet-error findings
    only, each exit-setting (packet_errors) or held (held_packet_errors: on manifests a review launch
    bound, present in their frozen copies); pending_errors are the --pending exits that carry no id."""
    def norm(p):
        return os.path.normpath(resolve(p))
    pend = []
    if psem:
        for k in ("Task", "Mission", "Analysis", "State"):
            if k not in lines:
                pend.append({"what": "line", "detail": f"no {k}: line in the pending entry"})
        for rv in reviews:      # a slug a pending Review: file names: the Phase 4 State: names it, the matrix reads it
            full = resolve(rv["file"])
            if os.path.isfile(full) and os.access(full, os.R_OK):
                for slug in dict.fromkeys(v[0] for v in (verdict_of(x) for x in read_text(full).split("\n")) if v):
                    if slug not in states:
                        pend.append({"what": "slug", "detail": f"slug {slug}: {rv['file']} names it; the pending State: "
                                                               "line does not"})
    bound = {norm(m["path"]) for m in mans if launch_binds(m["path"], m["id"]) is not None}

    def kept(m):
        """R1: a bound manifest whose frozen copies record the state when its review launched: not one that
        no longer canonicalizes, nor one bound by a path row carrying another scope id while no row carries
        its own (R3: edited or deleted after a launch)."""
        r = launch_binds(m["path"], m["id"])
        if r is None or m["id"] is None:
            return False
        sid = r.get("scope_id")
        return launch_binds(m["path"], m["id"], by_path=False) is not None or not (isinstance(sid, str) and sid)
    held_ok = {norm(m["path"]) for m in mans if norm(m["path"]) in bound and kept(m)}
    if mans and mrec and mans[-1]["id"] is not None and norm(mans[-1]["path"]) not in bound:
        lm = mans[-1]           # the unbound last manifest: its reviewer reads the frozen bytes, not the live files
        for tp in (mrec["edges"], mrec["repairs"], adv[1] if adv and adv[0] == "matrix" else None):
            want = lm["names"].get(os.path.basename(tp)) if tp else None
            if want is None:
                continue
            got = file_sha(resolve(tp))
            if got != want:
                pend.append({"what": "digest", "detail": f"{tp}: live {'sha256 ' + got[:12] if got else 'file absent or unreadable'} "
                                                         f"differs from manifest {lm['path']}'s {want[:12]} (the reviewer "
                                                         "reads the frozen bytes)"})
    bidx = [k for k, m in enumerate(mans) if norm(m["path"]) in held_ok]
    bm = mans[max(bidx)] if bidx else None          # the latest bound manifest whose launch state is its own
    # the time its frozen evaluation stands for: its latest launch, by every tier that binds it (R3)
    bts = max((t for t in (launch_ts(r) for r in binding_rows(bm["path"], bm["id"])) if t), default=None) if bm else None
    frozen = set()              # repairs rows byte-identical, at the same row number, in the copy beside that manifest
    crows = None                # the rows of the repairs file in force at that launch, read from its copy beside the
                                # manifest: [] when it froze none (no repairs= token was ever carried, or the manifest
                                # lists no such file); None when no copy can be read (listed, but absent, differing
                                # from the digest or unreadable)
    # the repairs= token in force at that launch: the value of the latest entry recorded before it, else the current
    rep_at = mrec.get("repairs") if mrec else None
    for x in (mrec.get("earlier") or []) if mrec and bts is not None else []:
        xt = parse_iso(x["ts"]) if isinstance(x["ts"], str) else None
        if xt is not None and xt < bts and x["eff"].get("repairs"):
            rep_at = x["eff"]["repairs"][0]
    same = bool(rep_at and mrec.get("repairs") and norm(rep_at) == norm(mrec["repairs"]))
    rb = os.path.basename(rep_at) if rep_at else None
    if bm is not None and not mrec.get("repairs"):
        crows = []
    elif bm is not None:
        cp = os.path.join(os.path.dirname(bm["full"]), rb)
        if bm["names"].get(rb) is None:
            crows = []
        elif file_sha(cp) == bm["names"][rb]:
            try:
                with open(resolve(mrec["repairs"]), "rb") as fh:
                    live = fh.read().split(b"\n")
            except OSError:
                live = []
            try:
                with open(cp, "rb") as fh:
                    cpl = fh.read().split(b"\n")
            except OSError:
                cpl = None
            if cpl is not None:     # S2: a row of the current file is frozen only in a copy of that file
                frozen = {i + 1 for i, ln in enumerate(live) if i < len(cpl) and ln == cpl[i] and ln.strip()} if same else set()
                crows = []
                for ln in cpl:
                    try:
                        r = json.loads(ln)
                    except ValueError:
                        continue
                    if isinstance(r, dict):
                        crows.append(r)
    wsince = mrec.get("wsince") or {} if mrec else {}

    def in_force(p):
        """A withdrawal first recorded before that launch (never one only the pending entry carries, S3)."""
        t = wsince.get(norm(p))
        t = parse_iso(t) if isinstance(t, str) else None
        return t is not None and bts is not None and t < bts

    def carried(ab):
        """R1: the copy's evaluation at that launch also lacks the row whose absence raised the error: a finding
        that existed then (its review launched before it) with no copy row other than one a withdrawal in force
        voids; a pair that was a pair then (no manifest between them withdrawn later) with no declaring row."""
        if crows is None:
            return False
        if ab[0] == "finding":
            # the issuing review's launch on the manifest it reviewed: the earliest of its session's rows binding it
            ir = ab[2] if isinstance(ab[2], dict) else None
            irs = [r for r in binding_rows(ir["scope"], ir.get("scope_id")) if r.get("session") == ir.get("session")] \
                if ir and isinstance(ir.get("scope"), str) and ir["scope"] else []
            issued = min((t for t in (launch_ts(r) for r in irs) if t), default=launch_ts(ir) if ir else None)
            if issued is None or bts is None or not bts > issued:
                return False
            return not any(r.get("finding") == ab[1] and not any(in_force(r[k]) for k in ("before", "after")
                                                                 if isinstance(r.get(k), str) and r[k].strip()) for r in crows)
        sc = [norm(p) for p in mrec["scope"]]
        a, b = norm(ab[1]), norm(ab[2])
        if a in sc and b in sc[sc.index(a) + 1:] and not all(in_force(p) for p in sc[sc.index(a) + 1:sc.index(b, sc.index(a) + 1)]):
            return False
        # the name as that launch saw it: the launch's repairs file is exempt for a pair any row names, the current
        # one (when another) was a member a row declares
        nm = ab[3] if same else (None if ab[3] == rb else ab[3] or os.path.basename(mrec["repairs"]))
        return not any(isinstance(r.get("before"), str) and isinstance(r.get("after"), str) and r["before"].strip()
                       and r["after"].strip() and norm(r["before"]) == a and norm(r["after"]) == b
                       and (nm is None or (isinstance(r.get("changed"), list) and nm in r["changed"])) for r in crows)

    def exits(fid, mt):
        if fid == "mission-withdrawn-bound" or mt["pend"] or (not mt["man"] and not mt["rows"]):
            return True
        if any(norm(p) not in held_ok for p in mt["man"]):
            return True
        if mt["absent"] is not None and not carried(mt["absent"]):
            return True
        return bool(mt["rows"]) and not all(n in frozen for n in mt["rows"])
    perr, held = [], []
    for (fid, d), mt in zip(L.findings, L.meta):
        if psem and fid == "analysis-grammar":
            pend.append({"what": "line", "detail": f"Analysis: {d}"})
        elif psem and fid == "line-missing" and d.startswith("Task ("):
            pend.append({"what": "line", "detail": "Task: " + d[len("Task ("):-1]})
        elif fid in PACKET_IDS:
            (perr if exits(fid, mt) else held).append({"id": fid, "detail": d})
    ex = 1 if perr or pend else 0
    mj = obj["mission"]
    out = {"mode": "packet-only", "ts": entry["ts"], "task": task, "exit": ex,
           "findings": list(dict.fromkeys(e["id"] for e in perr)), "packet_errors": perr, "held_packet_errors": held,
           "pending_errors": pend, "decisions_malformed": malformed, "trust": "same-uid",
           "mission": None if mj is None else {"name": mj["name"], "scope": mj["scope"], "scope_ids": mj.get("scope_ids", []),
                                               "withdrawn": mj.get("withdrawn", [])}}
    out["_lines"] = ([f"FAIL {e['id']}: {e['detail']}" for e in perr] + [f"HELD {e['id']}: {e['detail']}" for e in held]
                     + [f"PENDING {e['what']}: {e['detail']}" for e in pend]
                     + ([f"OK packet {entry['ts']}" + (f" held={len(held)}" if held else "")] if not ex else []))
    return out


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
                                                       "edges", "prds", "packet", "pending")):
                usage("--scope-id takes one manifest path and nothing else")
            return scope_id_mode(a["scope_id"])
        if a["pending"] is not None and not a["packet"]:
            usage("--pending needs --packet-only")
        if a["packet"] and any(a[k] is not None for k in ("entry", "matrix", "states", "edges", "prds")):
            usage("--packet-only lints the last entry (--last) of a log, without --entry, --matrix, --states or --edges")
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
    if a["packet"]:             # PRD-dream-packet-errors-while-repairable R1
        out = sys.stderr if a["json"] else sys.stdout
        for t in obj.pop("_lines"):
            print(t, file=out)
        if a["json"]:
            print(json.dumps(obj, separators=(",", ":")))
        return obj["exit"]
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


def mission_edges(slugs, mutate=None, known_only=False):
    """A selftest edges file (edge-map R2): header over PRD-<slug>.md for slugs, one known edge
    slugs[0] -> slugs[1], one external edge to hermes and (unless known_only) one owned unknown edge."""
    f8 = lambda p, c, x: {"producer": p, "consumer": c, "command": x + " command", "trigger": x + " trigger",
                          "authority": x + " authority", "effect_id": x + " effect", "recovery_owner": x + " owner",
                          "postcondition": x + " postcondition"}
    pr = [f"PRD-{s}.md" for s in slugs]
    h = {"mission": "selftest", "outcome": "selftest outcome", "invariants": ["one invariant"], "prds": pr,
         "external": ["hermes"]}
    es = [dict(id="E1", status="known", **f8(pr[0], pr[-1], "E1")),
          dict(id="E2", status="external", **f8(pr[-1], "external:hermes", "E2")),
          dict(id="E3", status="unknown", producer=pr[0], consumer="UNKNOWN", owner="selftest author")]
    if known_only:
        es = es[:2]
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

    # superseded chain-review pins (PRD-dream-mission-chain-review R5, which replaces the gate
    # fix's G5-G6): S_R1 on m1 APPROVEs foo, foo is edited (declared by an amended repairs row),
    # S_R2 on m2 (launched later, result=, mission=APPROVE) re-APPROVEs foo on the new bytes.
    # m1 and m2 freeze the PRDs, the matrix and the edges file (one frozen copy serves both).
    h = lambda b: hashlib.sha256(b).hexdigest()
    sid = lambda t: h("".join(sorted(set(t.splitlines(True)))).encode())
    MXB = os.path.basename(M_REL)

    def frozen(fx, foo, extra=""):
        edges = fx.files["notes/missions/selftest.edges.jsonl"]
        fx.files["notes/snapshots/selftest.edges.jsonl"] = edges
        fx.files["notes/snapshots/" + MXB] = fx.files[M_REL]
        return (f"{h(foo)}  PRD-foo.md\n{h(b'# bar stub' + chr(10).encode())}  PRD-bar.md\n"
                f"{h(fx.files[M_REL].encode())}  {MXB}\n{h(edges.encode())}  selftest.edges.jsonl\n" + extra)

    def chain(fx, slugs=("foo",), v2=None):
        old, new = b"# foo stub\n", b"# foo stub, edited\n"
        fx.files.update({"built-prds/PRD-foo.md": new.decode(), M_REL: mx_file(["foo", "bar"]),
                         "notes/missions/selftest.edges.jsonl": mission_edges(["foo", "bar"], known_only=True)})
        rep = json.dumps({"finding": None, "class": None, "author_session": S_D, "before": "notes/snapshots/m1.sha256",
                          "after": "notes/snapshots/m2.sha256", "changed": ["PRD-foo.md"], "sweep": ["E1"],
                          "disposition": "amended", "reason": "foo re-worded after the m1 review"}) + "\n"
        fx.files["notes/missions/selftest.repairs.jsonl"] = rep
        m1 = frozen(fx, old)
        m2 = frozen(fx, new, f"{h(rep.encode())}  selftest.repairs.jsonl\n")
        fx.files.update({"notes/snapshots/m1.sha256": m1, "notes/snapshots/m2.sha256": m2})
        fx.rows[3] = dict(fx.rows[3], role="author", scope="", scope_id="")
        fx.rows[4] = dict(fx.rows[4], role="review", scope="notes/snapshots/m1.sha256", scope_id=sid(m1))
        fx.rows[5] = dict(fx.rows[5], role="review", scope="notes/snapshots/m2.sha256", scope_id=sid(m2))
        v = "".join(f"{x} APPROVE fable\n" for x in slugs)
        v1, v2 = v + f"mission=APPROVE {S_R1}\n", (v2 or v) + f"mission=APPROVE {S_R2}\n"
        fx.files["notes/reviews/r1.txt"], fx.files["notes/reviews/r2.txt"] = v1, v2
        result_json(fx, "notes/reviews/r1.json", S_R1, "Done.\n" + v1)
        result_json(fx, "notes/reviews/r2.json", S_R2, "Done.\n" + v2)
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json",
                              f"Review: notes/reviews/r2.txt reviewer-session={S_R2} result=notes/reviews/r2.json"]
        fx.entry["State"] = "State: " + " ".join(f"{x}=reviewed:APPROVE {x}=reviewed:APPROVE" for x in slugs)
        fx.tail = ["Mission: selftest edges=notes/missions/selftest.edges.jsonl "
                   "scope=notes/snapshots/m1.sha256,notes/snapshots/m2.sha256 repairs=notes/missions/selftest.repairs.jsonl"]
        return fx
    passes("drsp-p1-superseded", chain(new()), lambda d: expect(
        d["provenance"]["snapshot"] == "verified" and d["reviews"][0].get("superseded") == [{"slug": "foo", "by": S_R2}]
        and "superseded" not in d["reviews"][1] and d["provenance"]["mission"] == "verified", (d["provenance"], d["reviews"])))
    passes("drsp-p4-b-not-superseded", chain(new(), ("foo", "bar")), lambda d: expect(
        d["reviews"][0].get("superseded") == [{"slug": "foo", "by": S_R2}], d["reviews"]))
    stale_r1 = ["notes/reviews/r1.txt", S_R1, "slug foo"]
    # R5 + R6: a later FIX supersedes the earlier APPROVE ("superseded by that later verdict") and holds the slug
    fx = chain(new(), v2="foo FIX fable\n"); fx.entry["State"] = "State: foo=reviewed:APPROVE foo=reviewed:FIX"
    passes("drsp-kb1-j-fix-held", fx, lambda d: expect(
        d["reviews"][0].get("superseded") == [{"slug": "foo", "by": S_R2}] and d["mission"]["dependent_slugs"] == [{"slug": "foo", "reason": "per-PRD verdict FIX"}, {"slug": "bar", "reason": "no per-PRD verdict"}],
        d.get("mission")))
    fx = chain(new(), v2="foo FIX fable\n"); fx.entry["State"] = "State: foo=reviewed:APPROVE foo=reviewed:FIX foo=eligible"
    refuse("drsp-kb1-j-fix-eligible", fx, "mission-approval-blocked", ["slug foo", "per-PRD verdict FIX"])
    # R2 orders launch ts only within one manifest; across manifests the index decides (R5 by line order)
    fx = chain(new()); fx.rows[5] = dict(fx.rows[5], ts="2026-11-15T01:20:00-08:00")
    passes("drsp-kb4-launch-across-manifests", fx, lambda d: expect(
        d["reviews"][0].get("superseded") == [{"slug": "foo", "by": S_R2}], d["reviews"]))
    fx = chain(new()); fx.tail = []
    refuse("drsp-kb5-no-mission", fx, "review-snapshot-stale", stale_r1)
    fx = chain(new()); fx.rows[5] = {k: v for k, v in fx.rows[5].items() if k != "role"}
    refuse("drsp-kb6-j-legacy", fx, "review-snapshot-stale", stale_r1)
    # a review bound to an unlisted manifest is no chain review (R2): it neither keeps nor sets a hold
    fx = chain(new()); s_x = "bbbbbbbb-0000-4000-8000-000000000006"
    fx.files["notes/snapshots/m3.sha256"] = fx.files["notes/snapshots/m2.sha256"] + "0" * 64 + "  notes.md\n"
    fx.rows.append(dict(fx.rows[5], ts="2026-11-15T01:50:00-08:00", session=s_x, scope="notes/snapshots/m3.sha256",
                        scope_id=sid(fx.files["notes/snapshots/m3.sha256"])))
    fx.files["notes/reviews/r3.txt"] = "foo FIX fable\n"
    fx.entry["Review"].append(f"Review: notes/reviews/r3.txt reviewer-session={s_x}")
    fx.entry["State"] = "State: foo=reviewed:APPROVE foo=reviewed:APPROVE foo=reviewed:FIX"
    passes("drsp-kb11-unlisted-manifest-not-chain", fx, lambda d: expect(
        len(d["mission"]["chain_reviews"]) == 2 and d["mission"]["dependent_slugs"] == [{"slug": "bar", "reason": "no per-PRD verdict"}], d.get("mission")))
    fx = chain(new()); fx.entry["Review"][1] = f"Review: notes/reviews/r2.txt reviewer-session={S_R2}"
    refuse("drsp-kb13-j-no-result", fx, "mission-verdict-missing", ["notes/reviews/r2.txt", "no result="])

    # bound mission (PRD-dream-mission-chain-review): one passing fixture, one refusal per new id
    def bound(fx, verdict="APPROVE", foo_line="foo APPROVE fable", mission_line=True, scope=None, extra_manifests=None):
        fx.files.update({M_REL: mx_file(["foo", "bar"]),
                         "notes/missions/selftest.edges.jsonl": mission_edges(["foo", "bar"], known_only=True)})
        m = frozen(fx, b"# foo stub\n")
        fx.files["notes/snapshots/m.sha256"] = m
        for rel, txt in (extra_manifests or {}).items():
            fx.files[rel] = txt
        fx.rows[3] = dict(fx.rows[3], role="author", scope="", scope_id="")
        fx.rows[4] = dict(fx.rows[4], role="review", scope="notes/snapshots/m.sha256", scope_id=sid(m))
        v = f"{foo_line}\nbar APPROVE fable\n" + (f"mission={verdict} {S_R1}\n" if mission_line else "")
        fx.files["notes/reviews/r1.txt"] = v
        result_json(fx, "notes/reviews/r1.json", S_R1, "Done.\n" + v)
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json"]
        fx.entry["State"] = f"State: foo=reviewed:{foo_line.split()[1]} bar=reviewed:APPROVE"
        fx.files[M_REL] = mx_file(["foo", "bar"])
        fx.entry["Mission"] = ("Mission: selftest edges=notes/missions/selftest.edges.jsonl scope="
                               + (scope or "notes/snapshots/m.sha256"))
        return fx
    passes("drmr-bound-mission", bound(new()), lambda d: expect(
        d["provenance"]["mission"] == "verified" and d["mission"]["verdict"] == "APPROVE"
        and len(d["mission"]["chain_reviews"]) == 1 and d["mission"]["dependent_slugs"] == [], d.get("mission")))
    fx = bound(new(), scope="notes/snapshots/m.sha256,notes/snapshots/bad.sha256",
               extra_manifests={"notes/snapshots/bad.sha256": "not a manifest\n"})
    refuse("drmr-malformed-manifest", fx, "mission-scope-mismatch", ["notes/snapshots/bad.sha256", "line-rule"])
    fx = new(); fx = bound(fx, scope="notes/snapshots/m0.sha256,notes/snapshots/m.sha256")
    fx.files["notes/snapshots/m0.sha256"] = "".join(l + "\n" for l in fx.files["notes/snapshots/m.sha256"].splitlines()
                                                    if not l.endswith(MXB))
    refuse("drmr-manifest-without-matrix", fx, "mission-scope-incomplete", ["notes/snapshots/m0.sha256", MXB])
    fx = bound(new()); other = frozen(fx, b"# foo stub\n", "0" * 64 + "  extra.md\n")
    fx.files["notes/snapshots/other.sha256"] = other
    fx.rows[4] = dict(fx.rows[4], scope="notes/snapshots/other.sha256", scope_id=sid(other))
    refuse("drmr-review-on-unlisted-manifest", fx, "mission-review-missing", [sid(other)])
    refuse("drmr-no-mission-line", bound(new(), mission_line=False), "mission-verdict-missing", ["notes/reviews/r1.txt"])
    refuse("drmr-fix-without-sidecar", bound(new(), verdict="FIX", foo_line="foo FIX fable"),
           "mission-finding-incomplete", ["r1.txt.findings.jsonl", "mission=FIX"])
    fx = bound(new()); fx.build()
    with open(os.path.join(fx.home, "notes/missions/selftest.edges.jsonl"), "a", encoding="utf-8") as fh:
        fh.write("\n")
    fx.files = {}
    refuse("drmr-edges-moved-after-approve", fx, "mission-snapshot-stale", ["selftest.edges.jsonl"])
    fx = bound(new()); fx.entry["Mission"] = "Mission: selftest edges=notes/missions/selftest.edges.jsonl"
    fx.entry["State"] = "State: foo=reviewed:APPROVE bar=reviewed:APPROVE foo=eligible"
    refuse("drmr-noscope-eligible", fx, "mission-approval-blocked", ["slug foo", "no mission scope"])

    # failure-class sweep (PRD-dream-failure-class-sweep): r1 on m1 FIX with finding F1 (foo,
    # consumer bar), the repairs rows, r2 on m2 APPROVE on foo's repaired bytes; one passing
    # repaired mission, one refusal per new id
    REP, N2 = "notes/missions/selftest.repairs.jsonl", "notes/snapshots/n2/m2.sha256"
    F1 = {"id": "F1", "class": "missing-producer-runner", "severity": "MEDIUM", "prds": ["PRD-foo.md"],
          "consumers": ["PRD-bar.md"], "counterexample": "foo writes nothing bar reads", "correction": "foo writes it",
          "control": "a bar run reads foo's record"}
    ROW = {"finding": "F1", "class": "missing-producer-runner", "author_session": S_D, "before": "notes/snapshots/m1.sha256",
           "after": "notes/snapshots/m2.sha256", "changed": ["PRD-foo.md"], "sweep": ["E1", "E2"], "disposition": "repaired"}

    def repaired(fx, rows=(ROW,), token=True, r2_side=None, narrow=False):
        old, newb = b"# foo stub\n", b"# foo stub, edited\n"
        e1 = mission_edges(["foo", "bar"], known_only=True)
        fx.files.update({"built-prds/PRD-foo.md": newb.decode(), M_REL: mx_file(["foo", "bar"]),
                         "notes/missions/selftest.edges.jsonl": e1})
        m1 = frozen(fx, old)
        rep = "".join(json.dumps(r) + "\n" for r in rows)
        if token:
            fx.files[REP] = rep
        replines = f"{h(rep.encode())}  selftest.repairs.jsonl\n" if token else ""
        m2rel = "notes/snapshots/m2.sha256"
        if narrow:                  # m2 (its own directory) drops bar from its packet and header, as does the live header
            e2 = mission_edges(["foo", "bar"], known_only=True, mutate=lambda hh, es: (
                hh.update(prds=["PRD-foo.md"]), es.__setitem__(slice(None), [dict(es[1], producer="PRD-foo.md")])))
            m2rel = N2
            fx.files.update({"notes/missions/selftest.edges.jsonl": e2, "notes/snapshots/n2/selftest.edges.jsonl": e2})
            m2 = (f"{h(newb)}  PRD-foo.md\n{h(fx.files[M_REL].encode())}  {MXB}\n{h(e2.encode())}  selftest.edges.jsonl\n"
                  + replines)
        else:
            m2 = frozen(fx, newb, replines)
        fx.files.update({"notes/snapshots/m1.sha256": m1, m2rel: m2,
                         "notes/reviews/r1.txt.findings.jsonl": json.dumps(F1) + "\n"})
        if r2_side is not None:
            fx.files["notes/reviews/r2.txt.findings.jsonl"] = "".join(json.dumps(r) + "\n" for r in r2_side)
        fx.rows[3] = dict(fx.rows[3], role="author", scope="", scope_id="")
        fx.rows[4] = dict(fx.rows[4], role="review", scope="notes/snapshots/m1.sha256", scope_id=sid(m1))
        fx.rows[5] = dict(fx.rows[5], role="review", scope=m2rel, scope_id=sid(m2))
        bar1, bar2 = ("", "") if narrow else ("bar APPROVE fable\n", "bar APPROVE fable\n")
        v1, v2 = f"foo FIX fable\n{bar1}mission=FIX {S_R1}\n", f"foo APPROVE fable\n{bar2}mission=APPROVE {S_R2}\n"
        fx.files["notes/reviews/r1.txt"], fx.files["notes/reviews/r2.txt"] = v1, v2
        result_json(fx, "notes/reviews/r1.json", S_R1, "Done.\n" + v1)
        result_json(fx, "notes/reviews/r2.json", S_R2, "Done.\n" + v2)
        fx.entry["Review"] = [f"Review: notes/reviews/r1.txt reviewer-session={S_R1} result=notes/reviews/r1.json",
                              f"Review: notes/reviews/r2.txt reviewer-session={S_R2} result=notes/reviews/r2.json"]
        fx.entry["State"] = "State: foo=reviewed:FIX foo=reviewed:APPROVE" + ("" if narrow else
                                                                             " bar=reviewed:APPROVE bar=reviewed:APPROVE")
        fx.entry["Mission"] = ("Mission: selftest edges=notes/missions/selftest.edges.jsonl "
                               f"scope=notes/snapshots/m1.sha256,{m2rel}" + (f" repairs={REP}" if token else ""))
        return fx
    passes("drfc-repaired-mission", repaired(new()), lambda d: expect(
        d["provenance"]["mission"] == "verified" and d["mission"]["repairs"]["rows"] == 1
        and d["mission"]["repairs"]["pending_after"] is False and d["mission"]["chain_reviews"][0]["verdict"] == "FIX",
        d.get("mission")))
    refuse("drfc-bad-disposition", repaired(new(), rows=(dict(ROW, disposition="fixed"),)), "repair-grammar",
           ["row 1", "disposition"])
    fx = bound(new())
    fx.files[REP] = ""
    fx.files["notes/snapshots/m.sha256"] += f"{h(b'')}  selftest.repairs.jsonl\n"
    fx.rows[4] = dict(fx.rows[4], scope_id=sid(fx.files["notes/snapshots/m.sha256"]))
    fx.entry["Mission"] += f" repairs={REP}"
    refuse("drfc-empty-repairs-file", fx, "mission-repairs-missing", [REP])
    refuse("drfc-second-row", repaired(new(), rows=(ROW, ROW)), "repair-duplicate", ["F1"])
    refuse("drfc-no-token", repaired(new(), token=False), "repair-missing", ["F1", "no repairs= token"])
    refuse("drfc-class-differs", repaired(new(), rows=(dict(ROW, **{"class": "authority-bypass"}),)), "repair-class-mismatch", ["F1"])
    refuse("drfc-sweep-short", repaired(new(), rows=(dict(ROW, sweep=["E1"]),)), "sweep-missing", ["F1", "E2"])
    refuse("drfc-reviewer-as-author", repaired(new(), rows=(dict(ROW, author_session=S_R1),)), "repair-author-mismatch", [S_R1])
    refuse("drfc-bar-claimed", repaired(new(), rows=(dict(ROW, changed=["PRD-foo.md", "PRD-bar.md"]),)), "repair-hash-mismatch",
           ["PRD-bar.md", "claimed changed"])
    ACC = {"id": "F2", "class": "provenance", "accepts": ["F1"], "prds": [], "consumers": [], "counterexample": "x",
           "correction": "none", "control": "y"}
    AMD = dict(ROW, finding=None, **{"class": None}, sweep=["E1"], disposition="amended", reason="foo re-worded")
    refuse("drfc-decline-not-same-manifest", repaired(new(), rows=(
        dict(ROW, disposition="declined", reason="no change needed", changed=[], after="notes/snapshots/m1.sha256"), AMD),
        r2_side=[ACC]), "repair-scope-mismatch", ["row 1", "after notes/snapshots/m1.sha256"])
    refuse("drfc-bar-dropped-unreviewed", repaired(new(), rows=(dict(ROW, changed=["PRD-foo.md", "selftest.edges.jsonl"], after=N2),),
                                                   narrow=True), "affected-consumer-unreviewed", ["PRD-foo.md", "PRD-bar.md", "E1"])
    refuse("drfc-decline-unaccepted", repaired(new(), rows=(dict(ROW, disposition="declined", reason="no change needed"),)),
           "repair-declined-unaccepted", ["F1"])

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
