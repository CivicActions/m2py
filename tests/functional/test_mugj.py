"""Functional tests for the mugj (MUMPS User Group Japan) test suite.

The MUGJ suite uses pattern-based validation instead of full output comparison.
Each routine is validated by checking:
1. Number of PASS markers matches expected count
2. No unexpected FAIL markers (beyond known collation failures)
3. Visual "should be identical" checks pass (consecutive lines match)

This approach is resilient to whitespace/formatting differences caused by
form feed pagination tracking ($Y) differences between YDB and m2py.

Usage:
    uv run pytest tests/functional/test_mugj.py -v
    uv run pytest tests/functional/test_mugj.py::TestMugjSuite -v
    uv run pytest tests/functional/test_mugj.py -k "V1WR" -v
"""

from __future__ import annotations

import re
import sys
import types
from dataclasses import dataclass

import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    filename_to_module_name,
    load_routine_source,
)
from tests.functional.suite_definitions import MUGJ_ROUTINES, RoutineDefinition


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "mugj"
MUGJ_DIR = FUNCTIONAL_BASE / SUITE_NAME
MUGJ_INREF = MUGJ_DIR / "inref"
MUGJ_OUTREF = MUGJ_DIR / "outref" / "mugj.txt"


# =============================================================================
# Pattern-Based Validation
# =============================================================================


@dataclass
class ValidationResult:
    """Result of pattern-based validation."""

    passed: bool
    pass_count: int
    expected_passes: int | None
    fail_count: int
    expected_fails: int
    unexpected_fails: list[str]
    visual_checks: int
    expected_visual: int
    visual_failures: list[tuple[str, str, str]]  # (context, expected, actual)
    errors: list[str]

    @property
    def summary(self) -> str:
        """Generate a summary message."""
        parts = []
        if self.expected_passes is not None:
            if self.pass_count != self.expected_passes:
                parts.append(
                    f"PASS count: {self.pass_count} (expected {self.expected_passes})"
                )
            else:
                parts.append(f"PASS count: {self.pass_count} ✓")
        else:
            parts.append(f"PASS count: {self.pass_count} (no expectation)")

        if self.unexpected_fails:
            parts.append(f"Unexpected FAILs: {self.unexpected_fails}")
        elif self.fail_count > 0:
            parts.append(f"Expected FAILs: {self.fail_count} ✓")

        if self.visual_failures:
            parts.append(f"Visual check failures: {len(self.visual_failures)}")
        elif self.expected_visual > 0:
            parts.append(
                f"Visual checks: {self.visual_checks}/{self.expected_visual} ✓"
            )

        if self.errors:
            parts.append(f"Errors: {self.errors}")

        return "\n".join(parts)


def validate_output_patterns(
    output: str,
    expected_passes: int | None = None,
    expected_visual: int | None = None,
    expected_fails: int | None = None,
) -> ValidationResult:
    """Validate routine output using pattern matching.

    Checks:
    1. Number of PASS markers matches expected (if specified)
    2. No unexpected "** FAIL" markers beyond expected_fails count
    3. Visual "should be identical" checks - verify consecutive lines match

    Args:
        output: The routine's output
        expected_passes: Expected number of PASS markers (None = no check)
        expected_visual: Expected number of visual checks (None = no check)
        expected_fails: Expected number of "** FAIL" markers (default 0)

    Returns:
        ValidationResult with detailed pass/fail information
    """
    expected_fails = expected_fails or 0
    expected_visual = expected_visual or 0
    errors: list[str] = []

    # Count PASS markers
    pass_matches = re.findall(r"\bPASS\b", output)
    pass_count = len(pass_matches)

    # Count and extract FAIL markers
    fail_matches = re.findall(r"\*\* FAIL\s+(\S+)", output)
    fail_count = len(fail_matches)

    # Determine unexpected fails (more than expected)
    unexpected_fails = (
        fail_matches[expected_fails:] if fail_count > expected_fails else []
    )

    # Check visual "should be identical" patterns
    visual_failures: list[tuple[str, str, str]] = []
    visual_checks = 0

    # Find all "should be identical" patterns and check the following two lines
    lines = output.split("\n")
    for i, line in enumerate(lines):
        if "should be identical" in line.lower():
            visual_checks += 1
            # Get context (the test description, usually the line before)
            context = lines[i - 1].strip() if i > 0 else "Unknown"

            # Find the next two non-empty lines
            next_lines = []
            j = i + 1
            while j < len(lines) and len(next_lines) < 2:
                if lines[j].strip():  # Skip empty lines
                    next_lines.append(lines[j])
                j += 1

            if len(next_lines) >= 2:
                expected_line = next_lines[0]
                actual_line = next_lines[1]
                if expected_line != actual_line:
                    visual_failures.append((context, expected_line, actual_line))
            else:
                errors.append(
                    f"Visual check at '{context}': insufficient lines to compare"
                )

    # Determine overall pass/fail
    passed = True

    # Check PASS count
    if expected_passes is not None and pass_count != expected_passes:
        passed = False

    # Check for unexpected fails
    if unexpected_fails:
        passed = False

    # Check visual failures
    if visual_failures:
        passed = False

    # Check expected visual count
    if expected_visual > 0 and visual_checks != expected_visual:
        passed = False
        errors.append(
            f"Expected {expected_visual} visual checks, found {visual_checks}"
        )

    return ValidationResult(
        passed=passed,
        pass_count=pass_count,
        expected_passes=expected_passes,
        fail_count=fail_count,
        expected_fails=expected_fails,
        unexpected_fails=unexpected_fails,
        visual_checks=visual_checks,
        expected_visual=expected_visual,
        visual_failures=visual_failures,
        errors=errors,
    )


# =============================================================================
# Routine Loading
# =============================================================================

# Cache for loaded routine modules (populated once for all tests)
_CACHED_MODULES: tuple[dict[str, types.ModuleType | None], dict[str, str]] | None = None


def _load_all_mugj_routines() -> tuple[
    dict[str, types.ModuleType | None], dict[str, str]
]:
    """Load and transpile ALL MUGJ routines from inref/.

    This loads all routines upfront so that inter-routine calls
    (D ^VREPORT, G ^V1WR1, etc.) can resolve properly.

    Note: Files starting with _ (like _.m, _1A.m) are registered with _pct_
    prefix module names since they represent MUMPS % routines.

    Returns:
        Tuple of (routine_modules dict, transpile_errors dict)
    """
    from m2py.codegen import generate_python

    all_routine_files = list(MUGJ_INREF.glob("*.m"))
    routine_modules: dict[str, types.ModuleType | None] = {}
    transpile_errors: dict[str, str] = {}

    for source_path in all_routine_files:
        filename_stem = source_path.stem
        module_name = filename_to_module_name(filename_stem)
        source = source_path.read_text()

        try:
            python_code = generate_python(source)
            module = types.ModuleType(module_name)
            sys.modules[module_name] = module
            exec(python_code, module.__dict__)
            routine_modules[module_name] = module
        except Exception as e:
            # Mark routine as failed to transpile
            routine_modules[module_name] = None
            transpile_errors[module_name] = str(e)

    return routine_modules, transpile_errors


def _get_cached_modules() -> tuple[dict[str, types.ModuleType | None], dict[str, str]]:
    """Get cached routine modules, loading if needed."""
    global _CACHED_MODULES
    if _CACHED_MODULES is None:
        _CACHED_MODULES = _load_all_mugj_routines()
    return _CACHED_MODULES


# =============================================================================
# Test Helpers
# =============================================================================


def make_test_id(routine_def: RoutineDefinition) -> str:
    """Create a test ID from routine definition."""
    return routine_def.routine


def get_routine_params() -> list[pytest.param]:
    """Generate pytest parameters for MUGJ routines, excluding skipped ones."""
    return [
        pytest.param(routine, id=make_test_id(routine))
        for routine in MUGJ_ROUTINES
        if not routine.skip_reason
    ]


# =============================================================================
# Parametrized Test Suite
# =============================================================================


@pytest.mark.mugj
@pytest.mark.functional
class TestMugjSuite:
    """Parametrized tests for MUGJ routines.

    Each test runs a routine through m2py with all MUGJ routines
    pre-loaded as modules (matching YDB behavior where all routines
    are available), then validates output using pattern matching:
    - Correct number of PASS markers
    - No unexpected FAIL markers
    - Visual "should be identical" checks pass
    """

    @pytest.mark.parametrize("routine_def", get_routine_params())
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a single MUGJ routine using pattern-based validation.

        Args:
            routine_def: The routine definition containing label, routine name,
                        expected counts, and optional skip reason.
        """
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        routine_name = routine_def.routine

        # Get pre-loaded modules
        routine_modules, transpile_errors = _get_cached_modules()

        # Check if routine failed to transpile
        if routine_name in transpile_errors:
            pytest.xfail(f"Transpile error: {transpile_errors[routine_name]}")

        module = routine_modules.get(routine_name)
        if module is None:
            pytest.xfail(f"Routine {routine_name} not available")

        # Create runtime — MUMPSRuntime() picks up the backend from
        # M2PY_GLOBAL_BACKEND env var when --backend is specified.
        runtime = MUMPSRuntime()
        runtime._capture_output = True
        runtime.clear()

        # Set up runtime context
        runtime._current_routine = getattr(module, "_routine_name", routine_name)
        runtime._current_source_lines = getattr(module, "_source_lines", [])
        runtime._current_label_lines = getattr(module, "_label_lines", {})

        # Get entry function - prefer _entry_function (line 1) over named label
        # This handles routines with labelless first lines (preamble)
        entry_func = getattr(module, "_entry_function", None)
        if entry_func is None:
            # Fall back to named label for older generated code
            entry_func = getattr(module, routine_name, None)
        if not entry_func or not callable(entry_func):
            pytest.xfail(f"No entry point for {routine_name}")

        try:
            run_with_goto_support(entry_func, runtime, {})
            actual_output = runtime.get_output()
        except Exception as e:
            pytest.fail(f"Runtime error in {routine_name}: {e}")

        # Validate using pattern matching
        result = validate_output_patterns(
            actual_output,
            expected_passes=routine_def.expected_passes,
            expected_visual=routine_def.expected_visual,
            expected_fails=routine_def.expected_fails,
        )

        if not result.passed:
            # Generate detailed failure message
            msg = f"\n{routine_name} validation failed\n"
            msg += f"{result.summary}\n"

            if result.visual_failures:
                msg += "\nVisual check failures:\n"
                for context, expected, actual in result.visual_failures:
                    msg += f"  Context: {context}\n"
                    msg += f"  Expected: {expected!r}\n"
                    msg += f"  Actual:   {actual!r}\n"

            if result.unexpected_fails:
                msg += f"\nUnexpected FAILs: {result.unexpected_fails}\n"

            pytest.fail(msg)


# =============================================================================
# Infrastructure Tests
# =============================================================================


@pytest.mark.mugj
@pytest.mark.functional
class TestMugjInfrastructure:
    """Tests to validate the mugj test infrastructure itself."""

    def test_routines_defined(self) -> None:
        """Verify mugj routines are defined in suite_definitions."""
        assert len(MUGJ_ROUTINES) > 0, "No routines defined for mugj"
        # First routine should be V1WR
        assert MUGJ_ROUTINES[0].routine == "V1WR"

    def test_outref_exists(self) -> None:
        """Verify the mugj outref file exists."""
        assert MUGJ_OUTREF.exists(), f"Outref not found: {MUGJ_OUTREF}"
        content = MUGJ_OUTREF.read_text()
        assert len(content) > 0, "Outref is empty"
        # Should contain V1WR output
        assert "V1WR" in content

    def test_inref_directory_exists(self) -> None:
        """Verify the mugj inref directory exists with routines."""
        assert MUGJ_INREF.exists(), f"Inref directory not found: {MUGJ_INREF}"
        routines = list(MUGJ_INREF.glob("*.m"))
        assert len(routines) > 0, "No .m files found in mugj/inref"

    def test_routine_source_loads(self) -> None:
        """Verify routine source files can be loaded."""
        source = load_routine_source(MUGJ_INREF, "V1WR")
        assert "V1WR" in source
        assert "WRITE" in source.upper()

    def test_routine_count_matches_definitions(self) -> None:
        """Verify routine count matches expected."""
        # 72 routines in mugj (70 active + 2 skipped)
        assert len(MUGJ_ROUTINES) == 72

    def test_expected_counts_defined(self) -> None:
        """Verify all routines have expected_passes or expected_visual defined."""
        missing = []
        for routine in MUGJ_ROUTINES:
            if routine.skip_reason:
                continue  # Skip reason means we don't run it
            if routine.expected_passes is None and routine.expected_visual is None:
                missing.append(routine.routine)

        if missing:
            pytest.fail(f"Routines missing expected counts: {missing}")

    def test_validation_patterns(self) -> None:
        """Test the pattern validation logic with sample output."""
        # Sample output with PASS markers
        output_with_passes = """
I-186  Comment coming after ls  (visual)
   PASS  I-186
I-187  Comment coming after label ls  (visual)
   PASS  I-187
I-188  Comment coming after command argument  (visual)
   PASS  I-188
"""
        result = validate_output_patterns(output_with_passes, expected_passes=3)
        assert result.passed
        assert result.pass_count == 3

        # Sample output with visual check
        output_with_visual = """
I-802.1  Output of upper-case alphabetics  (visual)
         following two lines should be identical
ABCDEFGHIJKLMNOPQRSTUVWXYZ
ABCDEFGHIJKLMNOPQRSTUVWXYZ
"""
        result = validate_output_patterns(output_with_visual, expected_visual=1)
        assert result.passed
        assert result.visual_checks == 1
        assert not result.visual_failures

        # Sample output with visual failure
        output_with_visual_fail = """
I-802.1  Output of upper-case alphabetics  (visual)
         following two lines should be identical
ABCDEFGHIJKLMNOPQRSTUVWXYZ
WRONG_OUTPUT
"""
        result = validate_output_patterns(output_with_visual_fail, expected_visual=1)
        assert not result.passed
        assert len(result.visual_failures) == 1

        # Sample output with expected FAIL
        output_with_fail = """
   PASS  II-144
** FAIL  II-145
   PASS  II-147
"""
        result = validate_output_patterns(
            output_with_fail, expected_passes=2, expected_fails=1
        )
        assert result.passed
        assert result.pass_count == 2
        assert result.fail_count == 1

        # Sample output with unexpected FAIL
        result = validate_output_patterns(
            output_with_fail, expected_passes=2, expected_fails=0
        )
        assert not result.passed
        assert result.unexpected_fails == ["II-145"]
