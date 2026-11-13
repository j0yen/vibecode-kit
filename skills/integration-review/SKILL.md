---
name: integration-review
description: >
  Per-boundary interface review. Given a boundary (producer, consumer, interface), runs the
  deterministic read-only helpers and reports each endpoint's identity (repo + commit or path +
  sha256), installed/loaded state or explicit UNKNOWN, and one label from {observed-defect,
  conditional-risk, historical-evidence, hypothesis, positive-control}. Use on /integration-review,
  "review this interface", "who consumes X", "does the consumer accept what the producer sends".
  Static review only: it is not live acceptance.
model: sonnet
effort: medium
last_updated: 2026-11-12
---

# /integration-review — one boundary, endpoint by endpoint

Narrow, additive, read-only. It does not repair, install, send events, call providers or write
production state, and it opens no tasks or PRs; findings go to their existing canonical owner row.

## Ground rules
- Static review is not live acceptance. A source reading proves what the source says, not what runs.
- A local checkout is not current upstream until fetched: `git fetch`, read `behind N`, read
  `origin/main` when behind, and say which tree was read.
- Missing facts are `UNKNOWN`, never a pass. An UNKNOWN effect is reported and never replayed.
- Coverage is derived from the enumerated endpoint records, never from a declared number.
- Credential-shaped evidence lines (token=, sk-ant, password, key headers) are referred to by
  file and index only; never print or quote them.

## Labels (exactly five)
`observed-defect` (reproduced on real source/behaviour) · `conditional-risk` (breaks only if a
condition holds that is not shown) · `historical-evidence` (past incident, not current state) ·
`hypothesis` (unproven) · `positive-control` (working behaviour, including a correct
committed-publish-pending). An endpoint not yet judged is `unclassified` and blocks a complete claim.

## Procedure
1. Name the boundary: producer, consumer, interface kind (http, cli, exit-code, filesystem, event,
   receipt, identity, schema, ordering, retry, trust, rollback, other).
2. Per endpoint capture identity (repo, commit or path, sha256, version) and installed/loaded
   state (`installed|loaded|source-only|UNKNOWN`). Hash with `sha256sum`; do not guess.
3. For an actor-name or case-pattern filter, run
   `python3 -I scripts/discriminator_check.py FILE --line N --names a,b,c --sha256 HEX`.
   The file is parsed as text, never executed. A refused name is `conditional-risk` unless it is
   an intended refusal (`--expect-refuse`); it is not evidence that live messages are lost.
4. Compare schemas with `scripts/schema_compat.py OLD NEW`: removed property/enum value, new
   required field, type change or unknown keyword is breaking; an optional addition is compatible.
5. Record endpoints in a register (`schema/register.schema.json`) and run
   `python3 -I scripts/register_validate.py REGISTER.json`. It refuses `all-interfaces-complete`
   while any role, endpoint, caller, installed state, version or label is UNKNOWN/unclassified.
6. Fill `templates/boundary-report.md`. Separate states: source change, tests, independent review,
   installed discovery, native Skill invocation, fleet coverage. State which are NOT done.

## Not this skill
Installing or linking itself, repairing a finding, replaying an effect, a universal gate.
