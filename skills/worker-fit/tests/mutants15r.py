"""Mutation check, repair 15 recovery: every mutant of mutants15.py (unchanged anchors) plus mutants of the name-rule cache added after
the repair 15 head 263a1a69 (the DEF-F readings cost one evaluation per word occurrence): the cache bypassed, keyed on a prefix of the
word, and never emptied; part 2: the prose-name reading cache bypassed, keyed without the glued flag and never emptied, and the
ASCII fast path of the format-character view taken for any text or never taken. Each mutant applies ONE source change to a COPY of the skill and runs the named test modules; caught = red; a
mutant whose scripts do not import is NOT-APPLIED. EXIT STATUS: 0 only when every mutant is caught; a survivor or NOT-APPLIED mutant exits
1, a red baseline 2.
usage: python3 tests/mutants15r.py [test_module ...]   (not collected by unittest discovery)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv, _argv = [sys.argv[0]], sys.argv
import mutants11 as base
import mutants15
sys.argv = _argv
EV = base.EV
R = [
 ("m201", "name-rule cache bypassed", EV, "    hit = _NOUN_RULE_CACHE.get(low, _NOUN_RULE_CACHE)\n", "    hit = _NOUN_RULE_CACHE\n"),
 ("m202", "name-rule cache keyed on a prefix", EV, "    hit = _NOUN_RULE_CACHE.get(low, _NOUN_RULE_CACHE)\n",
  "    hit = _NOUN_RULE_CACHE.get(low[:4], _NOUN_RULE_CACHE)\n    _NOUN_RULE_CACHE.setdefault(low[:4], _noun_by_rule_eval(low))\n"),
 ("m203", "name-rule cache never emptied", EV, "        if len(_NOUN_RULE_CACHE) > 8192:\n            _NOUN_RULE_CACHE.clear()",
  "        if False:\n            _NOUN_RULE_CACHE.clear()"),
 # part 2: the prose-name reading cache and the ASCII format view
 ("m204", "prose-name cache bypassed", EV, "    hit = _CRED_NOUN_CACHE.get(key)\n", "    hit = None\n"),
 ("m205", "prose-name cache key drops the glued flag", EV, "    key = (word, bool(glued))\n", "    key = word\n"),
 ("m206", "prose-name cache never emptied", EV, "        if len(_CRED_NOUN_CACHE) > 8192:\n            _CRED_NOUN_CACHE.clear()",
  "        if False:\n            _CRED_NOUN_CACHE.clear()"),
 ("m207", "format view skipped for any text", EV, "    if text.isascii():\n        return text\n", "    if True:\n        return text\n"),
 ("m208", "format view scans ASCII text", EV, "    if text.isascii():\n        return text\n", "    if False:\n        return text\n"),
]
M = mutants15.M + R
MODS = [a for a in sys.argv[1:] if not a.startswith("--")] or (mutants15.MODS + ["test_review_fixes15_cost", "test_review_fixes15_cost2"])

if __name__ == "__main__":
    sys.exit(base.main(M, MODS))
