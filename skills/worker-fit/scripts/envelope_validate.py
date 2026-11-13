#!/usr/bin/env python3
"""Validate worker-fit task envelopes. Standard library only, read-only, no network.

Usage: envelope_validate.py [--now TS|system] FILE [FILE...]   (FILE = one envelope, a list, or {"envelopes": [...]})
Exit 0 = no REFUSE finding, 1 = at least one REFUSE finding, 2 = unreadable input (not JSON, bad --now).
Observation window: observations older than STALE_WINDOW_SECONDS before the reference now, or dated after it,
are refused; the reference now is --now TS or else the host clock (--now system is an explicit alias).
Credential-shaped values are redacted from every printed line.
Counts are derived from the enumerated records; a declared total is only compared, never used.
A pass is a statement about the envelope's shape and internal consistency, not about production.
"""
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone

UNKNOWN = "UNKNOWN"
# values that stand for "nothing observed", compared after norm_text(): NFKC, format/control characters dropped,
# whitespace collapsed, edge punctuation/brackets/quotes stripped, lower-cased. A value with no letter or digit left
# (e.g. '?', '-', '--', '...') is a placeholder as well.
PLACEHOLDERS = {"unknown", "unk", "?", "tbd", "tba", "tbc", "todo", "-", "--", "n/a", "n.a", "na", "none", "null", "nil",
                "undefined", "not available", "not applicable", "unspecified", "missing", "empty", "pending", "unavailable",
                "unset", "not set", "unassigned", "unsure", "not known", "not provided", "not given", "no data", ""}
# the same words compared with every non-alphanumeric character removed, so spacing, slashes, backslashes, dots,
# hyphens, underscores and trailing punctuation never change the meaning: 'N / A', 'n\\a', 'n/a/', 'unknown-', 'Not-Set'.
_COMPACT_PLACEHOLDERS = {re.sub(r"[\W_]+", "", w) for w in PLACEHOLDERS if re.search(r"\w", w)}
# bare assertions that are neither an identity nor a reference: 'yes' / 'self' / 'authorized' as a consumer, reviewer,
# worker id or authorization/ACK evidence names nobody and cites nothing.
_NON_IDENTITY = {"yes", "no", "true", "false", "ok", "okay", "y", "n", "self", "me", "same", "own", "authorized",
                 "unauthorized", "approved", "accepted", "confirmed", "verified", "reviewed", "done", "ack", "acked",
                 "acknowledged", "granted", "noted", "agreed"}
# the placeholder class is a vocabulary of words, not a closed list of whole values: a value is a placeholder when every
# word in it (letters and digit groups, any separators) is a placeholder word, a negated evidence word ('not known',
# 'no data', 'to be determined'), an 'un<evidence word>' negation ('unidentified', 'unverified', 'unobserved', ...), a
# bare assertion or a stop word, and at least one word is a placeholder. 'unknown-host-7' and 'no-reply' are real names.
_P_WORDS = {"unknown", "unk", "unknwn", "tbd", "tba", "tbc", "tbs", "todo", "na", "none", "null", "nil", "undefined", "unspecified",
            "missing", "empty", "pending", "unavailable", "unset", "unassigned", "unsure", "unclear", "nobody", "nothing",
            "noone", "blank", "void", "placeholder", "redacted", "later", "soon", "waiting", "someone", "somebody",
            "something", "xxx", "dummy"}
_UN_RX = re.compile(r"un(?:identified|determined|observed|verified|confirmed|reported|named|recorded|specified|assigned|"
                    r"defined|resolved|checked|listed|disclosed|stated|supplied|provided|filled|populated|attested|"
                    r"established|documented|acknowledged|approved|reviewed|validated|detected|captured|collected|"
                    r"retrieved|queried|tracked|logged|noted|claimed|accepted|granted|authori[sz]ed|certified|signed|"
                    r"sourced|cited|decided|given|found|seen|read|known|set|sure|clear|available|applicable)")
_NEG = {"not", "no", "non", "never", "without", "be"}
_EVID = {"known", "available", "applicable", "set", "provided", "given", "specified", "determined", "identified", "observed",
         "recorded", "reported", "named", "assigned", "data", "value", "info", "information", "evidence", "one", "body",
         "decided", "defined", "found", "listed", "stated", "supplied", "confirmed", "verified", "seen", "read", "checked",
         "resolved", "disclosed", "filled", "yet", "relevant", "available"}
_STOP = {"yet", "to", "a", "an", "the", "of", "is", "are", "as", "by", "for", "this", "that", "it", "see", "above", "below",
         "per", "at", "on", "in", "with", "and", "or", "me", "trust", "here", "there"}
_EDGE = "<>[](){}\"'`.,;:!*_~|\\ "
STATES = ["NOT_STARTED", "RUNNING", "DONE", "BLOCKED", "UNKNOWN"]
SHAPES = ["implementation", "review", "decision", "deterministic", "UNKNOWN"]
EFFECTS = ["none", "applied", "UNKNOWN"]
SCHEMA_ID = "worker-fit-envelope/1"
REQUIRED_TOP = ["schema", "parent", "task_id", "revision", "approved_ac_refs", "work_shape", "source",
                "current_owner", "owner_reachable", "target", "worker", "state", "effect", "result",
                "consumer", "ack", "next_action", "observed_at", "evidence", "coverage_gaps",
                "declared_complete"]
OPTIONAL_TOP = ["label"]
WORKER_KEYS = ["host", "unit", "invocation", "child", "session", "account", "model", "effort"]
# kinds: s=nonempty str, i=int, b=bool, t=timestamp-or-UNKNOWN, tri=bool|UNKNOWN, sn=str|None, in=int|None
SUB = {
    "source": {"owner": "s", "identity": "s", "identity_at": "t", "revision_at": "t"},
    "target": {"repo": "s", "branch": "s", "head": "s"},
    "worker": {k: "s" for k in WORKER_KEYS},
    "effect": {"state": "e", "no_replay": "b", "policy": "s"},
    "result": {"artifact": "sn", "event": "sn", "task_id": "sn", "revision": "in", "reviewed": "tri"},
    "consumer": {"named": "s", "alternate": "sn", "alternate_authorized": "b", "available": "tri"},
    "ack": {"accepted": "b", "evidence": "sn"},
    "observed_at": {"envelope": "t", "worker": "t", "result": "t"},
}
# optional sub-fields and their kinds: reviewed_by = identity of a reviewer distinct from the worker;
# alternate_authorization_ref = reference to the evidence that authorises the alternate consumer
SUB_OPTIONAL = {"source": ["claim"], "result": ["reviewed_by"], "consumer": ["alternate_authorization_ref"]}
OPTIONAL_KIND = {"result.reviewed_by": "sn", "consumer.alternate_authorization_ref": "sn"}
EVIDENCE_OPTIONAL = ["head", "repo", "branch"]


def finding(code, path, message, severity="REFUSE"):
    return {"code": code, "severity": severity, "path": path, "message": message}


def norm_text(v):
    """The one normalizer for evidence-bearing strings: NFKC, zero-width/format and control characters dropped,
    any whitespace collapsed to one space, edge punctuation/brackets/quotes stripped, lower-cased."""
    s = unicodedata.normalize("NFKC", v)
    s = "".join(" " if c.isspace() else c for c in s if c.isspace() or unicodedata.category(c) not in ("Cf", "Cc"))
    return " ".join(s.split()).strip(_EDGE).strip().lower()


def _tokens(v):
    """Words (letter runs) and digit groups of a value, lower-cased; 'n/a' reads as 'na', 'un-known' as 'unknown'."""
    s = norm_text(v)
    s = re.sub(r"(?<![^\W\d_])n\s*[/\\.]\s*a(?![^\W\d_])", "na", s)
    s = re.sub(r"(?<![^\W\d_])un[\s_-]+(?=[^\W\d_])", "un", s)
    return re.findall(r"[^\W\d_]+|\d+", s)


def _placeholder_word(t, neg):
    return t in _P_WORDS or bool(_UN_RX.fullmatch(t)) or (neg and t in _EVID)


def _is_placeholder_phrase(v):
    """True when the value is made only of placeholder words, negated evidence words, stop words and digit groups,
    with at least one placeholder word: 'unidentified', 'TBA/TBD', 'N/A (unknown)', 'not yet known', 'pending 7'."""
    saw, neg = False, False
    for t in _tokens(v):
        if t.isdigit() or t in _STOP and t not in _NEG:
            continue
        if t in _NEG:
            neg = True
            continue
        if _placeholder_word(t, neg):
            saw = True
            continue
        return False
    return saw


def _no_substance(v):
    """True when no word of the value is substantive: only placeholder words, bare assertions (yes/ok/approved/...),
    negations and stop words, however many digits or locators come with them ('yes 1', 'unknown:0', 'ok #1')."""
    words = [t for t in _tokens(v) if not t.isdigit()]
    if not words:
        return False  # a bare number or locator ('12345', '#123') names no word at all
    neg = False
    for t in words:
        if t in _NEG:
            neg = True
        elif t in _STOP or t in _NON_IDENTITY or _placeholder_word(t, neg):
            continue
        else:
            return False
    return True


def is_unknown(v):
    """True for None and for any UNKNOWN-equivalent placeholder string, however spelled (see norm_text)."""
    if v is None:
        return True
    if not isinstance(v, str):
        return False
    s = norm_text(v)
    return (s in PLACEHOLDERS or not any(c.isalnum() for c in s) or _compact(s) in _COMPACT_PLACEHOLDERS
            or _is_placeholder_phrase(s))


def _compact(s):
    return re.sub(r"[\W_]+", "", s)


def is_assertion_word(v):
    """True for a bare yes/no/true/ok/self/authorized-style word (after norm_text, any punctuation or spacing)."""
    return isinstance(v, str) and _compact(norm_text(v)) in _NON_IDENTITY


def ref_like(v):
    """Positive validation for a reference (authorization reference, ACK evidence): a string that is not a placeholder
    or a bare assertion word, has at least one substantive word unless it is a bare number or locator, and carries a
    locator: a digit (id, number, date) or one of : / # @ (url, path, handle). 'yes 1', 'unknown:0', 'ok #1' fail."""
    if not isinstance(v, str) or is_unknown(v) or is_assertion_word(v) or _no_substance(v):
        return False
    s = unicodedata.normalize("NFKC", v)
    return any(c.isdigit() for c in s) or any(c in s for c in ":/#@")


_IDENT = re.compile(r"[A-Za-z0-9%][A-Za-z0-9._:@/+%=-]{0,127}")  # %12 (tmux pane), pid=77, fe80::1%eth0
_SHA = re.compile(r"[0-9a-fA-F]{7,64}")
_PATH = re.compile(r"[A-Za-z0-9._/+:@%=~?&#,-]{1,512}")
_SPLIT = re.compile(r"[-_./+=:@%~?&#,]+")
_HOST_PORT = re.compile(r"[^:]+:\d{1,5}")
_IPV6 = re.compile(r"[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*:[0-9A-Fa-f:.]*(?:%[A-Za-z0-9_.-]{1,32})?")


_DNS_HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,18}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,18}[a-z0-9])?){2,6}")
_DNS_TLDS = frozenset("net com org io dev local internal lan corp home arpa cloud app ai co".split())


def _dns_host(s):
    """A multi-label DNS name (3+ lower-case labels of at most 20 characters, a well-known last label), whose labels are
    machine-generated names that read as random ('tail9z8y7'): the DNS grammar is the field's grammar. A credential
    word in any label still marks it."""
    return bool(_DNS_HOST.fullmatch(s)) and s.rsplit(".", 1)[-1] in _DNS_TLDS and not _cred_marked([x for x in _SPLIT.split(s) if x])


def ident(v, kind=None):
    """The value as an identifier (ASCII word characters and . _ : @ / + -, no spaces), or None when it is not one, is a
    placeholder, or is not a trusted identity: its pieces must read as ids (_id_pieces_ok), no credential word may be
    joined to a non-trivial piece, a host has no user:password userinfo, and the credential layers of redact() must leave it
    unchanged. The random-token run rule does not apply here: a hex or uuid piece is a normal part of a unit, scope,
    session, invocation or consumer name, validated by this field format. kind="host" adds the host grammar.
    Used wherever a value names a host, unit, child, consumer, reviewer, owner, task, repo or branch."""
    if not isinstance(v, str) or is_unknown(v) or is_assertion_word(v):
        return None
    s = unicodedata.normalize("NFKC", v).strip()
    if not (((_IDENT.fullmatch(s) and _id_pieces_ok(s)) or (kind == "host" and _dns_host(s))) and redact_credentials(s) == s):
        return None
    if kind == "host" and ":" in s and not (_IPV6.fullmatch(s) or _HOST_PORT.fullmatch(s.rsplit("@", 1)[-1] if "@" in s else s)):
        return None
    return s


def path_ident(v):
    """The value as an artifact / event / reference locator (a path or id with no whitespace), or None: placeholder,
    assertion word, a piece that is not an id, a credential word joined to a non-trivial piece, or carrying a credential
    (credential-named pair or query parameter, provider shape)."""
    if not isinstance(v, str) or is_unknown(v) or is_assertion_word(v):
        return None
    s = unicodedata.normalize("NFKC", v).strip()
    return s if _PATH.fullmatch(s) and _id_pieces_ok(s) and redact_credentials(s) == s else None


# A validated identity value is carried through output as a marked span: redaction hides credentials everywhere but does
# not apply the random-token run rule to a span an identity field's own validation accepted. The marks hold a
# per-process random nonce, so no envelope text can forge one.
_NONCE = os.urandom(6).hex()
_MARK_OPEN, _MARK_CLOSE = "\ue000" + _NONCE + "\ue001", "\ue001" + _NONCE + "\ue000"
_MARK_RX = re.compile(re.escape(_MARK_OPEN) + r"(.{0,600}?)" + re.escape(_MARK_CLOSE), re.S)
_HOLD_RX = re.compile("\ue002" + _NONCE + r"(\d+)\ue003")


_KINDS = {"ident": ident, "host": lambda x: ident(x, "host"), "path": path_ident,
          "sha": lambda x: x.strip() if is_sha(x) else None}
_OPQ_KEY = os.urandom(16)


def opaque(label, v):
    """An opaque reference to a value this tool does not trust enough to print: the field label plus a short digest keyed
    with a per-process random 128-bit key (the interpreter's own keyed string hash over key, label and value: equal values
    give equal refs inside one run, different fields give different refs, a guess cannot be confirmed from the output, and
    nothing of the value is recoverable from 32 bits). Never the raw value. Refs are not stable across runs."""
    norm = unicodedata.normalize("NFKC", v if isinstance(v, str) else repr(v))
    return "[opaque %s %08x]" % (label, hash((_OPQ_KEY, label, norm)) & 0xFFFFFFFF)


def keep(kind, v, label=None):
    """The value to print for an identity field: marked when the field's own format validation accepts it (kind
    ident | host | path | sha) AND the one trust gate accepts it under the field's own profile (_profile(label): the id
    shapes this field carries), else the raw value, which then goes through full redaction. The printed text is the value
    as given; only the validated, trusted form skips the run rule."""
    if not isinstance(v, str):
        return v
    ok = _KINDS[kind](v)
    if kind != "sha" and ok == v and not _trusted_pieces(v, max_ids=2 if kind == "path" else 1, profile=_profile(label)):
        return v
    return v if ok is None or ok != v else _MARK_OPEN + v + _MARK_CLOSE


def show(label, v, kind="ident"):
    """What an identity field prints: the value when it validates against its field's grammar and the one trust gate under
    the field's own profile (marked, so the run rule skips it), a placeholder as it is (UNKNOWN stays UNKNOWN), and otherwise
    an opaque keyed reference, never the raw value."""
    if not isinstance(v, str) or is_unknown(v) or _OPQ_REF.fullmatch(v):
        return v
    k = keep(kind, v, label)
    return k if k != v else opaque(label, v)


_OPQ_REF = re.compile(r"\[opaque [a-z-]{1,12} [0-9a-f]{8}\]")
def show_row(label, v, words=frozenset()):
    """What a queue-row field prints (a row id, owner, wait, status or claim): the SAME trust gate as every identity
    (_gate_values: closed vocabulary, bounded numbers, exact id grammars, a small budget of unlisted characters). Each
    whitespace-separated token must also pass the credential layers; the whole value shares one budget, so any number of
    short pieces is bounded. Otherwise the whole value is an opaque keyed ref. A non-string value is an opaque ref (an
    integer of at most seven digits prints as the number), a placeholder stays as it is."""
    if isinstance(v, bool) or not isinstance(v, (str, int)):
        return opaque(label, v)
    if isinstance(v, int):
        return str(v) if abs(v) < 10 ** _MAX_DIGIT_PIECE else opaque(label, v)
    if is_unknown(v) or _OPQ_REF.fullmatch(v):
        return v
    s = unicodedata.normalize("NFKC", v).strip()
    toks = s.split()
    if (s == v.strip() and toks and len(s) <= 256 and all(
            redact_credentials(t) == t and not _cred_marked([x for x in _SPLIT.split(t) if x]) for t in toks)
            and _gate_values(toks, words, 0, _NO_PROFILE)):  # a queue row carries no hex id, uuid or ULID
        return v
    return opaque(label, v)


def show_ref(label, v):
    """A free-text reference (evidence ref): a single locator-shaped token prints when it validates and is otherwise an
    opaque ref; prose (whitespace) is narrative and goes through full redaction."""
    if not isinstance(v, str) or is_unknown(v):
        return v
    if any(c.isspace() for c in v.strip()):
        return redact(v, keep_marks=True)  # prose: the free-text trust gate
    return show(label, v, "path")


def unmark(v):
    """The value with every identity mark removed (no redaction): for results handed to library callers."""
    if isinstance(v, str):
        return _MARK_RX.sub(lambda m: m.group(1), v)
    if isinstance(v, list):
        return [unmark(x) for x in v]
    if isinstance(v, dict):
        return {k: unmark(x) for k, x in v.items()}
    return v


def is_sha(v):
    return isinstance(v, str) and bool(_SHA.fullmatch(v.strip()))


class DupDict(dict):
    """dict that remembers which keys the JSON text repeated (json would silently keep the last value)."""
    dups = ()


def _pairs(pairs):
    d, dups = DupDict(), []
    for k, v in pairs:
        if k in d:
            dups.append(k)
        d[k] = v
    d.dups = tuple(dups)
    return d


REDACTED = "[REDACTED]"
# Redaction is structural first and a list of provider shapes second. A value is hidden when (a) the key, flag or header
# it belongs to has a credential word in its name, whatever the value looks like, (b) it is a long run of token
# characters that mixes letters and digits and is not a known-safe identifier, or (c) it is URL userinfo or the value of
# a credential-named query parameter. The named provider patterns remain as an extra layer.
_NOT_DONE = r"(?!\[REDACTED\])"
# name/value separators: = : => -> and their full-width / small-form look-alikes
_SEP = r"(?:=>|->|[:=\uff1a\uff1d\ufe55\ufe66\u2236])"
_QUOTED_OR_WORD = r"""(?:"(?:[^"\\]|\\.)*"|'[^']*'|[^\s,;&)"'\]}]+)"""
# name words: a segment (split on non-alphanumerics and camelCase) equal to one of these, or holding one of the stems, or
# a '<qualifier>key' compound (apikey, accountkey, ...), marks a credential-carrying name
_CRED_WORDS = {"pass", "pwd", "auth", "authn", "authz", "key", "keys", "sig", "api", "dsn", "cert", "certs", "certificate",
               "session", "sessions", "sid", "cred", "creds", "jwt", "otp", "cookie", "cookies", "bearer", "token",
               "tokens", "secret", "secrets", "credential", "credentials", "private", "passphrase", "password", "passwd",
               # abbreviations of the same names (re-review 5 DEF-2)
               "pw", "pat", "pin", "ak", "sk", "seed", "salt", "hmac", "mnemonic", "passcode", "privkey", "prikey", "prvkey", "csrf", "xsrf", "cvv", "ssn", "unseal", "kubeconfig",
               # re-review 7: short forms and the rest of the family
               "tok", "tkn", "apikey", "apikeys", "passwords", "authkey", "accesskey", "secretkey", "sshkey", "oauth"}
_CRED_STEMS = ("token", "secret", "passw", "passphrase", "passcode", "credential", "cookie", "signature", "bearer",
               "authorization", "authorisation", "sessionid", "privatekey")
_KEY_COMPOUND = re.compile(r"(?:api|access|account|secret|private|ssh|auth|signing|encryption|master|shared|hmac|license|"
                           r"app|client|consumer|service|storage|public)key")


_CRED_COMPOUNDS = ("oauth_verifier", "code_verifier", "recovery_code", "recovery_codes", "backup_code", "backup_codes",
                   "unlock_code", "unlock_key", "sas")


_LEET = str.maketrans("013457$@", "oleastsa")
_ALPHA_RUNS = re.compile(r"[a-z]+")
_GLUE_KEY = re.compile(r"(?:api|access|account|secret|private|priv|pri|prv|ssh|auth|signing|encryption|master|shared|hmac|license|app|"
                       r"client|consumer|service|storage|public|my|aws|gcp|db|admin|user|root)key")


def _seg_cred(seg):
    """A name segment (lower case, no separators) that is a credential word, holds a credential stem, is a
    '<qualifier>key' compound, or carries one of those with digits or letters glued on (key9, pw9, mykey3, apikeyv2,
    t0ken): the digit-free runs and the leet-folded form are looked at too."""
    if seg in _CRED_WORDS or any(w in seg for w in _CRED_STEMS) or _KEY_COMPOUND.fullmatch(seg):
        return True
    if seg.isalpha() or not any(c.isdigit() for c in seg):
        return False
    for run in _ALPHA_RUNS.findall(seg):
        if run in _CRED_WORDS or any(w in run for w in _CRED_STEMS) or _GLUE_KEY.search(run):
            return True
    folded = seg.translate(_LEET)
    return folded != seg and any(w in folded for w in _CRED_STEMS)


_CRED_NAME_CACHE = {}


def _cred_name(name):
    hit = _CRED_NAME_CACHE.get(name)
    if hit is None:
        if len(_CRED_NAME_CACHE) > 8192:
            _CRED_NAME_CACHE.clear()
        hit = _CRED_NAME_CACHE[name] = _cred_name_uncached(name)
    return hit


def _cred_name_uncached(name):
    flat = "_" + re.sub(r"[^a-z0-9]+", "_", re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name).lower()).strip("_") + "_"
    if any("_" + c + "_" in flat for c in _CRED_COMPOUNDS):
        return True
    for seg in re.split(r"[^A-Za-z0-9]+", re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", name).lower()):
        if seg and _seg_cred(seg):
            return True
    return False


_SEP_AT = re.compile(r"[\"']?\s{0,8}" + _SEP + r"\s{0,8}")
_NAME_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-")
_VALUE = re.compile(_QUOTED_OR_WORD)
_FLAG_AT = re.compile(r"(?<![\w-])(?P<flag>--?[A-Za-z][\w-]{0,60})(?P<mid>[ \t]+)" + _NOT_DONE)
_USER_FLAG = re.compile(r"(?<![\w-])(?P<flag>--?(?:u|user|proxy-user|U))(?P<mid>[ \t]+)" + _NOT_DONE +
                        r"""(?P<val>(?:"[^"]*:[^"]*"|'[^']*:[^']*'|[^\s"']+:[^\s"']*))""")
_RUN = re.compile(r"(?<![A-Za-z0-9_\-+/.])[A-Za-z0-9_\-+/.]{20,}=*(?![A-Za-z0-9_\-+/.])")
_DIGEST_FIELD = re.compile(r"(?i)(?:head|sha\d*|digest|commit|rev(?:ision)?|oid|hash)\W{0,3}$")


_DIGIT = re.compile(r"\d")


def _keyish(val):
    """True for a value that reads as a key and not as a name: a piece of 6+ characters that mixes letters and digits and
    is neither a plain id piece, a hex or date id, nor a word-like name ('Zq9Xk3Lm' is, 'WF1663Impl', 'r7wfr7review',
    'abc123def456' are not). The name before it does not matter: this layer needs no credential word."""
    v = val.strip("\"'`")
    for seg in re.split(r"[-_./+=:,;@%~?&#]+", v):
        if (len(seg) >= 6 and seg.isascii() and seg.isalnum() and any(c.isdigit() for c in seg) and any(c.isalpha() for c in seg)
                and not _piece_ok(seg)):
            return True
    return False


def _redact_named_values(text):
    """name = value / name: value / "name": "value" / ?name=value where the name (the run of name characters before the
    separator) holds a credential word: the value is hidden, and so is a key-shaped value under any other name (the name
    is not trusted). Linear: each separator is looked at once, a value is read (bounded) and a hidden one is skipped."""
    out, pos = [], 0
    for m in _SEP_AT.finditer(text):
        if m.start() < pos:
            continue
        j = m.start()
        while j > pos and text[j - 1] in _NAME_CHARS:
            j -= 1
        if j == m.start():
            continue
        if text.startswith(REDACTED, m.end()):
            continue
        if not _cred_name(text[j:m.start()]):
            if not _DIGIT.search(text, m.end(), m.end() + 80):
                continue  # a key-shaped value mixes in a digit: nothing to read otherwise
            v = _VALUE.match(text, m.end(), m.end() + 200)  # any name: a key-shaped value is hidden; bounded read
            if v is None or not _keyish(v.group(0)):
                continue
        sep_end = m.end()
        while text[sep_end - 1].isspace():
            sep_end -= 1
        end = _structure_end(text, sep_end, j)
        if end is None:
            v = _VALUE.match(text, m.end())
            if v is None:
                continue
            end = v.end()
        out.append(text[pos:m.end()] + REDACTED)
        pos = end
    out.append(text[pos:])
    return "".join(out)


def _structure_end(text, i, name_start):
    """End of a non-scalar value that starts at i (after the separator): a JSON/flow array or object (string-aware
    bracket walk; an unclosed one runs to the end of the text, so a half-written secret fails closed) or a YAML block
    (the indented or '- ' lines under the key). None when the value is a scalar."""
    n = len(text)
    k = i
    while k < n and text[k] in " \t\r\n":
        k += 1
    if k < n and text[k] in "[{":
        depth, q = 0, None
        while k < n:
            c = text[k]
            if q:
                if c == "\\":
                    k += 1
                elif c == q:
                    q = None
            elif c in "\"'":
                q = c
            elif c in "[{":
                depth += 1
            elif c in "]}":
                depth -= 1
                if depth <= 0:
                    return k + 1
            k += 1
        return n
    nl = text.find("\n", i)
    if nl == -1 or text[i:nl].strip(" \t\r"):
        return None
    ls = text.rfind("\n", 0, name_start) + 1
    indent = len(text[ls:name_start]) - len(text[ls:name_start].lstrip(" \t"))
    end, pos = None, nl + 1
    while pos < n:
        e = text.find("\n", pos)
        e = n if e == -1 else e
        line = text[pos:e]
        body = line.lstrip(" \t")
        if body.strip() and not (len(line) - len(body) > indent or (len(line) - len(body) == indent and body.startswith("- "))):
            break
        if body.strip():
            end = e
        pos = e + 1
    return end


def _redact_flag_values(text):
    """--flag VALUE / -flag VALUE where the flag name holds a credential word."""
    out, pos = [], 0
    for m in _FLAG_AT.finditer(text):
        if m.start() < pos:
            continue
        cred = _cred_name(m.group("flag"))
        if not cred and not _DIGIT.search(text, m.end(), m.end() + 80):
            continue
        v = _VALUE.match(text, m.end()) if cred else _VALUE.match(text, m.end(), m.end() + 200)
        if v is None or not (cred or _keyish(v.group(0))):
            continue
        out.append(text[pos:m.end()] + REDACTED)
        pos = v.end()
    out.append(text[pos:])
    return "".join(out)


# short password flags whose meaning belongs to the command (-p is a port for ssh, a path switch for mkdir): keyed by command.
# Each entry is (command word, flag pattern, value-after-flag pattern). The command word is found once, its command (up to
# the next newline, | ; or &) is read once and every matching flag in it is redacted in that single pass, so repeated
# command words cost linear time.
_CMD_SEG_END = re.compile(r"[\n|;&]")
_CMD_PW_FLAGS = [
    (re.compile(r"(?<![\w-])sshpass\b"), re.compile(r"(?<![\w-])-p[ \t]*" + _NOT_DONE)),
    (re.compile(r"(?<![\w-])(?:mysql|mysqldump|mysqladmin|mariadb)\b"),
     re.compile(r"(?<=\s)-p(?:(?=\S)|[ \t]+)" + _NOT_DONE)),
    (re.compile(r"(?<![\w-])(?:unzip|zip)\b"), re.compile(r"(?<=\s)-P[ \t]*" + _NOT_DONE)),
    (re.compile(r"(?<![\w-])(?:7z|7za|7zr)\b"), re.compile(r"(?<=\s)-p(?=\S)" + _NOT_DONE)),
]


def _redact_one_command(text, cmd_rx, flag_rx):
    out, pos, scan = [], 0, 0
    for m in cmd_rx.finditer(text):
        if m.start() < scan:
            continue  # inside a command already read
        e = _CMD_SEG_END.search(text, m.end())
        seg_end = e.start() if e else len(text)
        scan = seg_end
        i = m.end()
        while i < seg_end:
            f = flag_rx.search(text, i, seg_end)
            if f is None:
                break
            v = _VALUE.match(text, f.end())
            if v is None:
                i = f.end()
                continue
            out.append(text[pos:f.end()] + REDACTED)
            pos = i = v.end()
            scan = max(scan, pos)
    out.append(text[pos:])
    return "".join(out)


def _redact_command_pw_flags(text):
    for cmd_rx, flag_rx in _CMD_PW_FLAGS:
        text = _redact_one_command(text, cmd_rx, flag_rx)
    return text


def _user_flag(m):
    return m.group("flag") + m.group("mid") + REDACTED


def _random_looking(core):
    """True unless every piece of the run (split on - _ . / + =) is short (<= 8), digits, a lower-case word, a
    capitalised word, or a short word followed by digits: ids, branch names, unit names, paths and dates read that way,
    a key, a hash or a base64 blob does not."""
    return any(not _plain_piece(seg) for seg in re.split(r"[-_./+=]+", core))


def _plain_piece(seg):
    return (len(seg) <= 8 or seg.isdigit() or re.fullmatch(r"[a-z]+", seg) is not None
            or re.fullmatch(r"(?:[A-Z][a-z]+)+|[A-Z]+", seg) is not None or re.fullmatch(r"[A-Za-z]{1,10}\d{1,10}", seg) is not None)


# Pieces an identity field may carry beyond the plain ones: a hex id (invocation, build, digest), a lower-case word with a
# hex suffix (tail1a2b3, r<hex32>), a compact UTC timestamp, a ULID, and a "word-like" mixed alphanumeric name
# (WF1663Impl, r7wfr6review, wmbuild1663impl2). A long piece that is none of these (a base62 key) is not an identifier by
# field format, whatever field it sits in.
_ID_PIECE = re.compile(r"[0-9a-fA-F]{9,64}|[a-z]{1,12}[0-9a-f]{1,64}|\d{8}T\d{6}Z?|[0-7][0-9A-HJKMNP-TV-Z]{25}|[0-7][0-9a-hjkmnp-tv-z]{25}")
_TOKENS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+")
_STRONG_WORDS = {"token", "tokens", "secret", "secrets", "password", "passwd", "pass", "pwd", "pw", "pat", "bearer",
                 "credential", "credentials", "apikey", "privkey", "passphrase", "passcode"}
_STRONG_STEMS = ("token", "secret", "passw", "credential", "bearer", "passphrase", "passcode", "apikey", "privkey")
_SHORT_STRONG = ("pat", "pw", "pwd", "pass")
_NAME_WORDS = frozenset("fleet quota ring service scope socket timer slice mount target path unit worker svc bot api user local prod dev test ci "
                        "refresh rotate store watch monitor check sync vault manager helper daemon proxy agent runner job "
                        "server client file cache reader writer fetch probe gate guard lint scan audit".split())
_TINY = re.compile(r"\d{1,4}")


_VOWELS = frozenset("aeiouyAEIOUY")
_DATE_PIECE = re.compile(r"(\d{8}T\d{6}Z?|20\d{6})")


def _wordish(seg):
    """A mixed letter/digit name that reads as words, not as a key: at most 32 ASCII alphanumerics in at most six letter or
    digit groups (at most two digit groups), where >= 60 % of the letters sit in alphabetic tokens of 4+ letters, at most
    two tokens have 1-2 letters, and every long token has vowels (>= 20 % of the letters of the long tokens). 'WF1663Impl',
    'r7wfr6review', 'wmbuild1663impl2' read as names; a random base62 key does, by measurement, in under 4 % of cases."""
    if not (seg.isascii() and seg.isalnum() and len(seg) <= 32):
        return False
    groups = _TOKENS.findall(seg)
    toks = [t for t in groups if not t.isdigit()]
    if "".join(groups) != seg or not toks or len(groups) > 6 or len(groups) - len(toks) > 2:
        return False
    letters = sum(map(len, toks))
    long_ = "".join(t for t in toks if len(t) >= 4)
    return (len(long_) * 100 >= letters * 60 and sum(1 for t in toks if len(t) <= 2) <= 2
            and sum(c in _VOWELS for c in long_) * 100 >= len(long_) * 20 and all(set(t) & _VOWELS for t in toks if len(t) >= 4))


def _class(c):
    return 0 if c.isdigit() else 1 if c.islower() else 2


def _idplain(seg):
    """A plain identity piece. Up to eight characters any short word, number or hex id reads as plain, but a short mixed
    piece with many digit/letter/case changes ('Zq9Xk3Lm') is key-shaped, not a name ('r7wfr6', 'WF1663', 'x7k2p' pass)."""
    if len(seg) <= 8 and not (seg.isdigit() or re.fullmatch(r"[0-9a-fA-F]+", seg)):
        if sum(1 for a, b in zip(seg, seg[1:]) if _class(a) != _class(b)) > 4:
            return False
    return _plain_piece(seg)


def _vocab_suffix(seg):
    """A vocabulary word of at least three letters followed by a generated suffix of at most five characters ('tail9z8y7'): the
    trust gate charges the suffix to the unlisted budget."""
    low = seg.lower()
    return seg.isascii() and seg.isalnum() and any(low.startswith(w) and 0 < len(low) - len(w) <= _MAX_SHORT
                                                     for w in _ID_WORDS if len(w) >= 3 and not _cred_name(w))


def _piece_ok(seg):
    """One piece of an identity: plain, an id shape, or word-like; a compact date inside a piece ('r7wfr620261113') is
    checked as its own piece."""
    if _idplain(seg) or _ID_PIECE.fullmatch(seg) or _wordish(seg) or _vocab_suffix(seg):
        return True
    parts = [x for x in _DATE_PIECE.split(seg) if x]
    return len(parts) > 1 and all(_idplain(x) or _ID_PIECE.fullmatch(x) or _wordish(x) for x in parts)


def _cred_marked(segs):
    """True when the id carries a credential word beside a non-trivial piece ('token-<hex>', 'Bearer-<hex>', 'pat_<hex>',
    'secret/<hex>'), or a credential word glued to a hex or digit tail ('token9f8e7d6c', 'pat9f8e7d6c5b4a'): a credential
    word names a credential, so the identity is not trusted. A bare word ('token-service') is a name."""
    marks = []
    for seg in segs:
        low = seg.lower()
        if low in _STRONG_WORDS:
            marks.append(seg)
        elif any(w in low for w in _STRONG_STEMS) and any(c.isdigit() for c in low):
            return True
        elif any(low.startswith(w) and re.fullmatch(r"(?=.*\d)[0-9a-f]{6,}", low[len(w):]) for w in _SHORT_STRONG):
            return True
    return bool(marks) and any(seg not in marks and not (_TINY.fullmatch(seg) or seg.lower() in _NAME_WORDS) for seg in segs)


# TRUST LAYER. Validating an identity against its field grammar is not proof that it is not a credential: a grammar-valid
# id can hold a secret. An identity prints only when its pieces are also trusted. A random-looking piece (a hex id of 9+
# characters, a word glued to one, a ULID) is trusted only beside pieces from a CLOSED vocabulary of name words (a
# positive list, never a list of credential words: a word this tool has not been told about is opaque by default), plus
# digits, dates and short hex groups; and a credential word joined to a long piece is never trusted.
_ID_WORDS = frozenset(("task tasks sess inv invocation run runs build builds wm wf unit units evt event events result "
                       "results review reviews reviewer verifier verify child children coder codex claude exec worker "
                       "workers service scope socket timer slice mount target path json log logs txt md out retained "
                       "mnt ssd cargo tmp var home usr opt src scripts script evidence artifact artifacts report reports "
                       "probe probes id pid ts tail host node pod vm i r w ryzen redbaron ryzen7 hermes ctl rb orch hub "
                       "seat consumer producer owner queue row ask rev revision rev attempt step phase lane slot batch "
                       "ci job jobs pipeline merge deploy release land lands head base main work tree wt clone repo "
                       "branch commit pr hook hooks cron tick wake loop agent agents bus hub fleet kit vibecode skill "
                       "fit trace span request req resp response msg message note notes doc docs journal acct account feat feature features hotfix bug "
                       "syn synthorg mcphost wintermute prd dream gate golden fixture fixtures sample demo example sandbox stage staging prod "
                       "production dev canary shadow backup snapshot snap checkpoint ckpt metrics stats status state github gh remote origin "
                       "upstream tmux pane window screen term pty shell bash sh py python rs rust node npm yarn proc process thread tid name label "
                       "spec specs plan plans diff patch fix fixes test tests suite case cases shift clock "
                       "wfit impl implementation opus sonnet haiku fable root temp us eu ap west east north south central compute region zone cluster "
                       "controller carbon hetzner josephsyen aide watch rotate refresh manager daemon runner quota ring monitor sync check").split())
_ULID_ANY = re.compile(r"[0-7][0-9A-HJKMNP-TV-Z]{25}|[0-7][0-9a-hjkmnp-tv-z]{25}")
_SHORT_HEX = re.compile(r"[0-9a-fA-F]{1,4}")

# THE ONE TRUST GATE (_gate_values). A piece of a value prints only when it is (a) a word of the CLOSED vocabulary
# (_ID_WORDS, the caller's reviewed words, the DNS top-level labels: enumerated in this file), (b) a bounded number, (c) a
# validated calendar timestamp or date, (d) one of the EXACT id shapes (a uuid 8-4-4-4-12, a hex id of 7-12, 32, 40 or 64
# characters that mixes digits and letters, an instance id, a ULID, an IP literal in a host) AND the shape is one the FIELD'S
# OWN PROFILE names, alone or beside other pieces in the field's template (_PROFILES, below), or (e) a small amount of unlisted
# material: a piece of at most five characters, or one unlisted token of at most three letters inside a vocabulary compound.
# Unlisted material has a TOTAL budget per value (_MAX_UNLISTED characters), so no count of short pieces adds up to a
# credential, and an id grammar is allowed once (twice in a path) so groups of hex do not concatenate into a key. Everything
# else is opaque. A grammar-valid id is never trusted for its grammar alone: a field that does not carry the shape prints an
# opaque ref, and no denylist word decides anything here.
_MAX_DIGIT_PIECE = 7  # the longest digit-only piece (a pid, a sequence number, a compact date)
_MAX_DIGITS_TOTAL = 14  # the most digits outside timestamps and ids one value may carry
_MAX_UNLISTED = 8  # the most characters of unlisted material one value may carry
_MAX_SHORT = 5  # the longest unlisted piece
_MAX_UNLISTED_WITH_ID = 0  # beside an id grammar nothing unlisted: a random id sits only beside closed-vocabulary pieces
_MAX_PIECES = 40
_UUID = re.compile(r"(?<![0-9A-Za-z])[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}(?![0-9A-Za-z])")
_DATE_OK = r"20\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])"
_TS_ID = re.compile(_DATE_OK + r"T(?:[01]\d|2[0-3])[0-5]\d[0-5]\dZ?")
_DATE_ID = re.compile(_DATE_OK)
_DATE_TAIL = re.compile(r"\d{1,2}" + _DATE_OK)
_GATE_SPLIT = re.compile(r"[\s\-_./+=:@%~?&#,\\]+")
_HEX_LENS = frozenset(list(range(7, 13)) + [32, 40, 64])
_DNS_WORDS = frozenset("net com org io dev local internal lan corp home arpa cloud app ai co".split())
_NUMERIC_NAMES = frozenset("pid ppid tid uid gid port seq rev revision count n line lines size bytes exit attempt retry retries ms "
                           "secs seconds epoch offset len length total num number version ver ttl age idx index rc returncode timeout wait delay duration "
                           "interval limit max min depth width height rows cols step steps page pages tries".split())


def _hex_id(seg, prev=""):
    """An exact hex id: 7-12, 32, 40 or 64 hex characters (17 after an 'i', an instance id) in one case that mix digits and
    letters. A digits-only run is a number, never an id."""
    n = len(seg)
    if not (n in _HEX_LENS or (n == 17 and prev.lower() == "i")) or not (seg.islower() or seg.isupper() or seg.isdigit()):
        return False
    return bool(re.fullmatch(r"[0-9a-fA-F]+", seg)) and any(c.isdigit() for c in seg) and any(c.isalpha() for c in seg)


_SHAPE_OF_LEN = {32: "h32", 40: "h40", 64: "h64", 17: "inst"}


def _id_shape(seg, prev=""):
    """(shape, id text) of an id piece, or None. Shapes: short (7-12 hex), h32, h40, h64, inst (i-<17 hex>), ulid. A word of
    the vocabulary glued to a hex id ('rbcca95bf8e2f', 'r' + 32 hex) is that hex id's shape."""
    if _hex_id(seg, prev):
        return _SHAPE_OF_LEN.get(len(seg), "short"), seg
    if _ULID_ANY.fullmatch(seg):
        return "ulid", seg
    for k in range(1, min(12, len(seg) - 6)):
        if (k >= 2 or seg[0] == "r") and seg[:k].lower() in _ID_WORDS and _hex_id(seg[k:]):  # one-letter prefix: only systemd's 'r'
            return _SHAPE_OF_LEN.get(len(seg) - k, "short"), seg[k:]
    return None


def _id_grammar(seg, prev=""):
    """The id grammar a piece is, or ''."""
    return "id" if _id_shape(seg, prev) else ""


# THE FIELD PROFILES. Each identity field has its OWN grammar: the id shapes it carries, alone (the whole value is that id) or
# beside other pieces, and for a hash-sized shape beside others the template the value must follow (`~` stands for the id).
# A grammar-valid id of a shape the field does not carry is opaque there: a 256-bit hex value is an invocation or a head, and
# a credential shape in an account, model, owner, repo, branch, host or task. An unknown label carries no ids at all. No
# credential-name list takes part: this is a positive table of what each field is.
_UNIT_SUFFIX = r"\.(?:service|scope|socket|timer|slice|mount|target|path)"
_ROLES = "verifier|reviewer|coder|codex|claude|worker|agent|seat"
_FILE_STEM = "evt|event|result|results|review|report|out|artifact|log|trace|journal|notes|dump"


def _prof(alone=(), beside=(), tmpl=None, ip=False, unit_name=False):
    return {"alone": frozenset(alone), "beside": frozenset(beside), "ip": ip, "unit_name": unit_name,
            "tmpl": {k: re.compile(v, re.I) for k, v in (tmpl or {}).items()}}


_UNIT_FORM = r"[\w.@+:-]*~[\w.@+:-]*" + _UNIT_SUFFIX
_STEM_FORM = r"(?:.*/)?(?:%s)[-_.]~(?:\.[a-z]{2,5})?" % _FILE_STEM
_PATH_PROFILE = _prof(beside=("short", "h32", "h40", "uuid"), tmpl={"short": _STEM_FORM, "h32": _STEM_FORM, "h40": _STEM_FORM,
                                                                      "uuid": r".*/~(?:/.*|\.[a-z]{2,5})?"})
_SESS_FORM = r"(?:sess|session|sid)[-_:]~"
_PROFILES = {
    "host": _prof(beside=("inst",), tmpl={"inst": r"i-~"}, ip=True),
    "unit": _prof(beside=("short", "h32", "uuid"), tmpl={"short": _UNIT_FORM, "h32": _UNIT_FORM, "uuid": _UNIT_FORM}, unit_name=True),
    "child": _prof(alone=("short",), beside=("short", "h32", "h40", "uuid"), tmpl={
        "short": _UNIT_FORM, "h32": r"child[-_.]~|" + _UNIT_FORM, "h40": r"child[-_.]~", "uuid": r"child[-_.]~|" + _UNIT_FORM}),
    "session": _prof(alone=("short", "h32", "uuid", "ulid"), beside=("short", "h32", "uuid", "ulid"), tmpl={
        "short": _SESS_FORM, "h32": _SESS_FORM, "uuid": _SESS_FORM, "ulid": _SESS_FORM}),
    "invocation": _prof(alone=("short", "h32", "h64", "uuid", "ulid"), beside=("short", "h32"), tmpl={
        "short": r"(?:inv|invocation)[-_:]~", "h32": r"(?:inv|invocation)[-_:]~"}),
    # a model, an effort, a repo and a host carry no id of a hash-like shape; an account, an owner and a branch carry one only
    # behind their own instance prefix (acct-<id>, r7-<id>, feat-<id>)
    "account": _prof(beside=("short", "uuid"), tmpl={k: r"(?:acct|account)[-_.]~" for k in ("short", "uuid")}),
    "owner": _prof(beside=("short",), tmpl={"short": r"(?:r7|rb|ctl|hermes|orch|aide|controller|acct)[-_.]~"}),
    "branch": _prof(beside=("short", "h32"), tmpl={k: r"(?:.*/)?(?:feat|feature|fix|hotfix|bug|wip|r7|rb)[-_]~" for k in ("short", "h32")}),
    "model": _prof(), "effort": _prof(), "repo": _prof(),
    "named": _prof(beside=("short", "h32"), tmpl={"short": r"(?:%s)[-_.]~" % _ROLES, "h32": r"(?:%s)[-_.]~" % _ROLES}),
    "task": _prof(alone=("ulid",), beside=("short", "h32", "uuid", "ulid"), tmpl={
        k: r"(?:task|wf|a|t)[-_]?~" for k in ("short", "h32", "uuid", "ulid")}),
    "path": _PATH_PROFILE,
}
_PROFILE_ALIAS = {"sess-id": "session", "current_owner": "owner", "reviewed_by": "owner", "consumer": "named", "alternate": "named",
                  "task_id": "task", "result": "path", "artifact": "path", "event": "path", "evidence-ref": "path", "ref": "path",
                  "target": "path"}
_NO_PROFILE = _prof()
_ANY_SHAPES = ("short", "h32", "h40", "h64", "uuid", "ulid", "inst")
_ANY_PROFILE = _prof(alone=_ANY_SHAPES, beside=_ANY_SHAPES, ip=True)  # the bare gate, no field: only a caller that names none gets it
_MAX_DIGITS_WITH_ID = 8  # beside an id grammar at most this many digits: an id plus fourteen digits is ~94 bits


def _profile(label):
    """The field profile for a label or field name (see THE FIELD PROFILES); strict (no ids) for an unknown one."""
    low = (label or "").lower().rsplit(".", 1)[-1]  # a field path (worker.unit, consumer.named) names its last key
    return _PROFILES.get(_PROFILE_ALIAS.get(low, low), _NO_PROFILE)


def _word(low, words):
    return (low in _ID_WORDS or low in words or low in _DNS_WORDS) and not _cred_name(low)


def _segment(low, words):
    """The number of vocabulary words (each at least two letters, at most four) a lower-case run splits into, or 0."""
    if len(low) < 4 or len(low) > 40:
        return 0
    best = [None] * (len(low) + 1)
    best[0] = 0
    for i in range(1, len(low) + 1):
        for j in range(max(0, i - 14), i - 1):
            if best[j] is not None and _word(low[j:i], words) and (best[i] is None or best[j] + 1 < best[i]):
                best[i] = best[j] + 1
    return best[-1] if best[-1] and best[-1] <= 4 else 0


def _compound(seg, words, st):
    """A mixed piece that reads as vocabulary joined with numbers ('wmbuild1663impl2', 'WF1663Impl', 'r7wfitfix2'): every
    alphabetic token is a vocabulary word (or splits into up to four of them), digits are bounded numbers, and at most ONE
    unlisted token of at most three letters ('wfr6') is allowed, charged to the budget."""
    toks = _TOKENS.findall(seg)
    if not toks or "".join(toks) != seg:
        return False
    unl = cost = digits = 0
    for t in toks:
        if t.isdigit():
            if _DATE_ID.fullmatch(t) or _DATE_TAIL.fullmatch(t):
                continue  # a calendar date, or a version digit or two glued to one ('r7wfr7' + '20261113')
            if len(t) > _MAX_DIGIT_PIECE:
                return False
            digits += len(t)
            continue
        low = t.lower()
        if _word(low, st["words"]) or _segment(low, st["words"]):
            continue
        if len(t) <= 3 and not _cred_name(low):
            unl += 1
            cost += len(t)
            continue
        return False
    if unl > 1:
        return False
    st["cost"] += cost
    st["digits"] += digits
    return True


def _piece(seg, prev, st):
    words = st["words"]
    low = seg.lower()
    if _word(low, words):
        return True
    if _TS_ID.fullmatch(seg) or _DATE_ID.fullmatch(seg):
        return True
    if seg.isdigit():
        if len(seg) > _MAX_DIGIT_PIECE:
            return False
        st["digits"] += len(seg)
        return True
    sh = _id_shape(seg, prev)
    if sh:
        st["ids"] += 1
        st["found"].append(sh)
        return True
    if not (seg.isascii() and seg.isalnum()):
        return False
    if _compound(seg, words, st):
        return True
    for w in sorted((x for x in set(_ID_WORDS) | set(words) if len(x) >= 3 and not _cred_name(x)), key=len, reverse=True):
        rest = seg[len(w):]
        if low.startswith(w) and 0 < len(rest) <= _MAX_SHORT and not _cred_name(rest):
            st["cost"] += len(rest)  # a vocabulary word with a short generated suffix ('tail1a2b3')
            return True
    if len(seg) <= _MAX_SHORT and not _cred_name(low):
        st["cost"] += len(seg)
        return True
    return False


def _name_value_ok(s):
    """An identity that carries `name=value` chunks ('pid=77'): the name is made of vocabulary words and the value of
    trusted plain pieces (digits, dates, a very short hex group, vocabulary words). 'pswd=hunter2x' is a pair, not an identity."""
    chunks = re.findall(r"([^=&?,#]*)=([^=&?,#]*)", s)
    if len(chunks) > 3:
        return False
    for name_, val_ in chunks:
        name = [x for x in _SPLIT.split(name_) if x]
        val = [x for x in _SPLIT.split(val_) if x]
        if not name or not all(_vocab(x) for x in name):
            return False
        if not all(_vocab(x) or (x.isdigit() and len(x) <= _MAX_DIGIT_PIECE) or _DATE_ID.fullmatch(x) or _SHORT_HEX.fullmatch(x)
                   for x in val):
            return False
    return True


def _vocab(seg):
    low = seg.lower()
    return low in _ID_WORDS or (low.rstrip("0123456789") in _ID_WORDS and len(low) - len(low.rstrip("0123456789")) <= 4
                                and not _cred_name(low))


_IPV4 = re.compile(r"(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)")
_MAX_IPV6_GROUPS = 4  # explicit groups of a compressed IPv6 literal (fe80::1, 2001:db8::1)
_IPV6_GROUP = re.compile(r"[0-9A-Fa-f]{1,4}")


def _ipv6(core):
    """An IPv6 literal: eight groups of at most four hex digits, with one '::' standing for one or more zero groups, an
    optional trailing IPv4. A compressed literal carries at most four explicit groups; a fully written one at most four
    non-zero groups (2001:db8:0:0:0:0:0:1), so no 128-bit random value passes as an address."""
    if core.count("::") > 1 or ":::" in core:
        return False
    head, _, tail = core.partition("::")
    parts = [x for x in head.split(":") if x != ""] if head else []
    tail_parts = [x for x in tail.split(":") if x != ""] if tail else []
    if "::" not in core and (core.startswith(":") or core.endswith(":")):
        return False
    groups = parts + tail_parts
    n = nonzero = 0
    for i, g in enumerate(groups):
        if i == len(groups) - 1 and "." in g:
            if not _IPV4.fullmatch(g):
                return False
            n += 2
            nonzero += 1
        elif _IPV6_GROUP.fullmatch(g):
            n += 1
            nonzero += int(g, 16) != 0
        else:
            return False
    if "::" in core:
        return len(groups) <= _MAX_IPV6_GROUPS and n <= 7
    return n == 8 and nonzero <= _MAX_IPV6_GROUPS


def _ip_literal(s):
    """An IP literal (IPv4 with an optional :port, or IPv6; an optional %zone of at most eight letters and digits; an
    optional user@): the exact grammar, so no free piece rides on it."""
    core = s.rsplit("@", 1)[-1]
    if "%" in core:
        core, zone = core.split("%", 1)
        if not re.fullmatch(r"[A-Za-z0-9]{1,8}", zone):
            return False
    if re.fullmatch(r"[0-9.]+:\d{1,5}", core):
        core = core.rsplit(":", 1)[0]
    return bool(_IPV4.fullmatch(core)) or (":" in core and _ipv6(core))


_UNIT_END = re.compile(r".*" + _UNIT_SUFFIX)


def _unit_name_segments(segs, whole, words):
    """The pieces of a systemd unit name that still need the gate. A unit may be NAMED for what it manages
    ('fleet-token-429-watch.service'): one strong credential word is a name word there, and only there, when the value ends in
    a unit suffix and every other piece is a closed-vocabulary word or a number of at most three digits, so nothing unlisted
    rides on it ('token-<anything>.service' keeps the word and fails the gate)."""
    named = [x for x in segs if x.lower() in _STRONG_WORDS]
    if len(named) != 1 or not _UNIT_END.fullmatch(whole.strip()):
        return segs
    rest = [x for x in segs if x is not named[0]]
    if all(_word(x.lower(), words) or (x.isdigit() and len(x) <= 3) for x in rest):
        return rest
    return segs


def _gate_values(vals, words=frozenset(), max_ids=1, profile=None):
    """True when every piece of every value in `vals` is trusted and the values together stay inside the budgets (see THE ONE
    TRUST GATE), and every id the values carry is of a shape the field's `profile` names, in the form (alone, or beside
    other pieces and following the shape's template) the profile allows (see THE FIELD PROFILES). Every output path passes its
    field's profile (a row field: none, so no ids); only a direct call that names no profile gets the bare gate.
    The caller's `words` extend the closed vocabulary for one field."""
    prof = profile or _ANY_PROFILE
    st = {"words": words, "cost": 0, "digits": 0, "ids": 0, "found": []}
    npieces = 0
    for s in vals:
        if not isinstance(s, str) or not s or len(s) > 512:
            return False
        if "=" in s and not _name_value_ok(s):
            return False
        if prof["ip"] and _ip_literal(s):
            continue
        st["found"] = []
        for m in _UUID.finditer(s):
            st["found"].append(("uuid", m.group(0)))
        st["ids"] += len(st["found"])
        whole = s
        s = _UUID.sub(".", s)
        s = _ISO_TS.sub(".", s)
        segs = [x for x in _GATE_SPLIT.split(s) if x]
        if prof["unit_name"]:
            segs = _unit_name_segments(segs, whole, words)
        npieces += len(segs)
        prev = ""
        for i, seg in enumerate(segs):
            nxt = segs[i + 1] if i + 1 < len(segs) else ""
            if len(seg) == 1 and seg.isalpha() and any(c.isdigit() for c in prev) and any(c.isdigit() for c in nxt):
                prev = seg
                continue  # a single letter between two numbered pieces ('r7-x-20261113')
            if not _piece(seg, prev, st):
                return False
            prev = seg
        for shape, text in st["found"]:
            if len(vals) == 1 and whole.strip() == text:
                if shape not in prof["alone"]:
                    return False
                continue
            rx = prof["tmpl"].get(shape)
            if shape not in prof["beside"] or (rx is not None and not rx.fullmatch(whole.replace(text, "~", 1))):
                return False
    return (npieces <= _MAX_PIECES and st["cost"] <= _MAX_UNLISTED and st["digits"] <= _MAX_DIGITS_TOTAL
            and st["ids"] <= max_ids and not (st["ids"] and (st["cost"] > _MAX_UNLISTED_WITH_ID or st["digits"] > _MAX_DIGITS_WITH_ID)))


def _trusted_pieces(s, words=frozenset(), max_ids=1, profile=None):
    """True when a grammar-valid identity passes the one trust gate under the field's profile (see THE ONE TRUST GATE). The
    host grammar is not an exemption: a DNS label is a piece like any other. No credential-name list decides here: a credential
    word is never a vocabulary word, so it is unlisted material inside the budget, and the ident() layers that look for one
    only refuse more."""
    return _gate_values([s], words, max_ids, profile)


def _plain_name(seg):
    return _idplain(seg) and not _ID_PIECE.fullmatch(seg) or bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9]{0,7}", seg) and _idplain(seg))


def _id_pieces_ok(s):
    """True when every piece of an identity reads as an id piece, no credential word is joined to a non-trivial piece, and
    a part before '@' (a user or a systemd template name) is plain names only, with no ':password'."""
    segs = [x for x in _SPLIT.split(s) if x]
    if _cred_marked(segs):
        return False
    if "@" in s:
        left = s.split("@", 1)[0]
        if ":" in left or any(c in left for c in "?&#,") or not all(_plain_name(x) for x in _SPLIT.split(left) if x):
            return False
    return all(_piece_ok(seg) for seg in segs)


def _run_repl(text):
    def repl(m):
        run = m.group(0)
        core = run.rstrip(".=")
        tail = run[len(core):]
        if not (any(c.isdigit() for c in core) and any(c.isalpha() for c in core)):
            return run
        if re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", core) and _DIGEST_FIELD.search(text[max(0, m.start() - 24):m.start()]):
            return run  # a git or sha256 digest in a head/sha/digest field is an identifier, not a secret
        return (REDACTED + tail) if _random_looking(core) else run
    return repl


_REDACTIONS = [
    # PEM private/secret key blocks (a missing END line redacts to the end of the text)
    (re.compile(r"-----BEGIN [A-Z0-9 ]*(?:PRIVATE|SECRET)[A-Z0-9 ]*-----.*?(?:-----END [A-Z0-9 ]*-----|\Z)", re.S), REDACTED),
    # URL userinfo with a password: scheme://user:pass@host, the password may itself hold @ or / (everything up to the
    # last @ of the unbroken run is redacted; both runs are length-bounded to keep matching linear on hostile input)
    (re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/@:\"'<>]{0,128}:[^\s\"'<>]{0,512}@"), r"\1" + REDACTED + "@"),
    # URL userinfo without a password: scheme://token@host
    (re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/@:]{0,256}@"), r"\1" + REDACTED + "@"),
    # Cookie / Set-Cookie headers: the whole rest of the line is the credential
    (re.compile(r"(?i)((?<![\w-])(?:set-)?cookie2?[\"']?\s*[:=]\s*)" + _NOT_DONE + r"[^\r\n]+"), r"\1" + REDACTED),
    # Authorization header value (Basic/Bearer/Digest/Token scheme plus credential)
    (re.compile(r"(?i)(\bauthorization[\"']?\s*" + _SEP + r"\s*[\"']?)" + _NOT_DONE +
                r"(?:(?:basic|bearer|digest|token|negotiate)\s+)?[^\s\"',;)]+"), r"\1" + REDACTED),
    # a multi-parameter scheme (Digest username=..., response=...) keeps no parameter
    (re.compile(r"(?i)(\bauthorization[\"']?\s*" + _SEP + r"\s*[\"']?(?:digest|negotiate|oauth|hmac)\s+)" + _NOT_DONE + r"[^\r\n]+"),
     r"\1" + REDACTED),
    (re.compile(r"(?i)\b(bearer)(?:\s*" + _SEP + r"\s*|\s+)" + _NOT_DONE + r"[^\s\"',;)]+"), r"\1 " + REDACTED),
    # curl -u / --user user:password
    (_USER_FLAG, _user_flag),
    # name = value / name: value (JSON, YAML, env, headers, query strings): the name holds a credential word
    (None, _redact_named_values),
    # command-line flag whose name holds a credential word, value as the next word: --password VALUE, -token VALUE
    (None, _redact_flag_values),
    # password short flags that belong to a named command: sshpass -p, mysql -p, unzip -P, 7z -p
    (None, _redact_command_pw_flags),
    (re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{3,}"), REDACTED),
    (re.compile(r"sk-(?:ant|proj|svcacct|admin|or)-[A-Za-z0-9_-]{8,}"), REDACTED),  # vendor-tagged keys, even glued to a word
    # provider token prefixes (each needs a long enough body, so ordinary words are left alone)
    (re.compile(r"(?:"
                r"(?:AKIA|ASIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ABIA|ACCA)[0-9A-Z]{12,}"            # AWS key ids
                r"|gh[pousr]_[A-Za-z0-9]{8,}|github_pat_[A-Za-z0-9_]{8,}"                           # GitHub
                r"|xox[a-z]-[A-Za-z0-9-]{8,}|xoxe\.xox[a-z]-[A-Za-z0-9-]{8,}|xapp-[A-Za-z0-9-]{8,}"  # Slack
                r"|ya29\.[A-Za-z0-9._-]{8,}|AIza[0-9A-Za-z_-]{20,}|GOCSPX-[A-Za-z0-9_-]{8,}"        # Google
                r"|npm_[A-Za-z0-9]{8,}"                                                             # npm
                r"|gl(?:pat|ptt|rt|dt|oas|ft|imt|agent|cbt|soat|ffct)-[A-Za-z0-9_-]{8,}"           # GitLab
                r"|(?:sk|rk|pk)_(?:live|test)_[A-Za-z0-9]{8,}|whsec_[A-Za-z0-9]{8,}"               # Stripe
                r"|SG\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}|hf_[A-Za-z0-9]{16,}|pypi-[A-Za-z0-9_-]{16,}"
                r"|dckr_pat_[A-Za-z0-9_-]{8,}|shp(?:at|ca|pa|ss)_[A-Za-z0-9]{8,}|dop_v1_[A-Za-z0-9]{8,}"
                r"|(?:SK|AC)[0-9a-f]{32}|key-[0-9a-f]{32}|dapi[0-9a-f]{32}"                         # Twilio, Mailgun, Databricks
                r"|glsa_[A-Za-z0-9_]{16,}|hvs\.[A-Za-z0-9_-]{16,}|hv[bs]\.[A-Za-z0-9_-]{16,}"       # Grafana, Vault
                r"|secret_[A-Za-z0-9]{16,}|ntn_[A-Za-z0-9]{16,}|lin_api_[A-Za-z0-9]{16,}"          # Notion, Linear
                r"|sntrys_[A-Za-z0-9+/=_-]{16,}|PMAK-[A-Za-z0-9-]{16,}|sq0[a-z]{3}-[A-Za-z0-9_-]{16,}"  # Sentry, Postman, Square
                r"|EAA[A-Za-z0-9]{20,}|AGE-SECRET-KEY-1[A-Z0-9]{16,}|fo1_[A-Za-z0-9_-]{16,}"       # Facebook, age, Fly
                r"|\d{6,12}:AA[A-Za-z0-9_-]{20,}"                                                  # Telegram bot token
                r"|HRKU-[A-Za-z0-9_-]{20,}"                                                         # Heroku
                r")"), REDACTED),
    (re.compile(r"(?<![/:])1//0[A-Za-z0-9_-]{20,}"), REDACTED),                          # Google refresh token
    # webhook URLs carry their secret in the path
    (re.compile(r"(?i)hooks\.slack\.com/services/[A-Za-z0-9/_-]{8,}|discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{8,}"), REDACTED),
    (re.compile(r"eyJ(?:(?!eyJ)[A-Za-z0-9_-]){4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"), REDACTED),
]


_ESC = re.compile(r"\\(?:u([0-9a-fA-F]{4})|([\"'\\/bfnrt]))")
_ESC_MAP = {"b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t"}
_PCT = re.compile(r"%([0-9a-fA-F]{2})")
_SURR = re.compile("[\ud800-\udbff][\udc00-\udfff]")


def _unescape(text):
    """The text with JSON string escapes decoded to a fixpoint (at most four layers): \\" \\\\ \\/ \\n \\uXXXX. A
    credential pair inside a string-encoded JSON value reads as the pair it is."""
    for _ in range(4):
        if "\\" not in text:
            break
        t = _ESC.sub(lambda m: chr(int(m.group(1), 16)) if m.group(1) else _ESC_MAP.get(m.group(2), m.group(2)), text)
        t = _SURR.sub(lambda m: chr(0x10000 + ((ord(m.group(0)[0]) - 0xD800) << 10) + (ord(m.group(0)[1]) - 0xDC00)), t)
        if t == text:
            break
        text = t
    return text


def _pct_decode(text):
    return _PCT.sub(lambda m: chr(int(m.group(1), 16)), text) if "%" in text else text


def _layers(text):
    for rx, rep in _REDACTIONS:
        text = rep(text) if rx is None else rx.sub(rep, text)
    return text


def _via_views(text, layers):
    """`layers` applied to the text and to its decoded views (JSON string escapes, then percent-escapes): when a decoded view
    shows something the layers hide, the deepest decoded view with it hidden is the result."""
    best = layers(text)
    view = text
    for dec in (_unescape, _pct_decode):
        d = dec(view)
        if d == view:
            continue
        view = d
        r = layers(view)
        if r != view:
            best = r
    return best


def redact_credentials(text):
    """The credential layers of redact(): everything except the random-token run rule and the free-text trust gate. A value
    this leaves unchanged carries no credential name, flag or known credential shape. The layers run on the text and on
    its decoded views (JSON string escapes, then percent-escapes): when a decoded view shows a credential the text hides,
    the deepest decoded view with its credential hidden is the result, so an escaped, \\u-encoded or string-encoded pair is
    hidden like a plain one."""
    if not isinstance(text, str):
        return text
    return _via_views(text, _layers)


# FREE-TEXT TRUST GATE. Free text is untrusted narrative. The value of any `name=value`, `name: value`, `"name": "value"`,
# `?name=value` or `--name value` pair is hidden unless the value is a closed-vocabulary or plain value (a small number, a
# time, a state word, a bracketed opaque ref) or the name is a schema key whose value validates as that field's identity
# and is trusted (keep()). The decision never asks whether the NAME is a credential name: the credential-name layers above
# remain, as an extra layer that hides more, and are not what lets a value print. A credential word joined to a value
# without a separator ('token-<value>') is hidden as a composite.
_FREE_CACHE = []
_ISO_TS = re.compile(r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?")
_CLOCK = re.compile(r"\d{1,2}:\d{2}(?::\d{2})?")
_FIELD_KIND = {"host": "host", "unit": "ident", "child": "ident", "session": "ident", "invocation": "ident",
               "account": "ident", "model": "ident", "effort": "ident", "named": "ident", "alternate": "ident",
               "owner": "ident", "current_owner": "ident", "reviewed_by": "ident", "repo": "ident", "branch": "ident",
               "task_id": "ident", "artifact": "path", "event": "path", "ref": "path", "target": "path",
               "head": "hex", "sha": "hex", "sha1": "hex", "sha256": "hex", "digest": "hex", "commit": "hex", "rev": "hex",
               "revision": "hex", "oid": "hex", "hash": "hex"}


_SRC_STRING = re.compile(r'"((?:[^"\\\n]|\\.)*)"')
_TRIPLE = re.compile(r'"""(?:.|\n)*?"""')


def _tool_words():
    """The words of the tool's own sentences (the double-quoted string literals of the three scripts, docstrings left out
    and anything shaped like a pattern skipped): public by construction, read from the code so the set cannot drift. A value
    that is a word the tool itself writes is plain vocabulary, never a secret."""
    words = set()
    here = os.path.dirname(os.path.abspath(__file__))
    for fn in ("envelope_validate.py", "recommend.py", "queue_adapter.py"):
        try:
            with open(os.path.join(here, fn), encoding="utf-8") as fh:
                src = fh.read()
        except (OSError, ValueError):
            continue
        for lit in _SRC_STRING.findall(_TRIPLE.sub("", src)):
            if not re.search(r"[\[\]\\^${}|]", lit):
                words.update(re.findall(r"(?<![a-z])[a-z]{2,16}(?![a-z])", lit.lower()))
    return words


def _free_words():
    if not _FREE_CACHE:
        w = set(_ID_WORDS) | _tool_words()
        for k in _schema_keys():
            w.update(x for x in re.split(r"[^a-z0-9]+", k.lower()) if x)
        for grp in (STATES, SHAPES, EFFECTS):
            for x in grp:
                w.update(y for y in re.split(r"[^a-z0-9]+", x.lower()) if y)
        w.update("unknown none null true false yes no ok text json system fast slow normal quick full partial strict lenient debug "
                 "verbose quiet auto manual dry live safe on off eth lo wlan root temp".split())
        _FREE_CACHE.append(frozenset(w))
    return _FREE_CACHE[0]


_FREE_SPLIT = re.compile(r"[\s\-_./+=:@%~?&#,\\]+")
_FLAG_TOKEN = re.compile(r"--?[A-Za-z][\w-]*")
_FREE_UNLISTED = 4  # the most characters of unlisted material (pieces of at most three characters) one free value may carry
_FREE_SHORT = 3
_FREE_PIECES = 2  # the most unlisted pieces one free value may carry
_FREE_WORD_RUN = 3  # vocabulary words joined by '-' or '_' in one free value: fewer than this
_FREE_DIGITS = 2  # the longest number that reads as a small count under a name outside the closed numeric list
_CRED_NEXT_OK = frozenset("required missing unset empty rotated rotation expired expires invalid valid stored hidden masked changed "
                          "present absent unknown none null true false ok ready set refresh refreshed service timer file path env "
                          "variable store vault cache check reader fetch sync watch monitor mismatch rejected accepted denied "
                          "granted failed not no yes the a an this that it all any each one two used left remaining count total".split())
_PORT_NAMES = frozenset(["p", "publish", "port", "ports", "expose"])
_NUMERIC_PAIRS = frozenset(["exit_code", "status_code", "return_code", "http_code"])
_NUMERIC_SUFFIX = ("count", "size", "bytes", "seconds", "lines", "total", "length", "number", "version", "index", "retries", "attempts",
                   "timeout", "duration")


def _numeric_name(name):
    """True for a name of the closed list of numeric field names (a pid, a port, a line, a count, a timeout, an exit code): the
    only names under which a number prints. A name outside the list ('mfa', 'mypass', 'code', 'foo') hides any number."""
    toks = [t.lower() for t in re.split(r"[^A-Za-z0-9]+|(?<=[a-z0-9])(?=[A-Z])", name) if t]
    if not toks:
        return False
    last = toks[-1]
    return (last in _NUMERIC_NAMES or (len(toks) > 1 and toks[-2] + "_" + last in _NUMERIC_PAIRS)
            or any(last.endswith(w) and len(last) > len(w) for w in _NUMERIC_SUFFIX))


def _benign_value(raw, name="", cred_context=False):
    """True for a value that reads as a plain closed-vocabulary value, so there is nothing to hide: a small number, a time, a
    state or vocabulary word, a bracketed opaque ref, another flag. The gate is the closed vocabulary (_free_words) plus
    numbers under a name of the closed list of numeric field names (_numeric_name: at most ten digits; at most two digits under
    any other name; two after a credential word), and at most four characters of unlisted material in at most two pieces; no more
    than two vocabulary words joined by '-' or '_'. A plain word that is not in the vocabulary ('sunshine', 'dragon'), a mixed
    piece, a number outside the closed list ('mfa=4821', 'code=1234') and any longer unlisted run are hidden, whatever the NAME
    is: no name is exempt and the name decides nothing but which numbers are counts."""
    if len(raw) > 128:
        return False  # a plain value is short
    v = raw.strip("\"'`").rstrip(".:")
    if not v or v.startswith("\ue002"):
        return True
    if v.startswith("["):
        return v.startswith(("[opaque", "[REDACTED"))
    if _ISO_TS.fullmatch(v) or _CLOCK.fullmatch(v) or _FLAG_TOKEN.fullmatch(v):
        return True
    if cred_context:  # right after a credential word only a state word may follow (the next-word check of _redact_cred_prose)
        return all(x == "" or x.lower() in _CRED_NEXT_OK or (x.isdigit() and len(x) <= 2) for x in _FREE_SPLIT.split(v))
    numeric = _numeric_name(name)
    limit = 10 if numeric else _FREE_DIGITS  # long numbers print only under a name of the closed numeric list
    if re.fullmatch(r"\d{1,5}:\d{1,5}", v) and name.lower().lstrip("-") in _PORT_NAMES:
        return True  # a port mapping (docker -p 8080:80)
    cost = pieces = 0
    run = 0  # vocabulary words joined by '-' or '_'
    prev_word = False  # the previous piece is a closed-vocabulary word: 'WF-1663', 'task-1663' are ids, not a secret number
    parts = re.split(r"([\s\-_./+=:@%~?&#,\\]+)", v)
    for i in range(0, len(parts), 2):
        x, sep = parts[i], (parts[i - 1] if i else "")
        if not x:
            continue
        low = x.lower()
        stripped = low.rstrip("0123456789")
        was_word, prev_word = prev_word, low in _free_words()
        run = run + 1 if prev_word and sep and not sep.strip("-_") else (1 if prev_word else 0)
        if run >= _FREE_WORD_RUN:
            return False  # three or more vocabulary words joined by '-' or '_' read as a passphrase
        if x.isdigit():
            if len(x) > (_MAX_DIGIT_PIECE if was_word else limit):
                return False
        elif low in _free_words() or (stripped in _free_words() and 0 < len(low) - len(stripped) <= 3) or _DATE_ID.fullmatch(x):
            continue
        elif _TS_ID.fullmatch(x):
            continue
        elif len(x) <= 2 or (len(x) <= _FREE_SHORT and x.isalnum()):
            cost += len(x)
            pieces += 1
        else:
            return False
    return cost <= _FREE_UNLISTED and pieces <= _FREE_PIECES


def _trusted_field_value(name, raw):
    """True when `name` is a schema key and `raw` validates as that field's identity and is trusted (see keep())."""
    kind = _FIELD_KIND.get(re.split(r"[.\-]", name)[-1].lower())
    core = raw.rstrip(".:")
    if kind == "hex":
        return bool(re.fullmatch(r"[0-9a-fA-F]{4,64}", core)) and not core.isdigit()
    return bool(kind) and keep(kind, core, re.split(r"[.\-]", name)[-1].lower()) != core


def _open_structure(text, e):
    k = e
    while k < len(text) and text[k] in " \t\r\n":
        k += 1
    return k if k < len(text) and text[k] in "[{" and not text.startswith(("[opaque", REDACTED), k) else None


def _redact_free_pairs(text, protect):
    """name SEP value in free text (see FREE-TEXT TRUST GATE). Linear: each separator is looked at once and a value is read
    with a bound; a quoted value that does not close within the bound is hidden to the end of the line."""
    out, pos, seen = [], 0, 0
    for m in _SEP_AT.finditer(text):
        if m.start() < max(pos, seen):
            continue
        j = m.start()
        while j > pos and text[j - 1] in _NAME_CHARS:
            j -= 1
        if j == m.start():
            continue
        e = m.end()
        if text.startswith(REDACTED, e) or text.startswith("\ue002", e):
            continue
        if m.group(0) == ":" and (text.startswith("//", e) or (text[m.start() - 1].isdigit() and text[e:e + 1].isdigit())):
            continue  # a URL scheme, a clock time, a port or a ratio
        k = _open_structure(text, e)
        if k is not None:
            end = _structure_end(text, e, j)
            if end is not None:
                out.append(text[pos:e] + REDACTED)
                pos = end
                continue
        v = _VALUE.match(text, e, e + 400)
        if v is None:
            if text[e:e + 1] in ("\"", "'"):
                nl = text.find("\n", e)
                out.append(text[pos:e] + REDACTED)
                pos = len(text) if nl == -1 else nl
            continue
        raw = v.group(0)
        seen = v.end()  # a value is read once: separators inside it belong to it
        if _benign_value(raw, text[j:m.start()]) and not (len(raw) >= 400 and v.end() < len(text) and text[v.end()] not in " \t\r\n,;&)\"']}"):
            continue
        if raw[:1] not in ("\"", "'") and _trusted_field_value(text[j:m.start()], raw):
            out.append(text[pos:e] + protect(raw.rstrip(".:")))
            pos = e + len(raw.rstrip(".:"))
            continue
        out.append(text[pos:e] + REDACTED)
        pos = v.end()
    out.append(text[pos:])
    return "".join(out)


def _redact_free_flags(text, protect):
    """--flag VALUE in free text: the value is hidden unless it is a plain closed-vocabulary value, whatever the flag is."""
    out, pos, seen = [], 0, 0
    for m in _FLAG_AT.finditer(text):
        if m.start() < max(pos, seen) or text.startswith("\ue002", m.end()):
            continue
        v = _VALUE.match(text, m.end(), m.end() + 400)
        if v is None:
            continue
        seen = v.end()
        if _benign_value(v.group(0), m.group('flag')) and not (len(v.group(0)) >= 400 and v.end() < len(text) and text[v.end()] not in " \t\r\n"):
            continue
        out.append(text[pos:m.end()] + REDACTED)
        pos = v.end()
    out.append(text[pos:])
    return "".join(out)


_COMPOSITE = re.compile(r"(?<![A-Za-z0-9\ue002])[A-Za-z0-9][A-Za-z0-9._-]{3,200}")
_GLUE_WORDS = ("tokens", "token", "secrets", "secret", "bearer", "apikey", "passwd", "password", "privkey", "passphrase",
               "passcode", "credentials", "credential")


def _glued_credential(segs):
    """A credential word joined to a value in one token: beside a non-trivial piece ('token-<v>', 'secret_run_<v>'), glued to
    a hex or digit tail, or glued to a long run that is not a word ('tokenArYYbbah')."""
    if _cred_marked(segs):
        return True
    for seg in segs:
        low = seg.lower()
        for w in _GLUE_WORDS:
            if low.startswith(w) and len(low) - len(w) >= 6:
                rest = seg[len(w):]
                if any(c.isdigit() for c in rest) or any(c.isupper() for c in rest) or (len(rest) >= 9 and not _vocab(rest)):
                    return True
    return False


_GLUE_HINT = re.compile(r"(?i)tok|secret|pass|pw|pat|bearer|cred|apikey|privkey|api")


def _redact_composites(text):
    if not _GLUE_HINT.search(text):
        return text  # no credential word anywhere: nothing can be glued to one

    def repl(m):
        tok = m.group(0)
        core = tok.rstrip(".-_")
        if _glued_credential([x for x in _SPLIT.split(core) if x]):
            return REDACTED + tok[len(core):]
        return tok
    return _COMPOSITE.sub(repl, text)


_CRED_PROSE = re.compile(
    r"(?i)(?<![A-Za-z0-9_.-])(?P<w>pass|passwd|password|passwords|passphrase|passcode|pwd|pw|pswd|pwrd|pin|otp|token|tokens|secret|"
    r"secrets|credential|credentials|apikey|passkey)(?P<mid>(?:\s+(?:is|are|was|were|to|with|as|be|set|use|using|[:=]))*\s+)"
    r"(?P<v>[^\s,;)\]}\"'\ue002\[]+)")


def _redact_cred_prose(text):
    """A credential word followed, in prose with no separator, by its value ('the password is sunshine', 'pass swordfish',
    'my pin 482917'): the next word is hidden unless it is a closed-vocabulary word (no number longer than two digits)."""
    if not _CRED_PROSE.search(text):
        return text

    def repl(m):
        if _benign_value(m.group("v"), "", True):
            return m.group(0)
        return m.group("w") + m.group("mid") + REDACTED
    return _CRED_PROSE.sub(repl, text)


def _free_layers(protect):
    return lambda t: _redact_composites(_redact_cred_prose(_redact_free_flags(_redact_free_pairs(t, protect), protect)))


def redact(text, keep_marks=False):
    """Replace credential-shaped values in any output string: PEM key blocks, URL userinfo, Cookie / Authorization /
    Bearer values, every name=value, name: value, "name": "value", --flag value, -u user:pass and query parameter whose
    name holds a credential word (token, key, secret, pass, auth, cookie, session, signature, sig, credential, api,
    private, dsn, cert, ...), the named provider token shapes, webhook URLs, JWTs, and finally any >= 20 character run of
    token characters that mixes letters and digits and is not a known-safe identifier (a digest in a sha/head field,
    a timestamp, a unit name, a path, a branch)."""
    if not isinstance(text, str):
        return text
    held = []

    def hold(m):
        held.append(m.group(1))
        return "\ue002%s%d\ue003" % (_NONCE, len(held) - 1)
    text = _MARK_RX.sub(hold, text)  # validated identity spans (see keep()) skip the run rule only
    text = redact_credentials(text)

    def protect(v):
        held.append(v)
        return "\ue002%s%d\ue003" % (_NONCE, len(held) - 1)
    text = _via_views(text, _free_layers(protect))
    text = _RUN.sub(_run_repl(text), text)
    if keep_marks:  # a trusted span stays marked for the tool's own later redact_tool() pass, which strips the marks
        return _HOLD_RX.sub(lambda m: _MARK_OPEN + held[int(m.group(1))] + _MARK_CLOSE if int(m.group(1)) < len(held) else "", text)
    return _HOLD_RX.sub(lambda m: held[int(m.group(1))] if int(m.group(1)) < len(held) else "", text)


def redact_tool(text):
    """redact() for a line the tool composed itself ('CODE path: message', a usage line): every envelope value in it already
    passed its field gate (show / opaque / safe_key), so the free-text trust gate, which reads 'path: message' as a pair, is
    not applied; the credential layers and the run rule are."""
    if not isinstance(text, str):
        return text
    held = []

    def hold(m):
        held.append(m.group(1))
        return "\ue002%s%d\ue003" % (_NONCE, len(held) - 1)
    text = _MARK_RX.sub(hold, text)
    text = redact_credentials(text)
    text = _RUN.sub(_run_repl(text), text)
    return _HOLD_RX.sub(lambda m: held[int(m.group(1))] if int(m.group(1)) < len(held) else "", text)


def safe_text(text, encoding="utf-8"):
    """text that the given encoding can always carry: a lone surrogate or any unencodable character is written as a
    backslash escape (\\ud800), never an exception."""
    return text.encode(encoding, "backslashreplace").decode(encoding)


def emit(text="", end="\n"):
    """print() that never raises on unencodable text: the one writer for every script output line."""
    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
    try:
        "".encode(enc)
    except LookupError:
        enc = "utf-8"
    sys.stdout.write(safe_text(text, enc) + end)


def scrub(v):
    """redact_tool() applied to every string inside a JSON-shaped value: envelope free text passes redact() (the trust gate)
    where it enters the output, and every identity or row field passes show() or the adapter's field gate."""
    if isinstance(v, str):
        return redact_tool(v)
    if isinstance(v, list):
        return [scrub(x) for x in v]
    if isinstance(v, dict):
        # a credential-named key hides its whole value, whatever structure it has (string, list, object, number)
        return {k: (REDACTED if isinstance(x, (str, list, dict, int, float)) and not isinstance(x, bool)
                    and isinstance(k, str) and _cred_name(k) and not (isinstance(x, str) and is_unknown(x)) else scrub(x))
                for k, x in v.items()}
    return v


def load_json_text(txt):
    try:
        return json.loads(txt, object_pairs_hook=_pairs)
    except RecursionError:
        raise ValueError("JSON nesting too deep")


def find_dups(obj, path="$"):
    """Paths of objects that carry a repeated key; such input is ambiguous and is refused. Iterative (an explicit stack,
    paths rendered only for a hit), so nesting depth never reaches the interpreter's recursion limit."""
    out = []
    stack = [(obj, (None, path))]
    while stack:
        node, link = stack.pop()
        if isinstance(node, dict):
            if getattr(node, "dups", ()):
                out.append("%s (%s)" % (_render_path(link), ",".join(safe_key(k) for k in node.dups)))
            kids = [(v, (link, ".%s" % safe_key(k))) for k, v in node.items()]
        elif isinstance(node, list):
            kids = [(v, (link, "[%d]" % i)) for i, v in enumerate(node)]
        else:
            continue
        stack.extend(reversed(kids))
    return out


def _render_path(link):
    parts = []
    while link is not None:
        parts.append(link[1])
        link = link[0]
    return "".join(reversed(parts))


def _schema_keys():
    """Every key name the schema defines (top level, sub-object fields, evidence fields): the only key names printed."""
    keys = set(REQUIRED_TOP) | set(OPTIONAL_TOP) | set(SUB) | set(EVIDENCE_OPTIONAL) | {"ref", "task_id", "revision", "observed_at"}
    for spec in SUB.values():
        keys |= set(spec)
    for opt in SUB_OPTIONAL.values():
        keys |= set(opt)
    return frozenset(keys)


def safe_key(k):
    """A JSON key as it may appear in a finding. The schema is known: a key it defines prints, every other key is an
    opaque ref, whatever it looks like. Key names come from the envelope and are never trusted to print."""
    if isinstance(k, str) and k in _schema_keys():
        return k
    return opaque("key", k)


def load_json_file(path):
    with open(path) as fh:
        return load_json_text(fh.read())


def parse_ts(v):
    """datetime (aware) or None for UNKNOWN; raises ValueError for malformed."""
    if v == UNKNOWN:
        return None
    if not isinstance(v, str):
        raise ValueError("not a string")
    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp lacks an offset")
    try:
        return dt.astimezone(timezone.utc)
    except OverflowError:
        raise ValueError("timestamp out of range")


def _kind_ok(kind, v):
    if kind == "s":
        return isinstance(v, str) and v != ""
    if kind == "t":
        return isinstance(v, str) and v != ""
    if kind == "i":
        return isinstance(v, int) and not isinstance(v, bool)
    if kind == "b":
        return isinstance(v, bool)
    if kind == "tri":
        return isinstance(v, bool) or v == UNKNOWN
    if kind == "sn":
        return v is None or (isinstance(v, str) and v != "")
    if kind == "in":
        return v is None or (isinstance(v, int) and not isinstance(v, bool))
    if kind == "e":
        return v in EFFECTS
    return False


def _shape(d):
    out = []
    for k in REQUIRED_TOP:
        if k not in d:
            out.append(finding("SCHEMA_MISSING", k, "required field missing"))
    for k in d:
        if k not in REQUIRED_TOP and k not in OPTIONAL_TOP:
            out.append(finding("UNKNOWN_KEY", safe_key(k), "field not in schema"))
    if d.get("schema", SCHEMA_ID) != SCHEMA_ID:
        out.append(finding("SCHEMA_ENUM", "schema", "expected " + SCHEMA_ID))
    for k, kind in (("parent", "s"), ("task_id", "s"), ("revision", "i"), ("current_owner", "s"),
                    ("next_action", "s"), ("declared_complete", "b"), ("owner_reachable", "tri")):
        if k in d and not _kind_ok(kind, d[k]):
            out.append(finding("SCHEMA_TYPE", k, "wrong type or empty"))
    if isinstance(d.get("task_id"), str) and is_unknown(d["task_id"]):
        out.append(finding("SCHEMA_TYPE", "task_id", "task id is a placeholder: no task is named"))
    if isinstance(d.get("revision"), int) and not isinstance(d.get("revision"), bool) and d["revision"] < 0:
        out.append(finding("SCHEMA_TYPE", "revision", "negative"))
    if "state" in d and d["state"] not in STATES:
        out.append(finding("SCHEMA_ENUM", "state", "not one of " + ",".join(STATES)))
    if "work_shape" in d and d["work_shape"] not in SHAPES:
        out.append(finding("SCHEMA_ENUM", "work_shape", "not one of " + ",".join(SHAPES)))
    for k in ("approved_ac_refs", "coverage_gaps"):
        if k in d and not (isinstance(d[k], list) and all(isinstance(x, str) and x for x in d[k])):
            out.append(finding("SCHEMA_TYPE", k, "must be a list of non-empty strings"))
    for k, spec in SUB.items():
        if k not in d:
            continue
        o = d[k]
        if not isinstance(o, dict):
            out.append(finding("SCHEMA_TYPE", k, "must be an object"))
            continue
        for f, kind in spec.items():
            if f not in o:
                out.append(finding("SCHEMA_MISSING", k + "." + f, "required field missing"))
            elif not _kind_ok(kind, o[f]):
                code = "SCHEMA_ENUM" if kind == "e" else "SCHEMA_TYPE"
                out.append(finding(code, k + "." + f, "wrong type, value or empty"))
        for f in o:
            if f not in spec and f not in SUB_OPTIONAL.get(k, []):
                out.append(finding("UNKNOWN_KEY", k + "." + safe_key(f), "field not in schema"))
            elif (k + "." + f) in OPTIONAL_KIND and not _kind_ok(OPTIONAL_KIND[k + "." + f], o[f]):
                out.append(finding("SCHEMA_TYPE", k + "." + f, "wrong type or empty"))
    ev = d.get("evidence")
    if "evidence" in d:
        if not isinstance(ev, list):
            out.append(finding("SCHEMA_TYPE", "evidence", "must be a list"))
        else:
            for i, e in enumerate(ev):
                p = "evidence[%d]" % i
                if not isinstance(e, dict):
                    out.append(finding("SCHEMA_TYPE", p, "must be an object"))
                    continue
                for f, kind in (("ref", "s"), ("task_id", "s"), ("revision", "i"), ("observed_at", "t")):
                    if f not in e:
                        out.append(finding("SCHEMA_MISSING", p + "." + f, "required field missing"))
                    elif not _kind_ok(kind, e[f]):
                        out.append(finding("SCHEMA_TYPE", p + "." + f, "wrong type or empty"))
                for f in e:
                    if f in EVIDENCE_OPTIONAL:
                        if not _kind_ok("s", e[f]):
                            out.append(finding("SCHEMA_TYPE", p + "." + f, "wrong type or empty"))
                    elif f not in ("ref", "task_id", "revision", "observed_at"):
                        out.append(finding("UNKNOWN_KEY", p + "." + safe_key(f), "field not in schema"))
    return out


def _timestamps(d):
    """Return ({path: datetime|None}, findings) for every timestamp in the envelope."""
    found, out = {}, []
    paths = [("source.identity_at", d["source"]["identity_at"]), ("source.revision_at", d["source"]["revision_at"]),
             ("observed_at.envelope", d["observed_at"]["envelope"]), ("observed_at.worker", d["observed_at"]["worker"]),
             ("observed_at.result", d["observed_at"]["result"])]
    for i, e in enumerate(d["evidence"]):
        paths.append(("evidence[%d].observed_at" % i, e["observed_at"]))
    for p, v in paths:
        try:
            found[p] = parse_ts(v)
        except (ValueError, TypeError):
            found[p] = None
            out.append(finding("BAD_TIMESTAMP", p, "not an ISO-8601 timestamp with offset or UNKNOWN"))
    return found, out


def as_now(now):
    """datetime (aware, UTC) from an aware datetime or an ISO-8601 string with offset; None stays None.
    ValueError for a naive datetime, UNKNOWN, an out-of-range value or any other type."""
    if now is None:
        return None
    if isinstance(now, datetime):
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("now must carry a UTC offset")
        try:
            return now.astimezone(timezone.utc)
        except OverflowError:
            raise ValueError("now out of range")
    if isinstance(now, str):
        t = parse_ts(now)
        if t is None:
            raise ValueError("now must be a timestamp, not UNKNOWN")
        return t
    raise ValueError("now must be a datetime or an ISO-8601 string")


def host_now():
    """The trusted host clock (aware UTC). The one module-level clock: tests patch this, live code never overrides it."""
    return datetime.now(timezone.utc)


def resolve_now(now):
    """The reference clock: an explicit `now` (datetime or ISO-8601 string) else the host clock. Never derived from the data."""
    return as_now(now) if now is not None else host_now()


def observation_times(d):
    """Every parseable observation time in one record (tolerant: used before validation to find the newest)."""
    out = []
    try:
        vals = [d["observed_at"][k] for k in ("envelope", "worker", "result")] + [e["observed_at"] for e in d["evidence"]]
    except (KeyError, TypeError):
        return out
    for v in vals:
        try:
            t = parse_ts(v)
        except (ValueError, TypeError):
            continue
        if t is not None:
            out.append(t)
    return out


def validate(d, now=None):
    """Findings for one envelope. Empty list = shape and internal consistency hold.
    `now` is the reference clock for the observation window; None = the host clock (host_now()).
    ValueError for a naive or out-of-range `now`; a malformed record never raises: it yields a refusal."""
    ref_now = resolve_now(now)
    try:
        return _validate(d, ref_now)
    except (RecursionError, OverflowError):
        return [finding("MALFORMED", "$", "record cannot be evaluated (nesting or number out of range)")]


def _validate(d, ref_now):
    if not isinstance(d, dict):
        return [finding("SCHEMA_TYPE", "$", "envelope must be an object")]
    dups = find_dups(d)
    if dups:
        return [finding("DUPLICATE_KEY", "$", "duplicate JSON key makes the record ambiguous: " + "; ".join(dups))]
    out = _shape(d)
    if any(f["code"] in ("SCHEMA_MISSING", "SCHEMA_TYPE", "SCHEMA_ENUM") for f in out):
        return out  # cross-field rules need a well-formed record
    ts, bad = _timestamps(d)
    out += bad
    # stale evidence: an observation older than the source identity or revision it cites
    refs = [ts[k] for k in ("source.identity_at", "source.revision_at") if ts.get(k)]
    if refs:
        newest = max(refs)
        for p, t in ts.items():
            if p.startswith("source."):
                continue
            if t is not None and t < newest:
                out.append(finding("STALE_EVIDENCE", p, "observed before the cited source identity/revision"))
    st = d["state"]
    # freshness evidence that is required for the state: an UNKNOWN one is unverifiable, never skipped
    required = ["observed_at.envelope"] + (["observed_at.worker"] if st == "RUNNING" else []) + \
        (["observed_at.result"] if st == "DONE" else []) + \
        (["evidence[%d].observed_at" % i for i in range(len(d["evidence"]))] if st != "DONE" else [])
    raw = {"observed_at.envelope": d["observed_at"]["envelope"], "observed_at.worker": d["observed_at"]["worker"],
           "observed_at.result": d["observed_at"]["result"]}
    raw.update({"evidence[%d].observed_at" % i: e["observed_at"] for i, e in enumerate(d["evidence"])})
    for p in required:
        if raw[p] == UNKNOWN and st != "UNKNOWN":  # a state-UNKNOWN record can only yield an UNKNOWN disposition anyway
            out.append(finding("UNKNOWN_TIMESTAMP", p, "required observation time is UNKNOWN: freshness cannot be verified"))
    if ref_now is not None:
        checked = [("observed_at.envelope", True), ("observed_at.worker", d["state"] != "DONE"),
                   ("observed_at.result", False)]
        checked += [("evidence[%d].observed_at" % i, d["state"] != "DONE") for i in range(len(d["evidence"]))]
        for p, stale_applies in checked:
            t = ts.get(p)
            if t is None:
                continue
            if (t - ref_now).total_seconds() > FUTURE_SKEW_SECONDS:
                out.append(finding("FUTURE_TIMESTAMP", p, "observation is dated after the reference now (%s)" % ref_now.isoformat()))
            elif stale_applies and (ref_now - t).total_seconds() > STALE_WINDOW_SECONDS:
                out.append(finding("STALE_EVIDENCE", p, "observed more than %d s before the reference now (%s)" %
                                   (STALE_WINDOW_SECONDS, ref_now.isoformat())))
    tid, rev = d["task_id"], d["revision"]
    for i, e in enumerate(d["evidence"]):
        if e["task_id"] != tid:
            out.append(finding("WRONG_TASK", "evidence[%d].task_id" % i, "evidence task_id differs from task_id (%s vs %s)" %
                               (opaque("task", e["task_id"]), opaque("task", tid))))
        elif e["revision"] != rev:
            out.append(finding("STALE_REVISION", "evidence[%d].revision" % i,
                               "evidence cites rev %d, envelope is rev %d" % (e["revision"], rev)))
        tg = d["target"]
        if not is_unknown(tg["head"]):
            for h in evidence_heads(e):
                if not same_head(h, tg["head"]):
                    out.append(finding("WRONG_TASK", "evidence[%d].head" % i,
                                       "evidence names a head that differs from target.head (%s vs %s)" %
                                       (opaque("head", h), opaque("head", tg["head"]))))
        if "repo" in e and not is_unknown(tg["repo"]) and norm_repo(e["repo"]) != norm_repo(tg["repo"]):
            out.append(finding("WRONG_TASK", "evidence[%d].repo" % i, "evidence repo differs from target.repo (%s vs %s)" %
                               (opaque("repo", e["repo"]), opaque("repo", tg["repo"]))))
        if "branch" in e and not is_unknown(tg["branch"]) and norm_branch(e["branch"]) != norm_branch(tg["branch"]):
            out.append(finding("WRONG_TASK", "evidence[%d].branch" % i, "evidence branch differs from target.branch (%s vs %s)" %
                               (opaque("branch", e["branch"]), opaque("branch", tg["branch"]))))
    r, w, st = d["result"], d["worker"], d["state"]
    if r["task_id"] is not None and r["task_id"] != tid:
        out.append(finding("WRONG_TASK", "result.task_id", "result task_id differs from task_id (%s vs %s)" %
                           (opaque("task", r["task_id"]), opaque("task", tid))))
    elif r["revision"] is not None and r["revision"] != rev:
        out.append(finding("STALE_REVISION", "result.revision", "result cites rev %d, envelope is rev %d" % (r["revision"], rev)))
    if st == "RUNNING":
        missing = [k for k in ("host", "unit", "child") if ident(w[k], "host" if k == "host" else None) is None]
        if missing or d["observed_at"]["worker"] == UNKNOWN:
            out.append(finding("RUNNING_NO_EVIDENCE", "worker",
                               "RUNNING needs observed host+unit+child (missing: %s)" %
                               ",".join(missing + (["observed_at.worker"] if d["observed_at"]["worker"] == UNKNOWN else []))))
        if not d["evidence"]:
            out.append(finding("RUNNING_NO_EVIDENCE", "evidence", "RUNNING needs at least one evidence entry; the list is empty"))
        elif all(is_unknown(e["ref"]) for e in d["evidence"]):
            out.append(finding("RUNNING_NO_EVIDENCE", "evidence", "RUNNING needs an evidence entry that names what was read; every ref is a placeholder"))
    if st == "NOT_STARTED" and not (is_unknown(w["unit"]) and is_unknown(w["child"])):
        out.append(finding("NOT_STARTED_WITH_WORKER", "worker",
                           "NOT_STARTED carries an observed unit or child: contradictory; a started worker is not an unowned slice"))
    if st == "DONE":
        if is_unknown(r["artifact"]) and is_unknown(r["event"]):
            out.append(finding("DONE_NO_ARTIFACT", "result", "DONE needs a durable result artifact or event"))
        elif r["task_id"] is None or r["revision"] is None:
            out.append(finding("RESULT_UNBOUND", "result", "result does not state which task and revision it answers"))
    if d["effect"]["state"] in ("applied", "UNKNOWN") and not d["effect"]["no_replay"]:
        out.append(finding("NO_REPLAY_POLICY", "effect.no_replay", "an applied or UNKNOWN effect must carry no_replay=true"))
    if d["ack"]["accepted"] and not ref_like(d["ack"]["evidence"]):
        out.append(finding("INVENTED_ACK", "ack", "accepted=true without evidence of the consumer's ACK"))
    if d["declared_complete"]:
        req = {"current_owner": d["current_owner"], "owner_reachable": d["owner_reachable"],
               "effect.state": d["effect"]["state"], "consumer.named": d["consumer"]["named"],
               "consumer.available": d["consumer"]["available"], "next_action": d["next_action"],
               "source.identity_at": d["source"]["identity_at"], "source.revision_at": d["source"]["revision_at"]}
        req.update({"target." + k: v for k, v in d["target"].items()})
        req.update({"worker." + k: v for k, v in w.items()})
        req["result.reviewed"] = r["reviewed"]
        unk = sorted(k for k, v in req.items() if is_unknown(v))
        for k in ("target.head",):  # positive validation where the field has a format: a hex sha
            if k not in unk and not is_sha(req[k]):
                unk.append(k)
        for k in ("worker.host", "worker.unit", "worker.child", "worker.session", "worker.invocation", "worker.account",
                  "worker.model", "worker.effort", "consumer.named"):
            if k not in unk and ident(req[k], "host" if k == "worker.host" else None) is None:
                unk.append(k)
        unk.sort()
        if unk or d["coverage_gaps"] or st != "DONE":
            out.append(finding("FALSE_COMPLETE", "declared_complete",
                               "declared complete with state %s and UNKNOWN: %s; coverage gaps listed: %d" %
                               (st, ",".join(unk) or "-", len(d["coverage_gaps"]))))
    return out


# Observation window: an envelope / worker / evidence observation older than this before the reference "now",
# or dated more than FUTURE_SKEW_SECONDS after it, is refused. The reference "now" is the caller's explicit
# `now` (CLI: --now TS; --now system = host clock) or, when none is given, the host clock. Never the data.
STALE_WINDOW_SECONDS = 24 * 3600
FUTURE_SKEW_SECONDS = 300

# a commit named in free text: after a keyword (head/commit/sha/rev/oid/hash, any separator) any 4-64 hex run, or a bare
# 7-64 hex run mixing digits and letters. Short (< 7) names never count as a match: they are an UNKNOWN ref.
_HEAD_KEYWORD = re.compile(r"(?i)\b(?:head|commit|sha1?|sha256|revision|rev|oid|hash)\b[\s=:#@-]*([0-9a-f]{4,64})(?![\w])")
_HEAD_BARE = re.compile(r"(?i)(?<![\w-])([0-9a-f]{7,64})(?![\w-])")


def evidence_heads(e):
    """Head shas an evidence entry names: its head field and every commit-like name in its ref."""
    heads = [e["head"]] if "head" in e else []
    # a hex run that sits under a credential name, flag or header is a secret, never a commit: candidates come from the ref
    # with its credential layers applied
    ref = redact_credentials(unicodedata.normalize("NFKC", e["ref"]))
    for m in _HEAD_KEYWORD.finditer(ref):
        h = m.group(1).lower()
        if len(h) >= 7 or any(c in "abcdef" for c in h):
            heads.append(h)
    for m in _HEAD_BARE.finditer(ref):
        h = m.group(1).lower()
        if any(c.isdigit() for c in h) and any(c in "abcdef" for c in h):
            heads.append(h)
    out = []
    for h in heads:
        if h not in out:
            out.append(h)
    return out


def same_head(a, b):
    """Equal, or one a prefix of the other with both at least 7 hex long. A shorter, unequal name is not a match."""
    a, b = a.strip().lower(), b.strip().lower()
    return a == b or (min(len(a), len(b)) >= 7 and (a.startswith(b) or b.startswith(a)))


def norm_repo(v):
    return v.strip().lower()


def norm_branch(v):
    v = v.strip()
    return v[len("refs/heads/"):] if v.startswith("refs/heads/") else v


def _records(obj):
    if isinstance(obj, dict) and "envelopes" in obj:
        return obj["envelopes"], obj.get("declared_total")
    if isinstance(obj, list):
        return obj, None
    return [obj], None


def validate_set(obj, now=None):
    """Per-envelope findings plus set rules: duplicate task, conflicting live target, derived count."""
    recs, declared = _records(obj)
    if not isinstance(recs, list):
        return {"derived_count": 0, "findings_by_index": [], "set_findings": [finding("SCHEMA_TYPE", "envelopes", "must be a list")]}
    ref_now = resolve_now(now)
    by_idx = [validate(r, ref_now) for r in recs]  # validate() never raises for a malformed record
    sets = []
    if isinstance(obj, dict) and getattr(obj, "dups", ()):
        f = finding("DUPLICATE_KEY", "$", "duplicate JSON key in the set wrapper: " + ",".join(safe_key(k) for k in obj.dups))
        sets.append(f)
        for fs in by_idx:
            fs.append(f)
    wf = [r for r in recs if isinstance(r, dict)]
    ids = {}
    for i, r in enumerate(recs):
        if isinstance(r, dict) and isinstance(r.get("task_id"), str):
            ids.setdefault(norm_text(r["task_id"]), []).append(i)
    for tid, idx in ids.items():
        if len(idx) > 1:
            f = finding("DUPLICATE_TASK", "task_id", "task %s appears %d times" % (opaque("task", recs[idx[0]]["task_id"]), len(idx)))
            sets.append(f)
            # state-aware, never positional: the first RUNNING record is the original and stays undisturbed;
            # with no RUNNING record the first listed keeps its place. Every other record of the id is refused.
            running = [i for i in idx if recs[i].get("state") == "RUNNING"]
            keep = running[0] if running else idx[0]
            for i in idx:
                if i != keep:
                    by_idx[i].append(f)
    live = {}
    for i, r in enumerate(recs):
        if not (isinstance(r, dict) and isinstance(r.get("task_id"), str) and isinstance(r.get("target"), dict)
                and r.get("state") in ("RUNNING", "NOT_STARTED")):
            continue
        t = r["target"]
        if isinstance(t.get("repo"), str) and isinstance(t.get("branch"), str) \
                and not is_unknown(t["repo"]) and not is_unknown(t["branch"]):
            live.setdefault((norm_repo(t["repo"]), norm_branch(t["branch"])), []).append(i)
    for key, idx in live.items():
        tasks = {recs[i]["task_id"] for i in idx}
        if len(tasks) < 2:
            continue
        running = [i for i in idx if recs[i]["state"] == "RUNNING"]
        refused = [i for i in idx if recs[i]["state"] != "RUNNING"] if len(running) == 1 else idx
        f = finding("CONFLICTING_TARGET", "target", "%d live tasks share %s@%s" % (len(tasks), opaque("repo", key[0]), opaque("branch", key[1])))
        sets.append(f)
        for i in refused:
            by_idx[i].append(f)
    if declared is not None and declared != len(recs):
        sets.append(finding("DECLARED_COUNT_MISMATCH", "declared_total",
                            "declared %s, enumerated %d (enumerated count is used)" %
                            (declared if isinstance(declared, int) and not isinstance(declared, bool) else "a non-integer value",
                             len(recs)), "WARN"))
    return {"derived_count": len(recs), "findings_by_index": by_idx, "set_findings": sets}


def parse_args(argv):
    """(paths, now) where --now TS sets the reference clock and --now system uses the host clock; ValueError if bad."""
    paths, now, it = [], None, iter(argv)
    for a in it:
        if a == "--now":
            v = next(it, None)
            if v is None:
                raise ValueError("--now needs a timestamp or 'system'")
            now = host_now() if v == "system" else as_now(v)
        else:
            paths.append(a)
    return paths, now


def main(argv):
    try:
        argv, now = parse_args(argv)
    except ValueError as e:
        emit(redact_tool("UNREADABLE --now: %s" % e))
        return 2
    if not argv:
        emit(__doc__)
        return 2
    rc = 0
    for path in argv:
        try:
            obj = load_json_file(path)
        except (OSError, ValueError) as e:
            emit(redact_tool("UNREADABLE %s: %s" % (path, e)))
            rc = max(rc, 2)
            continue
        res = validate_set(obj, now)
        emit(redact_tool("%s: %d envelope(s) enumerated" % (path, res["derived_count"])))
        everything = [(i, f) for i, fs in enumerate(res["findings_by_index"]) for f in fs]
        everything += [(None, f) for f in res["set_findings"]
                       if not any(f is g for _, g in everything)]
        for i, f in everything:
            emit(redact_tool("%s %s [%s] %s: %s" % (f["severity"], f["code"], "set" if i is None else i, f["path"], f["message"])))
        if any(f["severity"] == "REFUSE" for _, f in everything):
            rc = max(rc, 1)
        elif not everything:
            emit("OK (shape and internal consistency only; not production evidence)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
