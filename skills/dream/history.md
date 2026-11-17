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
