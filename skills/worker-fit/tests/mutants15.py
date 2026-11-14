"""Mutation check, repair 15: every mutant of mutants14.py (anchors kept current: m2, m34 in mutants11.py, m72, m74, m81, m83 in
mutants12.py, m114 in mutants13.py and m150, m151 in mutants14.py re-pointed because the context-tag charge, the bit budget, the
canonical case rule, the leet flag characters and the PRD words moved those lines) plus mutants of the repair-15 code, at least one
per defect of re-review 14: DEF-A the label decoration, the bracketed group, the format-character view, the prose decoration, the
spaced dash and the prose layer of redact_tool each off; DEF-B the placeholder branch raw again (identity, row) and the placeholder set opened; DEF-C the sentinel
accepted from input, a fixed sentinel, any ref-shaped text passed through, input marker characters kept; DEF-D the ASCII flag dropped
from the templates and the ISO gate, non-ASCII digits not refused, case not canonical, the model tag not charged, the bit budget off,
the joiner choice not charged, a free tail in every field; DEF-E the PRD slot a whole-value template again, the frame printing its
slug; DEF-F each new rule form dropped (@/$ leet, trailing leet, edits, English exclusion, abbreviations, non-English words, value
tails, weak-after-strong, whole-name join), a quote pair dropped, typographic quotes off in the pair layers; DEF-G the owner list off;
DEF-H a documented bound changed; the reviewer equal to the worker's unit accepted; the runner counting an import-breaking mutant.
Each mutant applies ONE source change to a COPY of the skill and runs the named test modules; caught = red; a mutant whose scripts do
not import is NOT-APPLIED. EXIT STATUS: 0 only when every mutant is caught; a survivor or NOT-APPLIED mutant exits 1, a red baseline 2.
usage: python3 tests/mutants15.py [test_module ...]   (not collected by unittest discovery)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv, _argv = [sys.argv[0]], sys.argv
import mutants11 as base
import mutants14
sys.argv = _argv
EV, RC = base.EV, base.RC
SK = "SKILL.md"
RUNNER = "tests/mutants11.py"
N = [
 # DEF-A
 ("m160", "label decoration not skipped", EV, "        if used < _LABEL_DECOR and _decor(c):", "        if False:"),
 ("m161", "bracketed label group not read", EV, "    if k > floor and text[k - 1] in _GROUP_OPEN:", "    if False:"),
 ("m162", "format-character view off", EV, "    for dec in (_unescape, _pct_decode, _drop_format):", "    for dec in (_unescape, _pct_decode):"),
 ("m163", "prose label decoration off", EV, r"""@$]{0,4}(?:\s+(?:is|are""", r"""@$]{0,0}(?:\s+(?:is|are"""),
 ("m164", "spaced dash separator off", EV, r"""(?:\s*[:=]+\s*|\s+[-\u2013\u2014]{1,2}\s+|\s+)""", r"""(?:\s*[:=]+\s*|\s+)"""),
 # DEF-B
 ("m165", "placeholder branch raw again (identity)", EV, "        return _placeholder_out(v)\n    k = keep(kind, v, label)", "        return v\n    k = keep(kind, v, label)"),
 ("m166", "placeholder branch raw again (row)", EV, "        return _placeholder_out(v)  # canonical", "        return v  # canonical"),
 ("m167", "placeholder set opened", EV, "    return v if v.lower() in PLACEHOLDERS and _canon(v) else UNKNOWN", "    return v"),
 # DEF-C
 ("m168", "sentinel accepted from input", EV, "if not isinstance(s, str) or not s or len(s) > 512 or _forgeable(s):", "if not isinstance(s, str) or not s or len(s) > 512:"),
 ("m169", "fixed sentinel", EV, '_CHARGED = "\\ue004" + os.urandom(8).hex() + "\\ue005"', '_CHARGED = "\\ue010"'),
 ("m170", "any ref-shaped text passes through", EV, "    return isinstance(v, str) and v in _MINTED", "    return isinstance(v, str) and bool(_OPQ_REF.fullmatch(v))"),
 ("m171", "input marker characters kept", EV, "    return _STRAY_RX.sub(", "    return text if True else _STRAY_RX.sub("),
 # DEF-D
 ("m172", "templates match any Unicode digit", EV, "_TEMPLATES = {k: re.compile(v.pattern, (v.flags & ~re.UNICODE) | re.ASCII) for k, v in _TEMPLATES.items()}", ""),
 ("m173", "ISO gate matches any Unicode digit", EV, '(?![0-9A-Za-z])" % _MAX_FRACTION, re.ASCII)', '(?![0-9A-Za-z])" % _MAX_FRACTION)'),
 ("m174", "non-ASCII digits not refused", EV, '(c.isdigit() and not c.isascii()) for c in s)', 'False for c in s)'),
 ("m175", "case not canonical", EV, "    return seg == seg.lower() or seg == seg.upper() or seg == seg[:1].upper() + seg[1:].lower() or seg in _CASED_WORDS", "    return True"),
 ("m176", "model tag digits not charged", EV, "core, tag = v[:m.start()], len(m.group(1))", "core, tag = v[:m.start()], 0"),
 ("m177", "bit budget off", EV, '            and (profile is None or _value_bits(st) <= (_MAX_PATH_BITS if prof["free_struct"] else _MAX_VALUE_BITS)))', ")"),
 ("m178", "joiner choice not charged", EV, '        st["joins"] += run[0] in _FREE_JOINERS', "        pass"),
 ("m179", "free tail in every field", EV, '"tail_ok": profile is None or prof["tail"]}', '"tail_ok": True}'),
 # DEF-E
 ("m180", "PRD slot a whole-value template again", EV, "        if name in _FRAMES:\n            continue", "        if False:\n            continue"),
 ("m181", "frame prints its slug", EV, 'opaque("prd-slug", m.group("slug"))', 'm.group("slug")'),
 # DEF-F
 ("m182", "@ and $ not leet letters", EV, '_LEET_RUN = re.compile(r"(?<=[A-Za-z])[0-9@$]+(?=[A-Za-z])")', '_LEET_RUN = re.compile(r"(?<=[A-Za-z])[013457]+(?=[A-Za-z])")'),
 ("m183", "trailing leet off", EV, '_LEET_TAIL = re.compile(r"(?<=[A-Za-z])[0-9@$]+$")', '_LEET_TAIL = re.compile(r"(?!)")'),
 ("m184", "edits from the closed stems off", EV, "and any(_edits(low, w, 1 if len(w) < 8 else 2) for w in _EDIT_STEMS))", "and False)"),
 ("m185", "English exclusion of the edits off", EV, "(len(low) >= 4 and low not in _EDIT_ENGLISH and", "(len(low) >= 4 and"),
 ("m186", "abbreviation set emptied", EV, '_CRED_ABBREV = frozenset("psw|pss|tok|tkn|skey|privk|prvk|pinno|pinnum|apitok|authtok|acctok|sesstok|rtok|atok|scrt".split("|"))', "_CRED_ABBREV = frozenset()"),
 ("m187", "non-English set emptied", EV, '"parol|parola|wachtwoord|salasana|lozinka|adgangskode|passord").split("|"))', '"parol|parola|wachtwoord|salasana|lozinka|adgangskode|passord").split("|")) and frozenset()'),
 ("m188", "value-tail rule off", EV, "            if len(parts) > 1 and parts[-1].lower() in _VALUE_TAILS and", "            if False and"),
 ("m189", "weak noun after a strong part off", EV, "        if n in _WEAK_NOUNS and any(", "        if False and any("),
 ("m190", "whole-name join off", EV, "            if len(parts) > 2 and len(whole) <= 24 and _noun_of(whole) is not None:", "            if False:"),
 ("m191", "a quote pair dropped (guillemets)", EV, '"\\u00ab": "\\u00bb\\u00ab", ', ""),
 ("m192", "typographic quotes off in the pair layers", EV, '""" + _TYPO_QUOTED + r"""|', '""" + r"""(?!)|'),
 ("m193", "a closed abbreviation dropped", EV, '"psw|pss|tok|tkn|', '"psw|pss|tkn|'),
 # DEF-G
 ("m194", "repo owner list off (shared budget)", EV, '        if owner in _REPO_OWNERS:\n            st["vocab"] += 1', '        if False:\n            st["vocab"] += 1'),
 # DEF-H
 ("m195", "documented bit budget differs", SK, "at most 160 bits of non-id material per value", "at most 196 bits of non-id material per value"),
 ("m196", "documented peer capacity differs", SK, "about 104 bits, measured", "about 140 bits, measured"),
 ("m197", "code bit budget differs from the doc", EV, "_MAX_VALUE_BITS = 160", "_MAX_VALUE_BITS = 200"),
 # unconfirmed concerns
 ("m198", "a reviewer equal to the worker's unit is distinct", RC, '("session", "invocation", "account", "child", "unit")', '("session", "invocation", "account", "child")'),
 ("m199", "runner counts an import-breaking mutant as caught", RUNNER, "    if imp.returncode != 0:\n", "    if False:\n"),
 ("m200", "redact_tool skips the prose credential-name layer", EV, "    text = _via_views(text, _redact_cred_prose)  # a bare", "    pass  # a bare"),
]
M = mutants14.M + N
MODS = [a for a in sys.argv[1:] if not a.startswith("--")] or ["test_review_fixes10", "test_review_fixes11", "test_review_fixes12",
                                                                 "test_review_fixes13", "test_review_fixes14", "test_review_fixes15"]

if __name__ == "__main__":
    sys.exit(base.main(M, MODS))
