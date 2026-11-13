"""Shared text rules for the integration-review scripts (stdlib only, pure functions).

Loaded by path from the sibling scripts (they run under `python3 -I`, which keeps the script directory off
sys.path). is_unknown() is the ONE definition of an UNKNOWN-equivalent: missing or not a string, then after
Unicode NFKC folding, removal of format/control characters (zero-width space, BOM, joiners) and
surrounding whitespace of any kind, lower-casing and removal of trailing/leading punctuation, one of
the placeholders unknown, unk, ?, tbd, -, n/a, na, none, null, nil or empty.
redact() replaces text shaped like a credential by a fixed marker; the original is never kept.
"""
import re
import unicodedata

PLACEHOLDERS = frozenset({"", "unknown", "unk", "?", "tbd", "-", "--", "n/a", "na", "none", "null", "nil"})
_EDGE = " \t\r\n.,;:!'\"`()[]{}<>*_~|\\/="
# Placeholder family, matched on the compact form (separators removed): see is_unknown().
_FAMILY = frozenset({"", "na", "undefined", "undef", "null", "nil", "none", "notavailable", "notapplicable",
                     "unavailable", "unknown", "unk", "notknown", "unspecified", "notspecified", "notset",
                     "notprovided", "notstated", "tbd", "tba", "todo", "tobedetermined", "tobeannounced"})
_DASHES = "\u2010\u2011\u2012\u2013\u2014\u2015\u2212\u2043\u207b\u208b\u2e3a\u2e3b\u058a\u05be\u1806\ufe58\ufe63\uff0d\u30fc"
CRED = re.compile(
    r"(token|secret|passw|bearer|api[_-]?key|sk-ant|sk-[A-Za-z0-9]{8}|sk_(?:live|test)_|rk_(?:live|test)_|-----BEGIN"
    r"|authorization\s*[:=]|://[^/\s]*:[^/\s]*@|gh[pousr]_[A-Za-z0-9]|github_pat_|glpat-|npm_[A-Za-z0-9]{8}"
    r"|pypi-[A-Za-z0-9_-]{8}|hf_[A-Za-z0-9]{8}|dop_v1_|shp(?:at|ss|ca|pa)_|SG\.[A-Za-z0-9_-]{8}|ya29\.|"
    r"\b(?:AKIA|ASIA)[A-Z0-9]{8}|eyJ[A-Za-z0-9_-]{6}|xox[abprs]-|AIza[0-9A-Za-z_-]{8}"
    r"|\b(?:key|auth|pwd|cred\w*)\s*[:=]\s*\S{6})", re.I)
_RUN = re.compile(r"[A-Za-z0-9+/=_-]{32,}")
REDACTED = "[credential-shaped text redacted]"


def fold(v):
    """Comparable form of a string: NFKC, no format/control/space characters at the edges, lower case."""
    t = unicodedata.normalize("NFKC", v)
    t = "".join(" " if (c.isspace() or unicodedata.category(c) in ("Zs", "Zl", "Zp")) else c
                for c in t if unicodedata.category(c) not in ("Cf", "Cc") or c.isspace())
    return t.strip().lower()


def canon(v):
    """Placeholder-comparable form: NFKD, combining marks (Mn) and variation selectors removed, format/control
    characters removed, every dash/minus variant folded to "-", case folded, whitespace collapsed."""
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
        out.append(" " if (c.isspace() or cat in ("Zs", "Zl", "Zp")) else c)
    return re.sub(r"\s+", " ", "".join(out)).strip().casefold()


def is_unknown(v):
    """The ONE UNKNOWN-equivalent rule: not a string; or, after canon() and stripping edge punctuation and "=",
    a value with no letter or digit at all (?, ???, -, --, ..., an ellipsis), or one of the placeholder family
    (unknown unk n/a in any dotting or spacing, undefined, null, nil, none, not available/applicable/known,
    unavailable, unspecified, tbd, tba, todo, empty) once separators (space . / _ -) are removed."""
    if not isinstance(v, str):
        return True
    t = canon(v)
    if t in PLACEHOLDERS:
        return True
    core = t.strip(_EDGE + "?-")
    if not any(c.isalnum() for c in t):
        return True
    return re.sub(r"[\s./_-]+", "", core) in _FAMILY


def _credential_view(t):
    if CRED.search(t):
        return True
    for m in _RUN.finditer(t):
        r = m.group(0)
        if (any(c.isupper() for c in r) and any(c.islower() for c in r) and any(c.isdigit() for c in r)
                and not r.startswith(("x-", "/"))):
            return True
    return False


def redact(text):
    """Fixed marker for text shaped like a credential, judged on the text as written, on its NFKC form and on
    the form with format/control characters (zero-width splits) and combining marks removed. A pattern list:
    a net, not a proof."""
    t = text if isinstance(text, str) else str(text)
    t = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), t)     # JSON-escaped text (json.dumps keys)
    n = unicodedata.normalize("NFKC", t)
    stripped = "".join(c for c in n if unicodedata.category(c) not in ("Cf", "Cc", "Mn"))
    if any(_credential_view(v) for v in (t, n, stripped)) or CRED.search(re.sub(r"\s+", "", stripped)):
        return REDACTED
    return t


def redact_obj(o):
    """Copy of a JSON-like value with every credential-shaped string value or key replaced."""
    if isinstance(o, dict):
        return {redact(k): redact_obj(v) for k, v in o.items()}
    if isinstance(o, list):
        return [redact_obj(x) for x in o]
    return redact(o) if isinstance(o, str) else o
