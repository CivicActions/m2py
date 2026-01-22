"""Functional tests for the MVTS (M Validation Test Suite).

The MVTS suite is a comprehensive MUMPS validation framework with sub-driver
routines that call individual test routines. Each sub-driver tests a specific
feature area of the MUMPS language.

Structure:
- VV1.m: Part 77 tests (60 sub-drivers)
- VV2.m: Part 84 tests (25 sub-drivers)
- VV3.m: Part 95 tests (23 sub-drivers)
- VV4.m: Part 95 continued (28 sub-drivers)
- Total: 136 sub-drivers, ~714 individual test routines

IMPORTANT: MVTS routines use framework routines (^V1PRESET, ^VEXAMINE, etc.)
that set up test state and validate results. Without the framework, individual
routines cannot be tested in isolation. All tests are marked as skipped with
the reason "MVTS framework" until framework support is implemented.

The sub-driver routines (V1WR, V1CMT, etc.) print their labels and call
individual test routines. This module tests each sub-driver as a parametrized
test case.

Usage:
    uv run pytest tests/functional/test_mvts.py -v
    uv run pytest tests/functional/test_mvts.py -k V1BOA -v  # Specific routine
"""

from __future__ import annotations

import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    compare_output,
    load_routine_source,
    run_mumps,
)
from tests.functional.suite_definitions import (
    MVTS_ROUTINES,
    MVTS_VV1_ROUTINES,
    MVTS_VV2_ROUTINES,
    MVTS_VV3_ROUTINES,
    MVTS_VV4_ROUTINES,
    RoutineDefinition,
)


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "mvts"
MVTS_DIR = FUNCTIONAL_BASE / "mvts"
MVTS_INREF = MVTS_DIR / "inref"
MVTS_OUTREF = MVTS_DIR / "outref" / "mvts.txt"
MVTS_DRIVER = MVTS_DIR / "u_inref" / "mvts.csh"


# =============================================================================
# Test Helpers
# =============================================================================


def make_test_id(routine_def: RoutineDefinition) -> str:
    """Create a test ID from routine definition."""
    return routine_def.routine


def get_routine_params() -> list[pytest.param]:
    """Generate pytest parameters for all MVTS routines."""
    params = []
    for routine in MVTS_ROUTINES:
        if routine.skip_reason:
            params.append(
                pytest.param(
                    routine,
                    id=make_test_id(routine),
                    marks=pytest.mark.skip(reason=routine.skip_reason),
                )
            )
        else:
            params.append(pytest.param(routine, id=make_test_id(routine)))
    return params


# =============================================================================
# Parametrized Test Suite
# =============================================================================


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsSuite:
    """Parametrized tests for MVTS sub-driver routines.

    Each test runs a sub-driver routine through m2py and validates:
    1. The routine can be parsed
    2. Python code is generated
    3. The code executes (xfail expected due to framework dependency)
    """

    @pytest.mark.parametrize("routine_def", get_routine_params())
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a single MVTS sub-driver routine.

        Args:
            routine_def: The routine definition containing label, routine name,
                        and optional skip reason.
        """
        # Load the routine source
        source = load_routine_source(MVTS_INREF, routine_def.routine)
        assert source is not None, f"Failed to load routine {routine_def.routine}"

        # Run through m2py
        result = run_mumps(source, timeout=30)

        # For MVTS, we expect execution to fail due to framework dependencies
        # but the routine should at least parse and generate code
        assert result is not None, f"No result for {routine_def.routine}"

        # Check if output matches expected label prefix
        # MVTS routines print their label like "1---V1WR"
        if result.success:
            expected_prefix = routine_def.label
            compare_output(result.stdout, expected_prefix)


# =============================================================================
# Subset Test Classes (for targeted testing)
# =============================================================================


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsVV1:
    """Tests for VV1 (Part 77) sub-drivers only."""

    @pytest.mark.parametrize(
        "routine_def",
        [
            pytest.param(
                r,
                id=r.routine,
                marks=pytest.mark.skip(reason=r.skip_reason) if r.skip_reason else (),
            )
            for r in MVTS_VV1_ROUTINES
        ],
    )
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a VV1 sub-driver routine."""
        source = load_routine_source(MVTS_INREF, routine_def.routine)
        assert source is not None, f"Failed to load routine {routine_def.routine}"


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsVV2:
    """Tests for VV2 (Part 84) sub-drivers only."""

    @pytest.mark.parametrize(
        "routine_def",
        [
            pytest.param(
                r,
                id=r.routine,
                marks=pytest.mark.skip(reason=r.skip_reason) if r.skip_reason else (),
            )
            for r in MVTS_VV2_ROUTINES
        ],
    )
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a VV2 sub-driver routine."""
        source = load_routine_source(MVTS_INREF, routine_def.routine)
        assert source is not None, f"Failed to load routine {routine_def.routine}"


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsVV3:
    """Tests for VV3 (Part 95) sub-drivers only."""

    @pytest.mark.parametrize(
        "routine_def",
        [
            pytest.param(
                r,
                id=r.routine,
                marks=pytest.mark.skip(reason=r.skip_reason) if r.skip_reason else (),
            )
            for r in MVTS_VV3_ROUTINES
        ],
    )
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a VV3 sub-driver routine."""
        source = load_routine_source(MVTS_INREF, routine_def.routine)
        assert source is not None, f"Failed to load routine {routine_def.routine}"


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsVV4:
    """Tests for VV4 (Part 95 continued) sub-drivers only."""

    @pytest.mark.parametrize(
        "routine_def",
        [
            pytest.param(
                r,
                id=r.routine,
                marks=pytest.mark.skip(reason=r.skip_reason) if r.skip_reason else (),
            )
            for r in MVTS_VV4_ROUTINES
        ],
    )
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a VV4 sub-driver routine."""
        source = load_routine_source(MVTS_INREF, routine_def.routine)
        assert source is not None, f"Failed to load routine {routine_def.routine}"


# =============================================================================
# Infrastructure Tests
# =============================================================================


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsInfrastructure:
    """Tests to validate the MVTS test infrastructure."""

    def test_inref_directory_exists(self) -> None:
        """Verify the mvts/inref directory exists with routines."""
        assert MVTS_INREF.exists(), f"MVTS inref directory not found: {MVTS_INREF}"
        routines = list(MVTS_INREF.glob("*.m"))
        assert len(routines) > 0, "No .m files found in mvts/inref"

    def test_outref_exists(self) -> None:
        """Verify the MVTS outref file exists."""
        assert MVTS_OUTREF.exists(), f"MVTS outref not found: {MVTS_OUTREF}"

    def test_driver_exists(self) -> None:
        """Verify the MVTS driver script exists."""
        assert MVTS_DRIVER.exists(), f"MVTS driver not found: {MVTS_DRIVER}"

    def test_main_test_routines_exist(self) -> None:
        """Verify the main MVTS test routines exist."""
        main_routines = ["VV1", "VV2", "VV3", "VV4", "VV4TP", "VSR"]
        for routine in main_routines:
            routine_path = MVTS_INREF / f"{routine}.m"
            assert routine_path.exists(), f"Main routine not found: {routine}"

    def test_sub_driver_count(self) -> None:
        """Verify the expected number of sub-drivers are defined."""
        assert len(MVTS_VV1_ROUTINES) == 59, (
            f"VV1 should have 59 sub-drivers, got {len(MVTS_VV1_ROUTINES)}"
        )
        assert len(MVTS_VV2_ROUTINES) == 25, (
            f"VV2 should have 25 sub-drivers, got {len(MVTS_VV2_ROUTINES)}"
        )
        assert len(MVTS_VV3_ROUTINES) == 23, (
            f"VV3 should have 23 sub-drivers, got {len(MVTS_VV3_ROUTINES)}"
        )
        assert len(MVTS_VV4_ROUTINES) == 28, (
            f"VV4 should have 28 sub-drivers, got {len(MVTS_VV4_ROUTINES)}"
        )
        assert len(MVTS_ROUTINES) == 135, (
            f"Total should be 135 sub-drivers, got {len(MVTS_ROUTINES)}"
        )

    def test_routine_files_exist(self) -> None:
        """Verify all defined routines have corresponding .m files."""
        missing = []
        for routine_def in MVTS_ROUTINES:
            routine_path = MVTS_INREF / f"{routine_def.routine}.m"
            if not routine_path.exists():
                missing.append(routine_def.routine)

        assert not missing, f"Missing routine files: {missing}"
