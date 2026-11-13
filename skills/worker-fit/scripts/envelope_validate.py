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


def keep(kind, v):
    """The value to print for an identity field: marked when the field's own format validation accepts it (kind
    ident | host | path | sha), else the raw value, which then goes through full redaction. The printed text is the value
    as given; only the validated, credential-free form skips the run rule."""
    if not isinstance(v, str):
        return v
    ok = _KINDS[kind](v)
    if kind != "sha" and ok == v and not _trusted_pieces(v):
        return v
    return v if ok is None or ok != v else _MARK_OPEN + v + _MARK_CLOSE


def show(label, v, kind="ident"):
    """What an identity field prints: the value when it validates against its field's grammar (marked, so the run rule
    skips it), a placeholder as it is (UNKNOWN stays UNKNOWN), and otherwise an opaque keyed reference, never the raw
    value."""
    if not isinstance(v, str) or is_unknown(v):
        return v
    k = keep(kind, v)
    return k if k != v else opaque(label, v)


def show_ref(label, v):
    """A free-text reference (evidence ref): a single locator-shaped token prints when it validates and is otherwise an
    opaque ref; prose (whitespace) is narrative and goes through full redaction."""
    if not isinstance(v, str) or is_unknown(v) or any(c.isspace() for c in v.strip()):
        return v
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


def _cred_name(name):
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
_NAME_WORDS = frozenset("service scope socket timer slice mount target path unit worker svc bot api user local prod dev test ci "
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


def _piece_ok(seg):
    """One piece of an identity: plain, an id shape, or word-like; a compact date inside a piece ('r7wfr620261113') is
    checked as its own piece."""
    if _idplain(seg) or _ID_PIECE.fullmatch(seg) or _wordish(seg):
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
                       "spec specs plan plans diff patch fix fixes test tests suite case cases shift clock").split())
_HEX_RUN = re.compile(r"[0-9a-fA-F]{9,64}")
_HEX_GLUED = re.compile(r"(?P<w>[A-Za-z]{1,12}?)(?P<h>[0-9a-f]{9,64})")
_ULID_ANY = re.compile(r"[0-7][0-9A-HJKMNP-TV-Z]{25}|[0-7][0-9a-hjkmnp-tv-z]{25}")
_SHORT_HEX = re.compile(r"[0-9a-fA-F]{1,8}")


def _vocab(seg):
    low = seg.lower()
    return low in _ID_WORDS or low.rstrip("0123456789") in _ID_WORDS and not _cred_name(low)


def _random_piece(seg):
    """(is_random, glued_word): the piece is a long hex id, a word glued to one, or a ULID."""
    if _HEX_RUN.fullmatch(seg) or _ULID_ANY.fullmatch(seg):
        return True, ""
    m = _HEX_GLUED.fullmatch(seg)
    if m and any(c.isdigit() for c in m.group("h")):
        return True, m.group("w")
    return False, ""


def _trusted_pieces(s):
    """True when every piece of a grammar-valid identity is trusted for printing (see TRUST LAYER)."""
    segs = [x for x in _SPLIT.split(s) if x]
    rnd = [_random_piece(x) for x in segs]
    for seg in segs:
        low = seg.lower()
        if _cred_name(seg) and any(len(o) >= 9 and o != seg and not o.isdigit() for o in segs):
            return False  # a credential word beside a long piece
        for w in _GLUE_PREFIXES:
            if low.startswith(w) and len(low) - len(w) >= 10 and low[len(w):].isalpha():
                return False  # a credential word glued to a long run of letters
    if not any(r for r, _ in rnd):
        return True
    for i, (seg, (r, glued)) in enumerate(zip(segs, rnd)):
        if r:
            if glued and glued.lower() != "r" and not _vocab(glued):
                return False
        elif not (seg.isdigit() or _SHORT_HEX.fullmatch(seg) or _DATE_PIECE.fullmatch(seg) or _vocab(seg)
                  or (len(seg) == 1 and 0 < i < len(segs) - 1 and not rnd[i - 1][0] and not rnd[i + 1][0]
                      and any(c.isdigit() for c in segs[i - 1]) and any(c.isdigit() for c in segs[i + 1]))):
            return False
    return True


_GLUE_PREFIXES = tuple(sorted((w for w in _CRED_WORDS if len(w) >= 2 and w not in ("session", "sessions", "sid", "api", "pin", "key", "keys")), key=len, reverse=True)) + ("key", "keys")


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


def redact_credentials(text):
    """The credential layers of redact(): everything except the random-token run rule. A value this leaves unchanged
    carries no credential name, flag or known credential shape. The layers run on the text and on its decoded views (JSON
    string escapes, then percent-escapes): when a decoded view shows a credential the text hides, the deepest decoded view
    with its credential hidden is the result, so an escaped, \\u-encoded or string-encoded pair is hidden like a plain one."""
    if not isinstance(text, str):
        return text
    best = _layers(text)
    view = text
    for dec in (_unescape, _pct_decode):
        d = dec(view)
        if d == view:
            continue
        view = d
        r = _layers(view)
        if r != view:
            best = r
    return best


def redact(text):
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
    """redact() applied to every string inside a JSON-shaped value."""
    if isinstance(v, str):
        return redact(v)
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
        emit(redact("UNREADABLE --now: %s" % e))
        return 2
    if not argv:
        emit(__doc__)
        return 2
    rc = 0
    for path in argv:
        try:
            obj = load_json_file(path)
        except (OSError, ValueError) as e:
            emit(redact("UNREADABLE %s: %s" % (path, e)))
            rc = max(rc, 2)
            continue
        res = validate_set(obj, now)
        emit(redact("%s: %d envelope(s) enumerated" % (path, res["derived_count"])))
        everything = [(i, f) for i, fs in enumerate(res["findings_by_index"]) for f in fs]
        everything += [(None, f) for f in res["set_findings"]
                       if not any(f is g for _, g in everything)]
        for i, f in everything:
            emit(redact("%s %s [%s] %s: %s" % (f["severity"], f["code"], "set" if i is None else i, f["path"], f["message"])))
        if any(f["severity"] == "REFUSE" for _, f in everything):
            rc = max(rc, 1)
        elif not everything:
            emit("OK (shape and internal consistency only; not production evidence)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
