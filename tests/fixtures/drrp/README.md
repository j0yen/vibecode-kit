# drrp fixtures (PRD-dream-repairs-file-in-packet R4)

The drrp tests carry no fixture files of their own: per the PRD's Technical considerations the
fixture notes reuse `tests/fixtures/drfc/` and the installed lint. `tests/drrp_ac04_lint_agrees.sh`
copies the drfc fixture through `tests/drfc_lib.sh` (`use`) and applies one mutation per case,
re-signing every manifest it edits with the lint's own `--scope-id` (`mansign`, `redit`, `repin`):

| case | base | mutation | expected |
|---|---|---|---|
| compliant-base | `base` | none (`after` lists the repairs file; row 1's `before` is `before`) | no `mission-scope-incomplete` naming `drfc-mission.repairs.jsonl` |
| compliant-three | `three` | none (`after` and `third` list it) | none |
| own-after | `base` | `after` re-frozen without the repairs line | exactly one, naming `after` |
| out-of-order | `three` | rows reordered (the F4 row, `before` = `after`, first; then the rows whose `before` is `before`); `after` re-frozen without the repairs line | exactly one, naming `after` |
| between | `three` | `third` (frozen between r2's finding F4 and its row) re-frozen without the repairs line | exactly one, naming `third` |

`tests/drrp_ac03_known_bads.sh` builds its SKILL.md copies from the landed file in a temporary
directory.
