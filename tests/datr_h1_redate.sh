#!/usr/bin/env bash
# H1 (PRD-dream-analysis-trigger-record amendment): tests/fixtures/redate.py moves dates and regenerates derived values exactly.
# 1. The re-dated drfc, drmr and drmx fixtures, re-dated back to their 43d5b39 dates, are byte-identical to 43d5b39 (the drmr README's
#    H1 sentence aside), so the re-date changed dates and the values derived from them and nothing else.
# 2. Exactly the drfc and drmr manifests that verified at 43d5b39 (sha256sum -c in their own directory) verify now, renamed paths mapped.
# 3. The tool refuses, writing nothing: a NEW date the tree already holds, an OLD date it does not hold, and a short digest prefix of a
#    changed file it cannot regenerate; after review r10, also a symlinked directory (LOW-3), an --also file that holds the NEW date (LOW-5) or
#    names a ROOT file by another spelling (LOW-4), and a write that fails part way (LOW-4: nothing is replaced); after review r13, also a
#    manifest whose --also line stops verifying beside a deliberately stale line (LOW-2), a rename onto an existing path that is not a file
#    being rewritten (LOW-3) and a symlinked --also file (LOW-4). Each refusal exits 2 with its own text, changes no path and leaves no
#    temporary file.
# 4. A manifest with a deliberately stale line keeps each line's state (review r10 LOW-6: lines are checked one by one), and an --also file
#    named by a bare file name in the working directory is re-dated (review r13 LOW-1).
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
T="$(mktemp -d)"; trap 'chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"' EXIT
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

snap() {   # each path under the given files and directories: type, mode and link target, then each regular file's sha256
  local p
  for p in "$@"; do
    find "$p" -printf '%y %m %p -> %l\n' | LC_ALL=C sort
    find "$p" -type f -exec sha256sum {} + | LC_ALL=C sort
  done
}
refuses() {   # refuses NAME DIR TEXT PATH... -- ARG...: run in DIR, the tool exits 2 saying TEXT, no PATH changes, no temporary file is left
  local name="$1" dir="$2" text="$3" paths=() before after rc; shift 3
  while [ "$1" != "--" ]; do paths+=("$1"); shift; done; shift
  before="$(snap "${paths[@]}")"
  (cd "$dir" && "${R[@]}" "$@") > "$T/$name.out" 2>&1; rc=$?
  after="$(snap "${paths[@]}")"
  [ "$rc" = 2 ] || fail "$name: exited $rc, not 2 (refused): $(head -c 800 "$T/$name.out")"
  grep -qF -- "$text" "$T/$name.out" || fail "$name: the refusal does not say '$text': $(head -c 800 "$T/$name.out")"
  [ "$before" = "$after" ] || fail "$name: a refused re-date changed something: $(diff <(printf '%s\n' "$before") <(printf '%s\n' "$after") | head -6)"
  [ -z "$(find "$T" -name '.redate-*' -print -quit)" ] || fail "$name: a refused re-date left a temporary file: $(find "$T" -name '.redate-*' | head -3)"
  REFUSALS=$((REFUSALS + 1))
}
REFUSALS=0
M=(--map 2027-02-01=2026-11-18)
mkdir -p "$T/c1" "$T/c2" "$T/c3" "$T/c4/real" "$T/c5" "$T/c6/sub" "$T/c7/d" "$T/c8" "$T/c9" "$T/c10/x/2026-11-18.md" "$T/c11" "$T/c12/root"
printf 'at 2027-02-01T08:00 and 2026-11-18T08:00\n' > "$T/c1/a.md"
refuses c1 . "NEW date 2026-11-18 already occurs" "$T/c1" -- "${M[@]}" "$T/c1"
printf 'no date here\n' > "$T/c2/a.md"
refuses c2 . "OLD date 2027-02-01 occurs nowhere" "$T/c2" -- "${M[@]}" "$T/c2"
printf 'entry 2027-02-01T08:00\n' > "$T/c3/a.md"
printf 'short ref %s\n' "$(sha256sum "$T/c3/a.md" | cut -c1-12)" > "$T/c3/b.md"
refuses c3 . "a prefix of the replaced value" "$T/c3" -- "${M[@]}" "$T/c3"
printf 'entry 2027-02-01T08:00\n' > "$T/c4/real/a.md"; ln -s real "$T/c4/link"
refuses c4 . "$T/c4/link (a symlink)" "$T/c4" -- "${M[@]}" "$T/c4"
printf 'entry 2027-02-01T08:00\n' > "$T/c5/a.md"; printf 'already 2026-11-18\n' > "$T/c5.also"
refuses c5 . "already occurs in $T/c5.also" "$T/c5" "$T/c5.also" -- "${M[@]}" --also "$T/c5.also" "$T/c5"
printf 'entry 2027-02-01T08:00\n' > "$T/c6/sub/a.md"
refuses c6 "$T" "--also file $T/c6/sub/a.md is inside a ROOT" "$T/c6" -- "${M[@]}" --also "$T/c6/sub/a.md" c6
printf 'entry 2027-02-01T08:00\n' > "$T/c7/a.md"; printf 'entry 2027-02-01T09:00\n' > "$T/c7/d/b.md"; chmod 555 "$T/c7/d"
refuses c7 . "writing failed, nothing replaced" "$T/c7" -- "${M[@]}" "$T/c7"
chmod 755 "$T/c7/d"
# review r13 LOW-2: a stale line keeps 1f7b12a's whole-manifest check from looking at the manifest, whose --also line then stops verifying
printf 'plain\n' > "$T/c9/b.md"; printf 'also 2027-02-01T08:00\n' > "$T/c9.also"
{ printf '%064d  b.md\n' 0; sha256sum "$T/c9.also" | sed "s|  $T/|  ../|"; } > "$T/c9/m.sha256"
(cd "$T/c9" && sha256sum -c m.sha256 2>/dev/null) > "$T/c9.check"      # exits 1 for the stale line, so read its output, not its status
grep -qxF '../c9.also: OK' "$T/c9.check" || fail "c9: the --also line does not verify before the re-date: $(cat "$T/c9.check")"
refuses c9 . "manifest $T/c9/m.sha256 line 2 verified before the re-date and not after" "$T/c9" "$T/c9.also" -- "${M[@]}" --also "$T/c9.also" "$T/c9"
# review r13 LOW-3: a rename onto an existing path that is not a planned file (an empty directory named with the NEW date)
printf 'entry 2027-02-01T08:00\n' > "$T/c10/a.md"; printf 'moved\n' > "$T/c10/x/2027-02-01.md"
refuses c10 . "rename target $T/c10/x/2026-11-18.md already exists" "$T/c10" -- "${M[@]}" "$T/c10"
# review r13 LOW-4: a symlinked --also file (it would be replaced by a regular file, its target keeping the OLD date)
printf 'entry 2027-02-01T08:00\n' > "$T/c11/a.md"; printf 'also 2027-02-01T08:00\n' > "$T/c11.target"; ln -s c11.target "$T/c11.link"
refuses c11 . "--also file $T/c11.link is a symlink" "$T/c11" "$T/c11.link" "$T/c11.target" -- "${M[@]}" --also "$T/c11.link" "$T/c11"

printf 'entry 2027-02-01T08:00\n' > "$T/c8/a.md"; printf 'plain\n' > "$T/c8/b.md"
{ sha256sum "$T/c8/a.md" | sed "s|  $T/c8/|  |"; printf '%064d  b.md\n' 0; } > "$T/c8/m.sha256"
"${R[@]}" "${M[@]}" "$T/c8" > "$T/c8.out" 2>&1 || fail "a manifest with one stale line was refused: $(cat "$T/c8.out")"
(cd "$T/c8" && sha256sum -c m.sha256 2>/dev/null) > "$T/c8.check"
grep -q '^a.md: OK$' "$T/c8.check" && grep -q '^b.md: FAILED$' "$T/c8.check" || fail "per-line manifest state not kept: $(cat "$T/c8.check")"
# review r13 LOW-1: an --also file named by a bare file name in the working directory is re-dated, not refused
printf 'entry 2027-02-01T08:00\n' > "$T/c12/root/a.md"; printf 'also 2027-02-01T08:00\n' > "$T/c12/here.sh"
(cd "$T/c12" && "${R[@]}" "${M[@]}" --also here.sh root) > "$T/c12.out" 2>&1 || fail "an --also file in the working directory was refused: $(cat "$T/c12.out")"
grep -qx 'also 2026-11-18T08:00' "$T/c12/here.sh" && grep -qx 'entry 2026-11-18T08:00' "$T/c12/root/a.md" \
  || fail "c12: the working-directory --also file or the ROOT file was not re-dated: $(cat "$T/c12/here.sh" "$T/c12/root/a.md")"
[ -z "$(find "$T/c12" -name '.redate-*' -print -quit)" ] || fail "c12: a temporary file was left"
[ "$REFUSALS" = 10 ] || fail "ran $REFUSALS refusal cases, not 10"
echo "PASS $(basename "$0"): drfc, drmr and drmx re-dated back equal $OLD; $n manifests verify as at $OLD; $REFUSALS refusals write nothing; a partly stale manifest keeps each line's state; a working-directory --also file is re-dated"
