import json
import re
import unittest

from helpers import FIX, SKILL

import envelope_validate as ev


class SkillSource(unittest.TestCase):
    def setUp(self):
        self.text = (SKILL / "SKILL.md").read_text()

    def test_frontmatter(self):
        m = re.match(r"---\n(.*?)\n---\n", self.text, re.S)
        self.assertTrue(m)
        fm = m.group(1)
        self.assertIn("name: worker-fit", fm)
        self.assertIn("model: sonnet", fm)
        self.assertIn("effort: medium", fm)
        self.assertIn("description:", fm)

    def test_states_boundaries_plainly(self):
        t = " ".join(self.text.lower().split())
        for phrase in ("recommendation only", "grants no action authority", "does not prove production behavior",
                       "is not a worker launch", "unknown", "never launches"):
            self.assertIn(phrase, t, phrase)
        for role in ("implementation", "independent-verification", "coordinator-decision", "deterministic-service"):
            self.assertIn(role, self.text)
        for disp in ("reuse-active-worker", "consume-completed-terminal", "ready-unowned-slice", "blocked"):
            self.assertIn(disp, self.text)

    def test_template_envelope_is_valid(self):
        self.assertEqual(ev.validate(json.loads((SKILL / "templates" / "envelope.template.json").read_text())), [])

    def test_fixtures_are_labelled_source_only_and_clean(self):
        bad = re.compile(r"token=|sk-ant|password|bearer|PRIVATE KEY|api[_-]?key", re.I)
        for p in FIX.glob("*.json"):
            txt = p.read_text()
            self.assertIn("source-only", txt, p.name)
            self.assertIsNone(bad.search(txt), p.name)

    def test_scripts_use_only_the_standard_library(self):
        allowed = {"json", "sys", "os", "string", "datetime", "envelope_validate", "queue_adapter"}
        for p in (SKILL / "scripts").glob("*.py"):
            mods = set(re.findall(r"^(?:import|from)\s+(\w+)", p.read_text(), re.M))
            self.assertLessEqual(mods, allowed, p.name)


if __name__ == "__main__":
    unittest.main()
