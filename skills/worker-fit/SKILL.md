---
name: worker-fit
description: >
  Per-task worker placement recommendation. Given one task (a canonical ask id plus revision, or an
  envelope file), runs read-only helpers and returns a RECOMMENDATION: the worker role
  (implementation | independent-verification | coordinator-decision | deterministic-service) kept
  separate from the disposition (reuse-active-worker | consume-completed-terminal |
  ready-unowned-slice | blocked | UNKNOWN), with the evidence used. Use on /worker-fit, "who should do
  this task", "is there already a worker on this", "should this be a new coder or a review".
  Recommendation only: it never launches, claims, kills, installs or writes canonical state.
model: sonnet
effort: medium
last_updated: 2026-11-13
---

# /worker-fit: one task, one placement recommendation

Narrow, additive, read-only. The output is a recommendation with its evidence. It grants no action
authority: launching, claiming, reviewing, installing and closing stay with their existing owners and
supported routes. It never launches, claims, kills, installs or writes canonical state, and it adds no
scheduler, coordinator, task store or mutation CLI.

## Ground rules
- A source-only or fixture result does not prove production behavior. The helpers prove shape and
  internal consistency of an envelope and the decision rules over it; installed bytes, effective
  invocation and live behavior are separate proof stages.
- A wrapper, queue row or claim string is not a worker launch. A worker is evidenced by observed
  host + unit + child (and the invocation/session that started it), read at a time not older than the
  revision it cites.
- UNKNOWN account, consumer, effect or target is reported as UNKNOWN, never filled in or guessed. Any
  UNKNOWN-equivalent placeholder counts as UNKNOWN wherever evidence is required (worker host/unit/child, artifact,
  ACK evidence, consumer, authorization reference, reviewer, target head, account): one shared normalizer applies NFKC,
  drops zero-width/format characters, collapses any whitespace, strips edge punctuation, brackets and quotes, and
  compares case-insensitively against `unknown unk ? tbd tba tbc todo - -- n/a n.a na none null nil undefined pending
  unavailable unset unassigned unsure "not available" "not applicable" "not set" "not known" "not provided" unspecified
  missing empty`, and also with every non-alphanumeric character removed, so `N / A`, `n\a`, `n/a/`, `unknown-`,
  `Not-Set` and a trailing `.`/`!`/`?` are the same placeholder (a longer real name such as `unknown-host-7` is not); a
  value with no letter or digit left is a placeholder too. The class is a vocabulary, not a closed list: a value is also a
  placeholder when every word in it is a placeholder word (`blank void nobody nothing later soon xxx ...`), a negated
  evidence word (`not known`, `no data`, `to be determined`), an `un<evidence word>` negation (`unidentified
  undetermined unobserved unverified unconfirmed unreported unnamed ...`), a bare assertion or a stop word, with at least
  one placeholder word and any digit groups or separators (`TBA/TBD`, `null/null`, `N/A (unknown)`, `pending 7`);
  `no-reply`, `not-set-up` and `unknown-host-7` hold a real word and stay names. A bare assertion word (`yes no true false ok self me same own
  authorized approved accepted confirmed verified done ack`) names nobody and cites nothing: it is never an identity
  and never a reference. Where a field has a format it is validated positively: host/unit/child/consumer/reviewer are
  identifiers (ASCII letters, digits and `. _ : @ / + % = -`, so `pid=77`, `%12`, `tmux:%12` pass; no spaces, not a placeholder, not an assertion word); an authorization reference and ACK evidence are
  references (not a placeholder or assertion word, with at least one substantive word unless it is a bare number or
  locator, and carrying a locator: a digit, or one of `: / # @`): `yes 1`, `ok 1`, `unknown:0`, `pending:1`, `tbd #1`,
  `n/a 1`, `yes/no` are refused as ACK evidence and as an authorization reference, `msg-4412`, `ack:msg-77`, `#123` and a
  URL are accepted;
  `target.head` is a hex sha of at least 7 characters when a record is declared complete. A RUNNING record whose
  evidence refs are all placeholders has no evidence. A placeholder `task_id` names no task and is refused.
  Unsupported authority is refusal or UNKNOWN. A named alternate consumer gains no authority from its label
  or from a bare `alternate_authorized: true`: it counts as authorized only with
  `consumer.alternate_authorization_ref` naming the authorization evidence.
- An UNKNOWN effect is never replayed; an unreachable owner's claim is never taken over.
- Counts come from enumerated records, never from a declared number. Endpoint expansion rows and
  metadata counts are not reviewed tasks.
- Never print or copy credential-shaped lines (token=, sk-ant, password, bearer, key headers, api keys).
  The scripts redact credential-shaped values from everything they print (recommendation JSON and text, validator
  lines, adapter output, UNREADABLE messages). Redaction is structural first, a list of provider shapes second:
  (a) the value of any `key=value`, `key: value`, JSON `"key": "value"`, `--flag value`, `-u/--user user:pass`,
  `Authorization`/`Cookie`/`Set-Cookie` header or URL query parameter whose name holds a credential word (token, key,
  secret, pass/password/passphrase/pwd, auth, cookie, session, signature, sig, credential, bearer, api, private, dsn,
  cert; split on separators and camelCase, so `passed`, `author` and `monkey` are not names; a credential word with digits
  or letters glued on counts: `key9`, `pw9`, `mykey3`, `apikeyv2`, `t0ken`) is hidden whatever the value looks like, and a
  key-shaped value (a piece of 6+ characters that mixes letters and digits and is no plain id, hex, date or word-like name,
  `Zq9Xk3Lm`) is hidden under ANY name, so no credential-word list is the only gate in free text (also `=>`, `->` and full-width `＝` `：` separators); (b) any run of 20 or more characters from
  `A-Za-z0-9_-+/=.` that mixes letters and digits and is not a known-safe identifier (a 40/64-hex digest that follows
  head/sha/digest/commit/rev/oid/hash, a timestamp, a unit name, a path or branch made of short, lower-case or digit
  pieces) is hidden, a UUID included; (c) URL userinfo is hidden and so are the values of credential-named query
  parameters; (d) a credential-named key hides its whole value, scalar, array, object or YAML block (abbreviations
  `pw pat pin ak sk seed salt hmac privkey ...` count), and the password flags of named commands (`sshpass -p`,
  `mysql -p`, `unzip -P`, `7z -p`, `--pw`, `--password`) hide their value. Credential pairs are
  also found inside JSON string escapes (`\"`, `\\`, `\uXXXX`, string-encoded JSON inside a string, up to four layers) and
  percent-escapes: the text is checked as written and as decoded, and the decoded view with the credential hidden is
  printed. Identity fields are field-aware and opaque by default: a host, unit, scope (`child`), session,
  invocation, account, model, effort, owner, task id, repo, branch, consumer, reviewer, artifact/event path, evidence
  ref (one locator token) or `target.head` is printed only through ONE trust gate (`_gate_values` in `envelope_validate.py`),
  which is the same gate for identities, queue-row fields and the values of free-text pairs. A piece prints only when it is
  (a) a word of the CLOSED vocabulary (`_ID_WORDS`, the caller's reviewed words for one row field, the DNS top-level labels:
  enumerated in the source, no credential word in it), (b) a bounded number (at most 7 digits; at most 14 digits in all), (c) a
  calendar-valid date or compact UTC timestamp, (d) one EXACT id grammar (a uuid 8-4-4-4-12, a hex id of 7-12, 32, 40 or 64
  characters mixing digits and letters, a ULID, an instance id `i-<17 hex>`, an IP literal in a host), but ONLY in a field whose
  OWN profile names that shape, in the form the profile allows (`_PROFILES`): a 32- or 64-hex id or a uuid alone is an
  `invocation` (a 32-hex id or uuid alone is also a `session`), a 7-64 hex id is a `target.head`; a hash-sized id beside
  other pieces is trusted only in a field template (`wm-build-<id>.service` and `run-r<id>.scope` in a unit, `child-<id>`,
  `sess-<id>`, `verifier-<id>`, `task-<id>`, `acct-<id>`, `evt-<id>`, `result-<id>.json`); account, owner, model, effort, repo,
  branch and host carry no hash-like id otherwise, so the same 256-bit value is an `invocation` and an opaque ref in an account
  or an owner. An unknown field carries no id at all, and a queue row none. One id per identity, two in a path, at most eight
  digits beside an id, and an id sits only beside closed-vocabulary pieces), or (e) a small amount of unlisted
  material: pieces of at most five characters with a TOTAL budget of eight characters per value, so no count of short pieces
  adds up to a credential. A vocabulary compound (`wmbuild1663impl2`, `WF1663Impl`, `r7wfitfix2`) is split into vocabulary
  words and bounded numbers. A value carries at most six vocabulary words (`_MAX_VOCAB_WORDS`; a path's directory words and a
  final file extension or unit type such as `.json` or `.service` are structure and do not count), so a passphrase of seven or
  more vocabulary words is an opaque ref in every field. Each field also has its OWN grammar (`_PROFILES`): `effort` is a closed
  set (`none minimal low medium normal default standard auto high xhigh max`); a `model` may end in a context tag (`[1m]`);
  a `unit`, `child`, `owner`, consumer, `branch`, `repo`, task id and path may carry ONE task slug, the fleet's exact slug
  template (one to three letters, two to five digits, at most two more groups of one or two letters and one digit, at most ten
  characters: `a1303rv8`, `wfr11`), never beside a hash-sized id and never in an account, model, session, invocation, host or
  queue row. A repo is `owner/name` with the owner one short piece of at most five characters; a `session` and a unit may carry
  the literal of their own id template (`session-<uuid>`, `tmux-spawn-<uuid>.scope`); a host with colons is an exact IP literal
  (a literal of random 16-bit groups is not one: at most two wide groups after the first). Identity invariant (re-review 12):
  a value prints only when every piece is accounted for by something this source fixes in advance (a word of the closed
  vocabulary of 273 words, a literal of the field's own template, an exact id template the field carries, a bounded number or
  date) and the rest fits the unlisted budget; how a value looks as language is never evidence. Pronounceability, dictionary
  membership, letter case and syllable structure are not read by any rule, because human-chosen and generator-made passwords
  (`sunshine`-class words, CV/CVC syllables) look exactly like names. A real name that is not enumerated is an opaque ref
  (fail-closed) until a reviewed source change adds its word to `_ID_WORDS`; the fleet's own unit, consumer, branch, repo and
  path words (`decide`, `regrade`, `agorabus`, `memlog`, `witness`, `swarm`, `repair`, `director`, `bootstrap`, `synthetic`, ...)
  are enumerated there. Residuals of this gate, each bounded by the code: (b) a value of up to six vocabulary words prints (about
  49 bits when drawn at random from the public list); (c) unlisted material of at most five characters a piece and eight a
  value prints in any identity field (a five-letter word, or a vocabulary word with a suffix of at most five characters such as
  `tail9z8y7`; about 38 bits as random lower-case letters, 0 beside an id). The cap on vocabulary words and the budgets apply to
  every field of the recommender and the adapter (each passes its own profile); only a library call that names no profile gets
  the bare gate; that size is the stated residual of the cap.
  Everything else (random letters, hex groups, digit groups, longer passphrases, a vocabulary word plus a random piece) is an opaque
  ref, whatever the field. A field grammar (no `user:password@` userinfo, ids as characters) makes a
  value VALID, never TRUSTED; the credential-name layers only refuse more and never let a value print. The envelope is never
  a trusted source. An identity that is itself a `name=value` pair needs a vocabulary name and a plain value (`pid=77` prints,
  `pswd=hunter2x` does not). A secret shorter than the budget (a few characters) and a bare hex id are indistinguishable from
  names and ids and are the stated residual. Queue rows (`queue_adapter.py`, `recommend.py --queue`) pass the same gate
  (`show_row`): row id, owner, wait, status, seq and claim print only when every token passes it; anything else is an opaque
  ref, and a non-string field is never printed. Free text is untrusted narrative: the value of any `name=value`,
  `name: value`, `"name": "value"` or `--name value` pair is hidden unless it is closed vocabulary (a word of the tool's own
  vocabulary, a time, a bracketed ref, a number of at most 2 digits, or up to 7 (up to 10 for a measurement such as `bytes`,
  `size`, `epoch`, `timeout`) under a closed list of numeric names, and at most four characters of unlisted material in at most
  two pieces, no more than two vocabulary words joined by `-` or `_`; plain JSON data of such keys and values; a closed MIME type
  under `Accept` / `Content-Type`; a percent-escaped value is read as what it decodes to) or the name is a schema field (`head`,
  `target.head`, a hex name such as `sha256`) whose value is a hex id or a trusted identity of that field; a name that merely ends
  in such a word (`mfa-hash`, `signing-rev`) is not the field. The closed numeric names are WHOLE names: a numeric word (`pid`, `seq`,
  `port`, `line`, `count`, `size`, `timeout`, `number`, ...) after at most three qualifier words from a closed list (`line`, `file`,
  `max`, `retry`, `exit`, `status`, `byte`, ...): `line_number`, `retry_count`, `file_size`, `exit_code` print their number,
  while `recovery_number`, `mfacount`, `unlock_limit` and `totp_index` do not, because ending in a numeric word is not being
  on the list. Whatever the NAME is, a plain word or a number outside the closed numeric list is hidden (`sessionkey=sunshine`,
  `code=abcdefgh`, `mfa=4821`, `mypass=1234`, `seedphrase=abc-def`, `mfa_number=482917`). No name is exempt: `code` is a name like any other.
  Residual by size: a value of three characters or fewer prints under any name, and so does a number of at most two digits.
  A credential name followed in prose by its value (`the password is sunshine`, `pass swordfish`, `my pin 482917`, `the api_key is
  Xk9fQ2mP7zab`, `private key X`, `client_secret X`, `X-Auth-Token X`; a name is any word run whose last word is a credential noun
  such as key, token, secret, pass, auth, creds, or ends in a strong noun glued to a qualifier of one to eight letters: `dbpass`, `userpass`, `rootpw`, `adminpwd`, `svctoken`; an English word that only ends in those letters, such as `compass`, `bypass`, `spin`, `sacred`, is a word) hides the next word, of any length, unless it is a state word (`required`,
  `missing`, `expired`, ...); the separator may be a space, `is`, `:`, `=`, `:=` or a quote, and a run of nouns (`secret key`)
  is one name. A bare `key`, `auth`, `bearer`, `code`, `unlock` or `vault` is also an ordinary word (`key point`, `exit code 2`): after one of them
  (and no credential qualifier such as api, private, client, recovery) a plain lower-case word, a closed-vocabulary word or a number
  of two digits reads as prose and prints, and anything else (a capital, a digit run, a mixed piece) is hidden; that is a stated residual. A credential word joined to
  a value in one token (`token-<v>`, `secret_run_<v>`, `tokenArYYbbah`) is hidden. The credential-name list above is an extra
  layer that hides more; it is never what lets a value print. Key names: only keys the schema defines print; any other key is an opaque
  `[opaque key <8 hex>]`, whatever it looks like. A value that does not validate is
  printed as an opaque keyed reference `[opaque <field> <8 hex>]` (HMAC-SHA256 over the field name and the value with a
  per-process random 128-bit key (`os.urandom(16)`), 32 bits shown: equal values give equal refs inside one run, nothing is recoverable, the ref
  does not depend on `PYTHONHASHSEED`, not stable across runs), never as the
  raw value; a placeholder stays UNKNOWN. A required identity (host, unit, child of a RUNNING record) that does not
  validate is UNKNOWN evidence, so the record is refused rather than reused. Mismatch findings (wrong task, repo,
  branch, head; duplicate task; conflicting target; unknown or duplicate key names) name the fields and carry opaque
  refs, never the raw values; a hex run in an evidence `ref` is read as a commit only after its credential layers are
  applied, so a hex under a credential name is never a head. Free narrative (coverage gaps, prose evidence refs)
  has no grammar and is printed through the redaction layers above. A `target.head` prints when it is a git object id: 7-64 hex characters of one case; digits only is an id only at the abbreviated lengths 7-12 or as git's null object id (40 or 64 zeros): any other run of digits (a 16-digit card, 13 or more digits) is a number, never a head. The run rule (b) applies to free text only. A temp path in Python's own tempfile name template (`/tmp/wf3-k2j_x9ab/b.json`: under `/tmp`, `/var/tmp`, `/dev/shm` or `$TMPDIR`, a first component `<prefix><8 of [a-z0-9_]>`) is echoed in a usage error: its 8-character random part is that template's id, in that position only; the prefix and every other piece still pass the key-shape check, the credential layers and the run rule (residual: an 8-character lower-case secret placed as such a component in the operator's own argv echoes). On top of that
  the named shapes stay: `Authorization:` values (Basic/Bearer/...), `bearer <x>`, `sk-...` keys,
  provider token prefixes as a class (AWS key ids `AKIA/ASIA/AGPA/AIDA/AROA/...`; Slack `xox?-`, `xoxe.`, `xapp-` and
  webhook URLs; Google `ya29.`, `AIza`, `GOCSPX-`, refresh tokens; npm `npm_`; GitLab `glpat-` and siblings; GitHub
  `ghp_/gho_/ghu_/ghs_/ghr_/github_pat_`; Anthropic/OpenAI `sk-...`; Stripe, SendGrid, Hugging Face, PyPI, Docker,
  Shopify, DigitalOcean), JWTs, PEM private-key blocks and URL userinfo (`scheme://user:pw@host`, the password may
  itself hold `@` or `/`; everything up to the last `@` of the unbroken run is redacted). Output that the terminal
  encoding cannot carry (a lone surrogate, any unencodable character) is written as a backslash escape, never an
  exception.
  The recommendation's `action` sentence is built only from tool-owned text: no envelope string (consumer, session,
  unit, owner, task id, authorization reference, `next_action`) is echoed into it; validated consumer identifiers appear
  in `next_consumer` / `later_consumers` and the redacted raw fields in `evidence_used`.
- Observation window: an envelope, worker or evidence observation older than 24 h
  (`STALE_WINDOW_SECONDS`) before the reference now, or dated more than 5 min after it, is refused. The reference
  now defaults to the trusted host clock (UTC now) for the CLI and the library alike; `--now TS` / `now=` inject
  an explicit clock (tests, replay), and `--now system` is an alias for the default. The newest observation in the
  set is never used as the reference, so stale or future input cannot green itself; a bad `--now` (garbage, naive,
  out of range) is UNREADABLE (exit 2); the library raises ValueError for a naive or out-of-range `now=`. A required
  observation time that is UNKNOWN (envelope always; worker for RUNNING; result for DONE; every evidence entry unless
  DONE) is unverifiable and refused (`UNKNOWN_TIMESTAMP`), never skipped (a state-UNKNOWN record can only yield an
  UNKNOWN disposition anyway). A record that cannot be evaluated (extreme
  timestamp, nesting deep enough to exhaust the recursion limit during validation) is refused for that record only
  (`MALFORMED`); the rest of the set is still evaluated. JSON nested beyond the JSON parser's recursion limit (tens of
  thousands of levels in CPython; the exact depth is interpreter-dependent) never reaches validation: the result is
  whole-file UNREADABLE (exit 2) and no record in it is evaluated. A queue row (`--queue`, `queue_adapter.py`) is walked
  iteratively and a row the interpreter cannot render becomes an empty-identity envelope that is refused alone. Both fail
  closed, with no traceback, at any nesting depth the parser accepts.
  Defaults: window 24 h, future skew 5 min, clock = host clock. Every recommendation records the reference clock it was
  made under, `reference_clock: {now, source: host|injected, live}` in JSON and a `reference clock:` line in text: a result
  made under an injected `--now` / `now=` says `injected` (`live: false`, "INJECTED --now: not a live result") and never
  reads as a live host-clock result; `--now system` is the host clock.
  Evidence may carry `head`, `repo`, `branch`; evidence naming a head or repo/branch different from the target is
  refused as WRONG_TASK. A head is recognised in its `head` field and in any commit-like name in its ref
  (`head=<sha>`, `head = <sha>`, `commit <sha>`, `sha=<sha>`, `rev <sha>`, a bare 7+ hex name); a name shorter than 7
  hex that is not equal to the target head is an UNKNOWN ref and is refused, never accepted as a match.

## Role is separate from disposition
| Role (who should do the next step) | Disposition (what state the task is in) |
|---|---|
| `implementation` | `reuse-active-worker` (healthy worker on the task; no new implementation) |
| `independent-verification` | `consume-completed-terminal` (a durable result exists; consume or review it, no new coder) |
| `coordinator-decision` | `ready-unowned-slice` (no worker, no conflicting live target) |
| `deterministic-service` | `blocked` (named dependency, unreachable owner) |
| | `UNKNOWN` (evidence missing, stale, malformed or refused) |

## Procedure
1. Get the evidence read-only (queue read, unit/process read, retained terminal, `git ls-remote`); never read
   a live FIFO, a secret-bearing environment or raw process arguments.
2. Write or reuse an envelope (`templates/envelope.template.json`; schema `schema/envelope.schema.json`).
   For canonical queue rows use `scripts/queue_adapter.py ROWS.json [OBSERVED_AT]`; it keeps UNKNOWN where the row is
   silent, and an extra argument or unknown option is a usage error (exit 2) that names it.
3. `python3 -I scripts/envelope_validate.py [--now TS] ENVELOPES.json`: refuses missing/malformed fields,
   duplicate JSON keys (ambiguous), stale or future-dated observations, a RUNNING task with no evidence entry,
   NOT_STARTED carrying an observed unit/child, stale evidence,
   wrong task or stale revision, RUNNING without host+unit+child, DONE without a result artifact, invented
   ACK, replay of an applied/UNKNOWN effect, duplicate tasks, conflicting live targets, and declared-complete
   with UNKNOWN or listed gaps.
4. `python3 -I scripts/recommend.py [--now TS] ENVELOPES.json` (or `--queue ROWS.json`): one recommendation per task
   (`templates/recommendation-report.md`). recommend.py takes exactly one FILE: a second file or an unknown option is
   a usage error (exit 2) that names the extra arguments, and nothing is evaluated; run it once per file (the
   validator accepts several files). A refusal is reported as a recommendation of UNKNOWN with its codes.
5. Hand the recommendation to the owning row; do not act on it from here.

## Decision rules (as implemented in recommend.py)
- Valid RUNNING on a reachable owner -> `reuse-active-worker`; never a second implementation.
- DONE with a durable result not yet reviewed -> `consume-completed-terminal` + `independent-verification`;
  never a new coder. The consumer for independent verification is never the worker's own session or
  invocation, and `result.reviewed: true` drops independent verification only with a distinct
  `result.reviewed_by` identity; the flag alone is the author's word. Independence contract: `reviewed_by` is an actor or
  session identity, not a subscription account. A `reviewed_by` equal (after case, spacing and NFKC normalisation) to the
  worker's own session, invocation, child, actor (`worker.account` name), `current_owner` or `source.owner` is the
  same-author case and is refused (independent verification kept); any other valid identifier is a distinct reviewer.
  No signing or account boundary is demanded, and the reviewer need not run on a different subscription account; account names are compared only as strings. If the consumer is busy or unavailable the terminal stays durable, the named later
  consumer (and an *authorized* alternate, if any) is reported, and no ACK is recorded.
- Duplicate task (task ids compared after normalisation), or a second live task on the same repo+branch -> refusal
  for the newcomer. The decision is state-aware, never positional: the RUNNING record of a task id is the original and
  stays `reuse-active-worker` in any record order; every other record of that id (ready, not started, done, a second
  RUNNING) is refused and never yields a ready/second-worker recommendation. With no RUNNING record the first listed
  record keeps its place. A different independent target progresses. Repo is
  compared case-insensitively and branch without a `refs/heads/` prefix.
- `declared_complete` is refused unless state is DONE and result.reviewed is known (plus every other
  required field known, no listed gap).
- Unreachable owner or UNKNOWN effect -> no takeover, no launch, no replay.
- NOT_STARTED, effect none, no worker evidence, no conflicting target, owner reachable -> `ready-unowned-slice`
  (recommendation, not a launch; NOT_STARTED with owner reachability UNKNOWN is UNKNOWN, no launch); NOT_STARTED with an applied effect is UNKNOWN (no replay), with an
  observed unit/child it is refused.
- Structurally null or non-JSON input (`{"envelopes": null}`, `{"rows": null}`, text) is UNREADABLE, exit 2.

## Not covered by this source slice
Installation, native Skill invocation, independent review, fleet-census classification and field use.
