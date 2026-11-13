#!/usr/bin/env python3
"""Decide whether a "message lost" finding is supported by a traced path (stdlib, read-only).

A finding that claims a message is lost needs every link of producer -> alias adapter -> installed
waiter, each with a ref and an identity (sha256 or commit), the waiter additionally installed with a
stated sha256 and a verdict for the producer's actor. The adapter stage needs either adapter links or
an explicit adapters_none_evidence ref. A missing link keeps the finding conditional-risk and is named;
a complete trace whose waiter refuses the (mapped) actor may be observed-defect; one the waiter
accepts is a positive control. Findings with another claim pass through untouched.
finding JSON: {id, claim, label, trace: {producer, adapters: [..], adapters_none_evidence, waiter}}
usage: lost_message_check.py FINDING.json   (exit 0 ok, 1 refused: observed-defect without a full trace, 2 unreadable)
"""
import json
import sys

CLAIM = "message-lost"


def _ok(link):
    return (isinstance(link, dict) and bool(link.get("ref")) and link.get("available") is not False
            and bool(link.get("sha256") or link.get("commit")))


def classify(f):
    claim, label = f.get("claim"), f.get("label")
    if claim != CLAIM:
        return {"id": f.get("id"), "label": label, "missing_links": [], "ok": True}
    t = f.get("trace") if isinstance(f.get("trace"), dict) else {}
    missing = []
    if not _ok(t.get("producer")):
        missing.append("producer")
    ad = t.get("adapters")
    if not ((isinstance(ad, list) and ad and all(_ok(a) for a in ad))
            or (isinstance(ad, list) and not ad and t.get("adapters_none_evidence"))):
        missing.append("adapter")
    w = t.get("waiter")
    if not (_ok(w) and w.get("installed_state") == "installed" and w.get("sha256")):
        missing.append("waiter-installed")
    if missing:
        new = "conditional-risk"
    elif (t["waiter"].get("verdict_for_actor")) == "accept":
        new = "positive-control"
    elif t["waiter"].get("verdict_for_actor") == "refuse":
        new = "observed-defect"
    else:
        new, missing = "conditional-risk", ["waiter-verdict"]
    ok = not (label == "observed-defect" and new != "observed-defect")
    return {"id": f.get("id"), "label": new, "missing_links": missing, "ok": ok}


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[1]) as fh:
            f = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"UNKNOWN: finding unreadable: {e}", file=sys.stderr)
        return 2
    res = classify(f)
    print(json.dumps(res, indent=2))
    if not res["ok"]:
        print(f"REFUSED: {res['id']} claims observed-defect but the trace lacks: {', '.join(res['missing_links'])}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
