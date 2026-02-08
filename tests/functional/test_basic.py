"""Functional tests for the basic YottaDB test suite.

Executes each basic routine via m2py transpilation and compares output
against the YottaDB reference output (outref).

The basic suite covers fundamental MUMPS features: arithmetic, booleans,
string functions, FOR loops, XECUTE, VIEW commands, and Z-extensions.

Usage:
    uv run pytest tests/functional/test_basic.py -v
    uv run pytest tests/functional/test_basic.py -k fact -v  # Single routine
"""

from __future__ import annotations

import re

import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    ExecutionResult,
    compare_output,
    load_routine_source,
    normalize_outref,
    run_mumps,
)
from tests.functional.suite_definitions import BASIC_ROUTINES, RoutineDefinition


def _make_test_id(routine_def: RoutineDefinition) -> str:
    """Create a test ID from a routine definition."""
    return routine_def.routine


def get_routine_params() -> list:
    """Generate pytest parameters for basic routines, excluding skipped ones."""
    return [
        pytest.param(r, id=_make_test_id(r))
        for r in BASIC_ROUTINES
        if not r.skip_reason
    ]


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "basic"
BASIC_DIR = FUNCTIONAL_BASE / "basic" / "inref"

# Routine-specific helper dependencies
# Maps routine name to list of helper routine names that must be loaded
ROUTINE_HELPERS: dict[str, list[str]] = {
    "extcall": ["extcall2"],
    "text4": ["texttst", "text1", "text2", "text3"],
    "per02457": ["per02457"],  # Self-reference via $TEXT(+1^per02457)
    "putfail": [
        "putfail1",
        "putfail2",
        "putfail3",
        "putfail4",
        "putfail5",
        "putfail6",
        "putfail7",
        "putfail8",
        "putfail9",
    ],
}


# =============================================================================
# Outref Loading
# =============================================================================


def extract_basic_outputs(normalized_outref: str) -> dict[str, str]:
    """Extract individual routine outputs from the normalized basic outref.

    The basic outref contains output from all routines concatenated together.
    Each routine's output follows a YDB> prompt showing the command executed.

    The format is:
        YDB>
        d ^fact(18)
        Factorial test
          PASS

        YDB>
        d ^arith(18)
        ...

    After normalization, YDB> prompts are stripped, so we look for lines
    that look like routine calls (starting with "d ^").

    Args:
        normalized_outref: Normalized outref content (preamble stripped)

    Returns:
        Dict mapping routine label to its expected output
    """
    outputs: dict[str, str] = {}
    lines = normalized_outref.splitlines()

    # State machine to extract routine outputs
    current_label: str | None = None
    current_lines: list[str] = []

    # Pattern to match routine call lines
    call_pattern = re.compile(r"^d\s+\^(\w+)(?:\([^)]+\))?\s*$", re.IGNORECASE)

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line is a routine call
        if call_pattern.match(stripped):
            # Save previous routine if any
            if current_label is not None:
                content = "\n".join(current_lines).strip()
                if content:
                    outputs[current_label] = content

            # Start new routine - use the stripped line as label
            current_label = stripped
            current_lines = []
            i += 1
            continue

        # Accumulate content for current routine
        if current_label is not None:
            current_lines.append(line)

        i += 1

    # Save final routine
    if current_label is not None:
        content = "\n".join(current_lines).strip()
        if content:
            outputs[current_label] = content

    return outputs


def load_basic_expected_outputs() -> dict[str, str]:
    """Load and parse all expected outputs from the basic outref.

    Returns:
        Dict mapping routine label to expected output string
    """
    outref_path = FUNCTIONAL_BASE / "basic" / "outref" / "basic.txt"
    if not outref_path.exists():
        return {}

    raw_content = outref_path.read_text()
    normalized = normalize_outref(raw_content)
    return extract_basic_outputs(normalized)


# =============================================================================
# Routine Execution
# =============================================================================

# Load common helpers once at module level
_COMMON_HELPERS = None


def _get_common_helpers() -> dict[str, str]:
    """Get common helper routines, loading once on first access."""
    global _COMMON_HELPERS
    if _COMMON_HELPERS is None:
        from tests.functional.conftest import load_common_helpers

        _COMMON_HELPERS = load_common_helpers()
    return _COMMON_HELPERS


def execute_basic_routine(
    routine_name: str, args: str | None = None, use_helpers: bool = True
) -> ExecutionResult:
    """Execute a single basic routine via m2py.

    Args:
        routine_name: Name of the routine (e.g., "fact")
        args: Optional arguments to pass to the routine entry point
        use_helpers: If True, make common helpers (examine, header) available

    Returns:
        ExecutionResult with output and status
    """
    try:
        source = load_routine_source(BASIC_DIR, routine_name)
    except FileNotFoundError as e:
        return ExecutionResult(output="", success=False, error=str(e))

    helpers = _get_common_helpers().copy() if use_helpers else {}

    # Load routine-specific helpers (e.g., extcall needs extcall2)
    if routine_name in ROUTINE_HELPERS:
        for helper_name in ROUTINE_HELPERS[routine_name]:
            try:
                helpers[helper_name] = load_routine_source(BASIC_DIR, helper_name)
            except FileNotFoundError as e:
                return ExecutionResult(
                    output="", success=False, error=f"Missing helper {helper_name}: {e}"
                )

    return run_mumps(source, args=args, helper_sources=helpers if helpers else None)


# =============================================================================
# Test Data
# =============================================================================

# Get expected outputs (loaded once at module level for efficiency)
_EXPECTED_OUTPUTS = load_basic_expected_outputs()


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.basic
@pytest.mark.functional
class TestBasicSuite:
    """Test suite for basic YDB routines.

    Each routine is tested individually, comparing m2py output against
    the expected output from the YDB outref file.
    """

    @pytest.mark.parametrize("routine_def", get_routine_params())
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a single basic routine against expected output.

        Args:
            routine_def: RoutineDefinition with label, routine name, and args
        """
        routine_name = routine_def.routine
        label = routine_def.label

        # Execute via m2py (pass args if defined)
        result = execute_basic_routine(routine_name, routine_def.args)

        # Check for complete failure (no output at all)
        if not result.output and not result.success:
            pytest.fail(f"Routine {routine_name} failed to execute: {result.error}")

        # Get expected output using the label format from outref
        expected = _EXPECTED_OUTPUTS.get(label)
        if expected is None:
            # Try lowercase version
            expected = _EXPECTED_OUTPUTS.get(label.lower())
        if expected is None:
            pytest.fail(
                f"No expected output found for {label} in outref - check outref parsing"
            )

        # Handle partial output due to external routine errors
        actual_output = result.output

        # Compare outputs
        comparison = compare_output(actual_output, expected)

        if not comparison.match:
            # Check if this is a partial match (external routine error at end)
            if result.error and "No module named" in result.error:
                if expected.startswith(actual_output.strip()):
                    pytest.fail(
                        f"Partial match - routine completed but external call failed: {result.error}"
                    )

            # Format failure message with diff
            msg = (
                f"\nOutput mismatch for routine {routine_name}\n"
                f"Label: {label}\n"
                f"Expected lines: {comparison.expected_lines}\n"
                f"Actual lines: {comparison.actual_lines}\n"
            )
            if result.error:
                msg += f"Execution error: {result.error}\n"
            msg += f"\nDiff:\n{comparison.diff}"

            pytest.fail(msg)


# =============================================================================
# Infrastructure Tests
# =============================================================================


class TestBasicInfrastructure:
    """Tests to validate the basic test infrastructure itself."""

    def test_routines_defined(self) -> None:
        """Verify basic routines are defined in suite_definitions."""
        assert len(BASIC_ROUTINES) > 0, "No routines defined for basic"
        # First routine should be fact
        assert BASIC_ROUTINES[0].routine == "fact"

    def test_outref_loads(self) -> None:
        """Verify the basic outref loads and normalizes."""
        outputs = load_basic_expected_outputs()
        assert len(outputs) > 0, "No outputs extracted from outref"
        # Should have output for d ^fact(18)
        assert any("fact" in label for label in outputs)

    def test_routine_source_loads(self) -> None:
        """Verify routine source files can be loaded."""
        source = load_routine_source(BASIC_DIR, "fact")
        assert "fact" in source.lower()

    def test_routine_count_matches_definitions(self) -> None:
        """Verify routine count matches expected."""
        # 57 routines in basic
        assert len(BASIC_ROUTINES) == 57
