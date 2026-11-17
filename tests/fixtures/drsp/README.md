# drsp fixture (gate fix: superseded chain-review APPROVE pins, A1723 prerequisite)

The P1 fixture of the gate-fix rule, linted by `tests/drsp_ac0N_*.sh` through
`tests/drsp_lib.sh` (copied into a temporary directory, private HOME, `--last` with
`--decisions`). Every positive and known-bad case is this fixture plus exactly one named
mutation (`mut <name>` in `drsp_lib.sh`).

- `decisions.jsonl`: three `dream` launch rows of task `SP-1` with the launcher's fourteen
  fields: author `...0001` (10:00, the Route row), review K `...0002` (10:10, scope
  `notes/snapshots/k/snapshot.sha256`), review J `...0003` (10:40, scope
  `notes/snapshots/j/snapshot.sha256`); each `scope_id` is the manifest's canonical id
  (`dream-run-note-lint.sh --scope-id`).
- `home/built-prds/PRD-{a,b,c}.md`: the current stubs. `PRD-a.md` was edited after K's
  review; `notes/snapshots/k/` holds the bytes K saw, `notes/snapshots/j/` the bytes J saw.
- `home/notes/reviews/k.txt`, `k.json`: K's verdict `a APPROVE` and its `result=` capture.
- `home/notes/reviews/j.txt`, `j.json`: J's verdict `a APPROVE` and `mission=APPROVE <J>`,
  and its `result=` capture holding the same lines.
- `home/notes/reviews/2026-11-16T10:05:00-08:00-adversarial.md`: the matrix (`## PRD-a`,
  `## PRD-b`, `## PRD-c`, six families each, `## Uncovered`).
- `home/notes/dream-log.md`: one entry; `Review:` K then J, `State:` with both `reviewed:`
  tokens, and `Mission: drsp-fixture scope=<k manifest>,<j manifest>`.

At 373ff679 the note exits 1 with one `review-snapshot-stale` (K, slug a); with the gate fix
it exits 0, snapshot `verified`, and K's `reviews[]` object carries
`superseded: [{"slug": "a", "by": "<J>"}]`.
