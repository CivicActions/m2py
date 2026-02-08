"""Functional tests for the merge YottaDB test suite.

The merge suite tests the MERGE command with various combinations of:
- Global to global (gbl2gbl)
- Global to local (gbl2lcl)
- Local to global (lcl2gbl)
- Local to local (lcl2lcl)
- Collation handling (gblcol, lclcol)
- Error conditions (errors)
- Transaction processing (tp_simple, tp_stress)
- Null subscripts (nullsubs)
- Unicode support (ugbl2gbl, etc.)
- Indirection (indirection)
- ZSHOW integration (zshowgbl, zshowlcl)

Structure:
- 23 driver scripts in u_inref/
- 25 outref files (each sub-test has its own output)
- 54 routines in inref/

Unlike mugj/basic, merge uses separate drivers and outrefs for each sub-test.
The outrefs contain significant YDB infrastructure output (database creation,
replication setup, etc.) that must be filtered when comparing output.

Usage:
    uv run pytest tests/functional/test_merge.py -v
    uv run pytest tests/functional/test_merge.py -k gbl2gbl -v  # Specific subtest
"""

from __future__ import annotations


import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    compare_output,
    load_routine_source,
    normalize_outref,
    run_mumps,
)
from tests.functional.suite_definitions import (
    MERGE_ROUTINES,
    MERGE_SUBTESTS,
    RoutineDefinition,
)


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "merge"
MERGE_DIR = FUNCTIONAL_BASE / "merge"
MERGE_INREF = MERGE_DIR / "inref"
MERGE_OUTREF = MERGE_DIR / "outref"
MERGE_UINREF = MERGE_DIR / "u_inref"
# Extracted routines (from CSH heredocs/input files, not in original YDB inref)
MERGE_EXTRACTED = FUNCTIONAL_BASE / "merge-routines"


# =============================================================================
# Merge-Specific Helper Loading
# =============================================================================

# Routines that need the lfill helper for database filling operations
_LFILL_DEPENDENT_ROUTINES = frozenset({"mergelv", "misclv"})

# Cache for merge helpers
_MERGE_HELPERS: dict[str, str] | None = None


def _load_merge_helpers() -> dict[str, str]:
    """Load merge-specific helper routines from inref/.

    The lfill.m helper is used by mergelv and other tests for
    database filling operations.

    Returns:
        Dict mapping routine name to MUMPS source code
    """
    global _MERGE_HELPERS
    if _MERGE_HELPERS is None:
        _MERGE_HELPERS = {}
        # Load lfill.m helper
        lfill_path = MERGE_INREF / "lfill.m"
        if lfill_path.exists():
            _MERGE_HELPERS["lfill"] = lfill_path.read_text()
    return _MERGE_HELPERS


def _needs_helpers(routine_name: str) -> bool:
    """Check if a routine needs helper routines to run."""
    return routine_name.lower() in _LFILL_DEPENDENT_ROUTINES


# =============================================================================
# Test Helpers
# =============================================================================


def make_test_id(routine_def: RoutineDefinition) -> str:
    """Create a test ID from routine definition."""
    return routine_def.label  # Use subtest name as ID


def get_subtest_params() -> list[pytest.param]:
    """Generate pytest parameters for merge subtests, excluding skipped ones."""
    return [
        pytest.param(subtest, id=make_test_id(subtest))
        for subtest in MERGE_SUBTESTS
        if not subtest.skip_reason
    ]


def get_routine_params() -> list[pytest.param]:
    """Generate pytest parameters for merge routines, excluding skipped ones."""
    return [
        pytest.param(routine, id=routine.routine)
        for routine in MERGE_ROUTINES
        if not routine.skip_reason
    ]


def load_subtest_outref(subtest_name: str) -> str | None:
    """Load and normalize the outref for a merge subtest.

    Args:
        subtest_name: Name of the subtest (e.g., "gbl2gbl")

    Returns:
        Normalized outref content, or None if not found
    """
    outref_path = MERGE_OUTREF / f"{subtest_name}.txt"
    if not outref_path.exists():
        return None

    content = outref_path.read_text()
    return normalize_outref(content)


# =============================================================================
# Parametrized Test Suite - Subtests
# =============================================================================


@pytest.mark.merge
@pytest.mark.functional
class TestMergeSuite:
    """Parametrized tests for merge subtests.

    Each test runs the primary routine for a subtest through m2py and
    compares against the normalized outref.
    """

    @pytest.mark.parametrize("subtest_def", get_subtest_params())
    def test_subtest(self, subtest_def: RoutineDefinition) -> None:
        """Test a merge subtest.

        Args:
            subtest_def: The subtest definition containing name and primary routine
        """
        # Load the primary routine source (check extracted routines dir first)
        try:
            source = load_routine_source(MERGE_EXTRACTED, subtest_def.routine)
        except FileNotFoundError:
            source = load_routine_source(MERGE_INREF, subtest_def.routine)
        assert source is not None, (
            f"Failed to load routine {subtest_def.routine} for {subtest_def.label}"
        )

        # Load helpers if needed (lfill.m for mergelv tests)
        helpers = _load_merge_helpers() if _needs_helpers(subtest_def.routine) else None

        # Run through m2py
        result = run_mumps(source, timeout=30, helper_sources=helpers)

        if result is None or (not result.output and not result.success):
            pytest.fail(f"No result for {subtest_def.label}")

        # Load expected output
        expected = load_subtest_outref(subtest_def.label)
        if expected and result.success:
            comparison = compare_output(
                result.output, expected, strip_internal_blanks=True
            )
            if not comparison.match:
                # Show first 40 lines of diff for debugging
                diff_preview = "\n".join((comparison.diff or "").split("\n")[:40])
                pytest.fail(
                    f"Output mismatch for {subtest_def.label} "
                    f"(actual={comparison.actual_lines}, "
                    f"expected={comparison.expected_lines}):\n{diff_preview}"
                )


# =============================================================================
# Parametrized Test Suite - Individual Routines
# =============================================================================


@pytest.mark.merge
@pytest.mark.functional
class TestMergeRoutines:
    """Parametrized tests for individual merge routines.

    Tests each merge routine can be parsed and executed, independent
    of the subtest structure.
    """

    @pytest.mark.parametrize("routine_def", get_routine_params())
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a merge routine.

        Args:
            routine_def: The routine definition
        """
        try:
            source = load_routine_source(MERGE_EXTRACTED, routine_def.routine)
        except FileNotFoundError:
            source = load_routine_source(MERGE_INREF, routine_def.routine)
        assert source is not None, f"Failed to load routine {routine_def.routine}"

        # Load helpers if needed (lfill.m for mergelv tests)
        helpers = _load_merge_helpers() if _needs_helpers(routine_def.routine) else None

        # Run through m2py
        result = run_mumps(source, timeout=30, helper_sources=helpers)

        if result is None or (not result.output and not result.success):
            pytest.fail(f"No result for {routine_def.routine}")


# =============================================================================
# Infrastructure Tests
# =============================================================================


@pytest.mark.merge
@pytest.mark.functional
class TestMergeInfrastructure:
    """Tests to validate the merge test infrastructure."""

    def test_inref_directory_exists(self) -> None:
        """Verify the merge/inref directory exists with routines."""
        assert MERGE_INREF.exists(), f"Merge inref directory not found: {MERGE_INREF}"
        routines = list(MERGE_INREF.glob("*.m"))
        assert len(routines) > 0, "No .m files found in merge/inref"

    def test_outref_directory_exists(self) -> None:
        """Verify the merge/outref directory exists."""
        assert MERGE_OUTREF.exists(), (
            f"Merge outref directory not found: {MERGE_OUTREF}"
        )

    def test_driver_directory_exists(self) -> None:
        """Verify the merge/u_inref directory exists."""
        assert MERGE_UINREF.exists(), (
            f"Merge driver directory not found: {MERGE_UINREF}"
        )

    def test_subtest_count(self) -> None:
        """Verify the expected number of subtests are defined."""
        assert len(MERGE_SUBTESTS) == 25, (
            f"Expected 25 subtests, got {len(MERGE_SUBTESTS)}"
        )

    def test_routine_count(self) -> None:
        """Verify the expected number of routines are defined."""
        assert len(MERGE_ROUTINES) == 19, (
            f"Expected 19 routines, got {len(MERGE_ROUTINES)}"
        )

    def test_subtest_outrefs_exist(self) -> None:
        """Verify outref files exist for all subtests."""
        missing = []
        for subtest in MERGE_SUBTESTS:
            outref_path = MERGE_OUTREF / f"{subtest.label}.txt"
            if not outref_path.exists():
                missing.append(subtest.label)

        assert not missing, f"Missing outref files: {missing}"

    def test_routine_files_exist(self) -> None:
        """Verify all defined routines have corresponding .m files."""
        missing = []
        for routine_def in MERGE_ROUTINES:
            inref_path = MERGE_INREF / f"{routine_def.routine}.m"
            extracted_path = MERGE_EXTRACTED / f"{routine_def.routine}.m"
            if not inref_path.exists() and not extracted_path.exists():
                missing.append(routine_def.routine)

        assert not missing, f"Missing routine files: {missing}"

    def test_driver_scripts_exist(self) -> None:
        """Verify driver scripts exist for subtests."""
        # Not all subtests have driver scripts - some share drivers
        drivers = list(MERGE_UINREF.glob("*.csh"))
        assert len(drivers) >= 20, f"Expected 20+ driver scripts, found {len(drivers)}"
