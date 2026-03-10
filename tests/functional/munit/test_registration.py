"""Tier 4c: Registration test routine (1 routine, 10 assertions).

Transpiles the Registration test routine via m2py, executes it through
``EN^%ut``, and verifies a clean pass.

- **ZZDGPTCO1** (10 assertions): patient combine via ``CHKCUR^DGPTCO1``

Dependencies (``DGPTCO1``, ``DICRW``, ``DIE``) are auto-loaded from VistA-M
via the ``MumpsAutoImporter`` and ``registration_library`` session fixture in
conftest.py.  ZZDGPTCO1's STARTUP calls ``DT^DICRW`` to set today's date,
which triggers the ``ADDREC`` path in ``CHKCUR^DGPTCO1`` — this exercises
the full FileMan ``DIE`` / ``UPDATE^DIE`` edit chain.
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
        result = transpile_and_execute(config, munit_runtime)

        assert result.status != "error", (
            f"{routine_name} crashed: {result.error_message}"
        )
        assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"
        assert result.failures == 0 and result.errors == 0, (
            f"{routine_name}: {result.failures} failures, {result.errors} errors "
            f"(tests={result.total_tests})"
        )
