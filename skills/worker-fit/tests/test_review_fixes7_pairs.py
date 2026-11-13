"""The reviewer's identity pair table of re-review 6 (29 identity positives, each with three credential negatives of the
same value in the same field: `token=V`, a `--api-key V` flag in free text, a nested credential object), the eight
credential-in-ID-grammar negatives, the escaped-JSON negatives and the mixed-alphanumeric positives, retained as
regression tests. Values are assembled at run time from fragments; nothing is printed."""
import json
import unittest

import helpers  # noqa: F401  (puts scripts/ on sys.path)
import recommend as rc
import test_review_fixes3 as t3
from test_review_fixes7 import N, hx, setp, short, uuid

running, done, one = t3.running, t3.done, t3.one

ULID = "01HZX3K9Q2M7V5N8R4T6W1Y0AB"


def positives():
    H, H12, H40, U = hx(32), hx(12, 5), hx(40, 4), uuid()
    return [
        ("worker.host", "ryzen7.tail1a2b3.ts.net"), ("worker.host", "i-0abc123def4567890"), ("worker.host", "jsy@ryzen7"),
        ("worker.host", "10.0.0.5"),
        ("worker.unit", "wm-build-%s.service" % H), ("worker.unit", "run-r%s.scope" % H), ("worker.unit", "coder@%s.service" % U),
        ("worker.unit", "wm-build-20261113T104303Z.service"), ("worker.unit", "w-WF-1663-r7-wfr6-20261113.service"),
        ("worker.unit", "codex-exec-%s.service" % H12),
        ("worker.child", "pid:2659106"), ("worker.child", "run-r%s.scope" % H), ("worker.child", "child-%s" % H40),
        ("worker.session", U), ("worker.session", H), ("worker.session", "sess-" + U), ("worker.session", ULID),
        ("worker.invocation", H), ("worker.invocation", "inv-20261113T104303Z-0007"), ("worker.invocation", U),
        ("consumer.named", "verifier-%s" % H12), ("consumer.named", "hermes"), ("consumer.named", "verifier-%s" % H),
        ("target.head", H40), ("target.head", H12),
        ("result.artifact", "/mnt/ssd/cargo-target/x/out/review.md"), ("result.artifact", "/retained/WF-1/result-%s.json" % H),
        ("result.event", "evt-%s" % H), ("result.artifact", "/retained/%s/review-%s.json" % (U, H12)),
    ]


def build(field, value):
    d = done() if field.startswith(("consumer", "result")) else running()
    if field == "result.event":
        d["result"]["artifact"] = None
    if field == "consumer.named":
        d["consumer"]["available"] = True
    return setp(d, field, value)


def shown(r):
    return "\n".join(r["evidence_used"] + [r["next_consumer"]] + r["later_consumers"])


def everything(r):
    return json.dumps(r) + "\n" + rc.render_text([r])


class ReviewerPairTable(unittest.TestCase):
    def test_every_positive_prints_and_its_three_credential_negatives_stay_hidden(self):
        for field, v in positives():
            r = one(build(field, v))
            self.assertIn(v, shown(r), (field, v))
            for label, neg in (("kv", build(field, N("tok", "en") + "=" + v)),
                               ("flag", dict(running(), coverage_gaps=["run --api-key %s now" % v])),
                               ("nested", dict(running(), coverage_gaps=['{"credentials": {"k": ["%s"]}}' % v]))):
                self.assertNotIn(v, everything(one(neg)), (label, field, v))

    def test_eight_credential_in_id_grammar_negatives(self):
        H, H40, U = hx(32), hx(40, 4), uuid()
        cases = [("worker.host", "admin:%s@10.0.0.5" % H, H), ("worker.host", "%s@ryzen7" % H40, H40),
                 ("worker.host", "bob:%s@ryzen7" % short(), short()), ("worker.unit", "token-%s.service" % H, H),
                 ("worker.session", "Bearer-%s" % H, H), ("worker.invocation", "pat_%s" % H, H),
                 ("result.artifact", "/retained/secret/%s.json" % H, H),
                 ("evidence.0.ref", "token=%s" % H40, H40), ("worker.unit", "secret@%s.service" % U, U),
                 ("coverage_gaps.0", '{\\"token\\":\\"%s\\"}' % short(), short())]
        for field, v, needle in cases:
            d = build(field, v) if field != "coverage_gaps.0" else dict(running(), coverage_gaps=[v])
            self.assertNotIn(needle, everything(one(d)), (field, v))

    def test_mixed_alphanumeric_names_are_reused(self):
        for field, v in [("worker.unit", "wm-build-WF1663Impl.service"), ("worker.unit", "claude-r7wfr6review.service"),
                         ("worker.unit", "codex-r7wfitfix2.service"), ("worker.unit", "wm-build-w1663impl-r7.service"),
                         ("worker.unit", "wfr6review20261113.service"), ("worker.child", "run-r7wfr620261113.scope"),
                         ("worker.host", "ryzen7build20261113.local"), ("worker.unit", "wmbuild1663impl2.service"),
                         ("worker.host", "ip-10-0-1-5.us-west-2.compute.internal"),
                         ("worker.unit", "claude-1481257-r7-wfr6-20261113-worker.service"),
                         ("worker.unit", "vibecode-kit-worker-fit-skill-review6.service")]:
            r = one(build(field, v))
            self.assertEqual(r["disposition"], "reuse-active-worker", v)
            self.assertIn(v, shown(r), v)


if __name__ == "__main__":
    unittest.main()
