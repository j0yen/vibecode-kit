---
name: dream
description: >
  Product-PRD dreaming that feeds a build loop. Takes a seed (a failure family, real
  traffic, a note, a project profile, a ticket, or an explicit ask), gathers evidence,
  synthesizes a vision, then writes buildable PRDs for whatever builder is installed. It
  reads that build's contract at run start, including the contract's hook scripts, so
  the same skill drives any builder without edits. Use when the user says /dream,
  /dream <topic>, /dream project <name>, /dream loop <name>, /dream amend <slug>, or
  asks to "draft PRDs for X" or "turn these notes into product docs."
fable-spawn: true
---

# /dream — a seed into buildable PRDs

`/dream` turns a seed into PRDs a builder can implement without a human. It researches,
writes a vision, splits it into PRD-sized pieces, and writes each PRD to the PRD standard
(`/atscale-prd-writer`: Customer Pain Test, P0/P1/P2 requirements, Given/When/Then ACs,
non-goals, metrics with baselines, anti-pattern audit). Dream does not implement.

Every PRD must name what it moves (its `Seed:`), and its evidence must be checked
before it leaves the drafter. Prose rules in this file point at the check that enforces
them (`lint:<id>`); a rule tagged `judgment` has no check. Why each rule exists:
`history.md`.

## Phase −1 — Discover (every invocation)

State one short line per item. Never assume a path exists.

**PRD home** (`$PRD_DIR`), first match: `$DREAM_PRD_DIR`; `~/Documents/PRDs/`;
`./PRDs/` (create). Layout: `build-queue/` (the only dir the builder scans), `built-prds/`,
`parked/`, `visions/`, `projects/`, `notes/dream-log.md`, `MANIFEST.md` (derived).
Dream writes only `build-queue/`, `visions/`, `notes/`, `MANIFEST.md`.

**Build contract.** Find `build-contract.md` in the installed build skill's directory (the builder reads the same file) and read it.
It defines targets, frontmatter keys, the AC line format, caps, and directories. No
contract: kit default (`build_target` ∈ `python-cli | python-lib | python-agent |
product`, numbered ACs, cap 8). Say which contract is in force. A PRD that misses the
contract is stranded.

**Dream hooks.** If the contract has a `## Dream hooks` table, resolve each row's script
relative to the contract's directory. A row whose script is missing or marked
`(stage N)` is absent. Say which hooks are live. The phases below run a hook when it is
live and fall back to the stated manual step when it is not.

| hook | when | fallback when absent |
|---|---|---|
| `dream.seeds` | Phase 0 | read seeds the user names |
| `dream.lint` | end of Phase 3, each PRD | the contract's lint script, else self-audit |
| `dream.dryrun` | end of Phase 3, each PRD | none; say so |
| `dream.amend` | before any amend | `scripts/amend-key-gate.sh` (this skill) |
| `dream.persist` | Phase 4, per batch | the manual Phase 4 steps |
| `dream.premise` | pre-admission, creative PRDs | AC 1 also proves the premise |
| `dream.scorecard` | Phase 0 | none |

**Project profile** (optional): `$PRD_DIR/projects/<name>.md` — seed sources, slug
prefix, vision, lineage decision, build defaults, loop name. Dream may append a dated
"Dream notes" section; it never rewrites a human's lines.

**Git.** If `$PRD_DIR` is a repo: `git pull --rebase` first; stage only this run's
files; machine identity, never set one; push if `origin` exists. Never commit in a
clone a build daemon owns (the persist hook refuses it).

**Lineage freshness.** For every `build_into` repo about to be cited, run
`scripts/lineage-freshness.sh <path>` and print `lineage: <path> <verdict>`. On
`behind <n>`, cite from `git show origin/main:<file>`; the PRD frontmatter carries one line per behind repo:
- Cited-tree: <repo>@<sha>
where `<sha>` is the `remote-sha=` value the script printed. `dirty`: cite local, note the count.
`no-remote`/`missing`: cite local, say freshness is unknown.

**Evidence sources** (detect, never assume): tracker MCP, `gh` / GitHub MCP, web
search, local repos. Absent → say so.

## Phase 0 — Seed

**Allowed seeds**, in priority order:
1. A family from the `dream.seeds` hook (a failure the build's measurement found, with
   no PRD covering it).
2. Real traffic (a user or caller id).
3. The user's explicit ask, dated.

Every PRD carries `Seed:` in the contract's Seed grammar; kit default
`user:<YYYY-MM-DD>` (lint:seed-missing). A family whose owner is the measurement
harness itself, not the product, becomes a hand fix to the harness, not a PRD; write
one line: `harness-vs-target: <family> → <target PRD | harness hand fix>`.

**Grounded vs creative.** A grounded PRD cites its seed's evidence. A creative PRD is
drafted only on an explicit ask, carries `Grounding: creative`, a `Falsifier:` line,
and a `Premise:` command that tests the premise cheaply before any build. Ungrounded
components stay in the vision as open questions. There is no fixed PRD count.

Then read: the seed source (fresh); `visions/`; `MANIFEST.md`, `build-queue/`,
`built-prds/`, `parked/` (parked PRDs are evidence, not work to redo); the dream-log
tail; the scorecard hook output when live.

**Lineage check.** Search for prior work that already covers part of the seed and
decide **extend** (carry `build_into`), **fork** (say what load-bearing model changes),
or **greenfield** (cite what was checked). Record it in the vision's Lineage section.

## Phase 1 — Research

Ground every claim; cite file, PR, issue, or URL.
1. Tracker bodies (spikes, epics) when connected.
2. User evidence: calls, threads, logs; quantify.
3. Engineering ground truth: the code the PRD will touch, from `origin/main` when the
   repo is behind. A PRD that describes an API unlike the code is wrong.
4. Outside research when the seed asks for it or the domain is new.
5. Existing PRDs, visions, parked work. Never duplicate intent (the slug check's
   similarity mode flags near-duplicates).

**Failure check (every seed, one line):** `Failure under this seed: yes — <what broke,
with the observation> | no — <why this is an opportunity>`. It goes in the vision and
the run log. The run note (Phase 4) also carries it typed: `Failure: none` or
`Failure: <class> <ref> [<ref> ...]`, the class one of `recurring-failure`,
`failed-acceptance`, `consequential-obstacle`, `transient` or `other`, each ref matching the
routing policy's `evidence.ref_pattern` and naming none of its `evidence.placeholders`.
Verdict files the author does not write set a floor: a REJECT of a slug the entry's `State:`
names, in any verdict file under the home's `notes/reviews/` bound to a review launch row of
the Task since its previous entry (named on a `Review:` line or not), makes the class at least
`failed-acceptance`; a FIX or REJECT of that slug after its earlier FIX or REJECT in this home
makes it `recurring-failure` (a first FIX is answered by the repairs file). A verdict file whose
first lines name several review sessions counts for the latest-launched one (a re-review cites
earlier sessions). An entry that is not covered (Phase 2) keeps today's rules and its `Failure:`
line is not read, unless verdict files set a floor for it: then it carries the line at the
floor, and the trigger classes' `/5whysandrhyme` rule applies to it.

**Five whys (failure seeds).** Ask why up to five levels, each answered by an
observation, stopping at a level outside the system's control. PRDs target the deepest
actionable level; a shallower fix ships only as a guard beside the root fix. A failure
within the fleet's incident scope gets a `/5whysandrhyme` page (the Phase 2 table says
when); any other failure keeps this why-chain inline, recorded as `5whys=inline`.

**Rhyme (levels 6-8).** When a vision holds two or more failure addenda within seven
days, lay the chains side by side and ask once why their roots rhyme, up to three more
levels. Write `Cross-chain whys 6-8 (rhyme check <date>)` in the vision; its deepest
level becomes a rule or a structural PRD.

`reference.md` holds PM frameworks (read every time) and one domain family (read only
for that domain).

## Phase 2 — Vision

Write or extend `visions/<slug>.md` (never replace): TL;DR · Problem statement
(Customer Pain Test: who, what, why they can't, quantified cost; no solution) ·
Lineage · End-state · **What would have to be true** (the end-state run forward, three
to seven leaves marked `known | testable | assumed`, name the weakest link — it becomes
the first PRD or the first open question; when the `/wwhtbt` skill is installed, run it
and cite its `decisions/*-wwhtbt.md` page here instead of re-deriving, and when the seed
is a failure, cite its `/5whysandrhyme` page) · Cross-chain whys (when due) · Components
(one line each) · Order · Loop contract (loop-ready only) · Open questions with owners.

**Run, reuse or skip.** Each analysis skill gets one value in the run note's `Analysis:`
line (Phase 4):

| skill | run | reuse | skip |
|---|---|---|---|
| `/wwhtbt` | `ran <page>`: its subject is in scope and no valid page covers the seed | `reused <page>`: an existing page's end-state names the seed's subject and no input it cites has changed; the vision records the path and the reason. A covered entry (below) writes `reused <page> sha256=<64 hex> inputs=<manifest>`: `sha256=` is the page's current digest and `inputs=` a `sha256sum` manifest under the PRD home listing every absolute path and `file:` ref the page cites plus the entry's seed file, which the lint checks with `sha256sum -c` in the manifest's own directory | `skipped: <reason>` (an amendment of an approved vision, say); a covered entry skips only as `skipped: blocked decision=<ts>` (below) |
| `/5whysandrhyme` | `page <page>`: a failure within the fleet's incident scope, and always for the `Failure:` classes `recurring-failure`, `failed-acceptance` and `consequential-obstacle`, the page bound to a 5whysandrhyme launch row of the entry's Task | `reused <page> sha256=<64 hex>`: one analysis per incident across runs, the page bound to a 5whysandrhyme launch row of any task and cited on the `Failure:` line as `page:<path>` | `inline`: a failure outside that scope keeps the Phase 1 why-chain, and a `transient` failure takes `inline` or `skipped: transient`; `skipped: <reason>`: not a failure seed; for the three trigger classes only `skipped: blocked decision=<ts>` |

**Covered entries and recorded skips.** From the cutover date written in the run-note lint,
an entry is covered when it carries or inherits a `Mission:` line, its `State:` names a slug no
earlier entry of its `Task:` names or carries `drafted`, its `Seeds:` line carries a token the
Task's previous entry did not, or a PRD its `State:` names differs from that slug's digest in the
newest manifest an earlier entry of the Task binds (a manifest that cannot be read, or is not
its review row's `scope_id`, counts as changed). The entry's date is its header's, or its dream
launch row's when that is later. A covered entry records a page it ran, an exact reuse as above
(the manifest is written with the page and reused unchanged: one regenerated at reuse proves
nothing), or `skipped: blocked decision=<ts>`: the decisions log holds a `denied` row of that
skill and Task at that `ts`, before the entry's header, whose whole reasons are one of the
resolver's own outage texts (`policy file not found`, `policy is malformed`, `malformed policy
JSON: <Error>`, `ledger lookup unavailable; cannot verify ledger:<id> (fail closed)`,
`<skill>: policy require_permission_mode must be a non-empty string (fail closed)`, or its
policy-error form `<skill>: policy ... (policy error, fail closed)`; the `policy-missing:` texts
for a policy file the caller named, `SKILL_ROUTE_POLICY` or `--policy`, and that infix inside
caller text the resolver quotes are the caller's to cure, and a denial the caller induced, such as
a malformed policy it chose or a `PATH` without `wm-asks`, excuses no skip even when its text is
an outage's: corroborating that is A1300's producer), and no launch row of that skill, for any task, falls
between that row and the entry's header, both ends included (a launch row without a readable
timestamp counts). A request the caller can fix, a live-worker denial (the
analysis is running; reuse its page when it lands) or an uncorroborated outage is refused, and so
is any other skip text. When the run has no wiki-write scope, write the page under the PRD home's
`notes/analysis/`: it binds there by its launch row as anywhere else.

A run with `Task: none` records `reused` or `skipped:`, never `ran`. Launch a governed
analysis with a session id drawn first, so its page binds to its launch row before the
page exists: `sid=$(cat /proc/sys/kernel/random/uuid)`, then
`fable-launch.sh --route-request <request> --session-id "$sid" ...`, and ask the worker
in its prompt to write `session: <sid>` in the page header. The decisions row the
launcher appends carries the same `session`, which is what the run-note lint checks.
Launch each reviewer (Phase 3) the same way: draw its session id first and pass it as
`--session-id`, and name in the request a `review.snapshot` = a `sha256sum` manifest of
the frozen files the reviewer reads (the PRDs, the vision, the matrix), its paths absolute
or relative to the manifest's own directory, because `sha256sum -c` is run there. The
launcher's row then carries `role` review, `scope` and `scope_id`; a request without a
snapshot launches as an author, which the lint refuses on a `Review:` line. Keep the
manifest until the run note is linted. A review row written on another host records that
host's absolute `scope`. The case-11 gate reads it on this host only through the lint's
`--scope-root <recorded root>=<PRD home>`, taken from the delivered decisions source that
names the root, and every content check still applies. A recorded root of `/` (or only
slashes), or one that holds or lies inside this run's PRD home, by the path given or its real
path, is refused.

**Mission trace and edge map (before decomposition).** When a run drafts a mission (several
PRDs over one shared chain), write `notes/missions/<name>.edges.jsonl` under the PRD home
before splitting it into PRDs. Line 1 is the header: `mission` (the name), `outcome`,
`invariants` (the load-bearing ones), `prds` (every mission PRD basename), `external` (names,
or `{name, contract}` with the path or paths of that external's contract file), optional
`packet` (other packet basenames, such as the vision), optional `matrix` (the basename of the
adversarial matrix current at that freeze, Phase 3) and, for a one-PRD mission,
`single_component` with its reason. Every later line is one edge: `id`, the eight fields
`producer`, `consumer`, `command`, `trigger`, `authority`, `effect_id`, `recovery_owner` and
`postcondition`, and a `status` of `known`, `external` (one endpoint is `external:<name>`) or
`unknown` (with an `owner`). An endpoint is a `prds` member, `external:<name>` or `UNKNOWN`.
An unexplained arrow is not completion: a known edge with an empty field or an `UNKNOWN`
endpoint is refused, and an edge whose producer or runner nobody can name yet is written
`unknown` with an owner, never left out. Check the file with
`scripts/dream-run-note-lint.sh --edges <path> --prds <PRD basenames>` before decomposing;
the run note opts in with its `Mission:` line (Phase 4).

## Loop-ready fleets (`/dream loop <name>` or a profile `Loop:` line)

The vision carries a Loop contract: loop name, metric (validated by hand on 3–5 known
cases first), population, corpus + gold (gold is truth, never the baseline), proxy and
truth tiers, measure command, preflight probes, deploy target, write scope, failure
families. Build order is harness PRD → deploy PRD → feature PRDs; each feature PRD
carries `Loop: <name>: <metric it moves>`. No feature PRD ahead of the harness.

## Phase 3 — Draft

One PRD per component at `build-queue/PRD-<slug>.md`, prose to `writing-standard.md`
(outline → draft → proofread).

**Before each PRD:** PRD vs RFC vs one-pager; Customer Pain Test; ship-independently
test; slug check (the contract's `prd-slug-check.sh <slug>` if present, else search all
three dirs). Never reuse a slug, even a shipped one.

**Frontmatter = the contract's Frontmatter table.** Bullet form, first 80 lines. Write
only keys the table lists (lint:unknown-frontmatter-key) and never a key the table marks
daemon-owned. Always: `Status: queued`, `Drafted:`, `Seed:`, the target keys, `Vision:`,
`Depends-on:` when order matters. Superseding prior work → `Absorbs:` (lint). Follow
every per-repo rule the contract states. A PRD whose target is the build tool's own
repo carries the contract's hand-built marker; if the contract defines none, write
`Status: blocked` + `Blocked-on: contract hand-built marker`.

Required keys (the drift test reads this list; every key must be in the contract table):
```
- Status:
- Drafted:
- Seed:
- Vision:
```

**Body, in order:** TL;DR → Problem statement (cited) → Goals / Non-Goals → User stories
(3–7, persona-tagged; enterprise features come as capability + control-plane pairs) →
Requirements (P0/P1/P2; "fast", "seamless", "scalable", "robust" need numbers) →
Success metrics table (baseline, target, method, timeframe) → Technical considerations
→ Migration / compatibility → Open questions table → Acceptance criteria.

### Acceptance criteria

Under `## Acceptance criteria`, one AC per line: `N. P0 — Given …, When …, Then ….`
Builders count `N. ` lines; tables and prose blocks are invisible. Edge cases on every
PRD: empty input, no permission, concurrent actors, load, upstream down.

- At most the contract's AC cap (kit default 8); more → two PRDs with `Depends-on`,
  split by ship-independent seams, never by number (lint).
- Stay under the contract's line-byte cap with margin (lint).
- One repo per PRD; a second repo → sibling PRD + `Depends-on`
  (lint:cross-repo-path-in-ac).
- Never pre-assign a shared counter (migration numbers, ordinal ids); say "the next
  free number at land time" (lint:shared-counter-preassigned).
- Adding a member to a generated set goes through its generator plus a drift test; the
  AC states the property (lint:generator-set-member).
- State the property, not a count ("every tool in the registry …", not "exactly 41
  tools") — judgment.
- AC 1 proves the class closed, not the one instance — judgment.
- Never "the full suite is green" as an AC; use the contract's deferral key.

### Live ACs (when the contract defines a Live grammar)

- An AC whose Given or When names a production host, service, or public URL carries the
  contract's Live tail with a verbatim evidence command (lint:premise-ac-not-live).
- A premise check (is the premise true at all?) that only prod can answer goes in the
  `Premise:` key, never in a builder AC; the builder cannot run it.
- Every file or script the evidence names exists at the target repo's `origin/main` or
  is the deliverable of another AC in the same PRD (lint:live-evidence-referent-missing).
- Evidence follows the contract's `## Lint rules` table (shell prefixes, required
  headers, cleanup of anything the command creates). Read the table before writing
  evidence; the lint hook enforces it.
- A Live AC that can only pass after a later event (a deploy, the next measurement run)
  says so and carries `Blocked-on:` (lint:later-event-without-blocked-on).
- A precondition only a human can produce → `Status: blocked` + `Blocked-on:`.

**Anti-pattern audit:** solution-first, vague requirements, missing edge cases, scope
hedging, too big, cargo-cult features, an engineering spec posing as a PRD.

**Check each PRD:** run `dream.lint` until it exits 0, then `dream.dryrun` when live.
Fix the PRD, never the check. A finding you believe is wrong goes to the user as one
line; the PRD waits.

**Phase routing:** each phase runs the model the shared policy resolves, never an inherited
dream model (`.config/skill-routing/policy.json`, skill `dream`, launched through
`fable-launch.sh --route-request` with `decision_class` = the phase). Deterministic code:
discovery, contract, duplicates, lint, manifest, persistence. Haiku: extraction, inventory,
classification. Sonnet medium: narrow amendments, drafting an approved vision. Fable high:
new vision, prioritization, difficult decomposition (evidence refs required). Fable xhigh:
evidence-linked consequential uncertainty. Max only as an exception recorded in the ledger first.
Nested skills (wwhtbt, 5whysandrhyme) resolve their own route.
On a host without `.config/skill-routing/policy.json` and `fable-launch.sh` (redbaron
and ryzen7 on 2026-11-14), `/dream` runs on the invoking session's own model and effort;
no pin stands in for the absent route, and the Phase 4 run note writes `Route: ungoverned`.

**Whole-chain review (before the first independent review):** on a mission run, once the
edge map is written, freeze the packet: one `sha256sum` manifest under
`notes/snapshots/` listing every mission PRD, the vision and other `packet` members the
edges header names, the adversarial matrix, the edges file, the `repairs=` file in every
manifest later than the earliest `before` once any repairs row exists, and a copy of each
external `contract` file (copied beside the PRDs, so the reviewer reads the bytes the edge
cites). Once any repairs row exists, the repairs file is a packet member: list its basename
in every `scope=` manifest later than the earliest `before` any row names, including that
row's own `after`, so write the row (it names `after` by path) before freezing `after`.
Launch one reviewer through the launcher with `review.snapshot` = that manifest and a
pre-drawn `--session-id`, record its `result.json` as `result=` on its `Review:` line, and
list the chain reviews of one manifest in launch order. The prompt forbids edits to the
packet, asks the reviewer to verify the manifest with `sha256sum -c` and to construct an
implementation that satisfies every local AC while failing the mission; per finding it
asks for a counterexample, the affected consumers, the minimal correction, a
discriminating control and one failure class of `provenance`, `missing-producer-runner`,
`authority-bypass`, `unreachable-transition`, `semantic-incompatibility`,
`false-green-acceptance`, written as one row of `<verdict file>.findings.jsonl`, numbered
from the note's next free id and never re-using an id from an earlier sidecar. A sidecar is
never rewritten: only the review's own session, resumed (a launch row with role review, its
`scope_id` and `resume`, later than that session's first such launch row that is not a
resume), may write `<verdict file>.findings.corrected-<n>.jsonl`, whose first row is
`{"corrects": <the sidecar's sha256>, "session": <that session>}` and whose other rows are
the sidecar's, in order, changing only `prds` and `consumers`, with no key repeated in a row. The lint reads it for the
finding grammar and the repairs rows, keeps the original's failures in the JSON's
`findings_historical`, and refuses any other correction as `sidecar-correction-unbound`. A
sidecar row may name a consumer `external:<name>` that its review's frozen edges header does not
declare when the manifest listed next in `scope=` freezes a header that declares `<name>` and the
mission author's (not the reviewer's) repairs row from the review's manifest to that next one
names the edges file in `changed`; the lint keeps the original failure in `findings_historical`
with `declared_by` (that manifest and repairs row). The final
message ends with one `findings=<sha256 of the sidecar, or none>` line, the per-PRD verdict
lines and one `mission=<APPROVE|FIX|REJECT> <session>` line verbatim, and the `result=`
capture carries those same lines. Before the `Review:` line is written, the verdict file and the
capture each pass `scripts/dream-run-note-lint.sh --verdicts <file> --scope <manifest>` against
the review's manifest (see **Review:**). The run note's `Mission:` line gains `scope=` (the
manifests, in freeze order). A mission split over several run entries keeps one `Mission:`
name and one multi-PRD edge map, and a repair appends the re-frozen manifest to `scope=`
rather than replacing it. Until the `Mission:` line carries `scope=` and a chain review of
the last listed manifest binds, and while that manifest's latest-launched review is on no
`Review:` line, every mission PRD is held back from `eligible`. A finding of the last chain
review, whatever its `mission=` line says, holds the PRDs it names and their one-hop edge
neighbours in either direction; an unknown edge holds both its endpoints; a PRD whose verdict
in the latest chain review naming it is FIX or REJECT, or that no chain review names, is held
itself; the other PRDs go ahead.

**Adversarial pass (before review):** for each PRD in the batch, write a table with the
columns `invariant` (the requirement or AC id), `still-broken implementation` (a
plausible one that passes the ACs as written), `counterexample`, `discriminating check`
(the AC or test that tells the two apart, or `uncovered`) and `evidence` (its state and
owner), over the six case families of the Hermes adapter's
`references/adversarial-planning-pass.md`: Identity and provenance; Boundary environment;
Evidence interpretation; Alternative bypasses and ordering; Falsifier quality;
Whole-scope coverage and handoff. One file per run (on a mission run whose edges header carries
`matrix`, one per review round), `notes/reviews/<ISO-ts>-adversarial.md` under the PRD home,
holds one section per PRD, headed by a line reading `## PRD-<slug>`
and nothing else (text before the first is a preamble; a section ends at the next `##`
heading of any kind). Inside it each family is a heading line `### <family name>` (the
six names above, alone on the line, once each) over its table, or that heading followed
by one line `n/a: <reason>`; a family named only in prose is not a heading. In
`### Alternative bypasses and ordering`, when applied, two rows have `invariant` cells
beginning `unconditional fallback:` and `conditional fallback:` (a case that does not
apply keeps its prefix and continues `n/a: <reason>`). The file closes with one
`## Uncovered` listing every row whose check is `uncovered` (`none` allowed). A reviewer
finding counts as resolved only when its failure class has a discriminating check. Lint
the matrix before launching the review turn (`scripts/dream-run-note-lint.sh --matrix
<path> --states <slug=value ...>`) and fix a refusal first. The file goes into the review
packet beside the PRDs, and the review prompt asks the reviewer to end with its verdict
lines verbatim in its final message, so a `result=` capture can verify the verdict file.
It is the run note's `adversarial=<path> uncovered=<n>`; `adversarial=skipped: <reason>`
only when the run's `Review:` line is `none`. On a mission run the edges header's `matrix`
names the matrix current at each freeze: a repair round writes a new matrix and updates
`matrix` before freezing, each manifest lists the matrix its own frozen header names (the lint
reads that copy beside the manifest, at its listed digest, against the matrix grammar), and
the note's `adversarial=` names the last, which the last manifest's header and the live header
name too. Until every listed manifest's frozen header carries `matrix`, a manifest whose header
has none keeps the matrix of the entry that first listed it: a repair round inside one run
entry keeps the matrix name, and a continued legacy mission writes the new run's matrix, later
than the previous entry. A post-review entry may name the previous entry's matrix when the previous entry is of the
same task, its `adversarial=` path, its `uncovered=` and its `Mission:` `scope=` equal the
previous entry's, and its `Review:` lines are the previous entry's (a previous `Review: none`
counts as no lines) plus at least one new line, each new line's session having as its latest
launch row for the task a review of the last listed manifest (its `scope_id`). A legacy manifest first listed before `LEGACY_MATRIX_SINCE` (a
constant in the lint, recorded in `history.md`; an entry is dated by its `Route:` line's
`decision=`, else by its header ts) that lists exactly one `*-adversarial.md` keeps that one as
its matrix member, not compared with the entry's `adversarial=` name, when an entry of the
mission not later than the linted one names it in `adversarial=` or its copy at the listed
digest passes `--matrix` for the first-listing entry's `State:` slugs that are `prds` members
of its frozen header; listing none, two or more, or one neither named nor passing, it keeps the
rule above.
Updating `matrix` moves the edges file's digest between consecutive
manifests, so the repair row's `changed` lists the edges basename (it may also name the old
matrix, checked against `before`, and the new one, checked against `after`), and the round does
not cascade into `repair-hash-mismatch`.

**Review:** one review turn per batch of at most 4 PRDs, with one verdict line per PRD;
approved PRDs persist, rejected ones go back to drafting. A creative PRD, or one that
touches more than one repo or surface, is reviewed alone and persists in a batch of
one. Write each verdict as `<slug> APPROVE|FIX|REJECT <reviewer>`, one line per PRD, to a
review file; a line counts as a verdict only when its first token is a PRD slug
(`[a-z0-9][a-z0-9-]*`), so a table row or other prose beside the verdicts is ignored. The slug is the
PRD's file name without `PRD-` and `.md`, exactly as the snapshot manifest lists it, never a shortened form. The write-time check
is `scripts/dream-run-note-lint.sh --verdicts <verdict file> --scope <manifest>`: the reviewer's prompt asks it to run the check
on its own verdict file before it ends its turn, and the chain-review step runs it on the verdict file and its `result=` capture
before the `Review:` line is written. Exit 1 (`verdict-slug-unscoped`, naming the line and the slug, or `verdict-lines-missing`)
refuses the review as written. A review file is never rewritten. A verdict line whose slug the manifest does not list is
corrected only by a fresh review session: one launched through the launcher with role review on the original review's
`scope_id` (its manifest), never the original reviewer resumed, the author or another reviewer. It writes
`<verdict file>.verdicts.corrected-<n>.jsonl`. Its first row is `{"corrects": <the Review: line's file>, "sha256": <that
file's sha256>, "session": <its reviewer session>, "corrected_by": <the fresh session>}`. Then comes one row
`{"line": <the original verdict line>, "slug": <the full slug>, "verdict": <the original word>}` per original verdict line, in
order. The full slug is the token itself when the manifest lists it, else the only listed slug ending `-<token>`. The
correction adds no verdict, changes no verdict word and drops no line, and it changes at least one slug. The lint reads it for that
`Review:` line's slugs and keeps the original text in its JSON and in the `result=` comparison. The fresh session's launch is a
review launch like any other: a correction of an earlier freeze's review makes that freeze the newer one for the control-mutant
rule (`control-mutants-missing`) until a later review of the last listed manifest is launched and listed on a `Review:` line. It
refuses any other correction, one id per failed condition: `review-correction-self`, `review-correction-unlaunched`,
`review-correction-verdict-changed`, `review-correction-lines-mismatch`, `review-correction-slug-unscoped`,
`review-correction-slug-undenoted`, `review-correction-original-changed`, `review-correction-foreign`,
`review-correction-grammar` and `review-correction-noop` (every slug already its line's token). The note's `State:` tokens then carry the corrected verdicts in `Review:` line order. An APPROVE binds to the snapshot's bytes: the lint compares each APPROVE
slug's current PRD file with the digest in its reviewer's `review.snapshot` manifest, so a
later edit to that PRD needs a new review (FIX and REJECT are not pinned). On a note whose
`Mission:` line carries `scope=`, only the latest chain review (in `Review:` line order)
whose file names a slug pins that slug; an earlier chain review's APPROVE on it is
superseded by that later verdict, and under `mission=APPROVE` the whole packet is pinned to
that review's manifest.

**After the first systemic finding or material repair:** classify each finding by the six
names (`provenance`, `missing-producer-runner`, `authority-bypass`, `unreachable-transition`,
`semantic-incompatibility`, `false-green-acceptance`). A `provenance` failure repairs
provenance only: the record, not the design: `changed` names only the packet files it moved
(it may be empty), and `sweep` is optional. A systemic
class triggers a failure-class sweep across every edge incident to the affected PRDs and
consumers (the finding's `prds` and `consumers`, read from the edges copy frozen in the
`before` manifest), recorded as one row of the `repairs=` file without waiting for a full
batch: `{finding, class, author_session, before, after, changed, sweep, disposition}`, where
`disposition` is `repaired`, `declined` (with a `reason`) or `amended` (an author change
between two reviews that answers no finding: `finding` and `class` null, a `reason`, and
`changed` naming what moved). A `repaired` row's `changed` names one of the finding's PRDs or a
contract file of an external among its `consumers`; for a finding whose `prds` is empty, the
mission's edges file or a member of its edges header's `packet` counts too, never the repairs file itself. Once any repairs row exists, the repairs file is a packet
member: list its basename in every `scope=` manifest later than the earliest `before` any
row names, including that row's own `after`, so write the row (it names `after` by path)
before freezing `after`. Feedback goes to the same author: `author_session` is a session
of this run's author lineage (an author launch row under the `Task:`). Compare each changed
contract and every affected consumer against the actual `before` and `after` hashes: `before`
and `after` are consecutive `scope=` manifests, every basename that moved between two listed
manifests is in some row's `changed`, and every consumer of a changed producer appears at its
`after` digest in a later review's manifest. A repaired row's `before` may also be a listed
manifest later than its issuing review's when no chain review is bound to a manifest after
that review's, up to `before`, and each of those is the `after` of some repairs row (a partial
repair frozen without a review). A later `amended` row may carry `consolidates: [<row numbers>]`
naming earlier `amended` rows of its pair by the same author: its `changed` and `sweep` are
their union, no row is consolidated twice, and the duplicate check judges it in their place,
keeping their duplicates in the JSON's `repairs_historical`; anything else is
`repair-consolidation-mismatch`. A file a manifest lists by a relative path outside
its own directory is keyed by that path (resolved against the manifest's directory and
normalized): a row names it by path, `changed` and `added` relative to the `after` manifest's
directory and `removed` relative to the `before` manifest's, with a `delta` record `{changed:
[{path, before, after}], added: [{path, sha256}], removed: [{path, sha256}]}` whose digests
equal the two manifests' (a `changed` path whose record sits under `delta.added` is served by
it). In the undeclared-change pass, an entry in either compared manifest's directory is keyed by
its basename. One manifest listing one key at two digests, or two files of one basename, one in
each directory of a compared pair, is `mission-scope-mismatch`. A row without `delta` is a legacy row: its bare basenames keep the basename rule, and a
basename that several entries of one manifest hold is listed in the JSON's `repairs.ambiguous`,
never failed; a row with `delta` names such a file by path. A header member (a `prds`, `packet`
or `contract` file, the matrix, the edges file, and the repairs file) is keyed by its basename
in every pass and listed once per manifest, and so is a header member of the other manifest of
a compared pair; a row without `delta` that names one by path is checked by its basename, as a
bare name is.
Reuse unchanged accepted evidence: a bounded
re-review covers changed ∪ affected, and an unaffected PRD keeps its earlier APPROVE. There is
no blanket hold: only the rows' `changed` members and their affected consumers wait, until the
mission's final APPROVE. A later chain reviewer, under any verdict, names each `declined`
finding it accepts in an advisory sidecar row of class `provenance` with an `accepts` list,
which the lint reads and which needs no repair row: an accepted decline is a reviewer's row
and never an author's label, an unaccepted one keeps holding its dependents, and an author who
later agrees writes one `repaired` row after the decline. A round's hold ends with the
mission's final APPROVE.

## Amend (`/dream amend <slug>`)

Run `dream.amend <slug> <keys>` (absent → `scripts/amend-key-gate.sh <status>
<has-dispatch-iter-log> <keys>`). It reads the PRD's run state; refuse with its reason
when it denies.
- Queued, no dispatch `iter_log` → amend: re-research the delta, edit in place, keep
  every AC number, append new ACs, append `- iter_log: <ts> amended by /dream (<seed>) —
  <what changed>`, log it.
- An open run reads a snapshot, so an amend is invisible to it; the hook says what the
  operator must do instead.
- Started, blocked, or parked → only `Superseded-by:` / `transferred_acs:`; otherwise
  draft a successor with `Absorbs:`.
- Wrong premise → successor, never an amend.

## Phase 4 — Persist

With `dream.persist` live: call it per batch of at most 4 PRDs, passing the review file
through the contract's args (`--review <file>`). It regenerates the manifest, guards the
diff, commits, pushes, and checks each PRD is eligible to build.
An ineligible PRD fails the batch; fix it and re-run.

Without it:
1. Regenerate `MANIFEST.md` from frontmatter across the three dirs (atomic write; both
   `- Key: v` and `Key: v`); stop if the diff touches lines this run did not add.
2. `git pull --rebase`; stage only this run's files; commit
   `dream: <N> PRDs (<slugs>)`; push.

Then append the run note to `notes/dream-log.md`:
```
## <ISO-ts>  /dream  vision-<slug>
Contract: <path>   Hooks: <live hooks>
Seeds: <Seed values>
Lineage: extend <repo> | fork <repo> | greenfield
Drafted: PRD-foo.md, PRD-bar.md   Build order: foo → bar
Lint: <clean | findings fixed>   Eligibility: <per slug>
Task: <canonical id | none>   Consumer: <name | none>
Route: <route> <model_id> <effort> session=<id> decision=<decisions.jsonl ts>
Analysis: wwhtbt=<ran <path> | reused <path> | skipped: <reason>> 5whys=<page <path> | inline | skipped: <reason>> adversarial=<<path> uncovered=<n> | skipped: <reason>>
Consumption: <record path>
Review: <verdict file path> reviewer-session=<id> [result=<json path>]
State: <slug>=<value> [<slug>=<value> ...]
Mission: <name> edges=<path> [scope=<manifest>[,<manifest>...]] [repairs=<path>] [withdrawn=<manifest>[,<manifest>...]]
Open questions: <items>
```
The six record lines, each on one line (`Mission:` only on a mission run):
- `Route:` names the launcher's decisions row (its `ts`) and the drafting session. On a
  host with no decisions log write `Route: ungoverned session=<id> host=<hostname>`. On a
  host that has one, only a launcher-started run passes: a typed `/dream` there writes
  `Route: ungoverned`, and the lint's `route-ungoverned-on-governed-host` stays in the
  note. `Task: none` admits only `Route: ungoverned`. No `account=`: the row holds it.
- `Review:` one line per reviewer session, or exactly one `Review: none`.
- `State:` values: `drafted`, `linted`, `reviewed:APPROVE|FIX|REJECT`, `persisted:<sha>`,
  `pending-scan`, `eligible`, `ineligible`. A slug repeats once per state it reached, in
  order (`foo=reviewed:FIX foo=persisted:<sha>` is a push after a FIX verdict). Its
  `reviewed:` tokens are exactly the verdicts the `Review:` files give it, in line order.
- `Mission:` names the mission and its edge map (`edges=`). A mission keeps one `Mission:`
  name and one edge map across its entries: a later entry of the same `Task:` inherits the
  `edges=`, `scope=` and `repairs=` tokens it omits, never names another edge map, and carries
  the line whenever its `State:` names a member of the mission (the live header's `prds`, the
  edges copy frozen beside every `scope=` manifest, and earlier entries' `State:` slugs). A
  run without the line lints as before. A freeze named last in `scope=` before it is written,
  and then never written, is dropped by a later entry's `withdrawn=<manifest>`: only when
  nothing is at the manifest's path, as written or normalized; no line of the decisions source
  scopes or names it (in a JSON row, any string value that resolves to the manifest; a line
  that is no JSON object, when it names it); it is the last element of the latest earlier list
  that names it; no row of any repairs file the Task's entries name names it (a file that
  cannot be read, a line that is no JSON object, or a row whose `before` or `after` is no
  path string rules nothing out); and that
  entry's own `scope=` is the previous entry's list without it, followed only by appended
  manifests. The token is never inherited, and the
  earlier entries are left as written.
- Paths are relative to the PRD home or absolute.

**Consuming analysis findings.** On and after the cutover date written in the lint, a note
whose `Analysis:` line binds a page (`wwhtbt=ran|reused`, `5whys=page|reused`) carries one
`Consumption: <record path>` line naming the run's consumption record, a JSONL file under the
PRD home (`notes/consumption/<ISO-ts>-<slug>.jsonl`), and so does a covered note while an earlier
record of the same Task still has an unconsumed row; a note that binds no page and inherits no
unconsumed row needs no line. The record binds every finding of each page: the falsifier
(wwhtbt `# Weakest link`, 5whysandrhyme `WWHTBT (the weakest link):`) and each `# Mechanisms`
item whose state word is not exactly `LIVE` or `MERGED`. Its grammar is
`analysis-consumption.v1`, one JSON object per line: `id` (unique in the file), `page` (as
written on the `Analysis:` line), `page_sha256`, `finding` (`falsifier` or `mechanism:<n>`, n the
item's 1-based number under `# Mechanisms`), `binding`, `author_session`, the binding's own keys
and an optional `note` (free text, never read as a binding). The five bindings:
- `requirement`: `prd` (a queued PRD) and `ac`, whose AC line names `<page basename>#<finding>`
  and carries a backticked command or a `tests/` path. A falsifier row adds `kill` =
  {`script`, `sha256`, `string`}: the page's own falsifier script, its digest and the kill
  string the AC line carries; it names AC 1 of a first PRD (no `Depends-on` inside the
  mission), and a falsifier owned outside the run binds `repair`, `residual` or `pending`. A
  mechanism row adds `control`, the discriminating control its AC test runs.
- `repair`: `ask`, `owner` and `successor`. The canonical ask names `<page basename>#<finding>`,
  the successor's text carries `closes-after=row:<ask>`, and the successor's done-check (or that
  of a row it closes after) is one plain bash command running `dream-run-note-lint.sh
  --consumption <record> --task <successor> --require-closed`; a satisfied repair shows an
  `accept` FAIL then a run PASS at one sha.
- `test`: `repo`, `commit` (40 hex) and `path`, a file at that commit naming the finding.
- `residual`: `owner`, `evidence` (refs matching the routing policy's `ref_pattern`) and
  `accepted_by`, a review session of the Task outside the author lineage whose own verdict file
  holds the line `accepts <id>`; optional `prd`, and `part` for a residual part of a finding.
- `pending`: `owner`, `due`, and `ask` and `successor` checked as for `repair`; optional `prd`.
A session, run id, rc, report or receipt path binds nothing. An unconsumed finding (a pending
row, a refused row, an unbound finding, a covered note's WWHTBT skip, or a 5whys skip under a
trigger-class `Failure:`) holds only what it names. A row naming `prd` holds that slug, and a
refused one every `State:` slug too when that PRD is none of the run's. A row naming no `prd`
holds the successor alone when the canonical ledger shows that successor still open with its
done-check running this lint, and every `State:` slug otherwise, as an unbound mechanism and that
5whys skip do. An unbound falsifier, a refused falsifier row and the WWHTBT skip hold the first
PRDs (every member when none is first). A note whose Task cannot be read (no `Task:` line, or
one from which no Task id can be read) holds every `State:` slug, since no earlier record of
its Task can be checked; a `Task: none` note has no Task whose earlier records apply. A held
slug cannot
reach `eligible`, and an earlier record's unconsumed row keeps holding until a later record
binds the same page and finding as consumed, or binds that page whole at its current bytes
(every current finding consumed) once the finding has left the page. `scripts/dream-run-note-lint.sh --consumption <record> --task <T> [--page <page>]
[--prd-home <dir>] [--reviews <dir>] [--require-closed] [--json]` answers the same question for
a done-check or a plugin: exit 0 consumed, 1 not, 2 cannot tell.

After appending the note, run `scripts/dream-run-note-lint.sh notes/dream-log.md --last
--json` on it. A note with a `Mission:` line is also checked for `mission-grammar`,
`mission-edges-missing`, `edge-grammar`, `edge-unexplained`, `edge-unknown-unowned`,
`edge-node-unlisted` and `mission-prd-unlisted`, and one whose line carries `scope=` for
`mission-scope-mismatch`, `mission-scope-incomplete`, `mission-review-missing`,
`mission-verdict-missing`, `mission-finding-incomplete`, `sidecar-correction-unbound`,
`mission-snapshot-stale` and
`mission-approval-blocked` (the last also without `scope=`, for a member reaching
`eligible`), and for its repairs (`repairs=`, or a finding followed by a later chain review,
or a digest moving between two listed manifests) for `repair-grammar`,
`mission-repairs-missing`, `repair-duplicate`, `repair-missing`, `repair-class-mismatch`,
`sweep-missing`, `repair-author-mismatch`, `repair-hash-mismatch`, `repair-scope-mismatch`,
`affected-consumer-unreviewed`, `repair-declined-unaccepted` and
`repair-consolidation-mismatch`. A note on or after the cutover
is also checked for `consumption-missing`, `consumption-grammar`, `consumption-binding-invalid`,
`consumption-binding-not-discriminating`, `consumption-repair-unbound`,
`consumption-repair-unproven`, `consumption-residual-unaccepted`, `consumption-pending-overdue`,
`consumption-receipt-only`, `consumption-finding-unbound`, `consumption-page-stale`,
`consumption-page-unparsed`, `canonical-unavailable`, `falsifier-not-first` and
`consumption-blocked`; its JSON lists the held slugs under `consumption.held`. Fix a finding you can fix and rerun the lint before the reply. A finding
you cannot fix (`route-ungoverned-on-governed-host`; `analysis-page-unbound` for a page
another worker wrote) stays in the note and is quoted in the reply with the lint's JSON.
The reply quotes the `State:` line and the provenance labels, `snapshot` and `mission` among them
(`mission`: `verified` for a bound `mission=APPROVE` with no mission finding, `self` for a
FIX, REJECT or refused chain, `none` without a `Mission:` line):
`verified` when every `Review:` row is a reviewer launched with a snapshot whose bytes its
APPROVEs still match, `legacy` for reviewer rows written before the launcher recorded a
role (reported, never a pass), `none` beside `Review: none`, else `self`; `verified` counts a
superseded APPROVE as matched, and the JSON names it under `superseded`. The labels mean consistent
with the launcher's record on this host (`boundary`), a verified `result=` capture
(`checked`), a gate-protected wiki page (`gated`) or the drafter's word (`self`); the
decisions log is a same-user file, so none of them is authentication (`trust: same-uid`).

`Status: queued` in `build-queue/` is the queue; end by stating the build order. Wiki
publication is opt-in: ask when write tools exist.

## Invocations

`/dream` (interactive) · `/dream <topic>` · `/dream project <name>` ·
`/dream loop <name>` · `/dream from <ticket>` · `/dream amend <slug>` ·
`/dream visions` (list and exit).

## Hard rules

1. Every PRD follows the PRD standard and names its `Seed:`.
2. Amend only through the amend hook or gate; otherwise draft a successor. Never delete.
3. Cite the research; an assertion without evidence is fiction.
4. Visions and logs are append-only.
5. Write to the build contract in force, never to memory of another build.
6. Grounded by default; creative only on an explicit ask, with `Falsifier:` and
   `Premise:`.
7. Lineage before greenfield.
8. Failure check on every seed; five whys before a fix; rhyme when chains pile up.
9. What would have to be true before decomposing; the weakest link goes first.
10. Loop-ready means harness-first.
11. A PRD leaves the drafter only with its lint hook clean.
12. No credentials or internal identifiers in PRDs; env-var names only.
13. The writing standard governs all prose.
