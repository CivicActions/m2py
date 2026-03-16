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
  — PASS (14 tests, 0 failures, 0 errors with DIC.py override)
- **DMUDIQ00** (7 assertions): data retrieval via ``DIQ`` — PASS

Dependencies are auto-loaded from VistA-M via the
``MumpsAutoImporter`` and ``fileman_library`` session fixture in conftest.py.
"""

from __future__ import annotations

import pytest

from .lib.adapter import transpile_and_execute
from .lib.helpers import assert_munit_pass, make_test_config, vista_testing_dir

_TESTING_DIR = vista_testing_dir("VA FileMan")

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


@pytest.mark.slow
@pytest.mark.munit
@pytest.mark.usefixtures("fileman_library")
class TestVAFileMan:
    """Run VA FileMan test routines through the transpiled M-Unit framework."""

    @pytest.mark.parametrize("routine_name", TIER3_ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one VA FileMan test routine."""
        config = make_test_config(
            routine_name,
            package_name="VA FileMan",
            tier=3,
            testing_dir=_TESTING_DIR,
        )
        result = transpile_and_execute(config, munit_runtime)
        assert_munit_pass(result, routine_name)
