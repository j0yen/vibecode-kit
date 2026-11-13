"""First falsifier: reproduce the captured ctl-event-wait.sh actor-name discriminator."""
import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "discriminator_check.py"
FIX = HERE / "fixtures" / "ctl-event-wait.sh"
SHA = HERE / "fixtures" / "ctl-event-wait.sh.sha256"

ACCEPT = ["ctl-intake-consumer", "rb", "r7", "controller", "plain",
          "hermes-1", "joe-20261112", "fivewhys-x"]
REFUSE_CONDITIONAL = ["ops", "bld", "rls"]
REFUSE_UNRELATED = ["totally-unrelated-source"]


def run(*args):
    return subprocess.run([sys.executable, "-I", str(SCRIPT), *args],
                          capture_output=True, text=True)


class Falsifier(unittest.TestCase):
    def test_fixture_sha256_matches_capture(self):
        want = SHA.read_text().split()[0]
        got = hashlib.sha256(FIX.read_bytes()).hexdigest()
        self.assertEqual(got, want, "fixture is not the captured file")

    def test_different_file_fails_sha(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "other.sh"
            p.write_bytes(FIX.read_bytes() + b"# tampered\n")
            r = run(str(p), "--line", "28", "--names", "rb",
                    "--sha256", SHA.read_text().split()[0])
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("sha256 mismatch", r.stdout + r.stderr)

    def check(self, names):
        r = run(str(FIX), "--line", "28", "--names", ",".join(names),
                "--sha256", SHA.read_text().split()[0], "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_positive_controls_accepted(self):
        out = self.check(ACCEPT)
        for n in ACCEPT:
            self.assertEqual(out["results"][n], "accept", n)

    def test_ops_bld_rls_and_unrelated_refused(self):
        out = self.check(REFUSE_CONDITIONAL + REFUSE_UNRELATED)
        for n in REFUSE_CONDITIONAL + REFUSE_UNRELATED:
            self.assertEqual(out["results"][n], "refuse", n)

    def test_disposition_is_conditional_risk(self):
        out = self.check(REFUSE_CONDITIONAL)
        for n in REFUSE_CONDITIONAL:
            self.assertEqual(out["labels"][n], "conditional-risk")
        self.assertIn("not shown", out["note"])
        self.assertNotIn("lost", out["note"].replace("not evidence that live messages are lost", ""))

    def test_text_output_lines(self):
        r = run(str(FIX), "--line", "28", "--names", "rb,ops")
        self.assertIn("accept rb", r.stdout)
        self.assertIn("refuse ops", r.stdout)

    def test_never_executes_file(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "ran"
            p = Path(d) / "x.sh"
            p.write_text(f"touch {marker}\nACT='^[^|]*\\| *(rb) *\\|'\n")
            r = run(str(p), "--line", "2", "--names", "rb,ops")
            self.assertFalse(marker.exists())
            self.assertIn("accept rb", r.stdout)

    def test_bad_locator_errors(self):
        r = run(str(FIX), "--line", "1", "--names", "rb")
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
