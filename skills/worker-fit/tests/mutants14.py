"""Mutation check, repair 14: every mutant of mutants13.py (anchors kept current: m7, m16, m35 in mutants11.py and m62, m66, m75, m79
in mutants12.py re-pointed because the row whitespace charge, the counted single letter, the structure-word cap, the name-rule
readings, the shared repo budget and the per-piece walk moved those lines) plus mutants of the repair-14 code, at least one per
defect of re-review 13: DEF-1 an unbounded or uncharged timestamp fraction, an uncharged single letter, uncounted dates, structure
words, separators, DNS labels, template literals, row whitespace, a separate repo-owner budget; DEF-2 each rule form of the
credential-name rule dropped, a quoted value hiding only its first word, the readable list widened to a credential compound or
emptied; DEF-3 each exact template widened to admit a credential negative, a template allowed in every field, a fleet word dropped;
DEF-4 the documented bounds changed. Each mutant applies ONE source change to a COPY of the skill and runs the named test modules;
caught = red. EXIT STATUS: 0 only when every mutant is caught; a survivor or NOT-APPLIED mutant exits 1, a red baseline exits 2.
usage: python3 tests/mutants14.py [test_module ...]   (not collected by unittest discovery)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv, _argv = [sys.argv[0]], sys.argv
import mutants11 as base
import mutants13
sys.argv = _argv
EV = base.EV
SK = "SKILL.md"
N = [
 # DEF-1
 ("m120", "timestamp fraction unbounded", EV, r'(?P<frac>\.\d{1,%d}(?!\d))?', r'(?P<frac>\.\d+)?'),
 ("m121", "timestamp fraction not charged", EV, 'st["digits"] += len(m.group(1) or ".") - 1', "pass"),
 ("m122", "single letters between numbers: no cap", EV, "_MAX_LETTER_GAP = 1 ", "_MAX_LETTER_GAP = 99 "),
 ("m123", "dates not counted", EV, 'and st["dates"] <= _MAX_DATES and', "and"),
 ("m124", "structure words not counted", EV, 'and st["struct"] <= _MAX_STRUCT_WORDS', ""),
 ("m125", "separator runs not charged", EV, 'st["cost"] += len(run) - 1 + (run[0] not in _FREE_JOINERS)', "pass"),
 ("m126", "DNS labels free", EV, '    if low == st["tail"] and not st["tail_used"]', '    if low in _DNS_WORDS:\n        return\n    if low == st["tail"] and not st["tail_used"]'),
 ("m127", "row whitespace not charged", EV, "cost0=spaces)):  # a queue row", "cost0=0)):  # a queue row"),
 ("m128", "repo owner and name with separate budgets", EV, '        ok = _gate_pieces([name], max_ids, dict(prof, slash=False), st, profile is not None)',
  '        st["cost"] = 0\n        ok = _gate_pieces([name], max_ids, dict(prof, slash=False), st, profile is not None)'),
 ("m129", "template literals not counted", EV, '        st["vocab"] += 1\n        return True  # a literal', '        return True  # a literal'),
 ("m130", "free-text timestamp fraction unbounded", EV, r'(?::\d{2}(?:\.\d{1,%d}(?!\d))?)?(?:Z|[+-]\d{2}:?\d{2})?)?" % _MAX_FRACTION)', r'(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?")'),
 # DEF-2
 ("m131", "de-leet off", EV, "    if not _LEET_RUN.search(w):", "    if True:"),
 ("m132", "plural form off", EV, "if low in _SIGN_ON or any((b in _STRONG_NOUNS and b not in _PLURAL_EXCEPT) or b in _SIGN_ON for b in _plurals(low)):", "if low in _SIGN_ON:"),
 ("m133", "misspelt form off", EV, "    if _misspelt(low):\n        return _RULE_NAME", "    if False:\n        return _RULE_NAME"),
 ("m134", "weak glue form off (key/code/phrase/pat)", EV, "if low.endswith(n) and 0 < len(low) - len(n) <= _MAX_GLUE_QUALIFIER:", "if False:"),
 ("m135", "sign-on nouns off", EV, '_SIGN_ON = frozenset("signin|signon|login|logon".split("|"))', "_SIGN_ON = frozenset()"),
 ("m136", "a quoted value hides only its first word", EV, "                v = text[start:end]\n",
  '                end = min(end, text.find(" ", start) if text.find(" ", start) != -1 else end)\n                v = text[start:end]\n'),
 ("m137", "plural exception widened to credential nouns", EV, '_PLURAL_EXCEPT = frozenset("pass|pin|seed".split("|"))', '_PLURAL_EXCEPT = frozenset("pass|pin|seed|secret|token|passcode|pwd|otp".split("|"))'),
 ("m138", "readable list admits credential compounds", EV, '"autocode|catchphrase|', '"masterkey|pincode|vpnkey|doorcode|autocode|catchphrase|'),
 ("m139", "readable list emptied", EV, "    if low in _READABLE_GLUED or any(b in _READABLE_GLUED for b in _plurals(low)) or low in _ID_WORDS:", "    if low in _ID_WORDS:"),
 ("m140", "misspelt subsequence rule widened", EV, 'p[0] == "p" and p[-1] == "d" and "w" in p', 'p[0] == "p"'),
 ("m141", "function words removed from the state words", EV, '"for from in on at by via with without and or but my your our their his her"', '""'),
 ("m142", "joined weak glue off", EV, "        if (len(parts) > 1 and last in _WEAK_GLUE and", "        if (False and"),
 ("m157", "split name not read as one", EV, "            if len(parts) > 1 and _noun_of(parts[-1]) is None and _noun_of(parts[-2] + parts[-1]) is not None:", "            if False:"),
 # DEF-3
 ("m143", "peer slug of any case", EV, '_PEER_SLUG = r"[a-z]{1,3}\\d{2,5}(?:[a-z]{1,2}\\d{0,2}){0,3}"', '_PEER_SLUG = r"[A-Za-z0-9]{1,16}"'),
 ("m144", "peer slug length unbounded", EV, '(name == "peer" and len(slug) > _PEER_SLUG_MAX)', "False"),
 ("m145", "prd slug of any characters", EV, r'prd-(?P<slug>[a-z]+(?:-[a-z]+){0,%d})', r'prd-(?P<slug>[A-Za-z0-9]+(?:-[A-Za-z0-9]+){0,%d})'),
 ("m146", "prd slug letters unbounded", EV, '(name == "prd" and len(slug.replace("-", "")) > _PRD_SLUG_LETTERS)', "False"),
 ("m147", "inner unit template widened", EV, r'"inner": re.compile(r"wm-build-inner\d{1,%d}-[a-z]\.service" % _INNER_DIGITS)', r'"inner": re.compile(r"wm-build-inner\w{1,%d}-\w+\.service" % (_INNER_DIGITS * 4))'),
 ("m148", "templates in every field", EV, '    for name in prof["exact"]:', "    for name in _TEMPLATES:"),
 ("m149", "template credential-word check dropped", EV, '        if (not _cred_marked([x for x in _SPLIT.split(s) if x]) and not any(_cred_name(w) for w in slug.split("-") if w)\n                and redact_credentials(s) == s):', "        if True:"),
 ("m150", "fleet word dropped from the vocabulary", EV, '"dotfiles ledger follow prio"', '"ledger follow prio"'),
 ("m151", "priority-level template off", EV, "    if _PRIO.fullmatch(low):", "    if False:"),
 ("m152", "priority-level template widened", EV, '_PRIO = re.compile(r"(?:p\\d){1,4}")', '_PRIO = re.compile(r"(?:p\\d){1,40}")'),
 ("m153", "user slot of the prd template widened", EV, "_PRD_USER_MAX = 4", "_PRD_USER_MAX = 16"),
 # DEF-4
 ("m154", "documented fraction bound differs", SK, "a timestamp's fraction of at most 9 digits", "a timestamp's fraction of at most 12 digits"),
 ("m155", "date cap differs from the doc", EV, "_MAX_DATES = 2", "_MAX_DATES = 3"),
 ("m156", "doc names gettempdir", SK, "(read from `os.environ`, so", "(read from `tempfile.gettempdir()` and `os.environ`, so"),
]
M = mutants13.M + N
MODS = [a for a in sys.argv[1:] if not a.startswith("--")] or ["test_review_fixes10", "test_review_fixes11", "test_review_fixes12",
                                                                 "test_review_fixes13", "test_review_fixes14"]

if __name__ == "__main__":
    sys.exit(base.main(M, MODS))
