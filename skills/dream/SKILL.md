---
name: dream
description: >
  AtScale product-PRD dreaming. Listens to the user's seed, gathers evidence (Jira/Confluence
  when Atlassian MCP tools are connected, otherwise whatever the user provides), synthesizes a
  vision, then writes a fleet of product PRDs following the /atscale-prd-writer standard —
  semantic layer, query protocols (DAX/MDX/SQL), BI integrations, MCP/AI capabilities, and
  platform features. Fully standalone: it discovers its PRD home and optional integrations at
  runtime and works with nothing but Claude Code and git installed. Use when the user says
  /dream, /dream <topic>, or asks to "draft product PRDs for X", "vision out the next feature
  area", or "turn these notes/spikes into product docs." Hand finished PRDs to /pybuilder
  to implement.
---

# /dream — vision into AtScale product PRDs

`/dream` turns a direction into a fleet of buildable Product Requirements Documents.
It listens, researches, synthesizes a vision, decomposes the vision into PRD-sized
pieces, and writes each PRD to the standard in the bundled **`/atscale-prd-writer`**
skill: Customer Pain Test on every problem statement, Goldilocks + MUST/SHOULD/MAY on
every requirement, Given/When/Then acceptance criteria, explicit non-goals, success
metrics with baselines, and the 7-anti-pattern audit before committing.

Dream doesn't implement. `/pybuilder` does that. Dream's job is to make what it
builds worth building.

## Phase −1 — Discover the environment (always run first)

This skill adapts to whatever machine it is on. Resolve each of the following **at the
start of every invocation** and state what you found in one short line each. Never
assume a path exists — check.

**PRD home** (`$PRD_DIR` below) — first match wins:
1. `$DREAM_PRD_DIR` if the env var is set.
2. `~/Documents/PRDs/` if it exists (an already-established PRD workspace).
3. `./PRDs/` under the current working directory — create it if absent.

Inside `$PRD_DIR`, dream maintains:
```
$PRD_DIR/
├── PRD-<slug>.md        # active PRDs (queued / building / blocked)
├── archive/             # finished PRDs (Status: built); dream never writes here
├── visions/<slug>.md    # vision docs
├── notes/dream-log.md   # append-only run log
└── MANIFEST.md          # one-line-per-PRD registry (create/refresh on each run)
```
A PRD's directory is derived from its `Status`: active statuses stay at
`$PRD_DIR/`, `built` moves to `$PRD_DIR/archive/`. `/build` is what performs that
move; dream only ever writes to `$PRD_DIR/` and only ever reads `archive/`.

**Git** — if `$PRD_DIR` is inside a git repository, commit what you write (stage the
specific files you created, never `git add -A`) using the machine's existing git
identity. Do not set or hardcode any name/email. Push only if an `origin` remote
already exists; a push failure is a warning, not an error. If `$PRD_DIR` is not in a
git repo, offer `git init` once; if declined, plain files are fine.

**Atlassian evidence (optional)** — check whether Jira/Confluence MCP tools are
available in this session (e.g. Atlassian/Rovo MCP: `searchJiraIssuesUsingJql`,
`getJiraIssue`, Confluence search). If they are, discover the cloud ID via the MCP's
resource-discovery call (e.g. `getAccessibleAtlassianResources`) — never hardcode
cloud IDs or page IDs. If no Atlassian tools are connected, say so and fall back to
what the user gives you: pasted tickets, links, meeting notes, customer quotes.

**Build queue** — there is no separate queue file to discover. A PRD's own
frontmatter `Status` field is the queue: dream writes new PRDs as `Status: queued`,
and `/build` scans `$PRD_DIR` for `queued` PRDs and drains them. Nothing to check
here beyond `$PRD_DIR` itself.

**Run log** — the run log is `$PRD_DIR/notes/dream-log.md`.

## Domain context

AtScale product areas this skill understands:

- **Universal Semantic Layer** — SML model definitions, dimensions, hierarchies,
  measures, calculated members, date/time intelligence, subject areas, governance
- **Query protocols** — one model served over DAX, MDX, SQL, PGWire, Python, and MCP;
  dialect conversion; backend routing to cloud data warehouses
- **BI integrations** — Power BI (live connection / XMLA), Excel, Tableau, Looker;
  migration tooling from BI-tool-native models into the semantic layer
- **AI / MCP capabilities** — the AtScale MCP server, LLM-grounded query generation,
  context-window management, parameter validation, agent-facing tool design
- **Performance & operations** — aggregate awareness/tuning, query planning,
  observability, sizing, deployment topologies

If the seed is outside these areas but still an enterprise data-platform feature, the
process is identical — only the domain vocabulary changes.

## Phase 0 — Listen

Enter with full context. Read:

- The user's prompt (the seed). If there is no seed, ask one question: "What area
  should this dream explore, and what prompted it?"
- `$PRD_DIR/visions/` — what visions already exist; extend rather than duplicate
- `$PRD_DIR/MANIFEST.md` and existing `PRD-*.md` — what has already been drafted
- The tail of the run log(s) — what previous dreams and builds have been doing

Sit with this. The point is to notice what problem actually needs solving, not to
confirm the topic the user named.

## Phase 1 — Research

Probe for evidence. Every PRD claim must be grounded in something real.

1. **Jira / Confluence (if connected).** Pull the full body of relevant spikes and
   epics; search recent tickets in the area (`project = <their project>, updatedDate
   >= -30d`, relevant keywords). Read ACs carefully — spikes often contain half-formed
   product requirements that need a proper PRD to operationalize.
2. **User-provided evidence (always).** Ask for or use whatever the user has: customer
   calls, support threads, sales notes, competitor observations. Quantify: how many
   customers, which accounts, what they couldn't do, what they did instead.
3. **Engineering ground truth.** If the feature touches code the user has locally,
   skim the actual repos for API surfaces, types, and error paths the PRD will
   reference. A PRD that describes an API differently from the code is wrong.
4. **Existing PRDs / visions.** Never duplicate intent. If a vision already covers
   this area, read it and extend it.

Cite specific findings. "JIRA-1234 AC2 asks for a server-side validator prototype" is
honest. A PRD that asserts a customer problem without citing evidence is fiction.

## Phase 2 — Vision

Synthesize. Write or update `$PRD_DIR/visions/<slug>.md`:

- **TL;DR** — one paragraph: what is true when this vision is fully realized?
- **Problem statement** — Customer Pain Test: WHO + WHAT + WHY they can't today +
  quantified consequence. No solution references.
- **End-state** — the concrete capability that exists when done
- **Components** — PRD-sized pieces; one bullet per future PRD, each with a one-line
  problem statement
- **Order** — what depends on what; which can ship in parallel
- **Open questions** — each with a named owner

Visions accumulate; they don't get replaced.

## Phase 3 — Decompose & draft

Write the PRDs, one per component, in dependency order, each at
`$PRD_DIR/PRD-<slug>.md`, each following the full **`/atscale-prd-writer`** standard
(read that skill before drafting if it isn't already in context). The prose
inside every section follows `writing-standard.md` (sibling file in this
skill) — read it before drafting, and run its three-step method (outline →
draft → proofread/workshop) on every PRD and vision doc.

**Before each PRD:** artifact check (PRD vs RFC vs One-Pager), Customer Pain Test,
Ship-Independently test.

**PRD frontmatter:**
```
- Status: queued                  # lifecycle field (unchanged semantics)
- build_target: python-cli | python-lib | python-agent | product
- PM: <the user>
- Drafted: YYYY-MM-DD
- Vision: visions/<slug>.md
- Jira: <issue key, or "to be filed">
- Epic: <epic key, if part of one>
- Engineering target: <repo/codebase the feature lands in>
- Relates: <other issue/PRD keys, if any>
```

When a PRD folds in prior or dissolved work (an abandoned spike, a superseded
PRD), add one optional line directly under the frontmatter: `Absorbed scope:
<what it replaces/folds in>` — a convention real AtScale PRDs use to keep that
provenance visible.

`Status` is a lifecycle field, not a draft marker: `queued` (new, not yet built)
→ `building` (a `/build` run is in progress) → `built` (shipped; the PRD moves to
`archive/`) → `blocked` (a `/build` run failed; the PRD stays in place with a
`Blocked:` reason). Dream always writes new PRDs as `Status: queued` — advancing
the field from there is `/build`'s job, never dream's.

`build_target` tells `/pybuilder` which of its targets implements the PRD:
`python-*` → `/pybuilder`, `product` → not auto-buildable (vision/process/GTM
work). Every PRD gets a `build_target`; a missing one strands the PRD.

**Default to `python-*`** (`python-cli` / `python-lib` / `python-agent`).
Python is the only build family; when it's ambiguous which of the three,
`/pybuilder`'s eval-gated pipeline picks the shape from the PRD's content.

**PRD body — core (every PRD, inverted pyramid, this order):** TL;DR → Problem
statement (with Phase 1 citations) → Goals / Non-Goals (measurable; non-goals
are things a reasonable reader would assume in scope) → User stories (3–7,
persona-tagged; privilege the operator over the consumer — enterprise features
come in capability + control-plane pairs) → Requirements (MUST/SHOULD/MAY,
functional and non-functional; banned without numbers: "fast", "seamless",
"scalable", "robust") → Success metrics (primary + secondary + guardrail, each
with baseline, target, method, timeframe — as a table) → Technical
considerations (constraints and interfaces, not implementation) → Migration /
compatibility (deprecation runway, tooling, rollback) → Open questions (as a
table: question, owner, due) → Acceptance criteria (numbered, testable,
Given/When/Then; edge-case ritual: empty input? no permission? concurrent
users? under load? upstream down?).

**PRD body — optional (add only when the feature warrants it; real AtScale
PRDs adopt these selectively):**
- **UX & interaction model** — earns its place when the feature has a
  user-facing surface (UI, CLI, config) worth walking through.
- **API specification** — earns its place when the feature exposes or changes
  a programmatic contract (REST, SQL, MCP, etc.).
- **Security & compliance** — earns its place when the feature touches auth,
  data-access boundaries, or a named compliance requirement.
- **GTM considerations** — earns its place when the feature changes packaging,
  pricing, or needs a customer-facing launch motion.
- **Appendix / Companion documents** — earns its place when supporting
  research, diagrams, or a linked RFC/tech spec is substantial enough not to
  belong inline.

**Anti-pattern audit before committing** (from `/atscale-prd-writer`): solution-first,
vague requirements, missing edge cases, scope-creep hedging, too big, cargo-cult
competitive features, engineering spec masquerading as a PRD.

**Range:** three to seven PRDs per vision. Don't draft past what the research
supports — leave ungrounded components as bullets in the vision doc.

**Drafting model:** PRD synthesis is deep-reasoning work. Draft on the most capable
model available in the session (Fable/Opus tier); if parallelizing drafting across
subagents, spawn the drafting subagents on that tier and reserve cheaper models for
mechanical legs (evidence collation, file edits, manifest updates).

## Phase 4 — Persist

1. **Write MANIFEST.md** — regenerate the one-line-per-PRD registry by scanning
   frontmatter across `$PRD_DIR/*.md` AND `$PRD_DIR/archive/*.md`: one line per
   PRD — filename, Status, build_target, Drafted. Atomic write (temp file in the
   same directory, then rename over); a concurrent `/build` run must never read
   a partial manifest.
2. **Commit** (if in a git repo): stage the specific PRD/vision/manifest/log files
   this run produced. Message: `dream: <N> PRDs + vision from <seed>`, body listing
   slugs. Push only if origin exists.
3. **Append the run note** to `$PRD_DIR/notes/dream-log.md`:
   ```
   ## <ISO-ts>  /dream  vision-<slug>
   Drafted: PRD-foo.md, PRD-bar.md
   Vision: visions/<slug>.md
   Seeded from: <Jira key | customer signal | user prompt>
   Build order: foo → bar (bar consumes foo's API)
   Open questions: <key unresolved items>
   ```
4. **Nothing separate to queue.** Every PRD dream drafts already carries
   `Status: queued` in its frontmatter — that field is the whole queue. End by
   telling the user the build order and that `/build` will drain it (or
   `/build $PRD_DIR/PRD-<first>.md` to build one specific PRD first).
5. **Offer Confluence publication (ask, never assume).** If Confluence write
   tools are available in this session (Atlassian MCP), ask the user whether
   they want the PRD(s) just drafted published to Confluence as drafts. Never
   create or edit Confluence content without an explicit yes in that session —
   the local `$PRD_DIR` files remain the source of truth either way. If they
   say yes, match the house style: the metadata block (Jira, Epic, Vision,
   Engineering target, PM, Drafted) as an info panel at the top, `Status` as a
   yellow "DRAFT v0.1" status macro, then the core/optional section order
   above. If no Atlassian tools are connected, skip this step silently.

## Invocations

- `/dream` → interactive; ask for the seed, walk all phases
- `/dream <topic>` → seed from topic
- `/dream from <jira-key>` → seed from a specific ticket/spike (requires Atlassian MCP)
- `/dream visions` → list known visions and their status, then exit

## Hard rules

1. **Every PRD follows the `/atscale-prd-writer` standard.** No exceptions.
2. **Never delete or modify existing PRDs.** Draft successors; `/build` archives
   finished ones — dream never moves or edits a PRD it didn't just write.
3. **Cite the research.** Every "Why" references specific Phase 1 evidence.
   Assertions without evidence are fiction.
4. **Visions are durable.** Update them; don't replace them silently.
5. **Logs are append-only.** Never rewrite history in the dream-log.
6. **Don't dream past the research.** Ungrounded components stay in the vision doc
   as open questions.
7. **Enterprise features come in pairs.** Consumer capability + operator control
   plane; if you draft one without the other, say so in Non-Goals.
8. **No credentials or internal identifiers in PRDs or in this skill's output.**
   No passwords, tokens, connection strings, cloud IDs. Reference env-var names only.
9. **Queue what you draft.** Every buildable PRD is written with `Status: queued`
   — that frontmatter field is the entire queuing step, no separate registration
   required.
10. **Discovery over assumption.** Re-run Phase −1 every invocation; environments
    change between runs.
11. **Confluence is opt-in per run.** Dream may offer to publish; it never writes
    to Confluence unasked.
12. **The writing standard governs all prose.** Every PRD and vision passes
    `writing-standard.md`'s quality gate — no draft ships on its first pass.
    Understandability outranks everything else in the standard — when in doubt,
    ship the version a first-time reader understands fastest.
