#!/usr/bin/env bash
# shellcheck disable=SC2034  # variables are read by the tests that source this file
# Shared helpers for the drvc_* tests: the Dream lint's append-only verdict correction (A1296 Increment-2 request 01,
# requests/a1296-inc2-e9d18227-request-01-dream-lint-verdict-correction.md). A review file whose verdict lines carry a
# shortened slug (PRD-<token>.md not in the reviewer's scope manifest) is corrected, never rewritten, by
# <verdict file>.verdicts.corrected-<n>.jsonl written by a FRESH review session launched with role review on the
# original review's scope_id. Reuses the drsc helpers (setup_v's verified fixture with its private HOME, lint, setline,
# decedit, jget, findline, no_traceback) and adds:
#   short_review: rewrite the verified fixture's review file and result= capture with the shortened slugs `alpha`
#                 APPROVE and `beta` FIX (the r1 shape), and the State: line the corrected verdicts need;
#   fresh_row [<session> [<python expr on r>]]: append a launch row for the fresh correction session, a copy of the
#                 original review row with its own session, a later ts and resume false, edited by the expression;
#   correction [<python expr on rows>] [<n>]: write <verdict file>.verdicts.corrected-<n>.jsonl, the valid correction
#                 of short_review's file (header, then one row per original verdict line in order), edited by the
#                 expression on the list `rows` (row 0 is the header);
#   run: lint the last entry, JSON in JS, text in OUT, exit in RC, stderr checked for a traceback.
# shellcheck source=tests/drsc_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsc_lib.sh"
S_FRESH=cccccccc-0000-4000-8000-00000000c0c1      # the fresh correction review session
S_OTHER=cccccccc-0000-4000-8000-00000000c0c2      # an unrelated session
CORR="$VERDICTS.verdicts.corrected-1.jsonl"
NL=$'\n'
SHORT_FILE="# verdicts (reviewer session $S_REV; shortened slugs, the r1 shape)${NL}alpha APPROVE fable${NL}beta FIX fable${NL}"
SHORT_RESULT="Review done.${NL}alpha APPROVE fable${NL}beta FIX fable"
SHORT_STATE="State: rs-alpha=linted rs-alpha=reviewed:APPROVE rs-beta=linted rs-beta=reviewed:FIX"
short_review() { verdicts "$SHORT_FILE" "$SHORT_RESULT" "$SHORT_STATE"; }
fresh_row() { python3 - "$DEC" "$S_REV" "${1:-$S_FRESH}" "${2:-r}" <<'PY'
import sys, json
p, orig, sess, expr = sys.argv[1:]
rows = [json.loads(l) for l in open(p).read().splitlines() if l.strip()]
base = next(r for r in rows if r.get("session") == orig and r.get("decision") == "launch" and r.get("role") == "review")
r = dict(base, session=sess, ts="2026-11-16T04:07:00-08:00", resume=False)
r = eval(expr, {"r": r, "dict": dict})
with open(p, "a") as fh:
    for x in (r if isinstance(r, list) else [r]):
        fh.write(json.dumps(x) + "\n")
PY
}
correction() { python3 - "$H" "$VERDICTS" "$S_REV" "$S_FRESH" "${1:-rows}" "${2:-1}" <<'PY'
import sys, json, hashlib, os
home, vf, orig, fresh, expr, n = sys.argv[1:]
raw = open(os.path.join(home, vf), "rb").read()
rows = [{"corrects": vf, "sha256": hashlib.sha256(raw).hexdigest(), "session": orig, "corrected_by": fresh},
        {"line": "alpha APPROVE fable", "slug": "rs-alpha", "verdict": "APPROVE"},
        {"line": "beta FIX fable", "slug": "rs-beta", "verdict": "FIX"}]
rows = eval(expr, {"rows": rows, "dict": dict, "json": json, "hashlib": hashlib})
out = rows if isinstance(rows, str) else "".join((x if isinstance(x, str) else json.dumps(x)) + "\n" for x in rows)
open(os.path.join(home, vf + ".verdicts.corrected-%s.jsonl" % n), "w").write(out)
PY
}
run() { JS=$(lint --json 2>"$T/err"); RC=$?; no_traceback "$(cat "$T/err")"; OUT=$(lint 2>&1); }
# ids: the JSON findings list
ids() { printf '%s' "$JS" | jget 'd["findings"]'; }
# want_ids '<JSON list>' <label>
want_ids() { [ "$(ids)" = "$1" ] || fail "$2: findings=$(ids) want $1: $OUT"; }
# not_read <label>: the correction is not read (the original's short-slug failures stand, no verdict_correction in JSON)
not_read() {
  findline review-scope-mismatch "$OUT" | grep >/dev/null -F 'slug alpha: PRD-alpha.md' || fail "$1: the original short-slug failure is gone: $OUT"
  [ "$(printf '%s' "$JS" | jget '"verdict_correction" in d["reviews"][0]')" = false ] || fail "$1: the correction was read: $JS"
}
