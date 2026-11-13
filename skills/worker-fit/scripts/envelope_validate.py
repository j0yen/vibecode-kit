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


def is_unknown(v):
    """True for None and for any UNKNOWN-equivalent placeholder string, however spelled (see norm_text)."""
    if v is None:
        return True
    if not isinstance(v, str):
        return False
    s = norm_text(v)
    return s in PLACEHOLDERS or not any(c.isalnum() for c in s) or _compact(s) in _COMPACT_PLACEHOLDERS


def _compact(s):
    return re.sub(r"[\W_]+", "", s)


def is_assertion_word(v):
    """True for a bare yes/no/true/ok/self/authorized-style word (after norm_text, any punctuation or spacing)."""
    return isinstance(v, str) and _compact(norm_text(v)) in _NON_IDENTITY


def ref_like(v):
    """Positive validation for a reference (authorization reference, ACK evidence): a string that is not a placeholder
    or a bare assertion word and carries a locator: a digit (id, number, date) or one of : / # @ (url, path, handle)."""
    if not isinstance(v, str) or is_unknown(v) or is_assertion_word(v):
        return False
    s = unicodedata.normalize("NFKC", v)
    return any(c.isdigit() for c in s) or any(c in s for c in ":/#@")


_IDENT = re.compile(r"[A-Za-z0-9%][A-Za-z0-9._:@/+%=-]{0,127}")  # %12 (tmux pane), pid=77, fe80::1%eth0
_SHA = re.compile(r"[0-9a-fA-F]{7,64}")


def ident(v):
    """The value as an identifier (ASCII word characters and . _ : @ / + -, no spaces), or None when it is not one
    or is a placeholder. Used wherever a value names a host, unit, child, consumer or reviewer."""
    if not isinstance(v, str) or is_unknown(v) or is_assertion_word(v):
        return None
    s = unicodedata.normalize("NFKC", v).strip()
    return s if _IDENT.fullmatch(s) else None


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
# the name starts at its secret word and may run on for a bounded stretch (keeps matching linear on hostile input)
_NAME = r"(?:token|key|password|passwd|pwd|secret|credential|authorization)[\w.-]{0,200}"
_NOT_DONE = r"(?!\[REDACTED\])"
# name/value separators: = : => -> and their full-width / small-form look-alikes
_SEP = r"(?:=>|->|[:=\uff1a\uff1d\ufe55\ufe66\u2236])"
_QUOTED_OR_WORD = r"""(?:"(?:[^"\\]|\\.)*"|'[^']*'|[^\s,;&)"'\]}]+)"""
_REDACTIONS = [
    # PEM private/secret key blocks (a missing END line redacts to the end of the text)
    (re.compile(r"-----BEGIN [A-Z0-9 ]*(?:PRIVATE|SECRET)[A-Z0-9 ]*-----.*?(?:-----END [A-Z0-9 ]*-----|\Z)", re.S), REDACTED),
    # URL userinfo with a password: scheme://user:pass@host, the password may itself hold @ or / (everything up to the
    # last @ of the unbroken run is redacted; both runs are length-bounded to keep matching linear on hostile input)
    (re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/@:\"'<>]{0,128}:[^\s\"'<>]{0,512}@"), r"\1" + REDACTED + "@"),
    # URL userinfo without a password: scheme://token@host
    (re.compile(r"(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]*://)[^\s/@:]{0,256}@"), r"\1" + REDACTED + "@"),
    # Authorization header value (Basic/Bearer/Digest/Token scheme plus credential)
    (re.compile(r"(?i)(\bauthorization[\"']?\s*" + _SEP + r"\s*[\"']?)" + _NOT_DONE +
                r"(?:(?:basic|bearer|digest|token|negotiate)\s+)?[^\s\"',;)]+"), r"\1" + REDACTED),
    (re.compile(r"(?i)\b(bearer)(?:\s*" + _SEP + r"\s*|\s+)" + _NOT_DONE + r"[^\s\"',;)]+"), r"\1 " + REDACTED),
    # name = value / name: value, value may be quoted (with spaces); the name contains a secret word
    (re.compile(r"(?i)(" + _NAME + r"[\"']?\s*" + _SEP + r"\s*)" + _NOT_DONE + _QUOTED_OR_WORD), r"\1" + REDACTED),
    # command-line flag whose name holds a secret word, value as the next word: --password VALUE, -token VALUE
    (re.compile(r"(?i)((?<![\w-])--?[a-z0-9-]{0,40}(?:token|key|password|passwd|pwd|secret|credential)[a-z0-9_-]{0,100}[ \t]+)"
                + _NOT_DONE + _QUOTED_OR_WORD), r"\1" + REDACTED),
    (re.compile(r"(?<![A-Za-z0-9_])sk-[A-Za-z0-9_-]{3,}"), REDACTED),
    (re.compile(r"sk-(?:ant|proj|svcacct|admin|or)-[A-Za-z0-9_-]{8,}"), REDACTED),  # vendor-tagged keys, even glued to a word
    # provider token prefixes, as a class (each needs a long enough body, so ordinary words are left alone)
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
                r")"), REDACTED),
    (re.compile(r"(?<![/:])1//0[A-Za-z0-9_-]{20,}"), REDACTED),                          # Google refresh token
    # webhook URLs carry their secret in the path
    (re.compile(r"(?i)hooks\.slack\.com/services/[A-Za-z0-9/_-]{8,}|discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]{8,}"), REDACTED),
    (re.compile(r"eyJ(?:(?!eyJ)[A-Za-z0-9_-]){4,}\.[A-Za-z0-9_-]{4,}\.[A-Za-z0-9_-]*"), REDACTED),
]


def redact(text):
    """Replace credential-shaped values in any output string: PEM key blocks, URL userinfo, Authorization/Bearer values,
    name=value pairs whose name holds token/key/password/secret/credential (quoted values with spaces included),
    sk-... keys, provider token prefixes (AWS, GitHub, Slack, Google, npm, GitLab, Stripe, ...), webhook URLs and JWTs."""
    if not isinstance(text, str):
        return text
    for rx, rep in _REDACTIONS:
        text = rx.sub(rep, text)
    return text


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
        return {k: scrub(x) for k, x in v.items()}
    return v


def load_json_text(txt):
    try:
        return json.loads(txt, object_pairs_hook=_pairs)
    except RecursionError:
        raise ValueError("JSON nesting too deep")


def find_dups(obj, path="$"):
    """Paths of objects that carry a repeated key; such input is ambiguous and is refused."""
    out = []
    if isinstance(obj, dict):
        if getattr(obj, "dups", ()):
            out.append("%s (%s)" % (path, ",".join(obj.dups)))
        for k, v in obj.items():
            out += find_dups(v, "%s.%s" % (path, k))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += find_dups(v, "%s[%d]" % (path, i))
    return out


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
            out.append(finding("UNKNOWN_KEY", k, "field not in schema"))
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
                out.append(finding("UNKNOWN_KEY", k + "." + f, "field not in schema"))
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
                        out.append(finding("UNKNOWN_KEY", p + "." + f, "field not in schema"))
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
            out.append(finding("WRONG_TASK", "evidence[%d].task_id" % i, "evidence is for task " + e["task_id"]))
        elif e["revision"] != rev:
            out.append(finding("STALE_REVISION", "evidence[%d].revision" % i,
                               "evidence cites rev %d, envelope is rev %d" % (e["revision"], rev)))
        tg = d["target"]
        if not is_unknown(tg["head"]):
            for h in evidence_heads(e):
                if not same_head(h, tg["head"]):
                    out.append(finding("WRONG_TASK", "evidence[%d].head" % i,
                                       "evidence names head %s, target.head is %s" % (h, tg["head"])))
        if "repo" in e and not is_unknown(tg["repo"]) and norm_repo(e["repo"]) != norm_repo(tg["repo"]):
            out.append(finding("WRONG_TASK", "evidence[%d].repo" % i, "evidence is for repo " + e["repo"]))
        if "branch" in e and not is_unknown(tg["branch"]) and norm_branch(e["branch"]) != norm_branch(tg["branch"]):
            out.append(finding("WRONG_TASK", "evidence[%d].branch" % i, "evidence is for branch " + e["branch"]))
    r, w, st = d["result"], d["worker"], d["state"]
    if r["task_id"] is not None and r["task_id"] != tid:
        out.append(finding("WRONG_TASK", "result.task_id", "result is for task " + r["task_id"]))
    elif r["revision"] is not None and r["revision"] != rev:
        out.append(finding("STALE_REVISION", "result.revision", "result cites rev %d, envelope is rev %d" % (r["revision"], rev)))
    if st == "RUNNING":
        missing = [k for k in ("host", "unit", "child") if ident(w[k]) is None]
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
            if k not in unk and ident(req[k]) is None:
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
    ref = unicodedata.normalize("NFKC", e["ref"])
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
        f = finding("DUPLICATE_KEY", "$", "duplicate JSON key in the set wrapper: " + ",".join(obj.dups))
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
            f = finding("DUPLICATE_TASK", "task_id", "task %s appears %d times" % (recs[idx[0]]["task_id"], len(idx)))
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
        f = finding("CONFLICTING_TARGET", "target", "%d live tasks share %s@%s" % (len(tasks), key[0], key[1]))
        sets.append(f)
        for i in refused:
            by_idx[i].append(f)
    if declared is not None and declared != len(recs):
        sets.append(finding("DECLARED_COUNT_MISMATCH", "declared_total",
                            "declared %r, enumerated %d (enumerated count is used)" % (declared, len(recs)), "WARN"))
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
