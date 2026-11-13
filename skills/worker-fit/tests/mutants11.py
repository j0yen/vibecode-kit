"""Mutation check of the trust gate and the field profiles (re-reviews 9 and 10): each mutant applies ONE source change to a COPY
of the skill in a temp directory and runs the named test modules against it; a mutant is caught when the run goes red.
m1..m36 are the earlier mutants (digit bound, DNS exemption, adapter raw, pair gate off, composites off, letters bound, strict
piece, pair loop, unredacted usage lines, each bound of the gate) with their anchors moved to the field-profile code; m40..
are changes to the profile table, the templates, the free-text numeric and passphrase bounds and the unit-name rule.
EXIT STATUS: 0 only when every mutant is caught; any survivor or NOT-APPLIED mutant (its anchor no longer in the source) exits 1,
and a red baseline exits 2. Every result line is printed before the status.
usage: python3 tests/mutants11.py [test_module ...]   |   python3 tests/mutants11.py --selftest survivor|not-applied|caught
(not collected by unittest discovery)"""
import os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EV, QA, RC = "scripts/envelope_validate.py", "scripts/queue_adapter.py", "scripts/recommend.py"
M = [
 ("m1", "digit piece bound removed", EV, "_MAX_DIGIT_PIECE = 7 ", "_MAX_DIGIT_PIECE = 700 "),
 ("m2", "DNS exempt from the gate", EV, 'not _trusted_pieces(core, max_ids=2 if kind == "path" else 1, profile=prof):', 'not (_trusted_pieces(core, max_ids=2 if kind == "path" else 1, profile=prof) or (kind == "host" and _dns_host(v))):'),
 ("m3", "adapter prints raw", QA, "return ev.show_row(label, v, words)", "return str(v)"),
 ("m4", "pair gate always benign", EV, "def _benign_value(raw, name=\"\", cred_context=False):", "def _benign_value(raw, name=\"\", cred_context=False):\n    return True"),
 ("m5", "composites off", EV, "def _redact_composites(text):", "def _redact_composites(text):\n    return text"),
 ("m6", "short piece bound removed", EV, "_MAX_SHORT = 5 ", "_MAX_SHORT = 500 "),
 ("m6b", "unlisted budget removed", EV, "_MAX_UNLISTED = 8 ", "_MAX_UNLISTED = 800 "),
 ("m7", "row gate bypassed", EV, "and _gate_values(toks, words, 0, _NO_PROFILE)):", "):"),
 ("m8", "pair loop disabled", EV, 'if text.startswith(REDACTED, e) or text.startswith("\\ue002", e):', "if True:"),
 ("m9", "recommend usage unredacted", RC, 'ev.emit(ev.redact_tool("UNREADABLE usage: %s" % msg))', 'ev.emit("UNREADABLE usage: %s" % msg)'),
 ("m9b", "adapter usage unredacted", QA, 'ev.emit(ev.redact_tool("UNREADABLE usage: %s" % msg))', 'ev.emit("UNREADABLE usage: %s" % msg)'),
 ("m9c", "recommend UNREADABLE unredacted", RC, 'ev.emit(ev.redact_tool("UNREADABLE %s: %s" % (path, e)))', 'ev.emit("UNREADABLE %s: %s" % (path, e))'),
 ("m10", "credential prose layer off", EV, "def _redact_cred_prose(text):", "def _redact_cred_prose(text):\n    return text"),
 ("m11", "id count unbounded", EV, 'and st["ids"] <= max_ids and', "and True and"),
 ("m12", "digit total unbounded", EV, 'st["digits"] <= _MAX_DIGITS_TOTAL', "True"),
 ("m13", "unlisted budget off in the check", EV, 'st["cost"] <= max_cost and', "True and"),
 ("m14", "free number bound removed", EV, "limit = _numeric_digits(name) or _FREE_DIGITS", "limit = _numeric_digits(name) or 99"),
 ("m15", "every name numeric", EV, "limit = _numeric_digits(name) or _FREE_DIGITS", "limit = 10"),
 ("m16", "rows may carry ids", EV, "and _gate_values(toks, words, 0, _NO_PROFILE)):", "and _gate_values(toks, words, 9, _ANY_PROFILE)):"),
 ("m17", "unlisted beside an id", EV, "_MAX_UNLISTED_WITH_ID = 0 ", "_MAX_UNLISTED_WITH_ID = 99 "),
 ("m19", "prose next-word vocabulary off", EV, "    if cred_context:  #", "    if False:  #"),
 ("m20", "digits-only counts as a hex id", EV, "[0-9a-fA-F]+\", seg)) and any(c.isdigit() for c in seg) and any(c.isalpha() for c in seg)", "[0-9a-fA-F]+\", seg)) and any(c.isdigit() for c in seg)"),
 ("m21", "ipv6 group bound removed", EV, "_MAX_IPV6_GROUPS = 4 ", "_MAX_IPV6_GROUPS = 8 "),
 ("m22", "path ids unbounded", EV, 'max_ids=2 if kind == "path" else 1, profile', "max_ids=9, profile"),
 ("m23", "vocabulary compound word count unbounded", EV, "best[-1] <= 4 else 0", "best[-1] <= 40 else 0"),
 ("m24", "row credential layer off", EV, "redact_credentials(t) == t and not _cred_marked([x for x in _SPLIT.split(t) if x]) for t in toks)", "True for t in toks)"),
 ("m26", "unlisted token per compound unbounded", EV, "    if unl > 1:", "    if False:"),
 ("m27", "random hex (7+) any length", EV, "_HEX_LENS = frozenset(list(range(7, 13)) + [32, 40, 64])", "_HEX_LENS = frozenset(range(7, 90))"),
 ("m28", "name=value chunks unbounded", EV, "    if len(chunks) > 3:", "    if False:"),
 ("m29", "free unlisted budget off", EV, "    return cost <= _FREE_UNLISTED and pieces <= _FREE_PIECES", "    return True"),
 ("m30", "free short piece bound", EV, "_FREE_SHORT = 3", "_FREE_SHORT = 30"),
 ("m31", "hex head name bypass", EV, "return bool(re.fullmatch(r\"[0-9a-fA-F]{4,64}\", core)) and not core.isdigit()", "return True"),
 ("m32", "piece count bound removed", EV, "_MAX_PIECES = 40", "_MAX_PIECES = 4000"),
 ("m33", "one-letter id prefix", EV, "if (k >= 2 or seg[0] == \"r\") and", "if True and"),
 ("m34", "ids beside unlisted or digits", EV, 'and not (st["ids"] and (st["cost"] > _MAX_UNLISTED_WITH_ID or st["digits"] > _MAX_DIGITS_WITH_ID\n                                                              or st["lang"])))', ')'),
 ("m35", "single letter between numbers free anywhere", EV, "if len(seg) == 1 and seg.isalpha() and any(c.isdigit() for c in prev) and any(c.isdigit() for c in nxt):", "if len(seg) == 1 and seg.isalpha():"),
 ("m36", "uuid not counted", EV, 'st["ids"] += len(st["found"])', "pass"),
 ("m40", "profile argument ignored", EV, "    prof = profile or _ANY_PROFILE", "    prof = _ANY_PROFILE"),
 ("m41", "label ignored: every field the bare gate", EV, "    return _PROFILES.get(_PROFILE_ALIAS.get(low, low), _NO_PROFILE)", "    return _ANY_PROFILE"),
 ("m42", "unknown label permissive", EV, "    return _PROFILES.get(_PROFILE_ALIAS.get(low, low), _NO_PROFILE)", "    return _PROFILES.get(_PROFILE_ALIAS.get(low, low), _ANY_PROFILE)"),
 ("m43", "templates not enforced", EV, 'if shape not in prof["beside"] or (rx is not None and not rx.fullmatch(whole.replace(text, "~", 1))):', 'if shape not in prof["beside"]:'),
 ("m44", "alone shapes not enforced", EV, '                if shape not in prof["alone"]:\n                    return False', '                if False:\n                    return False'),
 ("m45", "digits beside an id unbounded", EV, "_MAX_DIGITS_WITH_ID = 8 ", "_MAX_DIGITS_WITH_ID = 800 "),
 ("m46", "free small-number bound raised", EV, "_FREE_DIGITS = 2 ", "_FREE_DIGITS = 9 "),
 ("m47", "free unlisted budget raised", EV, "_FREE_UNLISTED = 4 ", "_FREE_UNLISTED = 40 "),
 ("m48", "free passphrase run unbounded", EV, "_FREE_WORD_RUN = 3 ", "_FREE_WORD_RUN = 30 "),
 ("m49", "free unlisted piece count unbounded", EV, "_FREE_PIECES = 2 ", "_FREE_PIECES = 20 "),
 ("m50", "unit-name credential word anywhere", EV, "    if len(named) != 1 or not _UNIT_END.fullmatch(whole.strip()):", "    if len(named) != 1:"),
 ("m51", "full ipv6 literal unbounded", EV, "return n == 8 and nonzero <= _MAX_IPV6_GROUPS", "return n == 8"),
 ("m52", "vocabulary word + suffix unbounded", EV, "0 < len(low) - len(w) <= _MAX_SHORT", "0 < len(low) - len(w)"),
 ("m53", "port mapping under any name", EV, "and name.lower().lstrip(\"-\") in _PORT_NAMES:", "and True:"),
 ("m54", "digit after a vocabulary word unbounded", EV, "len(x) > (_MAX_DIGIT_PIECE if was_word else limit)", "len(x) > 700"),
 ("m55", "numeric pair names open", EV, "toks[-2] + \"_\" + last in _NUMERIC_PAIRS", "True"),
]
MODS = [a for a in sys.argv[1:] if not a.startswith("--")] or ["test_review_fixes10", "test_review_fixes11"]


def run(m, mods, tmp):
    mid, desc, f, old, new = m
    d = "%s/mt_%s" % (tmp, mid)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(SRC, d + "/wf", ignore=shutil.ignore_patterns("__pycache__"))
    p = d + "/wf/" + f
    s = open(p).read()
    if old not in s:
        return mid, desc, "NOT-APPLIED"
    open(p, "w").write(s.replace(old, new, 1))
    r = subprocess.run([sys.executable, "-m", "unittest"] + mods, cwd=d + "/wf/tests", capture_output=True, text=True, timeout=1800)
    tail = (r.stderr.strip().splitlines() or [""])[-1]
    return mid, desc, ("SURVIVED" if r.returncode == 0 else "caught") + " " + tail[:60]


def main(mutants, mods):
    tmp = tempfile.mkdtemp(prefix="wfit-mut-")
    try:
        base = subprocess.run([sys.executable, "-m", "unittest"] + mods, cwd=SRC + "/tests", capture_output=True, text=True)
        if base.returncode != 0:
            print("BASELINE RED: " + base.stderr[-300:])
            return 2
        with ThreadPoolExecutor(8) as ex:
            res = list(ex.map(lambda m: run(m, mods, tmp), mutants))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    c = sum(1 for r in res if r[2].startswith("caught"))
    for r in res:
        print("%-5s %-45s %s" % r)
    print("MUTANTS %s caught %d/%d" % (" ".join(mods), c, len(res)))
    return 0 if c == len(res) else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        mode = sys.argv[sys.argv.index("--selftest") + 1]
        probe_old = 'UNKNOWN = "UNKNOWN"'
        mut = {"survivor": ("t1", "no-op change", EV, probe_old, probe_old),
               "not-applied": ("t2", "missing anchor", EV, "THIS TEXT IS NOT IN THE SOURCE", "x"),
               "caught": ("t3", "constant changed", EV, probe_old, 'UNKNOWN = "NOT-UNKNOWN"')}[mode]
        sys.exit(main([mut], ["test_validate"]))
    sys.exit(main(M, MODS))
