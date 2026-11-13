#!/usr/bin/env python3
"""Convert canonical-queue rows (`wm-asks asks query --json` shape) into worker-fit envelopes.

The queue row is silent about workers, effects, consumers and timestamps with an offset, so every such
field stays UNKNOWN. A claim string is carried verbatim in source.claim; it is a queue entry, not a
worker launch, and never fills worker.host/unit/child. Nothing is invented: a row with no ask_id or rev
yields an empty identity that the validator refuses. Read-only; standard library only.
Credential-shaped values are redacted from the printed envelopes (claim strings, owners).
Exit 0 on output, 2 (UNREADABLE) when the input is not JSON or not a list of rows.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import envelope_validate as ev  # noqa: E402

UNKNOWN = "UNKNOWN"


def row_to_envelope(row, observed_at=UNKNOWN):
    ask_id = row.get("ask_id") if isinstance(row.get("ask_id"), str) else ""
    if ev.find_dups(row):  # a row with a repeated key is ambiguous: no identity, so the validator refuses it
        ask_id = ""
    rev = row.get("rev") if isinstance(row.get("rev"), int) and not isinstance(row.get("rev"), bool) else None
    gaps = ["queue row is silent about worker, effect, consumer and target; all UNKNOWN",
            "queue timestamps carry no offset; source identity/revision times left UNKNOWN",
            "queue status=%s; a queue status is not delivery evidence" % row.get("status", UNKNOWN)]
    src = {"owner": str(row.get("owner") or UNKNOWN),
           "identity": "queue row %s seq %s rev %s" % (row.get("row_id", UNKNOWN), row.get("seq", UNKNOWN), rev),
           "identity_at": UNKNOWN, "revision_at": UNKNOWN}
    if row.get("claim"):
        src["claim"] = str(row["claim"])
        gaps.append("claim string present but not a worker launch: no observed child/process")
    if row.get("waits_on"):
        gaps.append("row waits on %s" % ",".join(map(str, row["waits_on"])))
    return {
        "schema": "worker-fit-envelope/1", "label": "adapter output from a queue row; UNKNOWN kept where silent",
        "parent": UNKNOWN, "task_id": ask_id, "revision": rev, "approved_ac_refs": [],
        "work_shape": UNKNOWN, "source": src, "current_owner": str(row.get("owner") or UNKNOWN),
        "owner_reachable": UNKNOWN,
        "target": {"repo": UNKNOWN, "branch": UNKNOWN, "head": UNKNOWN},
        "worker": {k: UNKNOWN for k in ("host", "unit", "invocation", "child", "session", "account", "model", "effort")},
        "state": UNKNOWN,
        "effect": {"state": UNKNOWN, "no_replay": True, "policy": "UNKNOWN effect: never replay"},
        "result": {"artifact": None, "event": None, "task_id": None, "revision": None, "reviewed": UNKNOWN},
        "consumer": {"named": UNKNOWN, "alternate": None, "alternate_authorized": False, "available": UNKNOWN},
        "ack": {"accepted": False, "evidence": None},
        "next_action": UNKNOWN,
        "observed_at": {"envelope": observed_at, "worker": UNKNOWN, "result": UNKNOWN},
        "evidence": [{"ref": "queue row %s" % row.get("row_id", UNKNOWN), "task_id": ask_id,
                      "revision": rev if rev is not None else 0, "observed_at": observed_at}],
        "coverage_gaps": gaps, "declared_complete": False,
    }


def rows_to_envelopes(rows, observed_at=UNKNOWN):
    """Envelopes for canonical queue rows. ValueError when the input is not a list of rows (or {"rows": [...]})."""
    if isinstance(rows, dict):
        rows = rows.get("rows", [])
    if not isinstance(rows, list):
        raise ValueError("rows must be a list")
    return [row_to_envelope(r if isinstance(r, dict) else {}, observed_at) for r in rows]


def main(argv):
    if not argv:
        ev.emit("usage: queue_adapter.py ROWS.json [OBSERVED_AT]")
        return 2
    try:
        obj = ev.load_json_file(argv[0])
        envs = rows_to_envelopes(obj, argv[1] if len(argv) > 1 else UNKNOWN)
    except (OSError, ValueError) as e:
        ev.emit(ev.redact("UNREADABLE %s: %s" % (argv[0], e)))
        return 2
    ev.emit(json.dumps(ev.scrub({"envelopes": envs}), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
