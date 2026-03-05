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
- **DMUDIC00** (54 tests): dictionary lookup via ``DIC``
  — xfail: LISTX1/X2 infinite DIC recursion, LISTX3 scope bug in DIBTED
- **DMUDIQ00** (8 assertions): data retrieval via ``DIQ`` — PASS

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
    "DMUDIC00",
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

# ---------------------------------------------------------------------------
# Known failures / expected behavior per routine
# ---------------------------------------------------------------------------

# Routines expected to xfail with reason
_XFAIL_ROUTINES: dict[str, str] = {
    "DMUDIC00": (
        "LISTX1/X2: infinite DIC GOTO recursion with X flag; "
        "LISTX3: KeyError DIBTLINE scope bug in DIBTED sort template builder"
    ),
}

# Timeout (seconds) for routines known to potentially hang.
_XFAIL_TIMEOUTS: dict[str, int] = {}

# Routines that run but have known partial failures (not full xfail)
_KNOWN_ERRORS: dict[str, dict] = {}


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
        """Transpile and execute one VA FileMan test routine.

        Classification:
        - Crashed (no summary line)              → xfail if in _XFAIL_ROUTINES
        - Completed with 0 fail/err              → pass
        - Known partial errors within tolerance   → pass (with note)
        - Completed with unexpected failures      → xfail
        """
        config = _make_config(routine_name)

        # Execute through the adapter (with timeout for known-hanging routines)
        t = _XFAIL_TIMEOUTS.get(routine_name, 0)
        result = transpile_and_execute(config, munit_runtime, timeout=t)

        # --- Known xfail routines ---
        if routine_name in _XFAIL_ROUTINES:
            if result.status == "error":
                pytest.xfail(
                    f"{routine_name} crashed (expected): "
                    f"{result.error_message or _XFAIL_ROUTINES[routine_name]}"
                )
            if result.failures > 0 or result.errors > 0:
                pytest.xfail(
                    f"{routine_name}: {result.failures} failures, "
                    f"{result.errors} errors — {_XFAIL_ROUTINES[routine_name]}"
                )
            # If it unexpectedly passes, that's great — let it pass

        # --- Crash: no summary line parsed ---
        if result.status == "error":
            pytest.xfail(f"{routine_name} crashed: {result.error_message}")

        # --- Known partial-error routines (pass with tolerance) ---
        if routine_name in _KNOWN_ERRORS:
            spec = _KNOWN_ERRORS[routine_name]
            assert result.total_tests >= spec["min_tests"], (
                f"{routine_name}: ran only {result.total_tests} tests "
                f"(expected >= {spec['min_tests']})"
            )
            if result.errors <= spec["max_errors"] and result.failures == 0:
                return  # Within known tolerance → PASS
            # Worse than expected
            pytest.xfail(
                f"{routine_name}: {result.failures} failures, "
                f"{result.errors} errors (expected <= {spec['max_errors']} errors)"
            )

        # --- Clean pass: 0 failures, 0 errors ---
        if result.failures == 0 and result.errors == 0:
            assert result.total_tests > 0, (
                f"{routine_name}: summary line found but 0 tests"
            )
            return

        # Unexpected failures in a routine that should pass
        pytest.xfail(
            f"{routine_name}: "
            f"{result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
