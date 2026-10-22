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
