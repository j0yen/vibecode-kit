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
- UNKNOWN-equivalents count as UNKNOWN everywhere the complete check reads a field (role, component, host,
  installed state, label, source repo, version, evidence and adoption refs). One shared rule
  (`scripts/ir_norm.py`): not a string, or after Unicode NFKD, removal of combining marks and variation
  selectors and of zero-width/control characters, folding of every dash/minus variant to `-`, case folding,
  whitespace collapse and dropping of edge punctuation and `=`, either a value with no letter or digit (`?`, `???`,
  `-`, `--`, `...`) or one of the placeholder family `unknown unk n/a` (any dotting or spacing: `N.A.`, `n a`),
  `undefined null nil none unavailable unspecified tbd tba todo` and `not available/applicable/known`, matched with
  spaces, dots, slashes and dashes removed. In the placeholder rule every slash look-alike (U+2215, U+2044, U+29F8, U+FF0F, U+2571 ...) and the
  backslash fold to `/` first (never inside a path: a look-alike in `/proc/<n>/exe` is not that path), so `N∕A`, `n\a` and `none⁄` are `n/a`, `none`; two equal UNKNOWN repos are never one repo. The same function decides every field. A real component named
  `none` must be given another name.
- Credential-shaped text (token/secret/password words, `ghp_`, `sk_live_`, `glpat-`, `npm_`, `hf_`, `AKIA`, `eyJ`,
  `xox`, key headers, `key=value` forms, and any 32+ character mixed-case-and-digit run such as a 40-character
  secret key; such a run is masked wherever it sits and whatever precedes it: after `/`, `s3://bucket/`, `x-` or any
  path-like prefix; a long mixed-case path is masked too, a full lowercase hex sha is not. Judged on the fully normalized
  text (NFKD, combining marks and zero-width/control characters removed, then NFKC, before any pattern is applied) and
  after decoding `\uXXXX`, `\n`, `\t` and `\r` escapes; a token split by a newline, tab or carriage return, or by their
  JSON escapes, is joined and masked in every output path including the `by_role`/`by_label` counts) is redacted from every message the scripts print, from record ids, roles, property names,
  finding ids, actors, record fields and duplicate-key names, in every script (`discriminator_check.py` included); the redactor is a pattern list, so it is a net, not a proof.

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
   JSON type (`1` is not `true`); a `type` added tightens and one removed loosens; a `$ref` retargeted (or
   swapped with an inline schema) has its two local targets compared, a target that is not a `#/...`
   pointer in its own document is UNDETERMINED (a `$ref` swapped with an equal inline schema, or identical files, is
   compatible: note only); `additionalProperties` as a schema is compared (open -> schema tightens, schema -> open
   loosens), and a property added under an old `additionalProperties` schema is checked against that schema
   (producer-first incompatible, for a closed consumer, when the new type is not accepted by it); an unsupported
   keyword with equal text on both sides is not a change (a note; UNDETERMINED when the same subtree changes). A list-shaped or otherwise unreadable
   `properties`/`definitions`/`required`/`enum` is rc 2, never a compatible result.
5. Record endpoints in a register (`schema/register.schema.json`) and run
   `python3 -I scripts/register_validate.py REGISTER.json`. It refuses `all-interfaces-complete`
   while any role, endpoint, caller, installed state, version, label or evidence is UNKNOWN/missing or
   any row is `family: UNASSIGNED` (kept under partial, counted, named by `record:code`), when there
   are zero records, when a timestamp is not parseable ISO-8601 or has no UTC offset (an offset-less time is
   ambiguous and is never read in the host time zone) or is later than the reference time plus 300 s
   (`--now ISO8601-with-offset` sets the reference time, default the system clock), or when `loaded` lacks
   `adoption_evidence`. An omitted `captured_at` on a source or `observed_at` on an evidence ref is as refused as
   an unparseable one (staleness is unprovable); `adoption_evidence` timestamps follow the evidence rules when
   stated (garbage, offset-less, future, or observed before the source capture: refused), and an unstamped
   adoption ref is refused like an unstamped evidence ref (`missing-timestamp`, naming the record; a warning under
   `partial`): `complete` never passes while any adoption ref has no parseable `observed_at`. `validate(now=...)` takes an aware
   datetime or None (the wall clock); a naive datetime raises ValueError, it is never silently replaced.
   Adoption rule: a ref is a positive observation of a running process only when it states a
   `/proc/<n>/exe|cmdline|comm|status|stat|cwd|fd` path, or `pid` with a positive integer (no sign, no `+`/`-` before the digits,
   no `0`, `1e3`, `1.5` or `0x1f`; `pid=-1` is the no-process sentinel; `pid-1` joined by a hyphen is the one accepted spelling) plus `exe`, `cmdline`,
   `comm` or `command`, or a listing tool (`ps pgrep pidof lsof fuser top`) with `shows|lists|reports|names|found
   process <name>`. It is refused when it carries a negation or placeholder word (`no not none never dead exited
   unknown n/a tbd ...`), or names a unit (`systemctl`, `list-units`, `*.service|timer|socket|...`), and a tool name,
   `pid=` with no number, or a bare keyword is not an observation. The rule is textual and conservative (a
   cmdline that itself contains `no` is refused: restate it); it does not prove the observed process is the right
   one, the reviewer still owns that.
   Scope: the `installed` rule (stated path and 64-hex sha256) is enforced by the extractor only. A
   hand-written register states `installed` on the reviewer's word, so the validator's OK line names every
   installed record taken on that word ("installed state of N record(s) taken on the declarer's word"); a
   complete claim made on it rests on that word; say so in the report.
   `path_or_command` separates two endpoints on one component; `sources` carries every stated
   source of a multi-repo component. To convert extraction rows run
   `python3 -I scripts/extract_register.py ENDPOINTS.jsonl OUTDIR` (sides and `loaded` are never
   invented; contradictory side marks give UNKNOWN; equally named endpoints fuse only on direct proof of
   one component: the same content sha256, or the same canonical repo identity (URL, `.git`, trailing `/` folded)
   with the same normalized path; a fused record carries `fusion_basis` and every source. Same-named
   components in different repos, or with distinct commits, stay separate: distinct commits never fuse, whatever the basis
   (same sha256 or same repo identity and path), directly or through a chain of other members. A path-less member beside a
   fused cluster keeps its own record_id and key (the fused record then carries its first member path, or `fused:<rows>`),
   so the extractor's output always passes the validator's duplicate-record check. The old guess (paths rooted in their
   own repos, identities distinct) is a heuristic, off by default, enabled only by `--heuristic-fusion`; it is the one
   stated exception to the distinct-commits rule (its premise is distinct identities), it is a
   guess and its records are labelled `same-name-and-repo-rooted-paths-heuristic`; raw identity and
   evidence kept verbatim; an identity parses only when the whole string is
   `path+sha256:<path> <64 hex>` or `commit <40 hex>` (a trailing newline or `(dirty, unverified)` is UNKNOWN); input is split on newline only, must be UTF-8, and a duplicate JSON key
   rejects the row). Unreadable or wrong-shape input exits 2 in every script, never with a traceback;
   schema_compat never reports an unreadable input as rc 1.
5b. A "message lost" finding needs producer -> alias adapter -> installed waiter, each traced:
   `python3 -I scripts/lost_message_check.py FINDING.json`. A missing link keeps it conditional-risk.
   Links are typed (sha256 64 hex, commit 40 hex, non-blank ref) and must agree on any stated
   family, interface, message and actor chain, compared by JSON type and value (actor `1` and `true` differ);
   a claim is a message-lost claim in any case, separators, word order or synonym (`messagelost`,
   `lost-message`, `message-dropped`, `msg-loss`); a claim not recognised is not silently passed: the output
   states `"claim_recognised": false` and a `NOT-CHECKED:` line (the label is then the declarer's, unverified); a disagreeing link is named and keeps conditional-risk, and
   an actor chain that returns to an earlier actor is a cycle (inconsistent). A trace in which no family,
   interface or message is stated on two links, that lacks the producer or waiter actor, or in which family, interface,
   message or actor is UNKNOWN-equivalent (`UNKNOWN`, `?`, `N/A`, `tbd`, `none`, null) on two links (equal UNKNOWNs never
   prove agreement), is marked
   `"consistency": "unproven"` with an `UNPROVEN:` line; its label is not changed by the tool, so say in the
   report that consistency is unproven.
6. Fill `templates/boundary-report.md`. Separate states: source change, tests, independent review,
   installed discovery, native Skill invocation, fleet coverage. State which are NOT done.

## Not this skill
Installing or linking itself, repairing a finding, replaying an effect, a universal gate.
