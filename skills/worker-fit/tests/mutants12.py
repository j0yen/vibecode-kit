"""Mutation check, repair 12: every mutant of mutants11.py (anchors kept current) plus mutants of the repair-12 code: the closed
numeric names and their digit caps, the credential-noun prose layer, the per-field grammars (effort enum, name words, task slug,
repo owner, session and unit literals), the vocabulary-word cap, the head grammar, the schema-field name rule, the IPv6 and host
rules, the keyed opaque ref, the JSON / MIME / percent-escape rules of the free-text gate, the dotted-flag, `:=` and `bearer is`
forms. Each mutant applies ONE source change to a COPY of the skill and runs the named test modules; caught = the run goes red.
EXIT STATUS: 0 only when every mutant is caught; a survivor or NOT-APPLIED mutant exits 1, a red baseline exits 2.
usage: python3 tests/mutants12.py [test_module ...]   (not collected by unittest discovery)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv, _argv = [sys.argv[0]], sys.argv
import mutants11 as base
sys.argv = _argv
EV = base.EV
N = [
 ("m60", "vocabulary word cap removed from the check", EV, '(profile is None or st["vocab"] <= _MAX_VOCAB_WORDS)', "True"),
 ("m61", "vocabulary word cap raised", EV, "_MAX_VOCAB_WORDS = 6", "_MAX_VOCAB_WORDS = 600"),
 ("m62", "structure words always free", EV, 'if low in _STRUCT_WORDS and st["free_struct"]:\n        st["struct"] += 1\n        return', "if low in _STRUCT_WORDS:\n        return"),
 ("m63", "numeric names: any qualifier", EV, "return all(t in _NUMERIC_QUALIFIERS or t in _NUMERIC_NAMES for t in toks[:-1])", "return True"),
 ("m64", "numeric names: qualifier count unbounded", EV, "_MAX_QUALIFIERS = 3", "_MAX_QUALIFIERS = 300"),
 ("m65", "numeric digit cap off", EV, "return 10 if last in _NUMERIC_WIDE else _NUMERIC_SHORT", "return 10"),
 ("m66", "prose credential nouns reduced to one", EV, "if (_noun_of(parts[-1]) is not None) if glued else parts[-1].lower() in _CRED_NOUNS:", 'if parts[-1].lower() in ("password",):'),
 ("m67", "prose noun chain off", EV, "if _cred_noun(v, glued=False) and v.isalpha():", "if False:"),
 ("m68", "prose name chain length zero", EV, "_MAX_NAME_CHAIN = 4", "_MAX_NAME_CHAIN = 0"),
 ("m69", "effort enum off", EV, 'if prof["enum"] is not None:', "if False:"),
 ("m70", "slug template in every field (was: name word budget, removed in repair 13)", EV, '"slug_ok": prof["slug"],', '"slug_ok": True,'),
 ("m71", "slug template loosened (was: name letter budget, removed in repair 13)", EV, '_SLUG = re.compile(r"[a-z]{1,3}\\d{2,5}', '_SLUG = re.compile(r"[a-z0-9]{2,10}|[a-z]{1,3}\\d{2,5}'),
 ("m72", "name shape re-admitted: a 6-12 letter word with a vowel is a name piece (repair 13)", EV, 'if st["slug_ok"] and not _cred_name(low) and _slug(low):', 'if st["slug_ok"] and not _cred_name(low) and (_slug(low) or (seg.isalpha() and 6 <= len(seg) <= 12 and any(c in "aeiouy" for c in low))):'),
 ("m73", "slug count unbounded", EV, 'and st["slugs"] <= 1', "and True"),
 ("m90", "weak nouns hide nothing plain", EV, "if not (_benign_value(v, \"\", True) or (not strong and _plain_word(v))):", "if False:"),
 ("m91", "bare weak noun is strong", EV, "strong = _strong_name(m.group(0)) or _qualified_before(text, m.start())", "strong = True"),
 ("m92", "explicit separator not skipped", EV, "if _EXPLICIT_SEP.match(t.group(\"mid\")):", "if False:"),
 ("m74", "slug beside an id (was: name words beside an id)", EV, '\n                                                              or st["slugs"])))', ")))"),
 ("m75", "repo owner gets the full budget", EV, 'or st["cost"] > _MAX_SHORT:', 'or st["cost"] > 999:'),
 ("m76", "head may be any digit run", EV, "return s if not s.isdigit() or len(s) in _ABBREV_LENS or s in _NULL_OIDS else None", "return s"),
 ("m77", "field name suffix rule restored", EV, 'if not all(re.sub(r"\\[\\d+\\]$", "", p).lower() in keys for p in parts[:-1]):', "if False:"),
 ("m78", "ipv6 wide groups unbounded", EV, "if len(wide) > _MAX_IPV6_WIDE:", "if False:"),
 ("m79", "host with colons unchecked", EV, 'if named and prof["ip"] and s.count(":") >= 2:', "if False:"),
 ("m80", "opaque ref key constant", EV, "mac = hmac.digest(_OPQ_KEY, ", 'mac = hmac.digest(b"k", '),
 ("m81", "session literal off", EV, 'if low in st["literals"]:', "if False:"),
 ("m82", "json data always benign", EV, "return _benign_json(json.loads(text), name, depth)", "return bool(json.loads(text)) or True"),
 ("m83", "dotted flag is not a flag", EV, "(?P<flag>--?[A-Za-z][\\w.-]{0,60})", "(?P<flag>--?[A-Za-z][\\w-]{0,60})"),
 ("m84", "walrus is not a separator", EV, '_SEP = r"(?:=>|->|:=|==|', '_SEP = r"(?:=>|->|'),
 ("m85", "bearer filler words", EV, '(?:\\s+(?:is|are|was|were|set|to|equals|of))*(?:\\s*" + _SEP', '(?:\\s*" + _SEP'),
 ("m86", "percent-escaped value read raw", EV, "return _benign_value(dv, name)  # a percent-escaped value is read as what it decodes to", "pass"),
 ("m87", "model context tag anywhere", EV, 'if prof["ctx"]:', "if True:"),
 ("m88", "slash profile off", EV, 'if prof["slash"] and len(vals) == 1', "if False and len(vals) == 1"),
 ("m89", "units may carry any literal", EV, 'literals=("spawn",)),\n    "child"', 'literals=("spawn", "x")),\n    "child"'),
]
# m89 changes nothing observable: drop it (kept out of the table so every listed mutant is a real behaviour change)
N = [m for m in N if m[0] != "m89"]
M = base.M + N
MODS = [a for a in sys.argv[1:] if not a.startswith("--")] or ["test_review_fixes10", "test_review_fixes11", "test_review_fixes12"]

if __name__ == "__main__":
    sys.exit(base.main(M, MODS))
