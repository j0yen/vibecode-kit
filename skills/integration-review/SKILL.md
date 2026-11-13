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
  file and index only; never print or quote them. The validator never prints an evidence ref: it names
  the record and `evidence[i]`, and redacts any credential-shaped text in a message.
- UNKNOWN-equivalents (any case, surrounding whitespace, empty) count as UNKNOWN everywhere the
  complete check reads a field.

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
4. Compare schemas with `scripts/schema_compat.py OLD NEW --direction producer-first|consumer-first|both
   --consumer closed|open`. Changes are classified by who is on the new schema: an added enum value
   a closed consumer will receive is incompatible; one only a new consumer accepts can be
   compatible; a changed regex is UNDETERMINED, never compatible; unknown keywords present in either schema are
   breaking; an added items constraint tightens and a removed one loosens; enum values compare by
   JSON type (`1` is not `true`).
5. Record endpoints in a register (`schema/register.schema.json`) and run
   `python3 -I scripts/register_validate.py REGISTER.json`. It refuses `all-interfaces-complete`
   while any role, endpoint, caller, installed state, version, label or evidence is UNKNOWN/missing or
   any row is `family: UNASSIGNED` (kept under partial, counted, named by `record:code`), when there
   are zero records, when a timestamp is not parseable ISO-8601, or when `loaded` lacks `adoption_evidence` (process adoption; a unit listing is not that).
   Scope: the `installed` rule (stated path and 64-hex sha256) is enforced by the extractor only. A
   hand-written register states `installed` on the reviewer's word, so a complete claim made on it
   rests on that word; say so in the report.
   `path_or_command` separates two endpoints on one component; `sources` carries every stated
   source of a multi-repo component. To convert extraction rows run
   `python3 -I scripts/extract_register.py ENDPOINTS.jsonl OUTDIR` (sides and `loaded` are never
   invented; contradictory side marks give UNKNOWN; a component fuses across repos only on positive
   evidence: each path rooted in its own repo, identities stated and distinct; raw identity and
   evidence kept verbatim; input is split on newline only, must be UTF-8, and a duplicate JSON key
   rejects the row). Unreadable or wrong-shape input exits 2 in every script, never with a traceback;
   schema_compat never reports an unreadable input as rc 1.
5b. A "message lost" finding needs producer -> alias adapter -> installed waiter, each traced:
   `python3 -I scripts/lost_message_check.py FINDING.json`. A missing link keeps it conditional-risk.
   Links are typed (sha256 64 hex, commit 40 hex, non-blank ref) and must agree on any stated
   family, interface, message and actor chain; a disagreeing link is named and keeps conditional-risk.
   A trace that states none of those fields is not proven consistent; say so in the report.
6. Fill `templates/boundary-report.md`. Separate states: source change, tests, independent review,
   installed discovery, native Skill invocation, fleet coverage. State which are NOT done.

## Not this skill
Installing or linking itself, repairing a finding, replaying an effect, a universal gate.
