---
name: atscale-prd-writer
description: >
  Apply the AtScale PRD-writing playbook for enterprise B2B data-platform PMs — structuring, drafting, and reviewing Product Requirements Documents for semantic-layer, data-platform, and analytics-infrastructure features. Centers on the artifact decision tree (One-Pager vs RFC vs PRD vs Design Doc vs Tech Spec), the 14-section PRD template, the customer-pain test for problem statements, the Goldilocks principle for requirements (testable, MUST/SHOULD/MAY, what-not-how), the inverted-pyramid for multi-audience readability, multi-persona requirements with operator/consumer pairs, the enterprise migration contract, API contract specification, the seven anti-patterns, and the 7-block review checklist. Use when drafting a new PRD, reviewing someone else's PRD, splitting a too-big PRD, writing a problem statement, picking the right artifact for an idea, defining success metrics, scoping non-goals, writing acceptance criteria, or specifying migration/API requirements for an enterprise data platform. Trigger on requests like "write a PRD for X", "review this PRD", "what should the success metrics be", "what goes in a non-goals section", "draft requirements doc", "is this a PRD or an RFC", "PRD problem statement template", "PRD review checklist", "split this PRD". Skip pure engineering design docs / RFCs / tech specs (those answer "how to build" — this skill is "what to build and why"), Jira ticket grooming (use ticket templates), one-pager strategy memos (different artifact), and OKR/roadmap planning (different framing).
version: 1.0.0
last_updated: 2026-05-18
---

# PRD Writing Guide — the enterprise B2B data-platform PM lens

## Core frame

A PRD answers "what are we building, for whom, and why" — not "how to build it." Problem-first, solution-last. Every section flows from a problem statement that a real customer would recognize as their own. Requirements live in the Goldilocks band: specific enough to test, flexible enough to leave design space. Enterprise B2B adds three non-negotiables: multi-persona conflicts must be surfaced and resolved, migration is a first-class product requirement (not an afterthought), and API/protocol stability is a customer contract. A PRD is read by engineers, executives, designers, QA, GTM, and support simultaneously — structure it as an inverted pyramid so each audience can stop at the depth they need.

## Key concepts

- **Artifact decision tree** — One-Pager (1pg, "should we invest"), RFC (2-5pg, "how should we build"), PRD (5-20pg, "what/who/why"), Design Doc (3-15pg, "technical architecture"), Tech Spec (2-10pg, "implementation details"). Do not collapse PRD and Design Doc into one document.
- **PRD scoping signs** — Too big if: >1 quarter eng, >3 personas with divergent needs, >50 requirements, value prop not stateable in 2 sentences, or multiple requirement-groups pass the **Ship Independently** test.
- **The 14-section PRD template** — Metadata, Problem Statement, Goals/Non-Goals, User Stories, Requirements (Functional + Non-Functional), Success Metrics, UX, Technical Considerations, Migration/Compatibility, API Specification, Security/Compliance, GTM Considerations, Open Questions, Milestones, Appendix. Required vs Recommended vs As-Needed.
- **Customer Pain Test** — Read the problem statement to the affected customer; they should say "Yes, that is exactly my problem." Structure: WHO + WHAT (job-to-be-done) + WHY they can't do it today + WHAT happens as a result. Quantify; cite evidence.
- **Goals vs Non-Goals** — Every goal measurable with a target. Non-goals must include something a reasonable person might assume is in scope (e.g. "We will not support custom SQL functions in V1"), not strawmen ("We will not rewrite the query engine").
- **User stories + Given/When/Then acceptance criteria** — 3-7 stories. Each independently testable. "As a [persona], I want to [action], so that [outcome]." Acceptance criteria are the PM-QA contract.
- **Priority bands** — P0 (Must Have, ship blocked, no workaround), P1 (Should Have, painful workaround exists), P2 (Nice to Have, can ship without).
- **MUST / SHOULD / MAY** — RFC-2119 verbs. MUST = required for ship. SHOULD = expected for ship. MAY = desired but deferrable. Every requirement gets one.
- **Goldilocks requirements** — Too vague ("fast"), too prescriptive ("Redis 5min TTL LRU"), just right ("<200ms p95 to 10B rows, cold-cache <2s"). Specify what, not how.
- **Success metrics — primary / secondary / guardrail** — At least one of each. Primary = "this worked". Secondary = "what else improved". Guardrail = "what must NOT get worse". Baseline + Target + Measurement Method + Timeframe.
- **Inverted pyramid for multi-audience** — Title+Problem (60s), Goals/Non-Goals+Stories (execs stop here), Requirements+Metrics (eng+QA), Tech/API/Migration (platform eng), Appendix (deep dive).
- **Multi-persona requirements** — Tag every requirement with its persona. One requirement, one persona. **Privilege the operator over the consumer** — if the data engineer can't configure/debug/maintain it, the analyst can't use it. Expose persona conflicts explicitly (CDO governance vs analyst flexibility) and resolve them with configurable policies, permission tiers, or approval workflows. Enterprise features always come in pairs: the capability + the control plane.
- **Enterprise Migration Contract** — (1) No surprise breakage, (2) Deprecation with runway (2-4 release cycles or 6-12 months minimum), (3) Migration **tooling**, not just documentation, (4) Rollback capability.
- **API backward-compatibility rules** — Additive = safe. Removing/renaming fields, changing field types, changing default behavior, adding required request fields = breaking changes requiring a new version. URL path versioning for REST; semver for SDKs.
- **The TL;DR block** — For VP+ PRDs: what's the problem, what you propose, what it costs (time/resources), what you expect in return. Execs read TL;DR + milestones table.

## Heuristics

- **Write the problem statement first, without any solution in mind.** If you can't articulate the problem without referencing your solution, you don't understand the problem yet.
- **Non-goals are as important as goals.** They prevent scope creep and manage expectations. A good non-goal is something a reasonable reader might assume is in scope.
- **The Ship Independently test** — for each requirement group, ask "could this ship on its own and deliver value?" If multiple groups pass, you have multiple PRDs masquerading as one — split them.
- **Convert every qualitative adjective to a quantified target.** "Scalable" → "10,000 concurrent connections, p99 <500ms." "Fast" → "p95 <200ms at 10B rows." Banned without numbers: seamless, intuitive, robust, scalable, enterprise-grade.
- **Edge-case ritual for every user story** — Empty input? No permission? Concurrent users doing this? Under load? Upstream dependency down?
- **Hedge-phrase audit** — Search the doc for "we should also consider," "it would be nice if," "while we are at it," "future enhancement." Each hit becomes P2-explicit-defer or cut.
- **Open questions are intellectual honesty, not weakness.** A PRD with zero open questions is either trivial or hiding uncertainty. Every open question gets an owner and a due date.
- **Competitive intelligence informs which problems to solve, not which features to build.** "Cube has X" is not a reason. "Our customers need X, and here's the evidence" is. Half a page max for competitive context.
- **Enterprise features always come in pairs** — every analyst/consumer capability needs an operator/admin control plane. AI recommendations need governance toggles. New formats need migration tooling.
- **Seven anti-patterns to refuse to ship** — (1) Solution-first thinking, (2) Vague requirements ("seamless"), (3) Missing edge cases, (4) Scope-creep hedging, (5) "Boil the ocean" PRD, (6) Cargo-cult competitive requirements, (7) Engineering spec masquerading as a PRD.

## When to apply

- Drafting a new PRD for a feature, capability, or platform increment
- Reviewing a peer's PRD before approval
- Splitting a too-large PRD or deciding it should be multiple PRDs
- Writing or critiquing a problem statement
- Picking the right artifact: PRD vs RFC vs One-Pager vs Design Doc vs Tech Spec
- Defining success metrics (primary / secondary / guardrail)
- Scoping explicit non-goals to prevent scope creep
- Writing Given/When/Then acceptance criteria
- Specifying migration / backward-compatibility / API-versioning requirements for an enterprise data platform
- Resolving multi-persona requirement conflicts (CDO vs analyst, operator vs consumer)
- Running the 7-block PRD review checklist (Problem & Scope, Goals & Non-Goals, User Stories & Personas, Requirements, Enterprise Concerns, Success Metrics, Completeness, Readability)
- Adding a TL;DR block for an executive-audience PRD

## Out of scope

- Engineering design docs / RFCs / tech specs (these answer "how to build" — PRDs answer "what and why")
- Jira ticket grooming or sprint-level work breakdown
- One-pager strategy memos (different artifact, different decision)
- OKR / roadmap / portfolio planning (different framing — PRD is feature-level)
- Pure UX/visual design specifications (Figma is the artifact, not a PRD)

## Source

The Definitive Guide to Writing PRDs for Enterprise B2B Data Platforms, AtScale Reference, 2026.
