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
  cert; split on separators and camelCase, so `passed`, `author` and `monkey` are not names) is hidden whatever the value
  looks like (also `=>`, `->` and full-width `＝` `：` separators); (b) any run of 20 or more characters from
  `A-Za-z0-9_-+/=.` that mixes letters and digits and is not a known-safe identifier (a 40/64-hex digest that follows
  head/sha/digest/commit/rev/oid/hash, a timestamp, a unit name, a path or branch made of short, lower-case or digit
  pieces) is hidden, a UUID included; (c) URL userinfo is hidden and so are the values of credential-named query
  parameters; (d) a credential-named key hides its whole value, scalar, array, object or YAML block (abbreviations
  `pw pat pin ak sk seed salt hmac privkey ...` count), and the password flags of named commands (`sshpass -p`,
  `mysql -p`, `unzip -P`, `7z -p`, `--pw`, `--password`) hide their value. Identity fields are validated by their own
  format, apart from that free-text redaction: a host, unit, scope (`child`), session, invocation, consumer, reviewer
  or artifact path whose pieces are plain words, digits, hex ids, UUIDs, compact timestamps or ULIDs, and that carries
  no credential name, flag or provider shape, is printed as given (a hex or UUID unit name stays usable); a long
  base62 / key-shaped piece, a credential-named pair or a provider shape in such a field is not an identifier and is
  hidden. A `target.head` that is a 7-64 hex sha prints. The run rule (b) applies to free text only. On top of that
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
  No signing or account boundary is demanded, and the reviewer need not run on a different subscription account. If the consumer is busy or unavailable the terminal stays durable, the named later
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
