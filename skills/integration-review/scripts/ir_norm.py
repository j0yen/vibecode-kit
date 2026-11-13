"""Shared text rules for the integration-review scripts (stdlib only, pure functions).

Loaded by path from the sibling scripts (they run under `python3 -I`, which keeps the script directory off
sys.path). is_unknown() is the ONE definition of an UNKNOWN-equivalent: missing or not a string, then after
Unicode NFKC folding, removal of format/control characters (zero-width space, BOM, joiners) and
surrounding whitespace of any kind, lower-casing and removal of trailing/leading punctuation, one of
the placeholders unknown, unk, ?, tbd, -, n/a, na, none, null, nil or empty.
redact() replaces text shaped like a credential (or an e-mail address) by a fixed marker; the original is never kept.
"""
import re
import unicodedata
from functools import lru_cache
from urllib.parse import unquote

PLACEHOLDERS = frozenset({"", "unknown", "unk", "?", "tbd", "-", "--", "n/a", "na", "none", "null", "nil"})
_EDGE = " \t\r\n.,;:!'\"`()[]{}<>*_~|\\/="
# Placeholder family, matched on the compact form (separators removed): see is_unknown().
_FAMILY = frozenset({"", "na", "undefined", "undef", "null", "nil", "none", "notavailable", "notapplicable",
                     "unavailable", "unknown", "unk", "notknown", "unspecified", "notspecified", "notset",
                     "notprovided", "notstated", "tbd", "tba", "todo", "tobedetermined", "tobeannounced"})
# Every slash look-alike (division slash, fraction slash, big solidus, box-drawing diagonal, set minus, reverse
# solidus forms) and the backslash fold to "/" in canon(slashes=True) (the placeholder rule), so "N\u2215A", "n\\a" and "none\u2044" read as n/a, none/.
_SLASHES = "\u2215\u2044\u29f8\u29f9\uff0f\u2571\u27cb\u27cd\u2216\u29f5\u29f7\u3033\u1735\u2e0b\ufe68\uff3c\\\u2572\u27c8\u2afb\u2afd"
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043\u207b\u208b\u2e3a\u2e3b\u058a\u05be\u1806\ufe58\ufe63\uff0d\u30fc"
# E-mail domain: a dotted name whose last label is alphabetic (a version pin such as svc@1.2.3 or pkg@2.0.0-rc.1 is
# not an address), localhost, a bracketed IP literal, or a dotted-quad IPv4.
_OCTET = r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])"
_EMAIL_HOST = (r"[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63}){0,7}\.[A-Za-z]{2,63}(?![A-Za-z0-9])"
               r"|localhost(?![A-Za-z0-9.-])|\[[^\]\s]{2,45}\]|%s(?:\.%s){3}(?![0-9A-Za-z]|\.[0-9A-Za-z])" % (_OCTET, _OCTET))
CRED = re.compile(
    r"(token|secret|passw|bearer|api[_-]?key|sk-ant|sk-[A-Za-z0-9]{8}|sk_(?:live|test)_|rk_(?:live|test)_|-----BEGIN"
    r"|authorization\s*[:=]|://[^/\s]*:[^/\s]*@|://[^/\s@:]*:(?!\d{1,5}/)[^\s@]{0,200}@|\b[a-z][a-z0-9+.-]{0,30}:[^A-Za-z0-9\s@]{0,6}[^/\s@:]{0,100}:[^/\s@]{0,200}@|gh[pousr]_[A-Za-z0-9]|github_pat_|glpat-|npm_[A-Za-z0-9]{8}"
    r"|pypi-[A-Za-z0-9_-]{8}|hf_[A-Za-z0-9]{8}|dop_v1_|shp(?:at|ss|ca|pa)_|SG\.[A-Za-z0-9_-]{8}|ya29\.|"
    r"(?-i:AKIA|ASIA)[A-Za-z0-9]{8}|(?:[A-Za-z0-9._%+-]{1,64}|\"[^\"\r\n]{1,64}\")@(?:" + _EMAIL_HOST + r")|eyJ[A-Za-z0-9_-]{6}|xox[abprs]-|AIza[0-9A-Za-z_-]{8}"
    r"|\b(?:key|auth|pwd|cred\w*)\s*[:=]\s*\S{6})", re.I)
_RUN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
REDACTED = "[credential-shaped text redacted]"

# Negation, one definition for the scripts. NEG_CORE: words that deny or fail a statement ("not verified", "no test",
# "failed", contractions). NEG_STATE adds the process-state words that say a process is not running (an adoption
# observation must not carry one). A word is matched whole, so "notify" or "diesel" never counts.
_NEG_CORE = (r"no|not|none|never|without|nothing|cannot|unable|fail|fails|failed|failing|failure|unverified|unconfirmed|"
             r"untested|nonexistent|absent|missing")
_NEG_STATE = (r"dead|exited|gone|stopped|terminated|killed|inactive|unknown|unk|undefined|null|nil|tbd|unavailable|"
              r"defunct|zombie|esrch|died|dies|crashed|aborted|reaped|unreachable|refused|denied|timeout")
_CONTR = r"\b[a-z]+n['\u2019]t\b|\bcan['\u2019]t\b"
NEG_CORE = re.compile(r"\b(?:%s)\b|%s|\bn\s*/\s*a\b" % (_NEG_CORE, _CONTR))
NEG_STATE = re.compile(r"\b(?:%s|%s)\b|%s|\bn\s*/\s*a\b|\btimed\s+out\b" % (_NEG_CORE, _NEG_STATE, _CONTR))


# NEG_DOUBT (doubt=True): the wordings that say a claim is not established, beyond a plain negation: falsity
# (false, untrue, incorrect, invalid, wrong), refutation (disproved, refuted, rejected, retracted), an open or
# skipped check (pending, skipped, waived, ignored, blocked, cancelled, tbd, todo, "to do"), a dispute, and any un- word that
# ends in -ed/-ied ("unchecked", "unreviewed", "unrun"; "united" and "unified" excepted).
_NEG_DOUBT = (r"false|untrue|incorrect|invalid|wrong|disprove[ds]?|disproven|refuted?|rejected|retracted|revoked|withdrawn|"
              r"doubtful|dubious|unclear|inconclusive|incomplete|pending|skipped|skip|skips|skipping|waived?|ignored|"
              r"blocked|cancell?ed|abandoned|tbd|tba|todo|to\s+do|disputed?|contested|questionable|doubt|doubted|"
              r"unproven|unrun|unseen|unsure|uncertain|undone|unfinished")
NEG_DOUBT = re.compile(r"\b(?:%s)\b|\bun(?!ited\b|ified\b)[a-z]{2,}(?:ed|ied)\b" % _NEG_DOUBT)
# A zero count of a failure word is a positive statement ("0 failed", "zero errors"); a zero count of passes is not
# evidence at all ("0 passed").
_ZERO_FAIL = re.compile(r"(?<![\w.])(?:0+|zero)\s+(?:tests?\s+)?(?:fail\w*|errors?|skipped|skips?|regress\w*|"
                        r"violations?|warnings?|unchecked|pending|missing)\b")
_ZERO_PASS = re.compile(r"(?<![\w.])(?:0+|zero)\s+(?:tests?\s+)?(?:passed|passing|succe\w+|ok)\b")


def negated(text, state=False, doubt=False):
    """True when the text carries a negation word (NEG_CORE; with state=True the process-state words too; with
    doubt=True the NEG_DOUBT wordings and a zero count of passes too). A zero count of failures ("0 failed, 12
    passed") is not a negation."""
    if not isinstance(text, str):
        return False
    t = canon(text, slashes=True).replace("\u2019", "'")
    t = _ZERO_FAIL.sub(" ", t)
    if doubt and (_ZERO_PASS.search(t) or NEG_DOUBT.search(t)):
        return True
    return bool((NEG_STATE if state else NEG_CORE).search(t))


def fold(v):
    """Comparable form of a string: NFKC, no format/control/space characters at the edges, lower case."""
    t = unicodedata.normalize("NFKC", v)
    t = "".join(" " if (c.isspace() or unicodedata.category(c) in ("Zs", "Zl", "Zp")) else c
                for c in t if unicodedata.category(c) not in ("Cf", "Cc") or c.isspace())
    return t.strip().lower()


def canon(v, slashes=False):
    """Placeholder-comparable form: NFKD, combining marks (Mn) and variation selectors removed, format/control
    characters removed, every dash/minus variant folded to "-", case folded, whitespace collapsed. With slashes=True
    every slash look-alike and the backslash fold to "/" too: used for placeholders and negations only, never for
    a path (a look-alike inside /proc/<n>/exe is not that path)."""
    t = unicodedata.normalize("NFKD", v)
    out = []
    for c in t:
        cat = unicodedata.category(c)
        if cat == "Mn" or 0xFE00 <= ord(c) <= 0xFE0F or 0xE0100 <= ord(c) <= 0xE01EF:
            continue
        if cat in ("Cf", "Cc") and not c.isspace():
            continue
        if c in _DASHES or cat == "Pd":
            c = "-"
        elif slashes and c in _SLASHES:
            c = "/"
        out.append(" " if (c.isspace() or cat in ("Zs", "Zl", "Zp")) else c)
    return re.sub(r"\s+", " ", "".join(out)).strip().casefold()


def repo_id(repo):
    """Canonical spelling of a repo identity: URL / scp forms, ".git" and trailing "/" removed, lower case."""
    r = repo.strip().lower()
    r = re.sub(r"^(?:https?|ssh|git)://(?:[^@/]*@)?", "", r)
    r = re.sub(r"^[^@/\s]+@([^:/\s]+):", r"\1/", r)
    return re.sub(r"(?:\.git)?/*$", "", r)


def is_unknown(v):
    """See _is_unknown(): the rule, with the result cached per string (the validator asks it for every field)."""
    return True if not isinstance(v, str) else _is_unknown(v)


@lru_cache(maxsize=65536)
def _is_unknown(v):
    """The ONE UNKNOWN-equivalent rule: not a string; or, after canon() and stripping edge punctuation and "=",
    a value with no letter or digit at all (?, ???, -, --, ..., an ellipsis), or one of the placeholder family
    (unknown unk n/a in any dotting or spacing, undefined, null, nil, none, not available/applicable/known,
    unavailable, unspecified, tbd, tba, todo, empty) once separators (space . / _ -) are removed."""
    if not isinstance(v, str):
        return True
    t = canon(v, slashes=True)
    if t in PLACEHOLDERS:
        return True
    core = t.strip(_EDGE + "?-")
    if not any(c.isalnum() for c in t):
        return True
    return re.sub(r"[\s./_-]+", "", core) in _FAMILY


# ---- commits and non-evidence prose (one definition each, shared by the scripts) -----------------------------
_COMMIT_LABEL = re.compile(r"^(?:sha-?(?:1|256)?|commit(?:\s*id)?|rev(?:ision)?|hash|git|oid)[\s:=#-]+", re.I)


def commit_id(c):
    """Canonical spelling of a commit, or None when the commit is UNSTATED. A value that is not a string or is an
    UNKNOWN-equivalent (is_unknown: UNKNOWN, TBD, n/a, null, empty ...) is unstated, as an unstated repo is. Otherwise
    NFKC folding, removal of format/control characters and surrounding blanks, lower case, a leading label ("sha:",
    "sha1:", "sha256:", "commit ", "rev ", "hash ", "git:" ...) and edge punctuation removed: "sha:<hex>", "commit <hex>"
    and a zero-width-marked hex are the same commit as the bare hex."""
    if not isinstance(c, str) or is_unknown(c):
        return None
    t = fold(c)
    t = _COMMIT_LABEL.sub("", t).strip(_EDGE)
    return None if is_unknown(t) else t


# Non-evidence prose: a statement that only says the fact is not known, missing, unavailable, pending or still to be
# done. NE_PLACEHOLDER words say so by themselves; NE_FILLER words only frame a statement (status, result, value, is,
# see above, to be verified ...). A prose ref with no concrete anchor (a digit, a path or URL
# separator, a dotted name, a hash mark, an at sign or a quote) is non-evidence when (A) every word is one of the two
# lists, or (B) it holds a NE_PLACEHOLDER word and is short (<= 6 words): "status: unknown", "value is nil", "needs
# review". "a.py:12", "status 200" and "src/unknown/x.py" have an anchor and are never judged by their words.
_NE_PLACEHOLDER = frozenset(
    "unknown unk unknowable unverifiable unverified undetermined undefined unspecified unstated unavailable unconfirmed "
    "null nil none nothing nada na tbd tba todo missing absent empty blank vacant pending placeholder dummy fake stub "
    "mock lorem ipsum xxx draft incomplete unfinished unnamed unset notset undone tentative provisional later "
    "unclear inconclusive".split())
_NE_FILLER = frozenset(
    "status result results evidence value values source owner output data answer check reviewer review reviewed "
    "is are was were be been being the a an of for to this that it its still yet currently now not "
    "see above below attached notes note ticket same as before earlier previous follow will verify verified confirm "
    "confirmed confirmation verification needs need needed awaiting await in progress determined announced provided stated known "
    "available applicable set filled fill details detail info information more further later soon todo".split())
_NE_ANCHOR = re.compile(r"[0-9/\\#@\"'`=]|\w\.\w|::|\w\(\)")


def non_evidence(ref):
    """True when a prose evidence ref only says the fact is unknown, missing, null, nil, unavailable or pending (rule in
    the comment above). Callers judge prose only (a path, URL or bare location is not passed here)."""
    if not isinstance(ref, str):
        return True
    t = canon(ref, slashes=True).replace("n/a", "na")
    words = re.findall(r"[a-z]+(?:['\u2019][a-z]+)?", t)
    if not words or _NE_ANCHOR.search(t):
        return False
    if all(w in _NE_PLACEHOLDER or w in _NE_FILLER for w in words):
        return True
    return len(words) <= 6 and any(w in _NE_PLACEHOLDER for w in words)


def _credential_view(t):
    """A credential-shaped text: a pattern from CRED, or a run of 32+ characters from [A-Za-z0-9+/=_-] holding
    an upper-case letter, a lower-case letter and a digit, wherever it sits and whatever precedes it (a path,
    a URL, "x-"): a long mixed-case path is masked too, which is the conservative side of the net."""
    if CRED.search(t):
        return True
    for m in _RUN.finditer(t):
        r = m.group(0)
        if any(c.isupper() for c in r) and any(c.islower() for c in r) and any(c.isdigit() for c in r):
            return True
    return False


_ESC = {"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "/": "/", "\\": "\\", '"': '"'}


def _unicode_escapes(t):
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)


def _json_escapes(t):
    """Decode the JSON escapes (\\n, \\t, \\r ...) that json.dumps leaves in a printed key or count, however many
    times the text was escaped (each dumps doubles the backslashes), so an escaped newline or tab inside a token
    does not hide it."""
    return re.sub(r"\\{1,64}([ntrbf])", lambda m: _ESC[m.group(1)], t)


def _plain(t):
    """The text after the FULL normalization: NFKD, combining marks (Mn), format and control characters removed,
    then NFKC (so letters that compose, such as p + U+0301, are judged as the plain letter)."""
    d = unicodedata.normalize("NFKD", t)
    d = "".join(c for c in d if unicodedata.category(c) not in ("Cf", "Cc", "Mn"))
    return unicodedata.normalize("NFKC", d)


def redact(text):
    """See _redact(): the rule, with printable ASCII that holds no backslash or percent sign judged on one view (every
    other view of such text is the text itself) and the result cached per string."""
    t = text if isinstance(text, str) else str(text)
    return _redact(t)


@lru_cache(maxsize=65536)
def _redact(t):
    if t.isascii() and t.isprintable() and "\\" not in t and "%" not in t:
        return REDACTED if (_credential_view(t) or CRED.search(re.sub(r"\s+", "", t))) else t
    return _redact_full(t)


def _redact_full(text):
    """Fixed marker for text shaped like a credential. It is judged on the text as written, on its NFKC form, and
    on the fully normalized form (NFKD, then combining marks, format and control characters removed, then NFKC,
    so neither a mark nor a zero-width character hides a token) before any pattern is applied; escapes (\\uXXXX,
    \\n, \\t, \\r) are decoded first, and a newline, tab or carriage return (with the blanks around it) inside a
    token is joined, so a wrapped token is judged whole. A pattern list: a net, not a proof."""
    t = text if isinstance(text, str) else str(text)
    t = _unicode_escapes(t)                     # the returned text keeps this decoding (json.dumps keys)
    e = _json_escapes(t)
    e = re.sub(r"\s*[\r\n\t]\s*", "", e) if re.search(r"[\r\n\t]", e) else e
    n = unicodedata.normalize("NFKC", e)
    plain = _plain(e)
    u = unquote(t)                              # a percent-encoded scheme separator ("%3A%2F%2F") hides nothing
    if any(_credential_view(v) for v in (t, e, n, plain, u)) or CRED.search(re.sub(r"\s+", "", plain)):
        return REDACTED
    return t


def redact_obj(o):
    """Copy of a JSON-like value with every credential-shaped string value or key replaced."""
    if isinstance(o, dict):
        return {redact(k): redact_obj(v) for k, v in o.items()}
    if isinstance(o, list):
        return [redact_obj(x) for x in o]
    return redact(o) if isinstance(o, str) else o
