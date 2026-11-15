# drrec fixtures (PRD-dream-run-record)

A passing PRD home for `skills/dream/scripts/dream-run-note-lint.sh`. The `tests/drrec_ac0N_*.sh`
tests copy it into a temporary directory and mutate one element per case. Session ids are
synthetic. `decisions.jsonl` carries the eleven fields of `fable-launch.sh` `dec_row`
(dotfiles `.local/bin/fable-launch.sh` at 61d0c6a2, lines 65-70): ts, decision, task_id,
skill, route, model, effort, account, session, resume, reasons; written by hand to that shape.
The PRD stubs sit in `built-prds/` (the lint searches build-queue/, built-prds/ and parked/);
a `build-queue/PRD-*.md` path is refused by the carbon prd-write-gate hook for hand writes.
The lint's own `--selftest` builds an independent fixture set in code.
