#!/usr/bin/env bash
# H1 (PRD-dream-analysis-trigger-record amendment): tests/fixtures/redate.py moves dates and regenerates derived values exactly.
# 1. The re-dated drfc, drmr and drmx fixtures, re-dated back to their 43d5b39 dates, are byte-identical to 43d5b39 (the drmr README's
#    H1 sentence aside), so the re-date changed dates and the values derived from them and nothing else.
# 2. Exactly the drfc and drmr manifests that verified at 43d5b39 (sha256sum -c in their own directory) verify now, renamed paths mapped.
# 3. The tool refuses, writing nothing: a NEW date the tree already holds, an OLD date it does not hold, and a short digest prefix of a
#    changed file it cannot regenerate; after review r10, also a symlinked directory (LOW-3), an --also file that holds the NEW date (LOW-5) or
#    names a ROOT file by another spelling (LOW-4), and a write that fails part way (LOW-4: nothing is replaced).
# 4. A manifest with a deliberately stale line keeps each line's state (review r10 LOW-6: lines are checked one by one).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
R=(python3 -I "$repo/tests/fixtures/redate.py")
OLD=43d5b39

mkdir -p "$T/old" "$T/new"
git -C "$repo" archive "$OLD" tests | tar -x -C "$T/old" || fail "cannot read $OLD from this checkout's history"
cp -r "$repo/tests" "$T/new/"
( cd "$T/new" && python3 -I - <<'PY'
p = "tests/fixtures/drmr/README.md"
s = open(p).read()
added = (", with one exception: PRD-dream-analysis-trigger-record's H1 amendment re-dated them from\n2027-01-04 to 2026-11-17 (before that PRD's cutover; "
         "times of day and order kept) with\n`tests/fixtures/redate.py`, which regenerated every digest, manifest and `scope_id` below.")
assert s.count(added) == 1, "drmr README: the H1 sentence is not there once"
open(p, "w").write(s.replace(added, "."))
PY
) || fail "drmr README does not carry the H1 sentence once"
( cd "$T/new" \
  && "${R[@]}" --map 2026-11-18=2027-02-01 --also tests/drfc_ac05_consumers.sh --also tests/drfc_lib.sh tests/fixtures/drfc \
  && "${R[@]}" --map 2026-11-17=2027-01-04 --also tests/drmr_lib.sh tests/fixtures/drmr \
  && "${R[@]}" --map 2026-11-18=2027-03-01 --also tests/fixtures/drmx/mfx.py --also tests/drmx_lib.sh --also tests/drmx_ac03_current.sh ) > "$T/back.out" 2>&1 \
  || fail "re-dating back to $OLD refused: $(cat "$T/back.out")"
for p in tests/fixtures/drfc tests/fixtures/drmr tests/fixtures/drmx tests/drfc_ac05_consumers.sh tests/drfc_lib.sh tests/drmr_lib.sh tests/drmx_lib.sh tests/drmx_ac03_current.sh; do
  diff -r -q "$T/old/$p" "$T/new/$p" > /dev/null || fail "$p re-dated back differs from $OLD: $(diff -r "$T/old/$p" "$T/new/$p" | head -5)"
done

verifying() {   # manifests under drfc/drmr of tree $1 that verify standalone (a variant's overlay manifest may need the base home)
  ( cd "$1" && find tests/fixtures/drfc tests/fixtures/drmr -name '*.sha256' -type f | sort | while IFS= read -r m; do
      ( cd "$(dirname "$m")" && sha256sum -c --quiet "$(basename "$m")" ) > /dev/null 2>&1 && printf '%s\n' "$m"; done )
}
verifying "$T/old" | python3 -I -c 'import re,sys; m={"2027-02-01":"2026-11-18","2027-01-04":"2026-11-17"}; [print(re.sub("|".join(m), lambda x: m[x.group(0)], l), end="") for l in sys.stdin]' > "$T/v.old"
verifying "$repo" > "$T/v.new"
n=$(wc -l < "$T/v.new")
[ "$n" -gt 0 ] || fail "no verifying manifest under drfc/drmr"
cmp -s "$T/v.old" "$T/v.new" || fail "manifests verifying at $OLD and now differ: $(diff "$T/v.old" "$T/v.new" | head -5)"

mkdir -p "$T/c1" "$T/c2" "$T/c3"
printf 'at 2027-02-01T08:00 and 2026-11-18T08:00\n' > "$T/c1/a.md"
"${R[@]}" --map 2027-02-01=2026-11-18 "$T/c1" > "$T/c1.out" 2>&1 && fail "a NEW date already in the tree was not refused"
grep -q "already occurs" "$T/c1.out" || fail "NEW-date refusal text: $(cat "$T/c1.out")"
printf 'no date here\n' > "$T/c2/a.md"
"${R[@]}" --map 2027-02-01=2026-11-18 "$T/c2" > "$T/c2.out" 2>&1 && fail "an absent OLD date was not refused"
grep -q "occurs nowhere" "$T/c2.out" || fail "absent-OLD refusal text: $(cat "$T/c2.out")"
printf 'entry 2027-02-01T08:00\n' > "$T/c3/a.md"
printf 'short ref %s\n' "$(sha256sum "$T/c3/a.md" | cut -c1-12)" > "$T/c3/b.md"
cp "$T/c3/a.md" "$T/c3.a.before"
"${R[@]}" --map 2027-02-01=2026-11-18 "$T/c3" > "$T/c3.out" 2>&1 && fail "a short digest prefix was not refused"
grep -q "a prefix of the replaced value" "$T/c3.out" || fail "short-prefix refusal text: $(cat "$T/c3.out")"
cmp -s "$T/c3/a.md" "$T/c3.a.before" || fail "a refused re-date wrote a file"
mkdir -p "$T/c4/real" "$T/c5" "$T/c6/sub" "$T/c7/d" "$T/c8"
printf 'entry 2027-02-01T08:00\n' > "$T/c4/real/a.md"; ln -s real "$T/c4/link"
"${R[@]}" --map 2027-02-01=2026-11-18 "$T/c4" > "$T/c4.out" 2>&1 && fail "a symlinked directory was not refused"
grep -q "a symlink" "$T/c4.out" || fail "symlink refusal text: $(cat "$T/c4.out")"
printf 'entry 2027-02-01T08:00\n' > "$T/c5/a.md"; printf 'already 2026-11-18\n' > "$T/c5.also"
"${R[@]}" --map 2027-02-01=2026-11-18 --also "$T/c5.also" "$T/c5" > "$T/c5.out" 2>&1 && fail "an --also file holding the NEW date was not refused"
grep -q "already occurs" "$T/c5.out" || fail "--also NEW-date refusal text: $(cat "$T/c5.out")"
printf 'entry 2027-02-01T08:00\n' > "$T/c6/sub/a.md"
(cd "$T" && "${R[@]}" --map 2027-02-01=2026-11-18 --also "$T/c6/sub/a.md" c6) > "$T/c6.out" 2>&1 && fail "an absolute --also spelling of a ROOT file was not refused"
grep -q "inside a ROOT" "$T/c6.out" || fail "--also inside-ROOT refusal text: $(cat "$T/c6.out")"
printf 'entry 2027-02-01T08:00\n' > "$T/c7/a.md"; printf 'entry 2027-02-01T09:00\n' > "$T/c7/d/b.md"
cp "$T/c7/a.md" "$T/c7.a.before"; cp "$T/c7/d/b.md" "$T/c7.b.before"; chmod 555 "$T/c7/d"
"${R[@]}" --map 2027-02-01=2026-11-18 "$T/c7" > "$T/c7.out" 2>&1; rc=$?; chmod 755 "$T/c7/d"
[ "$rc" = 2 ] || fail "a write that fails part way exited $rc, not 2: $(cat "$T/c7.out")"
grep -q "nothing replaced" "$T/c7.out" || fail "write-failure refusal text: $(cat "$T/c7.out")"
cmp -s "$T/c7/a.md" "$T/c7.a.before" && cmp -s "$T/c7/d/b.md" "$T/c7.b.before" || fail "a failed write changed a file"
[ -z "$(find "$T/c7" -name '.redate-*')" ] || fail "a failed write left a temporary file"
printf 'entry 2027-02-01T08:00\n' > "$T/c8/a.md"; printf 'plain\n' > "$T/c8/b.md"
{ sha256sum "$T/c8/a.md" | sed "s|  $T/c8/|  |"; printf '%064d  b.md\n' 0; } > "$T/c8/m.sha256"
"${R[@]}" --map 2027-02-01=2026-11-18 "$T/c8" > "$T/c8.out" 2>&1 || fail "a manifest with one stale line was refused: $(cat "$T/c8.out")"
(cd "$T/c8" && sha256sum -c m.sha256 2>/dev/null) > "$T/c8.check"
grep -q '^a.md: OK$' "$T/c8.check" && grep -q '^b.md: FAILED$' "$T/c8.check" || fail "per-line manifest state not kept: $(cat "$T/c8.check")"
echo "PASS $(basename "$0"): drfc, drmr and drmx re-dated back equal $OLD; $n manifests verify as at $OLD; seven refusals write nothing; a partly stale manifest keeps each line's state"
