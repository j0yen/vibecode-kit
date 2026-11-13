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
_EDGE = " \t\r\n.,;:!'\"`()[]{}<>*_~|\\/"
CRED = re.compile(
    r"(token|secret|passw|bearer|api[_-]?key|sk-ant|sk-[A-Za-z0-9]{8}|-----BEGIN|authorization\s*[:=]"
    r"|://[^/\s]*:[^/\s]*@|gh[pousr]_[A-Za-z0-9]|github_pat_|\b(?:AKIA|ASIA)[A-Z0-9]{8}|eyJ[A-Za-z0-9_-]{6}"
    r"|xox[abprs]-|AIza[0-9A-Za-z_-]{8}|\b(?:key|auth|pwd|cred\w*)\s*[:=]\s*\S{6})", re.I)
REDACTED = "[credential-shaped text redacted]"


def fold(v):
    """Comparable form of a string: NFKC, no format/control/space characters at the edges, lower case."""
    t = unicodedata.normalize("NFKC", v)
    t = "".join(" " if (c.isspace() or unicodedata.category(c) in ("Zs", "Zl", "Zp")) else c
                for c in t if unicodedata.category(c) not in ("Cf", "Cc") or c.isspace())
    return t.strip().lower()


def is_unknown(v):
    if not isinstance(v, str):
        return True
    t = fold(v)
    if t in PLACEHOLDERS:
        return True
    return t.strip(_EDGE) in PLACEHOLDERS


def redact(text):
    t = text if isinstance(text, str) else str(text)
    return REDACTED if CRED.search(unicodedata.normalize("NFKC", t)) else t


def redact_obj(o):
    """Copy of a JSON-like value with every credential-shaped string value or key replaced."""
    if isinstance(o, dict):
        return {redact(k): redact_obj(v) for k, v in o.items()}
    if isinstance(o, list):
        return [redact_obj(x) for x in o]
    return redact(o) if isinstance(o, str) else o
