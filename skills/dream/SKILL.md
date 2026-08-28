---
name: dream
description: >
  Product-PRD dreaming that feeds a build loop. Listens to a seed (a topic, a note, a
  project profile, a ticket), gathers evidence, synthesizes a vision, then writes a fleet
  of buildable PRDs to whatever /build is installed — it reads that build's contract at
  run start, so the same skill drives a Python-only kit /build and a Rust+Python private
  /build without edits. Loop-ready mode drafts the measurement harness first so a
  closed-loop scaffolder can drive the fleet. Use when the user says /dream,
  /dream <topic>, /dream project <name>, /dream loop <name>, or asks to "draft PRDs for
  X", "vision out the next area", or "turn these notes into product docs."
---

# /dream — a seed into a fleet of buildable PRDs

`/dream` turns a direction into Product Requirements Documents that a build skill can
implement without a human in the loop. It listens, researches, synthesizes a vision,
decomposes the vision into PRD-sized pieces, and writes each PRD to the bundled
PRD standard (`/atscale-prd-writer`: Customer Pain Test on every problem statement,
Goldilocks requirements with P0/P1/P2, Given/When/Then acceptance criteria, explicit
non-goals, success metrics with baselines, the anti-pattern audit before committing).

Dream doesn't implement. `/build` routes each PRD to its builder. Dream's job is to
make what gets built worth building — and to make it buildable as written.

## Phase −1 — Discover the environment (always run first)

Resolve every item below at the start of every invocation and state what you found
in one short line each. Never assume a path exists — check.

**PRD home** (`$PRD_DIR`) — first match wins:
1. `$DREAM_PRD_DIR` if the env var is set.
2. `~/Documents/PRDs/` if it exists.
3. `./PRDs/` under the current working directory — create it if absent.

Inside `$PRD_DIR`:
```
$PRD_DIR/
├── build-queue/PRD-<slug>.md   # what dream writes; the only dir /build scans
├── built-prds/PRD-<slug>.md    # shipped; /build moves files here; dream only reads
├── parked/PRD-<slug>.md        # set aside by a human; evidence, never scanned
├── visions/<slug>.md           # one vision per area; durable
├── projects/<name>.md          # project profiles (see below)
├── notes/dream-log.md          # append-only run log
└── MANIFEST.md                 # derived index; regenerate, never hand-edit
```
Create `build-queue/`, `built-prds/`, `parked/`, `visions/`, `notes/` if missing. Dream
writes only to `build-queue/`, `visions/`, `notes/`, and `MANIFEST.md`.

**Build contract** — find the installed `/build` skill (the `build` entry in the
session's skill list; on disk usually `~/.claude/skills/build/`, possibly a symlink).
If it has a `build-contract.md`, read it: it defines the accepted `build_target`
values, required companion keys (`build_into`, `publish`, …), the archive directory
name, the acceptance-criteria line format, and how it publishes. **Write PRDs to that
contract.** If no contract file exists, use this kit's default: `build_target` ∈
`python-cli | python-lib | python-agent | product`, ACs as numbered lines. Say which
contract is in force. A PRD that doesn't match the contract is stranded, not built.

**Project profile** (optional) — `$PRD_DIR/projects/<name>.md`. Selected by
`/dream project <name>`, `/dream loop <name>`, or when the seed names the project.
A profile carries: the seed source(s) to re-read every run (a note, a doc), the slug
prefix, the vision file, the lineage decision, build defaults (`build_target`,
`build_into`, `publish`), and — for loop-ready fleets — the loop name and the loop
contract seed. Profiles are data a human maintains; dream reads them, cites them, and
may append a dated "Dream notes" section but never rewrites a human's lines.

**Git** — if `$PRD_DIR` is a git repo, commit what you write (stage the specific
files, never `git add -A`) with the machine's existing identity; never set or
hardcode a name/email. `git pull --rebase` first when an `origin` exists — another
machine may have advanced the queue. Push only if `origin` exists; a push failure is
a warning. Not a repo: offer `git init` once; plain files are fine if declined.

**Evidence sources (all optional; detect, never assume)**
- *Issue/wiki tracker*: Atlassian MCP tools (`searchJiraIssuesUsingJql`,
  `getJiraIssue`, Confluence search) — discover the cloud ID via the MCP's
  resource-discovery call, never hardcode it. Absent → say so.
- *Code*: `gh auth status` succeeds, or GitHub MCP tools are present → read-only
  grounding in real repos (`gh search code`, `gh repo view`, `gh api`). Absent → say so.
- *Web*: a web search/fetch tool in the session → open-source intelligence for
  Phase 1. Absent → rely on what the user provides and say so.
- *Local repos*: whatever the profile or seed names under the home directory.

**Run log** — `$PRD_DIR/notes/dream-log.md`.

## Domain context

`reference.md` (sibling file) holds grounding for one domain family — semantic
layers, query protocols, governed AI data access — plus general product-management
frameworks. Read the PM-frameworks section for every seed; read the domain section
only when the seed is in that family. For any other domain, Phase 1 research is the
grounding; do not import the semantic-layer vocabulary into unrelated PRDs.

## Phase 0 — Listen

Read, in this order:
- The seed: the user's prompt, or the profile's seed source(s) re-read fresh (a note
  that changed since the last dream changes the fleet).
- `$PRD_DIR/visions/` — extend, don't duplicate.
- `$PRD_DIR/MANIFEST.md`, `build-queue/`, `built-prds/`, `parked/` — what exists,
  what shipped, what a human set aside (parked PRDs are evidence of intent, not work
  to redo).
- The tail of the run log.

**Lineage check (before any greenfield decision).** Search for prior work that
already realizes part of the seed: visions and built PRDs here, repos the code
evidence source can see, and anything the profile names. Decide one of:
- **extend** — a live repo implements the substrate; PRDs carry `build_into` and
  the contract's extend target;
- **fork** — prior work exists but the seed changes a load-bearing model (storage,
  auth, editing surface); say precisely what changes and what is reused;
- **greenfield** — nothing usable exists; cite what was checked.
Record the decision and its evidence in the vision's **Lineage** section. Never
start greenfield on a seed whose predecessor sits one search away.

Sit with all of it. The point is to notice what problem actually needs solving, not
to confirm the topic the user named.

## Phase 1 — Research

Every PRD claim is grounded in something real. Probe, in whatever order the
sources allow:

1. **Tracker (if connected).** Full bodies of relevant spikes/epics; recent tickets
   in the area. Spikes carry half-formed requirements that need a proper PRD.
2. **User-provided evidence (always).** Calls, threads, notes, quotes; quantify.
3. **Engineering ground truth.** Skim the actual code the PRD will touch — local
   repos, or GitHub read-only — for API surfaces, types, error paths. Cite repo,
   file, PR/issue. A PRD that describes an API differently from the code is wrong.
4. **Open-source intelligence (when the seed asks for it or the domain is new).**
   What people adopt, what they ask for (issues, roadmaps, launches), what the
   incumbents do. Cite URLs. Do the research the seed names explicitly — a seed
   that says "research how X renders Y" is an instruction, not a suggestion.
5. **Existing PRDs, visions, parked work.** Never duplicate intent.

Cite specific findings. An assertion without evidence is fiction.

## Phase 2 — Vision

Write or update `$PRD_DIR/visions/<slug>.md`:

- **TL;DR** — what is true when the vision is realized
- **Problem statement** — Customer Pain Test: WHO + WHAT + WHY they can't today +
  quantified consequence; no solution references
- **Lineage** — the Phase 0 decision with its evidence
- **End-state** — the concrete capability that exists when done
- **Components** — one bullet per future PRD, each with a one-line problem statement
- **Order** — dependencies; what ships in parallel
- **Loop contract** (loop-ready fleets only; see below)
- **Open questions** — each with a named owner

Visions accumulate; they don't get replaced.

## Loop-ready fleets

A loop-ready fleet is one a closed-loop scaffolder (a "buildloop": orient → preflight
→ harness gate → dream → build → deploy → measure → digest) will drive after the
first build. Enter this mode via `/dream loop <name>` or a profile with a `Loop:`
line. It changes two things.

**1. The vision carries a Loop contract** — everything the scaffolder needs, decided
now with evidence, not later by guesswork:

| field | meaning |
|---|---|
| loop name | `<name>-buildloop` |
| metric | one number per run, what it measures, how it's scored; validated by hand on 3–5 known-good/known-bad cases before it becomes a PRD |
| population | what the corpus represents (users × actions × conditions) and its real size |
| corpus + gold | where entries and their ground-truth expectations live; gold is truth, never the baseline being beaten |
| proxy tier / truth tier | the cheap fast check and the expensive faithful one, labelled |
| measure command | the executable that emits the score and a run record |
| preflight probes | substrate (data/infra up) and artifact (deployed binary answers) |
| deploy target | where the shipped artifact runs and how it's redeployed |
| write scope | the only repos/orgs the loop may push to |
| failure families | how failures cluster; one fix per family |

**2. The fleet is harness-first.** Build order is: (a) the **harness PRD** — corpus,
gold, scorer, measure command, preflight probes, ledger; (b) the **deploy PRD** —
unit files, env contract, redeploy script; (c) feature PRDs, each carrying a
frontmatter `Loop: <name>: <metric it moves>` line so the loop's digest can cluster
results by family. A feature PRD before the harness is a fleet the loop cannot
measure; do not draft it that way. When the seed itself names the reflection
component (a synthetic user population, a conformance suite), that component IS the
harness PRD.

Language follows the build contract: the harness may be Python (`python-agent`) while
the substrate is Rust, or the reverse — pick per component, state why.

## Phase 3 — Decompose & draft

One PRD per component, in dependency order, at `$PRD_DIR/build-queue/PRD-<slug>.md`
(slug `^[a-z0-9]+(-[a-z0-9]+)*$`, prefixed per profile), each to the full PRD
standard, prose to `writing-standard.md` (three-step method: outline → draft →
proofread on every document).

**Before each PRD:** artifact check (PRD vs RFC vs one-pager), Customer Pain Test,
Ship-Independently test.

**Frontmatter** — bullet form, within the first 80 lines, keys from the build
contract. Kit default shown; a private `/build` contract may add keys such as
`build_into`, `build_priority`, `publish`, `deferred_acs`:
```
- Status: queued
- build_target: <from the contract>
- build_into: <abs path>           # only when extending an existing repo
- publish: <from the contract>     # e.g. j0yen/private; omit if the contract has no publish key
- Vision: visions/<slug>.md
- Depends-on: PRD-<slug>.md        # when order matters
- Loop: <name>: <metric>           # loop-ready fleets only
- PM: <the user>
- Drafted: YYYY-MM-DD
- Engineering target: <repo/codebase the feature lands in>
- Tracker: <issue key, or omit when no tracker is connected>
```
`Absorbed scope: <what it folds in>` directly under the frontmatter when a PRD
supersedes prior work (a parked draft, an abandoned spike).

`Status` is a lifecycle field: `queued` → `building` → `built` (file moves to
`built-prds/`) or `blocked`. Dream writes `queued`; `/build` advances it.

**Body — core, inverted pyramid, this order:** TL;DR → Problem statement (with
Phase 1 citations) → Goals / Non-Goals → User stories (3–7, persona-tagged;
capability + control-plane pairs for enterprise features) → Requirements (P0/P1/P2,
functional and non-functional; "fast", "seamless", "scalable", "robust" are banned
without numbers) → Success metrics (primary, secondary, guardrail; baseline, target,
method, timeframe — a table) → Technical considerations (constraints and interfaces,
not implementation; name reused crates/modules from the lineage) → Migration /
compatibility → Open questions (table: question, owner, due) → Acceptance criteria.

**Acceptance criteria — the countable form.** Under the heading
`## Acceptance criteria`, one AC per line, numbered, level inline, Given/When/Then
on the same line:
```
1. P0 — Given an empty document, When a viewer requests it, Then 200 with an empty body.
2. P1 — Given 50 concurrent readers, When they read the same document, Then p95 < 150 ms.
```
Builders count `N. ` lines; `AC-1:` prefixes, tables, and prose blocks are invisible
to them. Edge-case ritual on every PRD: empty input? no permission? concurrent
actors? under load? upstream down?

**Body — optional, when warranted:** UX & interaction model · API specification ·
Security & compliance · GTM considerations · Appendix / companion documents.

**Anti-pattern audit before committing:** solution-first, vague requirements,
missing edge cases, scope-creep hedging, too big, cargo-cult competitive features,
engineering spec masquerading as a PRD.

**Range:** three to seven PRDs per vision; don't draft past the research. Ungrounded
components stay in the vision as open questions.

**Drafting model:** PRD synthesis runs on the most capable tier available in the
session (Fable, else Opus) — never Sonnet or Haiku; a PRD drafted below that tier is
a defect. Drafting subagents use the same tier. Everything mechanical — evidence
collation, file reads, manifest, git — goes to the cheapest capable model.

## Phase 4 — Persist

1. **MANIFEST.md** — regenerate by scanning frontmatter across `build-queue/`,
   `built-prds/`, and `parked/`: one line per PRD (directory, filename, Status,
   build_target, Drafted). Atomic write (temp file, rename). A concurrent `/build`
   must never read a partial manifest.
2. **Commit** — `git pull --rebase` if origin exists, stage only this run's files,
   message `dream: <N> PRDs + vision from <seed>` with slugs in the body, push if
   origin exists.
3. **Run note** in `notes/dream-log.md`:
   ```
   ## <ISO-ts>  /dream  vision-<slug>
   Profile: projects/<name>.md (or none)
   Contract: <which build-contract was in force>
   Lineage: extend <repo> | fork <repo> | greenfield
   Drafted: PRD-foo.md, PRD-bar.md
   Build order: foo → bar (bar consumes foo's API)
   Loop: <name> — metric <…> (loop-ready fleets)
   Open questions: <key unresolved items>
   ```
4. **Nothing separate to queue** — `Status: queued` in `build-queue/` is the queue.
   End by stating the build order and that `/build` will drain it (or
   `/build $PRD_DIR/build-queue/PRD-<first>.md` for one).
5. **Wiki publication is opt-in** — if Confluence write tools exist, ask; never
   write unasked. No tools: skip silently.

## Invocations

- `/dream` → interactive; ask for the seed, walk all phases
- `/dream <topic>` → seed from topic
- `/dream project <name>` → seed from `$PRD_DIR/projects/<name>.md`
- `/dream loop <name>` → same, in loop-ready mode (harness-first fleet + Loop contract)
- `/dream from <ticket-key>` → seed from a tracker item (requires a tracker MCP)
- `/dream visions` → list visions and their status, then exit

## Hard rules

1. **Every PRD follows the PRD standard.** No exceptions.
2. **Never delete or modify existing PRDs.** Draft successors; `/build` moves
   finished ones; humans park.
3. **Cite the research.** Every "Why" references Phase 1 evidence.
4. **Visions are durable.** Update; never replace silently.
5. **Logs are append-only.**
6. **Don't dream past the research.**
7. **Enterprise features come in pairs** — capability + control plane; say so in
   Non-Goals if one ships without the other.
8. **No credentials or internal identifiers in PRDs.** Env-var names only.
9. **Queue what you draft.** `Status: queued` in `build-queue/` is the whole step.
10. **Discovery over assumption.** Re-run Phase −1 every invocation.
11. **Wiki publication is opt-in per run.**
12. **The writing standard governs all prose.** Understandability outranks
    everything.
13. **Write to the build contract in force.** Targets, keys, AC line format, and
    directories come from the installed `/build`'s `build-contract.md`, never from
    memory of some other build.
14. **Lineage before greenfield.** A vision states extend / fork / greenfield with
    evidence; PRDs that extend carry `build_into`.
15. **Loop-ready means harness-first.** No feature PRD ahead of the harness PRD in a
    loop-ready fleet; every feature PRD names the metric it moves.
