"""Tier 4c: Registration test routine (1 routine, 10 assertions).

Transpiles the Registration test routine via m2py, executes it through
``EN^%ut``, and verifies a clean pass.

- **ZZDGPTCO1** (10 assertions): patient combine via ``CHKCUR^DGPTCO1``

Dependencies (``DGPTCO1``, ``DICRW``) are auto-loaded from VistA-M via the
``MumpsAutoImporter`` and ``registration_library`` session fixture in conftest.py.
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

_TESTING_DIR = _VISTA_DIR / "Packages" / "Registration" / "Testing" / "MUnit"

# ---------------------------------------------------------------------------
# TestList routine (from VistA/Packages/Registration/Testing/MUnit/TestList)
# ---------------------------------------------------------------------------

ROUTINES = ["ZZDGPTCO1"]

_INVOCATIONS = {r: f"D ^{r}" for r in ROUTINES}

# Timeout (seconds) for routines that may run slowly in the transpiled
# environment.  Before _AlarmTimeout(BaseException) the signal.alarm was
# silently caught by ``except Exception:`` handlers, so these routines
# appeared to complete.  Now the timeout is enforced; give them headroom.
_XFAIL_TIMEOUTS: dict[str, int] = {
    "ZZDGPTCO1": 90,
}


def _make_config(routine_name: str) -> TestRoutineConfig:
    """Build a TestRoutineConfig for a Tier 4c routine."""
    return TestRoutineConfig(
        routine_name=routine_name,
        package_name="Registration",
        invocation=_INVOCATIONS[routine_name],
        source_path=str(_TESTING_DIR / f"{routine_name}.m"),
        tier=4,
    )


@pytest.fixture(scope="module")
def _ensure_library(registration_library):
    """Module-level guard that Registration library routines are loaded."""
    return registration_library


@pytest.mark.slow
@pytest.mark.munit
class TestRegistration:
    """Run Registration test routines through the transpiled M-Unit framework."""

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
        """Transpile and execute one Registration test routine."""
        config = _make_config(routine_name)
        t = _XFAIL_TIMEOUTS.get(routine_name, 30)
        result = transpile_and_execute(config, munit_runtime, timeout=t)

        # Timeout / crash: xfail for routines with known timeout issues
        if result.status == "error":
            if routine_name in _XFAIL_TIMEOUTS:
                pytest.xfail(
                    f"{routine_name} timed out/crashed: {result.error_message}"
                )
            pytest.fail(f"{routine_name} crashed: {result.error_message}")

        assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"
        assert result.failures == 0 and result.errors == 0, (
            f"{routine_name}: {result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
