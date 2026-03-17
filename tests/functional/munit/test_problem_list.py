"""Tier 5: Problem List test routine (ZZRGUTEX).

Transpiles the ZZRGUTEX test routine via m2py, executes it through
``EN^%ut``, and validates the result against the osehravista baseline
(28 tests, 0 failures, 0 errors).

ZZRGUTEX exercises the Problem List API (``GMPLUTL``), Clinical Case
Registries (``RORHL17``), PCE Patient Care Encounter (``PXCAPL``,
``PXCAPOV``), Clinical Reminders (``PXRMISE``, ``PXRMPROB``), Quasar
(``ACKQUTL6``), and AICS (``IBDFBK3``) through 8 entry points:

- **PROBNAR** — create problem → verify narrative via IBDFBK3
- **PROBDIA** — verify diagnosis code lookup
- **RORLO** — Clinical Case Registries HL7 output
- **NEPROB** — new problem count (PXRMISE)
- **PXRMOUT** — Clinical Reminders output formatting
- **PXRMPRB** — PCE problem activity (PXCAPL)
- **PXDIAG** — PCE diagnosis activity (PXCAPOV)
- **ACKQLST** — Quasar problem list query

The 7 error routines (ZZRGUT, ZZRGUT1–5, ZZRGUTRB) are correctly excluded
— they require a fully configured VistA environment and are not transpilable.

Dependencies are auto-loaded via the ``MumpsAutoImporter`` and the
``problem_list_library`` session fixture in conftest.py.
"""

from __future__ import annotations

import pytest

from .lib.adapter import transpile_and_execute
from .lib.helpers import assert_munit_pass, make_test_config, vista_testing_dir

_TESTING_DIR = vista_testing_dir("Problem List")

# ---------------------------------------------------------------------------
# Routines
# ---------------------------------------------------------------------------

ROUTINES = ["ZZRGUTEX"]


@pytest.mark.slow
@pytest.mark.munit
@pytest.mark.usefixtures("problem_list_library")
class TestProblemList:
    """Run Problem List test routines through the transpiled M-Unit framework."""

    @pytest.mark.parametrize("routine_name", ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        config = make_test_config(
            routine_name,
            package_name="Problem List",
            tier=5,
            testing_dir=_TESTING_DIR,
        )
        result = transpile_and_execute(config, munit_runtime)
        assert_munit_pass(result, routine_name)
