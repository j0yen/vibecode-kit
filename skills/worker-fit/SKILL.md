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
  UNKNOWN-equivalent placeholder (`unknown` in any case, surrounding whitespace, `none`, `null`, `n/a`, empty)
  counts as UNKNOWN wherever evidence is required (unit, child, host, artifact, account, consumer, target).
  Unsupported authority is refusal or UNKNOWN. A named alternate consumer gains no authority from its label
  or from a bare `alternate_authorized: true`: it counts as authorized only with
  `consumer.alternate_authorization_ref` naming the authorization evidence.
- An UNKNOWN effect is never replayed; an unreachable owner's claim is never taken over.
- Counts come from enumerated records, never from a declared number. Endpoint expansion rows and
  metadata counts are not reviewed tasks.
- Never print or copy credential-shaped lines (token=, sk-ant, password, bearer, key headers, api keys).
  The scripts redact credential-shaped values (`token=`, `key=`, `password=`, `secret=`, `bearer <x>`, `sk-...`)
  from everything they print; the envelope's free-text `next_action` is never relayed as the recommended action.
- Observation window: an envelope, worker or evidence observation older than 24 h
  (`STALE_WINDOW_SECONDS`) before the reference now, or dated more than 5 min after it, is refused. The reference
  now is `--now TS` (`--now system` = host clock) or, without it, the newest observation in the set; a lone
  envelope with no `--now` is only checked against its own newest observation, so pass `--now` for live use.
  Evidence may carry `head`, `repo`, `branch`; evidence naming a head (also `head=<sha>` inside its ref) or
  repo/branch different from the target is refused as WRONG_TASK.

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
- Duplicate task, or a second live task on the same repo+branch -> refusal for the newcomer (the later
  record; the running original is undisturbed); a different independent target progresses. Repo is
  compared case-insensitively and branch without a `refs/heads/` prefix.
- `declared_complete` is refused unless state is DONE and result.reviewed is known (plus every other
  required field known, no listed gap).
- Unreachable owner or UNKNOWN effect -> no takeover, no launch, no replay.
- NOT_STARTED, effect none, no worker evidence, no conflicting target -> `ready-unowned-slice`
  (recommendation, not a launch); NOT_STARTED with an applied effect is UNKNOWN (no replay), with an
  observed unit/child it is refused.
- Structurally null or non-JSON input (`{"envelopes": null}`, `{"rows": null}`, text) is UNREADABLE, exit 2.

## Not covered by this source slice
Installation, native Skill invocation, independent review, fleet-census classification and field use.
