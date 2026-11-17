#!/usr/bin/env bash
# Known-bad on review binding (Terms "bound review", G5, G6.3, G6.7): KB6 J's row role
# author / role absent (legacy); KB16 J's session is the Route session / none
# (review-self); KB17 K and J one session on two Review lines; KB18 J's verdict file
# missing (review-file-missing); KB20 an author launch row carries J's session.
# Each: base == head bytes, exit 1, stale K/a.
set -uo pipefail
# shellcheck source=tests/drsp_lib.sh
. "$(dirname "${BASH_SOURCE[0]}")/drsp_lib.sh"
setup
if want KB6-author; then mut KB6-author; kb KB6-author review-provenance-missing; fi
if want KB6-absent; then mut KB6-absent; kb KB6-absent; fi
if want KB16-route; then mut KB16-route; kb KB16-route review-self; fi
if want KB16-none; then mut KB16-none; kb KB16-none review-self; fi
if want KB17; then mut KB17; kb KB17; fi
if want KB18; then mut KB18; kb KB18 review-file-missing; fi
if want KB20; then mut KB20; kb KB20; fi
pass "KB6 KB16 KB17 KB18 KB20"
