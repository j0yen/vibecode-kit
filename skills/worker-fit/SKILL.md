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
last_updated: 2026-11-12
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
  compares case-insensitively against `unknown unk ? tbd tba todo - -- n/a n.a na none null nil undefined
  "not available" "not applicable" unspecified missing empty`; a value with no letter or digit left is a placeholder too.
  Where a field has a format it is validated positively: host/unit/child/consumer/reviewer are identifiers (no spaces),
  `target.head` is a hex sha of at least 7 characters when a record is declared complete.
  Unsupported authority is refusal or UNKNOWN. A named alternate consumer gains no authority from its label
  or from a bare `alternate_authorized: true`: it counts as authorized only with
  `consumer.alternate_authorization_ref` naming the authorization evidence.
- An UNKNOWN effect is never replayed; an unreachable owner's claim is never taken over.
- Counts come from enumerated records, never from a declared number. Endpoint expansion rows and
  metadata counts are not reviewed tasks.
- Never print or copy credential-shaped lines (token=, sk-ant, password, bearer, key headers, api keys).
  The scripts redact credential-shaped values from everything they print (recommendation JSON and text, validator
  lines, adapter output, UNREADABLE messages): `name=value` / `name: "quoted value"` pairs whose name holds
  token/key/password/secret/credential, `Authorization:` values (Basic/Bearer/...), `bearer <x>`, `sk-...` keys,
  GitHub/Slack/AWS/Google token prefixes, JWTs, PEM private-key blocks and URL userinfo (`scheme://user:pw@host`).
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
  timestamp, absurd nesting) is refused for that record only; the rest of the set is still evaluated.
  Defaults: window 24 h, future skew 5 min, clock = host clock.
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
   For canonical queue rows use `scripts/queue_adapter.py`; it keeps UNKNOWN where the row is silent.
3. `python3 -I scripts/envelope_validate.py [--now TS] ENVELOPES.json`: refuses missing/malformed fields,
   duplicate JSON keys (ambiguous), stale or future-dated observations, a RUNNING task with no evidence entry,
   NOT_STARTED carrying an observed unit/child, stale evidence,
   wrong task or stale revision, RUNNING without host+unit+child, DONE without a result artifact, invented
   ACK, replay of an applied/UNKNOWN effect, duplicate tasks, conflicting live targets, and declared-complete
   with UNKNOWN or listed gaps.
4. `python3 -I scripts/recommend.py [--now TS] ENVELOPES.json` (or `--queue ROWS.json`): one recommendation per task
   (`templates/recommendation-report.md`). A refusal is reported as a recommendation of UNKNOWN with its codes.
5. Hand the recommendation to the owning row; do not act on it from here.

## Decision rules (as implemented in recommend.py)
- Valid RUNNING on a reachable owner -> `reuse-active-worker`; never a second implementation.
- DONE with a durable result not yet reviewed -> `consume-completed-terminal` + `independent-verification`;
  never a new coder. The consumer for independent verification is never the worker's own session or
  invocation, and `result.reviewed: true` drops independent verification only with a distinct
  `result.reviewed_by` identity (not the worker's own); the flag alone is the author's word. If the consumer is busy or unavailable the terminal stays durable, the named later
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
