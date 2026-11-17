# drei fixture (PRD-dream-mission-edge-map)

One passing mission home for `skills/dream/scripts/dream-run-note-lint.sh`, linted by
`tests/drei_ac0N_*.sh` through `tests/drei_lib.sh` (copied into a temporary directory with a
private HOME and `--decisions decisions.jsonl`; each case mutates one element). Session ids
are synthetic. This directory stays byte-unchanged after it lands (PRD-dream-mission-chain-review
R9, PRD-dream-failure-class-sweep R8).

- `decisions.jsonl`: one `dream` author launch row of task `EI-1` (session `eeeeeeee-…0001`,
  ts `2026-11-16T09:00:00-08:00`), written by hand to the fourteen-field shape of
  `tests/fixtures/drrec/verified/decisions.jsonl` (ts, decision, task_id, skill, route, model,
  effort, account, session, resume, reasons, role, scope, scope_id).
- `home/built-prds/PRD-a.md`, `home/built-prds/PRD-b.md`: the two mission PRD stubs (the carbon
  prd-write-gate refuses hand-written `build-queue/` stubs).
- `home/notes/missions/drei-mission.edges.jsonl`: the edge map: a header (`mission`
  drei-mission, `outcome`, one invariant, `prds` [PRD-a.md, PRD-b.md], `external` [hermes with a
  `contract` path]) and four edges: E1 and E2 `known` (a → b, b → a), E3 `external`
  (b → external:hermes), E4 `unknown` (a → UNKNOWN) with an `owner`.
- `home/notes/dream-log.md`: one entry with `Task:`, `Route:` (the author row), `Analysis:`
  (adversarial skipped), `Review: none`, `State: a=linted b=linted` and
  `Mission: drei-mission edges=notes/missions/drei-mission.edges.jsonl`. It lints exit 0, and
  exit 0 under the predecessor lint 373ff679, which ignores the line.
- `home/notes/dream-log-two.md`: the two-entry variant for the continuity rule (R1): entry 1
  (`2026-11-16T10:00:00-08:00`) carries the line with `scope=notes/snapshots/drei-m1/snapshot.sha256`;
  entry 2 (`2026-11-16T11:00:00-08:00`, the same `Task:`) carries no `Mission:` line and
  `State: a=linted a=eligible` (a `prds` member).
- `home/notes/snapshots/drei-m1/snapshot.sha256`: the frozen manifest entry 1 names; it lists
  `PRD-a.md`, `PRD-b.md` and `drei-mission.edges.jsonl`, frozen copies of which sit beside it
  (`home/notes/snapshots/drei-m1/PRD-a.md`, `PRD-b.md`, `drei-mission.edges.jsonl`).
