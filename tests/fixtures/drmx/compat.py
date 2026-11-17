#!/usr/bin/env python3
"""Compatibility driver for drmx_ac05 (and drpe_ac05, drle_ac05): lint every checked-in
compatibility note with two lints and compare stdout, stderr and exit code.

Usage: compat.py <tests/fixtures> <base lint> <head lint> <report> <allowed: python expr on tag, mode, entry>

The corpus is every note under tests/fixtures/drrec (home and verified), drei (both logs), drsp,
drmr and drfc, each variant of drmr and drfc materialized as tests/drmr_lib.sh and
tests/drfc_lib.sh `use` do (the base home, the variant's home files over it, the variant's
decisions log). Each note is linted at every `## <ts>  /dream  vision-` entry (--entry) and with
--last, in text and in --json mode, with HOME set to an empty temporary directory and
ANALYSIS_WIKI_DIR at the drrec wiki copy. A difference is a line of the report:
`<tag>\t<mode>\t<entry>\t<what differs>`. Exit 1 when a difference falls outside `allowed`.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

fix, base, head, report, allowed = sys.argv[1:6]
top = tempfile.mkdtemp(prefix="drmx-compat-")
home_env = os.path.join(top, "fakehome")
os.makedirs(home_env)


def notes():
    out = []
    c = os.path.join(top, "corpus")
    os.makedirs(c)
    shutil.copytree(os.path.join(fix, "drrec"), os.path.join(c, "drrec"))
    out.append(("drrec", f"{c}/drrec/home/notes/dream-log.md", f"{c}/drrec/home", f"{c}/drrec/decisions.jsonl"))
    out.append(("drrec-verified", f"{c}/drrec/verified/home/notes/dream-log.md", f"{c}/drrec/verified/home",
                f"{c}/drrec/verified/decisions.jsonl"))
    shutil.copytree(os.path.join(fix, "drei"), os.path.join(c, "drei"))
    for lg in sorted(os.listdir(f"{c}/drei/home/notes")):
        if lg.endswith(".md"):
            out.append((f"drei:{lg}", f"{c}/drei/home/notes/{lg}", f"{c}/drei/home", f"{c}/drei/decisions.jsonl"))
    shutil.copytree(os.path.join(fix, "drsp"), os.path.join(c, "drsp"))
    out.append(("drsp", f"{c}/drsp/home/notes/dream-log.md", f"{c}/drsp/home", f"{c}/drsp/decisions.jsonl"))
    for fam in ("drmr", "drfc"):
        src = os.path.join(fix, fam)
        vs = ["base"] + sorted(os.listdir(os.path.join(src, "variants")))
        for v in vs:
            w = os.path.join(c, fam, v)
            shutil.copytree(os.path.join(src, "home"), os.path.join(w, "home"))
            dec = os.path.join(src, "decisions.jsonl")
            if v != "base":
                vh = os.path.join(src, "variants", v, "home")
                if os.path.isdir(vh):
                    shutil.copytree(vh, os.path.join(w, "home"), dirs_exist_ok=True)
                dec = os.path.join(src, "variants", v, "decisions.jsonl")
            shutil.copy(dec, os.path.join(w, "decisions.jsonl"))
            out.append((f"{fam}:{v}", f"{w}/home/notes/dream-log.md", f"{w}/home", f"{w}/decisions.jsonl"))
    return out, c


def run(lint, log, home, dec, entry, js, wiki):
    args = ["bash", lint, log] + (["--entry", entry] if entry != "--last" else ["--last"]) + \
           ["--prd-dir", home, "--decisions", dec] + (["--json"] if js else [])
    env = {k: v for k, v in os.environ.items() if k not in ("SKILL_ROUTING_DECISIONS", "DREAM_TERMINAL_READER",
                                                            "DREAM_LINT_TEST_READER", "ACCOUNT_LANE_STATE",
                                                            "FABLE_LAUNCH_TEST")}
    env.update(HOME=home_env, ANALYSIS_WIKI_DIR=wiki)
    p = subprocess.run(args, capture_output=True, text=True, env=env, timeout=300)
    return p.returncode, p.stdout, p.stderr


corpus, cdir = notes()
wiki = os.path.join(cdir, "drrec", "wiki")
lines, bad, n = [], 0, 0
for tag, log, home, dec in corpus:
    ents = re.findall(r"^## (\S+)  /dream  vision-", open(log, encoding="utf-8").read(), re.M)
    for entry in list(dict.fromkeys(ents)) + ["--last"]:
        for js in (False, True):
            mode = "json" if js else "text"
            a, b = run(base, log, home, dec, entry, js, wiki), run(head, log, home, dec, entry, js, wiki)
            n += 1
            what = []
            if a[0] != b[0]:
                what.append(f"exit {a[0]} -> {b[0]}")
            if a[1] != b[1]:
                if js:
                    try:
                        ja, jb = json.loads(a[1]), json.loads(b[1])
                        keys = sorted({k for k in set(ja) | set(jb) if ja.get(k) != jb.get(k)})
                        mk = sorted({k for k in set(ja.get("mission") or {}) | set(jb.get("mission") or {})
                                     if (ja.get("mission") or {}).get(k) != (jb.get("mission") or {}).get(k)})
                        what.append(f"json keys {keys}" + (f" mission keys {mk}" if mk else ""))
                    except ValueError:
                        what.append("stdout differs (not JSON)")
                else:
                    what.append("stdout differs")
            if a[2] != b[2]:
                what.append("stderr differs")
            if what:
                ok = eval(allowed, {"tag": tag, "mode": mode, "entry": entry})
                bad += 0 if ok else 1
                lines.append(f"{tag}\t{mode}\t{entry}\t{'; '.join(what)}\t{'allowed' if ok else 'UNEXPECTED'}")
with open(report, "w", encoding="utf-8") as fh:
    fh.write(f"# compat: {len(corpus)} notes, {n} runs per lint, {len(lines)} differing, {bad} unexpected\n")
    fh.write("".join(x + "\n" for x in lines))
shutil.rmtree(top, ignore_errors=True)
print(f"compat: {len(corpus)} notes, {n} runs per lint, {len(lines)} differing, {bad} unexpected")
sys.exit(1 if bad else 0)
