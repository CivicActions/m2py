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

_TESTING_DIR = _VISTA_DIR / "Packages" / "Scheduling" / "Testing" / "MUnit"

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

# Invocation patterns from the TestList file (all use `D ^ROUTINE`)
_INVOCATIONS = {r: f"D ^{r}" for r in ROUTINES}


def _make_config(routine_name: str) -> TestRoutineConfig:
    """Build a TestRoutineConfig for a Tier 4b routine."""
    return TestRoutineConfig(
        routine_name=routine_name,
        package_name="Scheduling",
        invocation=_INVOCATIONS[routine_name],
        source_path=str(_TESTING_DIR / f"{routine_name}.m"),
        tier=4,
    )


@pytest.fixture(scope="module")
def _ensure_library(scheduling_library):
    """Module-level guard that Scheduling library routines are loaded."""
    return scheduling_library


@pytest.mark.slow
@pytest.mark.munit
class TestScheduling:
    """Run Scheduling test routines through the transpiled M-Unit framework."""

    @pytest.fixture(autouse=True)
    def _library(self, _ensure_library):
        """Auto-use the library fixture for every test in the class."""

    @pytest.mark.parametrize("routine_name", ROUTINES)
    def test_munit_routine(
        self,
        routine_name: str,
        munit_runtime,
        munit_baseline,
    ):
        """Transpile and execute one Scheduling SDK test routine."""
        config = _make_config(routine_name)
        result = transpile_and_execute(config, munit_runtime)

        assert result.status != "error", (
            f"{routine_name} crashed: {result.error_message}"
        )
        assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"
        assert result.failures == 0 and result.errors == 0, (
            f"{routine_name}: {result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
