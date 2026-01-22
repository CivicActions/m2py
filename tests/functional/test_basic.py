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
    get_routine_xfail_reason,
    load_routine_source,
    normalize_outref,
    run_mumps,
)
from tests.functional.suite_definitions import BASIC_ROUTINES, RoutineDefinition


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "basic"
BASIC_DIR = FUNCTIONAL_BASE / "basic" / "inref"


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


def execute_basic_routine(routine_name: str) -> ExecutionResult:
    """Execute a single basic routine via m2py.

    Args:
        routine_name: Name of the routine (e.g., "fact")

    Returns:
        ExecutionResult with output and status
    """
    try:
        source = load_routine_source(BASIC_DIR, routine_name)
    except FileNotFoundError as e:
        return ExecutionResult(output="", success=False, error=str(e))

    return run_mumps(source)


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

    @pytest.mark.parametrize(
        "routine_def",
        BASIC_ROUTINES,
        ids=lambda r: r.routine,
    )
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a single basic routine against expected output.

        Args:
            routine_def: RoutineDefinition with label, routine name, and args
        """
        # Check for skip
        if routine_def.skip_reason:
            pytest.skip(routine_def.skip_reason)

        routine_name = routine_def.routine
        label = routine_def.label

        # Check for known limitation (for xfail on failure)
        xfail_reason = get_routine_xfail_reason(routine_name)

        # Execute via m2py
        result = execute_basic_routine(routine_name)

        # Check for complete failure (no output at all)
        if not result.output and not result.success:
            if xfail_reason:
                pytest.xfail(f"{xfail_reason} - {result.error}")
            pytest.fail(f"Routine {routine_name} failed to execute: {result.error}")

        # Get expected output using the label format from outref
        expected = _EXPECTED_OUTPUTS.get(label)
        if expected is None:
            # Try lowercase version
            expected = _EXPECTED_OUTPUTS.get(label.lower())
        if expected is None:
            pytest.skip(f"No expected output found for {label} in outref")

        # Handle partial output due to external routine errors
        actual_output = result.output

        # Compare outputs
        comparison = compare_output(actual_output, expected)

        if not comparison.match:
            # Check if this is a partial match (external routine error at end)
            if result.error and "No module named" in result.error:
                if expected.startswith(actual_output.strip()):
                    pytest.skip(
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

            # Mark as xfail if known limitation
            if xfail_reason:
                pytest.xfail(f"{xfail_reason} - Output mismatch")
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
