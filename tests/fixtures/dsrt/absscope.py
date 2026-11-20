#!/usr/bin/env python3
"""Q5 fixture helper (A1723 source request 6, ruled A by the PRD author): the A1113 shape.

Rewrites, in place, every launch row with role review whose `scope` is relative to the PRD home, so that it names the
same file under another host's root as an absolute path, <root>/<scope>. The PRD home keeps the files; the root does
not exist on this host. Every other line is kept byte for byte.

Usage: absscope.py <decisions.jsonl> <absolute root> [<session>]
  <session>: rewrite only that session's rows. Prints the number of rows rewritten.
"""
import json
import os
import sys


def main(argv):
    if len(argv) not in (2, 3) or not os.path.isabs(argv[1]):
        sys.exit(__doc__)
    path, root = argv[0], argv[1]
    only = argv[2] if len(argv) == 3 else None
    out, n = [], 0
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    for ln in lines:
        try:
            r = json.loads(ln)
        except ValueError:
            out.append(ln)
            continue
        if (isinstance(r, dict) and r.get("decision") == "launch" and r.get("role") == "review"
                and isinstance(r.get("scope"), str) and r["scope"] and not os.path.isabs(r["scope"])
                and (only is None or r.get("session") == only)):
            out.append(json.dumps(dict(r, scope=os.path.join(root, r["scope"]))))
            n += 1
        else:
            out.append(ln)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("".join(x + "\n" for x in out))
    print(n)


if __name__ == "__main__":
    main(sys.argv[1:])
