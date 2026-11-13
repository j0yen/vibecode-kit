#!/usr/bin/env python3
"""Compare two JSON-schema documents (the subset used by register.schema.json).

breaking: removed property, newly required property, type change, removed enum value, tightened
additionalProperties, or a keyword outside the supported set. additive: new optional property or
new enum value. Pure comparison of two files; nothing is executed or fetched.
usage: schema_compat.py OLD.json NEW.json   (exit 0 compatible, 1 breaking)
"""
import json
import sys

KNOWN = {"$schema", "title", "description", "type", "enum", "required", "properties",
         "additionalProperties", "items", "pattern", "minLength", "minItems", "definitions", "$ref"}


def _types(v):
    return set(v) if isinstance(v, list) else {v}


def _walk(old, new, path, breaking, additive):
    if not isinstance(old, dict) or not isinstance(new, dict):
        return
    for k in new:
        if k not in KNOWN:
            breaking.append(f"{path}: unsupported keyword {k!r}")
    if "type" in old and "type" in new and not _types(new["type"]) >= _types(old["type"]):
        breaking.append(f"{path}: type changed {old['type']!r} -> {new['type']!r}")
    if "enum" in old and "enum" in new:
        for v in old["enum"]:
            if v not in new["enum"]:
                breaking.append(f"{path}: enum value {v!r} removed")
        for v in new["enum"]:
            if v not in old["enum"]:
                additive.append(f"{path}: enum value {v!r} added")
    for r in new.get("required", []):
        if r not in old.get("required", []):
            breaking.append(f"{path}: {r!r} newly required")
    if old.get("additionalProperties", True) is not False and new.get("additionalProperties", True) is False:
        breaking.append(f"{path}: additionalProperties tightened")
    for section in ("properties", "definitions"):
        op, np_ = old.get(section, {}), new.get(section, {})
        for name in op:
            if name not in np_:
                breaking.append(f"{path}/{section}/{name}: removed")
            else:
                _walk(op[name], np_[name], f"{path}/{section}/{name}", breaking, additive)
        for name in np_:
            if name not in op:
                additive.append(f"{path}/{section}/{name}: added")
                _walk({}, np_[name], f"{path}/{section}/{name}", breaking, [])
    if "items" in old and "items" in new:
        _walk(old["items"], new["items"], f"{path}/items", breaking, additive)


def compare(old, new):
    breaking, additive = [], []
    _walk(old, new, "#", breaking, additive)
    return {"compatible": not breaking, "additive": bool(additive) and not breaking,
            "breaking": breaking, "additions": additive}


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    with open(argv[1]) as a, open(argv[2]) as b:
        res = compare(json.load(a), json.load(b))
    print(json.dumps(res, indent=2))
    return 0 if res["compatible"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
