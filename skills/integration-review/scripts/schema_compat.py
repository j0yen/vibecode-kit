#!/usr/bin/env python3
"""Compare two JSON-schema documents (the subset used by register.schema.json) by consumer direction.

A schema describes a message: producers write it, consumers read it. During a rolling change one side
runs the old schema, so every change is classified for who is on the new schema:
  --direction producer-first  new schema on producers, OLD consumers still running
  --direction consumer-first  new schema on consumers, OLD producers still running
  --direction both            must be safe in either order (default)
  --consumer closed|open      closed (default): a consumer rejects values outside its schema;
                              open: it tolerates them. Decides enum/constraint handling.
Rules (L = loosened constraint, e.g. enum value added, type widened, pattern removed, minLength down;
T = tightened constraint, e.g. enum value removed, type narrowed, pattern added, minLength up):
  L: producer-first incompatible if consumer closed, consumer-first compatible
  T: producer-first compatible, consumer-first incompatible if consumer closed
  required added: consumer-first incompatible; required removed: producer-first incompatible
  property added: producer-first incompatible only if the old schema is additionalProperties:false
  property removed: producer-first incompatible; consumer-first incompatible if new is closed
  additionalProperties true->false: consumer-first incompatible; false->true: producer-first incompatible
  incomparable type change, unsupported keyword: incompatible; a pattern that changed text is
  UNDETERMINED (regexes are not compared) and is never reported compatible.
Pure comparison of two files; nothing is executed or fetched.
usage: schema_compat.py OLD.json NEW.json [--direction D] [--consumer C]   (exit 0 compatible, 1 not, 2 usage)
"""
import json
import sys

KNOWN = {"$schema", "title", "description", "type", "enum", "required", "properties",
         "additionalProperties", "items", "pattern", "minLength", "minItems", "definitions", "$ref"}
DIRECTIONS = ("producer-first", "consumer-first", "both")
CONSUMERS = ("closed", "open")


def _types(v):
    return set(v) if isinstance(v, list) else {v}


def _one(kind, d, closed, ctx):
    """(compatible?, reason) for one change kind under direction d (producer-first|consumer-first)."""
    pf = d == "producer-first"
    if kind == "loosen":
        return (not (pf and closed), "an old closed consumer receives a value outside its schema" if pf and closed else "")
    if kind == "tighten":
        return (not (not pf and closed), "an old producer may still send what the new closed consumer rejects" if not pf and closed else "")
    if kind == "req_add":
        return (pf, "old producers do not send the newly required field" if not pf else "")
    if kind == "req_rm":
        return (not pf, "old consumers still require a field new producers may omit" if pf else "")
    if kind == "prop_add":
        bad = pf and ctx.get("old_closed")
        return (not bad, "old consumer rejects additional properties" if bad else "")
    if kind == "prop_rm":
        bad = pf or (not pf and ctx.get("new_closed"))
        return (not bad, "old consumers may read the removed property" if pf else "new consumer rejects the removed property")
    if kind == "ap_tight":
        return (pf, "old producers may send properties the new consumer rejects" if not pf else "")
    if kind == "ap_loose":
        return (not pf, "new producers may send properties an old closed consumer rejects" if pf else "")
    return (False, "incompatible change")


def _classify(res, path, change, kind, direction, consumer, ctx=None):
    ctx = ctx or {}
    closed = consumer == "closed"
    if kind in ("incomparable", "unsupported"):
        verdict, reason = "incompatible", {"incomparable": "type change is neither widening nor narrowing",
                                           "unsupported": "keyword outside the supported set"}[kind]
    elif kind == "undetermined":
        verdict, reason = "undetermined", "regex text changed; direction cannot be decided mechanically"
    elif kind in ("removed_def",):
        verdict, reason = "incompatible", "definition removed"
    elif kind == "added_def":
        verdict, reason = "compatible", ""
    else:
        ds = ("producer-first", "consumer-first") if direction == "both" else (direction,)
        bad = [(d, r) for d in ds for ok, r in [_one(kind, d, closed, ctx)] if not ok]
        verdict = "incompatible" if bad else "compatible"
        reason = "; ".join(f"{d}: {r}" for d, r in bad)
    c = {"path": path, "change": change, "kind": kind, "direction": direction,
         "handling": consumer, "verdict": verdict, "reason": reason}
    res["classified"].append(c)
    text = f"{path}: {change}" + (f" [{direction}, {consumer} consumer: {reason}]" if reason else "")
    if verdict == "incompatible":
        res["breaking"].append(text)
    elif verdict == "undetermined":
        res["undetermined"].append(text)
    else:
        res["additions"].append(text)


def _walk(old, new, path, res, direction, consumer):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return
    cl = lambda *a, **k: _classify(res, path, *a, direction=direction, consumer=consumer, **k)  # noqa: E731
    for k in new:
        if k not in KNOWN:
            cl(f"unsupported keyword {k!r}", "unsupported")
    if "type" in old and "type" in new:
        o, n = _types(old["type"]), _types(new["type"])
        if n > o:
            cl(f"type widened {old['type']!r} -> {new['type']!r}", "loosen")
        elif n < o:
            cl(f"type narrowed {old['type']!r} -> {new['type']!r}", "tighten")
        elif n != o:
            cl(f"type changed {old['type']!r} -> {new['type']!r}", "incomparable")
    if "enum" in old and "enum" in new:
        for v in new["enum"]:
            if v not in old["enum"]:
                cl(f"enum value {v!r} added", "loosen")
        for v in old["enum"]:
            if v not in new["enum"]:
                cl(f"enum value {v!r} removed", "tighten")
    elif "enum" in new:
        cl("enum constraint added", "tighten")
    elif "enum" in old:
        cl("enum constraint removed", "loosen")
    if old.get("pattern") != new.get("pattern"):
        if "pattern" not in old:
            cl(f"pattern {new['pattern']!r} added", "tighten")
        elif "pattern" not in new:
            cl("pattern removed", "loosen")
        else:
            cl(f"pattern changed {old['pattern']!r} -> {new['pattern']!r}", "undetermined")
    for kw in ("minLength", "minItems"):
        o, n = old.get(kw, 0), new.get(kw, 0)
        if n > o:
            cl(f"{kw} raised {o} -> {n}", "tighten")
        elif n < o:
            cl(f"{kw} lowered {o} -> {n}", "loosen")
    for r in new.get("required", []):
        if r not in old.get("required", []):
            cl(f"{r!r} newly required", "req_add")
    for r in old.get("required", []):
        if r not in new.get("required", []):
            cl(f"{r!r} no longer required", "req_rm")
    oc = old.get("additionalProperties", True) is False
    nc = new.get("additionalProperties", True) is False
    if not oc and nc:
        cl("additionalProperties tightened", "ap_tight")
    elif oc and not nc:
        cl("additionalProperties loosened", "ap_loose")
    ctx = {"old_closed": oc, "new_closed": nc}
    for section in ("properties", "definitions"):
        op, np_ = old.get(section, {}), new.get(section, {})
        for name in op:
            if name not in np_:
                cl(f"{section}/{name} removed", "prop_rm" if section == "properties" else "removed_def", ctx=ctx)
            else:
                _walk(op[name], np_[name], f"{path}/{section}/{name}", res, direction, consumer)
        for name in np_:
            if name not in op:
                cl(f"{section}/{name} added", "prop_add" if section == "properties" else "added_def", ctx=ctx)
                _walk({}, np_[name], f"{path}/{section}/{name}", {"classified": [], "breaking": [],
                                                                    "additions": [], "undetermined": []},
                      direction, consumer)
    if "items" in old and "items" in new:
        _walk(old["items"], new["items"], f"{path}/items", res, direction, consumer)


def compare(old, new, direction="both", consumer="closed"):
    if direction not in DIRECTIONS or consumer not in CONSUMERS:
        raise ValueError(f"direction must be one of {DIRECTIONS}, consumer one of {CONSUMERS}")
    res = {"classified": [], "breaking": [], "additions": [], "undetermined": []}
    _walk(old, new, "#", res, direction, consumer)
    ok = not res["breaking"] and not res["undetermined"]
    return {"compatible": ok, "additive": ok and bool(res["additions"]), "direction": direction,
            "consumer": consumer, **res}


def main(argv):
    args = argv[1:]
    opts = {"--direction": "both", "--consumer": "closed"}
    files = []
    i = 0
    while i < len(args):
        if args[i] in opts and i + 1 < len(args):
            opts[args[i]] = args[i + 1]
            i += 2
        else:
            files.append(args[i])
            i += 1
    if len(files) != 2 or opts["--direction"] not in DIRECTIONS or opts["--consumer"] not in CONSUMERS:
        print(__doc__, file=sys.stderr)
        return 2
    with open(files[0]) as a, open(files[1]) as b:
        res = compare(json.load(a), json.load(b), opts["--direction"], opts["--consumer"])
    print(json.dumps(res, indent=2))
    return 0 if res["compatible"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
