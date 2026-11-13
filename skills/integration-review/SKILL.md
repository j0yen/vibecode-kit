---
name: integration-review
description: >
  Per-boundary interface review. Given a boundary (producer, consumer, interface), runs the
  deterministic read-only helpers and reports each endpoint's identity (repo + commit or path +
  sha256), installed/loaded state or explicit UNKNOWN, and one label from {observed-defect,
  conditional-risk, historical-evidence, hypothesis, positive-control}. Use on /integration-review,
  "review this interface", "who consumes X", "does the consumer accept what the producer sends".
  Static review only: it is not live acceptance.
model: sonnet
effort: medium
last_updated: 2026-11-12
---

# /integration-review — one boundary, endpoint by endpoint

Narrow, additive, read-only. It does not repair, install, send events, call providers or write
production state, and it opens no tasks or PRs; findings go to their existing canonical owner row.

## Ground rules
- Static review is not live acceptance. A source reading proves what the source says, not what runs.
- A local checkout is not current upstream until fetched: `git fetch`, read `behind N`, read
  `origin/main` when behind, and say which tree was read.
- Missing facts are `UNKNOWN`, never a pass. An UNKNOWN effect is reported and never replayed.
- Coverage is derived from the enumerated endpoint records, never from a declared number.
- Credential-shaped evidence lines (token=, sk-ant, password, key headers) are referred to by
  file and index only; never print or quote them. The validator never prints an evidence ref: it names
  the record and `evidence[i]`, and redacts any credential-shaped text in a message. Redaction covers every printed
  file name, path, option value, record id, property/required/enum name and message in all five scripts (a prefixed
  AWS key id inside a name, a URL credential whatever its scheme separator is spelled or percent-encoded, and an
  e-mail address, which is masked as well, though it is not a credential: a plain, a quoted-local-part
  (`"a b"@host`), an `@localhost`, a bracketed or dotted-quad IP-literal and any dotted domain ending in letters; a version
  pin such as `svc@1.2.3` or `pkg@2.0.0-rc.1` is not an address and prints as written. A URL credential whose password holds
  a raw `/` is masked too (a port followed by a path, `https://host:8080/@scope/pkg`, is not). A record id that must be
  redacted prints as `[credential-shaped text redacted #N]` with its position N in `records`, so two distinct redacted ids
  never print as one text and each REFUSED item stays traceable. The pattern list is a net, not a proof: a one-to-five digit
  password followed by `/` right after the colon of a URL reads as a port and is not masked).
- UNKNOWN-equivalents count as UNKNOWN everywhere the complete check reads a field (role, component, host,
  installed state, label, source repo, version, evidence and adoption refs). One shared rule
  (`scripts/ir_norm.py`): not a string, or after Unicode NFKD, removal of combining marks and variation
  selectors and of zero-width/control characters, folding of every dash/minus variant to `-`, case folding,
  whitespace collapse and dropping of edge punctuation and `=`, either a value with no letter or digit (`?`, `???`,
  `-`, `--`, `...`) or one of the placeholder family `unknown unk n/a` (any dotting or spacing: `N.A.`, `n a`),
  `undefined null nil none unavailable unspecified tbd tba todo` and `not available/applicable/known`, matched with
  spaces, dots, slashes and dashes removed. In the placeholder rule every slash look-alike (U+2215, U+2044, U+29F8, U+FF0F, U+2571 ...) and the
  backslash fold to `/` first (never inside a path: a look-alike in `/proc/<n>/exe` is not that path), so `N∕A`, `n\a` and `none⁄` are `n/a`, `none`; two equal UNKNOWN repos are never one repo. The same function decides every field. A real component named
  `none` must be given another name.
- Credential-shaped text (token/secret/password words, `ghp_`, `sk_live_`, `glpat-`, `npm_`, `hf_`, `AKIA`, `eyJ`,
  `xox`, key headers, `key=value` forms, and any 32+ character mixed-case-and-digit run such as a 40-character
  secret key; such a run is masked wherever it sits and whatever precedes it: after `/`, `s3://bucket/`, `x-` or any
  path-like prefix; a long mixed-case path is masked too, a full lowercase hex sha is not. Judged on the fully normalized
  text (NFKD, combining marks and zero-width/control characters removed, then NFKC, before any pattern is applied) and
  after decoding `\uXXXX`, `\n`, `\t` and `\r` escapes; a token split by a newline, tab or carriage return, or by their
  JSON escapes, is joined and masked in every output path including the `by_role`/`by_label` counts) is redacted from every message the scripts print, from record ids, roles, property names,
  finding ids, actors, record fields and duplicate-key names, in every script (`discriminator_check.py` included); the redactor is a pattern list, so it is a net, not a proof.

## Labels (exactly five)
`observed-defect` (reproduced on real source/behaviour) · `conditional-risk` (breaks only if a
condition holds that is not shown) · `historical-evidence` (past incident, not current state) ·
`hypothesis` (unproven) · `positive-control` (working behaviour, including a correct
committed-publish-pending). An endpoint not yet judged is `unclassified` and blocks a complete claim.

## Procedure
1. Name the boundary: producer, consumer, interface kind (http, cli, exit-code, filesystem, event,
   receipt, identity, schema, ordering, retry, trust, rollback, other).
2. Per endpoint capture identity (repo, commit or path, sha256, version) and installed/loaded
   state (`installed|loaded|source-only|UNKNOWN`). Hash with `sha256sum`; do not guess.
3. For an actor-name or case-pattern filter, run
   `python3 -I scripts/discriminator_check.py FILE --line N --names a,b,c --sha256 HEX`.
   The file is parsed as text, never executed. A refused name is `conditional-risk` unless it is
   an intended refusal (`--expect-refuse`); it is not evidence that live messages are lost.
4. Compare schemas with `scripts/schema_compat.py OLD NEW --direction producer-first|consumer-first|both
   --consumer closed|open`. Changes are classified by who is on the new schema: an added enum value
   a closed consumer will receive is incompatible; one only a new consumer accepts can be
   compatible; a changed regex is UNDETERMINED, never compatible; unknown keywords present in either schema are
   breaking; an added items constraint tightens and a removed one loosens; enum values compare by
   JSON type (`1` is not `true`); a `type` added tightens and one removed loosens; a `$ref` retargeted (or
   swapped with an inline schema) has its two local targets compared, a target that is not a `#/...`
   pointer in its own document is UNDETERMINED (a `$ref` swapped with an equal inline schema, or identical files, is
   compatible: note only); `additionalProperties` as a schema is compared (open -> schema tightens, schema -> open
   loosens), and a property added under an old `additionalProperties` schema is checked against that schema
   (producer-first incompatible, for a closed consumer, when the new type is not accepted by it); an unsupported
   keyword with equal text on both sides is not a change (a note; UNDETERMINED when the same subtree changes). A list-shaped or otherwise unreadable
   `properties`/`definitions`/`required`/`enum` is rc 2, never a compatible result.
5. Record endpoints in a register (`schema/register.schema.json`) and run
   `python3 -I scripts/register_validate.py REGISTER.json`. It refuses `all-interfaces-complete`
   while any role, endpoint, caller, installed state, version, label or evidence is UNKNOWN/missing or
   any row is `family: UNASSIGNED` (kept under partial, counted, named by `record:code`), when there
   are zero records, when a timestamp is not parseable ISO-8601 or has no UTC offset (an offset-less time is
   ambiguous and is never read in the host time zone) or is later than the reference time plus 300 s
   (`--now ISO8601-with-offset` sets the reference time, default the system clock), or when `loaded` lacks
   `adoption_evidence`. An omitted `captured_at` on a source or `observed_at` on an evidence ref is as refused as
   an unparseable one (staleness is unprovable); `adoption_evidence` timestamps follow the evidence rules when
   stated (garbage, offset-less, future, or observed before the source capture: refused), and an unstamped
   adoption ref is refused like an unstamped evidence ref (`missing-timestamp`, naming the record; a warning under
   `partial`): `complete` never passes while any adoption ref has no parseable `observed_at`. `validate(now=...)` takes an aware
   datetime or None (the wall clock); a naive datetime raises ValueError, it is never silently replaced.
   Adoption rule: a ref is a positive observation of a running process only when it states a
   `/proc/<n>/exe|cmdline|comm|status|stat|cwd|fd` path, or `pid` with a positive integer (no sign, no `+`/`-` before the digits,
   no `0`, `1e3`, `1.5` or `0x1f`; `pid=-1` is the no-process sentinel; `pid-1` joined by a hyphen is the one accepted spelling) plus `exe`, `cmdline`,
   `comm` or `command`, or a listing tool (`ps pgrep pidof lsof fuser top`) with `shows|lists|reports|names|found
   process <name>`. It is refused when it carries a negation, failure, non-running-state or placeholder word (`no not none never dead exited
   defunct zombie esrch died crashed aborted failed fails n't unknown n/a tbd ...`; one list, `ir_norm.NEG_STATE`), or names a unit (`systemctl`, `list-units`, `*.service|timer|socket|...`), and a tool name,
   `pid=` with no number, or a bare keyword is not an observation. The rule is textual and conservative (a
   cmdline that itself contains `no` is refused: restate it); it does not prove the observed process is the right
   one, the reviewer still owns that. A negated statement is never counted as evidence anywhere: a prose evidence ref
   (one with a space) carrying a negation (`not verified`, `no test`, `failed`) does not count as evidence for the
   complete check (`missing-evidence` names the record; a warning under `partial`), and a negated side mark
   (`not side=producer`, `side=producer failed`) is no side mark in the extractor (role UNKNOWN, claim kept).
   The negation rule is a class, not a word: a negation or doubt word (`ir_norm.NEG_CORE` plus `NEG_DOUBT`: false, untrue,
   invalid, disproved, refuted, rejected, pending, skipped, waived, TBD, to do, disputed, any `un-` word ending in
   -ed/-ied such as unchecked or unreviewed, and a few others) anywhere in the clause before a side mark (counted from the
   previous side mark; `;`, a newline or a full stop ends a clause) or after it up to the end of the clause leaves the role
   UNKNOWN, at any distance; a negation that heads another side mark does not reach this one. The same words make a prose
   evidence ref, or a single bare word such as `skipped`, non-evidence. A second class is non-evidence, which only says the fact is not known. It is judged on every ref, whatever its shape
   (`status=unknown`, `<evidence>` and `status: unknown` are one rule), with quotes, `=`, backticks, brackets, `#`, numbers
   and dates read as decoration: a weak mark (quote, `=`, backtick, `#`, a bare number, date or version such as `v1`) beside a
   placeholder word is never a concrete anchor. A concrete anchor is a code token: a lone call, dotted or `::` token (a token with no plain word beside it: `status()`, `verify()`, `a.status`, `Status::Unknown`, `check_null()`, `pkg.module.Class.method`) is a location whatever its words, unless every word in it is a placeholder word (`unknown()`, `null::nil`, `unknown.tbd`). Beside plain words only a precise token anchors: a call `f()`, `::`, a URL with a path (a bare site root is no location), `name@version`, a file (known extension or `:line`), a module path (`pkg.mock.Server`, `util.null_case`: three or more parts that are no host name, or a `_` name) or a path (`a/b/c`, `a/b.ext`, `:line`, `lib/parser` with a conventional directory first), and it must hold a word of two or more letters other than a placeholder or framing word (`a.py:12`, `src/unknown/x.py`, `see unknown::parse`). A bare two-part dotted name or two-part slash name with no conventional directory (`see foo.bar`, `stub generator in gen.stub`: restate it with a file extension, `:line`, `()` or a module path; alone it is a location), an abbreviation (`e.g.`, `i.e.`, `b/c`, `w/o`), a mention (`@bob`) or an alternative (`unknown/tbd`, `ask bob/alice`) is no anchor beside a placeholder word (`unknown e.g. later`, `status: unknown (owner @bob)`, `status: unknown, see foo.bar`). A number anchors only as a location noun and its number (`line 12`, `row 3`, `column 8`, `page 4`, `step 4`: line row column page step offset position index), as an observed result (`returned 404`, `exit 1`, `http 200`, `code 3`) or as a result count (`3 passed`, `2 errors`); after any other word, beside a state word (`unknown pending tbd null missing awaiting` ...: the words that say the fact is not known), a date or number is decoration (a descriptor word `stub mock dummy fake draft placeholder` names an artifact and is no state word: `stub took 3 retries`, `mock listens on port 8080` stay evidence; `pending PR 12 merged` is refused, restate it with a location) (`unknown since 2026-11-12`, `status unknown as of Nov 12`, `unknown after 3 retries`, `unknown ca. 2026`, `TBD by friday 5`, `pending sprint 14` are non-evidence), and the phrases `not known`, `not available`, `not applicable`, `not provided`, `not specified`, `not set`, `not stated`, `to be determined` and `to be announced` count as placeholder words; a ref with no placeholder word is also evidence
   when it holds a digit, quote, `=` or backtick (`status 200`, `4 passed`). A ref with no anchor is non-evidence when every
   word is a placeholder or framing word (`unknown null nil n/a n.a unavailable missing pending draft empty placeholder tbc
   fixme dunno redacted withheld awaiting`, plus `status result value is the see above needs review lost gone to be verified`),
   or when it holds a placeholder word in at most six words (`ir_norm.non_evidence`): `status: unknown`, `status=unknown`,
   `result = "unknown" (2026)`, `value is nil`, `evidence: n.a.`, `source unavailable`, `needs review`, `see above`. A zero
   count of failures (`tests: 0 failed, 12 passed`) is positive, `0 passed` is not. The lists are vocabulary and cannot be
   complete: an unlisted wording is read as positive, a sentence of more than six words that holds a placeholder word and a
   content word (`unknown opcodes are rejected by the parser`) is read as evidence, and a genuine ref of six words or fewer
   that uses a listed word with no anchor (`checked the stub generator`) is refused as missing-evidence (restate it with a
   location); UNKNOWN is never filled. A path-like ref (no space, not a bare word) is not judged for negation words, only
   by the rule above.
   Scope: the `installed` rule (stated path and 64-hex sha256) is enforced by the extractor only. A
   hand-written register states `installed` on the reviewer's word, so the validator's OK line names every
   installed record taken on that word ("installed state of N record(s) taken on the declarer's word"); a
   complete claim made on it rests on that word; say so in the report.
   `path_or_command` separates two endpoints on one component; `sources` carries every stated
   source of a multi-repo component. To convert extraction rows run
   `python3 -I scripts/extract_register.py ENDPOINTS.jsonl OUTDIR` (sides and `loaded` are never
   invented; contradictory side marks give UNKNOWN; equally named endpoints fuse only on direct proof of
   one component: the same content sha256, or the same canonical repo identity (URL, `.git`, trailing `/` folded)
   with the same normalized path; a fused record carries `fusion_basis` and every source. Same-named
   components in different repos, or with distinct commits, stay separate, also when the path text is identical: rows with
   one endpoint key and a path join one record only when their stated repos (canonical) and stated commits do not differ
   (an unstated repo or commit is not a difference); otherwise each is its own record with its own record_id, and the
   validator reads two records of one family/role/host/component/path/kind as one endpoint (`duplicate-record`) unless they
   prove they differ: both state repos (canonical) and share none, or both state commits and share none. One commit written
   two ways is one commit (`ir_norm.commit_id`, the one rule): case is folded, a label (`sha:`, `sha1:`, `sha256:`, `commit `,
   `rev `, `hash `, `git:`) and zero-width/format characters or edge punctuation around the hex are dropped, and an abbreviated
   hex sha of 7+ digits equals any longer sha it prefixes (a 6-digit one is not matched). A placeholder commit is an unstated commit. THE ONE IDENTITY RULE (`ir_norm.commit_id`): a commit text names the commit it IS. (1) A sha (7+ hex digits, not all zero), or a sha that is the subject of its text, is that commit: a hex of 7+ digits with a digit (all-digit hexes included) that is a token of its own, or glued to `0x`, `g` (`v1.0-3-g<hex>`) or a label (`commit sha sha1 sha256 rev revision hash oid git id ref tree blob archive`) by `-`, `_`, `:`, `=`, `#` or `@` (or by `/`: `commit/<hex>`, `/commit/<hex>`), optionally ending in a file suffix (`.patch .diff .zip .tar.gz`) or a slash, is the same commit as the bare hex: `0x<hex>`, `g<hex>`, `<hex> (HEAD)`, `HEAD@{<hex>}`, `commit <hex> main`, a URL ending in `@<hex>` or `/commit/<hex>`, `commit-<hex>`, `commit_<hex>`, `sha_<hex>`, `rev/<hex>`, `<hex>.patch`, `archive/<hex>.zip`, `(<hex>)`, `<hex>^{commit}`. (2) A relation to a sha is another commit, a name of its own: a relation word just before the hex, optionally with a preposition (`parent revert reverts cherry-picked backport hotfix fix merge rebase onto before after since base child successor previous ...`: `parent <hex>`, `revert <hex>`, `cherry-picked from <hex>`, `hotfix for <hex>`; a word after the hex is the commit's own subject, `<hex> Revert foo` is the sha; not in a URL) or a `~N` / `^N` suffix on it (`<hex>~1`) is distinct from the sha and equal only to the same text; the relation list is vocabulary, an unlisted relation word reads as the sha (refuse, never hide). (3) Text with a hex glued to a name by `-`, `/`, `_` or `.` (`feature/abc1234-login`, `fix-abc1234`, `abc1234-dirty`, `build-<hex>`, `pull/<hex>`) is part of that name and never fuses with another name or a sha; text naming two different hexes (`merge <hexA> and <hexB>`) is its own identity, equal to neither; a tag, a release or a branch such as `feature/login` is a commit of its own; a label before `-` is not stripped from a non-hex ref (`git-2.40` and `2.40`, `rev-1` and `1` are different commits). (4) A commit text that names no particular commit is a non-identifying commit, an unstated commit exactly as a placeholder repo is an unstated repo: any UNKNOWN-equivalent (`UNKNOWN`, `TBD`, `n/a`, `null`, empty), a placeholder wording (a commit text without a digit that says nothing but placeholder and label words, or a phrase with a blank that holds a placeholder word: `unknown (pending)`, `tbc`, `pending`, `missing`, `not recorded`, `unknown commit`, `no commit`; a name without a blank such as `pending-release` or `null-handling-fix` is a commit of its own), the null object (an all-zero sha: 7 to 64 zeros, `0x0000000`, `g0000000`; the all-zero sha is a hex but names no commit), a generic moving pointer, or a reflog / upstream expression. The pointer words are `HEAD`, `FETCH_HEAD`, `ORIG_HEAD`, `MERGE_HEAD`, `main`, `master`, `trunk`, `develop`, `development`, `default`, `latest`, `tip`, `current`, and the state words `stable`, `nightly`, `dev`, `edge`, `canary`, `release`, `uncommitted`, `unrecorded`, `not yet committed`, `not committed`, `working tree`, `wip`, `local`, with an `origin/` or `upstream/` or `refs/heads/` prefix, `the`/`current`/`latest`/`branch`/`tip of`/`detached`/`working`, a trailing `commit`, `branch`, `tag` or `detached` (`origin/main`, `refs/heads/main`, `branch main`, `detached HEAD`), `~N` or `^N` suffixes on a pointer (`HEAD~1`); a longer name that merely contains one (`main-fix-12`, `mainline`, `stable-2`, `release-7`) is a name. Any `@{..}` expression (`HEAD@{1}`, `main@{upstream}`, `@{u}`, `abc1234@{upstream}`, `stash@{3}`) is a moving state of a ref and is unstated, unless the braces hold a sha (`HEAD@{<hex>}`); the pointer and state lists are vocabulary: a pointer-like word outside them (another remote or channel name) is read as a name. An unstated commit differs from nothing, so records that differ only by it, or by a spelling above, are `duplicate-record`. The
   validator finds these groups by keyed lookup (near-linear, pairwise `_conflict` is the definition and reads the same
   commit rule through `_same_commit`; a test pins the two equal on random registers), never by scanning all pairs. A record that omits its
   commit or repo is never provably different, so a pair where one side omits it is refused (a `complete` claim is REFUSED
   naming both records), exactly as the extractor joins them. Path-less rows follow the same rule: different repos or
   distinct commits stay separate records, and path-less rows never fuse across repos (only path-less rows of the same
   repo and commit, or one that states neither, merge). Distinct commits never fuse, whatever the basis
   (same sha256 or same repo identity and path), directly or through a chain of other members. A path-less member beside a
   fused cluster keeps its own record_id and key (the fused record then carries its first member path, or `fused:<rows>`),
   so the extractor's output always passes the validator's duplicate-record check. The old guess (paths rooted in their
   own repos, identities distinct) is a heuristic, off by default, enabled only by `--heuristic-fusion`; it is the one
   stated exception to the distinct-commits rule (its premise is distinct identities), it is a
   guess and its records are labelled `same-name-and-repo-rooted-paths-heuristic`; `register_validate.py` reports every record
   whose `fusion_basis` is a heuristic as `WARN heuristic-fusion [<record>]` naming the basis, under partial and complete alike: a
   `complete` declaration WARNS and does not refuse (the fusion is opt-in and labelled, rc stays 0, but the guess is never an unmarked OK;
   refusing would block a stated, opt-in choice the operator can read in the output); raw identity and
   evidence kept verbatim; an identity parses only when the whole string is
   `path+sha256:<path> <64 hex>` or `commit <40 hex>` (an all-zero sha names no commit: UNKNOWN, as the validator reads it; a trailing newline or `(dirty, unverified)` is UNKNOWN); input is split on newline only, must be UTF-8, and a duplicate JSON key
   rejects the row). Unreadable or wrong-shape input exits 2 in every script, never with a traceback;
   schema_compat never reports an unreadable input as rc 1.
5b. A "message lost" finding needs producer -> alias adapter -> installed waiter, each traced:
   `python3 -I scripts/lost_message_check.py FINDING.json`. A missing link keeps it conditional-risk.
   Links are typed (sha256 64 hex, commit 40 hex, non-blank ref) and must agree on any stated
   family, interface, message and actor chain, compared by JSON type and value (actor `1` and `true` differ);
   a claim is a message-lost claim in any case, separators, word order or synonym (`messagelost`,
   `lost-message`, `message-dropped`, `msg-loss`); a claim not recognised is not silently passed: the output
   states `"claim_recognised": false` and a `NOT-CHECKED:` line (the label is then the declarer's, unverified); a disagreeing link is named and keeps conditional-risk, and
   an actor chain that returns to an earlier actor is a cycle (inconsistent). A trace in which no family,
   interface or message is stated on two links, that lacks the producer or waiter actor, or in which family, interface,
   message or actor is UNKNOWN-equivalent (`UNKNOWN`, `?`, `N/A`, `tbd`, `none`, null) on two links (equal UNKNOWNs never
   prove agreement), is marked
   `"consistency": "unproven"` with an `UNPROVEN:` line; its label is not changed by the tool, so say in the
   report that consistency is unproven.
6. Fill `templates/boundary-report.md`. Separate states: source change, tests, independent review,
   installed discovery, native Skill invocation, fleet coverage. State which are NOT done.

## Not this skill
Installing or linking itself, repairing a finding, replaying an effect, a universal gate.
