"""Mutation check, repair 13: every mutant of mutants12.py (anchors kept current; m70-m74/m76 re-pointed because the name-word
class and the head letter rule were removed) plus mutants of the repair-13 code: the closed vocabulary (a dictionary word added),
the glued credential nouns of the prose layer and their English words, the weak nouns `unlock`/`vault`, the tempfile name
template (prefix required, random part lower-case, prefix still checked), and the head template (abbreviated lengths, null id).
m72 re-admits a name SHAPE and m109 a dictionary word: neither can break a positive (they only widen), so a catch is by a
negative test. Each mutant applies ONE source change to a COPY of the skill and runs the named test modules; caught = red.
EXIT STATUS: 0 only when every mutant is caught; a survivor or NOT-APPLIED mutant exits 1, a red baseline exits 2.
usage: python3 tests/mutants13.py [test_module ...]   (not collected by unittest discovery)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.argv, _argv = [sys.argv[0]], sys.argv
import mutants11 as base
import mutants12
sys.argv = _argv
EV = base.EV
N = [
 ("m100", "glued credential nouns off", EV, "if low.endswith(n) and 1 <= len(low) - len(n) <= _MAX_GLUE_QUALIFIER:", "if False:"),
 ("m101", "English words ending in a noun are names", EV, "if not low.isalpha() or low in _GLUE_ENGLISH:", "if not low.isalpha():"),
 ("m102", "glued qualifier of one letter not allowed", EV, "1 <= len(low) - len(n) <= _MAX_GLUE_QUALIFIER", "3 <= len(low) - len(n) <= _MAX_GLUE_QUALIFIER"),
 ("m103", "unlock and vault are not nouns", EV, '"key|keys|auth|bearer|code|codes|phrase|unlock|vault"', '"key|keys|auth|bearer|code|codes|phrase"'),
 ("m104", "temp template without a prefix", EV, "if 9 <= len(comp) <= 96 and _TEMP_RAND.fullmatch(comp[-8:]):", "if 8 <= len(comp) <= 96 and _TEMP_RAND.fullmatch(comp[-8:]):"),
 ("m105", "temp random part of any case", EV, '_TEMP_RAND = re.compile(r"[a-z0-9_]{8}")', '_TEMP_RAND = re.compile(r"[A-Za-z0-9_]{8}")'),
 ("m106", "temp prefix not checked", EV, "return root + comp[:-8] + sep + rest", "return root + sep + rest"),
 ("m107", "temp template off (keyish)", EV, "    v = _temp_name(v) or v\n", "\n"),
 ("m108", "temp template off (run rule)", EV, 're.split(r"[-_./+=]+", _temp_name(core) or core))', 're.split(r"[-_./+=]+", core))'),
 ("m109", "a dictionary word added to the closed vocabulary", EV, '"decide regrade agorabus', '"sunshine dragonfly lantern velvet decide regrade agorabus'),
 ("m110", "head: any 40/64-digit run is a null id", EV, "or s in _NULL_OIDS else None", "or len(s) in (40, 64) else None"),
 ("m111", "head: abbreviated lengths widened", EV, "_ABBREV_LENS = range(7, 13)", "_ABBREV_LENS = range(7, 65)"),
 ("m112", "head: abbreviated digits refused (old rule)", EV, "return s if not s.isdigit() or len(s) in _ABBREV_LENS or s in _NULL_OIDS else None",
  "return s if not s.isdigit() else None"),
 ("m113", "a fleet word dropped from the vocabulary", EV, '"decide regrade agorabus reap memlog witness', '"decide agorabus reap memlog witness'),
 ("m115", "a glued word after a name chains into the name", EV, "if _cred_noun(v, glued=False) and v.isalpha():", "if _cred_noun(v) and v.isalpha():"),
 ("m114", "Title-case words trusted as names", EV, 'if st["slug_ok"] and not _cred_name(low) and _slug(low):', 'if st["slug_ok"] and not _cred_name(low) and (_slug(low) or (seg.istitle() and seg.isalpha() and len(seg) >= 6)):'),
]
M = mutants12.M + N
MODS = [a for a in sys.argv[1:] if not a.startswith("--")] or ["test_review_fixes10", "test_review_fixes11", "test_review_fixes12",
                                                                 "test_review_fixes13"]

if __name__ == "__main__":
    sys.exit(base.main(M, MODS))
