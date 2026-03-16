"""Shared helpers for M-Unit test modules.

Provides:
- ``make_test_config()`` — Build a ``TestRoutineConfig`` from common parameters.
- ``assert_munit_pass()`` — Assert a routine completed with 0 failures/errors.
- ``vista_testing_dir()`` — Resolve the VistA MUnit testing directory for a package.
"""

from __future__ import annotations

import os
from pathlib import Path

from .models import MUnitResult, TestRoutineConfig

_REPO_ROOT = Path(__file__).resolve().parents[4]
_VISTA_DEPS = Path(os.environ.get("VISTA_DEPS_DIR", str(_REPO_ROOT / ".vista-deps")))
_VISTA_DIR = Path(os.environ.get("VISTA_DIR", str(_VISTA_DEPS / "VistA")))


def vista_testing_dir(package_name: str) -> Path:
    """Return the MUnit testing directory for a VistA package."""
    return _VISTA_DIR / "Packages" / package_name / "Testing" / "MUnit"


def make_test_config(
    routine_name: str,
    *,
    package_name: str,
    tier: int,
    testing_dir: Path,
    invocation: str | None = None,
) -> TestRoutineConfig:
    """Build a ``TestRoutineConfig`` for a VistA test routine.

    If *invocation* is not given, defaults to ``D ^<routine_name>``.
    """
    return TestRoutineConfig(
        routine_name=routine_name,
        package_name=package_name,
        invocation=invocation or f"D ^{routine_name}",
        source_path=str(testing_dir / f"{routine_name}.m"),
        tier=tier,
    )


def assert_munit_pass(result: MUnitResult, routine_name: str) -> None:
    """Assert that a routine completed with >0 tests and 0 failures/errors."""
    assert result.status != "error", f"{routine_name} crashed: {result.error_message}"
    assert result.total_tests > 0, f"{routine_name}: summary line found but 0 tests"
    assert result.failures == 0 and result.errors == 0, (
        f"{routine_name}: {result.failures} failures, {result.errors} errors "
        f"(tests={result.total_tests})\n"
        f"Raw output:\n{result.raw_output}"
    )
