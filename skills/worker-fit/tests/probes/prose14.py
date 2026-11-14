"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/prose14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys, random, json
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
r = random.Random(1414)
A = "abcdefghijklmnopqrstuvwxyz"; B = A + A.upper() + "0123456789"
rs = lambda n, a: "".join(r.choice(a) for _ in range(n))
NAMES = {
  "nonenglish": ["contrasena", "passwort", "motdepasse", "senha", "clave", "kennwort", "jelszo", "heslo", "geheimnis", "losenord",
                 "sifre", "parol", "wachtwoord", "salasana"],
  "abbrev": ["psw", "pss", "pwds", "tkn", "tok", "skey", "privk", "pinno", "totp", "otpcode", "mfacode", "seedphrase", "mnemonic",
             "passkey", "sesstoken", "apitok", "authtok"],
  "leet": ["p@ssword", "pa$$word", "pa55w0rd", "p455w0rd", "s3cr3t", "t0k3n", "secr3t", "p4ss", "c0de", "k3y", "pa55", "passw0rd!"],
  "misspelt": ["passowrd", "pasword", "paswrod", "pssword", "psswrd", "secrit", "secert", "toekn", "tokn", "crediental",
               "credentails", "passwod", "passworf"],
  "compound": ["rootsecret", "mysecretz", "adminpin", "wifikey", "routerpw", "authcode", "accesscode", "securitycode", "smscode",
               "oneTimeCode", "otpCode", "PIN_CODE", "pin-number", "unlockpin", "signingkey", "apisecret", "Login_Password",
               "userPassphrase", "x-api-key", "sudo_pass"],
}
vals = {"mixed12": lambda: rs(4, B) + "9" + rs(3, B) + "Q" + rs(3, B), "lower10": lambda: rs(10, A), "num6": lambda: rs(6, "0123456789"),
        "word": lambda: r.choice(["lantern", "biscuit", "walnut", "harbor"]), "lower24": lambda: rs(24, A)}
forms = ["{n} {v}", "the {n} is {v}", "{n}: {v}", "{n}={v}", "\"{n}\": \"{v}\"", "--{n} {v}", "{n} was {v}.", "use {n} '{v}' now",
         "{{\"cfg\": {{\"{n}\": [\"{v}\"]}}}}", "{n} -> {v}", "{n} = \"{v}\""]
leak = {}
cases = 0
for cls, names in NAMES.items():
    for n in names:
        for vn, vf in vals.items():
            for fm in forms:
                v = vf()
                cases += 1
                if v in ev.redact(fm.format(n=n, v=v)):
                    leak.setdefault((cls, n), set()).add((vn, fm))
# quoted multiword values (DEF-2 second part), own names and phrasings
multi = 0; mleak = []
for n in ["password", "passphrase", "pin", "secret", "dbpass", "wifipass", "s3cret"]:
    for fm in ['{n} "{a} {b} {c}"', 'the {n} is "{a} {b} {c}"', "{n} '{a} {b} {c}' ok", '{n}: "{a} {b} {c}"', '{n} is `{a} {b} {c}`',
               '{n} = "{a} {b} {c}"', '{n} “{a} {b} {c}”']:
        a, b, c = rs(6, A), rs(7, A), rs(5, A)
        o = ev.redact(fm.format(n=n, a=a, b=b, c=c))
        multi += 1
        if b in o or c in o or a in o:
            mleak.append((n, fm))
total = sum(len(v) for v in NAMES.values())
print("names: %d own, cases %d; names leaking a value in redact(): %d" % (total, cases, len(leak)))
for cls in NAMES:
    ns = sorted(n for (c, n) in leak if c == cls)
    print("  %-10s %2d/%2d leak: %s" % (cls, len(ns), len(NAMES[cls]), ns))
for (c, n), fs in sorted(leak.items()):
    print("    LEAK %-14s %s" % (n, sorted(set(f for _, f in fs))[:4]))
print("quoted multiword: %d/%d leak a word: %s" % (len(mleak), multi, mleak))
# false positives: ordinary prose of my own that must stay readable (byte-identical)
PROSE = ["the login page loads in 2 seconds", "the key point is that the queue drains", "exit code 2 means a usage error",
         "please sign in before the review", "pass the test suite twice", "a code review of the patch", "the token bucket refills hourly",
         "the secret sauce is caching", "a passport photo is attached", "the passage on page 4", "a compass and a map",
         "the keyboard layout changed", "the monkey test found a crash", "the barcode scanner failed", "decode the base64 header",
         "the keynote starts at noon", "the password reset flow failed for user alice", "the token expired at 09:00",
         "password field is required", "pin the version to 3.12", "seed the random generator with 42", "the vault was sealed",
         "unlock the door at 8", "the auth service restarted", "key rotation runs weekly", "the code is on main",
         "logon scripts run at boot", "the pass rate was 98 percent", "the secret santa list", "the pinned issue moved",
         "the signin button is blue", "the login flow uses oauth", "pins and needles", "a phrase from the book"]
same = [p for p in PROSE if ev.redact(p) == p]
print("ordinary prose byte-identical: %d/%d" % (len(same), len(PROSE)))
for p in PROSE:
    if ev.redact(p) != p:
        print("  CHANGED: %r -> %r" % (p, ev.redact(p)))
