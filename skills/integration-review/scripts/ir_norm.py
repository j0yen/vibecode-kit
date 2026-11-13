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


# ---- placeholder vocabulary, commits and non-evidence prose (one definition each, shared by the scripts) ----------
# NE_PLACEHOLDER words say by themselves that the fact is not known, missing, unavailable, pending or still to be done;
# NE_FILLER words only frame a statement (status, result, value, is, see above, to be verified, this record ...). Both
# lists are vocabulary, not proof: UNKNOWN is never filled. They serve two rules: non_evidence() for prose evidence refs
# and commit_id() for a commit that says nothing.
_NE_PLACEHOLDER = frozenset(
    "unknown unk unknowable unverifiable unverified undetermined undefined unspecified unstated unavailable unconfirmed "
    "unresolved null nil none nothing nada na tbd tba tbc todo fixme missing absent empty blank vacant pending placeholder "
    "dummy fake stub mock lorem ipsum xxx draft incomplete unfinished unnamed unset notset undone tentative provisional "
    "later unclear inconclusive dunno redacted withheld awaiting await waiting".split())
_NE_FILLER = frozenset(
    "status result results evidence value values source owner output data answer check reviewer review reviewed "
    "is are was were be been being the a an of for to this that it its still yet currently now not "
    "see above below attached notes note ticket same as before earlier previous follow will verify verified confirm "
    "confirmed confirmation verification needs need needed in progress determined announced provided stated known "
    "available applicable set filled fill details detail info information more further soon todo "
    "decided insert here add lost gone record component endpoint interface vendor response reply us we our at time "
    "moment today update recorded captured supplied specified on by".split())
_COMMIT_NOISE = frozenset("commit sha id rev revision hash oid git ref no number".split())
# A label before a commit ("sha:", "sha1:", "sha-256:", "commit ", "rev ", "hash=", "git:" ...); only the sha forms may be
# followed by "-" ("sha256-<hex>"): "git-2.40" and "rev-1" are names, not a label and a value.
_COMMIT_LABEL = re.compile(r"^(?:(?:sha-?(?:1|256)?)[\s:=#-]+|(?:commit(?:\s*id)?|rev(?:ision)?|hash|git|oid)[\s:=#]+)", re.I)
# A sha written inside decoration: the hex (7-64 digits) is a token of its own, optionally glued to 0x, g (git describe), or
# label-. A hex glued to a name by - / _ . ("feature/abc1234-login", "fix-abc1234") is part of that name, never a commit.
_HEXTOK = re.compile(r"(?:(?<![\w/.-])(?:0x|g|(?:commit|rev|revision|sha|sha1|sha256|hash|oid|git|id)-)?|(?<=\d-)g|(?<=/commit/)|(?<=/commits/)|(?<=/tree/))"
                     r"([0-9a-f]{7,64})(?![\w/-]|\.\w)")
_NA = re.compile(r"\bn\s*[./]\s*a\b\.?")
_SPACED_LETTERS = re.compile(r"\b(?:[a-z] )+[a-z]\b")
# Non-identifying commits: the null object (all zeros) and the generic moving pointers. They say that no particular commit is
# named, so they are unstated, as UNKNOWN is. A pointer may carry a remote or refs/heads prefix, "the/current/latest" and a
# trailing "commit/branch", and ~N, ^N or @{..} suffixes. A specific name (a tag, a release, feature/login) is not one.
FLOATING_WORDS = ("HEAD", "FETCH_HEAD", "ORIG_HEAD", "MERGE_HEAD", "main", "master", "trunk", "develop", "development",
                  "default", "latest", "tip", "current")
_FLOATING = re.compile(r"(?:(?:origin|upstream)/|(?:refs/)?(?:heads|remotes/[^/\s]+)/)?(?:(?:the|current|latest) )*(?:%s)"
                       r"(?: commit| branch| ref)?(?:[~^]\d*|@\{[^}]*\})*" % "|".join(w.lower() for w in FLOATING_WORDS))
_POINTER_WORDS = frozenset(w.lower() for w in FLOATING_WORDS)
_NULL_SHA = re.compile(r"0{7,64}")
# A number or version is a concrete anchor only after a content word ("line 12"): "#12", "2026-11-12", "v1" beside a
# placeholder word are decoration. Code tokens are classified by _token_kind().
_WEAK = re.compile(r"[0-9\"'`=#]")
_NUMBER = re.compile(r"[#v]?[0-9][0-9:.,/-]*")
_TOK_EDGE = " \t\r\n.,;:!'\"`()[]{}<>*_~|=?-"
_CALL = re.compile(r"[a-z_][\w.]*\([^()\s]*\)")
_SCOPE = re.compile(r"\w::\w")
_PIN = re.compile(r"\w@[\w.{~^-]*[0-9]")
_LINE_SUFFIX = re.compile(r"(?::\d+(?:-\d+)?|#l\d+(?:-l?\d+)?)$")
_DOTTED = re.compile(r"[a-z_]\w*(?:\.[a-z_]\w*)+")
_TLD = frozenset("com org net io dev edu gov co uk de fr app ai".split())
_DIRS = frozenset("src lib bin pkg app apps cmd internal include test tests spec docs doc scripts tools util utils gen generated "
                  "config configs conf svc services handlers vendor build crates mod modules".split())
_EXT = frozenset("py rs js ts tsx jsx go java kt c h cc cpp hpp rb sh bash md rst txt log json jsonl yaml yml toml ini cfg conf "
                 "env sql html css scss proto xml csv tsv lock gradle php cs swift scala ex exs erl hs lua pl".split())


def _token_kind(tok):
    """What a whitespace-separated token of a ref is, as code: "call" (f(), a.b()), "scope" (a::b), "url" (a://b), "pin"
    (name@version), "file" (a dotted name with a known file extension or a line suffix), "path" (a/b/c, or a/b.ext, or a
    path with a line suffix), "module" (a.b.c with 3+ parts that is no host name, or a name with "_"), "slash" (lib/unknown) or "dotted" (a.b), the last two anchors only when lone, or None (prose, an abbreviation such as b/c / w/o,
    a mention such as @bob, an alternative such as unknown/tbd)."""
    b = tok.strip(_TOK_EDGE)
    if re.search(r"\w://[^/\s]+/\S", b):
        return "url"                                 # a URL with a path; a bare site root names no location
    if _CALL.search(tok):
        return "call"
    if _SCOPE.search(b):
        return "scope"
    if _PIN.search(b):
        return "pin"
    base = _LINE_SUFFIX.sub("", b)
    line = base != b
    base = re.sub(r"[#?].*$", "", base)             # a fragment or query on a path ("docs/x.md#pending")
    if "/" in base:
        segs = [x for x in base.split("/") if x]
        last = segs[-1] if segs else ""
        if len(segs) >= 3 or line or ("." in last and last.rsplit(".", 1)[1] in _EXT):
            return "path"
        if len(segs) == 2 and segs[0] in _DIRS and len(segs[1]) >= 2:
            return "path"                            # a conventional directory first: lib/parser, src/handler
        return "slash" if len(segs) == 2 and all(len(x) >= 2 for x in segs) else None   # lib/unknown; not b/c, w/o, i/o
    if _DOTTED.fullmatch(base):
        segs = base.split(".")
        if line or segs[-1] in _EXT:
            return "file"
        if (len(segs) >= 3 and segs[-1] not in _TLD) or any("_" in x for x in segs):
            return "module"                          # pkg.mock.Server, util.null_case; a host name (a.example.com) is not one
        return "dotted"                              # a.b, e.g., i.e.: never precise beside a placeholder
    return None


def _is_placeholder_commit(t):
    """A commit text with no digit that only says the commit is not known: nothing but placeholder, filler and label words
    ("unknown commit", "tbc", "not recorded", "no commit", "pending"); a phrase (it holds a blank, which no tag or branch name
    can) is also unstated when it holds any placeholder word ("pending approval from bob"). A name without a blank
    ("pending-release", "null-handling-fix") is a commit of its own unless all its words are placeholder words."""
    if any(c.isdigit() for c in t):
        return False
    words = re.findall(r"[a-z]+", t)
    if not words:
        return False
    if all(w in _NE_FILLER or w in _NE_PLACEHOLDER or w in _COMMIT_NOISE or w in _POINTER_WORDS for w in words):
        return True
    return bool(re.search(r"\s", t)) and any(w in _NE_PLACEHOLDER for w in words)


def _non_identifying(t):
    """The null object (an all-zero sha) or a generic moving pointer (see FLOATING_WORDS): names no particular commit."""
    return bool(_NULL_SHA.fullmatch(t) or _FLOATING.fullmatch(t))


def commit_id(c):
    """See _commit_id(): the rule, with the result cached per string (the validator asks it for every commit twice)."""
    return None if not isinstance(c, str) else _commit_id(c)


@lru_cache(maxsize=65536)
def _commit_id(c):
    """THE ONE IDENTITY RULE. Canonical spelling of a commit, or None when the commit is UNSTATED (non-identifying). A commit
    text identifies a commit when it is a sha (7+ hex digits, not all zero), a sha written inside decoration, or a name
    specific to one commit (a tag, a release, a branch such as feature/login); two spellings of one sha are one commit, and a
    name is only itself. It is unstated, as an unstated repo is, when it names no particular commit: not a string, an
    UNKNOWN-equivalent (is_unknown), a placeholder wording ("unknown (pending)", "tbc", "not recorded", "no commit"; see
    _is_placeholder_commit), the null object (all zeros), or a generic moving pointer (HEAD, main, origin/main, HEAD~1 ...;
    FLOATING_WORDS). Spelling: NFKC folding, removal of format/control characters and surrounding blanks, lower case, a
    leading label ("sha:", "sha1:", "sha256:", "commit ", "rev ", "hash ", "git:" ...) and edge punctuation removed; when what
    remains is not one bare hex but holds exactly one hex token of 7+ digits with a digit (a hex that is a token of its own, or
    glued to 0x, g or a label-: "0x<hex>", "g<hex>", "<hex> (HEAD)", "HEAD@{<hex>}", a URL ending in @<hex>,
    "commit-<hex>", "v1.0-3-g<hex>", a trailing ref name; all-digit hexes included), that hex is the commit. A hex glued to a
    name ("feature/abc1234-login") is part of that name; text naming two different hexes is its own identity."""
    if is_unknown(c):
        return None
    t = _COMMIT_LABEL.sub("", fold(c)).strip(_EDGE)
    t = re.sub(r"^0x(?=[0-9a-f]{7})", "", t)
    if not re.fullmatch(r"[0-9a-f]{7,64}", t):
        hexes = {m.group(1) for m in _HEXTOK.finditer(t) if any(x.isdigit() for x in m.group(1))}
        if len(hexes) == 1:
            t = hexes.pop()
    if is_unknown(t) or _is_placeholder_commit(t) or _non_identifying(t):
        return None
    return t


def _anchored(t):
    """True when the (canonical) ref text holds a concrete anchor. A LONE code token (every token with a letter is a code
    token, see _token_kind: status(), a.status, Status::Unknown, check_null()) is a location unless all its words are placeholder
    words (unknown(), null::nil). Beside plain prose words a code token anchors only when it is precise (a call, ::, URL,
    name@version, a file, a path; never a bare dotted name or two-part slash name, an abbreviation, a mention or an alternative) and holds a word
    of 2+ letters that is neither a placeholder nor a filler word (src/unknown/x.py). A number after a content word ("line 12") anchors."""
    toks = t.split()
    kinds = [(tok, _token_kind(tok)) for tok in toks]
    lone = any(k for _, k in kinds) and not any(k is None and re.search(r"[a-z]", tok) for tok, k in kinds)
    for tok, k in kinds:
        if k is None:
            continue
        ws = re.findall(r"[a-z0-9]+", tok)
        if lone:
            if any(w not in _NE_PLACEHOLDER and not w.isdigit() for w in ws):
                return True
        elif k not in ("dotted", "slash") and any(len(w) > 1 and w not in _NE_PLACEHOLDER and w not in _NE_FILLER and not w.isdigit()
                                                  for w in ws):
            return True
    prev = None
    for tok in toks:
        core = tok.strip(_EDGE + "?-")
        if _NUMBER.fullmatch(core) and prev is not None and prev not in _NE_PLACEHOLDER and prev not in _NE_FILLER \
                and len(prev) > 1:
            return True
        m = re.findall(r"[a-z]+", core)
        if m:
            prev = m[-1]
    return False


def non_evidence(ref):
    """True when a prose evidence ref only says the fact is unknown, missing, null, nil, unavailable or pending. The ONE
    rule for every ref (a token such as "status=unknown" or "<evidence>" is judged as a ref with spaces is): the words
    (NE_PLACEHOLDER / NE_FILLER) are read with quotes, "=", brackets, backticks, numbers and dates ignored; a ref with a
    concrete anchor (_anchored) is never judged by its words; a ref with no placeholder word and a weak mark (a digit,
    quote, "=", backtick, "#": "status 200") is evidence too; otherwise it is non-evidence when (A) every word is a
    placeholder or filler word, or (B) it holds a placeholder word and is short (<= 6 words): "status: unknown",
    "value is nil", "needs review". Callers judge a ref text only (a path or URL is an anchor)."""
    if not isinstance(ref, str):
        return True
    t = _SPACED_LETTERS.sub(lambda m: m.group().replace(" ", ""), _NA.sub("na", canon(ref, slashes=True)))
    words = re.findall(r"[a-z]+(?:['\u2019][a-z]+)?", t)
    if not words:
        return False
    ph = any(w in _NE_PLACEHOLDER for w in words)
    if _anchored(t) or (not ph and _WEAK.search(t)):
        return False
    if all(w in _NE_PLACEHOLDER or w in _NE_FILLER for w in words):
        return True
    return len(words) <= 6 and ph


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
