# drmr fixture (PRD-dream-mission-chain-review)

R10's fixture: this directory's `decisions.jsonl` and `home/` hold one passing bound mission,
and `variants/` holds 18 variants of it. In `tests/drmr_lib.sh`, `use <variant>` copies `home/`
and `decisions.jsonl` into a temporary directory with a private HOME, copies
`variants/<variant>/home/` over that home when the variant has one, and replaces
`decisions.jsonl` with the variant's, so a variant holds only the files that differ from the
passing mission. Each test case starts from the passing mission or one variant and edits its
copy. Paths below are relative to this directory. Session ids are synthetic: `...0001` is the
author session `dddddddd-0000-4000-8000-000000000001`, and `...0002`, `...0003` and `...0004`
are reviewer sessions of the same form. Times are on 2027-01-04 at -08:00 unless a variant says
otherwise. The fixture files stay byte-unchanged after they land (PRD-dream-failure-class-sweep
R8).

The tests that read it are `tests/drmr_ac01_approval_blocked.sh` to
`tests/drmr_ac07_ids_compat.sh` (AC 1 to AC 7). `tests/drmr_ac07_ids_compat.sh` also recomputes
every recorded `scope_id` through `dream-run-note-lint.sh --scope-id` and checks that this
README names every file and every recorded `scope_id`. `tests/drfc_ac07_ids_compat.sh` lints a
copy of the passing mission with the 373ff679 lint and the head lint and compares the two.

## Recorded scope_ids

Each review row of a `decisions.jsonl` records the `scope_id` of the manifest its `scope` names,
computed once through `--scope-id`; author rows record none. 28 review rows record one of five
values:

- `2c538f54eb13a3077f6fd1629d18fa09a8bb633439f41f7a6b91e19e48367e83`, recorded by 20 rows: the
  review row of `decisions.jsonl`; every review row of `fix`, `later-unlisted` (three),
  `noscope`, `perprd-fix`, `preinstall-line`, `preinstall-noline`, `rereview` (two), `reused-id`
  (two), `sidecar-accepts` and `sidecar-deleted`; the t1 row of `prefix`, `twomanifest` and
  `twomanifest-fix`; the s1 row of `superseded` and `superseded-bc`. Its manifests:
  `home/notes/snapshots/mission.sha256` and the byte-identical
  `variants/prefix/home/notes/snapshots/t1/snapshot.sha256`,
  `variants/twomanifest/home/notes/snapshots/t1/snapshot.sha256`,
  `variants/twomanifest-fix/home/notes/snapshots/t1/snapshot.sha256`,
  `variants/superseded/home/notes/snapshots/s1/snapshot.sha256` and
  `variants/superseded-bc/home/notes/snapshots/s1/snapshot.sha256`.
- `b15026c7a923981f8660ef7d1d4124d324681ad47cd8e34c307e4b2cee296333`, recorded by 3 rows: the t2
  row of `prefix`, `twomanifest` and `twomanifest-fix`. Its manifests:
  `variants/prefix/home/notes/snapshots/t2/snapshot.sha256`,
  `variants/twomanifest/home/notes/snapshots/t2/snapshot.sha256` and
  `variants/twomanifest-fix/home/notes/snapshots/t2/snapshot.sha256`.
- `4c487ac25a19077f8bb8440704505738aff772a3e7620295152448738d502b69`, recorded by 2 rows: the s2
  row of `superseded` and `superseded-bc`. Its manifests:
  `variants/superseded/home/notes/snapshots/s2/snapshot.sha256` and
  `variants/superseded-bc/home/notes/snapshots/s2/snapshot.sha256`.
- `43bba67caa1fd5103d0662cd05fc753b32a31f1b018d615bdfa37ae35f635523`, recorded by 2 rows: the
  review row of `single` and `single-split`. Its manifests:
  `variants/single/home/notes/snapshots/single/snapshot.sha256` and
  `variants/single-split/home/notes/snapshots/single/snapshot.sha256`.
- `56fd70da58320cb62a1c0508bb160216578013a7b553ec5154f9770d01dc13e0`, recorded by 1 row: the
  review row of `unknown`. Its manifest:
  `variants/unknown/home/notes/snapshots/unknown/snapshot.sha256`.

`dream-run-note-lint.sh --selftest` keeps nothing in this directory. It builds its own fixtures,
the `drmr-*` ones among them, under a temporary directory, computes their `scope_id` values
there at run time and removes the directory, so no selftest `scope_id` is recorded here.

## The passing bound mission

The AC 1 to AC 6 tests lint it, as it is and edited one case at a time, and every variant
overlays it. Each PRD stub, the vision stub and the contract holds one heading line; each frozen
copy is byte-equal to its live file.

- `decisions.jsonl`: the author row (`...0001`, 09:00, empty `scope`) and the chain review's
  launch row (`...0002`, 10:00, `scope` `notes/snapshots/mission.sha256`), with the launcher's
  fourteen fields.
- `home/built-prds/PRD-a.md`: PRD stub a.
- `home/built-prds/PRD-b.md`: PRD stub b.
- `home/built-prds/PRD-c.md`: PRD stub c.
- `home/contracts/x-contract.md`: external x's contract.
- `home/notes/dream-log.md`: one entry, `## 2027-01-04T12:00:00-08:00`, Task `MR-1`: `Route:`
  names the author session; `Review:` names `notes/reviews/chain/verdict.txt`, reviewer-session
  `...0002` and `result=notes/reviews/chain/result.json`; `State:` has a, b and c `linted` and
  `reviewed:APPROVE`; the `Mission:` line is `drmr-mission` with
  `edges=notes/missions/drmr-mission.edges.jsonl` and `scope=notes/snapshots/mission.sha256`.
- `home/notes/missions/drmr-mission.edges.jsonl`: the edges file: a header (`prds` a, b and c,
  `external` x with `contract` `contracts/x-contract.md`, `packet` `drmr-vision.md`) and three
  edges: E1 a → b and E2 b → c `known`, E3 c → external:x `external`.
- `home/notes/reviews/2027-01-04T09:10:00-08:00-adversarial.md`: the adversarial matrix.
- `home/notes/reviews/chain/result.json`: the chain review's `result=` capture; its text carries
  `findings=none` and the verdict file's four lines.
- `home/notes/reviews/chain/verdict.txt`: the chain review's verdict file: `a APPROVE`,
  `b APPROVE`, `c APPROVE` and `mission=APPROVE`, each with `...0002`.
- `home/notes/snapshots/2027-01-04T09:10:00-08:00-adversarial.md`: frozen copy of the matrix.
- `home/notes/snapshots/drmr-mission.edges.jsonl`: frozen copy of the edges file.
- `home/notes/snapshots/drmr-vision.md`: frozen copy of the vision stub.
- `home/notes/snapshots/mission.sha256`: the manifest `scope=` names: the sha256 of the seven
  frozen copies beside it, by basename.
- `home/notes/snapshots/PRD-a.md`: frozen copy of PRD stub a.
- `home/notes/snapshots/PRD-b.md`: frozen copy of PRD stub b.
- `home/notes/snapshots/PRD-c.md`: frozen copy of PRD stub c.
- `home/notes/snapshots/x-contract.md`: frozen copy of the contract.
- `home/visions/drmr-vision.md`: the vision stub, the edges header's `packet` member.

## Variants

### AC 1: `tests/drmr_ac01_approval_blocked.sh`

#### `variants/unknown`

The unknown-edge variant, frozen on its own. Its edges file adds E4, an `unknown` edge from a to
b. It has its own snapshot directory and manifest under `notes/snapshots/unknown/`, a review row
(`...0002`, 10:00) recorded against that manifest, and a verdict file
`notes/reviews/unknown/verdict.txt` with three APPROVE lines and `mission=APPROVE`. With a
eligible, the note is `mission-approval-blocked` naming slug a and E4.

- `variants/unknown/decisions.jsonl`
- `variants/unknown/home/notes/dream-log.md`
- `variants/unknown/home/notes/missions/drmr-mission.edges.jsonl`
- `variants/unknown/home/notes/reviews/unknown/result.json`
- `variants/unknown/home/notes/reviews/unknown/verdict.txt`
- `variants/unknown/home/notes/snapshots/unknown/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/unknown/home/notes/snapshots/unknown/PRD-a.md`
- `variants/unknown/home/notes/snapshots/unknown/PRD-b.md`
- `variants/unknown/home/notes/snapshots/unknown/PRD-c.md`
- `variants/unknown/home/notes/snapshots/unknown/drmr-mission.edges.jsonl`
- `variants/unknown/home/notes/snapshots/unknown/drmr-vision.md`
- `variants/unknown/home/notes/snapshots/unknown/snapshot.sha256`
- `variants/unknown/home/notes/snapshots/unknown/x-contract.md`

#### `variants/noscope`

The passing mission whose `Mission:` line carries `edges=` only, with no `scope=` (R9); its
`decisions.jsonl` equals the passing one. With a, b and c eligible, each is refused with the
reason "no mission scope".

- `variants/noscope/decisions.jsonl`
- `variants/noscope/home/notes/dream-log.md`

### AC 2: `tests/drmr_ac02_scope.sh`

#### `variants/twomanifest` (also AC 1 and AC 5)

The two-manifest variant:
`scope=notes/snapshots/t1/snapshot.sha256,notes/snapshots/t2/snapshot.sha256` and
`repairs=notes/missions/drmr-mission.repairs.jsonl`. t1 freezes the passing mission's seven
files. t2's frozen edges header, like the live edges file, adds the packet member
`drmr-extra.md` and external y (`contracts/y-contract.md`); t2 also lists the repairs file. One
chain review is bound to each manifest, t1's by `...0002` at 10:00 and t2's by `...0003` at
11:00, and both APPROVE a, b and c. The repairs file holds one `amended` row from t1 to t2.
AC 2: it exits 0 with two scope_ids, and t1's frozen edges copy, absent or differing, is
`mission-scope-mismatch`. AC 1: without t2's review row and `Review:` line, every eligible
member is refused with "no chain review of the last manifest". AC 5: a changed repairs file is
`mission-snapshot-stale`.

- `variants/twomanifest/decisions.jsonl`
- `variants/twomanifest/home/contracts/y-contract.md`
- `variants/twomanifest/home/notes/dream-log.md`
- `variants/twomanifest/home/notes/missions/drmr-mission.edges.jsonl`
- `variants/twomanifest/home/notes/missions/drmr-mission.repairs.jsonl`
- `variants/twomanifest/home/notes/reviews/t1/result.json`
- `variants/twomanifest/home/notes/reviews/t1/verdict.txt`
- `variants/twomanifest/home/notes/reviews/t2/result.json`
- `variants/twomanifest/home/notes/reviews/t2/verdict.txt`
- `variants/twomanifest/home/notes/snapshots/t1/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/twomanifest/home/notes/snapshots/t1/PRD-a.md`
- `variants/twomanifest/home/notes/snapshots/t1/PRD-b.md`
- `variants/twomanifest/home/notes/snapshots/t1/PRD-c.md`
- `variants/twomanifest/home/notes/snapshots/t1/drmr-mission.edges.jsonl`
- `variants/twomanifest/home/notes/snapshots/t1/drmr-vision.md`
- `variants/twomanifest/home/notes/snapshots/t1/snapshot.sha256`
- `variants/twomanifest/home/notes/snapshots/t1/x-contract.md`
- `variants/twomanifest/home/notes/snapshots/t2/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/twomanifest/home/notes/snapshots/t2/PRD-a.md`
- `variants/twomanifest/home/notes/snapshots/t2/PRD-b.md`
- `variants/twomanifest/home/notes/snapshots/t2/PRD-c.md`
- `variants/twomanifest/home/notes/snapshots/t2/drmr-extra.md`
- `variants/twomanifest/home/notes/snapshots/t2/drmr-mission.edges.jsonl`
- `variants/twomanifest/home/notes/snapshots/t2/drmr-mission.repairs.jsonl`
- `variants/twomanifest/home/notes/snapshots/t2/drmr-vision.md`
- `variants/twomanifest/home/notes/snapshots/t2/snapshot.sha256`
- `variants/twomanifest/home/notes/snapshots/t2/x-contract.md`
- `variants/twomanifest/home/notes/snapshots/t2/y-contract.md`
- `variants/twomanifest/home/visions/drmr-extra.md`

### AC 3: `tests/drmr_ac03_binding.sh`

#### `variants/twomanifest-fix`

`twomanifest` with the t2-bound review a FIX: t2's verdict file and capture read `a FIX` and
`mission=FIX`, and its sidecar holds F1 (`missing-producer-runner` on PRD a). With the `Review:`
lines in manifest order the mission verdict is FIX; with t2's line listed before t1's, the note
is `mission-review-missing` naming `notes/reviews/t1/verdict.txt` and the verdict is null.

- `variants/twomanifest-fix/decisions.jsonl`
- `variants/twomanifest-fix/home/contracts/y-contract.md`
- `variants/twomanifest-fix/home/notes/dream-log.md`
- `variants/twomanifest-fix/home/notes/missions/drmr-mission.edges.jsonl`
- `variants/twomanifest-fix/home/notes/missions/drmr-mission.repairs.jsonl`
- `variants/twomanifest-fix/home/notes/reviews/t1/result.json`
- `variants/twomanifest-fix/home/notes/reviews/t1/verdict.txt`
- `variants/twomanifest-fix/home/notes/reviews/t2/result.json`
- `variants/twomanifest-fix/home/notes/reviews/t2/verdict.txt`
- `variants/twomanifest-fix/home/notes/reviews/t2/verdict.txt.findings.jsonl`
- `variants/twomanifest-fix/home/notes/snapshots/t1/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/twomanifest-fix/home/notes/snapshots/t1/PRD-a.md`
- `variants/twomanifest-fix/home/notes/snapshots/t1/PRD-b.md`
- `variants/twomanifest-fix/home/notes/snapshots/t1/PRD-c.md`
- `variants/twomanifest-fix/home/notes/snapshots/t1/drmr-mission.edges.jsonl`
- `variants/twomanifest-fix/home/notes/snapshots/t1/drmr-vision.md`
- `variants/twomanifest-fix/home/notes/snapshots/t1/snapshot.sha256`
- `variants/twomanifest-fix/home/notes/snapshots/t1/x-contract.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/PRD-a.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/PRD-b.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/PRD-c.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/drmr-extra.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/drmr-mission.edges.jsonl`
- `variants/twomanifest-fix/home/notes/snapshots/t2/drmr-mission.repairs.jsonl`
- `variants/twomanifest-fix/home/notes/snapshots/t2/drmr-vision.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/snapshot.sha256`
- `variants/twomanifest-fix/home/notes/snapshots/t2/x-contract.md`
- `variants/twomanifest-fix/home/notes/snapshots/t2/y-contract.md`
- `variants/twomanifest-fix/home/visions/drmr-extra.md`

#### `variants/rereview`

The same-manifest re-review: two review rows on the passing manifest. The earlier-launched
`...0002` (10:00) is the passing mission's `notes/reviews/chain/`, all APPROVE. The
later-launched `...0003` (11:00) is `notes/reviews/chain-r2/`: `a FIX`, `mission=FIX`, and a
sidecar holding F3 (`unreachable-transition` on PRD a). In launch order the verdict is FIX;
listed out of launch order, the note is `mission-review-missing`. Without chain-r2's `Review:`
line, `unlisted_review_sessions` names `...0003` and eligible a is blocked.

- `variants/rereview/decisions.jsonl`
- `variants/rereview/home/notes/dream-log.md`
- `variants/rereview/home/notes/reviews/chain-r2/result.json`
- `variants/rereview/home/notes/reviews/chain-r2/verdict.txt`
- `variants/rereview/home/notes/reviews/chain-r2/verdict.txt.findings.jsonl`

#### `variants/later-unlisted`

`decisions.jsonl` only, over the passing home: three review rows on the passing manifest, the
unnamed `...0004` at 09:30, the listed `...0002` at 10:00 and the unnamed `...0003` at 11:00.
With a eligible, a is blocked naming the later unlisted review `...0003`. With that row removed,
the earlier unnamed `...0004` is only reported.

- `variants/later-unlisted/decisions.jsonl`

### AC 4: `tests/drmr_ac04_verdict_findings.sh`

#### `variants/fix` (also AC 5 and AC 6)

The FIX fixture. The chain review's verdict file and capture read `a FIX`, `b APPROVE`,
`c APPROVE` and `mission=FIX`. The sidecar `verdict.txt.findings.jsonl` holds F1
(`missing-producer-runner`, PRD a, consumers `[external:x]`) and the advisory F2 (class
`provenance`, `accepts` F0, empty `prds`). The capture's `findings=` line is the sidecar's
sha256, and its `decisions.jsonl` equals the passing one. AC 4: it lints clean with one finding
counted; its sidecar absent or empty, or a row lacking a field or carrying an unknown class, is
`mission-finding-incomplete`. AC 5: under `mission=FIX` a changed edges file pins nothing. AC 6:
a or b eligible is blocked naming F1, and E1 for b; c eligible passes.

- `variants/fix/decisions.jsonl`
- `variants/fix/home/notes/dream-log.md`
- `variants/fix/home/notes/reviews/chain/result.json`
- `variants/fix/home/notes/reviews/chain/verdict.txt`
- `variants/fix/home/notes/reviews/chain/verdict.txt.findings.jsonl`

#### `variants/sidecar-accepts`

`fix` with an `accepts` row F9 (accepting F1) appended to the sidecar and the capture unchanged:
`mission-finding-incomplete` naming the verdict file, the capture and its `findings=` line.

- `variants/sidecar-accepts/decisions.jsonl`
- `variants/sidecar-accepts/home/notes/dream-log.md`
- `variants/sidecar-accepts/home/notes/reviews/chain/result.json`
- `variants/sidecar-accepts/home/notes/reviews/chain/verdict.txt`
- `variants/sidecar-accepts/home/notes/reviews/chain/verdict.txt.findings.jsonl`

#### `variants/sidecar-deleted`

`fix` with F1 deleted from the sidecar and the capture unchanged: the same finding as
`sidecar-accepts`.

- `variants/sidecar-deleted/decisions.jsonl`
- `variants/sidecar-deleted/home/notes/dream-log.md`
- `variants/sidecar-deleted/home/notes/reviews/chain/result.json`
- `variants/sidecar-deleted/home/notes/reviews/chain/verdict.txt`
- `variants/sidecar-deleted/home/notes/reviews/chain/verdict.txt.findings.jsonl`

#### `variants/preinstall-line`

`sidecar-accepts` with the review row's `ts` at 2026-11-16T10:00:00-08:00, before the lint's
`SIDECAR_BINDING_SINCE`, and the capture keeping its `findings=` line: still
`mission-finding-incomplete`.

- `variants/preinstall-line/decisions.jsonl`
- `variants/preinstall-line/home/notes/dream-log.md`
- `variants/preinstall-line/home/notes/reviews/chain/result.json`
- `variants/preinstall-line/home/notes/reviews/chain/verdict.txt`
- `variants/preinstall-line/home/notes/reviews/chain/verdict.txt.findings.jsonl`

#### `variants/preinstall-noline`

`preinstall-line` with no `findings=` line in the capture: `sidecar_bound` is false and nothing
fires.

- `variants/preinstall-noline/decisions.jsonl`
- `variants/preinstall-noline/home/notes/dream-log.md`
- `variants/preinstall-noline/home/notes/reviews/chain/result.json`
- `variants/preinstall-noline/home/notes/reviews/chain/verdict.txt`
- `variants/preinstall-noline/home/notes/reviews/chain/verdict.txt.findings.jsonl`

#### `variants/reused-id`

The re-used-id variant: `fix`, whose `notes/reviews/chain/` files it repeats byte for byte,
followed by a second chain review, `...0003` at 11:00 in `notes/reviews/chain-r2/` (`b FIX`,
`mission=FIX`). That review's sidecar re-uses F1 as a non-advisory row (`authority-bypass` on
PRD b, consumers `[PRD-c.md]`), so the note is `mission-finding-incomplete` naming F1 and both
sidecars (R4). Renamed to F7, nothing of R4 fires.

- `variants/reused-id/decisions.jsonl`
- `variants/reused-id/home/notes/dream-log.md`
- `variants/reused-id/home/notes/reviews/chain-r2/result.json`
- `variants/reused-id/home/notes/reviews/chain-r2/verdict.txt`
- `variants/reused-id/home/notes/reviews/chain-r2/verdict.txt.findings.jsonl`
- `variants/reused-id/home/notes/reviews/chain/result.json`
- `variants/reused-id/home/notes/reviews/chain/verdict.txt`
- `variants/reused-id/home/notes/reviews/chain/verdict.txt.findings.jsonl`

### AC 5: `tests/drmr_ac05_snapshot.sh`

#### `variants/superseded`

The superseded-APPROVE variant: `scope=` lists s1 then s2, and `repairs=` names the repairs
file. PRD a's bytes moved between s1 and s2: the live `home/built-prds/PRD-a.md` reads "repaired
between s1 and s2", s1 holds the passing copy, and s2 holds the repaired copy and the repairs
file. The s1-bound review `...0002` and the s2-bound review `...0003` both APPROVE a, b and c.
The repairs file holds one `amended` row naming `PRD-a.md` and sweep E1. It lints clean with no
`review-snapshot-stale` for the s1 line; without the s2 `Review:` line, `review-snapshot-stale`
names slug a and the s1 file.

- `variants/superseded/decisions.jsonl`
- `variants/superseded/home/built-prds/PRD-a.md`
- `variants/superseded/home/notes/dream-log.md`
- `variants/superseded/home/notes/missions/drmr-mission.repairs.jsonl`
- `variants/superseded/home/notes/reviews/s1/result.json`
- `variants/superseded/home/notes/reviews/s1/verdict.txt`
- `variants/superseded/home/notes/reviews/s2/result.json`
- `variants/superseded/home/notes/reviews/s2/verdict.txt`
- `variants/superseded/home/notes/snapshots/s1/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/superseded/home/notes/snapshots/s1/PRD-a.md`
- `variants/superseded/home/notes/snapshots/s1/PRD-b.md`
- `variants/superseded/home/notes/snapshots/s1/PRD-c.md`
- `variants/superseded/home/notes/snapshots/s1/drmr-mission.edges.jsonl`
- `variants/superseded/home/notes/snapshots/s1/drmr-vision.md`
- `variants/superseded/home/notes/snapshots/s1/snapshot.sha256`
- `variants/superseded/home/notes/snapshots/s1/x-contract.md`
- `variants/superseded/home/notes/snapshots/s2/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/superseded/home/notes/snapshots/s2/PRD-a.md`
- `variants/superseded/home/notes/snapshots/s2/PRD-b.md`
- `variants/superseded/home/notes/snapshots/s2/PRD-c.md`
- `variants/superseded/home/notes/snapshots/s2/drmr-mission.edges.jsonl`
- `variants/superseded/home/notes/snapshots/s2/drmr-mission.repairs.jsonl`
- `variants/superseded/home/notes/snapshots/s2/drmr-vision.md`
- `variants/superseded/home/notes/snapshots/s2/snapshot.sha256`
- `variants/superseded/home/notes/snapshots/s2/x-contract.md`

#### `variants/superseded-bc`

`superseded` with the s2-bound verdict file and capture naming b and c only (r6 F35):
`review-snapshot-stale` names slug a and the s1 file.

- `variants/superseded-bc/decisions.jsonl`
- `variants/superseded-bc/home/built-prds/PRD-a.md`
- `variants/superseded-bc/home/notes/dream-log.md`
- `variants/superseded-bc/home/notes/missions/drmr-mission.repairs.jsonl`
- `variants/superseded-bc/home/notes/reviews/s1/result.json`
- `variants/superseded-bc/home/notes/reviews/s1/verdict.txt`
- `variants/superseded-bc/home/notes/reviews/s2/result.json`
- `variants/superseded-bc/home/notes/reviews/s2/verdict.txt`
- `variants/superseded-bc/home/notes/snapshots/s1/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/superseded-bc/home/notes/snapshots/s1/PRD-a.md`
- `variants/superseded-bc/home/notes/snapshots/s1/PRD-b.md`
- `variants/superseded-bc/home/notes/snapshots/s1/PRD-c.md`
- `variants/superseded-bc/home/notes/snapshots/s1/drmr-mission.edges.jsonl`
- `variants/superseded-bc/home/notes/snapshots/s1/drmr-vision.md`
- `variants/superseded-bc/home/notes/snapshots/s1/snapshot.sha256`
- `variants/superseded-bc/home/notes/snapshots/s1/x-contract.md`
- `variants/superseded-bc/home/notes/snapshots/s2/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/superseded-bc/home/notes/snapshots/s2/PRD-a.md`
- `variants/superseded-bc/home/notes/snapshots/s2/PRD-b.md`
- `variants/superseded-bc/home/notes/snapshots/s2/PRD-c.md`
- `variants/superseded-bc/home/notes/snapshots/s2/drmr-mission.edges.jsonl`
- `variants/superseded-bc/home/notes/snapshots/s2/drmr-mission.repairs.jsonl`
- `variants/superseded-bc/home/notes/snapshots/s2/drmr-vision.md`
- `variants/superseded-bc/home/notes/snapshots/s2/snapshot.sha256`
- `variants/superseded-bc/home/notes/snapshots/s2/x-contract.md`

### AC 6: `tests/drmr_ac06_dependents.sh`

#### `variants/perprd-fix`

The per-PRD-FIX variant: `a FIX` in the verdict file and the capture under `mission=APPROVE`,
and the sidecar holding one finding, F1 on PRD a; its `decisions.jsonl` equals the passing one.
Eligible a is blocked naming "per-PRD verdict FIX"; c passes with dependents a and b.

- `variants/perprd-fix/decisions.jsonl`
- `variants/perprd-fix/home/notes/dream-log.md`
- `variants/perprd-fix/home/notes/reviews/chain/result.json`
- `variants/perprd-fix/home/notes/reviews/chain/verdict.txt`
- `variants/perprd-fix/home/notes/reviews/chain/verdict.txt.findings.jsonl`

### AC 7: `tests/drmr_ac07_ids_compat.sh`

#### `variants/single`

A one-PRD mission, `drmr-single`. Its edges header has `prds` [PRD-a.md] and `single_component`
with its reason, and its one edge is E1 a → external:x. It has its own manifest under
`notes/snapshots/single/` and review `...0002` (`notes/reviews/single/`: `a APPROVE`,
`mission=APPROVE`). It lints clean and echoes `single_component`.

- `variants/single/decisions.jsonl`
- `variants/single/home/notes/dream-log.md`
- `variants/single/home/notes/missions/drmr-single.edges.jsonl`
- `variants/single/home/notes/reviews/single/result.json`
- `variants/single/home/notes/reviews/single/verdict.txt`
- `variants/single/home/notes/snapshots/single/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/single/home/notes/snapshots/single/PRD-a.md`
- `variants/single/home/notes/snapshots/single/drmr-single.edges.jsonl`
- `variants/single/home/notes/snapshots/single/drmr-vision.md`
- `variants/single/home/notes/snapshots/single/snapshot.sha256`
- `variants/single/home/notes/snapshots/single/x-contract.md`

#### `variants/single-split`

`single` after a same-Task entry at 08:00 whose `State:` names a, b and c and whose
`Mission: drmr-single` line has `edges=` only: `edge-grammar` naming `single_component`.

- `variants/single-split/decisions.jsonl`
- `variants/single-split/home/notes/dream-log.md`
- `variants/single-split/home/notes/missions/drmr-single.edges.jsonl`
- `variants/single-split/home/notes/reviews/single/result.json`
- `variants/single-split/home/notes/reviews/single/verdict.txt`
- `variants/single-split/home/notes/snapshots/single/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/single-split/home/notes/snapshots/single/PRD-a.md`
- `variants/single-split/home/notes/snapshots/single/drmr-single.edges.jsonl`
- `variants/single-split/home/notes/snapshots/single/drmr-vision.md`
- `variants/single-split/home/notes/snapshots/single/snapshot.sha256`
- `variants/single-split/home/notes/snapshots/single/x-contract.md`

#### `variants/prefix`

`twomanifest`'s files and rows under a two-entry note: entry 1, at 08:00 with `Review: none`,
lists t1 and t2 in `scope=`, and entry 2 lists t1 alone: `mission-grammar` naming entry 1's
timestamp, 2027-01-04T08:00:00-08:00.

- `variants/prefix/decisions.jsonl`
- `variants/prefix/home/contracts/y-contract.md`
- `variants/prefix/home/notes/dream-log.md`
- `variants/prefix/home/notes/missions/drmr-mission.edges.jsonl`
- `variants/prefix/home/notes/missions/drmr-mission.repairs.jsonl`
- `variants/prefix/home/notes/reviews/t1/result.json`
- `variants/prefix/home/notes/reviews/t1/verdict.txt`
- `variants/prefix/home/notes/reviews/t2/result.json`
- `variants/prefix/home/notes/reviews/t2/verdict.txt`
- `variants/prefix/home/notes/snapshots/t1/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/prefix/home/notes/snapshots/t1/PRD-a.md`
- `variants/prefix/home/notes/snapshots/t1/PRD-b.md`
- `variants/prefix/home/notes/snapshots/t1/PRD-c.md`
- `variants/prefix/home/notes/snapshots/t1/drmr-mission.edges.jsonl`
- `variants/prefix/home/notes/snapshots/t1/drmr-vision.md`
- `variants/prefix/home/notes/snapshots/t1/snapshot.sha256`
- `variants/prefix/home/notes/snapshots/t1/x-contract.md`
- `variants/prefix/home/notes/snapshots/t2/2027-01-04T09:10:00-08:00-adversarial.md`
- `variants/prefix/home/notes/snapshots/t2/PRD-a.md`
- `variants/prefix/home/notes/snapshots/t2/PRD-b.md`
- `variants/prefix/home/notes/snapshots/t2/PRD-c.md`
- `variants/prefix/home/notes/snapshots/t2/drmr-extra.md`
- `variants/prefix/home/notes/snapshots/t2/drmr-mission.edges.jsonl`
- `variants/prefix/home/notes/snapshots/t2/drmr-mission.repairs.jsonl`
- `variants/prefix/home/notes/snapshots/t2/drmr-vision.md`
- `variants/prefix/home/notes/snapshots/t2/snapshot.sha256`
- `variants/prefix/home/notes/snapshots/t2/x-contract.md`
- `variants/prefix/home/notes/snapshots/t2/y-contract.md`
- `variants/prefix/home/visions/drmr-extra.md`
