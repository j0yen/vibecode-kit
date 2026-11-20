#!/usr/bin/env bash
# dream-run-note-lint.sh — check a /dream run note (Phase 4) against the files the
# governed workflow writes, and a Phase 3 adversarial matrix against its grammar.
# See PRD-dream-run-record.
#
# Usage:
#   dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] [--json]
#                          [--prd-dir <dir>] [--decisions <path>] [--scope-root <recorded root>=<PRD home> ...]
#   dream-run-note-lint.sh --matrix <path> --states <slug=value ...> [--json]
#   dream-run-note-lint.sh --scope-id <manifest>
#   dream-run-note-lint.sh --edges <edges.jsonl> [--prds <PRD basename ...>] [--json]
#   dream-run-note-lint.sh --consumption <record> --task <T> [--page <page>] [--prd-home <dir>] [--reviews <dir>]
#                          [--decisions <path>] [--require-closed] [--json]      (PRD-dream-finding-consumption R8)
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
#   Mission: <name> edges=<path> [scope=<p>[,<p>...]] [repairs=<path>] [withdrawn=<p>[,<p>...]]   (optional sixth kind)
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
#   mission-approval-blocked
#   repair-grammar mission-repairs-missing repair-duplicate repair-missing repair-class-mismatch
#   sweep-missing repair-author-mismatch repair-hash-mismatch repair-scope-mismatch
#   affected-consumer-unreviewed repair-declined-unaccepted repair-consolidation-mismatch
#   sidecar-correction-unbound
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
# Scope roots (A1723 source request 6, Q5, ruled A): --scope-root <recorded root>=<PRD home>, repeatable, is given by
# the case-11 gate for a delivered decisions source whose observed.json names the PRD home root its rows were written
# under. A review row's absolute scope under a recorded root is read at the same relative path under this run's PRD
# home. The JSON's scope_roots carries the map and every such read with both paths; the review's scope_read carries
# its own. Every check stands: scope_id equality on the canonical bytes, the verdict slugs, each APPROVE slug's current
# file. The sweep and pin checks treat a read under a root whose canonical id is not the row's scope_id as unreadable.
# A scope under no recorded root, and a relative scope, is read as before. The right side must be this run's PRD home;
# a root of /, two roots where one holds the other, or a root holding this run's PRD home or inside it, exits 2. No
# row is rewritten.
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
# Withdrawn freeze (Repair 6, the PRD author's addendum 4): withdrawn=<manifest>[,...] on a Mission: line drops a
# planned freeze that was never written from the continuity check of every earlier entry that lists it and from this
# entry's list comparison, when (a) nothing is at its path (a dangling link is something; a path that cannot be checked
# may hold it), (b) no line of the decisions source scopes or names it (in a JSON row, any string value that resolves to
# it; no decisions source counts as one), (c) it is the last element of the scope= list of the latest earlier entry that
# lists it, (d) this entry's own scope= does not list it and is the previous entry's list without it followed only by
# appended manifests, and (e) no row of a repairs file any entry of the Task names names it as before or after.
# The token is the entry's own (never inherited) and applies whole: any unmet condition is mission-grammar ((e):
# repair-scope-mismatch) and the rules apply unchanged. The JSON's mission.withdrawn lists each token of the Task.
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
# Path keys and the legacy matrix (PRD-dream-generation-aware-mission-records R4, R1): each
# manifest's entries are also keyed by path, the line's path resolved against the manifest's
# directory; the scope id stays basename-based. A repairs row's `changed` and `added` hold paths
# relative to the `after` manifest's directory, `removed` relative to `before`'s, and `delta`
# {changed: [{path, before, after}], added: [{path, sha256}], removed: [{path, sha256}]} records
# them: a path entry (it holds `/`) needs its record, whose digests must be the two manifests'
# (repair-hash-mismatch naming path and digests). A row without `delta` is a legacy row: its bare
# basenames keep the basename rule, and one several entries of a manifest hold is listed in
# mission.repairs.ambiguous, never failed; a `delta` row naming such a basename is repair-grammar
# naming the paths. The undeclared-change pass keys entries holding `/` by path; bare names,
# entries in the directory of either manifest of the pair and header members (the repairs file
# included) by basename; a header member twice in one manifest is mission-scope-mismatch. A header
# member is looked up by its basename in every pass (a row without `delta` may name one by path,
# checked as installed), and every comparison of a row entry with a header member, an edge
# endpoint or a hold reads its basename; a record matches its entry by resolved key. A manifest
# whose frozen header has no `matrix`, first listed by an entry dated (Route decision=, else header
# ts) before LEGACY_MATRIX_SINCE, that lists exactly one *-adversarial.md keeps that matrix when an
# entry of the mission not later than the linted one names it in adversarial= or its copy at the
# listed digest passes the matrix grammar; otherwise the matrix rule above applies unchanged.
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
import os, re, sys, json, subprocess, tempfile, shutil, datetime, hashlib, shlex

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
# PRD-dream-analysis-trigger-record (A1723) R7: R1-R5 apply to entries whose header timestamp is at or after the cutover instant, this date's midnight
# at -08:00 (after_cutover), the merge date written here when the change lands (one ISO date, never a counter; shared with
# PRD-dream-finding-consumption). Earlier entries lint byte for byte as at 43d5b39.
TRIGGER_CUTOVER = "2026-11-20"
FAILURE_CLASSES = ("recurring-failure", "failed-acceptance", "consequential-obstacle", "transient", "other")
TRIGGER_CLASSES = ("recurring-failure", "failed-acceptance", "consequential-obstacle")
# R2 (amended 2026-11-19, Hermes H2): the resolver's own outage texts (skill-route-resolve.py 007932da...), each a whole `reasons` value. The two
# `policy-missing:` texts (a policy file the caller named) and every other text are no outage. Whether an outage was caller-induced (a malformed policy
# reached through SKILL_ROUTE_POLICY, --policy or FABLE_LAUNCH_TEST, or `ledger lookup unavailable` through PATH) is not in the row: A1300's producer.
OUTAGE_TEXTS = ("policy file not found", "policy is malformed")
OUTAGE_RES = (re.compile(r"malformed policy JSON: [A-Za-z_][A-Za-z0-9_]*"),   # the ledger id grammar is the resolver's own (line 140); its `$`
              # also matches before a trailing newline, so a caller-written `ledger:A1\n` reaches the outage text with a newline, which this refuses
              # (fail closed; R2 refuses caller-induced texts anyway, review r13 LOW-6)
              re.compile(r"ledger lookup unavailable; cannot verify ledger:[A-Za-z0-9][A-Za-z0-9._-]{0,63} \(fail closed\)"))
OUTAGE_INFIX = "(policy error, fail closed)"


class Exit2(Exception):
    pass


def usage(msg):
    raise Exit2(msg + " (usage: dream-run-note-lint.sh <dream-log.md> [--last | --entry <ISO-ts>] "
                "[--json] [--prd-dir <dir>] [--decisions <path>] [--scope-root <recorded root>=<PRD home> ...] | --matrix <path> --states "
                "<slug=value ...> [--json] | --scope-id <manifest> | --edges <path> [--prds <PRD basename ...>] [--json] "
                "| --consumption <record> --task <T> [--page <page>] [--prd-home <dir>] [--reviews <dir>] [--decisions <path>] "
                "[--require-closed] [--json] | --selftest)")


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


class ScopeRoots:
    """Q5 (A1723 source request 6, ruled A): --scope-root <recorded root>=<this run's PRD home>, given by the case-11
    gate from a delivered decisions source that names the PRD home root its rows were written under. A review row's
    absolute `scope` under a recorded root is read at the same relative path under the local home; every such read is
    recorded with both paths. A scope under no recorded root, and every relative scope, is read as before."""

    def __init__(self, pairs, home):
        self.pairs, self.home, self.reads = pairs, home, []

    def path(self, scope, row=None):
        """-> (the file read, the recorded root it was mapped under or None)."""
        full = scope if os.path.isabs(scope) else os.path.join(self.home, scope)
        if not os.path.isabs(scope):
            return full, None
        n = os.path.normpath(scope)
        for root, local in self.pairs:
            if n.startswith(root + os.sep):
                got = os.path.join(local, n[len(root) + 1:])
                rec = {"scope": scope, "read": got, "root": root,
                       "session": row.get("session") if isinstance(row, dict) else None}
                if rec not in self.reads:
                    self.reads.append(rec)
                return got, root
        return full, None


def scope_roots(vals, home):
    """Q5: the --scope-root values -> [(recorded root, local home)]. Exit 2 for a value that is not
    <absolute root>=<this run's PRD home>, a root of /, two roots where one holds the other, or a root that holds this
    run's PRD home or lies inside it (equal to it is the identity)."""
    pairs = []
    for v in vals or []:
        if v.count("=") != 1:
            usage(f"--scope-root {v!r}: not <recorded root>=<this run's PRD home> (one '=')")
        root, local = v.split("=")
        if not os.path.isabs(root) or os.path.normpath(root).strip("/") == "":
            usage(f"--scope-root {v!r}: the recorded root is not an absolute directory below /")
        if not local or os.path.realpath(local) != os.path.realpath(home):
            usage(f"--scope-root {v!r}: maps onto {local!r}, not this run's PRD home {home}")
        root, hp = os.path.normpath(root), os.path.realpath(home)
        for h in sorted({hp, os.path.abspath(home)}):      # the home as given and its real path (review r22 L1)
            if root != h and (h.startswith(root + os.sep) or root.startswith(h + os.sep)):
                usage(f"--scope-root {v!r}: the recorded root {root} and this run's PRD home {h} hold one another, so a "
                      "scope written on this host would be read at another path")
        for r0, _ in pairs:
            if r0 == root or r0.startswith(root + os.sep) or root.startswith(r0 + os.sep):
                usage(f"--scope-root {v!r}: the recorded root {root} overlaps {r0}")
        pairs.append((root, os.path.realpath(home)))
    return pairs


def scope_file(resolve, scope, row=None):
    """The file a review row's `scope` names on this host, and the --scope-root it was read under (or None)."""
    sr = getattr(resolve, "scope_roots", None)
    return sr.path(scope, row) if sr is not None else (resolve(scope), None)


def scope_digests(resolve, scope, row):
    """{basename: digest} of a review row's scope manifest, {} when unreadable. A read under a --scope-root binds by
    content only: its canonical id must be the row's scope_id (Q5), else it reads as unreadable."""
    if not isinstance(scope, str):
        return {}
    full, root = scope_file(resolve, scope, row)
    try:
        got, dg = scope_canon(full)
    except ScopeError:
        return {}
    return {} if root is not None and got != row.get("scope_id") else dg


def manifest_paths(full):
    """PRD-dream-generation-aware-mission-records R4: a manifest's entries keyed by path, in line
    order: [(path as written, resolved key, basename, digest)], each path resolved against the
    manifest's directory and normalized, as manifest paths are compared. None when the manifest is
    unreadable or breaks the line rule (scope_canon reports that)."""
    try:
        with open(full, "rb") as fh:
            data = fh.read()
    except OSError:
        return None
    if not data or not data.endswith(b"\n"):
        return None
    d = os.path.dirname(full)
    out = []
    for ln in data[:-1].split(b"\n"):
        if not SCOPE_LINE_RE.fullmatch(ln):
            return None
        h, raw = ln.split(b"  ", 1)
        ps = raw.decode("utf-8", "backslashreplace")
        out.append((ps, os.path.normpath(os.path.join(d, ps)), ps.rsplit("/", 1)[-1], h.decode("ascii")))
    return out


def entry_key(manifest_full, rel):
    """R4: a row entry's key, the path resolved against the directory of the manifest it is relative to."""
    return os.path.normpath(os.path.join(os.path.dirname(manifest_full), rel))


def split_keys(m, members, dirs=()):
    """R4: ({basename: digest} of the basename-keyed entries, {key: digest} of the path-keyed ones).
    Basename-keyed: a bare name, an entry in the manifest's own directory or in a directory of dirs
    (the other manifest of a compared pair, so a file one manifest lists bare and the other by path
    is compared), a header member; the first digest of a basename is the first of the sorted canon,
    as installed."""
    mdirs = {os.path.normpath(os.path.dirname(m["full"]))} | set(dirs)
    bk, pk = {}, {}
    for raw, key, base, dg in sorted(m.get("entries") or [], key=lambda e: (e[3], e[2])):
        if "/" not in raw or os.path.dirname(key) in mdirs or base in members:
            bk.setdefault(base, dg)
        else:
            pk.setdefault(key, dg)
    return bk, pk


def key_collisions(m, members, dirs=()):
    """R4 collisions (Q1 ruling, A1723 request 4): ({key: [digests]} for one resolved key a manifest lists
    at two or more digests, {basename: [(key, digest)]} for one basename a manifest lists for two files,
    one in each directory of a compared pair (dirs)). Header members are left to their occurs-twice rule.
    Either is mission-scope-mismatch; a pair compares neither (the name does not name one file)."""
    mdirs = {os.path.normpath(os.path.dirname(m["full"]))} | set(dirs)
    by_key, by_base = {}, {}
    for raw, key, base, dg in m.get("entries") or []:
        by_key.setdefault(key, set()).add(dg)
        if base not in members and ("/" not in raw or os.path.dirname(key) in mdirs):
            by_base.setdefault(base, {}).setdefault(key, set()).add(dg)
    two = {k: sorted(v) for k, v in by_key.items() if len(v) > 1}
    twins = {b: sorted((k, d) for k, ds in ks.items() for d in ds) for b, ks in by_base.items() if len(ks) > 1}
    return two, twins


def member_twins(m, names):
    """R4 collisions (Q1 ruling; review r20 F1): {basename: [(key, digest)]} for a basename in names, the header members
    of the other manifest of a compared pair that are not this manifest's own, that this manifest lists for two or more
    files. In the pair such a basename is keyed by basename (split_keys), so its files would compare as one; its own
    occurs-twice rule reads only its own members. Either way it is mission-scope-mismatch, and the pair compares it not."""
    by = {}
    for raw, key, base, dg in m.get("entries") or []:
        if base in names:
            by.setdefault(base, {}).setdefault(key, set()).add(dg)
    return {b: sorted((k, d) for k, ds in ks.items() for d in ds) for b, ks in by.items() if len(ks) > 1}


def entry_date(e):
    """R1: an entry's date: its Route line's decision= instant, else its header ts."""
    for ln in e["lines"]:
        mm = re.match(r"^Route:.*\bdecision=(\S+)", ln)
        if ln.startswith("Route:") and mm and parse_iso(mm.group(1)) is not None:
            return parse_iso(mm.group(1))
    return parse_iso(e["ts"])


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
    full, root = scope_file(resolve, scope, row)
    mapped = f"the row's scope {scope}, read at {full} under --scope-root {root}: " if root is not None else ""
    if root is not None:
        rv["scope_read"] = {"scope": scope, "read": full, "root": root}
    try:
        got, digests = scope_canon(full)
    except ScopeError as e:
        L.fail("review-scope-mismatch", f"{who}: {mapped}{e}")
        return False
    if ok and got != sid:
        L.fail("review-scope-mismatch", f"{who}: {mapped}scope {full} canonicalizes to {got}, the row's scope_id is {sid}")
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
MISSION_KEYS = ("edges", "scope", "repairs")
MISSION_TOKENS = MISSION_KEYS + ("withdrawn",)    # Repair 6: withdrawn= belongs to its own entry and is never inherited
EDGE_KEYS = ("id", "status", "producer", "consumer")


def parse_mission_line(line):
    """R1 grammar of one `Mission: <name> edges=<p> [scope=<p>[,<p>...]] [repairs=<p>] [withdrawn=<p>[,<p>...]]` line:
    (name or None, {key: value; scope and withdrawn lists}, [(token, why)])."""
    toks = line[len("Mission:"):].split()
    probs, keys, name = [], {}, None
    if not toks:
        return None, keys, [("Mission:", "no mission name")]
    rest = toks
    k0 = toks[0].split("=", 1)[0]
    if "=" in toks[0] and k0 in MISSION_TOKENS:
        probs.append((toks[0], "no mission name before the key=value tokens"))
    else:
        if MISSION_NAME_RE.fullmatch(toks[0]):
            name = toks[0]
        else:
            probs.append((toks[0], "name outside ^[a-z0-9][a-z0-9._-]*$"))
        rest = toks[1:]
    for t in rest:
        k, eq, v = t.partition("=")
        if not eq or k not in MISSION_TOKENS:
            probs.append((t, "unknown token (only edges=, scope=, repairs= and withdrawn= follow the name)"))
        elif k in keys:
            probs.append((t, f"a second {k}= token"))
        elif not v:
            probs.append((t, "empty value"))
        elif k in ("scope", "withdrawn"):
            items = v.split(",")
            if not all(items):
                probs.append((t, f"an empty {k}= item"))
            elif k == "withdrawn" and len({os.path.normpath(x) for x in items}) != len(items):
                probs.append((t, "a withdrawn= item repeats"))
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


def post_review_reuse(entries, ei, adv, mrec, rows, task, reviews_raw, resolve):
    """Producer-contract Repair 5 (A1723 decision 3, addendum 3): a post-review entry may name the previous entry's
    matrix when (a) its adversarial= path and uncovered= equal the previous entry's, (b) its Mission: scope= is the
    previous entry's, nothing added, and (c) its Review: lines are the previous entry's plus at least one new line,
    each new line's latest launch row of the Task having role review and the last listed manifest's scope_id."""
    if ei < 1 or task is None or not mrec or not mrec.get("scope") or not mrec.get("earlier"):
        return False
    prev = entries[ei - 1]
    if entry_task(prev) != task:
        return False
    pa = [ln for ln in prev["lines"] if ln.startswith("Analysis:")]
    pv = parse_analysis(pa[-1])[0].get("adversarial") if pa else None
    if not pv or pv[0] != "matrix" or adv[0] != "matrix" or pv[2] != adv[2] \
            or os.path.normpath(resolve(pv[1])) != os.path.normpath(resolve(adv[1])):
        return False                                                             # (a)
    pscope = (mrec["earlier"][-1]["eff"].get("scope") or ([], None))[0]
    if [os.path.normpath(resolve(x)) for x in pscope] != [os.path.normpath(resolve(x)) for x in mrec["scope"]]:
        return False                                                             # (b)
    old = [ln.rstrip() for ln in prev["lines"] if ln.startswith("Review:")
           and not re.fullmatch(r"Review:\s+none\s*", ln)]                    # review r23 L2: `Review: none` is no line
    cur = [ln.rstrip() for ln in reviews_raw]
    new = [ln for ln in cur if ln not in old]
    if not new or any(ln not in cur for ln in old):
        return False                                                             # (c) the previous lines plus a new one
    try:
        last_id = scope_canon(resolve(mrec["scope"][-1]))[0]
    except ScopeError:
        return False
    for ln in new:
        m = re.match(r"^Review:\s+\S+\s+reviewer-session=(\S+)", ln)
        lr = [r for r in rows or [] if m and r.get("session") == m.group(1) and r.get("decision") == "launch"
              and r.get("skill") == "dream" and r.get("task_id") == task]
        if not lr or lr[-1].get("role") != "review" or lr[-1].get("scope_id") != last_id:
            return False                                                         # (c) each new line's launch row
    return True


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
        return fh["matrix"], "matrix named by the frozen edges header", seq[first][2]
    dates = [x.get("date") for x in mrec["earlier"]] + [mrec.get("date")]
    one = legacy_matrix(m, fh, first, seq, dates)
    if one is not None:
        return one, LEGACY_MATRIX_RULE, seq[first][2]
    src = next((i for i, (_, a, _) in enumerate(seq) if i >= first and a), None)
    mx = seq[src][1] if src is not None else None
    return (os.path.basename(mx) if mx else None), "matrix named by adversarial= (the header names none)", seq[first][2]


def legacy_matrix(m, fh, first, seq, dates):
    """PRD-dream-generation-aware-mission-records R1: the basename of the one *-adversarial.md entry
    of a manifest whose frozen header has no `matrix`, first listed by an entry dated before
    LEGACY_MATRIX_SINCE, when an entry of the mission not later than the linted one names it in
    adversarial= or its copy at the listed digest passes the matrix grammar for the first-listing
    entry's State slugs that are prds members of the frozen header. None otherwise (no such entry,
    two or more, or one neither named nor passing): the matrix-per-manifest rule applies unchanged."""
    since = parse_iso(LEGACY_MATRIX_SINCE)
    d = dates[first] if first < len(dates) else None
    if since is None or d is None or not d < since or not fh:
        return None
    mx = {}
    for raw, key, base, dg in m.get("entries") or []:
        if base.endswith("-adversarial.md"):
            mx.setdefault(key, (base, dg))
    if len(mx) != 1:
        return None
    key, (base, dg) = next(iter(mx.items()))
    if any(a and os.path.basename(a) == base for _, a, _ in seq):
        return base
    if file_sha(key) != dg:
        return None
    sub = Lint()
    sl = [s for s in dict.fromkeys(seq[first][2]) if fh and f"PRD-{s}.md" in fh["prds"]]
    lint_matrix(sub, key, key, sl)
    return None if sub.findings else base


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


def path_keys(full):
    """The forms one resolved path is compared by (Repair 6): its normalized and its real path."""
    return {os.path.normpath(full), os.path.realpath(full)}


def withdrawn_scoped(w, resolve, dec):
    """Repair 6 (b): why a line of the decisions source may have scoped manifest w, or None. Every line is read,
    whatever its task, role or session. In a JSON row, every string value (its scope, a list's items, any other field)
    is compared as a path: as written, and for an absolute path under a --scope-root also as mapped; one that resolves
    to w counts (review r23d L2). A line that is no JSON object counts when it names w as written, resolved or relative
    to the PRD home. With no decisions source read, nothing rules a row out."""
    if dec is None:
        return "no decisions source was read, so a launch row scoping it cannot be ruled out"
    full = resolve(w)
    wk = path_keys(full)
    sr = getattr(resolve, "scope_roots", None)
    names = {w, full, os.path.relpath(os.path.normpath(full), resolve("."))} | wk

    def is_w(v):
        if not v.strip() or "\0" in v:
            return False
        forms = [resolve(v)]
        if sr is not None and os.path.isabs(v):
            m = os.path.normpath(v)
            forms += [os.path.join(local, m[len(root) + 1:]) for root, local in sr.pairs if m.startswith(root + os.sep)]
        return any(path_keys(f) & wk for f in forms)

    def strings(v, key):
        if isinstance(v, str):
            yield key, v
        elif isinstance(v, list):
            for x in v:
                yield from strings(x, key)
        elif isinstance(v, dict):
            for k, x in v.items():
                yield from strings(x, k)
    for n, ln in enumerate(read_text(dec["path"]).splitlines(), 1):
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            r = None
        if isinstance(r, dict):
            for k, v in strings(r, None):
                if is_w(v):
                    how = "scopes it" if k == "scope" else f"names it in {k}"
                    return (f"decisions line {n} (session {r.get('session')}, role {r.get('role')}) {how}, "
                            "so it may have been reviewed")
        elif any(x in ln for x in names):
            return f"decisions line {n}, which is no JSON object, names it, so a launch row scoping it cannot be ruled out"
    return None


def withdrawn_check(p, seq, resolve, dec):
    """Repair 6 (the PRD author's addendum 4): [(manifest, finding id, why)] for the withdrawn= token of seq[p], one
    item per unmet condition ([] when the token applies). seq is the same-Task entries carrying a Mission: line, in
    log order, the linted entry last; each item has ts, eff (tokens carried or inherited), own_scope (the line's own
    scope= or None) and withdrawn. A manifest may be withdrawn when (a) its file does not exist (nothing, not even a
    dangling link, is at its path); (b) no line of the decisions source scopes or names it; (c) it is the last element of the scope= list of the latest earlier entry that
    lists it (only a planned freeze can be withdrawn); (d) this entry carries its own scope=, which does not list it
    and is the previous entry's list without the withdrawn manifests followed only by appended manifests; and (e) no
    row of a repairs file any entry of the Task names, up to the linted one, names it as before or after (review r23d M1).
    A token applies only whole."""
    x, ws = seq[p], seq[p]["withdrawn"]
    tok = ",".join(ws)

    def same(a, b):
        return bool(path_keys(resolve(a)) & path_keys(resolve(b)))

    def scope_of(y):
        return (y["eff"].get("scope") or ([], None))[0]
    bad = []
    reps = []
    for y in seq:
        rp = (y["eff"].get("repairs") or (None, None))[0]
        if rp and rp not in reps:
            reps.append(rp)
    for w in ws:
        try:
            os.lstat(resolve(w))
            bad.append((w, "mission-grammar", f"{resolve(w)} exists; only a manifest that was never written is withdrawn"))
        except (FileNotFoundError, NotADirectoryError):
            pass                                 # (a): only a path that is not there is absent (review r23d L1)
        except OSError as e:
            bad.append((w, "mission-grammar", f"{resolve(w)} cannot be checked ({e.strerror}), so it may exist"))
        why = withdrawn_scoped(w, resolve, dec)
        if why:
            bad.append((w, "mission-grammar", why))
        lister = next((y for y in reversed(seq[:p]) if any(same(w, m) for m in scope_of(y))), None)
        if lister is None:
            bad.append((w, "mission-grammar", "no earlier entry of this Task lists it in scope="))
        elif not same(w, scope_of(lister)[-1]):
            bad.append((w, "mission-grammar", f"it is not the last element of the scope= list of entry {lister['ts']}, "
                                              "the latest that lists it (only a planned freeze, listed last, is withdrawn)"))
        if x["own_scope"] is not None and any(same(w, m) for m in x["own_scope"]):
            bad.append((w, "mission-grammar", "this entry's scope= still lists it"))
        for rp in reps:
            for n, r in repairs_rows({"repairs": rp}, resolve):
                for side in ("before", "after"):
                    if isinstance(r.get(side), str) and r[side] and same(w, r[side]):
                        bad.append((w, "repair-scope-mismatch", f"row {n} of {rp} names it as {side}"))
    if x["own_scope"] is None:
        bad.append((tok, "mission-grammar", "this entry's Mission: line carries no scope= of its own"))
    elif p > 0:
        base = [m for m in scope_of(seq[p - 1]) if not any(same(m, w) for w in ws)]
        if [os.path.normpath(resolve(m)) for m in x["own_scope"][:len(base)]] != \
                [os.path.normpath(resolve(m)) for m in base]:
            bad.append((tok, "mission-grammar", f"this entry's scope= is not the scope= list of entry {seq[p - 1]['ts']} "
                                                "without the withdrawn manifests, followed only by appended manifests"))
    return bad


def mission_record(L, entries, ei, task, states, resolve, dec=None):
    """Edge-map R1-R5 for entry ei: the Mission: line, its inheritance and continuity across
    same-Task entries, the edges file and the State slugs. Returns None when neither this
    entry nor an earlier same-Task entry carries the line, else a dict (`line` False when only
    the continuity rule applied). dec ({path, rows} of the decisions source, or None) is read
    only for a withdrawn= token (Repair 6)."""
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
                if k in MISSION_KEYS:
                    eff[k] = (v, e["ts"])
            prev = eff
            earlier.append({"ts": e["ts"], "name": nm, "eff": eff, "slugs": entry_state_slugs(e), "adv": entry_matrix(e),
                            "date": entry_date(e), "own_scope": toks.get("scope"), "withdrawn": toks.get("withdrawn") or []})
    if not mls and not earlier:
        return None
    reported = set()

    def miss(detail, key):
        if key not in reported:
            reported.add(key)
            L.fail("mission-edges-missing", detail)

    # Repair 6: the withdrawn= tokens of the earlier entries and of this one, each applying whole or not at all
    ctoks = parse_mission_line(mls[0])[1] if len(mls) == 1 else {}
    ceff = dict(earlier[-1]["eff"]) if earlier else {}
    ceff.update({k: (v, entry["ts"]) for k, v in ctoks.items() if k in MISSION_KEYS})
    seq = earlier + [{"ts": entry["ts"], "eff": ceff, "own_scope": ctoks.get("scope"), "withdrawn": ctoks.get("withdrawn") or []}]
    wd = []
    for p, y in enumerate(seq):
        if y["withdrawn"]:
            bad = withdrawn_check(p, seq, resolve, dec)
            wd.append({"pos": p, "entry": y["ts"], "manifests": list(y["withdrawn"]), "applies": not bad, "bad": bad})

    def withdrawn_after(i, mp):
        """(applying withdrawal, or a non-applying one, or None) of manifest mp by an entry later than earlier[i]."""
        hits = [w for w in wd if w["pos"] > i and any(path_keys(resolve(mp)) & path_keys(resolve(m)) for m in w["manifests"])]
        return next((w for w in hits if w["applies"]), hits[-1] if hits else None)

    # continuity set (R1): live headers + frozen copies of every earlier scope= manifest + earlier State slugs
    cont, by_name = set(), {}
    for i, x in enumerate(earlier):
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
            wa = withdrawn_after(i, mp) if wd else None
            if wa is not None and wa["applies"]:
                continue                       # Repair 6: withdrawn by a later entry; nothing of it was written
            mfull = resolve(mp)
            copy, _, err = frozen_edges_copy(mfull, base)
            if err:
                note = (f"; withdrawn= of entry {wa['entry']} does not apply: "
                        + "; ".join(f"{m}: {why}" for m, _, why in wa["bad"])) if wa is not None else ""
                miss(f"{copy}: {err} (continuity of entry {x['ts']}{note})", copy)
                continue
            hd, _, _ = read_edges(copy, copy)
            if hd is None:
                miss(f"{copy}: the frozen edges copy has no header (continuity of entry {x['ts']})", copy)
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
           "header": None, "edge_list": [], "earlier": earlier, "cont": cont, "date": entry_date(entry),
           "withdrawn": [{"entry": w["entry"], "manifests": w["manifests"], "applies": w["applies"],
                          "why": [f"{m}: {why}" for m, _, why in w["bad"]]} for w in wd]}
    own = wd[-1] if wd and wd[-1]["pos"] == len(earlier) else None
    if own is not None:
        for m, fid, why in own["bad"]:
            L.fail(fid, f"token 'withdrawn={','.join(own['manifests'])}': {m}: {why}; the token does not apply")
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
        if ps and own is not None and own["applies"]:     # Repair 6: compared without what this entry withdraws
            ps = ([x for x in ps[0] if not any(path_keys(resolve(x)) & path_keys(resolve(m)) for m in own["manifests"])],
                  ps[1])
        if "scope" in toks and ps and [os.path.normpath(resolve(x)) for x in toks["scope"][:len(ps[0])]] != \
                [os.path.normpath(resolve(x)) for x in ps[0]]:
            L.fail("mission-grammar", f"token 'scope={','.join(toks['scope'])}': does not begin with the scope= list "
                                      f"entry {last['ts']} carries or inherits ({','.join(ps[0])}); a later entry "
                                      "extends the list, never shortens or reorders it")
    rec["inherited_from"] = max(src, key=lambda t: [x["ts"] for x in earlier].index(t)) if src else None
    rec["edges"], rec["scope"], rec["repairs"] = eff.get("edges"), eff.get("scope") or [], eff.get("repairs")
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
    out = {"name": rec["name"], "edges_file": rec["edges"], "scope": list(rec["scope"]), "repairs": rec["repairs"],
           "inherited_from": rec["inherited_from"], "single_component": hd["single_component"] if hd else None,
           "prds": len(hd["prds"]) if hd else 0, "edges": edge_counts(edges),
           "unknown_edges": [e["id"] for e in edges if e["status"] == "unknown"]}
    if rec.get("withdrawn"):              # Repair 6: present only when an entry of the Task carries withdrawn=
        out["withdrawn"] = rec["withdrawn"]
    return out


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
# PRD-dream-generation-aware-mission-records R1: a legacy-header manifest first listed before this
# instant may keep the one matrix it lists. The commit instant of the per-manifest matrix lint,
# PRD-dream-matrix-per-manifest's landing (vibecode-kit 43d5b39), from which an edges header could
# carry `matrix` (Q4 ruling, A1723 request 5); recorded in history.md.
LEGACY_MATRIX_SINCE = "2026-11-18T06:04:49-08:00"
LEGACY_MATRIX_RULE = "the one matrix this legacy manifest lists, first listed before LEGACY_MATRIX_SINCE"
MISSION_IDS = ("mission-grammar", "mission-edges-missing", "edge-grammar", "edge-unexplained",
               "edge-unknown-unowned", "edge-node-unlisted", "mission-prd-unlisted",
               "mission-scope-mismatch", "mission-scope-incomplete", "mission-review-missing",
               "mission-verdict-missing", "mission-finding-incomplete", "mission-snapshot-stale", "sidecar-correction-unbound",
               "mission-approval-blocked")


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
    for p in mrec["scope"]:
        full = resolve(p)
        try:
            sid, digests = scope_canon(full)
        except ScopeError as e:
            L.fail("mission-scope-mismatch", f"manifest {p}: {e}")
            sid, digests = None, {}
        mans.append({"path": p, "full": full, "id": sid,
                     "names": {k.decode("utf-8", "backslashreplace"): v for k, v in digests.items()},
                     "entries": (manifest_paths(full) or []) if sid is not None else [],
                     "frozen": None, "frozen_edges": []})
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
            dg = scope_digests(resolve, k["row"].get("scope"), k["row"])
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


def repairs_rows(mrec, resolve):
    """[(row number, row)] of the Mission: line's repairs file, JSON objects only ([] when absent or unreadable: the
    repair sweep reports that)."""
    tok = mrec.get("repairs") if mrec else None
    if not tok:
        return []
    try:
        with open(resolve(tok), "rb") as fh:
            text = fh.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    out = []
    for n, ln in enumerate(text.split("\n"), 1):
        try:
            r = json.loads(ln) if ln.strip() else None
        except ValueError:
            r = None
        if isinstance(r, dict):
            out.append((n, r))
    return out


def late_declared(mans, k, exts, eb, rep_rows, admitted, reviewer, resolve):
    """Producer-contract Repair 4 (A1723 decision 3, addendum 2): the externals a chain review of manifest k may name
    though its frozen edges header does not declare them. {name: {manifest, repairs_row}} for each name the frozen
    header of the next listed manifest declares, when a repairs row with before = manifest k and after = that next
    manifest names the edges file in changed, written by the mission's author (an admitted author session when the
    host is governed), never the reviewer. Any other name stays mission-finding-incomplete."""
    if k + 1 >= len(mans) or mans[k + 1]["id"] is None or not mans[k + 1].get("frozen"):
        return {}
    nxt = mans[k + 1]
    names = set(nxt["frozen"]["external_names"]) - exts
    if not names or not eb:
        return {}

    def at(p):
        return isinstance(p, str) and p.strip() and os.path.normpath(resolve(p))
    for n, r in rep_rows:
        a_s, ch = r.get("author_session"), r.get("changed")
        if (at(r.get("before")) == os.path.normpath(mans[k]["full"]) and at(r.get("after")) == os.path.normpath(nxt["full"])
                and isinstance(ch, list) and any(isinstance(x, str) and os.path.basename(x) == eb for x in ch)
                and isinstance(a_s, str) and a_s.strip() and a_s != reviewer and (admitted is None or a_s in admitted)):
            return {nm: {"manifest": nxt["path"], "repairs_row": n} for nm in sorted(names)}
    return {}


def sidecar_rows(data):
    """A findings sidecar's rows: [(line number, JSON value or None)] for each non-blank line."""
    out = []
    for n, ln in enumerate(data.decode("utf-8", "replace").split("\n"), 1):
        if ln.strip():
            try:
                out.append((n, json.loads(ln)))
            except ValueError:
                out.append((n, None))
    return out


def sc_rows(c, rows_sc, sc, prset, exts, ids_seen, fail, live, late=None, hist=None):
    """Chain-review R4 on one sidecar's rows: each failure goes to fail(id, detail). `live` reads the rows as the
    review's findings (ids_seen, named, findings, advisory); a historical pass (Repair 2's original) only records.
    late: {name: declaration} of the externals the next freeze declares (producer-contract Repair 4); a consumer
    external:<name> its review's frozen header does not declare passes when late names it, and the live pass sends
    the failure it would have been to hist."""
    mine = set()
    for n, r in rows_sc:
        def bad(field, why, n=n):
            fail("mission-finding-incomplete", f"{sc}: row {n}: field {field}: {why}")
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
            if live and rid in ids_seen:
                fail("mission-finding-incomplete", f"finding id {rid} in {ids_seen[rid]} and {sc}: an id names its "
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
        undecl = [x for x in co if not (x in prset or (isinstance(x, str) and x.startswith("external:") and x[9:] in exts))] \
            if isinstance(co, list) else None
        late_ok = bool(undecl) and bool(late) and all(isinstance(x, str) and x.startswith("external:") and x[9:] in late
                                                      for x in undecl)
        if not isinstance(co, list) or (undecl and not late_ok) or (not co and not adv_row and cls != "provenance"):
            bad("consumers", "not a list of prds members or declared external:<name> (empty only for class provenance)")
            ok = False
        elif late_ok and live and hist is not None:
            hist({"id": "mission-finding-incomplete",
                  "detail": f"{sc}: row {n}: field consumers: {', '.join(undecl)} not declared by its review's frozen "
                            "edges header", "declared_by": {x: late[x[9:]] for x in undecl}})
        if adv_row:
            ac = r.get("accepts")
            if not isinstance(ac, list) or not ac or not all(isinstance(x, str) and x.strip() for x in ac):
                bad("accepts", "not a non-empty list of finding ids")
                ok = False
        if not live:
            continue
        if isinstance(rid, str) and rid.strip() and rid not in ids_seen:
            ids_seen[rid] = sc
            if not adv_row:
                c["named"].append(r)
        if ok:
            (c["advisory"] if adv_row else c["findings"]).append(r)


CORRECTED_RE = re.compile(r"\.findings\.corrected-([1-9][0-9]*)\.jsonl$")


def dup_keys(data):
    """[(line number, key)] for each key repeated inside one JSON object of a JSONL file, at any depth (review r21 L2: a
    parsed row keeps the last of two equal keys, so value equality would pass a byte change a first-wins reader sees)."""
    out = []
    for n, ln in enumerate(data.decode("utf-8", "replace").split("\n"), 1):
        if not ln.strip():
            continue

        def hook(pairs, n=n):
            seen = set()
            for k, _ in pairs:
                if k in seen:
                    out.append((n, k))
                seen.add(k)
            return dict(pairs)
        try:
            json.loads(ln, object_pairs_hook=hook)
        except ValueError:
            pass
    return out


def corrected_sidecar(L, c, f, full, sbytes, rows_sc, rows, task):
    """Producer-contract Repair 2 (A1723 decision 3): <verdict>.findings.corrected-<n>.jsonl beside the sidecar. Its first
    row is {"corrects": <the original sidecar's sha256>, "session": <the chain review's session>}, written by that session
    resumed (a launch row of the task with skill dream, role review, the review's scope_id and resume true, later than that
    session's first such row without resume; review r21 L1); its other rows are the original's, in order, each changing
    only prds and consumers, with no key repeated in any row of either file (review r21 L2, r23 L1). Each refused file is
    sidecar-correction-unbound. -> (shown path, rows) of the highest valid n, or None."""
    d, base = os.path.dirname(full), os.path.basename(full)
    try:
        names = sorted((int(m.group(1)), nm) for nm in os.listdir(d or ".")
                       for m in [CORRECTED_RE.search(nm)] if m and nm[:m.start()] == base)
    except OSError:
        names = []
    sess, sid = c["rv"]["session"], c["row"].get("scope_id")
    orig_sha = hashlib.sha256(sbytes).hexdigest()
    best = None
    for _, nm in names:
        shown = os.path.join(os.path.dirname(f), nm) if os.path.dirname(f) else nm
        try:
            with open(os.path.join(d, nm), "rb") as fh:
                raw = fh.read()
            got = sidecar_rows(raw)
        except OSError as e:
            L.fail("sidecar-correction-unbound", f"{shown}: unreadable ({e.strerror or type(e).__name__})")
            continue
        why = []
        dups = dup_keys(raw)
        if dups:
            why.append("a key repeated in one row (" + ", ".join(f"row {n}: {k}" for n, k in dups) + "): rows are "
                       "compared as parsed, so a repeated key could hide a byte change")
        odups = dup_keys(sbytes)
        if odups:                        # review r23 L1: the original it is compared with, too
            why.append("the original sidecar repeats a key in one row (" + ", ".join(f"row {n}: {k}" for n, k in odups)
                       + "): rows are compared as parsed, so a repeated key could hide a byte change")
        head = got[0][1] if got else None
        if not (isinstance(head, dict) and set(head) == {"corrects", "session"}):
            why.append("its first row is not {\"corrects\": <sha256>, \"session\": <session>}")
        else:
            if head["corrects"] != orig_sha:
                why.append(f"corrects {head['corrects']!r} is not the original sidecar's sha256 {orig_sha}")
            if head["session"] != sess:
                why.append(f"written by session {head['session']!r}, not the chain review's own session {sess}")
            else:
                mine = [r for r in rows if r.get("decision") == "launch" and r.get("skill") == "dream"
                        and r.get("task_id") == task and r.get("session") == sess and r.get("role") == "review"
                        and r.get("scope_id") == sid]
                first = [t for t in (parse_iso(r.get("ts")) for r in mine if r.get("resume") is not True) if t]
                if not any(r.get("resume") is True for r in mine):
                    why.append(f"no launch row resumes session {sess} with role review and scope_id {sid}")
                elif not first:
                    why.append(f"session {sess} has no review launch row with scope_id {sid} that is not a resume, so "
                               "no row shows a resumption after the review")
                elif not any(r.get("resume") is True and (parse_iso(r.get("ts")) or min(first)) > min(first) for r in mine):
                    why.append(f"no launch row resuming session {sess} is later than its review launch at "
                               f"{min(first).isoformat()}")
        body = got[1:]
        if len(body) != len(rows_sc):
            why.append(f"{len(body)} finding rows, the original has {len(rows_sc)}")
        for (cn, cr), (on, orw) in zip(body, rows_sc):
            if not (isinstance(cr, dict) and isinstance(orw, dict)):
                why.append(f"row {cn}: not a JSON object row against original row {on}")
                continue
            keep = lambda r: {k: v for k, v in r.items() if k not in ("prds", "consumers")}
            if cr.get("id") != orw.get("id"):
                why.append(f"row {cn}: id {cr.get('id')!r} is not original row {on}'s {orw.get('id')!r}")
            elif keep(cr) != keep(orw):
                diff = sorted(k for k in set(keep(cr)) | set(keep(orw)) if cr.get(k) != orw.get(k))
                why.append(f"row {cn} ({cr.get('id')}): changes {', '.join(diff)}; only prds and consumers may change")
        if why:
            L.fail("sidecar-correction-unbound", f"{shown}: {'; '.join(why)}")
        else:
            best = (shown, body)
    return best


def chain_review(L, mrec, mans, chain, rows, governed, task, adv, states, reviews, home, resolve):
    """PRD-dream-mission-chain-review R1-R4, R5 (mission pin), R6 and the R8 JSON fields for
    an entry whose Mission: line carries (or inherits) scope=. Returns the mission JSON fields
    and the dependent map {PRD basename: [reasons]}."""
    hd = mrec["header"]
    eb = os.path.basename(mrec["edges"]) if mrec["edges"] else None
    mxb = os.path.basename(adv[1]) if adv and adv[0] == "matrix" else None
    last = len(mans) - 1
    seen = set()

    def once(fid, detail):
        if detail not in seen:
            seen.add(detail)
            L.fail(fid, detail)

    # R1 per manifest: its frozen edges copy, completeness against that header (the last also
    # against the live header) and contract basenames
    for k, m in enumerate(mans):
        if m["id"] is None:
            continue
        copy, _, err = frozen_edges_copy(m["full"], eb)
        if err:
            once("mission-scope-mismatch", f"manifest {m['path']}: {err}")
        else:
            fh, fe, fpr = read_edges(copy, copy)
            if fh is None:
                once("mission-scope-mismatch", f"manifest {m['path']}: frozen edges copy {copy} has no header")
            for fid, d in fpr:      # matrix-per-manifest R1 on a frozen header (its other fields stay unread here)
                if fid == "edge-grammar" and ": field matrix: " in d:
                    once("edge-grammar", f"manifest {m['path']}: {d}")
            m["frozen"], m["frozen_edges"] = fh, fe
        mxm, mxl, mslugs = manifest_matrix(m, mrec, adv, states, resolve)
        m["matrix"] = mxm
        heads = ([("frozen", m["frozen"])] if m["frozen"] else []) + ([("live", hd)] if k == last and hd else [])
        for hi, (label, h) in enumerate(heads):
            cons = header_contracts(h)
            byb = {}
            for nm, cp in cons:
                byb.setdefault(os.path.basename(cp), []).append(cp)
            for b, cps in byb.items():
                if len(set(cps)) > 1:
                    once("mission-scope-mismatch", f"manifest {m['path']}: {label} edges header: contract paths "
                                                   f"{' and '.join(sorted(set(cps)))} share the basename {b}")
                if b in h["prds"] or b in h["packet"]:
                    once("mission-scope-mismatch", f"manifest {m['path']}: {label} edges header: contract path "
                                                   f"{cps[0]} and the member {b} share the basename {b}")
            need = [(b, "prds member") for b in h["prds"]] + [(b, "packet member") for b in h["packet"]]
            need += ([(mxm, None)] if mxm and hi == 0 else []) + ([(eb, "edges file")] if eb else [])
            need += [(os.path.basename(cp), f"external {nm} contract copy") for nm, cp in cons]
            for b, kind in need:
                if b not in m["names"]:
                    once("mission-scope-incomplete", f"manifest {m['path']}: lists no {b} ({mxl})" if kind is None else
                         f"manifest {m['path']}: lists no {b} ({kind} of the {label} edges header)")
        # generation-aware R4: header members (the repairs file among them) are keyed by basename,
        # so one may occur once per manifest
        mem = {b for b in (mxm, eb, os.path.basename(mrec["repairs"]) if mrec.get("repairs") else None) if b}
        for _, h in heads:
            mem |= set(h["prds"]) | set(h["packet"]) | {os.path.basename(cp) for _, cp in header_contracts(h)}
            mem |= {h["matrix"]} if h.get("matrix") else set()
        m["members"] = mem
        byb = {}
        for raw, key, base, _ in m.get("entries") or []:
            if base in mem:
                byb.setdefault(base, {}).setdefault(key, raw)
        for b, ks in sorted(byb.items()):
            if len(ks) > 1:
                once("mission-scope-mismatch", f"manifest {m['path']}: header member {b} occurs {len(ks)} times "
                                               f"({', '.join(sorted(ks.values()))}); a header member is keyed by basename")
        # matrix-per-manifest R3: the last manifest's frozen header, and the live header, name the
        # note's adversarial= matrix
        for label, h in (heads if k == last else []):
            if h.get("matrix") and h["matrix"] != mxb:
                where = f"manifest {m['path']}: frozen edges header" if label == "frozen" else f"{mrec['edges']}: live edges header"
                once("mission-scope-mismatch", f"{where} names matrix {h['matrix']}; the note's adversarial= names "
                                               f"{mxb or 'no matrix (adversarial=skipped:)'}")
        # matrix-per-manifest R5b: the matrix a header names is the copy beside the manifest, at its
        # listed digest, and passes the matrix grammar for the first-listing entry's State slugs
        # that are prds members of this header (a legacy header keeps the basename-only check)
        fhd = m["frozen"]
        if fhd and fhd.get("matrix") and mxm in m["names"]:
            cp = os.path.join(os.path.dirname(m["full"]), mxm)
            got = file_sha(cp)
            if got is None:
                once("adversarial-missing", f"manifest {m['path']}: matrix copy {cp} absent or unreadable "
                                            f"(the frozen edges header names {mxm})")
            elif got != m["names"][mxm]:
                once("adversarial-missing", f"manifest {m['path']}: matrix copy {cp} sha256 {got[:12]} differs from "
                                            f"the manifest's {m['names'][mxm][:12]}")
            else:
                sub = Lint()
                sl = [s for s in dict.fromkeys(mslugs) if f"PRD-{s}.md" in fhd["prds"]]
                lint_matrix(sub, cp, cp, sl)
                for fid, d in sub.findings:
                    once(fid, f"manifest {m['path']}: {d}")
    # generation-aware R4 (Q1): one key at two digests in one manifest, or one manifest listing a
    # basename for a file in each directory of a compared pair, is mission-scope-mismatch
    for k, m in enumerate(mans):
        if m["id"] is None:
            continue
        mdir = os.path.dirname(m["full"])
        for key, ds in sorted(key_collisions(m, m.get("members", set()))[0].items()):
            once("mission-scope-mismatch", f"manifest {m['path']}: {os.path.relpath(key, mdir)} is listed at "
                                           f"{len(ds)} digests ({', '.join(ds)}); one key names one file")
        if k + 1 < len(mans) and mans[k + 1]["id"] is not None:
            o = mans[k + 1]
            mem = m.get("members", set()) | o.get("members", set())
            pdirs = {os.path.normpath(os.path.dirname(m["full"])), os.path.normpath(os.path.dirname(o["full"]))}
            for x, y in ((m, o), (o, m)):
                xdir = os.path.dirname(x["full"])
                for b, kd in sorted(key_collisions(x, mem, pdirs)[1].items()):
                    once("mission-scope-mismatch", f"manifest {x['path']}: {b} is listed for two files, one in each "
                                                   f"directory of the pair with {y['path']}: "
                                                   f"{' and '.join(f'{os.path.relpath(kk, xdir)} at {d}' for kk, d in kd)}; "
                                                   "an entry there is keyed by its basename")
                for b, kd in sorted(member_twins(x, mem - x.get("members", set())).items()):
                    once("mission-scope-mismatch", f"manifest {x['path']}: {b} is a header member of {y['path']}, the "
                                                   f"other manifest of the pair, and is listed here for "
                                                   f"{len({kk for kk, _ in kd})} files: "
                                                   f"{' and '.join(f'{os.path.relpath(kk, xdir)} at {d}' for kk, d in kd)}; "
                                                   "a header member is keyed by its basename, so one name names one file")
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
    findings_hist = []      # Repair 2: an original sidecar's failures a corrected sidecar answers (never dropped);
                            # Repair 4: a consumer the next freeze declares
    rep_rows = repairs_rows(mrec, resolve)
    admitted = ({r.get("session") for r in rows or [] if r.get("decision") == "launch" and r.get("skill") == "dream"
                 and r.get("task_id") == task and r.get("role", "author") == "author"} if governed else None)
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
        rows_sc = sidecar_rows(read) if read is not None else []
        if fv in ("FIX", "REJECT") and not rows_sc and (read is not None or sbytes is None):
            L.fail("mission-finding-incomplete", f"{sc}: absent, unreadable or empty under mission={fv}")
        fh = mans[c["idx"]]["frozen"] or hd
        prset = set(fh["prds"]) if fh else set()
        exts = set(fh["external_names"]) if fh else set()
        late = late_declared(mans, c["idx"], exts, eb, rep_rows, admitted, c["rv"]["session"], resolve)
        # producer-contract Repair 2 (A1723 decision 3): a corrected sidecar written by this review's own session,
        # resumed, may change prds and consumers; it is read for finding grammar and the sweep, the original's failures
        # are kept as findings_historical, and findings= still binds the original bytes
        corr = corrected_sidecar(L, c, f, resolve(c["rv"]["file"]), sbytes, rows_sc, rows, task) \
            if read is not None and sbytes is not None else None
        if corr is not None:
            c["sidecar_corrected"] = corr[0]
            sc_rows(c, rows_sc, sc, prset, exts, ids_seen, lambda fid_, d: findings_hist.append(
                {"id": fid_, "detail": d, "corrected_by": corr[0]}), False)
            sc_rows(c, corr[1], corr[0], prset, exts, ids_seen, L.fail, True, late, findings_hist.append)
        else:
            sc_rows(c, rows_sc, sc, prset, exts, ids_seen, L.fail, True, late, findings_hist.append)
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
                                 "launch_ts": c["row"].get("ts"), "sidecar_bound": c["sidecar_bound"],
                                 **({"sidecar_corrected": c["sidecar_corrected"]} if c.get("sidecar_corrected") else {})}
                                for c in chain],
              "verdict": verdict, "findings": len(vr["findings"]) if vr else 0,
              "unlisted_review_sessions": unlisted}
    if findings_hist:
        fields["findings_historical"] = findings_hist
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
             "repair-scope-mismatch", "affected-consumer-unreviewed", "repair-declined-unaccepted",
             "repair-consolidation-mismatch")
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

    def moved():
        for k in range(len(mans) - 1):
            a, b = mans[k], mans[k + 1]
            if a["id"] is not None and b["id"] is not None:
                if any(n in b["names"] and b["names"][n] != dg for n, dg in a["names"].items() if n != rbase):
                    return True
                pa = {key: dg for raw, key, _, dg in a.get("entries") or [] if "/" in raw}
                if any(key in pa and pa[key] != dg for raw, key, _, dg in b.get("entries") or [] if "/" in raw):
                    return True
        return False
    if not tok and not need and not moved():
        return None
    out = {"file": tok, "rows": 0, "repaired": 0, "declined": [], "amended": [], "pending_after": False,
           "changed": [], "swept_edges": 0, "edges_added": [], "edges_removed": []}
    hist = []               # Repair 3: duplicates a consolidation row answers (JSON repairs_historical; never dropped)
    if not tok and need:                 # R2 (r4 F27): the check never waits for the token
        for p, f in need:
            L.fail("repair-missing", f"finding {f['id']} of {chain[p]['rv']['file']}: no repairs= token on the "
                                     "Mission: line (carried or inherited)")
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
                L.fail("repair-grammar", f"{tok}: row {n}: not a JSON object")
                continue
            ok = True

            def bad(field, why, n=n):
                L.fail("repair-grammar", f"{tok}: row {n}: field {field}: {why}")
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
            delta = None
            if "delta" in r:                # generation-aware R4: the path records of a row, and its path
                delta, why = parse_delta(r["delta"])     # lists (a row without delta keeps 43d5b39, which
                if why:                                  # read neither added nor removed)
                    bad("delta", why)
                    ok = False
                for k in ("added", "removed"):
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
                                                 "row (a repair that changes no bytes is declined with a reason)")
                        ok = False
                    elif not {os.path.basename(c) for c in ch} & allowed:
                        L.fail("repair-grammar", f"{tok}: row {n}: finding {fid}: changed names none of "
                                                 f"{', '.join(sorted(allowed))} (the PRDs and contract the finding names)")
                        ok = False
            recs.append({"n": n, "r": r, "ok": ok, "fid": fid if isinstance(fid, str) else None, "disp": disp,
                         "bi": man_index(r.get("before")), "ai": man_index(r.get("after")),
                         "changed": [x for x in r.get("changed") or [] if isinstance(x, str)] if isinstance(r.get("changed"), list) else [],
                         "sweep": [x for x in r.get("sweep") or [] if isinstance(x, str)] if isinstance(r.get("sweep"), list) else [],
                         "added": [x for x in r.get("added") or [] if isinstance(x, str)] if isinstance(r.get("added"), list) else [],
                         "removed": [x for x in r.get("removed") or [] if isinstance(x, str)] if isinstance(r.get("removed"), list) else [],
                         "delta": delta})
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
                                       "one row, or one declined row followed by one repaired row")
    # producer-contract Repair 3 (A1723 addendum 1): a later amended row may consolidate earlier amended rows of its
    # manifest pair; the duplicate check then judges it in their place, and their duplicates become historical
    cons_of = {}
    for x in recs:
        if "consolidates" not in x["r"]:
            continue
        lst, why = x["r"]["consolidates"], []
        pair = (x["r"].get("before"), x["r"].get("after"))
        listed = []
        if x["disp"] != "amended":
            why.append("only an amended row consolidates")
        if not (isinstance(lst, list) and lst and all(isinstance(v, int) and not isinstance(v, bool) for v in lst)):
            why.append("consolidates is not a non-empty list of row numbers")
        else:
            byn = {y["n"]: y for y in recs}
            for v in lst:
                y = byn.get(v)
                if y is None or v >= x["n"]:
                    why.append(f"row {v} is no earlier row of this file")
                    continue
                listed.append(y)
                if y["disp"] != "amended" or (y["r"].get("before"), y["r"].get("after")) != pair:
                    why.append(f"row {v} is not an amended row of ({pair[0]}, {pair[1]})")
                if y["r"].get("author_session") != x["r"].get("author_session"):
                    why.append(f"row {v}'s author_session {y['r'].get('author_session')} is not this row's")
                if v in cons_of:
                    why.append(f"row {v} is consolidated by row {cons_of[v]['n']} already")
            for k in ("changed", "sweep"):
                want = sorted(set().union(*(set(y[k]) for y in listed))) if listed else []
                if sorted(set(x[k])) != want:
                    why.append(f"{k} {sorted(set(x[k]))} is not the union of the listed rows' {k} {want}")
        if why:
            L.fail("repair-consolidation-mismatch", f"row {x['n']}: consolidates {lst}: {'; '.join(why)}")
        else:
            for y in listed:
                cons_of[y["n"]] = x
    ams = [x for x in recs if x["disp"] == "amended"]
    for i, x in enumerate(ams):
        for y in ams[i + 1:]:
            if (x["r"].get("before"), x["r"].get("after")) == (y["r"].get("before"), y["r"].get("after")):
                if cons_of.get(x["n"]) is y or cons_of.get(y["n"]) is x:
                    continue                # a consolidation row and a row it lists
                for b in sorted(set(x["changed"]) & set(y["changed"])):
                    d = f"amended rows {x['n']} and {y['n']} of ({x['r'].get('before')}, {x['r'].get('after')}) both name {b}"
                    if x["n"] in cons_of or y["n"] in cons_of:
                        hist.append({"id": "repair-duplicate", "detail": d,
                                     "consolidated_by": sorted({cons_of[v]["n"] for v in (x["n"], y["n"]) if v in cons_of})})
                    else:
                        L.fail("repair-duplicate", d)
    sup = {fid for fid, xs in byf.items() if [x["disp"] for x in xs] == ["declined", "repaired"]}
    # R1: the repairs file is listed in every manifest later than any row's before
    bis = [x["bi"] for x in recs if x["bi"] is not None]
    if tok and bis:
        for k in range(min(bis) + 1, len(mans)):
            if mans[k]["id"] is not None and rbase not in mans[k]["names"]:
                L.fail("mission-scope-incomplete", f"manifest {mans[k]['path']}: lists no {rbase} (the repairs file; "
                                                   f"a row's before is {mans[min(bis)]['path']})")
    # R2: rows required, declines accepted
    named = {x["fid"] for x in recs if x["fid"] is not None}     # a malformed row still names its finding
    for p, f in need:
        if f["id"] not in named:
            L.fail("repair-missing", f"finding {f['id']} of {chain[p]['rv']['file']}: no row in {tok} "
                                     f"(its following review {chain[p + 1]['rv']['file']} exists)")
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
            L.fail("repair-hash-mismatch", f"row {x['n']}: {field} {p}: {c}")
            return None
        return c[0], {k.decode("utf-8", "backslashreplace"): v for k, v in c[1].items()}
    pmap = {}

    def paths_of(x, field):
        """R4: the [(path, key, basename, digest)] entries of the row's before or after manifest."""
        k = x["bi"] if field == "before" else x["ai"]
        if k is not None:
            return mans[k].get("entries") or []
        p = x["r"].get(field)
        if p not in pmap:
            pmap[p] = manifest_paths(resolve(p)) or []
        return pmap[p]
    amb = []

    def short(d):
        return d[:12] if isinstance(d, str) else "none"

    def bare_ambiguous(x, field, b, sides):
        """R4: True when the bare basename b names several entries of a manifest the field reads;
        a legacy row lists it in repairs.ambiguous (never failed), a delta row is repair-grammar."""
        for side in sides:
            keys = {}
            for raw, key, base, _ in paths_of(x, side):
                if base == b:
                    keys.setdefault(key, raw)
            if len(keys) > 1:
                cands = sorted(keys.values())
                if x["delta"] is None:
                    amb.append({"row": x["n"], "field": field, "name": b, "manifest": x["r"].get(side), "paths": cands})
                else:
                    L.fail("repair-grammar", f"{tok}: row {x['n']}: {field} {b}: a bare basename that {len(cands)} entries "
                                             f"of {x['r'].get(side)} hold ({', '.join(cands)}); a row with delta names the path")
                return True
        return False

    def path_entry(x, field, p, memb):
        """R4: a path entry (it holds /) against its delta record and both manifests. A header member
        (memb) is keyed by its basename in every pass, so its digests are looked up by basename (one
        per manifest); a record matches the entry by resolved key, whatever its spelling."""
        n, r, dl = x["n"], x["r"], x["delta"]
        side = "before" if field == "removed" else "after"
        key, base = entry_key(resolve(r[side]), p), os.path.basename(p)

        def look(s):
            return next((dg for _, k, b_, dg in paths_of(x, s) if (b_ == base if base in memb else k == key)), None)
        bd, ad = look("before"), look("after")
        if dl is None:
            L.fail("repair-hash-mismatch", f"row {n}: {field} {p}: a path entry needs its delta record (the row carries "
                                           f"no delta); {r['before']} holds {short(bd)}, {r['after']} holds {short(ad)}")
            return
        kind = field
        rec = next((d for d in dl.get(field, []) if entry_key(resolve(r[side]), d["path"]) == key), None)
        if rec is None and field == "changed":      # a changed path whose record sits under delta.added
            rec = next((d for d in dl.get("added", []) if entry_key(resolve(r[side]), d["path"]) == key), None)
            kind = "added" if rec is not None else kind
        if rec is None:
            L.fail("repair-hash-mismatch", f"row {n}: {field} {p}: no delta.{field} record; {r['before']} holds "
                                           f"{short(bd)}, {r['after']} holds {short(ad)}")
            return
        if kind == "changed":
            want = (rec["before"], rec["after"])
            good = bd is not None and ad is not None and (bd, ad) == want and bd != ad
            what = f"delta before {short(want[0])} after {short(want[1])}"
        elif kind == "added":
            good, what = bd is None and ad == rec["sha256"], f"delta added {short(rec['sha256'])}"
        else:
            good, what = ad is None and bd == rec["sha256"], f"delta removed {short(rec['sha256'])}"
        if not good:
            L.fail("repair-hash-mismatch", f"row {n}: {field} {p}: {what}; {r['before']} holds {short(bd)}, "
                                           f"{r['after']} holds {short(ad)}")
    added, removed, swept, aff_of = set(), set(), set(), {}
    for x in recs:
        r, n, fid = x["r"], x["n"], x["fid"]
        swept |= set(x["sweep"])
        a_s = r.get("author_session")      # each check reads only its own fields (refusals stay independent)
        if isinstance(a_s, str) and a_s.strip() and a_s not in admitted:
            L.fail("repair-author-mismatch", f"row {n}: author_session {a_s} is not an author of Task {task} "
                                             f"(admitted: {', '.join(sorted(s for s in admitted if s)) or 'none'})")
        bi, ai = x["bi"], x["ai"]
        bcopy = mans[bi]["frozen_edges"] if bi is not None else []
        bhead = (mans[bi]["frozen"] if bi is not None else None) or hd
        bprds = set(bhead["prds"]) if bhead else prds
        # R3: class and sweep (affected graph at the before digest)
        if x["disp"] == "amended":
            aff, cls = {os.path.basename(b) for b in x["changed"]} & bprds, None
        elif fid in fobj and x["disp"] in ("repaired", "declined"):
            f = fobj[fid]
            aff, cls = set(names_of(f)), r.get("class")
            if cls != f.get("class"):
                L.fail("repair-class-mismatch", f"finding {fid}: row {n} class {cls}, the finding's {f.get('class')}")
        else:
            aff, cls = None, None
        if aff is not None and cls != "provenance" and bi is not None:
            want = [e["id"] for e in bcopy if e["producer"] in aff or e["consumer"] in aff]
            miss = [e for e in want if e not in x["sweep"]]
            if miss:
                L.fail("sweep-missing", f"{'finding ' + fid if fid else 'amended row'} (row {n}): sweep lacks "
                                        f"{', '.join(miss)} (incident to {', '.join(sorted(aff))})")
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
            L.fail("repair-scope-mismatch", f"row {n}: before {r['before']} is not a listed scope= manifest")
        elif anchor is not None and cb is not None:
            iss = chain[anchor]
            okids = ([ids[c["idx"]] for c in chain[anchor + 1:]] if x["disp"] == "repaired" and fid in sup
                     else [ids[iss["idx"]]])
            # producer-contract Repair 1 (A1723 decision 3): a repaired row's before may be a later listed manifest B when no
            # chain review is bound to a manifest in (issuer, B] and each of those is the after of some repairs row
            late = x["disp"] == "repaired" and cb[0] not in okids and bi > iss["idx"]
            between = range(iss["idx"] + 1, bi + 1) if late else range(0)
            reviewed = [cc for cc in chain if iss["idx"] < cc["idx"] <= bi] if late else []
            undeclared = [j for j in between if not any(y["ai"] == j for y in recs)]
            if cb[0] in okids or (late and not reviewed and not undeclared):
                pass
            elif late and not reviewed:
                L.fail("repair-scope-mismatch", f"row {n} (finding {fid}): before {r['before']} is later than the issuing "
                                                f"review's manifest ({ids[iss['idx']]}, {iss['rv']['file']}); "
                                                f"{', '.join(mans[j]['path'] for j in undeclared)} between them "
                                                "is the after of no repairs row")
            else:
                L.fail("repair-scope-mismatch", f"row {n} (finding {fid}): before {r['before']} canonicalizes to {cb[0]}; "
                                                f"the issuing review {iss['rv']['file']} is bound to {ids[iss['idx']]}")
        same_ok = x["disp"] == "declined" and ai is not None and ai == bi and fol is not None and fol["idx"] == ai
        if bi is not None and (ai is None or not (ai == bi + 1 or same_ok)):
            L.fail("repair-scope-mismatch", f"row {n}: after {r['after']} is not the listed scope= manifest following "
                                            f"before {r['before']}")
        elif fol is None:
            out["pending_after"] = True
        elif ai is not None and fol["idx"] < ai:
            L.fail("repair-scope-mismatch", f"row {n}: its following review {fol['rv']['file']} is bound to "
                                            f"{ids[fol['idx']]}, earlier than after {r['after']} ({ids[ai]})")
        if cb is not None and ca is not None and not (same_ok and not x["changed"]):
            mxo = mans[bi].get("matrix") if bi is not None else None
            mxn = mans[ai].get("matrix") if ai is not None else None
            memb = set().union(*(mans[i].get("members", set()) for i in (bi, ai) if i is not None))
            for b in x["changed"]:
                if "/" in b:                    # generation-aware R4: a path entry, relative to after's directory;
                    if x["delta"] is not None or os.path.basename(b) not in memb:
                        path_entry(x, "changed", b, memb)
                        continue
                    b = os.path.basename(b)     # a header member, keyed by basename in every pass: a row
                                                # without delta names it as installed
                if bare_ambiguous(x, "changed", b, ("before", "after")):
                    continue
                if mxo != mxn and b in (mxo, mxn):     # matrix-per-manifest R4: old against before, new against after
                    if b == mxo and b not in cb[1]:
                        L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from before {r['before']}")
                    elif b == mxn and b not in ca[1]:
                        L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from after {r['after']}")
                    continue
                if b not in cb[1]:
                    L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from before {r['before']}")
                elif b not in ca[1]:
                    L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, absent from after {r['after']}")
                elif cb[1][b] == ca[1][b]:
                    L.fail("repair-hash-mismatch", f"row {n}: {b}: claimed changed, digests equal in {r['before']} "
                                                   f"and {r['after']}")
            for field, sides in (("added", ("after", "before")), ("removed", ("before", "after"))):
                for b in x[field]:          # generation-aware R4: a path entry against its record; a bare
                    if "/" in b and (x["delta"] is not None or os.path.basename(b) not in memb):
                        path_entry(x, field, b, memb)       # name (or a header member a row without delta
                    else:                                   # names) is read only for ambiguity: 43d5b39
                        bare_ambiguous(x, field, os.path.basename(b), sides)   # read neither field
        # R6: affected consumers in a later review's manifest (once the following review exists)
        cons = [(b, e["consumer"], e["id"]) for b in x["changed"] for e in bcopy
                if e["producer"] == os.path.basename(b) and e["consumer"] in bprds]
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
                        dg = {k.decode("utf-8", "backslashreplace"): v
                              for k, v in scope_digests(resolve, rv["row"].get("scope"), rv["row"]).items()}
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
        mem = a.get("members", set()) | b.get("members", set())
        bdir = os.path.normpath(os.path.dirname(b["full"]))
        pdirs = {os.path.normpath(os.path.dirname(a["full"])), bdir}
        ab, ap = split_keys(a, mem, pdirs)
        bb, bp = split_keys(b, mem, pdirs)
        (a2, at2), (b2, bt2) = key_collisions(a, mem, pdirs), key_collisions(b, mem, pdirs)
        cold = set(at2) | set(bt2) | {os.path.basename(x) for x in set(a2) | set(b2)
                                      if os.path.dirname(x) in pdirs or os.path.basename(x) in mem}
        cold |= set(member_twins(a, mem - a.get("members", set()))) | set(member_twins(b, mem - b.get("members", set())))
        colk = set(a2) | set(b2)
        decl, decl_m, decl_p, legacy_bare = set(), set(), set(), set()
        for x in recs:
            if x["bi"] == k and x["ai"] == k + 1:
                for c in x["changed"]:
                    if "/" in c:                    # generation-aware R4: a path declares its key; its
                        key = entry_key(b["full"], c)    # basename declares a header member of that name
                        decl_p.add(key)
                        decl_m.add(os.path.basename(c))
                        if os.path.dirname(key) in pdirs:
                            decl.add(os.path.basename(c))
                    else:
                        decl.add(c)
                        if x["delta"] is None:      # a legacy row's bare name declares every path of it
                            legacy_bare.add(c)
        mxr = {a.get("matrix"), b.get("matrix")} - {None} if a.get("matrix") != b.get("matrix") else set()
        for nm in sorted(set(ab) & set(bb) - cold):
            if nm != rbase and nm not in mxr and ab[nm] != bb[nm] and nm not in decl and not (nm in mem and nm in decl_m):
                L.fail("repair-hash-mismatch", f"{nm}: changed but undeclared between {a['path']} and {b['path']}")
        for key in sorted(set(ap) & set(bp) - colk):
            if ap[key] != bp[key] and key not in decl_p and os.path.basename(key) not in legacy_bare:
                L.fail("repair-hash-mismatch", f"{os.path.relpath(key, bdir)}: changed but undeclared between "
                                               f"{a['path']} and {b['path']}")
        # the repairs file is exempt only for a pair whose rows it holds (writing them is what moves it)
        if rbase in a["names"] and rbase in b["names"] and a["names"][rbase] != b["names"][rbase] \
                and not any(x["bi"] == k and x["ai"] == k + 1 for x in recs):
            L.fail("repair-hash-mismatch", f"{rbase}: changed but undeclared between {a['path']} and {b['path']} "
                                           "(no row names this pair; the repairs file is exempt only for a pair whose rows it holds)")
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
                for b in {os.path.basename(c) for c in x["changed"]} | aff_of.get(x["n"], set()):
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
    if amb:
        out["ambiguous"] = amb
    if hist:
        out["historical"] = hist
    return out


HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


def parse_delta(v):
    """generation-aware R4: (the delta object, None) or (an empty one, why it is malformed). The shape
    is {changed: [{path, before, after}], added: [{path, sha256}], removed: [{path, sha256}]}, each
    list optional, paths non-empty strings, digests 64 lowercase hex."""
    empty = {"changed": [], "added": [], "removed": []}
    if not isinstance(v, dict):
        return empty, "not an object"
    extra = sorted(set(v) - set(empty))
    if extra:
        return empty, f"unknown key {extra[0]}"
    out = {}
    for k, fields in (("changed", ("before", "after")), ("added", ("sha256",)), ("removed", ("sha256",))):
        lst = v.get(k, [])
        if not isinstance(lst, list):
            return empty, f"{k} is not a list"
        for i, d in enumerate(lst):
            if not (isinstance(d, dict) and isinstance(d.get("path"), str) and d["path"].strip()):
                return empty, f"{k}[{i}]: no path"
            for f in fields:
                if not (isinstance(d.get(f), str) and HEX64_RE.fullmatch(d[f])):
                    return empty, f"{k}[{i}] {d['path']}: {f} is not a sha256"
        out[k] = lst
    return out, None


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
         "edges": None, "prds": None, "consumption": None, "task": None, "page": None, "prd_home": None, "reviews": None,
         "require_closed": False, "scope_roots": None}
    i = 0
    while i < len(argv):
        x = argv[i]
        if x == "--json":
            a["json"] = True
        elif x == "--last":
            a["mode"] = "last"
        elif x == "--selftest":
            a["selftest"] = True
        elif x == "--require-closed":
            a["require_closed"] = True
        elif x in ("--consumption", "--task", "--page", "--prd-home", "--reviews"):
            if i + 1 >= len(argv):
                usage(f"{x} needs a value")
            a[x[2:].replace("-", "_")] = argv[i + 1]
            i += 1
        elif x in ("--entry", "--prd-dir", "--decisions", "--matrix", "--scope-id", "--edges"):
            if i + 1 >= len(argv):
                usage(f"{x} needs a value")
            key = {"--entry": "entry", "--prd-dir": "prd_dir", "--decisions": "decisions", "--matrix": "matrix",
                   "--scope-id": "scope_id", "--edges": "edges"}[x]
            a[key] = argv[i + 1]
            if x == "--entry":
                a["mode"] = "entry"
            i += 1
        elif x == "--scope-root":
            if i + 1 >= len(argv):
                usage(f"{x} needs a value")
            a["scope_roots"] = (a["scope_roots"] or []) + [argv[i + 1]]
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


def parse_analysis(s, extended=False):
    """Return dict with keys wwhtbt, fivewhys, adversarial -> (kind, value, extra) or None
    per part, plus a list of grammar problems. `extended` (an entry on or after TRIGGER_CUTOVER) also reads
    `wwhtbt=reused <page> sha256=<64 hex> inputs=<manifest>` and `5whys=reused <page> sha256=<64 hex>` (trigger-record R3, R5)."""
    probs = []
    out = {"wwhtbt": None, "fivewhys": None, "adversarial": None}
    m = re.match(r"^Analysis:\s+wwhtbt=(.*?)\s+5whys=(.*?)\s+adversarial=(.*)$", s.rstrip())
    if not m:
        return out, ["Analysis line is not 'wwhtbt=... 5whys=... adversarial=...'"]
    w, f, adv = (x.strip() for x in m.groups())
    mm = re.match(r"^(ran|reused)\s+(\S+)$", w)
    mr = re.match(r"^reused\s+(\S+)\s+sha256=([0-9a-f]{64})\s+inputs=(\S+)$", w) if extended else None
    if mr:
        out["wwhtbt"] = ("reused", mr.group(1), {"sha256": mr.group(2), "inputs": mr.group(3), "raw": w})
    elif mm:
        out["wwhtbt"] = (mm.group(1), mm.group(2))
    elif re.match(r"^skipped:\s*\S", w):
        out["wwhtbt"] = ("skipped", re.sub(r"^skipped:\s*", "", w))
    else:
        probs.append(f"wwhtbt value '{w}'")
    mm = re.match(r"^page\s+(\S+)$", f)
    mr = re.match(r"^reused\s+(\S+)\s+sha256=([0-9a-f]{64})$", f) if extended else None
    if mr:
        out["fivewhys"] = ("reused", mr.group(1), {"sha256": mr.group(2), "raw": f})
    elif mm:
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


# ---------------------------------------------------------------- trigger record (PRD-dream-analysis-trigger-record, A1723)
# Applies to entries whose header timestamp is at or after the cutover instant (R7, after_cutover). A covered entry (R1) records a WWHTBT it ran, an
# exact reuse (R3) or a skip bound to a recorded route denial (R2), and a typed Failure: line (R4) whose trigger classes need a bound 5whysandrhyme
# page (R5).
def header_date(ts):
    """R7: the ISO date (YYYY-MM-DD, zero-padded) an entry header starts with, or None when it starts with no valid such date followed by the end, `T` or
    a space (such a header counts as after the cutover; targeted review abb2e978 H1)."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?=$|[T ])", ts or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return None


def after_cutover(ts, row_ts=False):
    """R7 (A1723 source request 4, Q3): a header timestamp, or a bound Route row's `ts` (row_ts), is at or after the cutover instant,
    `<TRIGGER_CUTOVER>T00:00:00-08:00`. One carrying an offset (any zone, `Z` included) is compared as an instant, so one instant written in two
    zones falls on one side; one without a readable offset keeps the date-text comparison (a header with no readable leading date counts as after)."""
    t = parse_iso(re.sub(r"z$", "Z", ts)) if isinstance(ts, str) else None     # RFC 3339 allows a lower-case z (review r20 F2)
    if t is not None:
        return t >= parse_iso(TRIGGER_CUTOVER + "T00:00:00-08:00")
    if row_ts:
        return str(ts)[:10] >= TRIGGER_CUTOVER
    d = header_date(ts)
    return d is None or d >= TRIGGER_CUTOVER


def entry_seed_tokens(e):
    """R1: the tokens of one entry's last Seeds: line; `file:<path> sha256=<hex>` (a file seed) is one token."""
    s = None
    for ln in (e or {}).get("lines", []):
        if ln.startswith("Seeds:"):
            s = ln
    if s is None:
        return []
    toks, out, i = s[len("Seeds:"):].split(), [], 0
    while i < len(toks):
        t = toks[i]
        if t.startswith("file:") and i + 1 < len(toks) and re.fullmatch(r"sha256=[0-9a-f]{64}", toks[i + 1]):
            t, i = t + " " + toks[i + 1], i + 1
        out.append(t)
        i += 1
    return out


def newest_review_snapshot(same, task, rows, resolve):
    """R1: the newest manifest an earlier entry of the Task binds through a reviewer's snapshot (the `scope` of the review launch row its Review: line
    names), in log order. -> (path, {basename: digest}) or None. (A Mission: line's scope= manifest needs no lookup: such an entry is covered as a mission.)"""
    found = None
    for e in same:
        for ln in e["lines"]:
            m = re.match(r"^Review:\s+\S+\s+reviewer-session=(\S+)", ln)
            if not m:
                continue
            m4 = [r for r in rows or [] if r.get("session") == m.group(1) and r.get("decision") == "launch" and r.get("skill") == "dream"
                  and r.get("task_id") == task and r.get("role") == "review"]
            if m4 and isinstance(m4[-1].get("scope"), str) and m4[-1]["scope"]:
                found = m4[-1]
    if found is None:
        return None
    try:          # fail closed: an unreadable snapshot, or one whose canonical id is not the row's scope_id, is no proof of unchanged bytes (security ddf46516 finding 4)
        sid, digests = scope_canon(scope_file(resolve, found["scope"], found)[0])
    except ScopeError:
        return found["scope"], None
    return (found["scope"], digests) if found.get("scope_id") == sid else (found["scope"], None)   # a row without scope_id proves nothing (abb2e978 L1)


def covered_kind(entries, ei, task, states, mrec, rows, home, resolve):
    """R1 -> ("mission" | "new-material" | "none", why). None of the triggers is the author's free claim."""
    if mrec is not None:
        return "mission", "it carries or inherits a Mission: line"
    same = [e for e in entries[:ei] if entry_task(e) == task]
    seen = {s for e in same for s in entry_state_slugs(e)}
    for slug, vals in states.items():
        if slug not in seen:
            return "new-material", f"State: names {slug}, which no earlier entry of Task {task} names"
        if "drafted" in vals:
            return "new-material", f"State: carries {slug}=drafted"
    prev = entry_seed_tokens(same[-1]) if same else []
    new = [t for t in entry_seed_tokens(entries[ei]) if t not in prev]
    if new:
        return "new-material", f"Seeds: carries {new[0]}, which Task {task}'s previous entry did not"
    snap = newest_review_snapshot(same, task, rows, resolve)
    if snap is not None and snap[1] is None:
        return "new-material", f"the review snapshot {snap[0]} an earlier entry of Task {task} binds is unreadable or is not its review row's scope_id"
    if snap is not None:
        for slug in states:
            want = snap[1].get(f"PRD-{slug}.md".encode())
            cur = next((os.path.join(home, d, f"PRD-{slug}.md") for d in PRD_DIRS if os.path.isfile(os.path.join(home, d, f"PRD-{slug}.md"))), None)
            if want and cur and file_sha(cur) != want:
                return "new-material", f"PRD-{slug}.md differs from its digest in {snap[0]}, the newest manifest an earlier entry of Task {task} binds"
    return "none", None


def outage_reason(reasons, skill):
    """R2 (amended, Hermes H2): a route outage in the resolver's own words, the whole reason: `policy file not found`, `policy is malformed`,
    `malformed policy JSON: <Error>`, `ledger lookup unavailable; cannot verify ledger:<id> (fail closed)`, `<skill>: policy require_permission_mode
    must be a non-empty string (fail closed)`, or the policy-error form `<skill>: policy ... (policy error, fail closed)`, <skill> being the denied
    row's. The infix elsewhere in a reason can be caller text the resolver quotes (`unknown decision_class '...'`), a request the caller can fix
    (security review ddf46516 findings 1-2); the two `policy-missing:` texts name a policy file the caller chose."""
    r = reasons if isinstance(reasons, str) else ""          # whole: the resolver writes no surrounding white space (review r10 LOW-1)
    if r in OUTAGE_TEXTS or any(p.fullmatch(r) for p in OUTAGE_RES):
        return True
    if r == skill + ": policy require_permission_mode must be a non-empty string (fail closed)":
        return True
    return r.startswith(skill + ": policy ") and r.endswith(OUTAGE_INFIX)


def blocked_skip_refusal(value, skill, task, rows, entry_ts):
    """R2 (wwhtbt) and R5 (5whysandrhyme): None when `skipped: blocked decision=<ts>` names a denied row of this skill and Task whose reasons are a route
    outage, corroborated by no launch row of the skill, for any task, between that row's ts and the entry's header; else why it is refused."""
    m = re.fullmatch(r"blocked decision=(\S+)", (value or "").strip())
    if not m:
        return f"'skipped: {value}' is not 'skipped: blocked decision=<ts>'"
    if rows is None:
        return f"no decisions log on this host to read decision={m.group(1)}"
    hits = [r for r in rows if r.get("ts") == m.group(1) and r.get("decision") == "denied" and r.get("skill") == skill and r.get("task_id") == task]
    if len(hits) != 1:
        return f"{len(hits)} denied {skill} rows of task {task} at ts={m.group(1)} (want exactly one)"
    if not outage_reason(hits[0].get("reasons"), skill):
        return f"the denied row's reasons are not a route outage the caller cannot cure: {str(hits[0].get('reasons'))[:160]}"
    t0, t1 = parse_iso(m.group(1)), parse_iso(entry_ts)
    if t0 is None or t1 is None:
        return f"decision={m.group(1)} or the entry header {entry_ts} is not an ISO timestamp with an offset"
    if not t0 < t1:      # the window the launcher log must leave empty runs from the denial to the header (code 88ec4f26 L1, behaviour 96397ae0 M2)
        return f"the denied row decision={m.group(1)} is not before the entry header {entry_ts}"
    for r in rows:       # both ends count, and a launch row without a readable ts could fall anywhere (security ddf46516 finding 6)
        if r.get("decision") != "launch" or r.get("skill") != skill:
            continue
        t = parse_iso(r.get("ts") or "")
        if t is None or t0 <= t <= t1:
            return (f"the outage is not corroborated: a {skill} launch row at {r.get('ts')} (task {r.get('task_id')}) "
                    + ("has no ISO timestamp with an offset, so it may fall after the denied row" if t is None else "falls between the denied row and the entry header"))
    return None


CITED_ABS_RE = re.compile(r"(?<![\w./~$}-])(/(?:[\w.@+-]+/)+[\w.@+-]+)")
CITED_HOME_RE = re.compile(r"(?<![\w./~$-])(?:~|\$HOME|\$\{HOME\})(/(?:[\w.@+-]+/)*[\w.@+-]+)")
FILE_REF_RE = re.compile(r"\bfile:([^\s`'\")\]>]+)")


def page_citations(text, home):
    """R3: the absolute paths (two segments or more) and `file:` refs a page cites, trailing punctuation dropped, `file:` refs resolved against the home;
    `~/`, `$HOME/` and `${HOME}/` paths count as absolute paths under the lint's HOME (security review ddf46516 finding 7)."""
    out = []
    for m in CITED_ABS_RE.finditer(text):
        p = m.group(1).rstrip(".,;:")
        if p not in out:
            out.append(p)
    for m in CITED_HOME_RE.finditer(text):
        p = os.path.expanduser("~") + m.group(1).rstrip(".,;:")
        if p not in out:
            out.append(p)
    for m in FILE_REF_RE.finditer(text):
        p = m.group(1).rstrip(".,;:")
        p = p if os.path.isabs(p) else os.path.join(home, p)
        if p not in out:
            out.append(p)
    return out


def reuse_check(L, label, page, sha, inputs, entry, home, resolve):
    """R3: the page's digest, its `sha256sum` input manifest under the PRD home (every cited absolute path and file: ref plus the entry's seed file), and
    `sha256sum -c` run in the manifest's own directory. -> the JSON `reuse` object (`verified` true only when every check passed)."""
    out = {"page": page, "sha256": sha, "inputs": inputs, "verified": False}
    full = resolve(page)
    if not os.path.isfile(full):
        return out                                      # analysis-page-missing is the provenance check's
    got = file_sha(full)
    if got != sha:
        L.fail("analysis-reuse-stale", f"{label}: page {page} sha256 {str(got)[:12]} differs from the recorded sha256={sha[:12]}")
        return out
    mfull = resolve(inputs)
    if not os.path.realpath(mfull).startswith(os.path.realpath(home) + os.sep):
        L.fail("analysis-grammar", f"{label}: inputs={inputs} is not under the PRD home {home}")
        return out
    try:
        mtext = read_text(mfull) if os.path.isfile(mfull) else ""
    except OSError:
        mtext = ""
    mlines = [ln for ln in mtext.splitlines() if ln.strip()]
    if not mlines:
        L.fail("analysis-grammar", f"{label}: inputs manifest {inputs} is absent or empty")
        return out
    mdir, listed = os.path.dirname(mfull), set()
    for ln in mlines:
        m = re.fullmatch(r"([0-9a-f]{64}) [ *](\S.*)", ln)
        if not m:
            L.fail("analysis-grammar", f"{label}: inputs manifest {inputs}: '{ln[:80]}' is not '<sha256>  <path>'")
            return out
        p = m.group(2)
        listed.add(os.path.realpath(p if os.path.isabs(p) else os.path.join(mdir, p)))
    want = page_citations(read_text(full), home)
    for t in entry_seed_tokens(entry):
        if t.startswith("file:"):
            s = t.split()[0][len("file:"):]
            want.append(s if os.path.isabs(s) else os.path.join(home, s))
    missing = [p for p in dict.fromkeys(want) if not os.path.isdir(p) and os.path.realpath(p) not in listed]
    if missing:   # a cited path that is no file on this host can never be listed: the page cannot be reused here (behaviour review 96397ae0 M3, L5)
        absent = [p for p in missing if not os.path.exists(p)]
        unlisted = [p for p in missing if p not in absent]

        def few(ps):
            return ", ".join(ps[:5]) + (f" (+{len(ps) - 5} more)" if len(ps) > 5 else "")
        L.fail("analysis-reuse-incomplete", f"{label}: inputs manifest {inputs}"
               + (f" omits {few(unlisted)} (its paths resolve against its own directory {mdir})" if unlisted else "")
               + ("; and" if unlisted and absent else "")
               + (f" cannot list {few(absent)}, which the page cites and which are not files on this host; re-run the analysis" if absent else ""))
        return out
    try:
        p = subprocess.run(["sha256sum", "-c", "--quiet", "--", os.path.basename(mfull)], cwd=mdir, capture_output=True, text=True, timeout=300,
                           stdin=subprocess.DEVNULL)
        rc, msg = p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as e:
        rc, msg = 1, str(e)
    if rc != 0:
        L.fail("analysis-reuse-stale", f"{label}: sha256sum -c {os.path.basename(mfull)} in {mdir} fails: {msg[:200]}")
        return out
    out["verified"] = True
    return out


def routing_evidence_rules():
    """R4: (ref regex, placeholders) from the routing policy (SKILL_ROUTING_POLICY, else ~/.config/skill-routing/policy.json); Exit2 when unreadable."""
    p = os.environ.get("SKILL_ROUTING_POLICY") or os.path.join(os.path.expanduser("~"), ".config", "skill-routing", "policy.json")
    try:
        ev = json.loads(read_text(p)).get("evidence") or {}
        return re.compile(ev["ref_pattern"]), {str(x).lower() for x in ev.get("placeholders") or []}
    except (OSError, ValueError, KeyError, TypeError, AttributeError, re.error) as e:
        raise Exit2(f"routing policy {p} unreadable or has no evidence.ref_pattern ({e}); cannot check the Failure: refs")


def review_file_verdicts(path):
    """R4: the verdict lines of one review file: a captured result JSON object's `result` text, else the file's own lines."""
    try:
        text = read_text(path)
    except OSError:
        return []
    try:
        d = json.loads(text)
    except ValueError:
        d = None
    if isinstance(d, dict) and isinstance(d.get("result"), str):
        text = d["result"]
    return [v for v in (verdict_of(x) for x in text.split("\n")) if v]


def failure_floor(entries, ei, task, states, rows, home):
    """R4: the lowest class the verdict files allow, from files the author does not write: every verdict file at any depth under notes/reviews/ (sidecar
    .jsonl excluded) whose first lines name the session of a dream `review` launch row. A session's verdicts are the union of its files' verdict lines, so a
    result.json and the verdict file it captures count once. Sessions of the Task launched after the Task's previous entry set the floor: a REJECT of a slug the
    State: names makes it failed-acceptance; a FIX or REJECT of such a slug after an earlier session's (by launch time) FIX or REJECT of that slug in this home
    makes it recurring-failure. A file whose first lines name several review sessions counts for one session only: the latest-launched session of this
    Task it names, else of any task.
    -> (None | "failed-acceptance" | "recurring-failure", [why])."""
    if not rows or task is None:
        return None, []
    same = [e for e in entries[:ei] if entry_task(e) == task]
    since = parse_iso(same[-1]["ts"]) if same else None
    revs = [r for r in rows if r.get("decision") == "launch" and r.get("skill") == "dream" and r.get("role") == "review" and r.get("session")]
    rdir = os.path.join(home, "notes", "reviews")
    files = []
    for d, ds, fs in os.walk(rdir):
        ds.sort()
        files += [os.path.join(d, f) for f in sorted(fs) if not f.endswith(".jsonl")]
    def launched(r):
        t = parse_iso(r.get("ts") or "")
        return (t is None, t.timestamp() if t else 0.0, r["session"])
    by_sess = {}
    for p in files:
        head = first_lines(p)
        named = [r for r in revs if r["session"] in head]
        if not named:
            continue
        # one file, one session: a re-review cites earlier review sessions, never later ones, so the latest-launched session it names is its own
        # (code review 88ec4f26 F2, behaviour review 96397ae0 M1); a file that also names another task's review (a parallel one) stays with this Task's
        # session (targeted review abb2e978 M2)
        named = [r for r in named if r.get("task_id") == task] or named
        r = max(named, key=lambda r: (not launched(r)[0], launched(r)[1], r["session"]))
        x = by_sess.setdefault(r["session"], {"row": r, "files": [], "v": set()})
        x["files"].append(os.path.relpath(p, home))
        x["v"] |= {(s, v) for s, v, _ in review_file_verdicts(p)}

    def when(x):
        return launched(x["row"])
    floor, why, earlier = None, [], set()
    for x in sorted(by_sess.values(), key=when):
        t = parse_iso(x["row"].get("ts") or "")
        mine = x["row"].get("task_id") == task and (since is None or (t is not None and t > since))
        for slug, verdict in sorted(x["v"]):
            if not mine or slug not in states:
                continue
            if verdict == "REJECT" and floor is None:
                floor = "failed-acceptance"
                why.append(f"{x['files'][0]}: {slug} REJECT")
            if verdict in ("FIX", "REJECT") and slug in earlier:
                floor = "recurring-failure"
                why.append(f"{x['files'][0]}: {slug} {verdict} after an earlier FIX or REJECT of {slug} in this home")
        earlier |= {s for s, v in x["v"] if v in ("FIX", "REJECT")}
    return floor, why


def fivewhys_refusal(f, prov5, refs, rows, task, entry_ts, resolve):
    """R5 for the three trigger classes: None when 5whys= is a bound page, a cited reuse bound to a 5whysandrhyme launch row of any task, or a
    corroborated outage skip; else why not."""
    if f is None:
        return "no 5whys= value"
    if f[0] == "page":
        return None if prov5 == "boundary" else f"5whys=page {f[1]} is not bound to a 5whysandrhyme launch row of Task {task}"
    if f[0] == "reused":
        page, sha = f[1], (f[2] or {}).get("sha256") if len(f) > 2 else None
        full = resolve(page)
        if not sha or not os.path.isfile(full) or file_sha(full) != sha:
            return f"5whys=reused {page}: the page is missing, has no sha256= or its bytes moved"
        head = first_lines(full)
        if not any(r.get("session") and r["session"] in head for r in rows or [] if r.get("decision") == "launch" and r.get("skill") == "5whysandrhyme"):
            return f"5whys=reused {page}: its first {PAGE_LINES} lines name no session of a 5whysandrhyme launch row"
        if "page:" + page not in refs:
            return f"5whys=reused {page}: the Failure: line does not cite page:{page}"
        return None
    if f[0] == "skipped":
        return blocked_skip_refusal(f[1], "5whysandrhyme", task, rows, entry_ts)
    return f"5whys={f[0]}"


def trigger_record(L, entries, ei, an, prov, task, states, mrec, rows, home, resolve, failure_lines, coverage=None, floor_info=None):
    """R1-R5 for one entry on or after the cutover. -> the R6 JSON additions to `analysis`. `coverage` and `floor_info` are covered_kind's and
    failure_floor's results when the caller already has them."""
    entry = entries[ei]
    covered, why = coverage or covered_kind(entries, ei, task, states, mrec, rows, home, resolve)
    out = {"covered": covered, "failure": None}
    floor, fwhy = floor_info or failure_floor(entries, ei, task, states, rows, home)
    f = an.get("fivewhys")
    if covered == "none":
        # R1: an uncovered entry keeps today's rules, so its Failure: line is not read (code review 88ec4f26 L3, behaviour review 96397ae0 L2), unless
        # verdict files bound since the Task's previous entry set an R4 floor: the next entry reads only later reviews, so an entry without the line would
        # drop the floor (security review ddf46516 finding 3). Such an entry carries the line at the floor, and R5 applies to it.
        if floor is None:
            return out
        if not failure_lines:
            L.fail("line-missing", f"Failure (verdict files set the floor {floor} for this entry: {'; '.join(fwhy)}; the Task's next entry reads only later reviews)")
            return out
    else:
        w = an.get("wwhtbt")
        if w and w[0] == "reused":
            if len(w) < 3 or not w[2]:
                L.fail("analysis-grammar", f"wwhtbt: a covered entry ({why}) reuses as 'reused <page> sha256=<64 hex> inputs=<manifest>'")
            else:
                out["reuse"] = reuse_check(L, "wwhtbt", w[1], w[2]["sha256"], w[2]["inputs"], entry, home, resolve)
                out["reuse"]["verified"] = out["reuse"]["verified"] and prov.get("wwhtbt") in ("gated", "boundary")   # and bound (code review 88ec4f26 L4)
        elif w and w[0] == "skipped":
            bad = blocked_skip_refusal(w[1], "wwhtbt", task, rows, entry["ts"])
            if bad:
                L.fail("analysis-skip-refused", f"wwhtbt: a covered entry ({why}): {bad}")
        if not failure_lines:
            L.fail("line-missing", f"Failure (a covered entry: {why})")
            if f and f[0] == "reused":
                L.fail("analysis-grammar", f"5whys value '{f[2]['raw']}' (R5: `reused` is the form of the three trigger classes, which a Failure: line names)")
            return out
    if len(failure_lines) > 1:
        L.fail("failure-grammar", f"{len(failure_lines)} Failure: lines (an entry carries one; code review 88ec4f26 L2)")
        return out
    toks = failure_lines[-1][len("Failure:"):].split()
    if toks == ["none"]:
        cls, refs = "none", []
    elif not toks or toks[0] not in FAILURE_CLASSES or len(toks) < 2:
        L.fail("failure-grammar", f"'{failure_lines[-1]}' is not 'Failure: none' or 'Failure: <{'|'.join(FAILURE_CLASSES)}> <ref> [<ref> ...]'")
        return out
    else:
        cls, refs = toks[0], toks[1:]
        pat, holders = routing_evidence_rules()
        bad = [r for r in refs if not pat.match(r) or r.split(":", 1)[-1].strip().lower() in holders]
        if bad:
            L.fail("failure-grammar", f"ref {', '.join(bad)} does not match the routing policy's evidence.ref_pattern or names a placeholder")
            return out
    out["failure"] = {"class": cls, "refs": refs}
    if floor == "failed-acceptance" and cls not in ("failed-acceptance", "recurring-failure") or floor == "recurring-failure" and cls != "recurring-failure":
        L.fail("failure-class-mismatch", f"Failure: {cls} is below the floor {floor} ({'; '.join(fwhy)})")
    if cls in TRIGGER_CLASSES:
        bad = fivewhys_refusal(f, prov.get("fivewhys"), refs, rows, task, entry["ts"], resolve)
        if bad:
            L.fail("analysis-trigger-unmet", f"Failure: {cls} needs a bound 5whysandrhyme page: {bad}")
    elif cls == "transient" and not (f and (f[0] == "inline" or f[0] == "skipped" and f[1].strip() == "transient")):
        L.fail("analysis-trigger-unmet", "Failure: transient takes 5whys=inline or 5whys=skipped: transient (bounded recovery, no analysis stack)")
    elif f and f[0] == "reused":     # R5: `other` and `none` keep today's values (code review 88ec4f26 F1)
        L.fail("analysis-grammar", f"5whys value '{f[2]['raw']}' (R5: for Failure: {cls}, today's values; `reused` is the form of the three trigger classes)")
    return out


# ---------------------------------------------------------------- finding consumption in the log check (PRD-dream-finding-consumption R1, R6, R7)
CONS_LINE_RE = re.compile(r"^Consumption:\s+(\S+)\s*$")
CONS_PRD_RE = re.compile(r"PRD-[A-Za-z0-9._-]+\.md")


def entry_post(ts, route, rows):
    """R9 (trigger-record R7): an entry is under R1-R7 when its header timestamp is at or after the cutover instant (after_cutover; a header with no
    readable leading date counts as after), or its Route: binds a dream launch row whose `ts` is. One cutover, shared by both PRDs."""
    return (after_cutover(ts)
            or bool(route and route.get("decision") and any(r.get("decision") == "launch" and r.get("skill") == "dream" and r.get("session") == route["session"]
                                                          and r.get("ts") == route["decision"] and after_cutover(r.get("ts"), row_ts=True) for r in rows or [])))


def entry_route(e):
    """The Route: of one log entry (its last Route: line) as lint_log parses it, or None."""
    s = None
    for ln in e["lines"]:
        if ln.startswith("Route:"):
            s = ln.rstrip()
    if s is None:
        return None
    mu = re.match(r"^Route:\s+ungoverned\s+session=(\S+)\s+host=(\S+)$", s)
    mg = re.match(r"^Route:\s+(\S+)\s+(\S+)\s+(\S+)\s+session=(\S+)\s+decision=(\S+)$", s)
    if mu:
        return {"route": "ungoverned", "session": mu.group(1), "decision": None}
    if mg and mg.group(1) != "ungoverned":
        return {"route": mg.group(1), "session": mg.group(4), "decision": mg.group(5)}
    return None


def entry_states(e):
    """slug -> values of one log entry's last State: line (grammar-valid tokens)."""
    s = None
    for ln in e["lines"]:
        if ln.startswith("State:"):
            s = ln
    out = {}
    for t in (s or "State:")[len("State:"):].split():
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)=(\S+)$", t)
        if m:
            out.setdefault(m.group(1), []).append(m.group(2))
    return out


def cons_entry_pages(an):
    """R1: the pages an entry's Analysis: line binds (`wwhtbt=ran|reused`, `5whys=page|reused`), as written there."""
    out = []
    w, f = an.get("wwhtbt"), an.get("fivewhys")
    if w and w[0] in ("ran", "reused") and w[1] not in out:
        out.append(w[1])
    if f and f[0] in ("page", "reused") and f[1] not in out:
        out.append(f[1])
    return out


def prd_depends_on(home, base):
    """The PRD basenames one PRD's `Depends-on:` frontmatter line names (empty without the line), or None when the home holds no such PRD."""
    p = next((os.path.join(home, d, base) for d in PRD_DIRS if os.path.isfile(os.path.join(home, d, base))), None)
    if p is None:
        return None
    try:
        text = read_text(p)
    except OSError:
        return None
    for l in text.split("\n"):
        if l.startswith("## "):
            break
        m = re.match(r"^(?:- )?Depends-on:\s*(.*)$", l)
        if m:
            return set(CONS_PRD_RE.findall(m.group(1)))
    return set()


def first_prds(home, members):
    """R6, R7: the first PRDs of a run (members whose Depends-on names no other member) and the members the home lacks (dependencies unknown).
    `members` is the mission's PRDs, else the PRDs the entry's State: line names."""
    first, unknown = [], []
    for b in members:
        d = prd_depends_on(home, b)
        if d is None:
            unknown.append(b)
        elif not d & (set(members) - {b}):
            first.append(b)
    return first, unknown


def cons_view(entries, j, rows, home, resolve):
    """What R1 and R7 read of entry j: Task, State, Analysis, coverage (trigger-record R1), the Failure: class trigger-record reads, the PRD members
    (mission PRDs, else State: slugs) and its Consumption: lines."""
    e = entries[j]
    task = entry_task(e)
    route = entry_route(e)
    post = entry_post(e["ts"], route, rows)
    states = entry_states(e)
    al = [ln.rstrip() for ln in e["lines"] if ln.startswith("Analysis:")]
    an = parse_analysis(al[-1], extended=post)[0] if al else {"wwhtbt": None, "fivewhys": None, "adversarial": None}
    mrec = None
    if any(ln.startswith("Mission:") for x in entries[:j + 1] for ln in x["lines"]):
        try:
            mrec = mission_record(Lint(), entries, j, task, list(states), resolve)
        except Exit2:
            mrec = None
    cov, floor = "none", None
    if post:
        try:
            cov = covered_kind(entries, j, task, states, mrec, rows, home, resolve)[0]
            floor = failure_floor(entries, j, task, states, rows, home)[0]
        except (Exit2, OSError):
            cov = "unknown"                  # read as covered: more holds, never fewer
    fl = [ln.rstrip() for ln in e["lines"] if ln.startswith("Failure:")]
    toks = fl[-1][len("Failure:"):].split() if fl and (cov != "none" or floor is not None) else []
    return {"ts": e["ts"], "task": task, "post": post, "states": states, "an": an, "covered": cov,
            "failure": toks[0] if toks and toks[0] in FAILURE_CLASSES else None,
            "members": list(mrec["header"]["prds"]) if mrec and mrec.get("header") else [f"PRD-{s}.md" for s in states],
            "lines": [ln.rstrip() for ln in e["lines"] if ln.startswith("Consumption:")], "route": route}


def cons_read_entry(L, v, rows, dec_path, home):
    """R1's line and R2-R6 for one entry's record. A bad line or an unreadable record is `consumption-missing` (into L). -> (path, obj, st) | None."""
    if not v["lines"]:
        return None
    if len(v["lines"]) > 1:
        L.fail("consumption-missing", f"{len(v['lines'])} Consumption: lines (an entry carries one)")
        return None
    m = CONS_LINE_RE.match(v["lines"][0])
    if not m:
        L.fail("consumption-missing", f"'{v['lines'][0]}' is not 'Consumption: <path>'")
        return None
    path = m.group(1)
    full = os.path.realpath(path if os.path.isabs(path) else os.path.join(home, path))
    hr = os.path.realpath(home)
    if os.path.commonpath([full, hr]) != hr or not os.path.isfile(full):
        L.fail("consumption-missing", f"Consumption: {path} is not a file under the PRD home {home}")
        return None
    a = {"consumption": full, "task": v["task"], "prd_home": home, "reviews": os.path.join(home, "notes", "reviews"), "decisions": dec_path,
         "drows": rows, "require_closed": False, "page": None, "lineage": [v["route"]["session"]] if v.get("route") else []}
    obj, st = cons_record(L, a, pages=cons_entry_pages(v["an"]), mode="authoring")
    if st is None:
        return None
    first, _ = first_prds(home, v["members"])                                                                                   # R6
    for r in st["rows"]:
        if r["binding"] == "requirement" and r["finding"] == "falsifier" and (r.get("ac") != 1 or r.get("prd") not in first):
            L.fail("falsifier-not-first", f"row {r['id']} ({os.path.basename(r['page'])}#falsifier): {r.get('prd')} AC {r.get('ac')} is not AC 1 of a "
                                          f"first PRD of this run ({', '.join(first) or 'none'}; members {', '.join(v['members']) or 'none'}); a falsifier "
                                          f"owned outside this run binds repair, residual or pending")
            if not any(x is r for x in st["refused"]):
                st["refused"].append(r)
            st["consumed"][(r["page"], "falsifier")] = False
    return path, obj, st


def cons_items(v, st, home):
    """R7: the unconsumed items of one entry: refused rows, valid pending rows, unbound findings (every finding of a bound page the record does not
    read), a covered entry's WWHTBT skip and a 5whys skip under a trigger class."""
    items = []
    if st is not None:
        items += [{"kind": "row", "row": r, "state": "refused", "resolve": st["resolve"], "gated": id(r) in st["gated"]} for r in st["refused"]]
        items += [{"kind": "row", "row": r, "state": "pending", "resolve": st["resolve"], "gated": id(r) in st["gated"]} for r in st["pending"]]
        items += [{"kind": "unbound", "page": pg, "finding": f, "resolve": st["resolve"]} for pg, f in st["unbound"]]
    else:
        def res(p):
            return p if os.path.isabs(p) else os.path.join(home, p)
        for pg in cons_entry_pages(v["an"]):
            try:
                need = cons_page_findings(read_text(res(pg)))[0]
            except OSError:
                need = None
            items += [{"kind": "unbound", "page": pg, "finding": f, "resolve": res} for f in (need or ["*"])]
    w, f5 = v["an"].get("wwhtbt"), v["an"].get("fivewhys")
    if v["covered"] != "none" and w and w[0] == "skipped":
        items.append({"kind": "wwhtbt-skip"})
    if v["failure"] in TRIGGER_CLASSES and f5 and f5[0] == "skipped":
        items.append({"kind": "5whys-skip"})
    return items


def cons_item_text(it):
    k = it["kind"]
    if k == "row":
        r = it["row"]
        where = f"{os.path.basename(r['page'])}#{r['finding']}" if isinstance(r.get("page"), str) and isinstance(r.get("finding"), str) else "?"
        return f"row {r.get('id', '?')} ({where}) {it['state']}"
    if k == "unbound":
        return f"{os.path.basename(it['page'])}#{it['finding']} unbound" if it["finding"] != "*" else f"{os.path.basename(it['page'])} unread (every finding)"
    return "a covered entry's WWHTBT skip (an unbound falsifier)" if k == "wwhtbt-skip" else "a 5whys skip under a trigger-class Failure:"


def cons_first_hold(v, home):
    """The slugs an unbound falsifier holds (R7): the run's first PRDs, members whose dependencies are unknown counting as first; when no member is
    first (a Depends-on cycle, with or without unknown members), every member (reviews r15 M2, r15b LOW 4)."""
    first, unknown = first_prds(home, v["members"])
    return [b[len("PRD-"):-len(".md")] for b in (first + unknown if first else list(v["members"]))]   # review r15b LOW 4: no first, every member


def cons_hold(it, v, home):
    """R7: the slugs one unconsumed item holds. A row naming `prd` holds that slug, and a refused one every slug of the entry's State: line too when
    that PRD is none of the run's (reviews r15 M1, r15b LOW 3); a row whose successor's ledger gate is verified (cons_ledger_gate: bound in the canonical
    ledger, its done-check running this lint, the successor still open) and that names no prd holds the successor through that gate and no slug; any other row, an unbound mechanism and a
    trigger-class 5whys skip hold every State: slug; an unbound falsifier, a refused falsifier row (review r15 L1) and a WWHTBT skip hold the first
    PRDs (cons_first_hold)."""
    k = it["kind"]
    if k == "row":
        r = it["row"]
        states = list(v["states"])
        held = []
        if isinstance(r.get("prd"), str) and CONS_PRD_RE.fullmatch(r["prd"]):
            s = r["prd"][len("PRD-"):-len(".md")]
            ours = set(states) | {b[len("PRD-"):-len(".md")] for b in v["members"]}
            held = [s] + ([] if s in ours or it["state"] != "refused" else states)      # review r15b LOW 3: a valid pending row holds its prd alone
        elif not it.get("gated"):
            held = states
        if r.get("finding") == "falsifier" and it["state"] == "refused":
            held += cons_first_hold(v, home)
        return list(dict.fromkeys(held))
    if k == "wwhtbt-skip" or k == "unbound" and it["finding"] == "falsifier":
        return cons_first_hold(v, home)
    return list(v["states"])


def cons_lifts(it, later):
    """R7: whether a later entry of the Task lifts one earlier item: a record binding the same page and finding as consumed (not pending), or binding
    that page whole at its current bytes (every current finding consumed, none pending or unbound) when the finding is no longer on it (review r15
    M3: a mechanism since marked LIVE), a later `wwhtbt=ran|reused` for a WWHTBT skip, a later bound 5whysandrhyme page for a trigger-class 5whys skip.
    later: [(view, st)]."""
    k = it["kind"]
    if k == "wwhtbt-skip":
        return any(v["an"].get("wwhtbt") and v["an"]["wwhtbt"][0] in ("ran", "reused") for v, _ in later)
    if k == "5whys-skip":
        return any(v["an"].get("fivewhys") and v["an"]["fivewhys"][0] in ("page", "reused") for v, _ in later)
    if k == "row":
        r = it["row"]
        if not (isinstance(r.get("page"), str) and isinstance(r.get("finding"), str) and r.get("page")):
            return False                     # a row without a page and a finding names nothing a later record can bind
        page, finding, res = r["page"], r["finding"], it["resolve"]
    else:
        page, finding, res = it["page"], it["finding"], it["resolve"]
    key = os.path.realpath(res(page))                    # the page as its own record resolves it (the PRD home), compared by real path
    for _, st in later:
        if st is None:
            continue
        pend = {(x["page"], x["finding"]) for x in st["pending"]}
        got = [(f, ok and (pg, f) not in pend) for (pg, f), ok in st["consumed"].items() if os.path.realpath(st["resolve"](pg)) == key]
        whole = bool(got) and all(ok for _, ok in got) and not any(os.path.realpath(st["resolve"](pg)) == key for pg, _ in st["unbound"])
        if finding == "*":
            if whole:
                return True
        elif any(f == finding and ok for f, ok in got):
            return True
        elif whole and finding not in {f for f, _ in got}:
            return True
    return False


def cons_log(L, entries, ei, cur, rows, dec_path, home, resolve):
    """PRD-dream-finding-consumption R1, R6 and R7 for the entry under check (on or after the cutover, R9). `cur`: its cons_view with lint_log's own
    readings. Earlier entries' records are read apart (their refusals are not this entry's findings); only their holds reach this entry.
    -> the `consumption` JSON block."""
    task = cur["task"]
    if task is None:                     # review r15 L2: a Task: line short of the full grammar still names the Task earlier records are read by
        task = entry_task(entries[ei])   # (entry_task, as for every earlier entry); line-missing reports the grammar
        cur = dict(cur, task=task)
    pages = cons_entry_pages(cur["an"])
    got = cons_read_entry(L, cur, rows, dec_path, home)
    path, obj, st = got if got else (None, None, None)
    views = {}

    def view(j):
        if j not in views:
            v = cons_view(entries, j, rows, home, resolve)
            g = cons_read_entry(Lint(), v, rows, dec_path, home) if v["post"] else None
            views[j] = (v, g[2] if g else None, g[0] if g else None)
        return views[j]
    same = [j for j in range(ei) if task not in (None, "none") and entry_task(entries[j]) == task]
    same = [j for j in same if view(j)[0]["post"]]                     # R9: an entry before the cutover is not under R1-R7, nor are its holds
    held, open_before, earlier = {}, [], []
    for j in same:
        v, sj, pj = view(j)
        later = [(view(k)[0], view(k)[1]) for k in same if k > j]
        rest = []
        for it in cons_items(v, sj, home):
            before = cons_lifts(it, later)
            if before or cons_lifts(it, [(cur, st)]):
                continue
            rest.append(cons_item_text(it))
            if it["kind"] in ("row", "unbound"):
                open_before.append(f"entry {v['ts']}: {cons_item_text(it)}")
            for s in cons_hold(it, v, home):
                held.setdefault(s, []).append(f"entry {v['ts']}: {cons_item_text(it)}")
        earlier.append({"entry": v["ts"], "record": pj, "unconsumed": rest})
    if not cur["lines"]:                                                                                                         # R1
        if pages:
            L.fail("consumption-missing", f"the Analysis: line binds {', '.join(pages)}; the entry carries no `Consumption: <path>` line")
        elif cur["covered"] != "none" and open_before:
            L.fail("consumption-missing", f"a covered entry while an earlier record of Task {task} still has unconsumed rows ({'; '.join(open_before[:5])}); "
                                          f"the entry carries no `Consumption: <path>` line")
    for it in cons_items(cur, st, home):                                                                                       # R7
        for s in cons_hold(it, cur, home):
            held.setdefault(s, []).append(cons_item_text(it))
    if task is None:                     # reviews r15 L2, r15b LOW 2: no Task can be read (the line is missing or unreadable), so none of its earlier
        for s in cur["states"]:          # records can be checked: every State: slug is held
            held.setdefault(s, []).append("the entry's Task: line cannot be read, so no earlier record of its Task can be checked")
    for slug, vals in cur["states"].items():
        if "eligible" in vals and slug in held:
            L.fail("consumption-blocked", f"slug {slug}=eligible while held by {'; '.join(held[slug][:5])}")
    pend = {(x["page"], x["finding"]) for x in st["pending"]} if st else set()
    return {"record": path, "pages": pages, "rows": len(st["rows"]) if st else 0,
            "unconsumed": sorted(f"{os.path.basename(p)}#{f}" for (p, f), ok in st["consumed"].items() if not ok) if st else [],
            "pending": sorted(f"{os.path.basename(p)}#{f}" for p, f in pend),
            "repairs": obj["repairs"] if obj else [],
            "held": [{"slug": s, "by": held[s]} for s in sorted(held)],
            "earlier": earlier}


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
    sroots = ScopeRoots(scope_roots(a["scope_roots"], home), home) if a["scope_roots"] else None

    def resolve(p):
        return p if os.path.isabs(p) else os.path.join(home, p)
    if sroots is not None:
        resolve.scope_roots = sroots       # Q5: read only by scope_file, for review rows' scope

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
    # trigger-record R7: the header timestamp, which the author writes, or the launcher's own: a header with no readable leading date, or a Route: bound
    # to a dream launch row at or after the cutover, puts the entry under R1-R5 too (security review ddf46516 finding 5). A timestamp with an offset
    # is compared as an instant (after_cutover); real headers carry sloppy times ('2026-09-13T16:2xZ', '2026-09-29T14:55', '2026-11-12'), for which
    # only the date is read, so every earlier entry keeps 43d5b39's output.
    post = entry_post(entry["ts"], route, rows)
    failure_lines = [ln.rstrip() for ln in entry["lines"] if ln.startswith("Failure:")] if post else []
    if "Analysis" in lines:
        an, probs = parse_analysis(lines["Analysis"], extended=post)
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
        mrec = mission_record(L, entries, ei, task, list(states), resolve,
                              {"path": dec_path, "rows": rows} if governed else None)

    # ---- trigger record R1 (PRD-dream-analysis-trigger-record): coverage, before provenance reads the Analysis values
    coverage, floor_info = None, None
    if post:
        coverage = covered_kind(entries, ei, task, states, mrec, rows, home, resolve)
        floor_info = failure_floor(entries, ei, task, states, rows, home)
        if coverage[0] == "none" and "Analysis" in lines:
            # an uncovered entry keeps today's Analysis grammar (code review 88ec4f26 F1): the extended `reused` forms are grammar problems there, as at
            # 43d5b39, except R5's `5whys=reused` when verdict files set a floor for the entry (R4 and R5 apply to it; see trigger_record)
            keep5 = floor_info[0] is not None
            an0, probs0 = parse_analysis(lines["Analysis"], extended=False)
            for p in probs0:
                if p not in probs and not (keep5 and p.startswith("5whys value ")):
                    L.fail("analysis-grammar", p)
            an = dict(an0, fivewhys=an["fivewhys"]) if keep5 else an0

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

    # ---- trigger record (PRD-dream-analysis-trigger-record R1-R6), entries on or after the cutover only
    trig = trigger_record(L, entries, ei, an, prov, task, states, mrec, rows, home, resolve, failure_lines, coverage, floor_info) if post else None

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
                if mt and pt and mt <= pt and not post_review_reuse(entries, ei, adv, mrec, rows, task, reviews_raw, resolve):
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
                if "historical" in repairs:         # producer-contract Repair 3: kept, never dropped
                    mfields["repairs_historical"] = repairs.pop("historical")
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

    # ---- finding consumption (PRD-dream-finding-consumption R1, R6, R7), entries on or after the cutover only (R9)
    cons = None
    if post:
        cur = {"ts": entry["ts"], "task": task, "post": True, "states": states, "an": an,
               "covered": coverage[0] if coverage else "none",
               "failure": (trig or {}).get("failure", {}).get("class") if (trig or {}).get("failure") else None,
               "members": list(mrec["header"]["prds"]) if mrec and mrec.get("header") else [f"PRD-{s}.md" for s in states],
               "lines": [ln.rstrip() for ln in entry["lines"] if ln.startswith("Consumption:")], "route": route}
        cons = cons_log(L, entries, ei, cur, rows, dec_path, home, resolve)

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
                         **({"superseded": r["superseded"]} if r.get("superseded") else {}),
                         **({"scope_read": r["scope_read"]} if r.get("scope_read") else {})) for r in reviews],
        "states": states,
        "provenance": prov,
        "mission": mission_json(mrec),
    }
    if sroots is not None:                              # Q5: the map and every review scope read under it, both paths
        obj["scope_roots"] = {"map": [{"recorded": r, "local": h} for r, h in sroots.pairs], "reads": sroots.reads}
    if trig is not None:
        obj["analysis"].update(trig)                    # trigger-record R6: covered, failure and, for a reuse, reuse
    if cons is not None:
        obj["consumption"] = cons                       # finding-consumption R7: what the case-11 gate and the persist hook (edge E37) read
    prov["mission"] = "none" if obj["mission"] is None else "self"
    if obj["mission"] is not None and mfields is not None:
        prds = mrec["header"]["prds"] if mrec["header"] else []
        obj["mission"].update(mfields)
        obj["mission"]["dependent_slugs"] = [{"slug": b[len("PRD-"):-len(".md")], "reason": "; ".join(deps[b])}
                                             for b in prds if b in deps]
        # R8: verified when a chain review binds, the mission verdict is APPROVE and no mission finding fired
        if vr is not None and mfields["verdict"] == "APPROVE" and not any(f in MISSION_IDS + SWEEP_IDS for f, _ in L.findings):
            prov["mission"] = "verified"
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


# ---------------------------------------------------------------- finding consumption (PRD-dream-finding-consumption R2-R5, R8)
CONS_SCHEMA = "analysis-consumption.v1"
CONS_COMMON = ("id", "page", "page_sha256", "finding", "binding", "author_session")
CONS_KEYS = {   # binding -> (required keys, optional keys)                                                                     (R2, R3)
    "requirement": (("prd", "ac"), ("kill", "reexpression", "control")),
    "test": (("repo", "commit", "path"), ()),
    "repair": (("ask", "owner", "successor"), ()),
    "residual": (("owner", "evidence", "accepted_by"), ("prd", "part")),
    "pending": (("owner", "due", "ask", "successor"), ("prd",)),
}
CONS_RECEIPT_KEYS = ("session", "run", "run_id", "rc", "report", "receipt", "result", "launch")                              # R4
CONS_FINDING_RE = re.compile(r"falsifier|mechanism:[1-9][0-9]*")
CONS_ASK_RE = re.compile(r"A[0-9]+")
CONS_HEX64 = re.compile(r"[0-9a-f]{64}")
CONS_HEX40 = re.compile(r"[0-9a-f]{40}")
CONS_TOKEN_RE = re.compile(r"(waits-on|closes-after)=row:([A-Za-z0-9_,-]+)")                                        # the close gate's TOKEN_RE


def cons_page_findings(text):
    """R5: the findings of a bound page that need a row, or (None, why) when the page has no parseable falsifier section or `# Mechanisms` heading.
    Falsifier: a `# Weakest link` heading (wwhtbt) or a line beginning `WWHTBT (the weakest link):` (5whysandrhyme). Mechanisms: the top-level lines
    beginning `- ` or `<n>. ` under `# Mechanisms`, up to the next `#` heading; an item whose state word (the text after its last ` state `, up to a
    parenthesis) is exactly LIVE or MERGED needs no row."""
    lines = text.split("\n")
    fals = any(re.match(r"^#\s+Weakest link\s*$", l) for l in lines) or any(l.startswith("WWHTBT (the weakest link):") for l in lines)
    start = next((i for i, l in enumerate(lines) if re.match(r"^#\s+Mechanisms\s*$", l)), None)
    if not fals:
        return None, "no falsifier section (`# Weakest link` or `WWHTBT (the weakest link):`)"
    if start is None:
        return None, "no `# Mechanisms` heading"
    need, n, fence = ["falsifier"], 0, False
    for l in lines[start + 1:]:
        if l.startswith("```"):                                     # review r14 L1: a fenced block is neither a heading nor an item
            fence = not fence
            continue
        if fence:
            continue
        if l.startswith("#"):
            break
        if re.match(r"^(- |[0-9]+\. )", l):
            n += 1
            st = l.rsplit(" state ", 1)[1].split("(", 1)[0].strip() if " state " in l else ""
            if st not in ("LIVE", "MERGED"):
                need.append(f"mechanism:{n}")
    return need, None


def cons_page_falsifier(text):
    """R3: the falsifier script the page itself names: its frontmatter `falsifier: <path> sha256=<64 hex>` (path and digest), else the script the first
    backticked command of its `# Weakest link` section runs (path only), read from the section's `**Falsifier` paragraph onward when it has one. A
    command is a span whose first word is a runner (`bash`, `sh`, `python3`, `python`) followed by a `.sh`/`.py` path, or a `./…` `.sh`/`.py` path; a
    path cited in backticks is not a command (review r14 M5). -> (path, sha256 or None) or (None, None)."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for l in m.group(1).split("\n"):
            fm = re.match(r"^falsifier:\s*(\S+)(?:\s+sha256=([0-9a-f]{64}))?\s*$", l)
            if fm:
                return fm.group(1), fm.group(2)
    sec = re.search(r"^#\s+Weakest link\s*$(.*?)(?=^#\s|\Z)", text, re.S | re.M)
    body = sec.group(1) if sec else ""
    fp = re.search(r"^\*\*Falsifier", body, re.M)
    for cmd in re.findall(r"`([^`]+)`", body[fp.start():] if fp else body):
        toks, i = cmd.split(), 0
        if toks and toks[0] == "timeout":                     # review r14b L-b: `timeout [opts] N`, then the runner's own options
            i = 1
            while i < len(toks) and toks[i].startswith("-"):
                i += 2 if toks[i] in ("-k", "-s") else 1
            i += 1
        if i < len(toks) and toks[i] in ("bash", "sh", "python3", "python"):
            i += 1
            while i < len(toks) and toks[i].startswith("-") and toks[i] not in ("-c", "-m"):
                i += 1
            if i < len(toks) and re.search(r"\.(sh|py)$", toks[i]):
                return toks[i], None
        elif i < len(toks) and toks[i].startswith("./") and re.search(r"\.(sh|py)$", toks[i]):
            return toks[i], None
    return None, None


def cons_names(text, base, finding):
    """True when text names `<page basename>#<finding>` (several findings of one page comma-separated after one basename, R3)."""
    for m in re.finditer(re.escape(base) + r"#((?:falsifier|mechanism:[1-9][0-9]*)(?:,(?:falsifier|mechanism:[1-9][0-9]*))*)", text):
        if finding in m.group(1).split(","):
            return True
    return False


def cons_ac_line(prd_text, ac):
    body = re.search(r"^## Acceptance criteria\s*$(.*?)(?=^## |\Z)", prd_text, re.S | re.M)
    for l in (body.group(1) if body else "").split("\n"):
        if re.match(r"^%d\. " % ac, l):
            return l
    return None


def cons_wm_asks(args):
    """The canonical ledger, read only: `wm-asks asks ...` -> parsed JSON, or None when wm-asks is not installed here (canonical-unavailable)."""
    exe = shutil.which("wm-asks")
    if not exe:
        return None
    p = subprocess.run([exe, "asks"] + args, capture_output=True, text=True, timeout=60)
    if p.returncode != 0:
        raise Exit2(f"wm-asks asks {' '.join(args)} exited {p.returncode}: {(p.stderr or p.stdout).strip()[:200]}")
    try:
        return json.loads(p.stdout)
    except ValueError as e:
        raise Exit2(f"wm-asks asks {' '.join(args)} printed no JSON ({e})")


def cons_record(L, a, pages=(), mode="check"):
    """R2-R5 for one consumption record, shared by check mode (R8) and authoring mode (R1-R7). `a`: consumption, task, prd_home, reviews,
    decisions, require_closed, and in authoring mode drows (the decisions rows the log check already read) and lineage (the entry's Route session).
    `pages`: the pages the record must bind (check mode's --page; authoring mode, the pages the entry's Analysis: line binds). In authoring mode an
    unreadable record is `consumption-missing` and a canonical read that cannot be made is the refusal `canonical-unavailable` (check mode: exit 2).
    -> (obj, st), obj the check-mode JSON object and st what R7 reads: grammar-valid rows, refused rows (any refusal, including every row of a stale
    or unreadable page), valid pending rows, unbound findings ((page, finding), finding `*` for a page whose findings cannot be read), the
    consumed map and `gated`, the ids (id()) of the repair and pending rows whose successor's ledger gate was verified (cons_ledger_gate: the ask and
    the successor bound in the canonical ledger, the successor's done-check running this lint); (None, None) when an authoring-mode record cannot be
    read."""
    L.repairs = []
    L.gated = set()
    rec, task = a["consumption"], a["task"]
    try:
        raw = read_text(rec)
    except OSError as e:
        if mode == "authoring":
            L.fail("consumption-missing", f"the consumption record {rec} cannot be read ({e})")
            return None, None
        raise Exit2(f"cannot read the consumption record {rec}: {e}")
    base_dir = a["prd_home"] or os.path.dirname(os.path.abspath(rec))

    def resolve(p):
        return p if os.path.isabs(p) else os.path.join(base_dir, p)
    st = {"rows": [], "refused": [], "pending": [], "unbound": [], "consumed": {}, "resolve": resolve, "gated": L.gated}

    def refuse_row(r):
        if not any(x is r for x in st["refused"]):
            st["refused"].append(r)
    rows, seen = [], set()
    for n, ln in enumerate(raw.split("\n"), 1):
        if not ln.strip():
            continue
        try:
            r = json.loads(ln)
        except ValueError:
            L.fail("consumption-grammar", f"line {n} is not one JSON object")
            refuse_row({})
            continue
        if not isinstance(r, dict):
            L.fail("consumption-grammar", f"line {n} is not one JSON object")
            refuse_row({})
            continue
        rid = r.get("id")
        b = r.get("binding")
        if b not in CONS_KEYS:                                                                                                  # R4
            L.fail("consumption-receipt-only", f"row {rid!r}: binding {b!r} is none of {', '.join(CONS_KEYS)}; a receipt binds nothing")
            refuse_row(r)
            continue
        req, opt = CONS_KEYS[b]
        if any(k in r for k in CONS_RECEIPT_KEYS) and not all(r.get(k) not in (None, "", []) for k in req):
            L.fail("consumption-receipt-only", f"row {rid!r}: its only target is a receipt ({', '.join(k for k in CONS_RECEIPT_KEYS if k in r)})")
            refuse_row(r)
            continue
        probs = []
        if not isinstance(rid, str) or not rid.strip():
            probs.append("id is not a non-empty string")
        elif rid in seen:
            probs.append(f"id {rid} repeats")
        if not isinstance(r.get("page"), str) or not r.get("page", "").strip():
            probs.append("page is not a path")
        if not isinstance(r.get("page_sha256"), str) or not CONS_HEX64.fullmatch(r.get("page_sha256", "")):
            probs.append("page_sha256 is not 64 lowercase hex")
        if not isinstance(r.get("finding"), str) or not CONS_FINDING_RE.fullmatch(r.get("finding", "")):
            probs.append("finding is not `falsifier` or `mechanism:<n>`")
        if not isinstance(r.get("author_session"), str) or not r.get("author_session", "").strip():
            probs.append("author_session is missing")
        extra = sorted(k for k in r if k not in CONS_COMMON + req + opt + ("note",))
        if extra:
            probs.append("keys outside analysis-consumption.v1: " + ", ".join(extra))
        if "note" in r and not isinstance(r["note"], str):
            probs.append("note is not text")
        if probs:
            L.fail("consumption-grammar", f"row {rid!r}: " + "; ".join(probs))
            refuse_row(r)
            continue
        seen.add(rid)
        rows.append(r)
    st["rows"] = rows
    authors = {r["author_session"] for r in rows}
    by_page = {}
    for r in rows:
        by_page.setdefault(r["page"], []).append(r)
    for pg in pages:
        if pg not in by_page:
            by_page[pg] = []                     # R8 --page, R1 an entry's pages: the record must bind that page's findings; each one it does not is named
    pages = list(by_page)
    if not rows and not by_page:
        L.fail("consumption-grammar", f"record {rec} has no row and no --page names a page it must bind (review r14 L5)")
    if a["require_closed"] and not any(r["binding"] in ("repair", "pending") and r.get("successor") == task for r in rows):
        L.fail("consumption-repair-unbound", f"--require-closed: no repair or pending row of {rec} names successor {task} (review r14 L5)")
    consumed = st["consumed"]                                                                                                   # (page, finding) -> bool
    page_info = {}
    for pg in pages:
        prs = by_page[pg]
        pth = resolve(pg)
        try:
            text = read_text(pth)
        except OSError:
            L.fail("consumption-page-unparsed", f"page {pg}: cannot be read")
            page_info[pg] = None
            for f in sorted({r["finding"] for r in prs}):
                consumed[(pg, f)] = False
            for r in prs:
                refuse_row(r)
            st["unbound"].append((pg, "*"))
            continue
        dig = hashlib.sha256(text.encode("utf-8")).hexdigest()
        stale = sorted({r["id"] for r in prs if r["page_sha256"] != dig})
        need, why = cons_page_findings(text)
        if stale:
            L.fail("consumption-page-stale", f"page {pg} hashes to {dig[:12]}…; rows {','.join(stale)} pin other bytes")
        if need is None:
            L.fail("consumption-page-unparsed", f"page {pg}: {why}")
        page_info[pg] = None if (stale or need is None) else (text, need)
        if page_info[pg] is None:                # R5: a stale or unparsed page leaves every finding of it unconsumed (review r14 M6)
            for f in (need or sorted({r["finding"] for r in prs})):
                consumed[(pg, f)] = False
            for r in prs:
                refuse_row(r)
            if need is None:
                st["unbound"].append((pg, "*"))
            else:
                st["unbound"] += [(pg, f) for f in need if not any(r["finding"] == f for r in prs)]
    for pg in pages:
        info = page_info.get(pg)
        if info is None:
            continue                                                                                                            # R5: every finding unconsumed
        text, need = info
        base = os.path.basename(pg)
        for r in by_page[pg]:
            if r["finding"] not in need:
                L.fail("consumption-grammar", f"row {r['id']}: {base}#{r['finding']} is no finding of the page that needs a row")
                refuse_row(r)
        for f in need:
            fr = [r for r in by_page[pg] if r["finding"] == f]
            main_rows = [r for r in fr if not (r["binding"] == "residual" and isinstance(r.get("part"), str) and r["part"].strip())]
            if not main_rows:
                L.fail("consumption-finding-unbound", f"{base}#{f}: no binding row")
                consumed[(pg, f)] = False
                st["unbound"].append((pg, f))
                for r in fr:
                    refuse_row(r)
                continue
            if len(main_rows) > 1:
                L.fail("consumption-grammar", f"{base}#{f}: rows {','.join(r['id'] for r in main_rows)} bind it; one row, plus residual rows with `part`")
                consumed[(pg, f)] = False
                for r in fr:
                    refuse_row(r)
                continue
            ok = True
            for r in fr:
                try:
                    got = cons_binding(L, a, r, f, base, text, task, authors, resolve)
                except Exit2 as e:
                    if mode != "authoring":
                        raise
                    L.fail("canonical-unavailable", f"row {r['id']} ({base}#{f}): {e}")       # R3: a refusal in authoring mode
                    got = False
                if not got:
                    refuse_row(r)
                elif r["binding"] == "pending":
                    st["pending"].append(r)
                ok = got and ok
            consumed[(pg, f)] = ok
    obj = {"schema": "dream-finding-consumption-check.v1", "record": rec, "task": task, "trust": "same-uid",
           "rows": len(rows), "pages": pages, "unconsumed": sorted(f"{os.path.basename(p)}#{f}" for (p, f), ok in consumed.items() if not ok),
           "pending": sorted({f"{os.path.basename(r['page'])}#{r['finding']}" for r in rows if r["binding"] == "pending"}),             # review r14 L6
           "repairs": L.repairs,              # each repair or pending row's canonical reading: intake state and the close gate's predicate (review r14b F2)
           "findings": L.ids()}
    return obj, st


def cons_check(a):
    """--consumption <record> --task <T> [--page <page>] [--prd-home <dir>] [--reviews <dir>] [--require-closed] [--json] (R8): R2-R5 for the record's
    pages. Exit 0 when every finding is consumed, 1 when any is not, 2 when it cannot tell (Exit2: unreadable record, no wm-asks for a repair or pending
    row, a canonical read that fails)."""
    L = Lint()
    if not a["task"]:
        usage("--consumption needs --task <T>")
    obj, st = cons_record(L, a, pages=[a["page"]] if a["page"] else [], mode="check")
    return L, obj, f"OK consumption {a['consumption']} task={a['task']} rows={len(st['rows'])}"


def cons_binding(L, a, r, f, base, page_text, task, authors, resolve):
    """R3 for one row; False (with a finding) when it does not bind."""
    rid, b = r["id"], r["binding"]

    def bad(fid, why):
        L.fail(fid, f"row {rid} ({base}#{f}): {why}")
        return False
    req = CONS_KEYS[b][0]
    missing = [k for k in req if r.get(k) in (None, "", [])]
    if missing:
        return bad("consumption-binding-invalid", "missing " + ", ".join(missing))
    if b == "requirement":
        if not a["prd_home"]:
            return bad("consumption-context-missing", "a requirement row needs --prd-home")
        prd, ac = r["prd"], r["ac"]
        if not (isinstance(prd, str) and re.fullmatch(r"PRD-[A-Za-z0-9._-]+\.md", prd)) or not isinstance(ac, int) or ac < 1:
            return bad("consumption-binding-invalid", "prd is not a PRD basename or ac is not a positive integer")
        pp = next((os.path.join(a["prd_home"], d, prd) for d in ("build-queue", "") if os.path.isfile(os.path.join(a["prd_home"], d, prd))), None)
        if not pp:
            return bad("consumption-binding-invalid", f"key prd: {prd} is not in this home")
        line = cons_ac_line(read_text(pp), ac)
        if line is None:
            return bad("consumption-binding-invalid", f"key ac: {prd} has no AC {ac}")
        if not cons_names(line, base, f):
            return bad("consumption-binding-invalid", f"key ac: AC {ac} of {prd} does not name {base}#{f}")
        if not (any(not re.fullmatch(re.escape(base) + r"#[a-z0-9:,]+", sp) for sp in re.findall(r"`([^`]+)`", line)) or "tests/" in line):   # r14 L2
            return bad("consumption-binding-invalid", f"key ac: AC {ac} of {prd} carries no backticked command and no tests/ path")
        if f == "falsifier":
            k = r.get("kill")
            if not (isinstance(k, dict) and all(isinstance(k.get(x), str) and k[x] for x in ("script", "sha256", "string"))):
                return bad("consumption-binding-not-discriminating", "a falsifier row needs kill = {script, sha256, string}")
            want, want_sha = cons_page_falsifier(page_text)
            if want is None:
                return bad("consumption-binding-not-discriminating", "key kill: the page names no falsifier script")
            if k["script"] != want or (want_sha and k["sha256"] != want_sha):
                return bad("consumption-binding-invalid", f"key kill: {k['script']} is not the page's own falsifier {want}")
            if file_sha(resolve(k["script"])) != k["sha256"]:
                return bad("consumption-binding-invalid", f"key kill: {k['script']} does not hash to its sha256")
            if os.path.basename(k["script"]) not in line or k["string"] not in line:
                return bad("consumption-binding-not-discriminating", f"key kill: AC {ac} of {prd} does not carry the script's basename and the kill string")
            rx = r.get("reexpression")
            if rx is not None:
                if not (isinstance(rx, dict) and isinstance(rx.get("script"), str) and isinstance(rx.get("sha256"), str) and not os.path.isabs(rx["script"])):
                    return bad("consumption-binding-invalid", "key reexpression: not {script, sha256} with a path under the PRD home")
                rxp = os.path.realpath(os.path.join(a["prd_home"], rx["script"]))
                if os.path.commonpath([rxp, os.path.realpath(a["prd_home"])]) != os.path.realpath(a["prd_home"]):         # review r14 L4
                    return bad("consumption-binding-invalid", "key reexpression: the script is not under the PRD home")
                if file_sha(rxp) != rx["sha256"] or os.path.basename(rx["script"]) not in line:
                    return bad("consumption-binding-invalid", "key reexpression: the script does not hash to its sha256 or AC does not carry its basename")
        elif not (isinstance(r.get("control"), str) and r["control"].strip()):
            return bad("consumption-binding-not-discriminating", "a mechanism row needs the control its AC's test runs")
        return True
    if b == "test":
        if not (isinstance(r["commit"], str) and CONS_HEX40.fullmatch(r["commit"])):
            return bad("consumption-binding-invalid", "key commit: not 40 hex")
        obj = f"{r['commit']}:{r['path']}"
        try:                                                                    # R3 `git cat-file`, and a blob, never a tree (review r14 L3)
            t = subprocess.run(["git", "-C", resolve(r["repo"]), "cat-file", "-t", obj], capture_output=True, text=True, timeout=60)
            p = subprocess.run(["git", "-C", resolve(r["repo"]), "cat-file", "blob", obj], capture_output=True, text=True, timeout=60) \
                if t.returncode == 0 and t.stdout.strip() == "blob" else t
        except (OSError, subprocess.SubprocessError) as e:
            return bad("consumption-binding-invalid", f"key path: git cat-file failed ({e})")
        if t.returncode != 0 or t.stdout.strip() != "blob" or p.returncode != 0:
            return bad("consumption-binding-invalid", f"key path: {r['path']} is not a file in {r['repo']} at {r['commit'][:12]}")
        if not cons_names(p.stdout, base, f):
            return bad("consumption-binding-invalid", f"key path: {r['path']} does not name {base}#{f}")
        return True
    if b == "residual":
        rx, ph = routing_evidence_rules()
        ev = r["evidence"]
        if not isinstance(ev, list) or not ev or not all(isinstance(e, str) and rx.match(e) and e.split(":", 1)[-1].lower() not in ph for e in ev):
            return bad("consumption-binding-invalid", "key evidence: refs must match the routing policy's ref_pattern and name no placeholder")
        if "part" in r and not (isinstance(r["part"], str) and r["part"].strip()):
            return bad("consumption-binding-invalid", "key part: empty")
        if not a["reviews"]:
            return bad("consumption-context-missing", "a residual row needs --reviews")
        acc = r["accepted_by"]
        if a.get("drows") is not None:                  # authoring mode: the decisions rows the log check already read
            drows = a["drows"]
        else:
            dec = a["decisions"] or default_decisions()
            if not os.path.isfile(dec):
                return bad("consumption-context-missing", f"no decisions log at {dec} to find {acc}'s review launch row")
            drows, _ = load_decisions(dec)
        dream = [x for x in drows if x.get("decision") == "launch" and x.get("skill") == "dream" and x.get("task_id") == task and x.get("session")]
        lineage = (set(authors) | set(a.get("lineage") or ())                    # authoring mode: the entry's Route session is an author too
                   | {x["session"] for x in dream if x.get("role", "author") == "author"})    # the R4 lineage (role author or none)
        m4 = [x for x in dream if x["session"] == acc]
        if not m4 or m4[-1].get("role") != "review" or acc in lineage:                  # review r14 M3: the latest dream launch row, bind_reviews' rule
            return bad("consumption-residual-unaccepted", f"accepted_by {acc}: no review launch row under {task} outside the author lineage "
                                                          f"(its latest dream launch row under {task} must be role review)")
        if not cons_accepts_line(a["reviews"], acc, rid, drows, task):
            return bad("consumption-residual-unaccepted", f"accepted_by {acc}: no verdict file under {a['reviews']} naming it holds `accepts {rid}`")
        return True
    # repair, pending: the canonical ledger (R3)
    if not (isinstance(r["ask"], str) and CONS_ASK_RE.fullmatch(r["ask"])) or not (isinstance(r["successor"], str) and CONS_ASK_RE.fullmatch(r["successor"])):
        return bad("consumption-binding-invalid", "ask and successor are canonical ids A<digits>")
    if b == "pending":
        due = parse_iso(r["due"]) if isinstance(r["due"], str) else None
        if due is None:
            return bad("consumption-binding-invalid", "key due: not an ISO timestamp")
        if due < datetime.datetime.now(datetime.timezone.utc):
            try:                         # review r15 M1: an overdue row holds no slug only when its successor's ledger gate is verified
                g = cons_ledger_gate(a, r, base, f)
                if g["bound"] and g["ok"] and g["succ_open"]:
                    L.gated.add(id(r))
            except Exit2:
                pass
            return bad("consumption-pending-overdue", f"due {r['due']} has passed")
    g = cons_ledger_gate(a, r, base, f)
    ask = g["ask"]
    if not g["bound"]:
        return bad("consumption-repair-unbound", f"ask {r['ask']} (owner {r['owner']}, naming {base}#{f}) and successor {r['successor']} "
                                                 f"(closes-after=row:{r['ask']}) are not both in the canonical ledger as bound")
    ev = cons_wm_asks(["events", r["ask"], "--json"]) or []
    istate = cons_intake_state(ev)
    satisfied = cons_satisfied(ask, istate)
    L.repairs.append({"row": r["id"], "ask": r["ask"], "successor": r["successor"], "intake_state": istate,         # review r14c L2: every bound row read
                      "status": ask.get("status") or ask.get("section"), "satisfied": satisfied})
    if not g["ok"]:
        return bad("consumption-repair-unproven", f"successor {r['successor']}'s done-check (or a closes-after row's) does not run dream-run-note-lint.sh "
                                                  f"--consumption {os.path.basename(a['consumption'])} --task {r['successor']} --require-closed: "
                                                  + "; ".join(g["whys"]))
    if g["succ_open"]:                   # R7: the ledger gate holds the successor (its done-check runs this lint) while it is open, so this row holds no
        L.gated.add(id(r))               # slug unless it names prd; a closed successor holds nothing (review r15b LOW 1)
    if istate == "cancelled":            # the close gate's predicate (Hermes H5 reading 6, chain review 11 R11-F2): a cancelled repair never satisfies
        return bad("consumption-repair-unproven", f"repair ask {r['ask']} was intake-cancelled; a cancelled repair never satisfies its successor")
    acc = [cons_detail(e) for e in ev if isinstance(e, dict) and e.get("op") == "accept"]
    proved = any(x.get("result") == "FAIL" and any(y.get("result") == "PASS" and y.get("sha") == x.get("sha") and y.get("mode") == "run"
                                                  for y in acc[i + 1:]) for i, x in enumerate(acc))
    if satisfied and not proved:
        return bad("consumption-repair-unproven", f"closed repair ask {r['ask']} shows no accept FAIL followed by a run PASS at one sha")
    if not g["succ_open"] and not (b == "repair" and satisfied):
        return bad("consumption-repair-unproven", f"successor {r['successor']} is closed, cancelled or intake-accepted while this {b} row is "
                                                  f"{'open' if b == 'repair' else 'pending'}: its done-check holds nothing any more")
    if not a["require_closed"] or r["successor"] != task:
        return True
    if b == "pending":
        return bad("consumption-repair-open", f"pending row for successor {task}: unconsumed until a revision replaces it")
    if not satisfied:
        return bad("consumption-repair-open", f"repair ask {r['ask']} is still open (neither closed nor intake-accepted)")
    return True


def cons_ledger_gate(a, r, base, f):
    """R3's canonical reads for a repair or pending row: `bound` when the ask and the successor are in the canonical ledger as bound (the ask owned by
    `owner` and naming `<base>#<f>`, the successor's text carrying closes-after=row:<ask>; review r14 M2), and `ok` when the successor's done-check, or
    the check of a row its text names in closes-after=row:, runs this lint on this record for the successor with --require-closed (review r14 M1; `whys`
    each checked row's reason); `succ_open` when the successor is neither closed, intake-cancelled nor intake-accepted (a closed or cancelled successor's
    done-check never runs again, reviews r15b LOW 1 and r15c M1: cons_satisfied alone reads a cancelled row as unsatisfied, which is right for a repair
    ask but not for a successor). Raises Exit2 when a canonical read cannot be made (canonical-unavailable)."""
    got = cons_wm_asks(["query", "--ids", f"{r['ask']},{r['successor']}", "--status", "all", "--json"])
    if got is None:
        raise Exit2(f"canonical-unavailable: wm-asks is not installed here; row {r['id']} ({r['binding']}) needs the canonical ledger")
    byid = {x.get("ask_id") or x.get("id"): x for x in got if isinstance(x, dict)}
    ask, succ = byid.get(r["ask"]), byid.get(r["successor"])
    closes = [i for m in CONS_TOKEN_RE.finditer((succ or {}).get("what") or "") if m.group(1) == "closes-after" for i in m.group(2).split(",") if i]
    g = {"ask": ask, "succ": succ, "bound": False, "ok": False, "whys": [], "succ_open": False}
    if not ask or not succ or (ask.get("owner") != r["owner"]) or not cons_names(ask.get("what") or "", base, f) or r["ask"] not in closes:
        return g
    g["bound"] = True
    si = cons_intake_state(cons_wm_asks(["events", r["successor"], "--json"]) or [])
    g["succ_open"] = si != "cancelled" and not cons_satisfied(succ, si)   # reviews r15b LOW 1, r15c M1: a cancelled successor is closed (its check never runs)
    ok, why = cons_runs_lint(succ.get("check"), a["consumption"], r["successor"])
    if not ok:
        g["whys"].append(f"successor {r['successor']}: {why}")
        for x in cons_wm_asks(["query", "--ids", ",".join(closes), "--status", "all", "--json"]) or []:
            if isinstance(x, dict):
                ok2, why2 = cons_runs_lint(x.get("check"), a["consumption"], r["successor"])
                ok = ok or ok2
                g["whys"].append(f"closes-after row {x.get('ask_id') or x.get('id')}: {why2}")
    g["ok"] = ok
    return g


def cons_detail(e):
    d = e.get("detail")
    try:
        d = json.loads(d) if isinstance(d, str) else d
    except ValueError:
        d = {}
    return d if isinstance(d, dict) else {}


def cons_intake_state(events):
    """The intake state of a canonical row, read from its own events in order (`wm-asks asks query --json` does not carry it), as swarm-decide's intake
    writes it: `add` (its `state`), `transition` (`to`), `accepted`, `cancel` (cancelled), the intake claim (claimed, from ready), `release` (ready),
    `release-unknown` (blocked) and `enabled` (draft to ready). `accepted` and `cancelled` are terminal, as in the store: no writer moves a row out of them
    (intake EDGES; claim_task needs ready, a correction or cancel draft or ready), so later events are not read (review r14b F2). A plain `asks claim`
    writes its stamp under `claim` and leaves the state, so only a claim without it is the intake claim. None for a row the intake never touched."""
    st = None
    for e in events:
        if st in ("accepted", "cancelled"):
            break
        if not isinstance(e, dict):
            continue
        op, d = e.get("op"), cons_detail(e)
        if op == "add" and isinstance(d.get("state"), str):
            st = d["state"]
        elif st is None:
            continue                                     # a row the intake never created keeps no intake state (it reads 'legacy' in the store)
        elif op == "transition" and isinstance(d.get("to"), str):
            st = d["to"]
        elif op == "accepted":
            st = "accepted"
        elif op == "cancel":
            st = "cancelled"
        elif op == "claim" and "claim" not in d and st == "ready":
            st = "claimed"
        elif op == "release":
            st = "ready"
        elif op == "release-unknown":
            st = "blocked"
        elif op == "enabled" and st == "draft":
            st = "ready"
    return st


def cons_satisfied(ask, istate):
    """The close gate's predicate, owned by PRD-swarm-decide-asks-waits-on-close-gate R1 and R4 (Hermes H5 reading 6; chain review 11 R11-F2): a bound
    row is satisfied when it is closed or currently intake-accepted, and never when intake-cancelled (a cancelled row reads closed)."""
    if istate == "cancelled":
        return False
    return (ask.get("status") or ask.get("section")) in ("closed", "done") or istate == "accepted"


def cons_accepts_line(reviews, session, rid, rows, task):
    """A verdict file under --reviews that is the session's own and holds the line `accepts <rid>` (R3 residual). A file is credited to one session: of
    the dream-launched sessions its first lines name as whole tokens (this Task's first), the one launched latest, each session dated by its FIRST launch
    row under this Task (rows of other Tasks only for a session with none here; review r14c L1), so a resumed author does not take a later review's file
    (review r14b L-a). Unlike failure_floor, author-lineage sessions take part: a file that
    a role-less or author session wrote and that names a review session is that lineage session's, never the review's (review r14 M4: a re-review that
    names an earlier review's session never counts for it). A file that names a session launched after its own is credited to that later session, which
    fails closed."""
    first, tasks = {}, {}                 # session -> (has a ts, ts) of its earliest launch row; session -> the Tasks its launch rows name
    for here in (True, False):            # review r14c L1: a session's earliest launch under this Task; its other Tasks' rows only when it has none here
        for x in rows:
            if x.get("decision") == "launch" and x.get("skill") == "dream" and isinstance(x.get("session"), str) and x["session"]:
                tasks.setdefault(x["session"], set()).add(x.get("task_id"))
                if (x.get("task_id") == task) != here or (not here and task in tasks[x["session"]]):
                    continue
                t = parse_iso(x.get("ts") or "")
                k = (t is not None, t.timestamp() if t else 0.0)
                if x["session"] not in first or (k[0], -k[1]) > (first[x["session"]][0], -first[x["session"]][1]):
                    first[x["session"]] = k
    for d, ds, files in os.walk(reviews):
        ds.sort()
        for fn in sorted(files):
            try:
                t = read_text(os.path.join(d, fn))
            except (OSError, UnicodeDecodeError):
                continue
            head = "\n".join(t.split("\n")[:PAGE_LINES])
            named = [s for s in first if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(s), head)]
            named = [s for s in named if task in tasks[s]] or named
            if named and max(named, key=lambda s: (first[s], s)) == session and any(l.strip() == f"accepts {rid}" for l in t.split("\n")):
                return True
    return False


CONS_CHECK_REFUSED = re.compile(r"[;&|()<>`$'\"\\{}*?\[\]!\n\r]|(?:^|\s)#")
CONS_CHECK_ASCII = re.compile(r"[ -~]+")                    # review r14c M1: printable ASCII only, so a word ends only at a space, as bash splits it
CONS_DURATION = re.compile(r"[0-9]+(\.[0-9]+)?[smhd]?")
CONS_SIGNAL = re.compile(r"[A-Za-z0-9]+")
CONS_TIMEOUT_FLAG = re.compile(r"--kill-after=[0-9]+(\.[0-9]+)?[smhd]?|--signal=[A-Za-z0-9]+|--preserve-status|--foreground|-v|--verbose")
CONS_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")    # review r14d LOW 1: a first word bash reads as an assignment, not as the command
CONS_BASH = ("bash", "/bin/bash", "/usr/bin/bash")              # review r14d LOW 2: the lint's bootstrap needs bash (`sh` is dash here)


def cons_check_path(w):
    """A path word of a done-check as the close gate's runner sees it: `~` expanded, a relative path taken from HOME (asks._run_check runs `bash -c` there)."""
    p = os.path.expanduser(w)
    return os.path.realpath(p if os.path.isabs(p) else os.path.join(os.path.expanduser("~"), p))


def cons_runs_lint(check, record, successor):
    """R3 (reviews r14 M1, r14b F1): the done-check is ONE plain command that runs this lint and nothing else, `[timeout [-k N|-s SIG|--…] N] [bash]
    <path to dream-run-note-lint.sh> <args>`: no quote, escape, operator, redirection, grouping, substitution, variable, glob, brace, `!` or comment, so the
    words bash runs are the words read here (a check that could exit 0 without the lint gating it binds nothing). Review r14d: the first word is no shell
    assignment (`FOO=x/dream-run-note-lint.sh` makes bash run the next word), and the runner is bash, never sh (the lint's bootstrap reads
    ${BASH_SOURCE[0]}, so under dash it fails whatever the record says). Review r14c M1: the text is printable
    ASCII and its words are split at spaces only, as bash splits them (no tab, no other whitespace); `~` only as a `~/` prefix (bash's other tilde forms,
    such as `~+`, expand to other directories); timeout takes only -k N, -s SIG, --kill-after=N, --signal=SIG, --preserve-status, --foreground, -v or
    --verbose before its duration (`--help` and `--version` exit 0 without running anything). The lint is named by a path (`~/`, absolute, or relative to
    HOME, where the close gate runs a check) to an existing file that is this lint (the same file or the same bytes), and the lint's own parser reads
    <args> as this mode with --consumption = this record, --task = the successor and --require-closed (a repeated flag counts as the parser takes it:
    the last value). -> (True, None) | (False, why)."""
    text = check if isinstance(check, str) else ""
    if not text.strip():
        return False, "it has no done-check"
    if not CONS_CHECK_ASCII.fullmatch(text) or CONS_CHECK_REFUSED.search(text):
        return False, ("it is not one plain command (printable ASCII words split by spaces; no tab, other whitespace, quote, escape, operator, redirection, "
                       "grouping, substitution, variable, glob, brace, ! or comment)")
    toks, i = [w for w in text.split(" ") if w], 0
    if any(w.startswith("~") and not w.startswith("~/") for w in toks):
        return False, "a word starts with a `~` form other than `~/`"
    if CONS_ASSIGNMENT.match(toks[0]):
        return False, f"its first word {toks[0]} is a shell assignment (bash runs the next word as the command)"
    if toks[0] == "timeout":
        i = 1
        while i < len(toks) and toks[i].startswith("-"):
            if toks[i] in ("-k", "-s") and i + 1 < len(toks) and (CONS_DURATION if toks[i] == "-k" else CONS_SIGNAL).fullmatch(toks[i + 1]):
                i += 2
            elif CONS_TIMEOUT_FLAG.fullmatch(toks[i]):
                i += 1
            else:
                return False, f"its timeout option {toks[i]} is not -k N, -s SIG, --kill-after=N, --signal=SIG, --preserve-status, --foreground, -v or --verbose"
        if i >= len(toks) or not CONS_DURATION.fullmatch(toks[i]):
            return False, "its timeout has no duration"
        i += 1
    if i < len(toks) and toks[i] in ("sh", "/bin/sh", "/usr/bin/sh"):
        return False, f"it runs the lint under {toks[i]}; the lint needs bash, so that check fails whatever the record says"
    if i < len(toks) and toks[i] in CONS_BASH:
        i += 1
    if i >= len(toks) or os.path.basename(toks[i]) != "dream-run-note-lint.sh" or "/" not in toks[i]:
        return False, "its command is not a path to dream-run-note-lint.sh"
    lint = cons_check_path(toks[i])
    me = os.path.realpath(sys.argv[0]) if sys.argv and sys.argv[0] else ""
    try:
        same = os.path.isfile(lint) and (lint == me or open(lint, "rb").read() == open(me, "rb").read())
    except OSError:
        same = False
    if not same:
        return False, f"{toks[i]} is not this lint (missing, or other bytes)"
    try:
        pa = parse_args(toks[i + 1:])
    except Exit2:
        return False, "the lint refuses its arguments"
    if pa["selftest"] or any(pa[k] not in (None, False) for k in ("log", "entry", "prd_dir", "matrix", "states", "scope_id", "edges", "prds",
                                                                   "scope_roots")):
        return False, "it runs another mode of the lint"
    if not pa["consumption"] or cons_check_path(pa["consumption"]) != os.path.realpath(record):
        return False, f"its --consumption is not {record}"
    if pa["task"] != successor:
        return False, f"its --task is {pa['task']}, not {successor}"
    if pa["require_closed"] is not True:
        return False, "it lacks --require-closed"
    return True, None


def main(argv):
    try:
        a = parse_args(argv)
        if a["selftest"]:
            return selftest()
        if a["consumption"] is not None or any(a[k] not in (None, False) for k in ("task", "page", "prd_home", "reviews", "require_closed")):
            if a["consumption"] is None or any(a[k] not in (None, False) for k in ("log", "entry", "prd_dir", "matrix", "states", "scope_id", "edges", "prds",
                                                                                   "scope_roots")):
                usage("--consumption <record> --task <T> goes with --page, --prd-home, --reviews, --decisions, --require-closed and --json only")
            L, obj, ok = cons_check(a)
            text = [f"FAIL {fid}: {d}" for fid, d in L.findings] or [ok]
            out = sys.stderr if a["json"] else sys.stdout
            for t in text:
                print(t, file=out)
            if a["json"]:
                print(json.dumps(obj, separators=(",", ":")))
            return 1 if L.findings else 0
        if a["scope_id"] is not None:
            if any(a[k] not in (None, False) for k in ("log", "entry", "prd_dir", "decisions", "matrix", "states", "json",
                                                       "edges", "prds", "scope_roots")):
                usage("--scope-id takes one manifest path and nothing else")
            return scope_id_mode(a["scope_id"])
        if a["edges"] is not None or a["prds"] is not None:
            if a["edges"] is None or any(a[k] not in (None, False) for k in
                                         ("log", "entry", "prd_dir", "decisions", "matrix", "states", "scope_id", "scope_roots")):
                usage("--edges takes one edges file, --prds <PRD basename ...> and --json, without a log, "
                      "--matrix or --scope-id")
            L, obj, ok = edges_mode(a)
        elif a["matrix"] is not None or a["states"] is not None:
            if a["matrix"] is None or a["states"] is None or a["log"] is not None or a["scope_roots"] is not None:
                usage("--matrix and --states go together, without a log or --scope-root")
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
FX_FINDINGS = "\n# Weakest link\n\nThe fixture's weakest link.\n\n# Mechanisms\n\n1. fixture mechanism — state LIVE\n"   # finding consumption R5: one finding
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
            "visions/wwhtbt.md": f"# wwhtbt page\nanswered_by: fable\nsession: {S_W}\n" + FX_FINDINGS,
            "visions/5whys.md": f"# five whys page\nsession: {S_5}\n" + FX_FINDINGS,
            "notes/reviews/r1.txt": "foo APPROVE fable\n",
            M_REL: mx_file(["foo"]),
        }
        self.prev_entry = None
        self.prev_lines = ["Contract: x"]   # the earlier entry's lines (trigger-record cases give it a Task:, State: and Seeds:)
        self.ts = E_TS               # the entry's header timestamp (trigger-record cases date it on or after TRIGGER_CUTOVER)
        self.seeds = "Seeds: selftest"
        self.failure = None          # a Failure: line (trigger-record R4), after the record lines
        self.tail = []               # lines after the five record lines (a Mission: line)
        self.git = False
        self.mtimes = {}
        # finding consumption R1 (entries on or after the cutover): `consume` writes a record binding every finding of each page the Analysis: line
        # binds, by `test` rows in a scratch repository (cons-repo) whose file names them; `cons_rows` replaces it with these rows; `cons_line` is the
        # entry's Consumption: line as written ("" for none)
        self.consume = True
        self.cons_rows = None
        self.cons_line = None
        self.path = None             # a directory put first on PATH (a scenario `wm-asks`)
        self.no_asks = False         # PATH without any `wm-asks` (finding consumption: canonical-unavailable)

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
        cons = self.write_consumption()
        lines = ["# dream log (selftest)", ""]
        if self.prev_entry:
            lines += [f"## {self.prev_entry}  /dream  vision-earlier"] + list(self.prev_lines) + [""]
        lines += [f"## {self.ts}  /dream  vision-selftest", "Contract: /x/build-contract.md   Hooks: dream.lint",
                  self.seeds, "Lineage: greenfield", "Drafted: PRD-foo.md   Build order: foo",
                  "Lint: clean   Eligibility: pending scan"]
        for k in KINDS:
            v = self.entry.get(k)
            if v is None:
                continue
            lines += v if isinstance(v, list) else [v]
        lines += ([self.failure] if self.failure else []) + ([cons] if cons else []) + self.tail + ["Open questions: none", ""]
        os.makedirs(os.path.join(self.home, "notes"), exist_ok=True)
        with open(os.path.join(self.home, "notes", "dream-log.md"), "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
        return self

    CONS_REL = "notes/consumption/fx.jsonl"

    def write_consumption(self):
        """Write the entry's consumption record (finding-consumption R1) from the pages as they are on disk; call again after editing a page the
        record binds. -> the Consumption: line, or None."""
        if self.cons_line is not None:
            line = self.cons_line or None
        elif self.cons_rows is not None:
            line = "Consumption: " + self.CONS_REL
        elif not self.consume or not after_cutover(self.ts):
            return None
        else:
            line = None
        rows = self.cons_rows
        if rows is None:
            pages = cons_entry_pages(parse_analysis(self.entry.get("Analysis") or "", extended=True)[0])
            texts = {}
            for pg in pages:
                full = pg if os.path.isabs(pg) else os.path.join(self.home, pg)
                try:
                    texts[pg] = read_text(full)
                except OSError:
                    return line
                if cons_page_findings(texts[pg])[0] is None:
                    return line
            if not pages:
                return line
            names = ", ".join(f"{os.path.basename(pg)}#{','.join(cons_page_findings(texts[pg])[0])}" for pg in pages)
            repo, commit = self.cons_repo(f"# binds {names}\n")
            rows = [{"id": f"fx-c{i}-{n}", "page": pg, "page_sha256": hashlib.sha256(texts[pg].encode("utf-8")).hexdigest(), "finding": f,
                     "binding": "test", "author_session": S_D, "repo": repo, "commit": commit, "path": "tests/cons.sh"}
                    for i, pg in enumerate(pages) for n, f in enumerate(cons_page_findings(texts[pg])[0])]
            line = line or "Consumption: " + self.CONS_REL
        p = os.path.join(self.home, self.CONS_REL)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in rows))
        return line

    def cons_repo(self, text):
        """A scratch git repository beside the home whose tests/cons.sh holds text; -> (path, 40-hex commit)."""
        repo = os.path.join(self.root, "cons-repo")
        env = dict(os.environ, HOME=self.root, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="selftest", GIT_AUTHOR_EMAIL="selftest@invalid",
                   GIT_COMMITTER_NAME="selftest", GIT_COMMITTER_EMAIL="selftest@invalid")
        os.makedirs(os.path.join(repo, "tests"), exist_ok=True)
        with open(os.path.join(repo, "tests", "cons.sh"), "w", encoding="utf-8") as fh:
            fh.write(text)
        cmds = ([["init", "-q"]] if not os.path.isdir(os.path.join(repo, ".git")) else []) + [["add", "-A"], ["commit", "-q", "--allow-empty", "-m", "fixture"]]
        for c in cmds:
            subprocess.run(["git", "-C", repo] + c, check=True, capture_output=True, env=env)
        return repo, subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], check=True, capture_output=True, text=True, env=env).stdout.strip()

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

    def fx_env(fx):
        if not getattr(fx, "path", None) and not getattr(fx, "no_asks", False):
            return env
        dirs = env.get("PATH", "/usr/bin:/bin").split(os.pathsep)
        if fx.no_asks:
            dirs = [d for d in dirs if not os.path.exists(os.path.join(d, "wm-asks"))]
        return dict(env, PATH=os.pathsep.join(([fx.path] if fx.path else []) + dirs))

    def run(fx, *extra, decisions=True, js=True):
        args = [script, os.path.join(fx.home, "notes", "dream-log.md"), "--last", "--prd-dir", fx.home]
        if decisions:
            args += ["--decisions", fx.dec]
        if js:
            args.append("--json")
        args += list(extra)
        p = subprocess.run(["bash"] + args, capture_output=True, text=True, env=fx_env(fx), timeout=120)
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

    # generation-aware mission records (PRD-dream-generation-aware-mission-records), R1 and R4: the
    # selftest's headers carry no `matrix` and its entries are dated before LEGACY_MATRIX_SINCE.
    # R1: a scope manifest listing one other matrix (not the adversarial= one), valid at its listed
    # digest, passes; listing two is refused as installed. R4: a path entry moved between m1 and m2
    # passes with its delta record; undeclared, or named by a row without delta, it is refused.
    OLDMX = ("2026-11-15T00:30:00-08:00-adversarial.md", "2026-11-15T00:20:00-08:00-adversarial.md")

    def legacy(fx, n):
        fx = bound(fx, scope="notes/snapshots/m0.sha256,notes/snapshots/m.sha256")
        keep = [ln for ln in fx.files["notes/snapshots/m.sha256"].splitlines() if not ln.endswith(MXB)]
        for b in OLDMX[:n]:
            fx.files["notes/snapshots/" + b] = mx_file(["foo", "bar"])
        fx.files["notes/snapshots/m0.sha256"] = "".join(
            ln + "\n" for ln in keep + [f"{h(mx_file(['foo', 'bar']).encode())}  {b}" for b in OLDMX[:n]])
        return fx
    passes("dgmr-legacy-one-matrix", legacy(new(), 1))
    refuse("dgmr-legacy-two-matrices", legacy(new(), 2), "mission-scope-incomplete", ["notes/snapshots/m0.sha256", MXB])
    GP, GV1, GV2 = "../../data/g/graph.json", b'{"v": 1}\n', b'{"v": 2}\n'

    def bsid(t):                # the scope id over basenames, as scope_canon computes it
        return h("".join(sorted({ln.split("  ", 1)[0] + "  " + ln.split("  ", 1)[1].rsplit("/", 1)[-1] + "\n"
                                 for ln in t.splitlines()})).encode())

    def pathed(fx, row):
        fx = repaired(fx, rows=(row,))
        fx.files["data/g/graph.json"] = GV2.decode()
        for rel, v in (("notes/snapshots/m1.sha256", GV1), ("notes/snapshots/m2.sha256", GV2)):
            fx.files[rel] += f"{h(v)}  {GP}\n"
        fx.rows[4] = dict(fx.rows[4], scope_id=bsid(fx.files["notes/snapshots/m1.sha256"]))
        fx.rows[5] = dict(fx.rows[5], scope_id=bsid(fx.files["notes/snapshots/m2.sha256"]))
        return fx
    passes("dgmr-path-entry-declared", pathed(new(), dict(ROW, changed=["PRD-foo.md", GP], delta={
        "changed": [{"path": GP, "before": h(GV1), "after": h(GV2)}]})))
    refuse("dgmr-path-entry-undeclared", pathed(new(), ROW), "repair-hash-mismatch", [GP, "changed but undeclared"])
    refuse("dgmr-path-entry-no-delta", pathed(new(), dict(ROW, changed=["PRD-foo.md", GP])), "repair-hash-mismatch",
           [GP, "needs its delta record"])

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

    # ---------- trigger record (PRD-dream-analysis-trigger-record): one datr-<case> line per R2-R5 refusal, with passing twins
    T_TS = TRIGGER_CUTOVER + "T02:00:00-08:00"
    OUT_TS, LATE_TS = TRIGGER_CUTOVER + "T00:30:00-08:00", TRIGGER_CUTOVER + "T01:00:00-08:00"
    S_F = "bbbbbbbb-0000-4000-8000-000000000009"
    pol = os.path.join(top, "fxpolicy.json")
    with open(pol, "w", encoding="utf-8") as fh:
        json.dump({"evidence": {"ref_pattern": "^(ledger|file|pr|run|commit|page):[^\\s]{2,200}$", "placeholders": ["none", "n/a", "tbd", "todo", "x"]}}, fh)
    env["SKILL_ROUTING_POLICY"] = pol
    AN = "Analysis: wwhtbt={w} 5whys={f} adversarial=" + M_REL + " uncovered=1"

    def tfx(w="ran visions/wwhtbt.md", f="skipped: not a failure seed", failure="Failure: none"):
        fx = new()
        fx.ts, fx.failure = T_TS, failure
        fx.entry["Analysis"] = AN.format(w=w, f=f)
        return fx

    def denied(skill, reasons, ts=OUT_TS, task="A1"):
        return row(ts, "denied", task, skill, "opus-xhigh", "claude-opus-5-5", "xhigh", "", reasons=reasons)

    def reuse_fx(page_sha=None, input_sha=None, omit=False, inputs="notes/inputs.sha256"):
        fx = tfx()
        page = f"# wwhtbt page\ntask: A1\nsession: {S_W}\ncites file:notes/inputs/a.txt\n" + FX_FINDINGS
        fx.files["visions/wwhtbt.md"] = page
        fx.files["notes/inputs/a.txt"] = "input a\n"
        real = hashlib.sha256(b"input a\n").hexdigest()
        fx.files["notes/inputs.sha256"] = "" if omit else f"{input_sha or real}  inputs/a.txt\n"
        fx.entry["Analysis"] = AN.format(w=f"reused visions/wwhtbt.md sha256={page_sha or hashlib.sha256(page.encode()).hexdigest()} inputs={inputs}",
                                         f="skipped: not a failure seed")
        return fx

    def jcov(want):
        return lambda d: expect(d["analysis"].get("covered") == want, d["analysis"])

    passes("datr-covered-ran", tfx(), lambda d: expect(d["analysis"]["covered"] == "new-material" and d["analysis"]["failure"] == {"class": "none", "refs": []}, d["analysis"]))
    refuse("datr-skip-free-text", tfx(w="skipped: a wiki page would be outside this task's scope"), "analysis-skip-refused", ("is not 'skipped: blocked decision=<ts>'",))
    fx = tfx(w=f"skipped: blocked decision={OUT_TS}")
    fx.rows.append(denied("wwhtbt", "evidence: placeholder ref refused (fixable request)"))
    refuse("datr-skip-fixable", fx, "analysis-skip-refused", ("not a route outage",))
    fx = tfx(w=f"skipped: blocked decision={OUT_TS}")
    fx.rows += [denied("wwhtbt", "policy file not found"), row(LATE_TS, "launch", "A9", "wwhtbt", "opus-xhigh", "claude-opus-5-5", "xhigh", S_F)]
    refuse("datr-skip-uncorroborated", fx, "analysis-skip-refused", ("not corroborated",))
    fx = tfx(w=f"skipped: blocked decision={OUT_TS}")
    fx.rows.append(denied("wwhtbt", "policy file not found"))
    passes("datr-skip-corroborated", fx, jcov("new-material"))
    fx = tfx(w=f"skipped: blocked decision={OUT_TS}")
    fx.rows.append(denied("wwhtbt", "policy-missing: SKILL_ROUTE_POLICY names no readable file"))
    refuse("datr-skip-caller-policy", fx, "analysis-skip-refused", ("not a route outage",))
    fx = new()
    fx.prev_entry, fx.prev_lines = "2026-11-15T00:30:00-08:00", ["Task: A1   Consumer: hermes", "Seeds: selftest", "State: foo=linted"]
    fx.ts = T_TS
    fx.entry["Analysis"] = AN.format(w="skipped: nothing new to plan", f="skipped: not a failure seed")
    passes("datr-uncovered-keeps-today", fx, jcov("none"))
    fx = reuse_fx()
    fx.entry["Analysis"] = AN.format(w="reused visions/wwhtbt.md", f="skipped: not a failure seed")
    refuse("datr-reuse-no-inputs", fx, "analysis-grammar", ("reused <page> sha256=<64 hex> inputs=<manifest>",))
    refuse("datr-reuse-empty-manifest", reuse_fx(omit=True), "analysis-grammar", ("absent or empty",))
    refuse("datr-reuse-page-moved", reuse_fx(page_sha="0" * 64), "analysis-reuse-stale", ("differs from the recorded",))
    refuse("datr-reuse-input-moved", reuse_fx(input_sha="1" * 64), "analysis-reuse-stale", ("sha256sum -c",))
    fx = reuse_fx()
    fx.files["notes/inputs.sha256"] = hashlib.sha256(b"other\n").hexdigest() + "  inputs/b.txt\n"
    fx.files["notes/inputs/b.txt"] = "other\n"
    refuse("datr-reuse-omits-cited", fx, "analysis-reuse-incomplete", ("notes/inputs/a.txt",))
    passes("datr-reuse-verified", reuse_fx(), lambda d: expect(d["analysis"]["reuse"]["verified"] is True, d["analysis"]))
    refuse("datr-failure-missing", tfx(failure=None), "line-missing", ("Failure (a covered entry",))
    refuse("datr-failure-unknown-class", tfx(failure="Failure: flaky ledger:A1"), "failure-grammar")
    refuse("datr-failure-placeholder-ref", tfx(failure="Failure: other file:tbd"), "failure-grammar", ("placeholder",))
    fx = tfx(failure="Failure: none")
    fx.rows.append(row(LATE_TS, "launch", "A1", "dream", "opus-xhigh", "claude-opus-5-5", "xhigh", S_F, role="review"))
    fx.files["notes/reviews/v-floor.md"] = f"# review\nReviewer: session {S_F}\nfoo REJECT opus\n"
    refuse("datr-failure-below-reject", fx, "failure-class-mismatch", ("below the floor failed-acceptance",))
    refuse("datr-trigger-inline", tfx(f="inline", failure="Failure: failed-acceptance ledger:A1"), "analysis-trigger-unmet")
    passes("datr-trigger-page", tfx(f="page visions/5whys.md", failure="Failure: recurring-failure ledger:A1"))
    fx = tfx(f=f"skipped: blocked decision={OUT_TS}", failure="Failure: consequential-obstacle ledger:A1")
    fx.rows += [denied("5whysandrhyme", "malformed policy JSON: JSONDecodeError"), row(LATE_TS, "launch", "A7", "5whysandrhyme", "opus-xhigh", "claude-opus-5-5", "xhigh", S_F)]
    refuse("datr-trigger-skip-uncorroborated", fx, "analysis-trigger-unmet", ("not corroborated",))
    five = f"# five whys page\nsession: {S_5}\n" + FX_FINDINGS
    fx = tfx(f=f"reused visions/5whys.md sha256={hashlib.sha256(five.encode()).hexdigest()}", failure="Failure: recurring-failure ledger:A1")
    refuse("datr-trigger-reuse-uncited", fx, "analysis-trigger-unmet", ("does not cite page:visions/5whys.md",))
    fx = tfx(f=f"reused visions/5whys.md sha256={hashlib.sha256(five.encode()).hexdigest()}", failure="Failure: recurring-failure ledger:A1 page:visions/5whys.md")
    passes("datr-trigger-reuse-cited", fx)
    refuse("datr-transient-page", tfx(f="page visions/5whys.md", failure="Failure: transient run:retry-1"), "analysis-trigger-unmet", ("transient",))
    passes("datr-transient-inline", tfx(f="inline", failure="Failure: transient run:retry-1"))
    # R7's cutover instant (Q3 of A1723 source request 4; AC 7's datr-cutover-zone twin): one instant written in two zones (-08:00 and Z, Z also as
    # RFC 3339's lower-case z, review r20 F2; after the cutover also -10:00, whose date text is the day before), in the header and in a bound Route
    # row's ts, just before and just after the cutover,
    # gets one result per side: a free-text WWHTBT skip is kept before (43d5b39's output, no R6 fields) and refused after (R2)
    prev = (datetime.date.fromisoformat(TRIGGER_CUTOVER) - datetime.timedelta(days=1)).isoformat()
    zone = {"-08:00": "pst", "-10:00": "hst", "Z": "utc", "z": "utcz"}
    for side, stamps in (("before", (prev + "T23:59:59-08:00", TRIGGER_CUTOVER + "T07:59:59Z", TRIGGER_CUTOVER + "T07:59:59z")),
                         ("after", (TRIGGER_CUTOVER + "T00:00:00-08:00", TRIGGER_CUTOVER + "T08:00:00Z", TRIGGER_CUTOVER + "T08:00:00z",
                                    prev + "T22:00:00-10:00"))):
        for where in ("header", "route"):
            for ts in stamps:
                fx = tfx(w="skipped: a wiki page would be outside this task's scope")
                if where == "header":
                    fx.ts = ts
                else:                                   # a header before the cutover in every reading, its Route bound to a launch row at ts
                    fx.ts = prev + "T23:00:00-08:00"
                    fx.entry["Route"] = f"Route: fable-xhigh claude-fable-5-1 xhigh session={S_D} decision={ts}"
                    fx.rows.append(row(ts, "launch", "A1", "dream", "fable-xhigh", "claude-fable-5-1", "xhigh", S_D))
                name = f"datr-cutover-zone-{where}-{side}-{zone[ts[-1] if ts[-1] in 'Zz' else ts[-6:]]}"
                if side == "before":
                    passes(name, fx, lambda d: expect(d["analysis"] is not None and "covered" not in d["analysis"], d["analysis"]))
                else:
                    refuse(name, fx, "analysis-skip-refused", ("is not 'skipped: blocked decision=<ts>'",))

    # ---------- finding consumption (PRD-dream-finding-consumption AC 7): one dfcn-<case> line per R1-R8 refusal, each with its exact finding-id set,
    # and passing twins. The authoring cases lint a covered entry on the cutover (R9) binding visions/wwhtbt.md (falsifier plus one SPEC mechanism);
    # R3's canonical reads come from a scenario `wm-asks` printing `asks query` and `asks events` in the CLI's shapes (dfcn AC 2 and AC 5 use a real
    # temp store); the check-mode cases (R8) lint a record at the home's root.
    KILL = "#!/bin/sh\necho KILL-FX\n"
    PG = "visions/wwhtbt.md"
    page_fx = (f"# wwhtbt page\nanswered_by: fable\nsession: {S_W}\n\n# Weakest link\n\nThe falsifier `bash scripts/kill-fx.sh` prints KILL-FX.\n\n"
               "# Mechanisms\n\n1. First — state SPEC\n2. Second — state LIVE\n")
    page_bare = f"# wwhtbt page\nanswered_by: fable\nsession: {S_W}\n"

    def h(t):
        return hashlib.sha256(t.encode()).hexdigest()
    prd_foo = ("# foo\n\n## Acceptance criteria\n\n1. P0 — Given wwhtbt.md#falsifier, When `bash scripts/kill-fx.sh` runs, Then it prints `KILL-FX`.\n"
               "2. P0 — Given wwhtbt.md#falsifier, When `bash scripts/kill-fx.sh` runs, Then it prints `KILL-FX`.\n")
    FAKE = ("#!/usr/bin/env python3\nimport json, sys\nsc = json.load(open(%r))\na = sys.argv[1:]\n"
            "if a[:2] == ['asks', 'query'] and '--ids' in a:\n    ids = a[a.index('--ids') + 1].split(',')\n"
            "    print(json.dumps([r for r in sc['rows'] if r['ask_id'] in ids]))\n"
            "elif a[:2] == ['asks', 'events']:\n    print(json.dumps([dict(e, detail=json.dumps(e['detail'])) for e in sc['events'].get(a[2], [])]))\n"
            "else:\n    sys.exit('scenario wm-asks: unexpected %%s' %% a)\n")

    def crow(rid, finding, binding, page=PG, psha=None, **kw):
        r = {"id": rid, "page": page, "page_sha256": psha or h(page_fx), "finding": finding, "binding": binding, "author_session": S_D}
        r.update(kw)
        return r

    def cfx(m1=None, state=None, extra=(), drop_m1=False, page=None, fal=None):
        fx = tfx()
        fx.files[PG] = page if page is not None else page_fx
        fx.files["scripts/kill-fx.sh"] = KILL
        fx.files["built-prds/PRD-foo.md"] = None                     # a requirement row's PRD is queued (R3 reads build-queue/ or the home's root)
        fx.files["build-queue/PRD-foo.md"] = prd_foo
        if state:
            fx.entry["State"] = state
        fx.repo, fx.commit = fx.cons_repo("# binds wwhtbt.md#falsifier,mechanism:1\n")
        good_fal = crow("c-fal", "falsifier", "requirement", prd="PRD-foo.md", ac=1,
                        kill={"script": "scripts/kill-fx.sh", "sha256": h(KILL), "string": "KILL-FX"})
        good_m1 = crow("c-m1", "mechanism:1", "test", repo=fx.repo, commit=fx.commit, path="tests/cons.sh")
        fx.cons_rows = [fal or good_fal] + ([] if drop_m1 else [m1 or good_m1]) + list(extra)
        return fx

    def ledger(fx, rows, events=None):
        d = os.path.join(fx.root, "scenario-bin")
        os.makedirs(d, exist_ok=True)
        sc = os.path.join(fx.root, "scenario.json")
        with open(sc, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows, "events": events or {}}, fh)
        with open(os.path.join(d, "wm-asks"), "w", encoding="utf-8") as fh:
            fh.write(FAKE % sc)
        os.chmod(os.path.join(d, "wm-asks"), 0o755)
        fx.path = d
        return fx

    def lrows(fx, record, succ_check=None, ask_status="open"):
        chk = succ_check if succ_check is not None else f"bash {script} --consumption {record} --task A102 --require-closed"
        return [{"ask_id": "A101", "owner": "ctl", "what": "repair wwhtbt.md#mechanism:1", "status": ask_status, "check": "true"},
                {"ask_id": "A102", "owner": "hermes", "what": "successor closes-after=row:A101", "status": "open", "check": chk}]
    AREC = lambda fx: os.path.join(fx.home, "notes", "consumption", "fx.jsonl")      # noqa: E731  (the authoring record Fx writes)

    def refuse_c(name, fx, fid, detail_has=()):
        refuse(f"dfcn-{name}", fx, fid, detail_has)
    passes("dfcn-consumed", cfx(), lambda d: expect(d["consumption"]["held"] == [] and d["consumption"]["unconsumed"] == []
                                                    and d["consumption"]["record"] == "notes/consumption/fx.jsonl", d.get("consumption")))
    fx = cfx(); fx.cons_line = ""
    refuse_c("missing-record-line", fx, "consumption-missing", ("binds visions/wwhtbt.md",))
    fx = cfx(); fx.cons_line = "Consumption: ../outside.jsonl"
    refuse_c("record-outside-the-home", fx, "consumption-missing", ("is not a file under the PRD home",))
    refuse_c("grammar", cfx(extra=["not one JSON object"]), "consumption-grammar", ("is not one JSON object",))
    fx = cfx()
    fx.cons_rows[1] = crow("c-m1", "mechanism:1", "test", repo=fx.repo, commit="abc", path="tests/cons.sh")
    refuse_c("binding-invalid", fx, "consumption-binding-invalid", ("row c-m1", "key commit"))
    refuse_c("binding-not-discriminating", cfx(fal=crow("c-fal", "falsifier", "requirement", prd="PRD-foo.md", ac=1)),
             "consumption-binding-not-discriminating", ("row c-fal", "kill"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102"))
    refuse_c("repair-unbound", ledger(fx, []), "consumption-repair-unbound", ("row c-m1", "A101"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102"))
    refuse_c("repair-unproven", ledger(fx, lrows(fx, AREC(fx), succ_check="true")), "consumption-repair-unproven", ("row c-m1", "done-check"))
    # review r15b LOW 1: the ledger gate holds a successor only while it is open; a repair proved (a run FAIL then a run PASS at one sha) is consumed
    # whatever its successor's state, and an open repair or a pending row whose successor is closed is refused (and holds every State: slug)
    def lrows2(fx, ask_status, succ_status):
        rows = lrows(fx, AREC(fx), ask_status=ask_status)
        rows[1]["status"] = succ_status
        return rows
    proved = {"A101": [{"op": "accept", "detail": {"result": "FAIL", "mode": "run", "sha": "s1"}},
                       {"op": "accept", "detail": {"result": "PASS", "mode": "run", "sha": "s1"}}]}
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102"))
    passes("dfcn-a-proved-repair-whose-successor-closed-is-consumed", ledger(fx, lrows2(fx, "closed", "closed"), proved))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102"))
    refuse_c("an-open-repair-whose-successor-is-closed", ledger(fx, lrows2(fx, "open", "closed")), "consumption-repair-unproven",
             ("row c-m1", "successor A102 is closed"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask="A101", successor="A102"))
    refuse_c("a-pending-row-whose-successor-is-closed", ledger(fx, lrows2(fx, "open", "closed")), "consumption-repair-unproven",
             ("row c-m1", "successor A102 is closed"))
    # review r15c M1: an intake-cancelled successor (closed in the store, its events ending in the intake cancel) holds nothing either
    cancelled = {"A102": [{"op": "add", "detail": {"state": "ready"}}, {"op": "cancel", "detail": {}}]}
    fx = cfx(m1=crow("c-m1", "mechanism:1", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask="A101", successor="A102"))
    refuse_c("a-pending-row-whose-successor-is-cancelled", ledger(fx, lrows2(fx, "open", "closed"), cancelled), "consumption-repair-unproven",
             ("row c-m1", "successor A102 is closed, cancelled or intake-accepted"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102"))
    refuse_c("an-open-repair-whose-successor-is-cancelled", ledger(fx, lrows2(fx, "open", "closed"), cancelled), "consumption-repair-unproven",
             ("row c-m1", "successor A102 is closed, cancelled or intake-accepted"))
    refuse_c("residual-without-a-review-launch-row", cfx(m1=crow("c-m1", "mechanism:1", "residual", owner="ctl", evidence=["ledger:A1"],
                                                                accepted_by="rv-nobody")), "consumption-residual-unaccepted", ("row c-m1", "rv-nobody"))
    refuse_c("pending-overdue", cfx(m1=crow("c-m1", "mechanism:1", "pending", owner="ctl", due="2020-01-01T00:00:00+00:00", ask="A101",
                                           successor="A102")), "consumption-pending-overdue", ("row c-m1", "has passed"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102")); fx.no_asks = True
    refuse_c("canonical-unavailable-is-a-refusal-here", fx, "canonical-unavailable", ("row c-m1",))
    refuse_c("receipt-only", cfx(extra=[{"id": "c-rc", "binding": "session", "session": S_D}]), "consumption-receipt-only", ("c-rc",))
    refuse_c("finding-unbound", cfx(drop_m1=True), "consumption-finding-unbound", ("wwhtbt.md#mechanism:1",))
    fx = cfx()
    fx.cons_rows = [dict(r, page_sha256="0" * 64) if r["id"] == "c-fal" else r for r in fx.cons_rows]
    refuse_c("page-stale", fx, "consumption-page-stale", ("rows c-fal",))
    fx = cfx(page=page_bare)
    fx.cons_rows = [dict(r, page_sha256=h(page_bare)) for r in fx.cons_rows]
    refuse_c("page-unparsed", fx, "consumption-page-unparsed", ("no falsifier section",))
    refuse_c("falsifier-not-first", cfx(fal=crow("c-fal", "falsifier", "requirement", prd="PRD-foo.md", ac=2,
                                                 kill={"script": "scripts/kill-fx.sh", "sha256": h(KILL), "string": "KILL-FX"})),
             "falsifier-not-first", ("row c-fal", "AC 2"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask="A101", successor="A102", prd="PRD-foo.md"),
             state="State: foo=linted foo=reviewed:APPROVE foo=eligible")
    refuse_c("blocked", ledger(fx, lrows(fx, AREC(fx))), "consumption-blocked", ("slug foo=eligible", "row c-m1"))
    fx = cfx(m1=crow("c-m1", "mechanism:1", "pending", owner="ctl", due="2099-01-01T00:00:00+00:00", ask="A101", successor="A102"),
             state="State: foo=linted foo=reviewed:APPROVE foo=eligible")
    passes("dfcn-pending-with-a-successor-holds-no-slug", ledger(fx, lrows(fx, AREC(fx))),
           lambda d: expect(d["consumption"]["held"] == [] and d["consumption"]["pending"] == ["wwhtbt.md#mechanism:1"], d.get("consumption")))

    def check_mode(name, fx, want_rc, fid, *extra, task="A1", detail=""):
        fx.cons_line = ""
        fx.build()
        rec = os.path.join(fx.home, "record.jsonl")                 # at the home's root: without --prd-home, rows resolve against the record's directory
        with open(rec, "w", encoding="utf-8") as fh:
            fh.write("".join((r if isinstance(r, str) else json.dumps(r)) + "\n" for r in fx.cons_rows))
        p = subprocess.run(["bash", script, "--consumption", rec, "--task", task, "--json", "--decisions", fx.dec,
                            "--reviews", os.path.join(fx.home, "notes", "reviews")] + list(extra),
                           capture_output=True, text=True, env=fx_env(fx), timeout=120)
        try:
            d = json.loads(p.stdout) if p.stdout.strip() else None
        except ValueError:
            d = None
        ok = p.returncode == want_rc and (want_rc == 2 and fid in p.stderr or d is not None and d.get("findings") == ([fid] if fid else []))
        ok = ok and (not detail or detail in p.stderr)
        check(f"{'pass' if want_rc == 0 else 'refuse:' + (fid or '')}:dfcn-check-{name}", ok,
              f"rc={p.returncode} findings={d and d.get('findings')} err={p.stderr.strip()[:300]}")
    fx = cfx()
    check_mode("consumed", fx, 0, None, "--prd-home", fx.home)
    check_mode("context-missing", cfx(), 1, "consumption-context-missing", detail="needs --prd-home")
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102"))
    ledger(fx, lrows(fx, os.path.join(fx.home, "record.jsonl")))
    check_mode("repair-open", fx, 1, "consumption-repair-open", "--prd-home", fx.home, "--require-closed", task="A102", detail="still open")
    fx = cfx()
    fx.files["visions/other.md"] = page_fx
    check_mode("page-the-record-does-not-bind", fx, 1, "consumption-finding-unbound", "--prd-home", fx.home, "--page", "visions/other.md",
               detail="other.md#falsifier")
    fx = cfx(m1=crow("c-m1", "mechanism:1", "repair", ask="A101", owner="ctl", successor="A102")); fx.no_asks = True
    check_mode("canonical-unavailable-exits-2", fx, 2, "canonical-unavailable", "--prd-home", fx.home)
    env.pop("SKILL_ROUTING_POLICY", None)

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
