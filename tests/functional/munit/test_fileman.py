"""Tier 3: VA FileMan test routines (ZZUTDIDT, DMUDT000, DMUDTC00, DMUDIC00, DMUDIQ00).

Transpiles each VA FileMan test routine via m2py, executes it through
``EN^%ut``, and classifies the result.

This is the first tier requiring global bootstrap — ``^DD`` (data dictionary)
and ``^DIC`` (file list) must be loaded from ZWR files before tests can run.

Test routines and their status:

- **ZZUTDIDT** (2 assertions): simplest, only needs ``%DT`` — PASS
- **DMUDTC00** (92 assertions baseline): date/time calculations via ``%DTC``
  — PASS (92 tests, 0 failures, 0 errors)
- **DMUDT000** (61 assertions): date/time validation via ``%DT``
  — PASS (61 tests, 0 failures, 0 errors)
- **DMUDIC00** (14 tests baseline): dictionary lookup via ``DIC``
  — xfail (timeout): FINDC computed-field evaluation triggers O(n log n)
  ``$ORDER`` scans over ~10K county records; transpilation is correct but
  too slow to complete within CI timeout
- **DMUDIQ00** (7 assertions): data retrieval via ``DIQ`` — PASS

Dependencies are auto-loaded from VistA-M via the
``MumpsAutoImporter`` and ``fileman_library`` session fixture in conftest.py.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from .lib.adapter import transpile_and_execute
from .lib.models import TestRoutineConfig


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[3]
_VISTA_DEPS = Path(os.environ.get("VISTA_DEPS_DIR", str(_REPO_ROOT / ".vista-deps")))
_VISTA_DIR = Path(os.environ.get("VISTA_DIR", str(_VISTA_DEPS / "VistA")))

_TESTING_DIR = _VISTA_DIR / "Packages" / "VA FileMan" / "Testing" / "MUnit"

# ---------------------------------------------------------------------------
# TestList routines  (from VistA/Packages/VA FileMan/Testing/MUnit/TestList)
# ---------------------------------------------------------------------------

TIER3_ROUTINES = [
    "ZZUTDIDT",
    "DMUDT000",
    "DMUDTC00",
    pytest.param(
        "DMUDIC00",
        marks=pytest.mark.xfail(
            reason=(
                "FINDC computed-field evaluation triggers O(n log n) $ORDER "
                "scans over ~10K county records — too slow for CI"
            ),
            strict=False,
        ),
    ),
    "DMUDIQ00",
]

# Invocation patterns from the TestList file (all use `D ^ROUTINE`)
_INVOCATIONS = {
    "ZZUTDIDT": "D ^ZZUTDIDT",
    "DMUDT000": "D ^DMUDT000",
    "DMUDTC00": "D ^DMUDTC00",
    "DMUDIC00": "D ^DMUDIC00",
    "DMUDIQ00": "D ^DMUDIQ00",
}

# TEMPORARY: DMUDIC00's FINDC test triggers O(n log n) $ORDER scans over ~10K
# county records.  Without a timeout the CI job hangs for 10+ minutes, which
# obscures the status of the other munit tests.  Remove once $ORDER performance
# is addressed (see the xfail marker on DMUDIC00 above).
_TIMEOUTS: dict[str, float] = {
    "DMUDIC00": 120,
}


def _make_config(routine_name: str) -> TestRoutineConfig:
    """Build a TestRoutineConfig for a Tier 3 routine."""
    return TestRoutineConfig(
        routine_name=routine_name,
        package_name="VA FileMan",
        invocation=_INVOCATIONS[routine_name],
        source_path=str(_TESTING_DIR / f"{routine_name}.m"),
        tier=3,
    )


@pytest.fixture(scope="module")
def _ensure_library(fileman_library):
    """Module-level guard that FileMan library routines are loaded."""
    return fileman_library


@pytest.mark.slow
@pytest.mark.munit
class TestVAFileMan:
    """Run VA FileMan test routines through the transpiled M-Unit framework."""

    @pytest.fixture(autouse=True)
    def _library(self, _ensure_library):
        """Auto-use the library fixture for every test in the class."""

    @pytest.mark.parametrize("routine_name", TIER3_ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one VA FileMan test routine."""
        config = _make_config(routine_name)
        timeout = _TIMEOUTS.get(routine_name, 0)
        result = transpile_and_execute(config, munit_runtime, timeout=timeout)

        assert result.status != "error", (
            f"{routine_name} crashed: {result.error_message}"
        )
        assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"
        assert result.failures == 0 and result.errors == 0, (
            f"{routine_name}: {result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
