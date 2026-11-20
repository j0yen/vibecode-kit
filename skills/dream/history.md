# /dream — why the rules are the way they are

SKILL.md holds the rules. This file holds the incidents behind them, so a reader who
doubts a rule can see what it cost when it was missing. Append-only.

- **Five whys before dreaming a fix (2026-09-09, burst-lane).** The level-1 fix was
  `mkdir`. The level-5 fix was outcome-asserting verification, and that one closed
  eight faults at once. A PRD drafted from a level-1 symptom builds the wrong thing
  with perfect ACs.
- **Rhyme check, levels 6-8 (2026-09-17).** Four red gates had four correct level-5
  fixes, and all four had one shape: mechanisms shipped on fixture proof with the live
  AC deferred. Level 8 was the loop's objective. It became "all gates green" and
  "no-defer live ACs".
- **Amend in place while untouched (2026-09-15).** A queued PRD the loop deferred for
  an incomplete requirement cost a v2 plus a park, where one amend would have done.
- **Superseded-by / transferred_acs exception (2026-09-18, decision 36622292).** A
  started predecessor can hand its remaining ACs to a successor without changing any
  text a receipt cites.
- **At most 8 ACs (2026-10-05).** 11–13-AC PRDs cost about 10 M weighted tokens each,
  about 25 times a 5-AC PRD, and long branches conflicted more at land. A month of run
  history later (10-22) showed AC count does not predict rework (Spearman ≈ 0), while
  tokens still rise with it (0.34–0.37). The cap stays.
- **Hand-built repos (2026-10-05).** A build tool must not build itself. The contract
  names those repos; the skill only copies the marker line.
- **Shift-left review (2026-10-22).** One month of runs on two build hosts: 149 of 331
  merged runs failed their Live AC; 28 PRDs were parked as prd-defect while prod was
  healthy; 43 runs (about 61 M tokens) went to premise ACs the builder could not run;
  72 runs died on the 500-byte AC cap; 31 runs hit base-merge conflicts from
  pre-assigned shared numbers; 42 decision rows were duplicates or superseded
  predecessors still building; 497 PRDs shipped with no confirmed real user, and
  nothing tied a PRD to the failure it was meant to remove. The answer was code, not
  more prose: the `Seed:` key, draft-time lint hooks, and a persist hook that checks
  eligibility before the batch leaves the drafter.
- **No model or effort pin; the routing policy is the one source (2026-11-14).** The
  frontmatter pinned `model: fable` and `effort: max` after Joe's 2026-10-24 instruction,
  quoted verbatim: "make /dream use Fable Max". On 2026-11-08 Joe approved the A1301
  five-step plan in Discord #general ("Approved. build it now"); its task file
  (`dream-phase-routing.task.md` line 3) reads, verbatim: "This expressly supersedes the
  old blanket Fable/max instruction for /dream." The routing policy
  (`.config/skill-routing/policy.json`, ledger A1300) sets `forbidden_efforts: ["max"]`
  and routes Dream by decision class. A1301's commit 11cd41be (branch
  `dream-phase-routing`) removed both pins and replaced the drafting paragraph with the
  Phase routing paragraph, but sat unmerged for six days because the drift test still
  required the pins. The decisions log (`decisions.jsonl`, 156 rows, 2026-11-09 to 11-14)
  showed Dream launches at fable-xhigh 38, sonnet-medium 16, fable-high 1, denied 11, and
  at effort `max` 0: the launcher sets model and effort itself, so the pin was read by no
  governed launch and misstated the model to every reader. Installed state on 2026-11-14:
  carbon holds the policy, resolver, `fable-launch.sh` and the spawn gate; redbaron holds
  only the spawn gate; ryzen7 holds neither the policy nor the launcher (re-read on
  ryzen7 2026-11-15: still absent). One SKILL.md serves all three hosts, so the skill now
  says that an ungoverned host runs `/dream` on the invoking session's own model and
  effort, and the drift test fails on any `model:` or `effort:` line in the frontmatter.
  As read on 2026-11-14, no approvals number is recorded for either instruction (none
  in the task file, `policy.json`, the approvals report or ledger rows A1300 and
  A1301), and none is invented here. The Joe 2026-10-24 quote now lives in this entry rather than in
  SKILL.md (PRD dream-route-pin-removal).
- **Superseded chain-review pins (2026-11-16, gate fix, A1723 prerequisite).** The
  A1719 snapshot pin held every listed review's APPROVE to the current bytes forever, so a
  truthful multi-round FIX loop that re-approved an edited PRD could never lint clean: the
  A1723 run note (`notes/dream-log.md`, entry `2026-11-16T22:23:45Z`, mission
  dream-early-integration) kept four stale pins (r3 edge-map, r5 chain-review and
  failure-class-sweep, r8 chain-review), each re-approved on the current bytes by the
  later-launched r9, and its only lint-clean rewrites dropped `Review:` lines, which
  falsifies the record. The gate fix lets a note's `Mission: ... scope=` list name the chain
  reviews; an earlier listed review's stale APPROVE is superseded only when the
  latest-launched bound review of the task is a listed review that re-approves the current
  bytes, is result-bound and says `mission=APPROVE`. A later FIX, a later stale pin or an
  unlisted later review keeps the pin. The rule is a strict subset of PRD
  dream-mission-chain-review R5 and is replaced when that PRD lands.
- **Mission edge map before decomposition (2026-11-16, A1723, parent A1296).** The 23
  wm-loop PRDs of the closed-loop mission each passed their own lint and two full review
  rounds of at most four PRDs per reviewer before round 3 named `R3B3-01` (CONSUMED has no
  writer; acceptance and the attempt-2 review are unreachable) and `R3B3-02` (the
  steady-state census has no runner; the ingest trigger is circular). Both are arrows
  between PRDs with no producer or no runner, and no record asked who writes `CONSUMED`:
  `Depends-on` orders builds without saying what crosses the boundary. A mission run now
  writes `notes/missions/<name>.edges.jsonl` before decomposition, every edge with its eight
  fields or an owned `unknown` status, and the run note's `Mission:` line makes the lint
  refuse an unexplained arrow (PRD dream-mission-edge-map).
- **Whole-chain review of a mission (2026-11-16, A1723, parent A1296).** Round-3 reviewers
  of the closed-loop mission found `R3B5-05 HIGH — CONSUMED has no writer; the repair
  attributes it to PRD 9 R1, whose bytes do not write it.` after a round-2 repair had
  claimed the fix, because every reviewer saw at most four PRDs and no record named a
  mission scope or a mission verdict. The first whole-mission packet (54 PRDs,
  `snapshot.sha256`, one reviewer with `role` review) was frozen at 08:00 PST on 2026-11-16
  by an orchestrator's hand, not by the skill. Phase 3 now freezes the mission packet as a
  manifest listed in the `Mission:` line's `scope=`, launches one whole-chain reviewer on
  it, and records its per-PRD verdicts, one `mission=` line and a findings sidecar with six
  failure classes; the lint refuses an incomplete scope, a missing or unbound chain review, a
  missing or unbound verdict or sidecar, a packet changed under `mission=APPROVE`, and a
  dependent PRD reaching `eligible`. Only the latest chain review naming a slug pins it,
  which replaces the gate fix's supersession rule above (PRD dream-mission-chain-review).
- **Failure-class sweep and repair rows (2026-11-16, A1723, parent A1296).** The closed-loop
  mission's wm-loop PRDs were repaired over three rounds, and each round's repair was
  re-checked only by the next full batch: `R3B5-05 HIGH — CONSUMED has no writer; the repair
  attributes it to PRD 9 R1, whose bytes do not write it.` was found in round 3 after round 2
  had claimed the fix, because nothing tied a repair to the bytes it moved, the edges it
  swept or the consumers it touched. A finding of a chain review followed by a later one now
  needs a row in the `Mission:` line's `repairs=` file (repaired, declined or amended) whose
  class, sweep over the incident edges, author lineage and `before`/`after` digests the lint
  checks; every digest that moves between two listed manifests is declared; affected
  consumers are re-reviewed at their new digests; only the changed PRDs and their consumers
  are held until the mission's final APPROVE, and a decline stands only when a later reviewer
  accepts it (PRD dream-failure-class-sweep).
- **The repairs file in every later manifest, said where the author reads (2026-11-17, A1723,
  parent A1296).** PRD dream-failure-class-sweep R1 made the repairs file a packet member from its
  first row on, and the lint enforced it (`mission-scope-incomplete` naming the repairs basename
  and the manifest), but neither the freeze paragraph nor the repair paragraph of Phase 3 said
  so. Native run2r (author 2b5b1db1) re-linted run 1's record and found no move the skill
  allows that clears the finding: the manifests frozen after the first row omit the file and a
  review binds to each manifest's bytes. Both paragraphs now carry one sentence, word for word:
  "Once any repairs row exists, the repairs file is a packet member: list its basename in every
  `scope=` manifest later than the earliest `before` any row names, including that row's own
  `after`, so write the row (it names `after` by path) before freezing `after`." The freeze
  list names the `repairs=` file with that condition, and a drift test lints fixture notes that
  follow and break the sentence (PRD dream-repairs-file-in-packet).
- **A matrix per manifest (2026-11-17, A1723, parent A1296).** The lint checked every frozen
  manifest against one matrix basename, the note's single `adversarial=` value, while the skill
  told the author to write one matrix file per run under a timestamped name. Native run3 (8
  reviews, mission APPROVE, lint exit 1) renamed its matrix each repair round: 7
  `mission-scope-incomplete` findings named the final matrix against manifests frozen before it
  existed, and 58 `repair-hash-mismatch` findings followed from rows naming the old and the new
  matrix in `changed`; the manifests were frozen, so the refusal was permanent. The edges header
  now carries an optional `matrix`, each manifest is checked against the matrix its own frozen
  header names (that copy, at its listed digest, against the matrix grammar), the last header
  names the note's `adversarial=` matrix, a renamed matrix in `changed` is checked on its own side
  of the row, and a header without `matrix` keeps the matrix of the entry that first listed the
  manifest, so the existing notes lint unchanged (PRD dream-matrix-per-manifest).
- **An analysis is run, reused exactly, or skipped only on a recorded outage (2026-11-19, A1723).**
  Of the 20 governed run-note entries on carbon (four PRD homes, read 2026-11-19), 18 said
  `wwhtbt=skipped` with free text and 2 ran a page; nine are missions. The skips were for reasons
  that had since gone away (a Fable-only route, a wiki path out of scope). The lint accepted any skip text, a `reused` it could not verify, and a failure recorded
  only in prose, so a skip made for a reason that still holds looked the same as one that no
  longer does. From the cutover date written in the lint, a covered entry (a mission, new material,
  or a PRD moved since the last manifest a reviewer bound) records a page it ran, a reuse whose page
  digest and input manifest verify, or a skip naming a denied route-outage row that no later launch
  of the same skill contradicts. A typed `Failure:` line names the class, whose floor comes from
  verdict files the author does not write, and the three trigger classes need a bound
  5whysandrhyme page. Pages may live under the PRD home's `notes/analysis/`, which removes the
  wiki-scope reason for skipping (PRD dream-analysis-trigger-record). An outage skip names one of
  the resolver's own outage texts, whole; the `policy-missing:` texts and any denial the caller
  induced are the caller's to cure, and proving an outage was not induced is the route-source
  producer's (A1300). The 2027-dated fixture families were re-dated before the cutover by a
  checked-in tool that regenerates every digest and scope id, so the cutover stays the merge date
  and every fixture keeps its output (Hermes H1/H2, 2026-11-19).
- **An analysis finding counts as consumed only by the effect it names (2026-11-19, A1723).** The
  lint read a bound analysis page's first lines for its session and nothing past them: the one
  mission page on file (A1724's WWHTBT) listed eight mechanisms, all `state SPEC`, and its
  falsifier waited in a JSON note, while chain-review findings already had a consumer (the
  repairs file) and analysis findings had none, so a run could cite a page and drop everything
  in it, and a receipt (a session, a report) stood in for consumption. From the cutover date
  written in the lint, a note that binds a page carries a `Consumption:` line naming a record
  that binds each finding to one of five bindings: a `requirement` (an AC that runs a command;
  the falsifier on AC 1 of a first PRD), a `repair` (a canonical ask whose successor's done-check
  runs this lint with `--require-closed`), a `test` (a file at a commit), a `residual` accepted
  by a review session outside the author lineage, or a `pending` row with its owner, due date,
  ask and successor. An unconsumed finding holds only the slugs it names, and the same answer is
  available as `--consumption <record> --task <T>` for a canonical done-check or the A1673
  plugin (PRD dream-finding-consumption).
- **Legacy matrices and path keys in mission records (2026-11-19, A1723, parent A1296).** The
  A1724 mission record (GEN1-GEN10) linted with 28,250 `repair-hash-mismatch` findings and one
  `mission-scope-incomplete` under the installed lint (vibecode-kit 43d5b39), the matrix and
  basename-key defects of the F28 lint-owner handoff: its rows name packet files outside the
  manifests' directories by relative path with `delta` records, which the lint compared by
  basename, so five `graph.json` files at different paths collided; and its GEN1 manifest,
  frozen before the edges header carried `matrix`, lists the one matrix its first entry named
  while the entry first listing it named a later one. Two rules of PRD
  dream-generation-aware-mission-records are built. R1: a legacy-header manifest first listed
  before `LEGACY_MATRIX_SINCE` = 2026-11-18T06:04:49-08:00 keeps the one matrix it lists when
  an entry names it in `adversarial=` or its copy passes the matrix grammar at its listed
  digest. That instant is the commit instant of the per-manifest matrix lint (vibecode-kit
  43d5b39), from which an edges header could carry `matrix`; it falls before every fixture
  the trigger-record cutover re-dated onto 2026-11-18, so those families keep their side of it. R4: an entry a manifest lists by a path outside the directories of the
  manifests compared is keyed by that path, a row names it by path with a `delta` record
  checked against both manifests, a legacy row's ambiguous bare basename is listed in
  `repairs.ambiguous`, and header members, the repairs file among them, stay basename-keyed in
  every pass, so a row without `delta` may name one by path (the repairs ledger cannot carry
  its own digest in a record). In the undeclared-change pass an entry in either compared
  manifest's directory is keyed by its basename, and one manifest listing one key at two
  digests, or two files of one basename, one in each directory of a compared pair, is
  `mission-scope-mismatch` (the PRD author's Q1 and Q2 rulings on A1723 source request 4), and so
  is one manifest listing for two files a basename that is a header member of the pair's other
  manifest only (review r20 F1: such a name is keyed by basename in the pair, and its own
  occurs-twice rule read only its own members). Re-linted with these rules, the A1724 home's 28,250 hash
  findings and its GEN1 `mission-scope-incomplete` clear, and two amended rows' unswept edges
  show as `sweep-missing`. R2 (sidecar schema), R3 (generation-local judgement and merged chain
  reviews), R5 (lineage) and the rest of R8 are not built.
- **Producer-contract repairs for an append-only mission record (2026-11-20, A1723).** The
  A1723 mission record could not be corrected where its own history was wrong: rows 111-114
  repaired their findings after a partial repair was frozen with no chain review (round 11b),
  so their `before` was not the issuing review's manifest; review 12's sidecar row R12-F3 named
  no PRD and an undeclared external, bound by its `findings=` line; and three `amended` rows of
  one manifest pair named the same files. The repairs file and sidecars are append-only, so
  three rules were added (the A1723 supervisor's decision 3, specified by the PRD author with
  negative, positive and over-strict controls). A repaired row's `before` may be a later listed
  manifest when every manifest between is unreviewed and the `after` of a repairs row. The
  review's own session, resumed, may write `<verdict>.findings.corrected-<n>.jsonl` changing
  only `prds` and `consumers`, read in the original's place with its failures kept in
  `findings_historical` (`sidecar-correction-unbound` otherwise). A later `amended` row may
  `consolidates` earlier ones of its pair, judged for duplicates in their place with theirs kept
  in `repairs_historical` (`repair-consolidation-mismatch` otherwise). Each falls back to the
  existing finding when its conditions fail, and no recorded row or sidecar is rewritten.
  Review r21 then executed two gaps in the correction rule. A review session whose only launch
  row was itself marked `resume`, or whose resume row was stamped before its review launch, had
  its correction read, though nothing showed a resumption after the review. And a corrected row
  repeating a key compared equal as parsed, while a first-wins reader saw the other value. The
  resume row must now be later than the session's first review launch that is not a resume, and
  a repeated key is refused.
  Two more repairs followed (the PRD author's addenda 2 and 3). Review 13's sidecar rows 1-3
  named a consumer, `external:<name>`, that the review's frozen header did not declare. The
  author declared it at the next freeze (the 093500Z header) with an edges row (row 136). The
  lint now accepts such a consumer when the manifest listed next declares it and the author's
  repairs row from the review's manifest to that one names the edges file. The original failure
  is kept in `findings_historical` with `declared_by`. Review 14's post-review entry (1:53:07 AM)
  named the matrix of the pre-review entry (1:22:59 AM) for the same round, which the recency
  rule read as an earlier run's matrix. A post-review entry may now carry the previous entry's
  matrix forward when the previous entry is of the same task, the matrix path, `uncovered=` and
  `scope=` are unchanged, and it keeps the previous entry's `Review:` lines (`Review: none`
  counts as none) and adds at least one, each new line's session having as its latest launch row
  for the task a review of the last listed manifest (review r23 L2, L3).
  A sixth followed (addendum 4). The 4:16:48 AM entry named the round-18 freeze 124000Z in
  `scope=` before writing it, as the skill orders, and the freeze was then stopped on Hermes'
  4:18 AM checkpoint, so the manifest was never written. The log is append-only: keeping the name
  fails the continuity check, and dropping it fails the list comparison. A later entry may now
  carry `withdrawn=<manifest>`, which drops the manifest from both checks. It applies only when
  nothing is at its path, no line of the decisions source scopes or names it, it is the last
  element of the latest earlier list naming it, no row of any repairs file the Task names names
  it, and the entry's own `scope=` is the previous list without it, followed only by appended
  manifests. Any unmet condition keeps today's findings.
  A seventh followed (addendum 5). Chain review 19's verdict file holds a markdown table, and
  its row `| FIX and UNKNOWN hold; only explicitly free proceeds | Met. ...` has FIX as its
  second token, so the lint read it as the verdict FIX for the slug `|`: three findings on every
  later run, on a reviewer-owned file no entry can repair. A verdict line's first token must now
  be a PRD slug (`[a-z0-9][a-z0-9-]*`); any other line is prose. dream-persist.sh reads a
  separate file of verdict lines only, so it is unchanged.
- **Reading a review scope recorded on another host (2026-11-20, A1723).** A1113's nine
  chain reviews ran on Carbon, and their launch rows record `scope` under Carbon's PRD home
  (`/home/jsy/.cache/dream-a1113/prds-clone`). The continuation on RedBaron holds the same
  manifests at the same home-relative paths, under another root. The lint read an absolute
  `scope` literally, so on RedBaron the case-11 union cleared the nine
  `review-provenance-missing` findings but left nine `review-scope-mismatch`. The PRD author
  ruled the explicit root map (source request 6, Q5, option A), and the lint gained
  `--scope-root <recorded root>=<this run's PRD home>`, which the gate passes for a delivered
  source whose `observed.json` names the root. A row's absolute `scope` under the recorded
  root is read at the same relative path under the local home. Both paths are recorded, in
  `scope_roots` and the review's `scope_read`. Every content check stands, and the sweep and
  pin checks take a mapped read only when it canonicalizes to the row's `scope_id`. A scope
  under no recorded root is read as before. Review r22 found the containment check reading
  only the home's real path (a home given through a link gave a false refusal) and a root of
  `//` accepted; both halves now check the home as given and its real path, and refuse a root
  that is only slashes.
