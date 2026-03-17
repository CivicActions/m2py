"""Tier 4b: Scheduling SDK test routines (6 routines, ~122 assertions).

Transpiles each Scheduling SDK test routine via m2py, executes it through
``EN^%ut``, and classifies the result.  All 6 pass on the osehravista baseline.

- **ZZUTSDIMO** (4 assertions): SDAMA203 IMO check
- **ZZUTPATAPPT** (7 assertions): SDAMA204 patient appointments
- **ZZUTNEXTAPPT** (32 assertions): SDAMA201 next appointment
- **ZZUTGETAPPT** (37 assertions): SDAMA201 get appointment
- **ZZUTGETPLIST** (37 assertions): SDAMA202 patient list
- **ZZUTSDAPI** (6 assertions): SDAMA301 scheduling API

Note: The 6 Group B regression routines (ZZRGUSD1–6) are excluded because
they ERROR on the osehravista baseline (require ``fakedoc1`` test user).

Dependencies are auto-loaded from VistA-M and VistA-VEHU-M via the
``MumpsAutoImporter`` and ``scheduling_library`` session fixture in conftest.py.
"""

from __future__ import annotations

import pytest

from .lib.adapter import transpile_and_execute
from .lib.helpers import assert_munit_pass, make_test_config, vista_testing_dir

_TESTING_DIR = vista_testing_dir("Scheduling")

# ---------------------------------------------------------------------------
# TestList routines  (from VistA/Packages/Scheduling/Testing/MUnit/TestList)
# ---------------------------------------------------------------------------

# SDK Tests — all pass on osehravista baseline
ROUTINES = [
    "ZZUTSDIMO",
    "ZZUTPATAPPT",
    "ZZUTNEXTAPPT",
    "ZZUTGETAPPT",
    "ZZUTGETPLIST",
    "ZZUTSDAPI",
]


@pytest.mark.slow
@pytest.mark.munit
@pytest.mark.usefixtures("scheduling_library")
class TestScheduling:
    """Run Scheduling test routines through the transpiled M-Unit framework."""

    @pytest.mark.parametrize("routine_name", ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one Scheduling SDK test routine."""
        config = make_test_config(
            routine_name,
            package_name="Scheduling",
            tier=4,
            testing_dir=_TESTING_DIR,
        )
        result = transpile_and_execute(config, munit_runtime)
        assert_munit_pass(result, routine_name)
