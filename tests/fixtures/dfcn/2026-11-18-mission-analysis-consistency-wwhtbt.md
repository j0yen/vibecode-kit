---
session: 6c13f316-33dd-457a-9551-92ed11dc4ee5
task: A1724
title: "WWHTBT: mcg validator seam ready (A1724, edge E13): weakest readiness condition R4 held-out, falsifier = core canary"
date: 2026-11-18
asked_by: A1300 routing owner session 2883a65b, dispatching A1724 edge E13 (2026-11-18, about 4:5x PM PST)
answered_by: claude-opus-5-5 at xhigh effort, governed /wwhtbt author, session 6c13f316-33dd-457a-9551-92ed11dc4ee5 (launch row ~/.local/state/skill-routing/decisions.jsonl line 533, route opus-xhigh, task_id A1724)
status: reviewed
amended_by: 09dccd0e-7397-4895-af90-6e146e3d1d48 (claude-opus-5-5 xhigh, 2026-11-18 5:25 PM PST)
review_reason: independent_verifier_required (parallel-readiness/dependencies/out/handoff-A1300-E13.md line 78, G-E13-4, asks for a distinct non-author review of this page). This worker was told to launch no other worker, so the review was not launched here; the dispatcher routes it.
---

Paths below are relative to `/home/jsy/wintermute-operations/mission-contract-graph-20261117/` unless they start with `~`. "CONTRACT" = `design/out/contract/CONTRACT.md` (sha256 010d43b3…, mtime 3:52 PM, GEN8 draft, read by heading); "vocabulary" = `design/out/contract/vocabulary.json` (sha256 f2e03799…, `contract_version` 1.0.0-draft.8 at line 3; the bytes were the same at 4:5x PM and 5:0x PM, though the mtime moved to 4:57 PM); "PRD" = `design/out/prd-home/build-queue/PRD-mcg-core-gen8.md` (sha256 75354cb9…). gen8 is the newest core generation: the A1724 author created it at 4:57 PM while this page was being written. PRD-mcg-core-gen7.md now carries `Superseded-by: PRD-mcg-core-gen8.md` and `transferred_acs` (gen7 lines 16-17). gen8 pins draft.8 and absorbs gen7's eight ACs one for one (PRD line 13). "edges" = `design/out/prd-home/notes/missions/mcg-validator.edges.jsonl` (current), and "GEN7 review" = `review-gen7/assembled/out/assembled-review.md`. The GEN8 draft changes § 13's control-outcome and held-out identity text (D44-D46) but keeps R1-R4 and their order. The frozen GEN7 § 13 and the current § 13 were diffed at 4:5x PM.

# End-state

The evidence holds no verbatim Joe quote. The seed note records his instruction in Hermes's words (`design/out/prd-home/notes/missions/mcg-validator/external/mission-contract-graph-20261117.md` line 46: stop closed-loop work "until the Mission Contract Graph is ready"; line 50): "Readiness to resume closed-loop means a populated, independently assessed graph whose coverage is reconciled to the frozen scope, with an accepted executable validation path that rejects the known-bad handoffs and accepts a compatible control. A documented graph or self-reported compatibility does not qualify. The current defective mission instance must truthfully report FIX, not be forced green." [P4: the line's third sentence, left out of the filed quote, restored.] Analysis asked 2026-11-18 at 4:53 PM PST (from `date`).

Hermes, the terminal consumer, holds one `mcg readiness` object for the A1724 instance's one `input_digest`. In it, R1, R2, R3 and R4 are each `met`, in that order, recomputed from the records of one binary (CONTRACT line 316, line 339, line 352). A green `mcg check` record alone never counts (CONTRACT line 356; vocabulary line 736, last sentence). Hermes observes this by comparing the output's `read` sha256 values with the artifacts it issued and pinned (CONTRACT line 316).

[P4] At readiness the instance's own `mcg check` still truthfully exits 1 on its rule and witness findings. `design/out/instance/wm-loop-gen7/expected.json` gives `exit` 1, and its error-level `must_count` entries are 433 rule and 19 witness findings, nothing else. Those findings are the repair worklist and do not block R1 (CONTRACT line 347), and PRD AC 8 pins the core slice's counts (PRD line 121). Readiness is never a green instance.

# Leaves

The contract fixes each condition as one condition whose causes combine (any FIX makes it FIX, otherwise any UNKNOWN makes it UNKNOWN; CONTRACT line 316, D36). The leaves keep that split and order, so this page and the readiness output read alike. Each leaf lists its failure modes under it.

1. **R1 validator record** — testable. The R1 identities hold and the report is consistent. Its `evaluated_codes` are every vocabulary code: 67 codes over four slices, core 28, rules 29, replay 8 and views 2 (vocabulary `codes` counted by `slice`). The attestation is schema-valid, the report has no structural error and no binding error that R1 owns, and the author controls record passes against the author suite (CONTRACT line 347). The draft.8 suite has 300 controls (`design/out/controls/expected.json`); GEN7 had 291 (CONTRACT line 697).
   - Test: each slice's AC 1 at its land (core: `mcg controls contract/controls --record …`, PRD line 114), about 5 min once a binary exists (estimate). Full R1 comes only at the views land, because a report short of every code is UNKNOWN for R1 (CONTRACT line 325): `mcg readiness <bundle> --attest <a> --check-record <c> --controls-record <r> --controls contract/controls` (vocabulary `commands`, readiness entry).
   - Kills the plan: R1 FIX, meaning an author control or the base does not pass, or an identity does not match.
   - Today: no `mcg` binary and no `j0yen/mcg` repo exist (PRD line 29). The GEN7 review left the core slice ineligible on G7-IDENTITY-02 (GEN7 review line 13), the `suite.role` defect under leaf 4, which also fails R1. GEN8 makes the role a required suite member (D44, PRD line 29). That repair is not yet accepted: CONTRACT § 22 still reads "COUNTS PENDING" (line 709), and no `review-gen8` directory existed when the mission root was listed at 4:5x PM.
2. **R2 coverage complete** — known (false today). 1,239 coverage rows are unknown and 1,074 proposed exclusions are open (CONTRACT line 703; GEN7 review line 14). The coverage decider holds 1,447 proposals (1,277 accepts, 154 refusals, 16 unresolved), none integrated or attested (GEN7 review line 232). The path is known: population work plus a Hermes-attested `decisions.json` (CONTRACT line 312, line 360). R2 needs no binary to advance, and the gap is already visible.
3. **R3 graph fidelity** — testable. This needs an attested independent `graph_fidelity` PASS with exactly one faithful disposition per graph element and none of the four verdict findings (CONTRACT line 349).
   - Test: edge E11 (`external:fidelity-review`, edges line 12) can run on the graph now, before any binary exists. Cost: one independent review session, about 60-180 min (estimate, not measured).
   - Kills the plan: `graph_fidelity` FIX, or an element without a faithful disposition.
   - E11 must decide D30's receipt repairs, D39's 36 flow keys and two waits (CONTRACT line 699), and the source gap left to it at CONTRACT line 443. No producer has been commissioned since GEN2 (`review-2/out/chain-review.md` line 116; GEN7 review line 14).
4. **R4 held-out** — assumed. A held-out suite is authored and run outside the author and builder lineages and frozen before the binary runs it. Every control and the suite's own base pass under Control outcomes. Its sessions are listed as independent with purpose `held_out`, and its SHA256SUMS differs from the author suite's (CONTRACT line 350; vocabulary line 736, clause (R4)).
   - It cannot be tested today. No binary exists (PRD line 29) and no suite exists (E12 producer `external:held-out-suite`, edges line 13; GEN7 review line 14). By design, the acceptance suite stays unseen until the binary under acceptance runs it (`design/out/controls/HELD-OUT.md` line 3, line 11). The full judgment needs a report with every code evaluated (vocabulary line 736, Control outcomes), so it comes after all four slices are built.
   - Failure mode (a), reachability: a conforming build may be unable to write a held-out record that readiness accepts.
   - Failure mode (b), agreement: the binary is built to expectations from the author lineage and may disagree with an independent reading on cases it never saw.

# Weakest link

**R4 held-out.** It is the leaf most likely to be false, and finding out late costs the most.

If only R4 fails, the end-state still fails: the bundle is ready only when all four conditions are met (CONTRACT line 352).

R4 is the most likely to be false for three reasons:
- **Agreement (b).** Every independent review so far returned FIX on the author's reading:
  - GEN1, review 32c3f70f (`frozen-design-gen5/report.md` line 11);
  - GEN2, 019ba9b5 (`review-2/out/chain-review.md` line 162);
  - GEN3, 94f85379 (CONTRACT line 426);
  - GEN5, 35d7e039 (CONTRACT line 543);
  - GEN6, 9653ff43 (CONTRACT line 642);
  - GEN7, fd714c59 (GEN7 review line 9).

  GEN8 is still in repair (CONTRACT lines 707-709, "COUNTS PENDING"). ~~In each generation the author also records~~ [P3] In GEN2 and GEN3 the author recorded ambiguities that "two implementations could resolve differently" (CONTRACT line 386, line 407). The expectations the builder will build to were reasoned from the contract by the author lineage and cross-checked with the author's own reference evaluator (PRD line 95). That evaluator was itself defective ~~in GEN4 (CONTRACT line 452) and GEN5 (CONTRACT line 532)~~ [P3]: the GEN3 evaluator, found during GEN4 (CONTRACT line 452), and the GEN5 evaluator (CONTRACT line 532). GEN7's transform tooling was too (CONTRACT line 693). A held-out run is the first executable meeting between that lineage's readings and an independent one.
- **Reachability (a).** Through GEN7, no conforming build could write the R4 record. `suite.role` had no determining input, while readiness required `author` for R1 and `held-out` for R4, "so any constant a build writes fails one of the two" (GEN7 review lines 55-57). An honest slice controls record also came out FIX (GEN7 review lines 59-63). Both defects were found by reading; ~~no held-out record has ever been produced~~ [P1] no runner has written a held-out record from an independently authored suite. The author's readiness fixtures do carry a held-out record (`design/out/controls/readiness/records/held-out/controls.record.json`, runner session `control-held-out-runner-fixture`). Its suite is a synthetic two-control suite copied from the author suite under new ids (`design/out/controls/readiness/suite-held-out/expected.json`, `status`). The `held-out` role is the label the author's fixture generator writes into that suite, and its stand-in writer copies it into the record (`design/gen8-repair/out/work/tools/gen_controls_gen8.rdy.py` lines 42, 55-59, 89, 113; in GEN7 the generator passed the role into the record as an argument, `design/out/population/author-tools/gen_controls_gen7.rdy.py` line 109). RD-ready shows R4 met only in the author evaluator standing in for a binary. `design/out/controls/readiness/cases.json` expects R4-held-out `met` in 44 of 77 cases, and its `status` reads "records produced by the author reference evaluator as a stand-in binary". That is the tautological-fixture class rhymed below. GEN8's D44 and D46 are author repair claims, not accepted (CONTRACT line 339, line 343, line 709).
- **Honesty.** R4 is the only condition that runs the binary on input it never saw. § 13's stated limit says a binary that consistently forges its own reports is caught only when the consumer re-executes the frozen binary or the held-out runner session executes it (CONTRACT line 354). R4's run is the second of these.

Finding out late costs the most because the acceptance run comes after core, rules, replay and views are built (vocabulary `slices` at line 587; Control outcomes at line 736). An independent reviewer triages a disagreement to the binary, the held-out control or the contract (HELD-OUT.md line 25). A cause in the contract opens another GEN. GEN5, GEN6 and GEN7 each changed the vocabulary, so no digest of the prior generation carried over (CONTRACT lines 539, 638, 705). That means re-pinning the controls and PRDs of slices already built.

Why the other three rank lower:
- **R2** is the surest failure today, but it is already known, so nothing is found late, and it advances without a binary.
- **R3** can be tested now through E11, with no binary. A late R3 FIX changes the graph and its `input_digest`, so the records and the attestation are re-issued, but no slice is rebuilt.
- **R1** is checked against the visible author suite at every slice land (AC 1), and the builder iterates against it.

The GEN7 review also labels its routed cycles obligations R1-R5 (GEN7 review line 19). Its "G7-IDENTITY-02 = R1" means routed obligation R1, not readiness R1.

**Falsifier (cheapest): the core canary.** This is a spent suite shaped like the held-out suite. It is read twice: against the author evaluator before any binary exists, and against the built core binary at the core land.

1. **Write it now.** No binary is needed; it takes about 60 min of one session (estimate).
   - Author: a session outside the effective author lineage and outside the builder lineage. The author lineage is c6a71acb, 5dee3894 and their successor d2c90b55 (HELD-OUT.md line 7; CONTRACT line 695).
   - Contents: about 8 core-slice controls over the public `controls/base/`, aimed at the core rules GEN6-GEN8 changed:
     - D7 and D8: integer numbers and duplicate member names;
     - D16: reciprocity;
     - D33: least citation;
     - D34: dangling names;
     - D38: eligibility branches.
   - Its `expected.json` declares `role: held-out`. Its SHA256SUMS is frozen before anything runs it.
   - It stays outside the packet and the PRD home. Its results reach the builder, so it is spent, and no canary case is reused in the E12 acceptance suite.
2. **Pre-read** (minutes, now). The canary author runs the author evaluator's `controls` command over the canary (`design/out/population/author-tools/expect.py`, `main` at line 3000).
   - Kill: the evaluator fails to reproduce a canary expectation, unless triage (HELD-OUT.md line 25) finds the canary case wrong.
   - The pinned expectations were reasoned by the author lineage and cross-checked with that evaluator (PRD line 95). An evaluator that disagrees with an independent expectation therefore marks a reading that the pinned set was checked against, and a binary built to the pinned set would likely carry the same reading.
   - [P2] **R4 readiness rehearsal** (minutes, now). The core-land read cannot reach the readiness recomputation, because `mcg readiness` is slice views (vocabulary `commands`, readiness entry). The second GEN7 reachability defect, an honest slice controls record recomputed as FIX, was in that path (GEN7 review lines 59-63). The author evaluator's `readiness` command already takes `--held-out-record` and `--held-out` (expect.py lines 3024-3027), so the canary author and runner rehearse R4 there:
     - The evaluator's `controls <canary> --record <dir>` writes only per-control reports into `<dir>` (expect.py lines 3017, 2574-2576). It writes no `mcg-record/5` controls record and takes no runner flags. So the canary runner assembles the held-out record from those reports by the stand-in writer's recipe (`gen_controls_gen8.rdy.py` `controls_record`, lines 54-78): `suite.role` copied from the canary's `expected.json`, `suite.manifest_sha256` its SHA256SUMS sha256, each row's report named by path and sha256, its own runner session, and `binary_sha256` the stand-in's (`cases.json` `stand_in_binary_sha256`).
     - Run `expect.py readiness bundle --attest <rehearsal attestation> --check-record records/check.record.json --controls-record records/author/controls.record.json --controls suite-author --held-out-record <canary record> --held-out <canary dir>`, from `design/out/controls/readiness` and with RD-ready's other arguments (`cases.json`, RD-ready `args`). The rehearsal attestation is a temp copy of that directory's `attest.json`. Its `held_out` entry names the canary's SHA256SUMS sha256, control ids, author and runner, and its `sessions` list the canary author and runner with role `independent` and purpose `held_out` (the fields expect.py reads at lines 2945-2972). It is never counted.
     - Kill: R4 is not `met` for any cause other than a canary expectation disagreement, which the pre-read above already kills.
     - Limit: the record is assembled, not written by a build. A pass shows that readiness accepts an independent suite, record and attestation; whether a build can write that record stays with step 3 and the views land.
3. **Core-land read** (about 1 min, estimate). The canary's runner session runs `mcg controls <canary dir> --record <r> --runner-task <t> --runner-session <s>` with the binary that passed AC 1. Any one of these kills the plan:
   - the record's `suite.role` is not `held-out` (reachability);
   - its `suite.manifest_sha256` is not the sha256 of the canary's SHA256SUMS (reachability);
   - its `binary_sha256` differs from the AC 1 author record's (reachability);
   - the base or any canary row is not `pass` under its core projection (agreement).

   A kill stops the rules slice's build start until an independent reviewer triages it.

A canary pass does not make R4 met. It removes the earliest and cheapest ways R4 can fail, and it does so two slices and one acceptance run sooner.

**Threading into the core PRD's AC 1.** The dispatch named PRD-mcg-core-gen7 AC 1. gen8 now supersedes gen7 and carries the same AC 1 (PRD line 13, line 114), so the thread goes into PRD-mcg-core-gen8 AC 1. This is text for the A1724 author; this page edits no PRD.

- **Builder-visible clause, appended to AC 1.** The builder can test it, and it names no hidden case (PRD line 46): "; a temp copy of `contract/controls` whose `expected.json` declares role `held-out`, with its SHA256SUMS rewritten, yields a record whose `suite.role` is `held-out`, whose `suite.manifest_sha256` is the copy's SHA256SUMS sha256 and whose `binary_sha256` equals the author run's, and every row still matches its core projection".
  - It kills a constant or path-derived role (the G7-IDENTITY-02 class) at the core land.
  - The clause could not pass on gen7's draft.7 packet, because `role` had no input there (GEN7 review line 55). gen8 pins the D44 packet, in which `role` is a required suite member (PRD line 29, line 65; `design/out/contract/schema/controls.schema.json`, `$id` `urn:mcg:controls:8`, `role` enum `author` | `held-out`), so the clause can pass there.
- **Consumer step,** for the PRD's `Falsifier:` line (PRD line 83) and an edge row the A1724 author names (E12's or a new one): "At the core land, the canary runner runs the frozen core canary on this build; any kill result stops the next slice's build start until triaged."
- **Route fact.** gen8 is `Status: blocked` (PRD line 3). The PRD records that dream.amend accepts only `Superseded-by` and `transferred_acs` on a blocked PRD (PRD line 14). Whether gen8's AC 1 body can still take the clause, or a successor carries it, is the A1724 author's route to decide.

# Backward rhyme

This covers the testable and assumed leaves (R1, R3, R4). Paths are under `~/Notes/wiki/answers/` unless noted.

R4 (these past failures move it up the ranking):
- 2026-11-06: `2026-11-06-hold-aware-alarms-overnight-three-green-worker-heads-failed-independent-review-bundle-source-only-hermes-watchdog-429-gap-implementer-owned-unit-of-proof-five-whys-rhyme.md` lines 65, 71, 73 → three worker heads were green on their own tests and failed independent review. Its weakest link was "the implementer-owned unit of proof". Here, the builder builds to author-lineage expectations, and R4 is the one unit of proof neither lineage owns. Root rhyme.
- 2026-10-13: `2026-10-13-ryzen7-red-legs-five-whys-rhyme.md` line 22 → "The fixture was written to the consumer's expectation, not to the producer's output (agent-written fixture, tautological until proven)." Here, the author's own evaluator cross-checks the author controls (PRD line 95).
- 2026-10-30: `2026-10-30-ryzen7-wmb-gate-v38-replay-b99b56f4-fail-full-census-fails-diffed-against-lib-only-base-cache-tautological-selftest-fixture-five-whys-rhyme.md` line 30 → a selftest fixture wrote the same string into both sides, so it proved only that two equal sets are equal. Here, the GEN7 transform tooling found four defects of its own (CONTRACT line 693).
- 2026-10-17: decision ledger `~/.claude/projects/-home-jsy/memory/project_sonnet_operator_decision_ledger_20261016.md` line 328 → "the fake box never checked names = tautological fixture". Here, a double that never applies the consumer's check stands in for the consumer.
- 2026-10-31: `2026-10-31-ryzen7-p368-relaunch-mutation-expect-mismatch-hand-typed-expect-t1-unreachable-from-finalize-run-no-reach-check-before-launch-five-whys-rhyme.md` line 43 → a mutation expectation could not be reached from the code it named, and no reach check ran before launch. Here, no conforming build could write the R4 record through GEN7 (GEN7 review lines 55-57); this was found by reading, never by a run. The canary's reachability kill (step 3) is that reach check.
- 2026-11-17, the GEN1 false green: `frozen-design-gen5/report.md` line 11 → "validator green" stood in for readiness. CONTRACT line 426 names the recurring class: "an acceptance predicate evaluated on a stand-in instead of on the identity it is about". An author-suite pass standing in for a pass on an unseen suite is the same class. The governed /5whysandrhyme page for that failure is E13's other half, not this page.
- LIVE TRAPS (`~/.claude/projects/-home-jsy/memory/MEMORY.md` line 47): the 11-06 hold-aware alarms trap, the same failure as the first R4 bullet. No other LIVE TRAPS line names this assumption.

R1:
- 2026-10-27: `2026-10-27-mcphost-deploy-82-caddy-429-subset-verify-green-master-red-five-whys-rhyme.md` lines 31, 48 → a subset verify read green while the full gate was red. Here, a slice report is green only over its projection. R1's every-code clause (CONTRACT line 347) and D46's full-judgment rule (vocabulary line 736) stop a slice green from standing in. Branch, already guarded.

R3:
- No five-whys page was found for an independent review whose producer was never commissioned. The nearest records are CONTRACT line 636 ("an owner label is not completion") and the GEN2 chain review's "Both are external with no commissioned producer" for E11 and E12 (`review-2/out/chain-review.md` line 116), unchanged at GEN7 (GEN7 review line 14). Branch.

# Mechanisms

- R4 reachability clause in core AC 1 — ⚙ PRD-mcg-core-gen8 line 114, or its successor if the blocked body cannot change — owner A1724 author — state SPEC (proposed on this page, not threaded)
- Core canary suite, its pre-read ([P2] with its R4 readiness rehearsal) and its core-land run — ⚙ consumer step in the core PRD's `Falsifier:` line + an edge row in `design/out/prd-home/notes/missions/mcg-validator.edges.jsonl` — owner Hermes (commissions the independent author and runner, as for E12) — state SPEC
- R4 recomputation — ⚙ `mcg readiness` (PRD-mcg-views R4; vocabulary `commands`, readiness entry) — owner A1724 builder — state SPEC (no binary)
- Held-out acceptance suite, with the builder sessions listed in `author_sessions` before the run (D27) — ⚙ edge E12 (edges line 13) + HELD-OUT.md lines 7-11 — owner Hermes — state SPEC (no producer)
- R1 author-controls run per slice — ⚙ each slice PRD's AC 1 (core: PRD line 114) — owner A1724 builder — state SPEC (no binary; core stays ineligible on G7-IDENTITY-02 until D44 is accepted)
- R2 attested decisions and coverage population — ⚙ `decisions.json` attested under § 14 (CONTRACT line 360) — owner Hermes as decider, plus the population owner — state SPEC (1,447 proposals, none integrated; GEN7 review line 232)
- R3 fidelity verdict — ⚙ edge E11 (edges line 12) — owner `external:fidelity-review`, commissioned by Hermes — state SPEC (no producer)
- E13 provenance for this page — ⚙ launch row `~/.local/state/skill-routing/decisions.jsonl` line 533 + `wwhtbt=ran <path>` in the A1724 run note (handoff-A1300-E13.md line 77, G-E13-3) — owner A1724 author — state SPEC

Architecture: keep — R1-R4 and the held-out suite at acceptance stay as designed. The core canary adds an earlier, spent reading of R4's risk and replaces nothing.

# Hand-off

This is a plan, not a product feature, so it goes to no /dream run. Its step 1 is the core canary: author it now and pre-read it against the author evaluator. Its AC 1 thread is the builder-visible reachability clause plus the consumer step above. The A1724 author threads both at a compatible checkpoint. The dispatcher (A1300) routes the review named in `review_reason`.

## Amendments after claude-opus-5-5 regrade (60a28a4b-a243-4eaf-b08d-62bc4942b17a), 2026-11-18 5:26 PM PST

The independent review graded the page APPROVE with four LOW findings (`dependency-execution/A1300/out/a1724-pages/wwhtbt/review/out/review.md` and `findings.jsonl`). It changed no leaf label, the weakest link, the falsifier's structure or the AC 1 clause, so none of those changes here. Each finding is applied below and marked `[P<n>]` in place; struck text is the filed original. Amendment author: session 09dccd0e-7397-4895-af90-6e146e3d1d48 (claude-opus-5-5 xhigh). Every read below was taken at 5:2x PM PST.

Evidence drift since filing (not a finding): CONTRACT is now sha256 d12871e9… (mtime 5:19 PM) and PRD-mcg-core-gen8 is c1fa1187… (mtime 5:20 PM); vocabulary is unchanged (f2e03799…). Every CONTRACT line this page cites still matches the reviewer's excerpts (`review/out/scratch/contract-lines.txt`) except § 22's "COUNTS PENDING" (lines 708-709). § 22 now carries its counts (`grep -c 'COUNTS PENDING'` gives 0). Line 709 now opens "These are author repair claims, not independent acceptance", and line 753 says "nothing here is accepted". So the page's claim that D44-D46 are unaccepted still holds; only the quoted marker is gone. No `review-gen8` directory exists. PRD lines 3, 13, 14, 29, 46, 65, 83, 95 and 114 still carry what the page cites.

- **P1 (Weakest link, Reachability (a)).**
  - Wrong: "no held-out record has ever been produced" is false as written. The author's readiness fixtures hold one, and the clause left out the evidence that best supports the page's argument.
  - Corrected text, in place: no runner has written a held-out record from an independently authored suite. The fixture record is over a synthetic two-control suite copied from the author suite, its role is the author generator's label, and RD-ready shows R4 met only in the author evaluator standing in for a binary.
  - Refinement of the finding's wording: the finding says the role was "set by hand". The GEN8 generator writes `role: held-out` into the synthetic suite and its stand-in writer copies the role from there (`gen_controls_gen8.rdy.py` lines 42, 55-59, 89, 113). The GEN7 generator passed the role into the record as an argument (`gen_controls_gen7.rdy.py` line 109). Either way the label is the author's, not a runner's, so the finding's point holds and the page names the generator instead of "by hand".
  - Reads: `python3 -I` over `records/held-out/controls.record.json` gave `suite.role` held-out and `runner.session` control-held-out-runner-fixture. Over `cases.json` it gave R4-held-out `met` in 44 of 77 cases, RD-ready among them, and `status` "records produced by the author reference evaluator as a stand-in binary". `suite-held-out/expected.json` `status` reads "SYNTHETIC HELD-OUT SUITE FIXTURE for readiness: 2 controls copied from the author suite under new ids". The frozen GEN7 fixture (`design/gen8-repair/out/frozen-design-gen7/controls/readiness/`) has the same record over a suite whose `expected.json` has no `role` member. GEN7 review lines 55-57 bear out that no runner could write it then.
- **P2 (Falsifier, step 2 Pre-read).** Applied in corrected form; the finding's literal command is disputed.
  - Wrong: the pre-read ran only the evaluator's `controls` command and killed only on agreement (b). The readiness recomputation, where the second GEN7 reachability defect lived (GEN7 review lines 59-63), is slice views, so the core-land read cannot reach it before the views land.
  - Corrected text, in place: a new **R4 readiness rehearsal** sub-step under step 2, with the finding's kill ("R4 is not met for any cause other than a canary expectation disagreement"), a rehearsal attestation that is never counted, and a stated limit. The canary mechanism line under Mechanisms names it too.
  - Dispute, for the next reviewer: the finding's `expect.py controls <canary> --record <r>` followed by `readiness … --held-out-record <r>` does not compose. The evaluator's `--record` is a directory into which `run_controls` writes only `<id>.report.json` files (expect.py lines 3017, 2574-2576). Its `controls` command takes no runner flags. `readiness` reads `--held-out-record` as a JSON record document of kind `controls` (expect.py lines 2940-2943). The amended step therefore has the canary runner assemble the record from those reports by the readiness fixtures' stand-in writer recipe (`gen_controls_gen8.rdy.py` lines 54-78). It also runs readiness with RD-ready's other arguments from `design/out/controls/readiness` and names the attestation fields R4 reads (expect.py lines 2945-2972). Because the record is assembled, a rehearsal pass shows only that readiness accepts an independent suite, record and attestation. Whether a build can write that record stays with step 3 and the views land.
  - Reads: `awk 'NR>=3008 && NR<=3027'`, `NR>=2537 && NR<=2600` and `NR>=2936 && NR<=2990` over `design/out/population/author-tools/expect.py`. Vocabulary `commands` gives readiness slice `views` and controls slice `core`. `cases.json` RD-ready `args` and `invocation` ("every path relative to controls/readiness").
- **P3 (Weakest link, Agreement (b)).**
  - Wrong: "In each generation the author also records ambiguities" overstates two lines, and "defective in GEN4 (CONTRACT line 452)" misnames the evaluator line 452 describes.
  - Corrected text, in place: "In GEN2 and GEN3 the author recorded ambiguities that 'two implementations could resolve differently' (CONTRACT line 386, line 407)" and "the GEN3 evaluator, found during GEN4 (CONTRACT line 452), and the GEN5 evaluator (CONTRACT line 532)".
  - Reads: `grep -n -i 'two implementations\|resolve differently'` over CONTRACT gives lines 386 and 407 only, in § 15 (GEN2 edits, heading line 366) and § 16 (GEN3 edits, heading line 390). `sed -n 452p` reads "the GEN3 author evaluator checked step references only inside its loop …", under § 18 GEN4 edits (heading line 424). Line 532 is under § 19 GEN5 edits (heading line 456) and reads "the author evaluator's transition-form anchoring ignored the lineage-write result".
- **P4 (End-state).**
  - Wrong: the seed quote stopped before line 50's third sentence, so the end-state did not say that the defective instance still reports FIX at readiness.
  - Corrected text, in place: the full line 50 quote, and a paragraph stating that at readiness the instance's own `mcg check` still truthfully exits 1 on its rule and witness findings, which are the repair worklist and do not block R1 (CONTRACT line 347), and that readiness is never a green instance.
  - Reads: `sed -n 50p` over the seed note (`design/out/prd-home/notes/missions/mcg-validator/external/mission-contract-graph-20261117.md`) ends "The current defective mission instance must truthfully report FIX, not be forced green." CONTRACT line 347 reads "rule and witness errors are the repair worklist and do not block R1". `design/out/instance/wm-loop-gen7/expected.json` gives `exit` 1, and its error-level `must_count` entries total rule 433 and witness 19 with no other check. PRD line 121 (AC 8) pins the core slice's exit, codes, `must_count` and `must_include`.
