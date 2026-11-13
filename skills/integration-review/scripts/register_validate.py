#!/usr/bin/env python3
"""Validate an integration-review register (stdlib only, read-only).

Coverage counts are derived from the enumerated records; a declared count is ignored (warned if it
differs). A register declaring "all-interfaces-complete" is REFUSED (exit 1) while any record has
role, component (endpoint/caller), installed state or version UNKNOWN, is unclassified, or a family
lacks a producer or a consumer endpoint, or evidence is older than the source identity.
Unknown-equivalents (any case, surrounding whitespace, empty) are UNKNOWN. Complete also needs: at least one
record; loaded = adoption_evidence; parseable timestamps. (installed needing a stated path + sha256 is an
extractor rule only: a hand register states installed on the reviewer's word, see SKILL.md.) Evidence refs are never printed (records and indexes are named); credential-shaped text in any
message is redacted. A duplicate JSON key or a non-object register is unreadable (exit 2).
usage: register_validate.py REGISTER.json   (exit 0 ok, 1 refused, 2 unreadable)
"""
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone

SCHEMA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "schema", "register.schema.json")
COMPLETE = "all-interfaces-complete"
UNASSIGNED = "UNASSIGNED"
CRED = re.compile(r"(token|secret|passw|bearer|api[_-]?key|sk-ant|-----BEGIN|://[^/\s]*:[^/\s]*@)", re.I)


def _pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {_safe(k)!r}")
        seen.add(k)
    return dict(pairs)


def _safe(text):
    t = str(text)
    return "[credential-shaped text redacted]" if CRED.search(t) else t


def _blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def _unk(v):
    """UNKNOWN-equivalent: missing, empty/whitespace, or UNKNOWN in any case."""
    return not isinstance(v, str) or not v.strip() or v.strip().upper() == "UNKNOWN"


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
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(timezone.utc)
    except (ValueError, AttributeError, OverflowError, OSError):
        return None


def _key(r):
    return tuple(_hk(r.get(k)) for k in ("family", "role", "host", "component", "path_or_command", "interface_kind"))


def _rid(r):
    v = r.get("record_id")
    return _safe(v) if isinstance(v, str) else _hk(v)


def _refs(items):
    """Non-blank evidence refs among items, as (index, item)."""
    return [(i, e) for i, e in enumerate(items if isinstance(items, list) else [])
            if isinstance(e, dict) and isinstance(e.get("ref"), str) and e["ref"].strip()]


def _sources(r):
    """Every stated source of a record as (label, dict). source_identity xor sources."""
    if isinstance(r.get("sources"), list):
        return [(f"sources[{i}]", s if isinstance(s, dict) else {}) for i, s in enumerate(r["sources"])]
    if isinstance(r.get("source_identity"), dict):
        return [("source_identity", r["source_identity"])]
    return []


def validate(reg, schema):
    findings = []
    errs = []
    _check(reg, schema, schema, "", errs)
    recs = reg.get("records") if isinstance(reg, dict) and isinstance(reg.get("records"), list) else []
    recs = [r for r in recs if isinstance(r, dict)]
    cov = reg.get("coverage") if isinstance(reg, dict) and isinstance(reg.get("coverage"), dict) else {}
    declared = cov.get("declared")
    complete = declared == COMPLETE

    def add(code, msg, rec=None, gap=False):
        # gap = a completeness gap: error only when the register claims completeness
        sev = "error" if (not gap or complete) else "warn"
        findings.append({"code": code, "severity": sev, "record": rec, "message": _safe(msg)})

    for path, msg in errs:
        add("schema", f"{path or '/'}: {msg}")

    if complete and not recs:
        add("no-records", "declared all-interfaces-complete with zero enumerated records; coverage is unproven")

    seen_ids, seen_keys = Counter(), Counter()
    for r in recs:
        seen_ids[_hk(r.get("record_id"))] += 1
        seen_keys[_key(r)] += 1
    for i, n in seen_ids.items():
        if n > 1:
            add("duplicate-record", f"record_id {_safe(i)} appears {n} times", _safe(i))
    for k, n in seen_keys.items():
        if n > 1:
            ids = [_rid(r) for r in recs if _key(r) == k]
            add("duplicate-record", f"same family/role/host/component/path_or_command/kind recorded {n} times: {ids}", ",".join(ids))

    fl = reg.get("families") if isinstance(reg, dict) and isinstance(reg.get("families"), list) else []
    fams = {f["id"]: f for f in fl if isinstance(f, dict) and isinstance(f.get("id"), str)}
    for r in recs:
        rid = _rid(r)
        srcs = _sources(r)
        if ("sources" in r) == ("source_identity" in r):
            add("source-form", "a record needs exactly one of source_identity or sources", rid)
        if not _refs(r.get("evidence")):
            add("missing-evidence", "no evidence recorded", rid, gap=True)
        if r.get("family") == UNASSIGNED:
            add("unassigned", "family UNASSIGNED: row not claimed by any family; coverage unproven", rid, gap=True)
        if _unk(r.get("role")):
            add("unknown-field", "role UNKNOWN", rid, gap=True)
        if _unk(r.get("component")):
            add("missing-endpoint", "component/endpoint missing or UNKNOWN", rid, gap=True)
        if _unk(r.get("installed_state")):
            add("unknown-field", "installed_state UNKNOWN", rid, gap=True)
        lbl = r.get("label")
        if not isinstance(lbl, str) or lbl.strip().lower() in ("", "unclassified"):
            add("unclassified", f"{_safe(r.get('role'))} record is unclassified", rid, gap=True)
        for lab, si in srcs:
            if _unk(si.get("version")):
                add("unknown-field", f"{lab} source version UNKNOWN", rid, gap=True)
            if si.get("available") is False and not _unk(r.get("installed_state")):
                add("unavailable-source-not-unknown",
                    f"{lab} source unavailable but installed_state is not UNKNOWN; an unavailable source is UNKNOWN, not a pass", rid)
        if r.get("effect_state") == "UNKNOWN" and r.get("replay") != "none":
            add("unknown-effect-replayed", "an UNKNOWN effect must be reported with replay=none, never retried", rid)
        if r.get("condition") == "committed-publish-pending" and r.get("label") != "positive-control":
            add("pending-mislabelled", "committed-publish-pending is a positive control, not a failure", rid)
        if r.get("installed_state") == "loaded" and not _refs(r.get("adoption_evidence")):
            add("unevidenced-state", "installed_state loaded without adoption_evidence (process adoption)", rid, gap=True)
        evs = r.get("evidence") if isinstance(r.get("evidence"), list) else []
        for lab, si in srcs:
            cap = _ts(si.get("captured_at")) if "captured_at" in si else None
            if "captured_at" in si and cap is None:
                add("unparseable-timestamp", f"{lab} captured_at is not a parseable ISO-8601 time; staleness unprovable", rid, gap=True)
            for i, ev in enumerate(evs):
                at = _ts(ev["observed_at"]) if isinstance(ev, dict) and "observed_at" in ev else None
                if at and cap and at < cap:
                    add("stale-evidence", f"evidence[{i}] observed {at.isoformat()} before {lab} identity {cap.isoformat()}", rid, gap=True)
        for i, ev in enumerate(evs):
            if isinstance(ev, dict) and "observed_at" in ev and _ts(ev["observed_at"]) is None:
                add("unparseable-timestamp", f"evidence[{i}] observed_at is not a parseable ISO-8601 time; staleness unprovable", rid, gap=True)
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
            add("unknown-family", f"family {_safe(r.get('family'))} not listed in families", r.get("record_id"), gap=True)

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
            "counts": counts, "findings": findings}


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
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
        res = validate(reg, load_schema())
    except (TypeError, AttributeError, KeyError, RecursionError) as e:
        print(f"UNKNOWN: register shape not processable ({type(e).__name__})", file=sys.stderr)
        return 2
    print(json.dumps(res["counts"], indent=2, sort_keys=True))
    for f in res["findings"]:
        print(_safe(f"{f['severity'].upper()} {f['code']} [{f['record']}] {f['message']}"))
    if not res["ok"]:
        if res["declared"] == COMPLETE:
            bad = sorted({f"{f['record']}:{f['code']}" for f in res["findings"]
                          if f["severity"] == "error" and f["record"]})
            print(_safe(f"REFUSED: declared {COMPLETE} but gaps remain in: {', '.join(bad) or 'register-level (see findings)'}"))
        else:
            print("REFUSED: register has errors")
        return 1
    print(f"OK (declared {res['declared']}; counts derived from {res['counts']['records']} records)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
