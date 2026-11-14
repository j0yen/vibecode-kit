"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/smuggle14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys, random, math, itertools
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
r = random.Random(1414)
L = "abcdefghijklmnopqrstuvwxyz"; D = "0123456789"
rs = lambda n, a: "".join(r.choice(a) for _ in range(n))
FIELDS = [("current_owner", "ident"), ("reviewed_by", "ident"), ("worker.account", "ident"), ("worker.model", "ident"), ("worker.host", "host"),
          ("worker.unit", "ident"), ("worker.child", "ident"), ("consumer", "ident"), ("alternate", "ident"), ("target.branch", "ident"),
          ("target.repo", "ident"), ("task_id", "ident"), ("worker.invocation", "ident"), ("sess-id", "ident"), ("result", "path"),
          ("artifact", "path"), ("evidence-ref", "path")]
ROWS = ("row", "owner", "claim", "waits-on", "status")


def where(v):
    f = [n for n, k in FIELDS if ev.unmark(ev.show(n, v, k)) == v]
    rw = [n for n in ROWS if ev.show_row(n, v) == v]
    return f, rw


def report(name, vals, bits):
    hits_f, hits_r = {}, {}
    for v in vals:
        f, rw = where(v)
        for x in f: hits_f[x] = hits_f.get(x, 0) + 1
        for x in rw: hits_r[x] = hits_r.get(x, 0) + 1
    n = len(vals)
    fs = ", ".join("%s=%d" % kv for kv in sorted(hits_f.items()))
    rs_ = ", ".join("%s=%d" % kv for kv in sorted(hits_r.items()))
    print("%-34s ~%6.1f bits/value  n=%d | fields: %s | rows: %s" % (name, bits, n, fs or "-", rs_ or "-"))


# Unicode decimal digits that Python's re \d matches but that are not ASCII
UD = [chr(c) for c in range(0x110000) if chr(c).isdecimal() and not chr(c).isascii()]
UDb = math.log2(len(UD) + 10)
ud = lambda n: "".join(r.choice(UD) for _ in range(n))
print("unicode decimal digits matched by \\d (non-ASCII): %d (%.1f bits each)" % (len(UD), UDb))

# 1. templates (keep() matches _TEMPLATES before ident()/NFKC): unicode digits in the digit slots
peer = lambda: "claude-%s-r7-ab%sc%s-20%s1113" % (ud(7), ud(5), ud(2), ud(2))
report("peer template, unicode digits", [peer() for _ in range(50)], 16 * UDb)
peer_ascii_max = lambda: "claude-%s-%s-%s%s%s%s%s%s%s-20261113-worker" % (rs(7, D), r.choice(getattr(ev, "_SEATS", ("r7",))), rs(1, L), rs(2, D), rs(2, L), rs(2, D), rs(2, L), rs(2, D), rs(1, L))
report("peer template, ascii, max slots", [peer_ascii_max()[:200] for _ in range(50)], 7 * 3.32 + 2.8 + 12 * 4.5)
inner = lambda: "wm-build-inner%s-a.service" % ud(5)
report("inner template, unicode digits", [inner() for _ in range(50)], 5 * UDb)
prd_u = lambda: "/home/jsy/Notes/prd-abc-20%s%s%s.md" % (ud(2), "11", "1" + ud(1))
report("prd template, unicode date digits", [prd_u() for _ in range(50)], 3 * UDb)
prd_rand = lambda: "/home/%s/Notes/prd-%s-%s-%s-%s-20261113.md" % (rs(4, L), rs(6, L), rs(6, L), rs(6, L), rs(6, L))
report("prd template, 24 random letters", [prd_rand() for _ in range(50)], 28 * 4.7)

# 2. the ISO gate with unicode digits (rows are not limited to ASCII; identity fields are)
iso_u = lambda: "20%s-11-1%sT0%s:1%s:2%s.%s" % (ud(2), ud(1), ud(1), ud(1), ud(1), ud(9))
report("ISO ts, unicode digits, frac 9", [iso_u() for _ in range(50)], 15 * UDb)
two = lambda: iso_u() + "-" + "20%s-11-1%sT0%s:1%s:2%s.%s" % (ud(2), ud(1), ud(1), ud(1), ud(1), ud(5))
report("two ISO ts, unicode digits", [two() for _ in range(50)], 26 * UDb)

# 3. the ISO gate, ASCII: what a calendar-valid timestamp carries uncharged (date, time, zone), two per value
def ts():
    y, mo, d = r.randint(2000, 2099), r.randint(1, 12), r.randint(1, 28)
    h, mi, s = r.randint(0, 23), r.randint(0, 59), r.randint(0, 59)
    z = r.choice(["Z", "", "+%02d:%02d" % (r.randint(0, 14), r.randint(0, 59)), "-%02d%02d" % (r.randint(0, 14), r.randint(0, 59))])
    return "%04d-%02d-%02dT%02d:%02d:%02d.%s%s" % (y, mo, d, h, mi, s, rs(7, D), z)
tsb = math.log2(100 * 12 * 28 * 86400) + math.log2(2 + 2 * 15 * 60)
report("two ASCII ISO ts, frac 7 each", [ts() + "_" + ts() for _ in range(80)], 2 * tsb + 14 * 3.32)
report("ISO ts frac 10 (over bound)", ["2026-11-13T09:41:27." + rs(10, D) for _ in range(20)], 0)
report("three ISO dates (over cap 2)", ["2026-11-13-2026-11-14-2026-11-15" for _ in range(1)], 0)

# 4. the free sentinel piece: the gate's own placeholder for a charged uuid/timestamp, supplied by the input
J = list("-_./:@")
sent = lambda: getattr(ev, "_CHARGED", "\ue010") + "".join(r.choice(J) + getattr(ev, "_CHARGED", "\ue010") for _ in range(38))
report("sentinel pieces + joiners (38)", [sent() for _ in range(50)], 38 * math.log2(6))
sent2 = lambda: " ".join(getattr(ev, "_CHARGED", "\ue010") + "".join(r.choice(J) + getattr(ev, "_CHARGED", "\ue010") for _ in range(9)) for _ in range(4))
report("sentinel, 4 row tokens", [sent2() for _ in range(50)], 36 * math.log2(6))

# 5. joiner choice with charged pieces: 14 one-digit pieces + 6 vocabulary words + 8 one-letter unlisted pieces
VOC = sorted(w for w in ev._ID_WORDS if len(w) >= 3 and not ev._cred_name(w))
def joiners():
    pieces = [r.choice(D) for _ in range(14)] + [r.choice(VOC) for _ in range(6)] + [r.choice("bcdefghjklmnopqstuvxyz") for _ in range(8)]
    r.shuffle(pieces)
    return "".join(p + r.choice(J) for p in pieces[:-1]) + pieces[-1]
jb = 27 * math.log2(6) + 14 * 3.32 + 6 * math.log2(len(VOC)) + 8 * 4.46 + math.log2(math.factorial(28))
report("joiners + full charged caps", [joiners() for _ in range(200)], jb)

# 6. case of closed-vocabulary words (lower-cased before the vocabulary look-up)
def case_variants(w):
    ok = 0
    for bits in itertools.product((0, 1), repeat=len(w)):
        v = "".join(c.upper() if b else c for c, b in zip(w, bits))
        ok += ev.unmark(ev.show("current_owner", v)) == v
    return ok
cv = {w: case_variants(w) for w in ("invocation", "verifier", "bootstrap", "synthorg", "controller", "wintermute", "production")}
print("case variants of one vocab word printing in current_owner:", ", ".join("%s=%d (%.1f bits)" % (w, n, math.log2(n)) for w, n in cv.items()))
def casey():
    ws = r.sample(["invocation", "bootstrap", "controller", "wintermute", "production", "synthorg"], 6)
    return "-".join("".join(c.upper() if r.random() < .5 else c for c in w) for w in ws)
report("6 vocab words, random case", [casey() for _ in range(200)], 0)

# 7. priority-level run, letter gap, model context tag
report("prio run p0p1p2p3 x3", ["p%sp%sp%sp%s-p%sp%sp%s" % tuple(rs(7, D)) for _ in range(50)], 7 * 3.32)
report("model ctx tag, unicode digits", ["claude-opus-5-5[%sm]" % ud(4) for _ in range(50)], 4 * UDb)
report("letter gap twice (r7-x-1-y-2)", ["r7-%s-1-%s-2" % (r.choice("bcdfg"), r.choice("bcdfg")) for _ in range(50)], 0)
