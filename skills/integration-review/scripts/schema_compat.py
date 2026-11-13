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
  items constraint added = T, removed = L (an empty items schema is no constraint); a changed items form
  (schema vs tuple list) is incompatible; enum values compare by JSON type (1 differs from true, 1 equals 1.0)
  type present in only one schema: added = T, removed = L; $ref retargeted (or swapped with an inline schema):
  the two targets are compared, an unresolvable target (not "#/..." in its own document) is UNDETERMINED;
  additionalProperties as a schema: open->schema = T, schema->open = L, schema->schema compared;
  incomparable type change, unsupported keyword in OLD or NEW (so a removed one too): incompatible; a pattern that changed text is
  UNDETERMINED (regexes are not compared) and is never reported compatible.
Pure comparison of two files; nothing is executed or fetched.
usage: schema_compat.py OLD.json NEW.json [--direction D] [--consumer C]
exit 0 compatible, 1 not compatible, 2 usage or unreadable input (missing, not UTF-8, bad JSON, duplicate
key, not an object); rc 1 is never used for an unreadable input.
"""
import importlib.util
import json
import os
import sys


def _load_norm():
    m = sys.modules.get("ir_norm")
    if m is None:
        spec = importlib.util.spec_from_file_location("ir_norm", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ir_norm.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        sys.modules["ir_norm"] = m
    return m


redact = _load_norm().redact

ANNOTATIONS = {"format", "default", "examples", "example", "$comment", "$id", "id", "deprecated", "readOnly", "writeOnly",
               "contentEncoding", "contentMediaType"}
KNOWN = {"$schema", "title", "description", "type", "enum", "required", "properties",
         "additionalProperties", "items", "pattern", "minLength", "minItems", "definitions", "$ref"}
DIRECTIONS = ("producer-first", "consumer-first", "both")
CONSUMERS = ("closed", "open")


def _pairs(pairs):
    seen = set()
    for k, _ in pairs:
        if k in seen:
            raise ValueError(f"duplicate JSON key {redact(k)!r}")
        seen.add(k)
    return dict(pairs)


def _canon(v):
    """Hashable identity of an enum value: bool is not int, 1 equals 1.0, containers by sorted JSON."""
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, (int, float)):
        return ("num", v)
    return ("json", json.dumps(v, sort_keys=True))


def _constrains(it):
    return isinstance(it, dict) and bool(it)


def _types(v):
    return set(v) if isinstance(v, list) else {v}


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _shape(n):
    """Refuse (ValueError -> rc 2) a node whose keywords have a shape this comparison cannot read."""
    for k in ("properties", "definitions"):
        if k in n and not (isinstance(n[k], dict) and all(isinstance(x, dict) or isinstance(x, bool) for x in n[k].values())):
            raise ValueError(f"{k} is not an object of schemas")
    if "required" in n and not (isinstance(n["required"], list) and all(isinstance(x, str) for x in n["required"])):
        raise ValueError("required is not a list of names")
    if "enum" in n and not isinstance(n["enum"], list):
        raise ValueError("enum is not a list")
    if "type" in n and not (isinstance(n["type"], str) or (isinstance(n["type"], list) and all(isinstance(x, str) for x in n["type"]))):
        raise ValueError("type is not a string or list of strings")
    for k in ("minLength", "minItems"):
        if k in n and not _num(n[k]):
            raise ValueError(f"{k} is not a number")
    if "pattern" in n and not isinstance(n["pattern"], str):
        raise ValueError("pattern is not a string")
    if "$ref" in n and not isinstance(n["$ref"], str):
        raise ValueError("$ref is not a string")
    if "items" in n and not isinstance(n["items"], (dict, list)):
        raise ValueError("items is neither a schema nor a list")


def _ap(n):
    """open | closed | schema for additionalProperties."""
    v = n.get("additionalProperties", True)
    if v is True or v == {}:
        return "open"
    if v is False:
        return "closed"
    if isinstance(v, dict):
        return "schema"
    raise ValueError("additionalProperties is neither boolean nor schema")


def _resolve(root, ref):
    """Local JSON-pointer target of a "#/..." $ref inside its own document, else None."""
    if not isinstance(ref, str) or not (ref == "#" or ref.startswith("#/")):
        return None
    node = root
    for part in [p for p in ref[2:].split("/") if p] if ref != "#" else []:
        part = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) else None


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
        bad = pf and (ctx.get("old_closed") or (closed and ctx.get("ap_rejects")))
        why = ("old consumer rejects additional properties" if ctx.get("old_closed")
               else "the new property's schema is not accepted by the old consumer's additionalProperties schema")
        return (not bad, why if bad else "")
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
        verdict, reason = "undetermined", "direction cannot be decided mechanically (a changed regex or an unevaluated keyword)"
    elif kind in ("removed_def",):
        verdict, reason = "incompatible", "definition removed"
    elif kind in ("added_def", "note", "unchanged_note"):
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
    if kind == "unchanged_note":
        res.setdefault("notes", []).append(text)
    elif verdict == "incompatible":
        res["breaking"].append(text)
    elif verdict == "undetermined":
        res["undetermined"].append(text)
    else:
        res["additions"].append(text)


def _done_node(res, cl, unchanged, before):
    """Unchanged unsupported keywords are not a change: a note when nothing else in the subtree changed, else the
    subtree is UNDETERMINED (their interplay with the change is not evaluated)."""
    if not unchanged:
        return
    names = ", ".join(repr(k) for k in unchanged)
    if len(res["classified"]) > before:
        cl(f"unchanged unsupported keyword(s) {names} may interact with the changes in this subtree; not evaluated", "undetermined")
    else:
        cl(f"unchanged unsupported keyword(s) {names}: equal text on both sides, not evaluated", "unchanged_note")


def _walk(old, new, path, res, direction, consumer, depth=0):
    if not isinstance(old, dict) or not isinstance(new, dict):
        if old != new or isinstance(old, dict) != isinstance(new, dict):
            raise ValueError("subschema is not an object on both sides")
        return
    _shape(old)
    _shape(new)
    cl = lambda *a, **k: _classify(res, path, *a, direction=direction, consumer=consumer, **k)  # noqa: E731
    before_node = len(res["classified"])
    unchanged_applicators = []
    for k in sorted(set(old) | set(new)):
        if k not in KNOWN:
            if k in old and k in new and json.dumps(old[k], sort_keys=True) == json.dumps(new[k], sort_keys=True):
                if k not in ANNOTATIONS:        # unchanged: not a change; noted, and undetermined if the subtree changes
                    unchanged_applicators.append(k)
                continue
            where = "old and new" if k in old and k in new else ("old" if k in old else "new")
            cl(f"unsupported keyword {k!r} in {where}", "unsupported")
    orf, nrf = old.get("$ref"), new.get("$ref")
    if orf != nrf:
        oo = _resolve(res["_roots"][0], orf) if orf is not None else old
        nn = _resolve(res["_roots"][1], nrf) if nrf is not None else new
        if oo is None or nn is None or depth >= 16:
            cl(f"$ref changed {orf!r} -> {nrf!r}; a target is not resolvable in its own document", "undetermined")
        else:
            before = len(res["classified"])
            _walk(oo, nn, f"{path}/$ref", res, direction, consumer, depth + 1)
            if len(res["classified"]) == before:
                cl(f"$ref retargeted {orf!r} -> {nrf!r}; the targets are equivalent", "note")
        _done_node(res, cl, unchanged_applicators, before_node)
        return          # a $ref replaces its siblings: the compared targets are the whole comparison of this node
    if "type" in old and "type" in new:
        o, n = _types(old["type"]), _types(new["type"])
        if n > o:
            cl(f"type widened {old['type']!r} -> {new['type']!r}", "loosen")
        elif n < o:
            cl(f"type narrowed {old['type']!r} -> {new['type']!r}", "tighten")
        elif n != o:
            cl(f"type changed {old['type']!r} -> {new['type']!r}", "incomparable")
    elif "type" in new:
        cl(f"type constraint added {new['type']!r}", "tighten")
    elif "type" in old:
        cl(f"type constraint removed (was {old['type']!r})", "loosen")
    if "enum" in old and "enum" in new:
        oe, ne = {_canon(v) for v in old["enum"]}, {_canon(v) for v in new["enum"]}
        for v in new["enum"]:
            if _canon(v) not in oe:
                cl(f"enum value {v!r} added", "loosen")
        for v in old["enum"]:
            if _canon(v) not in ne:
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
    oa, na = _ap(old), _ap(new)
    oc, nc = oa == "closed", na == "closed"
    if oa == na == "schema":
        _walk(old["additionalProperties"], new["additionalProperties"], f"{path}/additionalProperties",
              res, direction, consumer, depth + 1)
    elif (oa, na) in (("open", "closed"), ("open", "schema"), ("schema", "closed")):
        cl(f"additionalProperties tightened ({oa} -> {na})", "ap_tight")
    elif (oa, na) in (("closed", "open"), ("closed", "schema"), ("schema", "open")):
        cl(f"additionalProperties loosened ({oa} -> {na})", "ap_loose")
    ctx = {"old_closed": oc, "new_closed": nc}
    for section in ("properties", "definitions"):
        op, np_ = old.get(section, {}), new.get(section, {})
        for name in op:
            if name not in np_:
                cl(f"{section}/{name} removed", "prop_rm" if section == "properties" else "removed_def", ctx=ctx)
            else:
                _walk(op[name], np_[name], f"{path}/{section}/{name}", res, direction, consumer, depth + 1)
        for name in np_:
            if name not in op:
                pctx = ctx
                if section == "properties" and oa == "schema":
                    sub = {"classified": [], "breaking": [], "additions": [], "undetermined": [], "_roots": res["_roots"]}
                    _walk(old["additionalProperties"], np_[name], f"{path}/{section}/{name}", sub,
                          "producer-first", consumer, depth + 1)
                    pctx = dict(ctx, ap_rejects=bool(sub["breaking"] or sub["undetermined"]))
                cl(f"{section}/{name} added", "prop_add" if section == "properties" else "added_def", ctx=pctx)
                _walk({}, np_[name], f"{path}/{section}/{name}", {"classified": [], "breaking": [],
                                                                    "additions": [], "undetermined": [],
                                                                    "_roots": res["_roots"]},
                      direction, consumer, depth + 1)
    oi, ni = old.get("items"), new.get("items")
    if isinstance(oi, dict) and isinstance(ni, dict):
        if oi and ni:
            _walk(oi, ni, f"{path}/items", res, direction, consumer, depth + 1)
        elif ni:
            cl("items constraint added", "tighten")
        elif oi:
            cl("items constraint removed", "loosen")
    elif oi != ni and not (oi in (None, {}) and ni in (None, {})):
        if _constrains(ni) and oi is None:
            cl("items constraint added", "tighten")
        elif _constrains(oi) and ni is None:
            cl("items constraint removed", "loosen")
        else:
            cl("items form changed (schema vs list/other)", "unsupported")
    _done_node(res, cl, unchanged_applicators, before_node)


def compare(old, new, direction="both", consumer="closed"):
    if direction not in DIRECTIONS or consumer not in CONSUMERS:
        raise ValueError(f"direction must be one of {DIRECTIONS}, consumer one of {CONSUMERS}")
    res = {"classified": [], "breaking": [], "additions": [], "undetermined": [], "notes": [], "_roots": (old, new)}
    _walk(old, new, "#", res, direction, consumer)
    del res["_roots"]
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
    docs = []
    for fn in files:
        try:
            with open(fn, encoding="utf-8") as fh:
                doc = json.load(fh, object_pairs_hook=_pairs)
        except (OSError, ValueError, RecursionError) as e:
            print(f"UNKNOWN: schema unreadable: {redact(fn)}: {type(e).__name__}: {redact(e)}", file=sys.stderr)
            return 2
        if not isinstance(doc, dict):
            print(f"UNKNOWN: schema unreadable: {fn}: top level is {type(doc).__name__}, not an object", file=sys.stderr)
            return 2
        docs.append(doc)
    try:
        res = compare(docs[0], docs[1], opts["--direction"], opts["--consumer"])
    except (TypeError, AttributeError, LookupError, ValueError, RecursionError) as e:
        print(f"UNKNOWN: schema shape not comparable ({type(e).__name__}: {redact(e)})", file=sys.stderr)
        return 2
    print(json.dumps(res, indent=2))
    return 0 if res["compatible"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
