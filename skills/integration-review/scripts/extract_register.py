#!/usr/bin/env python3
"""Convert child-B endpoints.jsonl rows into integration-review register records (stdlib, read-only).

Evidence fidelity rules (nothing is invented; every unstated fact stays UNKNOWN or missing):
- source identity is parsed only from the forms the row states: "path+sha256:<path> <64 hex>" and
  "commit <40 hex>"; anything else is version UNKNOWN, available false. The raw string is kept.
- a producer/consumer/caller/adapter side is kept only when the row's own evidence states it as
  "side=<role>" matching the claimed role; otherwise role is UNKNOWN and the claim is kept in
  claimed_roles.
- "loaded" is never emitted (it needs proven process adoption; a unit listing is not that). "installed"
  needs a stated path+sha256, "source-only" needs a stated path+sha256 or commit; otherwise UNKNOWN,
  with the claim kept in claimed_installed_states.
- every evidence ref is kept verbatim (no truncation); no evidence is recorded as an empty list.
- a row naming no valid family becomes family UNASSIGNED (kept, counted, blocks a complete claim).
- unparseable lines and non-object rows are rejected into rejected.json, never repaired.
- rows with one endpoint key merge (evidence union); rows of one component from different stated
  repos with different paths become ONE record with a sources list (no component qualifier).
- labels stay "unclassified"; effect_state/replay are not emitted.
usage: extract_register.py ENDPOINTS.jsonl OUTDIR   (exit 0 ok, 3 if any row was rejected, 2 unreadable)
Writes register-partial.json, register-declared-complete.json (same records, for refusal checks),
rejected.json, extraction.json.
"""
import hashlib
import json
import os
import re
import sys
from collections import Counter

FAMILY = re.compile(r"^IF[0-9]{3}$")
UNASSIGNED = "UNASSIGNED"
KINDS = {"http", "cli", "exit-code", "filesystem", "event", "receipt", "identity", "schema",
         "ordering", "retry", "trust", "rollback", "other"}
SIDES = ("producer", "consumer", "caller", "adapter")
PATH_SHA = re.compile(r"^path\+sha256:(\S+) ([0-9a-f]{64})$")
COMMIT = re.compile(r"^commit ([0-9a-f]{40})\b")
SIDE_MARK = re.compile(r"\bside=(producer|consumer|caller|adapter)\b")


def _s(v):
    return v if isinstance(v, str) and v.strip() else None


def parse_identity(row):
    raw = row.get("source_identity")
    repo = _s(row.get("source_repo")) or "UNKNOWN"
    rawtxt = raw if isinstance(raw, str) else "UNKNOWN"
    si = {"repo": repo, "version": "UNKNOWN", "available": False, "raw": rawtxt}
    m = PATH_SHA.match(rawtxt)
    if m:
        si.update(path=m.group(1), sha256=m.group(2), version=m.group(2), available=True)
    else:
        m = COMMIT.match(rawtxt)
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


def norm_role(row, ev):
    claimed = row.get("role")
    if claimed not in SIDES:
        return "UNKNOWN", None
    marks = {m for t in ev for m in SIDE_MARK.findall(t)}
    if claimed in marks:
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


def convert(rows, declared="partial"):
    return _build(list(enumerate(rows, 1)), declared, [])


def convert_lines(lines, declared="partial"):
    items, rejected = [], []
    for n, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            items.append((n, json.loads(line)))
        except ValueError as e:
            rejected.append({"line": n, "reason": f"not JSON: {e}"})
    return _build(items, declared, rejected)


def _build(items, declared, rejected):
    stats = Counter()
    eps = {}  # (family, role, host, component, kind, path) -> endpoint
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
        kind = row.get("interface_kind") if row.get("interface_kind") in KINDS else "other"
        host = _s(row.get("host")) or "UNKNOWN"
        comp = _s(row.get("component")) or "UNKNOWN"
        path = _s(row.get("path_or_command"))
        k = (fam, role, host, comp, kind, path)
        ep = eps.get(k)
        if ep is None:
            ep = eps[k] = {"key": k, "rows": [], "sources": [], "evidence": [], "states": [],
                           "claimed_roles": [], "claimed_states": []}
            order.append(ep)
        ep["rows"].append(n)
        if (si["repo"], si["raw"]) not in [(s["repo"], s["raw"]) for s in ep["sources"]]:
            ep["sources"].append(si)
        for t in ev:
            e = {"ref": t}
            if _s(row.get("observed_at")):
                e["observed_at"] = row["observed_at"]
            if e not in ep["evidence"]:
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
        repos = [{s["repo"] for s in m["sources"]} for m in members]
        flat = [r for rs in repos for r in rs]
        fuse = (len(members) > 1 and all(len(rs) == 1 for rs in repos) and "UNKNOWN" not in flat
                and len(set(flat)) == len(flat))
        if fuse:
            stats["fused_multi_source_components"] += 1
            members = [_fuse(members)]
        records += [_record(m, stats) for m in members]
    stats["records"] = len(records)
    stats["unassigned_records"] = sum(1 for r in records if r["family"] == UNASSIGNED)
    fams = sorted({r["family"] for r in records if r["family"] != UNASSIGNED})
    reg = {"schema_version": 1, "coverage": {"declared": declared},
           "families": [{"id": f} for f in fams], "records": records}
    return {"register": reg, "rejected": rejected, "stats": dict(stats)}


def _fuse(members):
    out = {"key": members[0]["key"][:5] + (None,), "rows": [], "sources": [], "evidence": [], "states": [],
           "claimed_roles": [], "claimed_states": [], "fused": True}
    for m in members:
        out["rows"] += m["rows"]
        for s in m["sources"]:
            s = dict(s, path_or_command=m["key"][5]) if m["key"][5] else dict(s)
            out["sources"].append(s)
        for key in ("evidence", "claimed_roles", "claimed_states"):
            out[key] += [x for x in m[key] if x not in out[key]]
        out["states"] += m["states"]
    return out


def _record(ep, stats):
    fam, role, host, comp, kind, path = ep["key"]
    states = set(ep["states"])
    state = states.pop() if len(states) == 1 else "UNKNOWN"
    rec = {"record_id": _id(fam, role, host, comp, kind, path), "family": fam, "role": role,
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
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[1]) as f:
            lines = f.read().splitlines()
    except OSError as e:
        print(f"UNKNOWN: input unreadable: {e}", file=sys.stderr)
        return 2
    os.makedirs(argv[2], exist_ok=True)
    out = convert_lines(lines, "partial")
    for name, decl in (("register-partial.json", "partial"),
                       ("register-declared-complete.json", "all-interfaces-complete")):
        reg = dict(out["register"], coverage={"declared": decl})
        with open(os.path.join(argv[2], name), "w") as f:
            json.dump(reg, f, indent=1)
    with open(os.path.join(argv[2], "rejected.json"), "w") as f:
        json.dump(out["rejected"], f, indent=1)
    out["stats"]["rejected_lines"] = len(out["rejected"])
    with open(os.path.join(argv[2], "extraction.json"), "w") as f:
        json.dump(out["stats"], f, indent=1, sort_keys=True)
    for k, v in sorted(out["stats"].items()):
        print(f"{k}: {v}")
    return 3 if out["rejected"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
