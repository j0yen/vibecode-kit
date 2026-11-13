#!/usr/bin/env python3
"""Extract an actor-name discriminator from a captured shell file and test names against it.

The file is only read as text: the quoted regex on the named line is parsed out and
applied to a synthetic log line "<ts> | <name> | <msg>". Nothing is executed.

usage: discriminator_check.py FILE --line N --names a,b,c [--sha256 HEX] [--expect-refuse x,y] [--json]
exit: 0 ok, 2 bad input (sha mismatch, no quoted pattern on the line, unsafe name)
"""
import argparse
import hashlib
import json
import re
import sys

NOTE = ("Conditional integration risk: the file does not accept these names; whether any producer "
        "publishes them is not shown. This is not evidence that live messages are lost.")
ASSIGN = re.compile(r"""^\s*(?:export\s+)?[A-Za-z_][A-Za-z0-9_]*=(['"])(.*)\1\s*(?:#.*)?$""")
SAFE = re.compile(r"^[A-Za-z0-9._-]+$")


def extract_pattern(text, line_no):
    lines = text.splitlines()
    if not 1 <= line_no <= len(lines):
        raise ValueError(f"line {line_no} out of range (file has {len(lines)} lines)")
    m = ASSIGN.match(lines[line_no - 1])
    if not m:
        raise ValueError(f"line {line_no} has no quoted NAME='pattern' assignment")
    return m.group(2)


def verdicts(pattern, names):
    rx = re.compile(pattern)
    out = {}
    for n in names:
        if not SAFE.match(n):
            raise ValueError(f"unsafe actor name {n!r}")
        out[n] = "accept" if rx.search(f"2026-11-12T00:00:00 | {n} | message") else "refuse"
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file")
    ap.add_argument("--line", type=int, required=True)
    ap.add_argument("--names", required=True)
    ap.add_argument("--sha256")
    ap.add_argument("--expect-refuse", default="")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        raw = open(a.file, "rb").read()
    except OSError as e:
        print(f"UNKNOWN: source unavailable: {e}", file=sys.stderr)
        return 2
    digest = hashlib.sha256(raw).hexdigest()
    if a.sha256 and digest != a.sha256.lower():
        print(f"sha256 mismatch: file {digest} expected {a.sha256}", file=sys.stderr)
        return 2
    names = [n for n in a.names.split(",") if n]
    expect_refuse = {n for n in a.expect_refuse.split(",") if n}
    try:
        pattern = extract_pattern(raw.decode("utf-8", "replace"), a.line)
        res = verdicts(pattern, names)
    except (ValueError, re.error) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    labels = {n: ("positive-control" if v == "accept" or n in expect_refuse else "conditional-risk")
              for n, v in res.items()}
    if a.json:
        print(json.dumps({"file_sha256": digest, "line": a.line, "pattern": pattern,
                          "results": res, "labels": labels, "note": NOTE}, indent=2))
    else:
        print(f"source sha256 {digest} line {a.line}")
        print(f"pattern {pattern}")
        for n, v in res.items():
            print(f"{v} {n} [{labels[n]}]")
        if any(v == "refuse" and n not in expect_refuse for n, v in res.items()):
            print(NOTE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
