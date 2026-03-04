"""Tier 2: M XML Parser test routines (MXMLBLD, MXMLTMPT, MXMLPATT, MXMLDOMT).

Transpiles each M XML Parser test routine via m2py, executes it through
``EN^%ut``, and classifies the result.

Test routines and their status:

- **MXMLBLD** (13 assertions): XML Builder — fully passing
- **MXMLTMPT** (49 assertions): XML Templates — fully passing.
  Dependencies loaded from VistA-M (MXMLTMP1, MXMLTMPL,
  DDIOL, DICRW, DIALOG, etc.)
- **MXMLPATT** (25 tests): XML Path — fully passing.
  Dependencies loaded (MXMLPATH, %ZOSV, DIALOG globals).
- **MXMLDOMT** (8 tests): XML DOM Parser — fully passing.
  File I/O via ``%ZISH`` provided by a Python implementation
  (zish_impl.py) since ZISHGUX.m's ZEXCEPT scoping isn't yet supported.

Library routines are loaded from VistA-M via the
``mxml_library`` session fixture defined in conftest.py.
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

_TESTING_DIR = _VISTA_DIR / "Packages" / "M XML Parser" / "Testing" / "MUnit"

# ---------------------------------------------------------------------------
# TestList routines  (from VistA/Packages/M XML Parser/Testing/MUnit/TestList)
# ---------------------------------------------------------------------------

TIER2_ROUTINES = [
    "MXMLBLD",
    "MXMLTMPT",
    "MXMLPATT",
    "MXMLDOMT",
]

# Invocation patterns from the TestList file
_INVOCATIONS = {
    "MXMLBLD": "D TEST^MXMLBLD",
    "MXMLTMPT": "D TEST^MXMLTMPT",
    "MXMLPATT": "D TEST^MXMLPATT",
    "MXMLDOMT": "D ^MXMLDOMT",
}


def _make_config(routine_name: str) -> TestRoutineConfig:
    """Build a TestRoutineConfig for a Tier 2 routine."""
    return TestRoutineConfig(
        routine_name=routine_name,
        package_name="M XML Parser",
        invocation=_INVOCATIONS[routine_name],
        source_path=str(_TESTING_DIR / f"{routine_name}.m"),
        tier=2,
    )


@pytest.fixture(scope="module")
def _ensure_library(mxml_library):
    """Module-level guard that M XML Parser library routines are loaded."""
    return mxml_library


@pytest.mark.slow
@pytest.mark.munit
class TestMXMLParser:
    """Run M XML Parser test routines through the transpiled M-Unit framework."""

    @pytest.fixture(autouse=True)
    def _library(self, _ensure_library):
        """Auto-use the library fixture for every test in the class."""

    @pytest.mark.parametrize("routine_name", TIER2_ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one M XML Parser test routine.

        All four routines (MXMLBLD, MXMLTMPT, MXMLPATT, MXMLDOMT)
        are expected to pass cleanly.  Crashes or failures are real
        test failures.
        """
        config = _make_config(routine_name)

        # Execute through the adapter
        result = transpile_and_execute(config, munit_runtime)

        # --- Crash: no summary line parsed ---
        assert result.status != "error", (
            f"{routine_name} crashed: {result.error_message}\n"
            f"--- raw output ---\n{result.raw_output}"
        )

        # --- Must have run some tests ---
        assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"

        # --- Must have 0 failures and 0 errors ---
        assert result.failures == 0 and result.errors == 0, (
            f"{routine_name}: "
            f"{result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})\n"
            f"--- raw output ---\n{result.raw_output}"
        )
