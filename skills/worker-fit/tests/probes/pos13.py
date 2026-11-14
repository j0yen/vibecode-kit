"""Retained reviewer probe (re-review 13 of e9632349, probes/own/pos13.py), source path made relative to this repo; literal canary words are
assembled from fragments. Not collected by unittest discovery."""
import os
import sys, uuid, random
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev, queue_adapter as qa
r = random.Random(5)
hx = lambda n: "".join(r.choice("0123456789abcdef") for _ in range(n))
POS = [("worker.unit", "ident", u) for u in ("wm-build-inner566-a.service", "r7-irv-a-221051.service", "r7-irv-b-221051.service",
        "wm-build-inner561-a.service", "fleet-token-429-watch.service", "agorabus-reap.timer", "memlog-witness.service",
        "summa-commit.service", "fleet-sync.timer", "prd-sync.service", "token-ledger.service", "aide-account-follow.timer",
        "seat-tick@rb.timer", "swarm-decide-regrade.service", "fleet-merge.timer", "run-r%s.scope" % hx(32), "wm-build@%s.service" % hx(8))] + [
    ("current_owner", "ident", v) for v in ("r7", "rb", "ctl", "hermes", "aide", "orch", "controller", "jyen.pm", "josephsyen")] + [
    ("consumer", "ident", v) for v in ("claude-2004560-r7-wfr13-20261113-worker", "claude-3252684-r7-a1296p2r87rv-20261113", "verifier-1",
                                       "hermes-aae-worker", "claude-1096112-mcphost-table-sql-exec-and-grammar")] + [
    ("target.branch", "ident", v) for v in ("r7/worker-fit-skill", "main", "rb/fix-a1663", "pr-412", "owed-now-hook", "feat/A1663-repair-13",
                                            "prio3-p0p1p2", "mcphost-table-sql-exec-and-grammar")] + [
    ("target.repo", "ident", v) for v in ("j0yen/vibecode-kit", "mcphost", "synthorg", "wm-build", "dotfiles", "j0yen/dotfiles",
                                          "j0yen/swarm-decide", "j0yen/mcphost", "joeyen-atscale/bimpipe")] + [
    ("worker.invocation", "ident", hx(32)), ("sess-id", "ident", str(uuid.UUID(int=r.getrandbits(128)))),
    ("task_id", "ident", "01HZX3K9Q2M7V5N8R4T6W1Y0AB"), ("task_id", "ident", "A1663"), ("task_id", "ident", "A1296"),
    ("task_id", "ident", "WF1663Impl"), ("task_id", "ident", "wmbuild1663impl2"), ("task_id", "ident", "d-20261101-173305-aide-f24a"),
    ("result.artifact", "path", "/mnt/ssd/cargo-target/r7-wfr13-20261113/out/review.md"), ("result.artifact", "path", "/tmp/wf3-k2j_x9ab/b.json"),
    ("result.artifact", "path", "/mnt/data/jsy/tmp/p5task/prio3/repo"), ("result.artifact", "path", "/home/jsy/Notes/prd-priority-selective-unpark-20261111.md"),
    ("head", "sha", "e9632349288cf861ad055ca80ad41b873f15ed45"), ("head", "sha", "0" * 40), ("head", "sha", "3141592"), ("head", "sha", "59d991cb"),
    ("worker.host", "host", "ryzen7"), ("worker.host", "host", "redbaron"), ("worker.host", "host", "carbon"), ("worker.host", "host", "orch"),
    ("worker.host", "host", "ryzen7.tail1234.ts.net"), ("worker.host", "host", "ip-10-0-1-23.ec2.internal"), ("worker.host", "host", "mcphost-1"),
    ("worker.host", "host", "fe80::1%eth0"), ("worker.host", "host", "2001:db8::1"), ("worker.host", "host", "10.0.0.7:22"),
    ("worker.host", "host", "hub"), ("worker.host", "host", "instance-1.us-central1-a.c.proj-123.internal"),
    ("worker.model", "ident", "claude-opus-5-5[1m]"), ("worker.model", "ident", "claude-fable-5-1"), ("worker.account", "ident", "jyen.tech"),
    ("worker.account", "ident", "mcphost.dev"), ("worker.account", "ident", "acct-a")]
ROWS = [("owner", "ctl"), ("owner", "r7"), ("claim", "host:ryzen7:unit:r7-irv-a-221051@2026-11-12T22:11"), ("row", "d-20261111-015556-controller-dd8d"),
        ("waits-on", "A1662"), ("status", "open"), ("claim", "claimed by r7 at 2026-11-13T10:00:00Z")]
op = [(f, v) for f, k, v in POS if v not in ev.show(f, v, k)] + [("row." + f, v) for f, v in ROWS if v not in qa._gate(f, v)]
print("positives %d, opaque %d" % (len(POS) + len(ROWS), len(op)))
for f, v in op:
    print("  OPAQUE", f, v)
