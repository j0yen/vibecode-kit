#!/usr/bin/env python3
"""Decide whether a "message lost" finding is supported by a traced path (stdlib, read-only).

A finding that claims a message is lost needs every link of producer -> alias adapter -> installed
waiter, each with a ref and an identity (sha256 or commit), the waiter additionally installed with a
stated sha256 and a verdict for the producer's actor. The adapter stage needs either adapter links or
an explicit adapters_none_evidence ref. A missing link keeps the finding conditional-risk and is named;
a complete trace whose waiter refuses the (mapped) actor may be observed-defect; one the waiter
accepts is a positive control. Findings with another claim pass through untouched.
Links are typed: ref a non-blank string, sha256 64 hex or commit 40 hex, adapters_none_evidence a non-blank
ref string. Links must agree: family, interface and message, where stated, are equal across producer,
adapters and waiter, and the actor chain holds (producer actor -> adapter maps_from/maps_to -> waiter
actor); a disagreeing link is named and the finding stays conditional-risk. claim and label are matched
after trim, lower-casing and "_"/space -> "-". Non-object or duplicate-key input is unreadable (exit 2).
finding JSON: {id, claim, label, trace: {producer, adapters: [..], adapters_none_evidence, waiter}}
usage: lost_message_check.py FINDING.json   (exit 0 ok, 1 refused: observed-defect without a full trace, 2 unreadable)
"""
import json
import re
import sys

CLAIM = "message-lost"
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
HEX40 = re.compile(r"^[0-9a-fA-F]{40}$")


def _pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {k!r}")
        seen.add(k)
    return dict(pairs)


def _norm(v):
    return re.sub(r"[\s_]+", "-", v.strip().lower()) if isinstance(v, str) else v


def _str(v):
    return isinstance(v, str) and bool(v.strip())


def _ok(link):
    return (isinstance(link, dict) and _str(link.get("ref")) and link.get("available") is not False
            and ((isinstance(link.get("sha256"), str) and bool(HEX64.match(link["sha256"])))
                 or (isinstance(link.get("commit"), str) and bool(HEX40.match(link["commit"])))))


def _consistency(t):
    """Names of links that disagree with the rest of the trace on family, interface, message or actor."""
    links = [("producer", t.get("producer"))]
    ad = t.get("adapters") if isinstance(t.get("adapters"), list) else []
    links += [(f"adapters[{i}]", a) for i, a in enumerate(ad)]
    links.append(("waiter", t.get("waiter")))
    bad = []
    for fld in ("family", "interface", "message"):
        vals = [(n, l[fld]) for n, l in links if isinstance(l, dict) and fld in l]
        if len({json.dumps(v, sort_keys=True) for _, v in vals}) > 1:
            first = vals[0][1]
            bad += [f"{n}: {fld} {v!r} differs from {vals[0][0]} {first!r}" for n, v in vals[1:]
                    if json.dumps(v, sort_keys=True) != json.dumps(first, sort_keys=True)]
    p = t.get("producer")
    cur = p.get("actor") if isinstance(p, dict) else None
    for i, a in enumerate(ad):
        if not isinstance(a, dict):
            continue
        if cur is not None and "maps_from" in a and a["maps_from"] != cur:
            bad.append(f"adapters[{i}]: maps_from {a['maps_from']!r} is not the actor reaching it ({cur!r})")
        if "maps_to" in a:
            cur = a["maps_to"]
    w = t.get("waiter")
    if isinstance(w, dict) and cur is not None and "actor" in w and w["actor"] != cur:
        bad.append(f"waiter: actor {w['actor']!r} is not the actor reaching it ({cur!r})")
    return bad


def classify(f):
    claim, label = _norm(f.get("claim")), _norm(f.get("label"))
    if claim != CLAIM:
        return {"id": f.get("id"), "label": f.get("label"), "missing_links": [], "inconsistent_links": [], "ok": True}
    t = f.get("trace") if isinstance(f.get("trace"), dict) else {}
    missing = []
    if not _ok(t.get("producer")):
        missing.append("producer")
    ad = t.get("adapters")
    if not ((isinstance(ad, list) and ad and all(_ok(a) for a in ad))
            or (isinstance(ad, list) and not ad and _str(t.get("adapters_none_evidence")))):
        missing.append("adapter")
    w = t.get("waiter")
    if not (_ok(w) and w.get("installed_state") == "installed" and isinstance(w.get("sha256"), str)
            and HEX64.match(w["sha256"])):
        missing.append("waiter-installed")
    inconsistent = _consistency(t)
    verdict = w.get("verdict_for_actor") if isinstance(w, dict) else None
    if missing or inconsistent:
        new = "conditional-risk"
    elif verdict == "accept":
        new = "positive-control"
    elif verdict == "refuse":
        new = "observed-defect"
    else:
        new, missing = "conditional-risk", ["waiter-verdict"]
    ok = not (label == "observed-defect" and new != "observed-defect")
    return {"id": f.get("id"), "label": new, "missing_links": missing, "inconsistent_links": inconsistent,
            "verdict_for_actor": verdict if isinstance(verdict, str) else None, "ok": ok}


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            f = json.load(fh, object_pairs_hook=_pairs)
    except (OSError, ValueError, RecursionError) as e:
        print(f"UNKNOWN: finding unreadable: {e}", file=sys.stderr)
        return 2
    if not isinstance(f, dict):
        print(f"UNKNOWN: finding unreadable: top level is {type(f).__name__}, not an object", file=sys.stderr)
        return 2
    res = classify(f)
    print(json.dumps(res, indent=2))
    if not res["ok"]:
        why = []
        if res["missing_links"]:
            why.append("lacks: " + ", ".join(res["missing_links"]))
        if res["inconsistent_links"]:
            why.append("inconsistent: " + "; ".join(res["inconsistent_links"]))
        if not why:
            why.append(f"lacks: a refusing waiter verdict (it is {res.get('verdict_for_actor')!r})")
        print(f"REFUSED: {res['id']} claims observed-defect but the trace {' | '.join(why)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
