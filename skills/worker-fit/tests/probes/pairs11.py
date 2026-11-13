"""Retained reviewer probe (re-review 11 of 74551e2c, probes/pairs11.py), source path made relative to this repo. Not collected by unittest discovery."""
import sys, random, json, subprocess, tempfile, os
R = None
import os; S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev, queue_adapter as qa
r = random.Random(1111)
A = "abcdefghijklmnopqrstuvwxyz"; B = A.upper() + A + "0123456789"
def hx(n):
    while True:
        s = "".join(r.choice("0123456789abcdef") for _ in range(n))
        if any(c.isdigit() for c in s) and any(c.isalpha() for c in s): return s
lc = lambda n: "".join(r.choice(A) for _ in range(n))
b62 = lambda n: "".join(r.choice(B) for _ in range(n))
dg = lambda n: "".join(r.choice("0123456789") for _ in range(n))
uu = lambda: "-".join([hx(8), hx(4), hx(4), hx(4), hx(12)])
Z = "zq" + "vkwj" + "hxd"  # fake canary, 9 letters
Z2 = "lm" + "4tr9" + "wb"
Z3 = "Xk" + "9fQ2" + "mP7z"
res = []
def idp(field, kind, pos, neg):
    o1 = ev.show(field, pos, kind); o2 = ev.show(field, neg, kind)
    return (pos in o1, neg not in o2)
def rowp(f, pos, neg):
    return (pos in qa._gate(f, pos), neg not in qa._gate(f, neg))
def freep(pos, neg, secret):
    o1 = ev.redact(pos); o2 = ev.redact(neg)
    return (o1 == pos, secret not in o2)
def toolp(pos, neg, secret):
    return (ev.redact_tool(pos) == pos, secret not in ev.redact_tool(neg))
P = []
add = lambda name, kind, *a: P.append((name, kind, a))
# identity fields (pos, neg-of-similar-shape in credential-named field)
add("unit/name", "id", "worker.unit", "ident", "wm-build-wf1663-impl.service", "wm-build-" + b62(14) + ".service")
add("unit/hexsuffix", "id", "worker.unit", "ident", "app-claude@" + hx(8) + ".service", "app-claude@" + b62(24) + ".service")
add("unit/token-word", "id", "worker.unit", "ident", "fleet-token-429-watch.service", "token-" + b62(16) + ".service")
add("unit/glued-vocab", "id", "worker.unit", "ident", "wmbuild1663impl2.service", "wmbuild" + b62(12) + ".service")
add("invocation/h32", "id", "worker.invocation", "ident", hx(32), "inv-" + b62(24))
add("session/uuid", "id", "worker.session", "ident", uu(), "sess-" + b62(24))
add("session/ulid", "id", "worker.session", "ident", "01HZXK3M7Q2V8N5R4T6Y9B0C1D", "01HZXK3M7Q2V8N5R4T6Y9B0C1D" + b62(8))
add("account/name", "id", "worker.account", "ident", "jyen.tech", hx(32))
add("account/uuid", "id", "worker.account", "ident", "mcphost.dev", uu())
add("account/pre-b62", "id", "worker.account", "ident", "jyen.pm", "acct-" + b62(20))
add("model/h40", "id", "worker.model", "ident", "claude-fable-5-1", hx(40))
add("model/pre-h32", "id", "worker.model", "ident", "claude-opus-5-5", "claude-" + hx(32))
add("owner/h64", "id", "current_owner", "ident", "r7", hx(64))
add("owner/b62", "id", "current_owner", "ident", "hermes", b62(20))
add("reviewer/uuid", "id", "reviewed_by", "ident", "hermes", uu())
add("repo/h40", "id", "target.repo", "ident", "j0yen/vibecode-kit", "j0yen/" + hx(40))
add("branch/b62", "id", "target.branch", "ident", "r7/worker-fit-skill", "r7/" + lc(7) + "-" + lc(7) + "-" + lc(7))
add("branch/uuid", "id", "target.branch", "ident", "feature/A1663-fix-gate", "feature/" + uu())
add("task/h64", "id", "task_id", "ident", "A1663", "A1663-" + hx(64))
add("host/random-dns", "id", "worker.host", "host", "ryzen7.tail1234.ts.net", lc(12) + "." + lc(12) + ".net")
add("host/h32", "id", "worker.host", "host", "redbaron", hx(32))
add("host/ipv6-full", "id", "worker.host", "host", "fe80::1%eth0", ":".join(hx(4) for _ in range(8)))
add("consumer/h32", "id", "consumer", "ident", "claude-1275054-hermes-aae", hx(32))
add("consumer/pre-b62", "id", "consumer", "ident", "hermes", "hermes-" + b62(20))
add("artifact/b62", "id", "result", "path", "/mnt/ssd/cargo-target/r7-wfit-20261112/out/report.md", "/mnt/ssd/out/" + b62(24) + ".md")
add("artifact/h64", "id", "result", "path", "/mnt/ssd/cargo-target/r7-wfit-20261112/out/review.md", "/mnt/ssd/out/" + hx(64))
add("event/digits", "id", "event", "path", "evt-20261113-0042", "evt-" + dg(10) + "-" + dg(10))
add("head/nonhex", "id", "head", "sha", hx(40), b62(40))
# queue rows
add("row/id", "row", "row", "d-20261101-173305-aide-f24a", "d-" + b62(6) + "-" + b62(6) + "-" + b62(6) + "-" + b62(6))
add("row/owner-h32", "row", "owner", "hermes", hx(32))
add("row/claim-uuid", "row", "claim", "r7-wfr11-20261113-worker", uu())
add("row/waits-b62", "row", "waits-on", "A1662", "A1662-" + b62(20))
add("row/status", "row", "status", "running", "running-" + b62(20))
# free text
add("free/kv", "free", "exit=0", "password=%s" % Z, Z)
add("free/flag-sp", "free", "--timeout 30", "--password %s" % Z, Z)
add("free/flag-eq", "free", "--retries=3", "--api-key=%s" % Z, Z)
add("free/short-p", "free", "-n 5", "-p %s" % Z, Z)
add("free/json", "free", '{"line": 12}', '{"client_secret": "%s"}' % Z, Z)
add("free/json-esc", "free", '{\\"line\\": 12}', '{\\"client_secret\\": \\"%s\\"}' % Z, Z)
add("free/json-u", "free", '{"line": 12}', '{"pass\\u0077ord": "%s"}' % Z, Z)
add("free/json-dbl", "free", '\\\\"line\\\\": 12', '\\\\"secret\\\\": \\\\"%s\\\\"' % Z, Z)
add("free/json-str", "free", json.dumps({"x": json.dumps({"line": 12})}), json.dumps({"x": json.dumps({"password": Z})}), Z)
add("free/nested-obj", "free", '{"meta": {"line": 12}}', '{"credentials": {"inner": {"v": "%s"}}}' % Z, Z)
add("free/nested-arr", "free", '{"lines": [1,2]}', '{"tokens": ["%s", "%s"]}' % (Z, Z2), Z)
add("free/pct", "free", "path=%2Fvar%2Flog", "password%%3D%s" % Z, Z)
add("free/url-userinfo", "free", "https://host.example/p?x=1", "https://bob:%s@host.example/p" % Z, Z)
add("free/quoted-mw", "free", 'note="build ok"', 'password="%s %s"' % (Z, Z2), Z)
add("free/camel", "free", "lineCount=12", "clientSecret=%s" % Z, Z)
add("free/leet", "free", "line=12", "p4ssw0rd=%s" % Z, Z)
add("free/glue-digit", "free", "line=12", "password1%s" % Z, Z)
add("free/glue-letter", "free", "line=12", "mypassword=%s" % Z, Z)
add("free/unlisted-name-num4", "free", "count=1234", "mfa=4821", "4821")
add("free/unlisted-name-num2", "free", "pid=42", "dbpw=42", "dbpw=42")
add("free/numeric-name-secret", "free", "pid=4242", "seq=%s" % dg(9), None)
add("free/mid-word", "free", "retries: 3", "hush=ab-cd", "hush=ab-cd")
add("free/vocab-passphrase", "free", "state: queue-support", "sekrit=queue-support-timeout", "queue-support-timeout")
add("free/hex-under-hexname", "free", "head=a1b2c3d4e5f6", "blob=a1b2c3d4e5f6", "a1b2c3d4e5f6")
add("free/bare-prose", "free", "the build is ok", "the password is %s" % Z, Z)
add("free/header", "free", "Accept: text/plain", "Authorization: Bearer %s" % Z, Z)
add("free/code-kv", "free", "exit code=2", "code=%s" % Z, Z)
add("free/code-json", "free", '{"exit_code": 2}', '{"code": "%s"}' % Z, Z)
add("free/code-query", "free", "https://x.example/cb?state=1", "https://x.example/cb?code=%s&state=1" % Z, Z)
add("free/code-num6", "free", "status_code=404", "code=482917", "482917")
add("free/pin-flag", "free", "--port 8080", "--pin 4821", "4821")
add("free/schema-name-h32", "free", "invocation=%s" % hx(32), "account=%s" % hx(32), None)
add("free/digits-under-ids", "free", "--pid 12345", "--seed 12345678", "12345678")
add("free/escaped-nl", "free", "a=1", "a=1\\npassword=%s" % Z, Z)
add("free/kv-3d", "free", "retries=3", "otp=%s" % dg(3), None)

add("free/numsuffix-number", "free", "line_number=482917", "recovery_number=482917", "482917")
add("free/numsuffix-count", "free", "retry_count=4", "mfacount=482917", "482917")
add("free/numsuffix-limit", "free", "max_retries=3", "unlock_limit=4829175310", "4829175310")
add("free/prose-api_key", "free", "the build is ok", "the api_key is %s" % Z3, Z3)
add("free/prose-client_secret", "free", "state ok", "client_secret %s" % Z3, Z3)
add("free/prose-private-key", "free", "state ok", "private key %s" % Z3, Z3)
add("free/prose-access_token", "free", "state ok", "the access_token is %s" % Z3, Z3)
add("id/effort-medium", "id", "worker.effort", "ident", "medium", b62(12))
add("id/unit-fleet-agent", "id", "worker.unit", "ident", "agorabus-reap.timer", "agorabus-" + b62(14) + ".timer")
add("id/consumer-peer", "id", "consumer", "ident", "claude-3947245-r7-a1303rv8-20261113-worker", "claude-3947245-r7-" + b62(12) + "-worker")
out = []
for name, kind, a in P:
    if kind == "id":
        pp, nh = idp(*a)
        sec = a[3]
    elif kind == "row":
        pp, nh = rowp(*a); sec = a[2]
    else:
        pos, neg, sec = a
        if sec is None:
            sec = neg.split("=")[-1].split(" ")[-1]
            if name == "free/schema-name-h32":
                sec = neg.split("=")[1]
        o1 = ev.redact(pos); o2 = ev.redact(neg)
        if sec in ("dbpw=42", "hush=ab-cd"):
            sec = sec.split("=")[1]
        pp = (o1 == pos) or (pos in o1) ; nh = sec not in o2
    out.append((name, pp, nh))
ok = 0
for n, pp, nh in out:
    g = pp and nh; ok += g
    print("%-26s pos_prints=%-5s neg_hidden=%-5s %s" % (n, pp, nh, "" if g else "<<<"))
print("PAIRS %d/%d" % (ok, len(out)))
