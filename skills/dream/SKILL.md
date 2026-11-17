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
`behind <n>`, cite from `git show origin/main:<file>` and add
`Cited-tree: <repo>@<remote-sha>` to the PRD. `dirty`: cite local, note the count.
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
the run log.

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
| `/wwhtbt` | `ran <page>`: its subject is in scope and no valid page covers the seed | `reused <page>`: an existing page's end-state names the seed's subject and no input it cites has changed; the vision records the path and the reason | `skipped: <reason>` (an amendment of an approved vision, say) |
| `/5whysandrhyme` | `page <page>`: a failure within the fleet's incident scope | — | `inline`: a failure outside that scope keeps the Phase 1 why-chain; `skipped: <reason>`: not a failure seed |

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
manifest until the run note is linted.

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
Before launching it, run the pre-launch packet check below (`--packet-only --pending`).
Launch one reviewer through the launcher with `review.snapshot` = that manifest and a
pre-drawn `--session-id`, record its `result.json` as `result=` on its `Review:` line, and
list the chain reviews of one manifest in launch order. The prompt forbids edits to the
packet, asks the reviewer to verify the manifest with `sha256sum -c` and to construct an
implementation that satisfies every local AC while failing the mission; per finding it
asks for a counterexample, the affected consumers, the minimal correction, a
discriminating control and one failure class of `provenance`, `missing-producer-runner`,
`authority-bypass`, `unreachable-transition`, `semantic-incompatibility`,
`false-green-acceptance`, written as one row of `<verdict file>.findings.jsonl`, numbered
from the note's next free id and never re-using an id from an earlier sidecar; no findings
means no file (the reviewer writes no sidecar, and its line reads `findings=none`). The final
message ends with one `findings=<sha256 of the sidecar, or none>` line, the per-PRD verdict
lines and one `mission=<APPROVE|FIX|REJECT> <session>` line verbatim, and the `result=`
capture carries those same lines. The run note's `Mission:` line gains `scope=` (the
manifests, in freeze order). A mission split over several run entries keeps one `Mission:`
name and one multi-PRD edge map, and a repair appends the re-frozen manifest to `scope=`
rather than replacing it. Until the `Mission:` line carries `scope=` and a chain review of
the last listed manifest binds, and while that manifest's latest-launched review is on no
`Review:` line, every mission PRD is held back from `eligible`. A finding of the last chain
review, whatever its `mission=` line says, holds the PRDs it names and their one-hop edge
neighbours in either direction; an unknown edge holds both its endpoints; a PRD whose verdict
in the latest chain review naming it is FIX or REJECT, or that no chain review names, is held
itself; the other PRDs go ahead.

**Pre-launch packet check (after each freeze, before its reviewer launches):** on a mission
run, write the pending entry to a file outside `notes/dream-log.md`, never appended to the log as a
draft: its `Task:`, `Route:` (this run's), `Mission:` (`scope=` including the new manifest, and
`edges=`, `repairs=` and `withdrawn=` where they apply), the full `Analysis:` line (`adversarial=`),
`State:` (this run's slugs, repeating the re-listed reviews' `reviewed:` tokens; a header member that
reached no state in this run is not named before launch and enters the Phase 4 `State:` through the
`reviewed:` token its verdict gives) and its `Review:` lines with `result=`: the chain reviews listed
by the last same-Task entry that carries the `Mission:` line, re-listed in their order, then this
run's returned chain reviews in launch order. Then run `scripts/dream-run-note-lint.sh
notes/dream-log.md --last --packet-only --pending <file> --json` after each freeze and before
launching its reviewer. It reports only packet errors, over every listed manifest, as if the pending
entry were appended (a missing or empty note counts as one holding only that entry); it counts the
review about to launch as the following review and as a `Review:` line other than none, and refuses
a pending entry missing a `Task:`, `Mission:`, `Analysis:` or `State:` line, a slug a pending
`Review:` file names that the pending `State:` omits, and a live packet file whose bytes differ from
the digest the unbound last manifest lists. Fix its errors before the reviewer launches: a defect is
fixed before a new freeze, never in the live file alone, because the reviewer reads the frozen bytes.
An unbound manifest (one no review launch has touched) that carries an error is withdrawn and
replaced: add it to `withdrawn=<manifest>[,<manifest>...]` on the pending `Mission:` line (it keeps
its place in `scope=`, and a later entry inherits the token), freeze a corrected replacement after
it, and write any repairs row that named it again, naming the replacement, with its own `sweep` (a
row naming a withdrawn manifest is void); the lint records each withdrawal and its reason under
`mission.withdrawn`. A defect beside the manifest, such as a missing copy, is fixed by placing the
copy, not by a same-content replacement (a replacement with the withdrawn manifest's scope id is
`mission-scope-mismatch`). A manifest a review launch has touched is never withdrawn
(`mission-withdrawn-bound`): an error on it that its own frozen copies carry is held and reported
(`held_packet_errors`, which do not set the exit), and one the pending entry or a new repairs row
would introduce (for example a new matrix name that a bound manifest lists no copy of, in a mission
whose header has no `matrix`) is refused until the author keeps the old name. The packet
obligations, listed once: the matrix rule of PRD dream-matrix-per-manifest (each manifest lists the
matrix its frozen edges header names, else the first-listing entry's, and the note's `adversarial=`
names the last); a continued run writes a matrix later than the previous entry; the matrix holds a
`## PRD-<slug>` section for every PRD the last manifest's edges header lists, which is what "for
each PRD in the batch" in the adversarial pass means on a mission run; Once any repairs row exists, the repairs file is a packet member: list its basename in every `scope=` manifest later than the earliest `before` any row names, including that row's own `after`, so write the row (it names `after` by path) before freezing `after`. `sweep` on
`amended` rows (the declared edges incident to each changed PRD); and the reviewer's findings
sidecar, whose author checks its digest against the `findings=` line before writing the `Review:`
line (`findings=none` only when no sidecar file exists).

**Adversarial pass (before review):** for each PRD in the batch, write a table with the
columns `invariant` (the requirement or AC id), `still-broken implementation` (a
plausible one that passes the ACs as written), `counterexample`, `discriminating check`
(the AC or test that tells the two apart, or `uncovered`) and `evidence` (its state and
owner), over the six case families of the Hermes adapter's
`references/adversarial-planning-pass.md`: Identity and provenance; Boundary environment;
Evidence interpretation; Alternative bypasses and ordering; Falsifier quality;
Whole-scope coverage and handoff. One file per review round, `notes/reviews/<ISO-ts>-adversarial.md`
under the PRD home, holds one section per PRD, headed by a line reading `## PRD-<slug>`
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
than the previous entry. Updating `matrix` moves the edges file's digest between consecutive
manifests, so the repair row's `changed` lists the edges basename (it may also name the old
matrix, checked against `before`, and the new one, checked against `after`), and the round does
not cascade into `repair-hash-mismatch`.

**Review:** one review turn per batch of at most 4 PRDs, with one verdict line per PRD;
approved PRDs persist, rejected ones go back to drafting. A creative PRD, or one that
touches more than one repo or surface, is reviewed alone and persists in a batch of
one. Write each verdict as `<slug> APPROVE|FIX|REJECT <reviewer>`, one line per PRD, to a
review file. An APPROVE binds to the snapshot's bytes: the lint compares each APPROVE
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
`changed` naming what moved). Once any repairs row exists, the repairs file is a packet
member: list its basename in every `scope=` manifest later than the earliest `before` any
row names, including that row's own `after`, so write the row (it names `after` by path)
before freezing `after`. Feedback goes to the same author: `author_session` is a session
of this run's author lineage (an author launch row under the `Task:`). Compare each changed
contract and every affected consumer against the actual `before` and `after` hashes: `before`
and `after` are consecutive `scope=` manifests, every basename that moved between two listed
manifests is in some row's `changed`, and every consumer of a changed producer appears at its
`after` digest in a later review's manifest. Reuse unchanged accepted evidence: a bounded
re-review covers changed ∪ affected, and an unaffected PRD keeps its earlier APPROVE. There is
no blanket hold: only the rows' `changed` members and their affected consumers wait, until the
mission's final APPROVE. A later chain reviewer, under any verdict, names each `declined`
finding it accepts in an advisory sidecar row of class `provenance` with an `accepts` list,
which the lint reads and which needs no repair row: an accepted decline is a reviewer's row
and never an author's label, an unaccepted one keeps holding its dependents, and an author who
later agrees writes one `repaired` row after the decline. A round's hold ends with the
mission's final APPROVE. Each re-frozen `after` passes the pre-launch packet check
(`--packet-only --pending`) before its reviewer launches.

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
- `Review:` one line per reviewer session, or exactly one `Review: none`; a later entry of a
  mission re-lists the earlier entry's chain reviews before its own, because the lint reads chain
  reviews only from the linted entry, and that entry's `State:` repeats their `reviewed:` tokens.
- `State:` values: `drafted`, `linted`, `reviewed:APPROVE|FIX|REJECT`, `persisted:<sha>`,
  `pending-scan`, `eligible`, `ineligible`. A slug repeats once per state it reached, in
  order (`foo=reviewed:FIX foo=persisted:<sha>` is a push after a FIX verdict). Its
  `reviewed:` tokens are exactly the verdicts the `Review:` files give it, in line order.
- `Mission:` names the mission and its edge map (`edges=`). A mission keeps one `Mission:`
  name and one edge map across its entries: a later entry of the same `Task:` inherits the
  `edges=`, `scope=` and `repairs=` tokens it omits, never names another edge map, and carries
  the line whenever its `State:` names a member of the mission (the live header's `prds`, the
  edges copy frozen beside every `scope=` manifest, and earlier entries' `State:` slugs). A
  run without the line lints as before. `withdrawn=` names the unbound manifests withdrawn at the
  pre-launch packet check (Phase 3); each keeps its place in `scope=`, a later entry inherits the
  token, and a present one carries every inherited path.
- Paths are relative to the PRD home or absolute.

After appending the note, run `scripts/dream-run-note-lint.sh notes/dream-log.md --last
--json` on it. A note with a `Mission:` line is also checked for `mission-grammar`,
`mission-edges-missing`, `edge-grammar`, `edge-unexplained`, `edge-unknown-unowned`,
`edge-node-unlisted` and `mission-prd-unlisted`, and one whose line carries `scope=` for
`mission-scope-mismatch`, `mission-scope-incomplete`, `mission-withdrawn-bound`, `mission-review-missing`,
`mission-verdict-missing`, `mission-finding-incomplete`, `mission-snapshot-stale` and
`mission-approval-blocked` (the last also without `scope=`, for a member reaching
`eligible`), and for its repairs (`repairs=`, or a finding followed by a later chain review,
or a digest moving between two listed manifests) for `repair-grammar`,
`mission-repairs-missing`, `repair-duplicate`, `repair-missing`, `repair-class-mismatch`,
`sweep-missing`, `repair-author-mismatch`, `repair-hash-mismatch`, `repair-scope-mismatch`,
`affected-consumer-unreviewed` and `repair-declined-unaccepted`. Fix a finding you can fix and rerun the lint before the reply. A finding
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
