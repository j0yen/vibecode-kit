"""Retained reviewer probe (re-review 14 of bffbfc29, probes/own/punct14.py), source path made relative to this repo. Not collected by unittest
discovery."""
import os
import sys
S = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts")
sys.path.insert(0, S)
import envelope_validate as ev
v = "Xk9f" + "Q2mP7zab"
forms = ['"password!": "%s"', '"password?": "%s"', '{"password!": ["%s"]}', 'password!=%s', 'password! %s', '"api key!": "%s"',
         '"token#": "%s"', '"secret*": "%s"', "password​: %s", "pass​word: %s", "pass⁠word=%s", "\"pass‍word\": \"%s\"",
         '"foo!": "%s"', "foo​=%s"]
n = 0
for t in forms:
    a, b = v in ev.redact(t % v), v in ev.redact_tool(t % v)
    n += a
    print("%-28r redact_leak=%s tool_leak=%s" % (t, a, b))
print("PUNCT14 redact leaks %d/%d" % (n, len(forms)))
