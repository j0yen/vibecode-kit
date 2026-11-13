"""Mutation check of the trust gate (re-review 9 DEF-5): each mutant applies ONE source change to a COPY of the skill in a temp
directory and runs the named test module (default test_review_fixes10) against it; a mutant is caught when the run goes red.
m1..m9c are the reviewer's mutants (digit bound, DNS exemption, adapter raw, pair gate off, composites off, letters bound,
strict piece, pair loop, unredacted usage lines) mapped onto the closed gate; m10.. are further changes to each bound.
usage: python3 tests/mutants10.py [test_module]   (not collected by unittest discovery)"""
import os, shutil, subprocess, sys, tempfile
from concurrent.futures import ThreadPoolExecutor
SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TMP = tempfile.mkdtemp(prefix="wfit-mut-")
MOD = sys.argv[1] if len(sys.argv) > 1 else "test_review_fixes10"
EV, QA, RC = "scripts/envelope_validate.py", "scripts/queue_adapter.py", "scripts/recommend.py"
M = [
 ("m1", "digit piece bound removed", EV, "_MAX_DIGIT_PIECE = 7 ", "_MAX_DIGIT_PIECE = 700 "),
 ("m2", "DNS exempt from the gate", EV, 'if kind != "sha" and ok == v and not _trusted_pieces(v, max_ids=2 if kind == "path" else 1):', 'if kind != "sha" and ok == v and not (_trusted_pieces(v, max_ids=2 if kind == "path" else 1) or (kind == "host" and _dns_host(v))):'),
 ("m3", "adapter prints raw", QA, "return ev.show_row(label, v, words)", "return str(v)"),
 ("m4", "pair gate always benign", EV, "def _benign_value(raw, name=\"\", cred_context=False):", "def _benign_value(raw, name=\"\", cred_context=False):\n    return True"),
 ("m5", "composites off", EV, "def _redact_composites(text):", "def _redact_composites(text):\n    return text"),
 ("m6", "short piece bound removed", EV, "_MAX_SHORT = 5 ", "_MAX_SHORT = 500 "),
 ("m6b", "unlisted budget removed", EV, "_MAX_UNLISTED = 8 ", "_MAX_UNLISTED = 800 "),
 ("m7", "row gate bypassed", EV, "and _gate_values(toks, words, 0)):", "):"),
 ("m8", "pair loop disabled", EV, 'if text.startswith(REDACTED, e) or text.startswith("\\ue002", e):', "if True:"),
 ("m9", "recommend usage unredacted", RC, 'ev.emit(ev.redact_tool("UNREADABLE usage: %s" % msg))', 'ev.emit("UNREADABLE usage: %s" % msg)'),
 ("m9b", "adapter usage unredacted", QA, 'ev.emit(ev.redact_tool("UNREADABLE usage: %s" % msg))', 'ev.emit("UNREADABLE usage: %s" % msg)'),
 ("m9c", "recommend UNREADABLE unredacted", RC, 'ev.emit(ev.redact_tool("UNREADABLE %s: %s" % (path, e)))', 'ev.emit("UNREADABLE %s: %s" % (path, e))'),
 ("m10", "credential prose layer off", EV, "def _redact_cred_prose(text):", "def _redact_cred_prose(text):\n    return text"),
 ("m11", "id count unbounded", EV, 'and st["ids"] <= max_ids and', "and True and"),
 ("m12", "digit total unbounded", EV, 'st["digits"] <= _MAX_DIGITS_TOTAL', "True"),
 ("m13", "unlisted budget off in the check", EV, 'st["cost"] <= _MAX_UNLISTED and', "True and"),
 ("m14", "free number bound removed", EV, "limit = 2 if cred_context else (10 if last in _NUMERIC_NAMES else _FREE_DIGITS)", "limit = 10"),
 ("m15", "every name plain", EV, "elif name.lower() in _PLAIN_VALUE_NAMES and", "elif True and"),
 ("m16", "rows may carry ids", EV, "and _gate_values(toks, words, 0)):", "and _gate_values(toks, words, 9)):"),
 ("m17", "unlisted beside an id", EV, "_MAX_UNLISTED_WITH_ID = 0 ", "_MAX_UNLISTED_WITH_ID = 99 "),
 ("m19", "prose next-word vocabulary off", EV, "    if cred_context:  #", "    if False:  #"),
 ("m20", "digits-only counts as a hex id", EV, "[0-9a-fA-F]+\", seg)) and any(c.isdigit() for c in seg) and any(c.isalpha() for c in seg)", "[0-9a-fA-F]+\", seg)) and any(c.isdigit() for c in seg)"),
 ("m21", "ipv6 group bound removed", EV, "_MAX_IPV6_GROUPS = 4 ", "_MAX_IPV6_GROUPS = 8 "),
 ("m22", "path ids unbounded", EV, 'max_ids=2 if kind == "path" else 1)', "max_ids=9)"),
 ("m23", "vocabulary compound word count unbounded", EV, "best[-1] <= 4 else 0", "best[-1] <= 40 else 0"),
 ("m24", "row credential layer off", EV, "redact_credentials(t) == t and not _cred_marked([x for x in _SPLIT.split(t) if x]) for t in toks)", "True for t in toks)"),
 ("m26", "unlisted token per compound unbounded", EV, "    if unl > 1:", "    if False:"),
 ("m27", "random hex (7+) any length", EV, "_HEX_LENS = frozenset(list(range(7, 13)) + [32, 40, 64])", "_HEX_LENS = frozenset(range(7, 90))"),
 ("m28", "name=value chunks unbounded", EV, "    if len(chunks) > 3:", "    if False:"),
 ("m29", "free unlisted budget off", EV, "    return cost <= _FREE_UNLISTED", "    return True"),
 ("m30", "free short piece bound", EV, "_FREE_SHORT = 3", "_FREE_SHORT = 30"),
 ("m31", "hex head name bypass", EV, "return bool(re.fullmatch(r\"[0-9a-fA-F]{4,64}\", core)) and not core.isdigit()", "return True"),
 ("m33", "one-letter id prefix", EV, "if (k >= 2 or seg[0] == \"r\") and", "if True and"),
 ("m34", "ids beside unlisted", EV, 'and not (st["ids"] and st["cost"] > _MAX_UNLISTED_WITH_ID))', ')'),
 ("m35", "single letter between numbers free anywhere", EV, "if len(seg) == 1 and seg.isalpha() and any(c.isdigit() for c in prev) and any(c.isdigit() for c in nxt):", "if len(seg) == 1 and seg.isalpha():"),
 ("m36", "uuid not counted", EV, 'st["ids"] += len(_UUID.findall(s))', "pass"),
 ("m32", "piece count bound removed", EV, "_MAX_PIECES = 40", "_MAX_PIECES = 4000"),
]
def run(m):
    mid, desc, f, old, new = m
    d = "%s/mt10_%s" % (TMP, mid)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(SRC, d + "/wf", ignore=shutil.ignore_patterns("__pycache__"))
    p = d + "/wf/" + f
    s = open(p).read()
    if old not in s:
        return mid, desc, "NOT-APPLIED"
    open(p, "w").write(s.replace(old, new, 1))
    r = subprocess.run([sys.executable, "-m", "unittest", MOD], cwd=d + "/wf/tests", capture_output=True, text=True, timeout=900)
    tail = (r.stderr.strip().splitlines() or [""])[-1]
    return mid, desc, ("SURVIVED" if r.returncode == 0 else "caught") + " " + tail[:60]
base = subprocess.run([sys.executable, '-m', 'unittest', MOD], cwd=SRC + '/tests', capture_output=True, text=True)
assert base.returncode == 0, 'baseline red: ' + base.stderr[-300:]
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(run, M))
c = sum(1 for r in res if r[2].startswith("caught"))
for r in res: print("%-5s %-45s %s" % r)
print("MUTANTS %s caught %d/%d" % (MOD, c, len(res)))
shutil.rmtree(TMP, ignore_errors=True)
