#!/usr/bin/env python3
"""Frozen-evaluation oracle for `--packet-only` (PRD-dream-packet-errors-while-repairable R1).

R1 holds an error on a bound manifest "only when it is also present in the bound manifest's own frozen
copies (its repairs-file copy and its matrix, which record the state when its review launched)". This
oracle computes that evaluation mechanically and compares every packet error against it; it never reads
the lint's held logic, only its command line: `--scope-id`, `--packet-only` and the full lint.

For a note, an evaluated entry E (the `--pending` file, else the note's last entry) and B, the latest
listed manifest a review launch bound whose launch state is still its own, the launch-state
reconstruction of B is a private copy of the PRD home in which
- the note holds the entries recorded before B's latest launch, then E as it stood at that launch: its
  Mission: scope= cut after B, repairs= the value in force then (the latest entry recorded before the
  launch, else E's), withdrawn= inherited from those entries only, adversarial= E's (with --pending,
  a pending adversarial= B does not list is replaced by the matrix in force then, S3); its Review: lines
  those of the reviews launched before the launch, then the review launching on B, whose verdict carries
  no finding ("named before launch", R-10): a stub review bound to B at that launch time;
- every packet file B lists is restored from B's own verified copies, under the names in force at the
  launch: the edges file, the repairs file (absent when B lists none: it froze no row), the matrix, the
  contract copies and packet members of B's frozen header, and the PRDs;
- the decisions log holds the rows up to and including B's latest launch row, and the stub review's row.
The full lint (not --packet-only) on that copy is the frozen evaluation. For every packet error:
- `mission-withdrawn-bound`, an error naming no manifest and no row (S4), an error on an unbound or pending
  manifest (S5), or on a bound manifest edited or deleted after its launch (R3), sets the exit;
- any other error (on bound manifests, or on rows of the repairs file) is HELD iff the frozen evaluation
  reports the same defect: the same finding id and the same object (the manifest and member, the pair and
  member, the finding id, or the row number with the row's bytes).
States the reconstruction cannot rebuild (oracle-scope.md) are classified directly by their R1/R5 sentence.

usage: oracle.py <lint> <log> <home> <decisions|-> [--pending <file>] [--label <name>] [--keep <dir>]
       oracle.py --corpus <tests/fixtures> <lint>      every checked-in compatibility note, --last
Prints one line per packet error (`ok` or `DIS`, expected, actual, the reason, the error) and exits 1
when any disagrees, 0 otherwise, 2 when the lint refuses the packet run (rc 2).
"""
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HEADER_RE = re.compile(r"^## (\S+)  /dream  vision-")
PRD_DIRS = ("build-queue", "built-prds", "parked")
PACKET_HOLDERS = ("visions", "notes/missions", "notes/reviews")
SWEEP_IDS = ("repair-grammar", "mission-repairs-missing", "repair-duplicate", "repair-missing", "repair-class-mismatch",
             "sweep-missing", "repair-author-mismatch", "repair-hash-mismatch", "repair-scope-mismatch")
STUB_SESSION = "00000000-0000-4000-8000-0000000c0de1"
STUB_DIR = "notes/reviews/oracle-launch"


def parse_iso(s):
    try:
        return datetime.datetime.fromisoformat(s.replace("Z", "+00:00")) if isinstance(s, str) else None
    except ValueError:
        return None


def entries_of(text):
    out, cur = [], None
    for ln in text.split("\n"):
        m = HEADER_RE.match(ln)
        if m:
            cur = {"ts": m.group(1), "head": ln, "lines": []}
            out.append(cur)
        elif ln.startswith("## "):
            cur = None
        elif cur is not None:
            cur["lines"].append(ln)
    return out


def render(e):
    lines = list(e["lines"])
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join([e["head"]] + lines) + "\n"


def line_of(e, kind):
    v = [ln.rstrip() for ln in e["lines"] if ln.startswith(kind + ":")]
    return v[-1] if v else None


def task_of(e):
    t = line_of(e, "Task")
    m = re.match(r"^Task:\s+(\S+)\s+Consumer:", t or "")
    return m.group(1) if m else None


def mission_of(e):
    """(name, {key: value; scope and withdrawn lists}) of an entry's Mission: line, or None."""
    ml = line_of(e, "Mission")
    if ml is None:
        return None
    toks = ml[len("Mission:"):].split()
    name, keys = (toks[0] if toks and "=" not in toks[0] else None), {}
    for t in toks[1 if name else 0:]:
        k, _, v = t.partition("=")
        keys[k] = v.split(",") if k in ("scope", "withdrawn") else v
    return name, keys


def adv_of(e):
    a = line_of(e, "Analysis")
    m = re.search(r"\badversarial=(\S+)", a or "")
    return m.group(1) if m and not m.group(1).startswith("skipped:") else None


def reviews_of(e):
    out = []
    for ln in e["lines"]:
        m = re.match(r"^Review:\s+(\S+)\s+reviewer-session=(\S+)", ln)
        if m:
            out.append({"file": m.group(1), "session": m.group(2), "line": ln.rstrip()})
    return out


def manifest_names(full):
    """{basename: digest} of a manifest, or None when it does not read as `<sha256>  <path>` lines."""
    try:
        data = open(full, "rb").read()
    except OSError:
        return None
    out = {}
    for ln in data.decode("utf-8", "replace").split("\n"):
        if not ln:
            continue
        m = re.fullmatch(r"([0-9a-f]{64})  (\S+)", ln)
        if not m:
            return None
        out.setdefault(m.group(2).rsplit("/", 1)[-1], m.group(1))
    return out


def file_sha(path):
    try:
        return hashlib.sha256(open(path, "rb").read()).hexdigest()
    except OSError:
        return None


class Oracle:
    def __init__(self, lint, log, home, dec, pending=None, label=None, keep=None):
        self.lint, self.log, self.home = lint, os.path.abspath(log), os.path.abspath(home)
        self.dec = None if dec in (None, "-") or not os.path.isfile(dec) else os.path.abspath(dec)
        self.pending, self.label, self.keep = pending, label or os.path.basename(home), keep
        self.top = tempfile.mkdtemp(prefix="drpe-oracle.")
        self.fake = os.path.join(self.top, "fakehome")
        os.makedirs(self.fake)
        self.notes = []          # the reasons a state was classified directly

    # ---- the lint, by its command line only
    def run(self, args):
        env = {k: v for k, v in os.environ.items() if k not in ("SKILL_ROUTING_DECISIONS", "DREAM_TERMINAL_READER",
                                                               "DREAM_LINT_TEST_READER", "ACCOUNT_LANE_STATE")}
        env["HOME"] = self.fake
        p = subprocess.run(["bash", self.lint] + args, capture_output=True, text=True, env=env)
        return p.returncode, p.stdout, p.stderr

    def sid(self, full):
        rc, out, _ = self.run(["--scope-id", full])
        return out.strip() if rc == 0 and re.fullmatch(r"[0-9a-f]{64}", out.strip()) else None

    def resolve(self, p, home=None):
        return p if os.path.isabs(p) else os.path.join(home or self.home, p)

    def norm(self, p, home=None):
        return os.path.normpath(self.resolve(p, home))

    # ---- the note and the evaluated entry
    def load(self):
        text = open(self.log, encoding="utf-8").read() if os.path.isfile(self.log) else ""
        self.recorded = entries_of(text) if text.strip() else []
        if self.pending:
            pe = entries_of(open(self.pending, encoding="utf-8").read())
            self.E, self.before_E = pe[0], list(self.recorded)
        else:
            self.E, self.before_E = self.recorded[-1], self.recorded[:-1]
        self.task = task_of(self.E)
        self.same = [e for e in self.before_E if task_of(e) == self.task and mission_of(e)]
        eff = {}
        for e in self.same:
            eff.update(mission_of(e)[1])
        mE = mission_of(self.E)
        self.name = mE[0] if mE else (mission_of(self.same[-1])[0] if self.same else None)
        self.eff = dict(eff, **(mE[1] if mE else {}))
        self.rows = []
        if self.dec:
            for ln in open(self.dec, encoding="utf-8").read().splitlines():
                try:
                    r = json.loads(ln)
                except ValueError:
                    continue
                if isinstance(r, dict):
                    self.rows.append(r)

    def launch(self, r):
        return r.get("decision") == "launch" and r.get("task_id") == self.task

    def binding(self, path, sid):
        """R3's binding rows of one manifest: role-review launch rows of the task naming its path or carrying its
        scope id, and a Review: line's reviewer launch row carrying the scope id."""
        n, sess = self.norm(path), {rv["session"] for rv in reviews_of(self.E)}
        out = []
        for i, r in enumerate(self.rows):
            if not self.launch(r):
                continue
            sc, rid = r.get("scope"), r.get("scope_id")
            by_path = r.get("role") == "review" and isinstance(sc, str) and sc and self.norm(sc) == n
            by_id = sid is not None and rid == sid and (r.get("role") == "review" or r.get("session") in sess)
            if by_path or by_id:
                out.append((i, r))
        return out

    def manifests(self):
        self.scope = list(self.eff.get("scope") or [])
        wl = list(self.eff.get("withdrawn") or [])
        self.mans = []
        for p in self.scope:
            full = self.resolve(p)
            sid = self.sid(full)
            rows = self.binding(p, sid)
            bound = bool(rows)
            # R1 launch state: canonicalizes, and a row carries its current id or binds it by path with no id
            kept = bound and sid is not None and any(r.get("scope_id") == sid or not (isinstance(r.get("scope_id"), str)
                                                                                    and r["scope_id"]) for _, r in rows)
            wd = any(self.norm(w) == self.norm(p) for w in wl) and not bound
            self.mans.append({"path": p, "full": full, "sid": sid, "rows": rows, "bound": bound, "kept": kept,
                              "withdrawn": wd, "names": manifest_names(full)})
        live = [m for m in self.mans if not m["withdrawn"]]
        ks = [m for m in live if m["kept"]]
        self.B = ks[-1] if ks else None
        if self.B is None:
            return
        brows = [(i, r) for i, r in self.B["rows"] if r.get("scope_id") == self.B["sid"]
                 or not (isinstance(r.get("scope_id"), str) and r["scope_id"])]
        ts = [(parse_iso(r.get("ts")), i, r) for i, r in brows if parse_iso(r.get("ts")) is not None]
        if not ts:
            self.B = None
            self.notes.append("B has no launch row with a timestamp: no launch state (every error exits)")
            return
        self.bts, self.bi, self.brow = max(ts, key=lambda x: (x[0], x[1]))

    # ---- the launch state
    def launch_entry(self):
        B, bts = self.B, self.bts
        # recorded before the launch (the evaluated entry too when it is recorded and its header precedes it; a
        # pending entry is never recorded, S3)
        self.rec = [e for e in self.recorded if parse_iso(e["ts"]) is not None and parse_iso(e["ts"]) < bts
                    and not (self.pending and e is self.E)]
        rec_same = [e for e in self.rec if task_of(e) == self.task and mission_of(e)]
        rep_rec = None
        for e in rec_same:
            v = mission_of(e)[1].get("repairs")
            if v:
                rep_rec = v
        self.rep_now = self.eff.get("repairs")
        self.rep_at = rep_rec or self.rep_now
        cut = next(i for i, p in enumerate(self.scope) if self.norm(p) == self.norm(B["path"]))
        toks = [f"edges={self.eff['edges']}"] if self.eff.get("edges") else []
        toks.append("scope=" + ",".join(self.scope[:cut + 1]))
        if self.rep_at:
            toks.append(f"repairs={self.rep_at}")
        mline = f"Mission: {self.name} " + " ".join(toks)
        adv = adv_of(self.E)
        self.adv_at = adv
        if self.pending and adv and B["names"] is not None and os.path.basename(adv) not in B["names"]:
            prior = [adv_of(e) for e in self.rec if task_of(e) == self.task and adv_of(e)]
            self.adv_at = prior[-1] if prior else None
        keep_rv = []
        for rv in reviews_of(self.E):
            t = [parse_iso(r.get("ts")) for _, r in enumerate(self.rows[:self.bi + 1])
                 if r.get("session") == rv["session"] and self.launch(r) and r.get("skill") == "dream"]
            t = [x for x in t if x is not None]
            if t and min(t) < bts:
                keep_rv.append(rv["line"])
        keep_rv.append(f"Review: {STUB_DIR}/verdict.txt reviewer-session={STUB_SESSION} result={STUB_DIR}/result.json")
        lines, rv_done = [], False
        for ln in self.E["lines"]:
            if ln.startswith("Mission:"):
                lines.append(mline)
            elif ln.startswith("Review:"):
                if not rv_done:
                    lines += keep_rv
                    rv_done = True
            elif ln.startswith("Analysis:") and adv != self.adv_at:
                lines.append(re.sub(r"\badversarial=(\S+)( uncovered=\S+)?",
                                    f"adversarial={self.adv_at} uncovered=1" if self.adv_at else
                                    "adversarial=skipped: oracle launch state", ln))
            else:
                lines.append(ln)
        if not rv_done:
            lines += keep_rv
        if not any(ln.startswith("Mission:") for ln in lines):
            lines.append(mline)
        return {"ts": self.E["ts"], "head": self.E["head"], "lines": lines}

    def restore(self, rh):
        """B's verified copies over the live files, under the names in force at the launch."""
        B, names = self.B, self.B["names"] or {}
        bdir = os.path.dirname(B["full"])

        def copy_of(base):
            cp = os.path.join(bdir, base)
            return cp if base in names and file_sha(cp) == names[base] else None

        def put(rel, src):
            dst = self.resolve(rel, rh)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.lexists(dst):
                os.remove(dst)
            if src is not None:
                shutil.copyfile(src, dst)
        self.nohdr = self.repbad = False
        eb = os.path.basename(self.eff["edges"]) if self.eff.get("edges") else None
        hdr = None
        if eb and copy_of(eb):
            put(self.eff["edges"], copy_of(eb))
            try:
                hdr = json.loads(open(copy_of(eb), encoding="utf-8").readline())
            except ValueError:
                hdr = None
        if not isinstance(hdr, dict):
            self.nohdr = True
            hdr = {}
        if self.rep_at:
            rb = os.path.basename(self.rep_at)
            if rb not in names:
                put(self.rep_at, None)                 # B froze no row of it
            elif copy_of(rb):
                put(self.rep_at, copy_of(rb))
            else:
                self.repbad = True
        if self.adv_at and copy_of(os.path.basename(self.adv_at)):
            put(self.adv_at, copy_of(os.path.basename(self.adv_at)))
        for x in hdr.get("external") or []:
            cs = x.get("contract") if isinstance(x, dict) else None
            for cp in (cs if isinstance(cs, list) else [cs]):
                if isinstance(cp, str) and cp.strip() and copy_of(os.path.basename(cp)):
                    put(cp, copy_of(os.path.basename(cp)))
        for b in hdr.get("packet") or []:
            if isinstance(b, str) and copy_of(b):
                hold = next((os.path.join(d, b) for d in PACKET_HOLDERS if os.path.isfile(os.path.join(rh, d, b))), None)
                put(hold or os.path.join("visions", b), copy_of(b))
        for b in names:
            if re.fullmatch(r"PRD-[a-z0-9-]+\.md", b) and copy_of(b):
                hold = next((os.path.join(d, b) for d in PRD_DIRS if os.path.isfile(os.path.join(rh, d, b))), None)
                put(hold or os.path.join("built-prds", b), copy_of(b))

    def frozen(self):
        """The full lint's findings on B's launch-state reconstruction: [(id, detail)]."""
        rt = os.path.join(self.top, "recon")
        rh = os.path.join(rt, "home")
        shutil.copytree(self.home, rh, symlinks=True)
        le = self.launch_entry()
        self.restore(rh)
        os.makedirs(os.path.join(rh, STUB_DIR), exist_ok=True)
        with open(os.path.join(rh, STUB_DIR, "verdict.txt"), "w", encoding="utf-8") as fh:
            fh.write(f"mission=APPROVE {STUB_SESSION}\n")
        with open(os.path.join(rh, STUB_DIR, "result.json"), "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"type": "result", "is_error": False, "session_id": STUB_SESSION,
                                 "result": f"Done.\nfindings=none\nmission=APPROVE {STUB_SESSION}"}) + "\n")
        stub = dict(self.brow, session=STUB_SESSION, role="review", scope=self.B["path"], scope_id=self.B["sid"],
                    decision="launch", skill="dream", task_id=self.task, resume=False)
        dec = os.path.join(rt, "decisions.jsonl")
        with open(dec, "w", encoding="utf-8") as fh:
            fh.write("".join(json.dumps(r) + "\n" for r in self.rows[:self.bi + 1] + [stub]))
        note = os.path.join(rt, "dream-log.md")
        with open(note, "w", encoding="utf-8") as fh:
            fh.write("# dream log (oracle launch-state reconstruction)\n\n"
                     + "\n".join(render(e) for e in self.rec + [le]))
        self.rhome = rh
        rc, sout, err = self.run([note, "--last", "--prd-dir", rh, "--decisions", dec])
        self.frc = rc
        out = []
        for ln in sout.split("\n") if rc in (0, 1) else []:
            m = re.match(r"^FAIL (\S+): (.*)$", ln)
            if m:
                out.append((m.group(1), m.group(2)))
        if rc == 2:
            self.notes.append(f"the reconstruction's full lint refused (rc 2): {err.strip()[:200]}")
        return out

    # ---- objects
    def row_bytes(self, rep, home, n):
        try:
            lines = open(self.resolve(rep, home), "rb").read().split(b"\n") if rep else []
        except OSError:
            return None
        return lines[n - 1] if 0 < n <= len(lines) else None

    def key(self, fid, d, home, rep):
        d = d.replace(home, "<H>")
        for r in (self.rep_now, getattr(self, "rep_at", None)):
            if r:
                d = d.replace(r, "<REP>")
        if fid == "repair-missing":
            m = re.match(r"finding (\S+) of (\S+): ", d)
            if m:
                return (fid, m.group(1), m.group(2))
        if fid == "mission-scope-incomplete":
            m = re.match(r"manifest (\S+): lists no (\S+) \(", d)
            if m:
                return (fid, self.norm(m.group(1)), m.group(2))
        if fid == "mission-scope-mismatch":
            d = re.sub(r"^(manifest \S+: )(?:live|frozen) edges header: ", r"\1edges header: ", d)
        if fid == "repair-hash-mismatch":
            m = re.match(r"(\S+): changed but undeclared between (\S+) and (\S+)", d)
            if m:
                return (fid, m.group(1), self.norm(m.group(2)), self.norm(m.group(3)))
        rows = self.rows_named(d)
        if rows:
            return (fid, tuple((n, self.row_bytes(rep, home, n)) for n in rows), re.sub(r"\brows? [\d, and]+", "row", d))
        return (fid, d)

    @staticmethod
    def rows_named(d):
        m = re.search(r"\brows ((?:\d+(?:, | and )?)+)", d)
        if m:
            return [int(x) for x in re.findall(r"\d+", m.group(1))]
        m = re.search(r"\brow (\d+)\b", d)
        return [int(m.group(1))] if m else []

    def named(self, fid, d):
        """The listed manifests an error names (by path in its text, or a finding's following review)."""
        out = []
        for m in self.mans:
            for form in {m["path"], m["full"], os.path.normpath(m["full"])}:
                if re.search(r"(?:^|[\s(])" + re.escape(form) + r"(?=$|[\s:),;'])", d):
                    out.append(m)
                    break
        if fid == "repair-missing" and not out:
            # the manifest the finding's following review reads: the next chain review after its issuer (a Review:
            # line whose reviewer's latest launch row of the task has role review and a listed scope id), else
            # the review about to launch on the last listed manifest
            f = re.match(r"finding \S+ of (\S+): ", d)
            chain = []
            for rv in reviews_of(self.E):
                rs = [r for r in self.rows if r.get("session") == rv["session"] and self.launch(r)
                      and r.get("skill") == "dream"]
                hit = [m for m in self.mans if rs and rs[-1].get("role") == "review" and m["sid"] is not None
                       and rs[-1].get("scope_id") == m["sid"]]
                if hit:
                    chain.append((rv["file"], hit[0]))
            k = next((i for i, (fl, _) in enumerate(chain) if f and fl == f.group(1)), None)
            live = [m for m in self.mans if not m["withdrawn"]]
            if k is not None and k + 1 < len(chain):
                out.append(chain[k + 1][1])
            elif k is not None and live:
                out.append(live[-1])
        return list({id(m): m for m in out}.values())

    # ---- the check
    def expect(self, fid, d, fkeys):
        rows = self.rows_named(d)
        ms = [] if rows else self.named(fid, d)      # S2: a row error is judged by its rows, not the paths it quotes
        if fid == "mission-withdrawn-bound":
            return "FAIL", "S3 mission-withdrawn-bound"
        if fid == "mission-grammar":
            return "FAIL", "S4 mission-grammar names no manifest"
        if not ms and not rows:
            return "FAIL", "S4 names no manifest and no row"
        if any(m["withdrawn"] for m in ms):
            return "FAIL", "S3/S5 names a withdrawn manifest"
        if any(not m["bound"] for m in ms):
            return "FAIL", "S5 names an unbound or pending manifest"
        if any(not m["kept"] for m in ms):
            return "FAIL", "R3 names a bound manifest edited or deleted after its launch"
        if self.B is None:
            return "FAIL", "no bound manifest keeps its launch state"
        if self.repbad and fid in SWEEP_IDS + ("mission-scope-incomplete",) and (fid != "mission-scope-incomplete"
                                                                                 or "(the repairs file;" in d):
            return "FAIL", "S2/R-5 the repairs copy beside B is listed but absent or differs"
        if rows and self.rep_at != self.rep_now:
            return "FAIL", "S2 a row of the current repairs file, renamed since B's launch: B froze no row of it"
        if self.nohdr and self.B in ms and ("of the live edges header)" in d or "live edges header: contract" in d
                                            or "(matrix named by adversarial=" in d):
            # B froze no readable edges header: the live header at its launch is not recorded. A need no header
            # supplies is carried (the edges file; the matrix in force at the launch, which a pending adversarial=
            # B does not list is not, S3); any other live-header defect has nothing that vouches for it.
            eb = os.path.basename(self.eff["edges"]) if self.eff.get("edges") else None
            mx = os.path.basename(self.adv_at) if getattr(self, "adv_at", None) else None
            m = re.match(r"manifest \S+: lists no (\S+) \(", d)
            ok = m is not None and m.group(1) in (eb, mx)
            return ("HELD", "R-1 no readable frozen header: a need no header supplies") if ok else \
                ("FAIL", "R-1 no readable frozen header: a live-header defect nothing vouches for")
        k = self.key(fid, d, self.home, self.rep_now)
        return ("HELD", "present in the frozen evaluation") if k in fkeys else ("FAIL", "absent from the frozen evaluation")

    def check(self):
        self.load()
        args = [self.log, "--last", "--packet-only", "--prd-dir", self.home, "--json"]
        if self.pending:
            args[1:1] = ["--pending", self.pending]
        if self.dec:
            args += ["--decisions", self.dec]
        rc, out, err = self.run(args)
        if rc == 2:
            print(f"{self.label}: packet run refused (rc 2): {err.strip()[:200]}")
            return 2
        obj = json.loads(out)
        errs = [("FAIL", e["id"], e["detail"]) for e in obj["packet_errors"]] + \
               [("HELD", e["id"], e["detail"]) for e in obj["held_packet_errors"]]
        self.manifests()
        fkeys = set()
        if self.B is not None:
            ff = self.frozen()
            fkeys = {self.key(f, d, self.rhome, self.rep_at) for f, d in ff}
        bad = 0
        bdesc = "none" if self.B is None else f"{self.B['path']} launched {self.brow.get('ts')}"
        print(f"{self.label}: B={bdesc} packet rc={rc} errors={len(errs)}"
              + ("" if self.B is None else f" frozen rc={self.frc} findings={len(fkeys)}")
              + (f" repairs@launch={self.rep_at}" if self.B is not None and self.rep_at != self.rep_now else "")
              + "".join(f" [{n}]" for n in self.notes))
        if os.environ.get("DRPE_ORACLE_SHOW") and self.B is not None:
            for f, d in ff:
                print(f"  frozen: {f}: {d}")
        for got, fid, d in errs:
            want, why = self.expect(fid, d, fkeys)
            if want != got:
                bad += 1
            print(f"  {'ok ' if want == got else 'DIS'} want={want} got={got} ({why}) {fid}: {d}")
        if self.keep:
            shutil.copytree(self.top, self.keep, dirs_exist_ok=True)
        shutil.rmtree(self.top, ignore_errors=True)
        return 1 if bad else 0


def corpus(fix, top):
    """The checked-in compatibility notes, materialized as tests/fixtures/drmx/compat.py does: [(tag, log, home,
    decisions)] (drrec home and verified, drei's logs, drsp, every drmr and drfc variant over its base home)."""
    out = []
    shutil.copytree(os.path.join(fix, "drrec"), os.path.join(top, "drrec"))
    out.append(("drrec", f"{top}/drrec/home/notes/dream-log.md", f"{top}/drrec/home", f"{top}/drrec/decisions.jsonl"))
    out.append(("drrec-verified", f"{top}/drrec/verified/home/notes/dream-log.md", f"{top}/drrec/verified/home",
                f"{top}/drrec/verified/decisions.jsonl"))
    shutil.copytree(os.path.join(fix, "drei"), os.path.join(top, "drei"))
    for lg in sorted(os.listdir(f"{top}/drei/home/notes")):
        if lg.endswith(".md"):
            out.append((f"drei:{lg}", f"{top}/drei/home/notes/{lg}", f"{top}/drei/home", f"{top}/drei/decisions.jsonl"))
    shutil.copytree(os.path.join(fix, "drsp"), os.path.join(top, "drsp"))
    out.append(("drsp", f"{top}/drsp/home/notes/dream-log.md", f"{top}/drsp/home", f"{top}/drsp/decisions.jsonl"))
    for fam in ("drmr", "drfc"):
        src = os.path.join(fix, fam)
        for v in ["base"] + sorted(os.listdir(os.path.join(src, "variants"))):
            w = os.path.join(top, fam, v)
            shutil.copytree(os.path.join(src, "home"), os.path.join(w, "home"))
            dec = os.path.join(src, "decisions.jsonl")
            if v != "base":
                vh = os.path.join(src, "variants", v, "home")
                if os.path.isdir(vh):
                    shutil.copytree(vh, os.path.join(w, "home"), dirs_exist_ok=True)
                dec = os.path.join(src, "variants", v, "decisions.jsonl")
            shutil.copy(dec, os.path.join(w, "decisions.jsonl"))
            out.append((f"{fam}:{v}", f"{w}/home/notes/dream-log.md", f"{w}/home", f"{w}/decisions.jsonl"))
    return out


def main(argv):
    if argv[:1] == ["--corpus"] and len(argv) == 3:
        top = tempfile.mkdtemp(prefix="drpe-oracle-corpus.")
        worst = 0
        for tag, log, home, dec in corpus(argv[1], top):
            worst = max(worst, Oracle(argv[2], log, home, dec, label=tag).check())
        shutil.rmtree(top, ignore_errors=True)
        return 1 if worst == 1 else 0
    if len(argv) < 4:
        print(__doc__.strip().split("\n\n")[-1], file=sys.stderr)
        return 2
    kw, rest, i = {}, argv[4:], 0
    while i < len(rest):
        kw[rest[i].lstrip("-")] = rest[i + 1]
        i += 2
    return Oracle(argv[0], argv[1], argv[2], argv[3], **kw).check()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
