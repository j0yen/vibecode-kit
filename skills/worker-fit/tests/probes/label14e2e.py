"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/label14e2e.py), source path made relative to this repo. Not collected by unittest
discovery."""
import sys, json, copy, os, subprocess, tempfile
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
base = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "fixtures", "review", "f_good.json")))
v = "Xk9f" + "Q2mP7zab"
texts = ["login notes: Password*: %s (rotate monthly)" % v, "creds in the wiki, API key*: %s" % v, "[password]: %s" % v, "Password (required): %s" % v, "PIN#: 4829" + "17"]
for i, t in enumerate(texts):
    for where in ("coverage_gaps", "next_action", "evidence.ref"):
        e = copy.deepcopy(base)
        if where == "coverage_gaps": e["coverage_gaps"] = [t]
        elif where == "next_action": e["next_action"] = t
        else: e["evidence"][0]["ref"] = t
        fd, p = tempfile.mkstemp(suffix=".json"); os.close(fd); json.dump({"envelopes": [e]}, open(p, "w"))
        outs = []
        for args in ([S + "/recommend.py", "--now", "2026-11-13T07:00:00Z", p], [S + "/recommend.py", "--now", "2026-11-13T07:00:00Z", "--format", "json", p],
                     [S + "/envelope_validate.py", "--now", "2026-11-13T07:00:00Z", p]):
            o = subprocess.run([sys.executable, "-B"] + args, capture_output=True, text=True)
            outs.append((v if i < 4 else "482917") in (o.stdout + o.stderr))
        os.unlink(p)
        print("text#%d %-14s rec-text=%s rec-json=%s validate=%s" % (i, where, *outs))
