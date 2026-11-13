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
after trim, lower-casing and "_"/space -> "-". An actor chain that returns to an actor already reached
(a -> b -> a; an identity mapping is not a loop) is inconsistent. A trace in which no family, interface or message is
stated on two links, or that lacks the producer or waiter actor, is marked "consistency": "unproven"
with the reasons in "unproven" and an UNPROVEN line; its label is unchanged, the marker is the signal.
Credential-shaped text in any printed value is redacted. Non-object or duplicate-key input is unreadable (exit 2).
finding JSON: {id, claim, label, trace: {producer, adapters: [..], adapters_none_evidence, waiter}}
usage: lost_message_check.py FINDING.json   (exit 0 ok, 1 refused: observed-defect without a full trace, 2 unreadable)
"""
import importlib.util
import json
import os
import re
import sys


def _load_norm():
    m = sys.modules.get("ir_norm")
    if m is None:
        spec = importlib.util.spec_from_file_location("ir_norm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_norm.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.modules["ir_norm"] = m
    return m


_N = _load_norm()
redact, redact_obj = _N.redact, _N.redact_obj

CLAIM = "message-lost"
HEX64 = re.compile(r"[0-9a-fA-F]{64}")      # always used with fullmatch: "$" would accept a trailing newline
HEX40 = re.compile(r"[0-9a-fA-F]{40}")


def _pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {redact(k)!r}")
        seen.add(k)
    return dict(pairs)


def _norm(v):
    return re.sub(r"[\s_]+", "-", v.strip().lower()) if isinstance(v, str) else v


def _str(v):
    return isinstance(v, str) and bool(v.strip())


def _ok(link):
    return (isinstance(link, dict) and _str(link.get("ref")) and link.get("available") is not False
            and ((isinstance(link.get("sha256"), str) and bool(HEX64.fullmatch(link["sha256"])))
                 or (isinstance(link.get("commit"), str) and bool(HEX40.fullmatch(link["commit"])))))


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
    chain = [cur] if cur is not None else []
    for i, a in enumerate(ad):
        if not isinstance(a, dict):
            continue
        if cur is not None and "maps_from" in a and a["maps_from"] != cur:
            bad.append(f"adapters[{i}]: maps_from {a['maps_from']!r} is not the actor reaching it ({cur!r})")
        if "maps_to" in a:
            cur = a["maps_to"]
            if chain and cur == chain[-1]:
                continue                      # an identity mapping is not a loop
            if cur in chain:
                bad.append(f"adapters[{i}]: actor chain cycle, {cur!r} was already reached")
            chain.append(cur)
    w = t.get("waiter")
    if isinstance(w, dict) and cur is not None and "actor" in w and w["actor"] != cur:
        bad.append(f"waiter: actor {w['actor']!r} is not the actor reaching it ({cur!r})")
    return bad


def _unproven(t):
    """Reasons the trace is not PROVEN consistent (nothing disagrees, but too little is stated to compare)."""
    links = [("producer", t.get("producer")), ("waiter", t.get("waiter"))]
    links += [(f"adapters[{i}]", a) for i, a in enumerate(t.get("adapters") if isinstance(t.get("adapters"), list) else [])]
    why = []
    if not any(sum(1 for _, l in links if isinstance(l, dict) and fld in l) >= 2
               for fld in ("family", "interface", "message")):
        why.append("none of family, interface or message is stated on two links, so no link is compared")
    p, w = t.get("producer"), t.get("waiter")
    if isinstance(p, dict) and "actor" not in p:
        why.append("producer actor not stated, the verdict is not tied to the producer's actor")
    if isinstance(w, dict) and "actor" not in w:
        why.append("waiter actor not stated, the verdict is not tied to an actor")
    return why


def classify(f):
    claim, label = _norm(f.get("claim")), _norm(f.get("label"))
    if claim != CLAIM:
        return {"id": f.get("id"), "label": f.get("label"), "missing_links": [], "inconsistent_links": [],
                "unproven": [], "consistency": "not-applicable", "ok": True}
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
            and HEX64.fullmatch(w["sha256"])):
        missing.append("waiter-installed")
    inconsistent = _consistency(t)
    unproven = _unproven(t)
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
            "unproven": unproven, "consistency": "proven" if not (unproven or inconsistent) else
            ("inconsistent" if inconsistent else "unproven"),
            "verdict_for_actor": verdict if isinstance(verdict, str) else None, "ok": ok}


def main(argv):
    if len(argv) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            f = json.load(fh, object_pairs_hook=_pairs)
    except (OSError, ValueError, RecursionError) as e:
        print(f"UNKNOWN: finding unreadable: {redact(e)}", file=sys.stderr)
        return 2
    if not isinstance(f, dict):
        print(f"UNKNOWN: finding unreadable: top level is {type(f).__name__}, not an object", file=sys.stderr)
        return 2
    res = classify(f)
    print(json.dumps(redact_obj(res), indent=2))
    if res.get("unproven"):
        print(redact("UNPROVEN: " + res["id"].__str__() + " consistency is not proven: " + "; ".join(res["unproven"])))
    if not res["ok"]:
        why = []
        if res["missing_links"]:
            why.append("lacks: " + ", ".join(res["missing_links"]))
        if res["inconsistent_links"]:
            why.append("inconsistent: " + "; ".join(res["inconsistent_links"]))
        if not why:
            why.append(f"lacks: a refusing waiter verdict (it is {res.get('verdict_for_actor')!r})")
        print(redact(f"REFUSED: {res['id']} claims observed-defect but the trace {' | '.join(why)}"))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
