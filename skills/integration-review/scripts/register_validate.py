#!/usr/bin/env python3
"""Validate an integration-review register (stdlib only, read-only).

Coverage counts are derived from the enumerated records; a declared count is ignored (warned if it
differs). A register declaring "all-interfaces-complete" is REFUSED (exit 1) while any record has
role, component (endpoint/caller), installed state or version UNKNOWN, is unclassified, or a family
lacks a producer or a consumer endpoint, or evidence is older than the source identity.
Unknown-equivalents (scripts/ir_norm.py is_unknown: any case, Unicode/zero-width whitespace, trailing
punctuation, the placeholders UNK ? tbd - n/a none, empty) are UNKNOWN in every field the check reads: role,
component, host, installed_state, label, source repo and version, evidence refs, adoption refs. Complete also
needs: at least one record; loaded = adoption_evidence naming a process observation (pid, /proc/<n>, process,
cmdline, exe, lsof, fuser); an unlisted unit state is not adoption; timestamps parseable, with an explicit UTC
offset (an offset-less time is ambiguous and never read in the host zone) and not later than --now plus 300 s.
(installed needing a stated path + sha256 is an extractor rule only: a hand register states installed on the
reviewer's word; the OK line names every installed record taken on that word.) Evidence refs are never
printed (records and indexes are named); credential-shaped text in any message is redacted. A duplicate JSON
key or a non-object register is unreadable (exit 2).
usage: register_validate.py REGISTER.json [--now ISO8601-with-offset]   (exit 0 ok, 1 refused, 2 unreadable or bad --now)
"""
import importlib.util
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone


def _load_norm():
    m = sys.modules.get("ir_norm")
    if m is None:
        spec = importlib.util.spec_from_file_location("ir_norm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_norm.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.modules["ir_norm"] = m
    return m


_N = _load_norm()
is_unknown = _N.is_unknown

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schema", "register.schema.json")
COMPLETE = "all-interfaces-complete"
UNASSIGNED = "UNASSIGNED"
CRED = _N.CRED
SKEW = timedelta(seconds=300)
HEX64 = re.compile(r"[0-9a-f]{64}")
# Process-adoption rule (SKILL.md step 5): a ref is a positive observation of a running process when it states
# /proc/<n>/<exe|cmdline|comm|status|stat|cwd|fd>, or "pid" with a non-zero number plus exe/cmdline/comm/command,
# or a process-listing tool (ps, pgrep, pidof, lsof, fuser, top) with "shows|lists|reports|names|found process <name>".
# It is refused when it carries a negation or placeholder word or names a unit (systemctl, *.service, list-units):
# a tool name alone, an UNKNOWN value, "no process found", "pid=" and a unit listing are not observations.
_PROC_PATH = re.compile(r"/proc/[1-9][0-9]*/(?:exe|cmdline|comm|status|stat|cwd|fd)\b")
# a positive integer only: the separator never consumes a sign ("pid=-1" is the no-process sentinel, "pid +3",
# "pid=1e3", "pid=1.5" and "pid=0x1f" are not a pid); "pid-1" with the hyphen joined to the word is the existing
# accepted spelling.
_PID_NUM = re.compile(r"\bpid(?:[\s:=#_]*|-)[1-9][0-9]*(?![0-9a-z_]|\.[0-9])")
_PID_FACT = re.compile(r"\b(?:exe|cmdline|comm|command)\b")
_TOOL_SAYS = re.compile(r"\b(?:ps|pgrep|pidof|lsof|fuser|top)\b[^\n]*?\b(?:shows|lists|reports|names|found)\s+(?:a\s+)?process\s+(?P<n>[^\s,;]+)")
_NEGATED = _N.NEG_STATE            # the one negation rule (scripts/ir_norm.py): negations, failures and non-running process states
_UNIT = re.compile(r"\bsystemctl\b|\blist-units?\b|\blist-unit-files\b|\.(?:service|timer|socket|target|mount|path|slice|scope)\b")


def _observed_process(ref):
    t = _N.canon(ref)
    if _N.negated(ref, state=True) or _UNIT.search(t):
        return False
    if _PROC_PATH.search(t) or (_PID_NUM.search(t) and _PID_FACT.search(t)):
        return True
    m = _TOOL_SAYS.search(t)
    return bool(m) and not _unk(m.group("n"))


def _pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {_safe(k)!r}")
        seen.add(k)
    return dict(pairs)


def _safe(text):
    return _N.redact(text)


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


_unk = is_unknown     # the one shared definition, scripts/ir_norm.py


def _hk(v):
    return json.dumps(v, sort_keys=True, default=str)


def load_schema():
    with open(SCHEMA_PATH) as f:
        return json.load(f)


# ---- minimal JSON-schema subset -------------------------------------------------------------
_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


def _is(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _TYPES[t])


def _check(v, s, root, path, errs):
    if "$ref" in s:
        node = root
        for part in s["$ref"].lstrip("#/").split("/"):
            node = node[part]
        s = node
    if "type" in s:
        ts = s["type"] if isinstance(s["type"], list) else [s["type"]]
        if not any(_is(v, t) for t in ts):
            errs.append((path, f"expected type {ts}, got {type(v).__name__}"))
            return
    if "enum" in s and v not in s["enum"]:
        errs.append((path, f"{v!r} not in enum {s['enum']}"))
    if isinstance(v, str):
        if "minLength" in s and len(v) < s["minLength"]:
            errs.append((path, "empty string"))
        if "pattern" in s and not re.search(s["pattern"], v):
            errs.append((path, f"{v!r} does not match {s['pattern']}"))
    if isinstance(v, dict):
        for r in s.get("required", []):
            if r not in v:
                errs.append((path, f"missing required {r!r}"))
        props = s.get("properties", {})
        for k, sub in v.items():
            if k in props:
                _check(sub, props[k], root, f"{path}/{k}", errs)
            elif s.get("additionalProperties", True) is False:
                errs.append((path, f"unexpected property {k!r}"))
    if isinstance(v, list):
        if "minItems" in s and len(v) < s["minItems"]:
            errs.append((path, "too few items"))
        if "items" in s:
            for i, it in enumerate(v):
                _check(it, s["items"], root, f"{path}[{i}]", errs)


# ---- semantic checks ------------------------------------------------------------------------
def _ts(s):
    """(UTC datetime, "ok") | (None, "bad") unparseable | (None, "ambiguous") no UTC offset, never read in the host zone."""
    try:
        d = datetime.fromisoformat(s[:-1] + "+00:00" if s.endswith(("Z", "z")) else s)
    except (ValueError, AttributeError):
        return None, "bad"
    if d.tzinfo is None or d.utcoffset() is None:
        return None, "ambiguous"
    try:
        return d.astimezone(timezone.utc), "ok"
    except (OverflowError, OSError, ValueError):
        return None, "bad"


def _key(r):
    """Endpoint base key: the fields that name an endpoint. Whether two records with one base key are ONE endpoint
    is _conflict()'s question (the stated repos and commits), never a part of the key."""
    return tuple(_hk(r.get(k)) for k in ("family", "role", "host", "component", "path_or_command", "interface_kind"))


def _ident(r):
    """(the (canonical repo, path) endpoints the sources state, the commits they state). A source's own
    path_or_command wins over the record's (a fused record lists the path of each member; a member without one
    has none); a record with no source states a repo of None, which is not a difference."""
    own = None if r.get("fusion_basis") else r.get("path_or_command")
    srcs = [si for _, si in _sources(r)] or [{}]
    ends, commits = set(), set()
    for si in srcs:
        repo = si.get("repo")
        rid = _N.repo_id(repo) if isinstance(repo, str) and not _unk(repo) else None
        ends.add((rid, si.get("path_or_command", own)))
        cid = _N.commit_id(si.get("commit"))             # a placeholder commit is unstated, as an unstated repo is
        if cid is not None:
            commits.add(cid)
    if any(rp is not None for rp, _ in ends):
        ends = {e for e in ends if e[0] is not None}      # an unstated source beside a stated repo adds no wildcard
    return frozenset(ends), frozenset(commits)


_HEXC = re.compile(r"[0-9a-f]{7,64}")


def _same_commit(x, y):
    """One commit written two ways is not two commits (the rule is _commit_toks(), the only one): the canonical
    spellings (ir_norm.commit_id: no label such as sha: or "commit ", no zero-width character, any case) are equal or,
    when both are hex of 7+ digits, one is a prefix of the other (an abbreviated sha). An unstated commit (a
    placeholder) is the same as none and differs from nothing."""
    fx, px = _commit_toks([x])
    fy, py = _commit_toks([y])
    return bool(fx & py or fy & px)


def _conflict(a, b):
    """Two records of one base key are one endpoint (a duplicate) unless they PROVE they differ: no (repo, path)
    endpoint is shared (an unstated repo matches any repo on the same path), or both state commits and none is
    the same commit (_same_commit). A record that omits its repo or commit, or one side of a pair that does, is
    therefore never provably different, as in the extractor. This pairwise form is the definition;
    _duplicate_groups() reaches the same groups by keyed lookup."""
    (ea, ca), (eb, cb) = a, b
    if ca and cb and not any(_same_commit(x, y) for x in ca for y in cb):
        return False
    return any(pa == pb and (ra is None or rb is None or ra == rb) for ra, pa in ea for rb, pb in eb)


def _commit_toks(commits):
    """(full tokens, prefix tokens) of a record's commits (spelling normalised by ir_norm.commit_id; an unstated commit
    has none): the canonical commit, and for a hex commit of 7+ digits every prefix of 7+ digits. Two commits are the same
    commit exactly when the full token of one is a prefix token of the other, so equality of tokens finds them without
    comparing pairs; _same_commit() reads the same tokens, so this is the one commit-equality rule."""
    full, pre = set(), set()
    for c in commits:
        c = _N.commit_id(c)
        if c is None:
            continue
        full.add(c)
        if _HEXC.fullmatch(c):
            pre.update(c[:n] for n in range(7, len(c) + 1))
        else:
            pre.add(c)
    return full, pre


def _duplicate_groups(recs):
    """Groups (record lists, size > 1) of records that are one endpoint: the connected records under _conflict()
    within one base key, found by keyed lookup and never by a scan of all pairs (a union-find over: the records of
    one path, grouped by stated repo; within a repo, one hub per commit token, or every record when one states no
    commit; a record with an unstated repo is joined to the records of the path that share a commit token, or to
    all of them when it states no commit; a record stating no commit is joined to every record of its repo)."""
    by = {}
    for i, r in enumerate(recs):
        by.setdefault(_key(r), []).append(i)
    out = []
    for idx in by.values():
        if len(idx) < 2:
            continue
        parent = {i: i for i in idx}

        def find(i):
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i, j):
            parent[find(i)] = find(j)
        info = {i: _ident(recs[i]) for i in idx}
        toks = {i: _commit_toks(info[i][1]) for i in idx}
        paths = {}
        for i in idx:
            for rp, pa in info[i][0]:
                paths.setdefault(pa, []).append((i, rp))
        for ents in paths.values():
            _link_path(ents, toks, union)
        comps = {}
        for i in idx:
            comps.setdefault(find(i), []).append(i)
        out += [[recs[i] for i in c] for c in comps.values() if len(c) > 1]
    return out


def _token_index(members, toks):
    fm, pm = {}, {}
    for i in members:
        full, pre = toks[i]
        for t in full:
            fm.setdefault(t, []).append(i)
        for t in pre:
            pm.setdefault(t, []).append(i)
    return fm, pm


def _link_path(ents, toks, union):
    """Union the records of one path (entries (index, canonical repo or None)) that _conflict() relates."""
    groups, nulls = {}, []
    for i, rp in ents:
        if rp is None:
            nulls.append(i)
        else:
            groups.setdefault(rp, []).append(i)
    for g in groups.values():                       # same stated repo: related unless both state disjoint commits
        bare = [i for i in g if not toks[i][0]]
        if bare:
            for i in g:
                union(bare[0], i)
            continue
        fm, pm = _token_index(g, toks)
        for t, fl in fm.items():
            for i in pm[t]:
                union(fl[0], i)
    if not nulls:
        return
    everyone = [i for i, _ in ents]
    bare_null = [i for i in nulls if not toks[i][0]]
    if bare_null:                                   # an unstated repo with no commit is related to every record
        for i in everyone:
            union(bare_null[0], i)
        return
    bare = [i for i in everyone if not toks[i][0]]
    if bare:
        for i in bare:
            union(nulls[0], i)
        for i in nulls[1:]:
            union(i, bare[0])
    fm, pm = _token_index(everyone, toks)
    seen_p, seen_f = set(), set()
    for n in nulls:                                 # an unstated repo is related to every record sharing a commit
        full, pre = toks[n]
        for t in full:
            if t not in seen_p:
                seen_p.add(t)
                for i in pm[t]:
                    union(n, i)
        for t in pre:
            if t in fm:
                if t not in seen_f:
                    seen_f.add(t)
                    for i in fm[t]:
                        union(n, i)
                else:
                    union(n, fm[t][0])


def _rid(r, pos=None):
    """The printed name of a record: its record_id as written, or JSON for a non-string id. An id that must be
    redacted prints with the record's 1-based position in the register ("[credential-shaped text redacted #3]"), so
    two distinct redacted ids never print as the same text and the record stays traceable."""
    v = r.get("record_id")
    if not isinstance(v, str):
        return _hk(v)
    safe = _safe(v)
    return safe if safe == v or pos is None else _N.REDACTED[:-1] + f" #{pos}]"


def _refs(items):
    """Evidence refs among items that are not UNKNOWN-equivalent, as (index, item)."""
    return [(i, e) for i, e in enumerate(items if isinstance(items, list) else [])
            if isinstance(e, dict) and not _unk(e.get("ref"))]


_BARE_WORD = re.compile(r"[A-Za-z'\u2019-]+[.!]?")


def _prose_ref(ref):
    """A ref is judged as prose when it carries a space or is one bare word (no path, URL, digit or colon):
    "skipped", "pending" and "Waived" are statements; "tests/failed/run.log" and "a.py:12" are locations."""
    t = ref.strip()
    return bool(re.search(r"\s", t)) or bool(_BARE_WORD.fullmatch(t))


def _positive_refs(items):
    """Evidence refs that count as evidence: not UNKNOWN-equivalent and, when they are prose (see _prose_ref), neither
    negated ("not verified", "no test", "failed"), nor a doubt wording (ir_norm NEG_DOUBT: unchecked, skipped, pending,
    TBD, waived, disproved, invalid, false ...), nor non-evidence (ir_norm.non_evidence, judged on every ref whatever its shape: text that only says
    the fact is unknown, missing, null, nil, unavailable or pending, such as "status: unknown", "status=unknown" or "needs
    review"). A zero count of failures ("tests: 0 failed, 12 passed") is positive; "0 passed" is not. The word lists are vocabulary, not proof:
    UNKNOWN is never filled."""
    return [(i, e) for i, e in _refs(items)
            if not (isinstance(e["ref"], str) and ((_prose_ref(e["ref"]) and _N.negated(e["ref"], doubt=True))
                                                   or _N.non_evidence(e["ref"])))]


def _adopted(items):
    """Adoption refs that state a process observation; a unit listing or an install location is not adoption."""
    return [(i, e) for i, e in _refs(items) if _observed_process(e["ref"])]


def _on_word(r, srcs):
    """installed with no source that states a path and a full sha256: taken on the declarer's word."""
    return not any(not _unk(si.get("path")) and isinstance(si.get("sha256"), str) and HEX64.fullmatch(si["sha256"])
                   for _, si in srcs)


def _sources(r):
    """Every stated source of a record as (label, dict). source_identity xor sources."""
    if isinstance(r.get("sources"), list):
        return [(f"sources[{i}]", s if isinstance(s, dict) else {}) for i, s in enumerate(r["sources"])]
    if isinstance(r.get("source_identity"), dict):
        return [("source_identity", r["source_identity"])]
    return []


def validate(reg, schema, now=None):
    if now is None:
        now = datetime.now(timezone.utc)
    elif not isinstance(now, datetime):
        raise TypeError("now must be a timezone-aware datetime or None")
    elif now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("now is a naive datetime: it is ambiguous and is never replaced by the wall clock")
    findings = []
    errs = []
    _check(reg, schema, schema, "", errs)
    recs = reg.get("records") if isinstance(reg, dict) and isinstance(reg.get("records"), list) else []
    pos = {id(r): n for n, r in enumerate(recs, 1)}
    recs = [r for r in recs if isinstance(r, dict)]
    cov = reg.get("coverage") if isinstance(reg, dict) and isinstance(reg.get("coverage"), dict) else {}
    declared = cov.get("declared")
    complete = declared == COMPLETE

    def add(code, msg, rec=None, gap=False):
        # gap = a completeness gap: error only when the register claims completeness
        sev = "error" if (not gap or complete) else "warn"
        findings.append({"code": code, "severity": sev, "record": _safe(rec) if isinstance(rec, str) else rec,
                         "message": _safe(msg)})

    for path, msg in errs:
        add("schema", f"{path or '/'}: {msg}")

    if complete and not recs:
        add("no-records", "declared all-interfaces-complete with zero enumerated records; coverage is unproven")

    seen_ids = Counter()
    where = {}
    for r in recs:
        k = _hk(r.get("record_id"))
        seen_ids[k] += 1
        where.setdefault(k, []).append(pos[id(r)])
    for i, n in seen_ids.items():
        if n > 1:
            shown = _safe(i)
            if shown != i:                       # a redacted id is told apart by the positions that hold it
                shown = _N.REDACTED[:-1] + " at records " + ", ".join(f"#{p}" for p in where[i]) + "]"
            add("duplicate-record", f"record_id {shown} appears {n} times", shown)
    for grp in _duplicate_groups(recs):
        ids = [_rid(r, pos[id(r)]) for r in grp]
        add("duplicate-record", f"same family/role/host/component/path_or_command/kind recorded {len(grp)} times "
            f"(an unstated repo or commit is not a difference): {ids}", ",".join(ids))

    fl = reg.get("families") if isinstance(reg, dict) and isinstance(reg.get("families"), list) else []
    fams = {f["id"]: f for f in fl if isinstance(f, dict) and isinstance(f.get("id"), str)}
    on_word = []
    for r in recs:
        rid = _rid(r, pos[id(r)])
        srcs = _sources(r)
        fb = r.get("fusion_basis")
        if isinstance(fb, str) and "heuristic" in fb.lower():
            # a guess, not proof: reported under partial and complete alike (a warning, never an error)
            findings.append({"code": "heuristic-fusion", "severity": "warn", "record": rid,
                             "message": f"record is a heuristic fusion ({_safe(fb.strip())}), a guess and not proof that its sources are one component"})
        if ("sources" in r) == ("source_identity" in r):
            add("source-form", "a record needs exactly one of source_identity or sources", rid)
        if not _positive_refs(r.get("evidence")):
            add("missing-evidence", "no evidence recorded (a negated ref such as \"not verified\" or \"failed\" is not evidence)", rid, gap=True)
        if r.get("family") == UNASSIGNED:
            add("unassigned", "family UNASSIGNED: row not claimed by any family; coverage unproven", rid, gap=True)
        if _unk(r.get("role")):
            add("unknown-field", "role UNKNOWN", rid, gap=True)
        if _unk(r.get("component")):
            add("missing-endpoint", "component/endpoint missing or UNKNOWN", rid, gap=True)
        if _unk(r.get("host")):
            add("unknown-field", "host UNKNOWN", rid, gap=True)
        if _unk(r.get("installed_state")):
            add("unknown-field", "installed_state UNKNOWN", rid, gap=True)
        lbl = r.get("label")
        if _unk(lbl) or _N.canon(lbl) == "unclassified":
            add("unclassified", f"{_safe(r.get('role'))} record is unclassified", rid, gap=True)
        for lab, si in srcs:
            if _unk(si.get("version")):
                add("unknown-field", f"{lab} source version UNKNOWN", rid, gap=True)
            if _unk(si.get("repo")):
                add("unknown-field", f"{lab} source repo UNKNOWN", rid, gap=True)
            if si.get("available") is False and not _unk(r.get("installed_state")):
                add("unavailable-source-not-unknown",
                    f"{lab} source unavailable but installed_state is not UNKNOWN; an unavailable source is UNKNOWN, not a pass", rid)
        if r.get("effect_state") == "UNKNOWN" and r.get("replay") != "none":
            add("unknown-effect-replayed", "an UNKNOWN effect must be reported with replay=none, never retried", rid)
        if r.get("condition") == "committed-publish-pending" and r.get("label") != "positive-control":
            add("pending-mislabelled", "committed-publish-pending is a positive control, not a failure", rid)
        if r.get("installed_state") == "loaded" and not _adopted(r.get("adoption_evidence")):
            add("unevidenced-state", "installed_state loaded without adoption_evidence naming a process observation", rid, gap=True)
        if r.get("installed_state") == "installed" and _on_word(r, srcs):
            on_word.append(rid)
        def stamp(what, value):
            d, st = _ts(value)
            if st == "bad":
                add("unparseable-timestamp", f"{what} is not a parseable ISO-8601 time; staleness unprovable", rid, gap=True)
            elif st == "ambiguous":
                add("ambiguous-timestamp", f"{what} has no UTC offset; it is not read in the host time zone, staleness unprovable", rid, gap=True)
            elif d > now + SKEW:
                add("future-timestamp", f"{what} is later than the reference time plus 300 s", rid, gap=True)
            return d

        # every stated source needs a captured_at and every evidence / adoption ref an observed_at: an omitted
        # stamp makes staleness unprovable, the same refusal as an unparseable one.
        caps = []
        for lab, si in srcs:
            if "captured_at" not in si:
                add("missing-timestamp", f"{lab} has no captured_at; staleness unprovable", rid, gap=True)
                caps.append((lab, None))
            else:
                caps.append((lab, stamp(f"{lab} captured_at", si["captured_at"])))
        for field in ("evidence", "adoption_evidence"):
            items = r.get(field) if isinstance(r.get(field), list) else []
            for i, ev in enumerate(items):
                if not isinstance(ev, dict) or _unk(ev.get("ref")):
                    continue
                what = f"{field}[{i}] observed_at"
                if "observed_at" not in ev:
                    add("missing-timestamp", f"{what} is missing; staleness unprovable", rid, gap=True)
                    continue
                at = stamp(what, ev["observed_at"])
                for lab, cap in caps:
                    if at and cap and at < cap:
                        add("stale-evidence", f"{field}[{i}] observed {at.isoformat()} before {lab} identity {cap.isoformat()}", rid, gap=True)
        if r.get("role") == "caller":
            reg_callers = (fams.get(r.get("family")) or {}).get("registered_callers")
            if isinstance(reg_callers, list) and r.get("component") not in reg_callers:
                add("unregistered-caller", f"caller {_safe(r.get('component'))} not registered for {_safe(r.get('family'))}", rid)

    # endpoint presence per family, from the enumerated records only
    for fid, f in fams.items():
        mine = [r for r in recs if r.get("family") == fid and not _unk(r.get("component"))]
        roles = {r.get("role") for r in mine}
        if "producer" not in roles:
            add("missing-endpoint", f"family {fid} has no producer endpoint record", fid, gap=True)
        if "consumer" not in roles:
            add("missing-endpoint", f"family {fid} has no consumer endpoint record", fid, gap=True)
        have = {_hk(r.get("component")) for r in mine if r.get("role") == "caller"}
        for c in (f.get("registered_callers") if isinstance(f.get("registered_callers"), list) else []):
            if _hk(c) not in have:
                add("missing-endpoint", f"registered caller {_safe(c)} of {fid} has no record", fid, gap=True)
    for r in recs:
        if not (isinstance(r.get("family"), str) and (r["family"] in fams or r["family"] == UNASSIGNED)):
            add("unknown-family", f"family {_safe(r.get('family'))} not listed in families", _rid(r, pos[id(r)]), gap=True)

    counts = {"families": len(fams), "records": len(recs),
              "unassigned": sum(1 for r in recs if r.get("family") == UNASSIGNED),
              "by_role": dict(Counter(_safe(_hk(r.get("role")).strip('"')) for r in recs)),
              "by_label": dict(Counter(_safe(_hk(r.get("label")).strip('"')) for r in recs)),
              "by_installed_state": dict(Counter(_safe(_hk(r.get("installed_state")).strip('"')) for r in recs)),
              "unknown_or_unclassified_records": len({f["record"] for f in findings
                                                      if f["code"] in ("unknown-field", "unclassified", "missing-endpoint", "unassigned", "missing-evidence") and f["record"]})}
    dc = cov.get("declared_counts")
    if isinstance(dc, dict):
        for k, v in dc.items():
            if k in counts and counts[k] != v:
                findings.append({"code": "declared-count-ignored", "severity": "warn", "record": None,
                                 "message": f"declared {k}={v} ignored; derived {counts[k]}"})
    return {"ok": not any(f["severity"] == "error" for f in findings), "declared": declared,
            "counts": counts, "findings": findings, "installed_on_word": on_word}


def main(argv):
    args, now = argv[1:], None
    if "--now" in args:
        i = args.index("--now")
        if i + 1 >= len(args):
            print(__doc__, file=sys.stderr)
            return 2
        now, st = _ts(args[i + 1])
        if st != "ok":
            print("UNKNOWN: --now is not an ISO-8601 time with a UTC offset", file=sys.stderr)
            return 2
        del args[i:i + 2]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    argv = [argv[0]] + args
    try:
        with open(argv[1], encoding="utf-8") as f:
            reg = json.load(f, object_pairs_hook=_pairs)
    except (OSError, ValueError, RecursionError) as e:
        print(f"UNKNOWN: register unreadable: {_safe(e)}", file=sys.stderr)
        return 2
    if not isinstance(reg, dict):
        print(f"UNKNOWN: register unreadable: top level is {type(reg).__name__}, not an object", file=sys.stderr)
        return 2
    try:
        res = validate(reg, load_schema(), now)
    except (TypeError, AttributeError, LookupError, ValueError, RecursionError) as e:
        print(f"UNKNOWN: register shape not processable ({type(e).__name__})", file=sys.stderr)
        return 2
    print(json.dumps(res["counts"], indent=2, sort_keys=True))
    for f in res["findings"]:
        print(_safe(f"{f['severity'].upper()} {f['code']} [{f['record']}] {f['message']}"))
    if not res["ok"]:
        if res["declared"] == COMPLETE:
            bad = sorted({f"{f['record']}:{f['code']}" for f in res["findings"]
                          if f["severity"] == "error" and f["record"]})
            # each item was redacted where its record id was formed (and again here, item by item): the joined line is
            # not re-judged as one text, because separators between items read as one long credential-shaped run.
            print(f"REFUSED: declared {COMPLETE} but gaps remain in: {', '.join(_safe(b) for b in bad) or 'register-level (see findings)'}")
        else:
            print("REFUSED: register has errors")
        return 1
    word = (f"; installed state of {len(res['installed_on_word'])} record(s) taken on the declarer's word, "
            f"no stated path+sha256: {', '.join(res['installed_on_word'])}") if res["installed_on_word"] else ""
    print(_safe(f"OK (declared {res['declared']}; counts derived from {res['counts']['records']} records{word})"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
