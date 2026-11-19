#!/usr/bin/env bash
# PRD-dream-finding-consumption AC 1 (R5, R8): the A1724 WWHTBT page (a falsifier and eight SPEC mechanisms) with records binding 0 to 9 of its
# findings, checked by `--consumption`: every partial record exits 1 with consumption-finding-unbound naming exactly the unbound findings
# (`2026-11-18-mission-analysis-consistency-wwhtbt.md#mechanism:5` and the like); the full record exits 0; an edited page gives
# consumption-page-stale; a page without its `# Mechanisms` heading gives consumption-page-unparsed. Bindings are `test` rows on a scratch git repo
# whose blob names each finding.
set -uo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; repo="$(dirname "$here")"
LINT="$repo/skills/dream/scripts/dream-run-note-lint.sh"
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
fail() { echo "FAIL $(basename "$0"): $*"; exit 1; }
python3 -I - "$LINT" "$repo/tests/fixtures/dfcn/2026-11-18-mission-analysis-consistency-wwhtbt.md" "$T" <<'PY' || exit 1
import hashlib, json, os, subprocess, sys
lint, page_src, T = sys.argv[1:4]
NAME = "2026-11-18-mission-analysis-consistency-wwhtbt.md"
home = os.path.join(T, "home"); os.makedirs(os.path.join(home, "notes", "analysis"))
page = os.path.join("notes", "analysis", NAME)
data = open(page_src, "rb").read()
open(os.path.join(home, page), "wb").write(data)
FIND = ["falsifier"] + ["mechanism:%d" % n for n in range(1, 9)]
gr = os.path.join(T, "repo"); os.makedirs(os.path.join(gr, "tests"))
open(os.path.join(gr, "tests", "bind.sh"), "w").write("# exercises %s#%s\n" % (NAME, ",".join(FIND)))
env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "-m", "fixture"]):
    subprocess.run(["git", "-C", gr] + c, check=True, env=env, capture_output=True)
head = subprocess.run(["git", "-C", gr, "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()

def record(k, sha):
    rp = os.path.join(T, "rec-%d.jsonl" % k)
    with open(rp, "w") as f:
        for i, fd in enumerate(FIND[:k]):
            f.write(json.dumps({"id": "c%d" % i, "page": page, "page_sha256": sha, "finding": fd, "binding": "test", "author_session": "a-1",
                                "repo": gr, "commit": head, "path": "tests/bind.sh"}) + "\n")
    return rp

def check(rp):
    p = subprocess.run(["bash", lint, "--consumption", rp, "--task", "A1", "--page", page, "--prd-home", home, "--json"], capture_output=True, text=True)
    try:
        d = json.loads(p.stdout.strip().splitlines()[-1]) if p.stdout.strip() else {}
    except ValueError:
        d = {}
    return p.returncode, d, p.stderr

def die(msg):
    print("FAIL dfcn_ac01_coverage.sh: " + msg); sys.exit(1)

sha = hashlib.sha256(data).hexdigest()
for k in range(0, 10):
    rc, d, err = check(record(k, sha))
    want = sorted(NAME + "#" + f for f in FIND[k:])
    if k < 9:
        if rc != 1 or d.get("findings") != ["consumption-finding-unbound"] or d.get("unconsumed") != want:
            die("record binding %d of 9: rc %s findings %s unconsumed %s (want 1, [consumption-finding-unbound], %s)\n%s" % (k, rc, d.get("findings"), d.get("unconsumed"), want, err))
        named = sorted(l[len("FAIL consumption-finding-unbound: "):].split(": no binding row")[0]
                       for l in err.splitlines() if l.startswith("FAIL consumption-finding-unbound: "))
        if named != want:
            die("record binding %d of 9 names %s, not exactly the unbound %s" % (k, named, want))
    elif rc != 0 or d.get("unconsumed") != []:
        die("the full record: rc %s unconsumed %s\n%s" % (rc, d.get("unconsumed"), err))
open(os.path.join(home, page), "ab").write(b"\nedited\n")
rc, d, err = check(record(9, sha))
if rc != 1 or "consumption-page-stale" not in (d.get("findings") or []) or d.get("unconsumed") != []:
    die("an edited page: rc %s findings %s (want consumption-page-stale)\n%s" % (rc, d.get("findings"), err))
bare = data.replace(b"\n# Mechanisms\n", b"\n# Mechanism list\n")
assert bare != data
open(os.path.join(home, page), "wb").write(bare)
rc, d, err = check(record(9, hashlib.sha256(bare).hexdigest()))
if rc != 1 or d.get("findings") != ["consumption-page-unparsed"]:
    die("a page without its # Mechanisms heading: rc %s findings %s (want consumption-page-unparsed)\n%s" % (rc, d.get("findings"), err))
print("PASS dfcn_ac01_coverage.sh: records binding 0-8 of 9 findings name exactly the unbound ones; the full record exits 0; edited page stale; sectionless page unparsed")
PY
