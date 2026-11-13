"""Shared test helpers. Source-only: fixtures are synthetic or derived, never live state."""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
SKILL = HERE.parent
sys.path.insert(0, str(SKILL / "scripts"))
FIX = HERE / "fixtures"


def load(name):
    return json.loads((FIX / (name + ".json")).read_text())


def codes(findings):
    return {f["code"] for f in findings}
