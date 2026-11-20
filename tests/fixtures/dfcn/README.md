# dfcn fixtures (PRD-dream-finding-consumption)

`2026-11-18-mission-analysis-consistency-wwhtbt.md` is a byte copy of the A1724 WWHTBT page
`~/Notes/wiki/decisions/2026-11-18-mcg-validator-seam-ready-weakest-r4-held-out-wwhtbt.md`
(sha256 f84b4be8d702b1a50bdbe4672d2dff28b7da982a668c389c1b3cb5d5bad75ad2, copied 2026-11-19), under the name AC 1 of the PRD gives it:
a `# Weakest link` falsifier section and eight `# Mechanisms` items, each `state SPEC`, so nine findings need a row.

`dfcnfx.py` builds the check-mode cases (AC 2, AC 3, the H5 predicate, the no-drift control and AC 5 on a temp store driven by the close
gate's own code); `dfcnlog.py` builds the authoring-mode cases (AC 3's authoring half, AC 4 and AC 8), each a PRD home whose last run note,
dated on the cutover, is linted with `--last --json`.
