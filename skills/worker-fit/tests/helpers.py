"""Shared test helpers. Source-only: fixtures are synthetic or derived, never live state."""
import json
import pathlib
import sys
from unittest import mock

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))
FIX = HERE / "fixtures"


def load(name):
    return json.loads((FIX / (name + ".json")).read_text())


def codes(findings):
    return {f["code"] for f in findings}


# Test clock injection: fixture dates are fixed (2026-11-13T06:xx), so tests that rely on them run against this
# injected clock via the module-level clock function envelope_validate.host_now. The live default stays the host clock.
FIXTURE_NOW = "2026-11-13T07:00:00Z"
_patcher = None


def install_fixture_clock():
    global _patcher
    import envelope_validate as ev
    _patcher = mock.patch.object(ev, "host_now", lambda: ev.as_now(FIXTURE_NOW))
    _patcher.start()


def remove_fixture_clock():
    _patcher.stop()
