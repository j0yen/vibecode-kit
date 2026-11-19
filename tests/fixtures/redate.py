#!/usr/bin/env python3
"""Re-date fixture trees and regenerate every value derived from their bytes.

Usage: redate.py [--check] --map OLD=NEW [--map OLD=NEW ...] [--also FILE ...] [ROOT ...]

OLD and NEW are YYYY-MM-DD dates. In every regular file under each ROOT, each occurrence of OLD in the bytes and in the path below the ROOT
becomes NEW (a renamed file moves; the ROOT itself keeps its name). Then every value derived from a changed file's bytes is replaced by its new
value wherever it occurs in the rewritten files, repeating until nothing changes:
  - the file's sha256 (64 lowercase hex), and
  - for a sha256sum manifest (non-empty, final LF, every line `<sha256>  <path>` with no white space in the path), its review scope id: the
    sha256 of the canonical scope text (lines `<sha256>  <basename>`, bytewise sorted and de-duplicated, each ending in LF), the value
    `dream-run-note-lint.sh --scope-id` prints.
Each --also FILE (a test script or generator outside the trees that names fixture paths, times or digests) gets the same date and digest
replacements but is not hashed. Times of day, the order of every instant, and every other byte stay as they were.

Refused (exit 2, nothing written):
  - a ROOT or --also file that holds a NEW date already (the map must stay one-to-one, so a later re-date of the result is unambiguous);
  - anything under a ROOT that is not a regular file or a directory, a symlinked directory included, and an --also file that is a ROOT file;
  - an OLD date that occurs in no ROOT and no --also file;
  - two paths renamed onto one;
  - a manifest line that verified before the rewrite (sha256sum -c, paths relative to the manifest's directory) and does not after;
  - a hex run of 8 or more characters left in the rewritten bytes that is a prefix of a replaced value (a short reference this tool cannot
    regenerate);
  - one old value that would map to two new values.
--check computes and verifies everything and writes nothing. Exit 0: written (or checked). Every new file is written to a temporary file beside its
destination first; only when all are written does any replace its target, so a write error (a full disk) leaves the trees as they were (exit 2).
"""
import argparse
import hashlib
import os
import re
import sys

DATE_RE = re.compile(r"\d{4}-\d\d-\d\d")
HEX64 = re.compile(rb"[0-9a-f]{64}")
HEXRUN = re.compile(rb"[0-9a-f]{8,}")
SCOPE_LINE_RE = re.compile(rb"[0-9a-f]{64}  [^\s]+")   # dream-run-note-lint.sh SCOPE_LINE_RE (LC_ALL=C [:space:])


class Refused(Exception):
    pass


def sha(b):
    return hashlib.sha256(b).hexdigest().encode("ascii")


def manifest_lines(data):
    """The (digest, path) lines of a sha256sum manifest, or None when the bytes are not one."""
    if not data or not data.endswith(b"\n"):
        return None
    lines = data[:-1].split(b"\n")
    if not all(SCOPE_LINE_RE.fullmatch(ln) for ln in lines):
        return None
    return [tuple(ln.split(b"  ", 1)) for ln in lines]


def scope_id(lines):
    canon = sorted({h + b"  " + p.rsplit(b"/", 1)[-1] + b"\n" for h, p in lines})
    return sha(b"".join(canon))


def sub_dates(b, pairs):
    for old, new in pairs:
        b = b.replace(old, new)
    return b


def sub_digests(b, dmap):
    return HEX64.sub(lambda m: dmap.get(m.group(0), m.group(0)), b)


def walk(root):
    out = []
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for dn in dirs:
            if os.path.islink(os.path.join(d, dn)):                       # os.walk lists a symlinked directory but does not enter it (review r10 LOW-3)
                raise Refused("not a regular file or directory: %s (a symlink)" % os.path.join(d, dn))
        for f in sorted(files):
            p = os.path.join(d, f)
            if os.path.islink(p) or not os.path.isfile(p):
                raise Refused("not a regular file: %s" % p)
            out.append(p)
    return out


def plan(pairs, roots, also):
    bpairs = [(o.encode(), n.encode()) for o, n in pairs]
    files = {}                              # path -> (root or None, original bytes)
    for r in roots:
        for p in walk(r):
            with open(p, "rb") as fh:
                files[p] = (r, fh.read())
    real = {os.path.realpath(q) for q in files}
    for p in also:
        if p in files or os.path.realpath(p) in real:                      # review r10 LOW-4: an absolute or linked spelling of a ROOT file
            raise Refused("--also file %s is inside a ROOT" % p)
        with open(p, "rb") as fh:
            files[p] = (None, fh.read())
    for o, n in bpairs:
        hit = [p for p, (r, b) in files.items() if n in b or (r is not None and n in os.path.relpath(p, r).encode())]   # --also too (review r10 LOW-5)
        if hit:
            raise Refused("NEW date %s already occurs in %s" % (n.decode(), hit[0]))
        if not any(o in b or (r is not None and o in os.path.relpath(p, r).encode()) for p, (r, b) in files.items()):
            raise Refused("OLD date %s occurs nowhere" % o.decode())
    newpath = {}
    for p, (r, _) in files.items():
        newpath[p] = p if r is None else os.path.join(r, sub_dates(os.path.relpath(p, r).encode(), bpairs).decode())
    seen = {}
    for p, q in newpath.items():
        if q in seen:
            raise Refused("two paths renamed onto %s: %s and %s" % (q, seen[q], p))
        seen[q] = p
    dated = {p: sub_dates(b, bpairs) for p, (r, b) in files.items()}
    hashed = [p for p, (r, _) in files.items() if r is not None]
    # Fixed point: each round recomputes every derived value from the previous round's map. References form no cycle (a file cannot hold
    # its own digest), so the map stops changing after at most as many rounds as the longest reference chain.
    dmap = {}
    for _ in range(len(hashed) + 2):
        nxt = {}

        def put(old, new):
            if old == new:
                return
            if old in nxt and nxt[old] != new:
                raise Refused("one old value %s maps to %s and %s" % (old.decode(), nxt[old].decode(), new.decode()))
            nxt[old] = new

        for p in hashed:
            orig, cur = files[p][1], sub_digests(dated[p], dmap)
            put(sha(orig), sha(cur))
            ml = manifest_lines(orig)
            if ml is not None:
                ml2 = manifest_lines(cur)
                if ml2 is None:
                    raise Refused("manifest %s stops being a manifest" % p)
                put(scope_id(ml), scope_id(ml2))
        if nxt == dmap:
            break
        dmap = nxt
    else:
        raise Refused("derived values did not settle (a reference cycle)")
    final = {p: sub_digests(dated[p], dmap) for p in files}
    # every manifest line that verified before must verify after (line by line: a manifest with deliberately stale lines is checked too, review r10 LOW-6)
    by_old = {q: b for q, (_, b) in files.items()}
    by_new = {newpath[p]: final[p] for p in files}

    def verifies(h, rel, base, table):
        q = os.path.normpath(os.path.join(base, rel.decode()))
        return q in table and sha(table[q]) == h
    for p, (r, orig) in files.items():
        ml = manifest_lines(orig)
        if r is None or ml is None:
            continue
        after = manifest_lines(final[p])
        for k, ((h, rel), (h2, rel2)) in enumerate(zip(ml, after)):
            if verifies(h, rel, os.path.dirname(p), by_old) and not verifies(h2, rel2, os.path.dirname(newpath[p]), by_new):
                raise Refused("manifest %s line %d verified before the re-date and not after" % (p, k + 1))
    # no short reference to a replaced value may survive
    olds = set(dmap)
    pre = {}
    for o in olds:
        pre.setdefault(o[:8], []).append(o)
    news = set(dmap.values())
    for p, b in final.items():
        for m in HEXRUN.finditer(b):
            run = m.group(0)
            if run in news:
                continue
            for o in pre.get(run[:8], []):
                if o.startswith(run[:64]):
                    raise Refused("%s keeps %s, a prefix of the replaced value %s" % (p, run[:16].decode(), o[:16].decode()))
    return files, newpath, final, dmap


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--map", action="append", required=True, metavar="OLD=NEW")
    ap.add_argument("--also", action="append", default=[], metavar="FILE")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("roots", nargs="*")
    a = ap.parse_args(argv)
    pairs = []
    for m in a.map:
        o, _, n = m.partition("=")
        if not (DATE_RE.fullmatch(o) and DATE_RE.fullmatch(n)) or o == n:
            print("redate: --map wants OLD=NEW, two different YYYY-MM-DD dates (got %r)" % m, file=sys.stderr)
            return 2
        pairs.append((o, n))
    if len({o for o, _ in pairs}) != len(pairs) or {o for o, _ in pairs} & {n for _, n in pairs}:
        print("redate: the map repeats an OLD date or chains one date into another", file=sys.stderr)
        return 2
    roots = [os.path.normpath(r) for r in a.roots]
    for r in roots:
        if not os.path.isdir(r):
            print("redate: ROOT %s is not a directory" % r, file=sys.stderr)
            return 2
    also = [os.path.normpath(f) for f in a.also]
    try:
        files, newpath, final, dmap = plan(pairs, roots, also)
    except (Refused, OSError) as e:
        print("redate: refused: %s" % e, file=sys.stderr)
        return 2
    changed = [p for p in files if final[p] != files[p][1] or newpath[p] != p]
    moved = [p for p in files if newpath[p] != p]
    if not a.check:
        tmps, cur, made = [], None, []           # phase 1: every new file beside its target; a failure removes them all and changes nothing
        try:
            for p in changed:
                q = newpath[p]
                d = os.path.dirname(q)
                while d and not os.path.isdir(d):          # the directories a rename needs, outermost last, so a failure can remove them
                    made.append(d)
                    d = os.path.dirname(d)
                os.makedirs(os.path.dirname(q), exist_ok=True)
                cur = os.path.join(os.path.dirname(q), ".redate-%d-%s" % (os.getpid(), os.path.basename(q)))
                with open(cur, "wb") as fh:
                    fh.write(final[p])
                    fh.flush()
                    os.fsync(fh.fileno())
                os.chmod(cur, os.stat(p).st_mode & 0o7777)
                tmps.append((p, q, cur))
                cur = None
        except OSError as e:
            for t in [x[2] for x in tmps] + ([cur] if cur else []):
                try:
                    os.unlink(t)
                except OSError:
                    pass
            for d in sorted(set(made), key=len, reverse=True):
                try:
                    os.rmdir(d)
                except OSError:
                    pass
            print("redate: refused: writing failed, nothing replaced: %s" % e, file=sys.stderr)
            return 2
        for p, q, t in tmps:                     # phase 2: replace targets, then drop the old paths of renamed files
            os.replace(t, q)
        for p, q, t in tmps:
            if q != p:
                os.unlink(p)
        for r in roots:   # drop directories a rename emptied
            for d, dirs, fs in sorted(os.walk(r, topdown=False)):
                if d != r and not os.listdir(d):
                    os.rmdir(d)
    print("redate: %s %d file(s), renamed %d, replaced %d derived value(s)%s" % (
        "would rewrite" if a.check else "rewrote", len(changed), len(moved), len(dmap), " (check only)" if a.check else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
