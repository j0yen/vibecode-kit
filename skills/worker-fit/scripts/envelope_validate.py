#!/usr/bin/env python3
"""Validate worker-fit task envelopes. Standard library only, read-only, no network.

Usage: envelope_validate.py FILE [FILE...]   (FILE = one envelope, a list, or {"envelopes": [...]})
Exit 0 = no REFUSE finding, 1 = at least one REFUSE finding, 2 = unreadable input.
Counts are derived from the enumerated records; a declared total is only compared, never used.
A pass is a statement about the envelope's shape and internal consistency, not about production.
"""
import json
import sys
from datetime import datetime, timezone

UNKNOWN = "UNKNOWN"
STATES = ["NOT_STARTED", "RUNNING", "DONE", "BLOCKED", "UNKNOWN"]
SHAPES = ["implementation", "review", "decision", "deterministic", "UNKNOWN"]
EFFECTS = ["none", "applied", "UNKNOWN"]
SCHEMA_ID = "worker-fit-envelope/1"
REQUIRED_TOP = ["schema", "parent", "task_id", "revision", "approved_ac_refs", "work_shape", "source",
                "current_owner", "owner_reachable", "target", "worker", "state", "effect", "result",
                "consumer", "ack", "next_action", "observed_at", "evidence", "coverage_gaps",
                "declared_complete"]
OPTIONAL_TOP = ["label"]
WORKER_KEYS = ["host", "unit", "invocation", "child", "session", "account", "model", "effort"]
# kinds: s=nonempty str, i=int, b=bool, t=timestamp-or-UNKNOWN, tri=bool|UNKNOWN, sn=str|None, in=int|None
SUB = {
    "source": {"owner": "s", "identity": "s", "identity_at": "t", "revision_at": "t"},
    "target": {"repo": "s", "branch": "s", "head": "s"},
    "worker": {k: "s" for k in WORKER_KEYS},
    "effect": {"state": "e", "no_replay": "b", "policy": "s"},
    "result": {"artifact": "sn", "event": "sn", "task_id": "sn", "revision": "in", "reviewed": "tri"},
    "consumer": {"named": "s", "alternate": "sn", "alternate_authorized": "b", "available": "tri"},
    "ack": {"accepted": "b", "evidence": "sn"},
    "observed_at": {"envelope": "t", "worker": "t", "result": "t"},
}
SUB_OPTIONAL = {"source": ["claim"]}


def finding(code, path, message, severity="REFUSE"):
    return {"code": code, "severity": severity, "path": path, "message": message}


def parse_ts(v):
    """datetime (aware) or None for UNKNOWN; raises ValueError for malformed."""
    if v == UNKNOWN:
        return None
    if not isinstance(v, str):
        raise ValueError("not a string")
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("timestamp lacks an offset")
    return dt.astimezone(timezone.utc)


def _kind_ok(kind, v):
    if kind == "s":
        return isinstance(v, str) and v != ""
    if kind == "t":
        return isinstance(v, str) and v != ""
    if kind == "i":
        return isinstance(v, int) and not isinstance(v, bool)
    if kind == "b":
        return isinstance(v, bool)
    if kind == "tri":
        return isinstance(v, bool) or v == UNKNOWN
    if kind == "sn":
        return v is None or (isinstance(v, str) and v != "")
    if kind == "in":
        return v is None or (isinstance(v, int) and not isinstance(v, bool))
    if kind == "e":
        return v in EFFECTS
    return False


def _shape(d):
    out = []
    for k in REQUIRED_TOP:
        if k not in d:
            out.append(finding("SCHEMA_MISSING", k, "required field missing"))
    for k in d:
        if k not in REQUIRED_TOP and k not in OPTIONAL_TOP:
            out.append(finding("UNKNOWN_KEY", k, "field not in schema"))
    if d.get("schema", SCHEMA_ID) != SCHEMA_ID:
        out.append(finding("SCHEMA_ENUM", "schema", "expected " + SCHEMA_ID))
    for k, kind in (("parent", "s"), ("task_id", "s"), ("revision", "i"), ("current_owner", "s"),
                    ("next_action", "s"), ("declared_complete", "b"), ("owner_reachable", "tri")):
        if k in d and not _kind_ok(kind, d[k]):
            out.append(finding("SCHEMA_TYPE", k, "wrong type or empty"))
    if isinstance(d.get("revision"), int) and not isinstance(d.get("revision"), bool) and d["revision"] < 0:
        out.append(finding("SCHEMA_TYPE", "revision", "negative"))
    if "state" in d and d["state"] not in STATES:
        out.append(finding("SCHEMA_ENUM", "state", "not one of " + ",".join(STATES)))
    if "work_shape" in d and d["work_shape"] not in SHAPES:
        out.append(finding("SCHEMA_ENUM", "work_shape", "not one of " + ",".join(SHAPES)))
    for k in ("approved_ac_refs", "coverage_gaps"):
        if k in d and not (isinstance(d[k], list) and all(isinstance(x, str) and x for x in d[k])):
            out.append(finding("SCHEMA_TYPE", k, "must be a list of non-empty strings"))
    for k, spec in SUB.items():
        if k not in d:
            continue
        o = d[k]
        if not isinstance(o, dict):
            out.append(finding("SCHEMA_TYPE", k, "must be an object"))
            continue
        for f, kind in spec.items():
            if f not in o:
                out.append(finding("SCHEMA_MISSING", k + "." + f, "required field missing"))
            elif not _kind_ok(kind, o[f]):
                code = "SCHEMA_ENUM" if kind == "e" else "SCHEMA_TYPE"
                out.append(finding(code, k + "." + f, "wrong type, value or empty"))
        for f in o:
            if f not in spec and f not in SUB_OPTIONAL.get(k, []):
                out.append(finding("UNKNOWN_KEY", k + "." + f, "field not in schema"))
    ev = d.get("evidence")
    if "evidence" in d:
        if not isinstance(ev, list):
            out.append(finding("SCHEMA_TYPE", "evidence", "must be a list"))
        else:
            for i, e in enumerate(ev):
                p = "evidence[%d]" % i
                if not isinstance(e, dict):
                    out.append(finding("SCHEMA_TYPE", p, "must be an object"))
                    continue
                for f, kind in (("ref", "s"), ("task_id", "s"), ("revision", "i"), ("observed_at", "t")):
                    if f not in e:
                        out.append(finding("SCHEMA_MISSING", p + "." + f, "required field missing"))
                    elif not _kind_ok(kind, e[f]):
                        out.append(finding("SCHEMA_TYPE", p + "." + f, "wrong type or empty"))
    return out


def _timestamps(d):
    """Return ({path: datetime|None}, findings) for every timestamp in the envelope."""
    found, out = {}, []
    paths = [("source.identity_at", d["source"]["identity_at"]), ("source.revision_at", d["source"]["revision_at"]),
             ("observed_at.envelope", d["observed_at"]["envelope"]), ("observed_at.worker", d["observed_at"]["worker"]),
             ("observed_at.result", d["observed_at"]["result"])]
    for i, e in enumerate(d["evidence"]):
        paths.append(("evidence[%d].observed_at" % i, e["observed_at"]))
    for p, v in paths:
        try:
            found[p] = parse_ts(v)
        except (ValueError, TypeError):
            found[p] = None
            out.append(finding("BAD_TIMESTAMP", p, "not an ISO-8601 timestamp with offset or UNKNOWN"))
    return found, out


def validate(d):
    """Findings for one envelope. Empty list = shape and internal consistency hold."""
    if not isinstance(d, dict):
        return [finding("SCHEMA_TYPE", "$", "envelope must be an object")]
    out = _shape(d)
    if any(f["code"] in ("SCHEMA_MISSING", "SCHEMA_TYPE", "SCHEMA_ENUM") for f in out):
        return out  # cross-field rules need a well-formed record
    ts, bad = _timestamps(d)
    out += bad
    # stale evidence: an observation older than the source identity or revision it cites
    refs = [ts[k] for k in ("source.identity_at", "source.revision_at") if ts.get(k)]
    if refs:
        newest = max(refs)
        for p, t in ts.items():
            if p.startswith("source."):
                continue
            if t is not None and t < newest:
                out.append(finding("STALE_EVIDENCE", p, "observed before the cited source identity/revision"))
    tid, rev = d["task_id"], d["revision"]
    for i, e in enumerate(d["evidence"]):
        if e["task_id"] != tid:
            out.append(finding("WRONG_TASK", "evidence[%d].task_id" % i, "evidence is for task " + e["task_id"]))
        elif e["revision"] != rev:
            out.append(finding("STALE_REVISION", "evidence[%d].revision" % i,
                               "evidence cites rev %d, envelope is rev %d" % (e["revision"], rev)))
    r, w, st = d["result"], d["worker"], d["state"]
    if r["task_id"] is not None and r["task_id"] != tid:
        out.append(finding("WRONG_TASK", "result.task_id", "result is for task " + r["task_id"]))
    elif r["revision"] is not None and r["revision"] != rev:
        out.append(finding("STALE_REVISION", "result.revision", "result cites rev %d, envelope is rev %d" % (r["revision"], rev)))
    if st == "RUNNING":
        missing = [k for k in ("host", "unit", "child") if w[k] == UNKNOWN]
        if missing or d["observed_at"]["worker"] == UNKNOWN:
            out.append(finding("RUNNING_NO_EVIDENCE", "worker",
                               "RUNNING needs observed host+unit+child (missing: %s)" %
                               ",".join(missing + (["observed_at.worker"] if d["observed_at"]["worker"] == UNKNOWN else []))))
    if st == "DONE":
        if not (r["artifact"] or r["event"]):
            out.append(finding("DONE_NO_ARTIFACT", "result", "DONE needs a durable result artifact or event"))
        elif r["task_id"] is None or r["revision"] is None:
            out.append(finding("RESULT_UNBOUND", "result", "result does not state which task and revision it answers"))
    if d["effect"]["state"] in ("applied", "UNKNOWN") and not d["effect"]["no_replay"]:
        out.append(finding("NO_REPLAY_POLICY", "effect.no_replay", "an applied or UNKNOWN effect must carry no_replay=true"))
    if d["ack"]["accepted"] and not d["ack"]["evidence"]:
        out.append(finding("INVENTED_ACK", "ack", "accepted=true without evidence of the consumer's ACK"))
    if d["declared_complete"]:
        req = {"current_owner": d["current_owner"], "owner_reachable": d["owner_reachable"],
               "effect.state": d["effect"]["state"], "consumer.named": d["consumer"]["named"],
               "consumer.available": d["consumer"]["available"], "next_action": d["next_action"],
               "source.identity_at": d["source"]["identity_at"], "source.revision_at": d["source"]["revision_at"]}
        req.update({"target." + k: v for k, v in d["target"].items()})
        req.update({"worker." + k: v for k, v in w.items()})
        unk = sorted(k for k, v in req.items() if v == UNKNOWN)
        if unk or d["coverage_gaps"]:
            out.append(finding("FALSE_COMPLETE", "declared_complete",
                               "declared complete with UNKNOWN: %s; coverage gaps listed: %d" % (",".join(unk) or "-", len(d["coverage_gaps"]))))
    return out


def _records(obj):
    if isinstance(obj, dict) and "envelopes" in obj:
        return obj["envelopes"], obj.get("declared_total")
    if isinstance(obj, list):
        return obj, None
    return [obj], None


def validate_set(obj):
    """Per-envelope findings plus set rules: duplicate task, conflicting live target, derived count."""
    recs, declared = _records(obj)
    if not isinstance(recs, list):
        return {"derived_count": 0, "findings_by_index": [], "set_findings": [finding("SCHEMA_TYPE", "envelopes", "must be a list")]}
    by_idx = [validate(r) for r in recs]
    sets = []
    wf = [r for r in recs if isinstance(r, dict)]
    ids = {}
    for i, r in enumerate(recs):
        if isinstance(r, dict) and isinstance(r.get("task_id"), str):
            ids.setdefault(r["task_id"], []).append(i)
    for tid, idx in ids.items():
        if len(idx) > 1:
            f = finding("DUPLICATE_TASK", "task_id", "task %s appears %d times" % (tid, len(idx)))
            sets.append(f)
            for i in idx:
                by_idx[i].append(f)
    live = {}
    for i, r in enumerate(recs):
        if not (isinstance(r, dict) and isinstance(r.get("target"), dict) and r.get("state") in ("RUNNING", "NOT_STARTED")):
            continue
        t = r["target"]
        if isinstance(t.get("repo"), str) and isinstance(t.get("branch"), str) and UNKNOWN not in (t["repo"], t["branch"]):
            live.setdefault((t["repo"], t["branch"]), []).append(i)
    for key, idx in live.items():
        tasks = {recs[i]["task_id"] for i in idx}
        if len(tasks) < 2:
            continue
        running = [i for i in idx if recs[i]["state"] == "RUNNING"]
        refused = [i for i in idx if recs[i]["state"] != "RUNNING"] if len(running) == 1 else idx
        f = finding("CONFLICTING_TARGET", "target", "%d live tasks share %s@%s" % (len(tasks), key[0], key[1]))
        sets.append(f)
        for i in refused:
            by_idx[i].append(f)
    if declared is not None and declared != len(recs):
        sets.append(finding("DECLARED_COUNT_MISMATCH", "declared_total",
                            "declared %r, enumerated %d (enumerated count is used)" % (declared, len(recs)), "WARN"))
    return {"derived_count": len(recs), "findings_by_index": by_idx, "set_findings": sets}


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    rc = 0
    for path in argv:
        try:
            with open(path) as fh:
                obj = json.load(fh)
        except (OSError, ValueError) as e:
            print("UNREADABLE %s: %s" % (path, e))
            rc = max(rc, 2)
            continue
        res = validate_set(obj)
        print("%s: %d envelope(s) enumerated" % (path, res["derived_count"]))
        everything = [(i, f) for i, fs in enumerate(res["findings_by_index"]) for f in fs]
        everything += [(None, f) for f in res["set_findings"]
                       if not any(f is g for _, g in everything)]
        for i, f in everything:
            print("%s %s [%s] %s: %s" % (f["severity"], f["code"], "set" if i is None else i, f["path"], f["message"]))
        if any(f["severity"] == "REFUSE" for _, f in everything):
            rc = max(rc, 1)
        elif not everything:
            print("OK (shape and internal consistency only; not production evidence)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
