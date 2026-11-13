#!/usr/bin/env python3
"""Convert child-B endpoints.jsonl rows into integration-review register records (stdlib, read-only).

Evidence fidelity rules (nothing is invented; every unstated fact stays UNKNOWN or missing):
- source identity is parsed only from the forms the row states, matched in full (no trailing newline or
  qualifier text): "path+sha256:<path> <64 hex>" and "commit <40 hex>"; anything else is version UNKNOWN, available false. The raw string is kept.
- a producer/consumer/caller/adapter side is kept only when the row's own evidence states it as
  "side=<role>" (not negated: "not side=producer" and "side=producer failed" are no mark) matching the claimed role and states no other side; otherwise (no mark, or contradictory
  marks) role is UNKNOWN and the claim is kept in claimed_roles.
- "loaded" is never emitted (it needs proven process adoption; a unit listing is not that). "installed"
  needs a stated path+sha256, "source-only" needs a stated path+sha256 or commit; otherwise UNKNOWN,
  with the claim kept in claimed_installed_states.
- every evidence ref is kept verbatim (no truncation); no evidence is recorded as an empty list.
- a row naming no valid family becomes family UNASSIGNED (kept, counted, blocks a complete claim).
- unparseable lines, duplicate JSON keys and non-object rows are rejected into rejected.json, never
  repaired. Lines are split on "\\n" only (U+2028/U+0085 inside a valid row are data); input must be UTF-8.
- rows with one endpoint key merge (evidence union) unless they prove different sources (stated repos or commits that
  differ; path-less rows too: they never fuse across repos). Equally named endpoints with different paths fuse into ONE
  record (a sources list, no component qualifier) only on direct proof that they are one component: the same
  content sha256, or the same canonical repo identity (URL/scp/.git/trailing-slash spellings folded) with the same
  normalized path. Same-named records in different repos, or with distinct commits, stay separate. The fused
  record carries fusion_basis and every source. The old guess (repo-rooted paths + distinct identities) is OFF
  by default; `--heuristic-fusion` / convert(heuristic_fusion=True) turns it on, labels it
  "same-name-and-repo-rooted-paths-heuristic" and it is a guess, not proof. UNKNOWN-equivalents
  (scripts/ir_norm.py) in component, host, repo, path and evidence refs are treated as not stated.
- labels stay "unclassified"; effect_state/replay are not emitted.
usage: extract_register.py [--heuristic-fusion] ENDPOINTS.jsonl OUTDIR   (exit 0 ok, 3 if any row was rejected, 2 unreadable input or output)
Writes register-partial.json, register-declared-complete.json (same records, for refusal checks),
rejected.json, extraction.json.
"""
import bisect
import hashlib
import importlib.util
import json
import os
import posixpath
import re
import sys
from collections import Counter


def _load_norm():
    m = sys.modules.get("ir_norm")
    if m is None:
        spec = importlib.util.spec_from_file_location("ir_norm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_norm.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.modules["ir_norm"] = m
    return m


_N = _load_norm()
is_unknown, redact = _N.is_unknown, _N.redact

FAMILY = re.compile(r"^IF[0-9]{3}$")
UNASSIGNED = "UNASSIGNED"
KINDS = {"http", "cli", "exit-code", "filesystem", "event", "receipt", "identity", "schema",
         "ordering", "retry", "trust", "rollback", "other"}
SIDES = ("producer", "consumer", "caller", "adapter")
PATH_SHA = re.compile(r"path\+sha256:(\S+) ([0-9a-f]{64})")      # always fullmatch: "$" would accept a trailing newline
COMMIT = re.compile(r"commit ([0-9a-f]{40})")                     # always fullmatch: no trailing qualifier text
SIDE_MARK = re.compile(r"\bside=(producer|consumer|caller|adapter)\b")


def _pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {redact(k)!r}")
        seen.add(k)
    return dict(pairs)


def _s(v):
    return v if isinstance(v, str) and not is_unknown(v) else None


def parse_identity(row):
    raw = row.get("source_identity")
    repo = _s(row.get("source_repo")) or "UNKNOWN"
    rawtxt = raw if isinstance(raw, str) else "UNKNOWN"
    si = {"repo": repo, "version": "UNKNOWN", "available": False, "raw": rawtxt}
    m = PATH_SHA.fullmatch(rawtxt)
    if m:
        si.update(path=m.group(1), sha256=m.group(2), version=m.group(2), available=True)
    else:
        m = COMMIT.fullmatch(rawtxt)
        if m:
            si.update(commit=m.group(1), version=m.group(1), available=True)
    if _s(row.get("captured_at")):
        si["captured_at"] = row["captured_at"]
    return si


def evidence_text(row):
    e = row.get("evidence")
    items = e if isinstance(e, list) else [e]
    out = []
    for x in items:
        ref = x.get("ref") if isinstance(x, dict) else x
        if _s(ref):
            out.append(ref)
    return out


_CLAUSE_END = re.compile(r"[;\n]|\.\s")


def _marks(t):
    """Side marks of one evidence ref that are stated positively. A mark is negated, as a class and at any distance,
    by a negation or doubt word (ir_norm NEG_CORE and NEG_DOUBT: "no evidence that side=producer", "never really
    established that side=producer", "unverified: side=producer", "side=producer is false") between the start of its
    clause and the mark, counted from the end of the previous side mark, or one after it up to the end of its clause
    (; newline or a full stop ends the clause). A negation that heads another side mark does not reach this one
    ("side=producer, not side=consumer" keeps the producer mark); a zero count of failures is no negation."""
    out = set()
    prev_end = 0
    for m in SIDE_MARK.finditer(t):
        a = max([c.end() for c in _CLAUSE_END.finditer(t, 0, m.start())] or [0])
        c = _CLAUSE_END.search(t, m.end())
        z = c.start() if c else len(t)
        before = t[max(a, prev_end):m.start()]
        prev_end = m.end()
        after = SIDE_MARK.sub(" ", re.sub(r"(?i)\b(?:not|no|never|without|isn['\u2019]t)\s+(?=side=)", " ", t[m.end():z]))
        if _N.negated(before, doubt=True) or _N.negated(after, doubt=True):
            continue
        out.add(m.group(1))
    return out


def norm_role(row, ev):
    claimed = row.get("role")
    if claimed not in SIDES:
        return "UNKNOWN", None
    marks = {m for t in ev for m in _marks(t)}
    if marks == {claimed}:
        return claimed, None
    return "UNKNOWN", claimed


def norm_state(row, si):
    claimed = row.get("installed_state")
    if claimed == "installed" and "sha256" in si:
        return "installed", None
    if claimed == "source-only" and ("sha256" in si or "commit" in si):
        return "source-only", None
    if claimed in (None, "UNKNOWN"):
        return "UNKNOWN", None
    return "UNKNOWN", claimed


def _id(*parts):
    return "x-" + hashlib.sha256(json.dumps(parts).encode()).hexdigest()[:16]


def convert(rows, declared="partial", heuristic_fusion=False):
    return _build(list(enumerate(rows, 1)), declared, [], heuristic_fusion)


def convert_lines(lines, declared="partial", heuristic_fusion=False):
    items, rejected = [], []
    for n, line in enumerate(lines, 1):
        if not line.strip(" \t\r"):
            continue
        try:
            items.append((n, json.loads(line, object_pairs_hook=_pairs)))
        except ValueError as e:
            rejected.append({"line": n, "reason": f"not JSON: {redact(e)}"})
        except RecursionError:
            rejected.append({"line": n, "reason": "not JSON: nested too deeply to parse"})
    return _build(items, declared, rejected, heuristic_fusion)


def _build(items, declared, rejected, heuristic_fusion=False):
    stats = Counter()
    index = {}  # (family, role, host, component, kind, path) -> _KeyIndex of its endpoints
    order = []
    for n, row in items:
        if not isinstance(row, dict):
            rejected.append({"line": n, "reason": f"row is {type(row).__name__}, not an object"})
            continue
        stats["rows"] += 1
        fam = row.get("family")
        fam = fam if isinstance(fam, str) and FAMILY.match(fam) else UNASSIGNED
        ev = evidence_text(row)
        role, claimed_role = norm_role(row, ev)
        si = parse_identity(row)
        state, claimed_state = norm_state(row, si)
        kind = row.get("interface_kind")
        kind = kind if isinstance(kind, str) and kind in KINDS else "other"
        host = _s(row.get("host")) or "UNKNOWN"
        comp = _s(row.get("component")) or "UNKNOWN"
        path = _s(row.get("path_or_command"))
        k = (fam, role, host, comp, kind, path)
        ix = index.get(k)
        rid = None if si["repo"] == "UNKNOWN" else _repo_id(si["repo"])
        ep = ix.find(rid, si.get("commit")) if ix else None
        if ep is None:
            ep = {"key": k, "rows": [], "sources": [], "evidence": [], "states": [],
                  "claimed_roles": [], "claimed_states": [], "seen_src": set(), "seen_ev": set(), "rid": rid, "cm": si.get("commit")}
            if ix:
                ep["salt"] = n          # same key, different repo or commit: its own record, id salted by first row
            else:
                ix = index[k] = _KeyIndex()
            ix.add(ep, len(order))
            order.append(ep)
        ep["rows"].append(n)
        ix.update(ep, rid, si.get("commit"))
        if (si["repo"], si["raw"]) not in ep["seen_src"]:
            ep["seen_src"].add((si["repo"], si["raw"]))
            ep["sources"].append(si)
        for t in ev:
            e = {"ref": t}
            if _s(row.get("observed_at")):
                e["observed_at"] = row["observed_at"]
            ek = (t, e.get("observed_at"))
            if ek not in ep["seen_ev"]:
                ep["seen_ev"].add(ek)
                ep["evidence"].append(e)
        ep["states"].append(state)
        for lst, v in ((ep["claimed_roles"], claimed_role), (ep["claimed_states"], claimed_state)):
            if v and v not in lst:
                lst.append(v)

    # Fuse endpoints of one component whose differing paths come from distinct, stated repos.
    groups = {}
    for ep in order:
        groups.setdefault(ep["key"][:5], []).append(ep)
    records = []
    for g, members in groups.items():
        if len(members) > 1:
            clusters = _positive_clusters(members)
            if heuristic_fusion:
                repos = [{s["repo"] for s in m["sources"]} for m in members]
                flat = [r for rs in repos for r in rs]
                if (all(len(rs) == 1 for rs in repos) and "UNKNOWN" not in flat
                        and len(set(flat)) == len(flat) and _one_component(members)):
                    clusters = [(list(range(len(members))), "same-name-and-repo-rooted-paths-heuristic")]
            used = {i for idx, _ in clusters for i in idx}
            fused = []
            rest = [m for i, m in enumerate(members) if i not in used]
            taken = {m["key"] for m in rest}             # a fused record never takes the key of a record beside it
            for n, (idx, basis) in enumerate(clusters):
                stats["fused_multi_source_components"] += 1
                f = _fuse([members[i] for i in idx], basis)
                if n or f["key"] in taken:
                    paths = [members[i]["key"][5] for i in idx if members[i]["key"][5]]
                    cands = paths + ["fused:" + ",".join(str(r) for r in f["rows"])]
                    f["key"] = next(f["key"][:5] + (c,) for c in cands if f["key"][:5] + (c,) not in taken)
                taken.add(f["key"])
                fused.append(f)
            members = fused + rest
        records += [_record(m, stats) for m in members]
    stats["records"] = len(records)
    stats["unassigned_records"] = sum(1 for r in records if r["family"] == UNASSIGNED)
    fams = sorted({r["family"] for r in records if r["family"] != UNASSIGNED})
    reg = {"schema_version": 1, "coverage": {"declared": declared},
           "families": [{"id": f} for f in fams], "records": records}
    return {"register": reg, "rejected": rejected, "stats": dict(stats)}


class _KeyIndex:
    """The endpoints of one key, found by the stated repo and commit instead of a rescan of every endpoint.
    A row joins the FIRST endpoint (creation order) it does not provably differ from: both state a repo and the
    canonical identities differ, or both state commits and the commits differ; unstated is not different. An
    endpoint holds at most one canonical repo and one commit (a row joins only when it does not differ, and then
    fills what the endpoint left unstated), so ordered buckets by (repo, commit), repo and commit answer every
    lookup. An entry whose endpoint has since gained a repo or commit is stale for its old bucket and is dropped
    when met."""

    def __init__(self):
        self.first = None
        self.rc, self.r, self.c = {}, {}, {}

    def __bool__(self):
        return self.first is not None

    @staticmethod
    def _put(d, key, ep):
        bisect.insort(d.setdefault(key, []), (ep["seq"], id(ep), ep))

    def add(self, ep, seq):
        ep["seq"] = seq
        if self.first is None:
            self.first = ep
        self._put(self.rc, (ep["rid"], ep["cm"]), ep)
        self._put(self.r, ep["rid"], ep)
        self._put(self.c, ep["cm"], ep)

    def update(self, ep, rid, commit):
        old = (ep["rid"], ep["cm"])
        if rid is not None and ep["rid"] is None:
            ep["rid"] = rid
        if commit is not None and ep["cm"] is None:
            ep["cm"] = commit
        if (ep["rid"], ep["cm"]) != old:
            self._put(self.rc, (ep["rid"], ep["cm"]), ep)
            if ep["rid"] != old[0]:
                self._put(self.r, ep["rid"], ep)
            if ep["cm"] != old[1]:
                self._put(self.c, ep["cm"], ep)

    @staticmethod
    def _head(lst, live):
        while lst and not live(lst[0][2]):
            lst.pop(0)
        return lst[0][2] if lst else None

    def find(self, rid, commit):
        if rid is not None and commit is not None:
            probes = [(self.rc, (r, c), (lambda ep, r=r, c=c: (ep["rid"], ep["cm"]) == (r, c)))
                      for r in (rid, None) for c in (commit, None)]
        elif rid is not None:
            probes = [(self.r, r, (lambda ep, r=r: ep["rid"] == r)) for r in (rid, None)]
        elif commit is not None:
            probes = [(self.c, c, (lambda ep, c=c: ep["cm"] == c)) for c in (commit, None)]
        else:
            return self.first
        best = None
        for d, key, live in probes:
            ep = self._head(d.get(key, []), live)
            if ep is not None and (best is None or ep["seq"] < best["seq"]):
                best = ep
        return best


def _repo_id(repo):
    return _N.repo_id(repo)


def _path_id(path):
    return posixpath.normpath(path) if isinstance(path, str) and path else None


def _commits(m):
    return {s["commit"] for s in m["sources"] if "commit" in s}


def _distinct_commits(a, b):
    """Two members that each state commits, and not the same ones: they are different builds and never fuse,
    whatever the basis label (same sha256, same repo and path, or the heuristic)."""
    ca, cb = _commits(a), _commits(b)
    return bool(ca) and bool(cb) and ca != cb


def _positive_clusters(members):
    """Members (same family/role/host/component/kind, different path) that POSITIVELY are one component:
    the same canonical repo identity with the same normalized path, or the same content sha256. Returns
    [(member indexes, basis)] for clusters of two or more; every other member stays a separate record.
    Members with distinct commits never fuse (directly or through a chain of other members)."""
    parent = list(range(len(members)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    sha = [{s["sha256"] for s in m["sources"] if "sha256" in s} for m in members]
    repos = [{_repo_id(s["repo"]) for s in m["sources"] if s["repo"] != "UNKNOWN"} for m in members]
    paths = [_path_id(m["key"][5]) for m in members]
    # per cluster root: its commit sets (members that state commits). A cluster holds at most one set (two
    # clusters with distinct sets never unite), so a cluster is empty or has exactly one set.
    csets = [{frozenset(_commits(m))} if _commits(m) else set() for m in members]

    marks = [set() for _ in members]     # per cluster root: the buckets it has been through (small-to-large merged)

    def union(i, j):
        ri, rj = find(i), find(j)
        if ri == rj:
            return
        ca, cb = csets[ri], csets[rj]
        if ca and cb and ca != cb:
            return
        parent[ri] = rj
        csets[rj] = ca | cb
        if len(marks[ri]) > len(marks[rj]):
            marks[ri], marks[rj] = marks[rj], marks[ri]
        marks[rj] |= marks[ri]
        marks[ri] = set()

    def ckey(i):
        cs = csets[find(i)]
        return next(iter(cs)) if cs else None

    # Related members are met through buckets (one per content sha256, one per canonical repo + normalized path),
    # not by a pairwise scan; the related pairs are tried in (i, j) order, so the clusters are those of the
    # pairwise rule. Two shortcuts, neither changes a result: (1) a member whose cluster has already been through
    # a bucket adds nothing there (every later member was joined to that cluster or is refused for good: a
    # cluster's commit set never changes once stated); (2) a member whose cluster states commits only meets the
    # bucket members stating the same commits or none (the others are refused for good).
    bucket_of, hows, mem = {}, [], []
    mine = [[] for _ in members]
    for i in range(len(members)):
        keys = [("sha", h) for h in sha[i]]
        if paths[i]:
            keys += [("rp", r, paths[i]) for r in repos[i]]
        for key in keys:
            if key not in bucket_of:
                bucket_of[key] = len(mem)
                mem.append([])
                hows.append("same-content-sha256" if key[0] == "sha" else "same-repo-identity-and-path")
            mem[bucket_of[key]].append(i)
            mine[i].append(bucket_of[key])
    bykey = []
    for lst in mem:
        d = {}
        for i in lst:
            d.setdefault(next(iter(csets[i])) if csets[i] else None, []).append(i)
        bykey.append(d)
    for i in range(len(members)):
        cands, used = {}, []
        ri = find(i)
        x = ckey(i)
        for b in mine[i]:
            if b in marks[ri]:
                continue
            used.append(b)
            if x is None:
                partners = mem[b][bisect.bisect_right(mem[b], i):]
            else:
                partners = []
                for k in (x, None):
                    lst = bykey[b].get(k, [])
                    partners += lst[bisect.bisect_right(lst, i):]
            for j in partners:
                if hows[b] == "same-content-sha256" or j not in cands:
                    cands[j] = hows[b]
        for j in sorted(cands):
            union(i, j)
        for b in used:
            marks[find(i)].add(b)
    # label: the basis of the last related pair, in (i, j) order, inside the final cluster (sha beats repo+path)
    last = {}
    for b, lst in enumerate(mem):
        by_root = {}
        for i in lst:
            by_root.setdefault(find(i), []).append(i)
        for root, g in by_root.items():
            if len(g) > 1:
                cand = (g[-2], g[-1], hows[b] == "same-content-sha256", hows[b])
                if root not in last or cand[:3] > last[root][:3]:
                    last[root] = cand
    out = {}
    for i in range(len(members)):
        out.setdefault(find(i), []).append(i)
    res = []
    for root, idx in out.items():
        if len(idx) > 1:
            res.append((idx, last[root][3] if root in last else "same-repo-identity-and-path"))
    return res


def _rooted(path, repo):
    """path, with "." and ".." resolved, lies inside repo/ (never absolute, never climbing out)."""
    if not isinstance(path, str) or not path or path.startswith("/"):
        return False
    if repo != repo.strip() or repo.endswith("/") or "//" in path or "//" in repo:
        return False                        # a non-canonical spelling is not read as rooted
    r = posixpath.normpath(repo)
    n = posixpath.normpath(path)
    return r not in ("", ".", "..") and not r.startswith(("/", "../")) and n.startswith(r + "/")


def _one_component(members):
    """Heuristic (it does not prove it) that differently-sourced, equally named endpoints are one component:
    every member's normalized path is rooted in its own stated repo and carries a stated identity, and the
    identities are distinct."""
    vers = []
    for m in members:
        path, repo = m["key"][5], next(iter({s["repo"] for s in m["sources"]}))
        if not _rooted(path, repo):
            return False
        v = {s["version"] for s in m["sources"]}
        if len(v) != 1 or "UNKNOWN" in v:
            return False
        vers += v
    return len(set(vers)) == len(vers)


def _fuse(members, basis):
    out = {"key": members[0]["key"][:5] + (None,), "rows": [], "sources": [], "evidence": [], "states": [],
           "claimed_roles": [], "claimed_states": [], "fused": True, "fusion_basis": basis}
    seen = {"evidence": set(), "claimed_roles": set(), "claimed_states": set()}
    for m in members:
        out["rows"] += m["rows"]
        for s in m["sources"]:
            s = dict(s, path_or_command=m["key"][5]) if m["key"][5] else dict(s)
            out["sources"].append(s)
        for key in ("evidence", "claimed_roles", "claimed_states"):
            for x in m[key]:
                xk = json.dumps(x, sort_keys=True)
                if xk not in seen[key]:
                    seen[key].add(xk)
                    out[key].append(x)
        out["states"] += m["states"]
    return out


def _record(ep, stats):
    fam, role, host, comp, kind, path = ep["key"]
    states = set(ep["states"])
    state = states.pop() if len(states) == 1 else "UNKNOWN"
    rec = {"record_id": _id(fam, role, host, comp, kind, path, *([ep["salt"]] if "salt" in ep else [])), "family": fam, "role": role,
           "host": host, "component": comp, "interface_kind": kind}
    if path:
        rec["path_or_command"] = path
    srcs = ep["sources"]
    if len(srcs) > 1 or ep.get("fused"):
        if not ep.get("fused") and path:
            srcs = [dict(s, path_or_command=path) for s in srcs]
        rec["sources"] = srcs
        stats["multi_source_records"] += 1
    else:
        rec["source_identity"] = srcs[0]
    rec.update(installed_state=state, label="unclassified", evidence=ep["evidence"], source_rows=ep["rows"])
    if ep.get("fused"):
        rec["fusion_basis"] = ep["fusion_basis"]
    if ep["claimed_roles"]:
        rec["claimed_roles"] = ep["claimed_roles"]
        stats["roles_claimed_not_evidenced"] += 1
    if ep["claimed_states"]:
        rec["claimed_installed_states"] = ep["claimed_states"]
        stats["installed_state_claimed_not_evidenced"] += 1
    if not ep["evidence"]:
        stats["missing_evidence_records"] += 1
    return rec


def main(argv):
    heur = "--heuristic-fusion" in argv
    argv = [a for a in argv if a != "--heuristic-fusion"]
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8", newline="") as f:
            lines = f.read().split("\n")
    except (OSError, ValueError) as e:
        print(f"UNKNOWN: input unreadable: {type(e).__name__}: {redact(e)}", file=sys.stderr)
        return 2
    out = convert_lines(lines, "partial", heur)
    try:
        os.makedirs(argv[2], exist_ok=True)
        for name, decl in (("register-partial.json", "partial"),
                           ("register-declared-complete.json", "all-interfaces-complete")):
            reg = dict(out["register"], coverage={"declared": decl})
            with open(os.path.join(argv[2], name), "w", encoding="utf-8") as f:
                json.dump(reg, f, indent=1)
        with open(os.path.join(argv[2], "rejected.json"), "w", encoding="utf-8") as f:
            json.dump(out["rejected"], f, indent=1)
        out["stats"]["rejected_lines"] = len(out["rejected"])
        with open(os.path.join(argv[2], "extraction.json"), "w", encoding="utf-8") as f:
            json.dump(out["stats"], f, indent=1, sort_keys=True)
    except OSError as e:
        print(f"UNKNOWN: output unwritable: {type(e).__name__}: {redact(e)}", file=sys.stderr)
        return 2
    for k, v in sorted(out["stats"].items()):
        print(f"{k}: {v}")
    return 3 if out["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
