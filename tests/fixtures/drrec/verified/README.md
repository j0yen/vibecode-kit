# verified fixture (PRD-dream-run-record-review-scope R9)

A passing run note whose `Review:` row carries `role` review, `scope` and `scope_id`, linted by
the `tests/drsc_ac0N_*.sh` tests through `tests/drsc_lib.sh` (copied into a temporary directory,
`--last` with `--decisions`). It sits in its own subtree so the drrec fixture's existing files
stay byte-unchanged.

- Source: `../review-scope/` is dotfiles `tests/fixtures/skill-routing/review-scope/` copied
  byte-for-byte from dotfiles `main` at `a244971e489bfa240782de5d56e023228bb9a48d` (the launcher
  PRD fable-launch-review-scope-guard's landing by hand, j0yen/dotfiles PR 429); every file's git
  blob id was compared equal to that commit's tree. Launcher `.local/bin/fable-launch.sh` at that
  commit: sha256 `ffb44bb45170190935e1e48a14bf418d7ac6bacb7ec5ba39067db424f8e2e81e` (the same
  launcher sha256 the copied README records against source commit `4bf514c6`).
- `decisions.jsonl`: the five `../review-scope/rows.jsonl` rows, verbatim except `scope`.
  Rewrite 1 (in the launcher repo): the original `scope` values were the absolute paths
  `/mnt/data/hand/rb-a1721-review-scope-guard-20261116/src/tests/fixtures/skill-routing/review-scope/<name>.sha256`,
  rewritten there to `<name>.sha256` (see `../review-scope/README.md`). Rewrite 2 (here):
  `happy.sha256` -> `notes/snapshots/happy.sha256` (rows 2 and 5) and `prefixed.sha256` ->
  `notes/snapshots/prefixed.sha256` (row 3, a denied row the lint never binds; its manifest is
  not copied). Empty `scope` values (author rows) stay `""`.
- `home/notes/snapshots/happy.sha256`: `../review-scope/happy.sha256`, copied. A relative
  `scope` resolves against the PRD home (`home/`); `scope_id` depends on basenames and digests
  only, so it is unchanged by the move.
- `home/built-prds/PRD-rs-alpha.md`, `PRD-rs-beta.md`: the stubs, byte-identical copies.
- `home/notes/reviews/rs-rows-review.txt` and `.json`: the verdict file and `result=` capture
  for the recorded reviewer session `0b6b700d-6ba2-4493-9d72-bc1e2da83594` (row 2), written by
  hand to the lint's verdict grammar.
- `home/notes/reviews/2026-11-16T04:05:40-08:00-adversarial.md`: the matrix the `Analysis:`
  line names (`## PRD-rs-alpha`, `## PRD-rs-beta`, six families each, `## Uncovered`);
  `wwhtbt` and `5whys` are `skipped:`.
- `home/notes/dream-log.md`: one entry; `Task:`, `Route:` and `Review:` values are the
  recorded rows' (author row 1, reviewer row 2).
