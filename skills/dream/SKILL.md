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
actionable level; a shallower fix ships only as a guard beside the root fix.

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
the first PRD or the first open question) · Cross-chain whys (when due) · Components
(one line each) · Order · Loop contract (loop-ready only) · Open questions with owners.

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

**Drafting model:** the most capable tier in the session; mechanical work (collation,
reads, manifest, git) goes to the cheapest capable model.

**Review:** one review turn per batch of at most 4 PRDs, with one verdict line per PRD;
approved PRDs persist, rejected ones go back to drafting. A creative PRD, or one that
touches more than one repo or surface, is reviewed alone and persists in a batch of
one. Write each verdict as `<slug> APPROVE|FIX|REJECT <reviewer>`, one line per PRD, to a
review file.

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
Open questions: <items>
```
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
