"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/pos14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys, uuid, random
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev, queue_adapter as qa
r = random.Random(14)
hx = lambda n: "".join(r.choice("0123456789abcdef") for _ in range(n))
DEF3 = [("target.repo", "ident", "dotfiles"), ("target.repo", "ident", "j0yen/dotfiles"), ("worker.unit", "ident", "aide-account-follow.timer"),
        ("worker.unit", "ident", "wm-build-inner566-a.service"), ("worker.unit", "ident", "token-ledger.service"),
        ("target.branch", "ident", "prio3-p0p1p2"), ("consumer", "ident", "claude-3252684-r7-a1296p2r87rv-20261113"),
        ("result.artifact", "path", "/home/jsy/Notes/prd-priority-selective-unpark-20261111.md")]
POS = [("worker.unit", "ident", u) for u in (
        "summa-commit.timer", "fleet-dash-collect.service", "seat-tick@r7.timer", "aide-wake.timer", "swarm-decide-regrade.timer",
        "fleet-guard.service", "prd-sync.timer", "memlog-witness.timer", "agorabus-reap.service", "user@1000.service",
        "app-gnome-Terminal-4242.scope", "session-3.scope", "wm-build-rb-a1777-20261114.service", "claude-seat@ctl.service",
        "wm-build-inner12-b.service", "fleet-token-jyentech-mon.timer", "aide-account-follow.service", "seat-ask-due.timer",
        "fleet-merge.service", "run-r%s.scope" % hx(32), "wm-build-inner9-c.service")] + [
    ("consumer", "ident", v) for v in ("claude-515371-r7-aaerv9-20261114-worker", "claude-3381216-r7-a1572tc-20261113-worker",
                                       "claude-4153553-r7-wfr14-20261114", "verifier-7", "hermes", "coder-3", "claude-77-rb-a57-20261101")] + [
    ("alternate", "ident", v) for v in ("rb", "ctl", "verifier-2")] + [
    ("target.branch", "ident", v) for v in ("rb/owed-now-hook", "r7/wfit-repair-14", "pr-1999", "feat/A1777-quota-gate", "prio2-p0p1",
                                            "hotfix/fleet-dash-version", "r7/a1572tc", "main")] + [
    ("target.repo", "ident", v) for v in ("j0yen/fleet-dash", "j0yen/agorabus", "j0yen/summa", "joeyen-atscale/bimpipe-buildloop",
                                          "j0yen/wintermute", "j0yen/swarm-decide", "vibecode-kit")] + [
    ("worker.host", "host", v) for v in ("carbon.tail9z8y7.ts.net", "ip-172-31-5-9.us-west-2.compute.internal", "redbaron.local",
                                         "fe80::1c2b:3aff:fe4d:5e6f%wlan0", "100.101.102.103", "ryzen7", "mcphost-1", "hub")] + [
    ("task_id", "ident", v) for v in ("A1777", "A1663-r14", "P32", "M3", "A57", "C096", "d-20261114-043013-r7-9f3c", "r7wfr14",
                                      "01J9ZX3K9Q2M7V5N8R4T6W1Y0C")] + [
    ("result.artifact", "path", v) for v in ("/mnt/ssd/cargo-target/r7-wfr14-20261114/out/findings.json", "/tmp/tmpk2j_x9ab/env.json",
                                             "/home/jsy/Notes/prd-dotfiles-prefix-admit-20261102.md", "/home/jsy/.cache/aide/open-asks.tsv",
                                             "/mnt/ssd/cargo-target/r7-a1572tc-20261113/out/report.md",
                                             "~/Notes/wiki/decisions/2026-10-31-week-plan-quota-to-launch-wwhtbt.md",
                                             "/mnt/ssd/cargo-target/r7-wfr14-20261114/tmp/tmpq8z_3k1m.json")] + [
    ("worker.invocation", "ident", hx(32)), ("sess-id", "ident", str(uuid.UUID(int=r.getrandbits(128)))),
    ("head", "sha", "bffbfc29e342c41e262adb0e2cb74c80a05d34af"), ("head", "sha", "4092317"), ("head", "sha", "31ac1c4"),
    ("worker.model", "ident", "claude-sonnet-5-5"), ("worker.model", "ident", "claude-haiku-5-5"), ("worker.model", "ident", "claude-fable-5-1[1m]"),
    ("worker.account", "ident", "jyen.pm"), ("worker.account", "ident", "josephsyen"), ("worker.account", "ident", "mcphost.dev")]
ROWS = [("owner", "aide"), ("waits-on", "rb"), ("status", "blocked"), ("claim", "claimed by ctl at 2026-11-14T04:00:00Z"),
        ("row", "d-20261114-043013-r7-9f3c"), ("owner", "r7"), ("waits-on", "A1777"), ("claim", "host:redbaron:unit:wm-build-rb-a1777-20261114")]
for name, pos in (("DEF-3 set", DEF3), ("own set", POS)):
    op = [(f, v) for f, k, v in pos if ev.unmark(ev.show(f, v, k)) != v]
    print("%s: positives %d, opaque %d" % (name, len(pos), len(op)))
    for f, v in op:
        print("  OPAQUE", f, v)
opr = [(f, v) for f, v in ROWS if qa._gate(f, v) != v]
print("rows: positives %d, opaque %d %s" % (len(ROWS), len(opr), opr))
