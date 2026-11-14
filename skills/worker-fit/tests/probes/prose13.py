"""Retained reviewer probe (re-review 13 of e9632349, probes/own/prose13.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys, random, json
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
r = random.Random(1313)
A = "abcdefghijklmnopqrstuvwxyz"; B = A + A.upper() + "0123456789"
rs = lambda n, a: "".join(r.choice(a) for _ in range(n))
listed = ["dbpass", "userpass", "mypass", "rootpw", "dbpw", "unlock", "vault"]
own = ["adminpass", "wifipass", "mysqlpwd", "rootpasswd", "dbsecret", "apitoken", "authtoken", "svcpin", "atmpin", "dbcreds",
       "smtppassword", "ldappw", "vpnpasscode", "gitpat", "dbkey", "masterkey", "wpakey", "unlockcode", "vaultpass", "pword",
       "passwrd", "pswrd", "pazzword", "p4ssword", "passw0rd", "s3cret", "t0ken", "pwd2", "DbPass", "RootPw", "MyPassword",
       "dbPassword", "userPwd", "DB_PASS", "db-pass", "passcodes", "secretz", "keyphrase", "passkey", "logincode", "signin", "pincode"]
vals = {"mixed12": lambda: rs(4, B) + "9" + rs(3, B) + "Q" + rs(3, B), "lower10": lambda: rs(10, A), "num6": lambda: rs(6, "0123456789"),
        "num4": lambda: rs(4, "0123456789"), "word8": lambda: r.choice(["sun" + "shine", "dragon" + "fly", "foot" + "ball", "prin" + "cess"]),
        "lower24": lambda: rs(24, A)}
forms = ["{n} {v}", "the {n} is {v}", "{n} is {v}", "my {n} {v} please", "{n} = {v}", "{n}: {v}", "\"{n}\": \"{v}\"", "{n}='{v}'",
         "set {n} to {v}", "{{\"cfg\": {{\"{n}\": \"{v}\"}}}}", "--{n} {v}", "--{n}={v}", "{n} was {v}.", "use {n} \"{v}\" now"]
res = {}
for nset, names in (("listed", listed), ("own", own)):
    for n in names:
        for vn, vf in vals.items():
            for fm in forms:
                v = vf()
                txt = fm.format(n=n, v=v)
                o1 = ev.redact(txt)
                o2 = ev.redact_tool(txt)
                if v in o1:
                    res.setdefault((nset, "redact", vn), set()).add(n)
                if v in o2:
                    res.setdefault((nset, "tool", vn, fm), set()).add(n)
for k in sorted(k for k in res if k[1] == "redact"):
    print("REDACT-LEAK %-6s %-8s %2d names: %s" % (k[0], k[2], len(res[k]), sorted(res[k])))
tool = {}
for k, ns in res.items():
    if k[1] == "tool":
        tool.setdefault((k[0], k[3]), set()).update(ns)
for k in sorted(tool):
    print("TOOL-LEAK %-6s form %-28r %d names" % (k[0], k[1], len(tool[k])))
