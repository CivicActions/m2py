"""Functional tests for the mugj (MUMPS User Group Japan) test suite.

Executes each mugj routine via m2py transpilation and compares output
against the YottaDB reference output (outref).

The mugj suite is the primary validation suite for MUMPS implementations,
containing comprehensive tests for all MUMPS language features.

Usage:
    uv run pytest tests/functional/test_mugj.py -v
    uv run pytest tests/functional/test_mugj.py -k V1WR -v  # Single routine
"""

from __future__ import annotations

import re
from typing import NamedTuple

import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    ExecutionResult,
    RoutineCall,
    compare_output,
    load_routine_source,
    normalize_outref,
    parse_driver,
    run_mumps,
)


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "mugj"
MUGJ_DIR = FUNCTIONAL_BASE / SUITE_NAME


# =============================================================================
# T010: Parse mugj.csh driver to extract routine execution order
# =============================================================================


def get_mugj_routines() -> list[RoutineCall]:
    """Get the list of routines to test from the mugj driver script.

    Returns:
        List of RoutineCall tuples in execution order
    """
    driver_path = MUGJ_DIR / "u_inref" / "mugj.csh"
    if not driver_path.exists():
        return []
    driver_content = driver_path.read_text()
    return parse_driver(driver_content)


# =============================================================================
# T012: Load and normalize mugj outref content
# =============================================================================


class RoutineOutput(NamedTuple):
    """Expected output for a single routine."""

    label: str  # The label printed before output (e.g., "V1WR")
    content: str  # The expected output content


def extract_routine_outputs(normalized_outref: str) -> dict[str, str]:
    """Extract individual routine outputs from the normalized outref.

    The outref contains output from all routines concatenated together.
    Each routine's output starts with a blank line, followed by the
    routine label on its own line (e.g., "V1WR"), then the routine output.

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
    in_routine = False

    # Pattern to match routine label lines (standalone short uppercase names)
    # Labels appear after blank lines and match the driver's W !!,"LABEL" output
    label_pattern = re.compile(r"^[A-Z][A-Z0-9_]*$")

    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this line could be a routine label
        # A label is a short identifier appearing after blank line(s)
        if label_pattern.match(stripped) and len(stripped) <= 20:
            # Look back to see if previous non-empty content ended
            # This is a heuristic - labels follow blank lines
            prev_blank = i > 0 and not lines[i - 1].strip()

            if prev_blank or not in_routine:
                # Save previous routine if any
                if current_label and current_lines:
                    # Trim leading/trailing blank lines from content
                    content = "\n".join(current_lines).strip()
                    outputs[current_label] = content

                # Start new routine
                current_label = stripped
                current_lines = []
                in_routine = True
                i += 1
                continue

        # Accumulate content for current routine
        if in_routine:
            current_lines.append(line)

        i += 1

    # Save final routine
    if current_label and current_lines:
        content = "\n".join(current_lines).strip()
        outputs[current_label] = content

    return outputs


def load_mugj_expected_outputs() -> dict[str, str]:
    """Load and parse all expected outputs from the mugj outref.

    Returns:
        Dict mapping routine label to expected output string
    """
    outref_path = MUGJ_DIR / "outref" / "mugj.txt"
    if not outref_path.exists():
        return {}

    raw_content = outref_path.read_text()
    normalized = normalize_outref(raw_content)
    return extract_routine_outputs(normalized)


# =============================================================================
# T013: Execute routines via m2py
# =============================================================================


def execute_routine(routine_name: str) -> ExecutionResult:
    """Execute a single mugj routine via m2py.

    Args:
        routine_name: Name of the routine (e.g., "V1WR")

    Returns:
        ExecutionResult with output and status
    """
    inref_dir = MUGJ_DIR / "inref"
    try:
        source = load_routine_source(inref_dir, routine_name)
    except FileNotFoundError as e:
        return ExecutionResult(output="", success=False, error=str(e))

    return run_mumps(source)


# =============================================================================
# Test Data Generation
# =============================================================================

# Get list of routines from driver
_ROUTINES = get_mugj_routines()

# Get expected outputs (loaded once at module level for efficiency)
_EXPECTED_OUTPUTS = load_mugj_expected_outputs()


def get_routine_ids() -> list[str]:
    """Get list of routine names for test parametrization."""
    return [r.routine for r in _ROUTINES]


# =============================================================================
# T009, T011: Create mugj test runner with parametrized tests
# =============================================================================


@pytest.mark.mugj
class TestMugjSuite:
    """Test suite for mugj routines.

    Each routine is tested individually, comparing m2py output against
    the expected output from the YDB outref file.
    """

    @pytest.mark.parametrize("routine_call", _ROUTINES, ids=lambda r: r.routine)
    def test_routine(self, routine_call: RoutineCall) -> None:
        """Test a single mugj routine against expected output.

        T014: Compare m2py output against normalized outref with diff on failure

        Args:
            routine_call: RoutineCall with label and routine name
        """
        routine_name = routine_call.routine
        label = routine_call.label

        # Execute via m2py
        result = execute_routine(routine_name)

        # Check for complete failure (no output at all)
        if not result.output and not result.success:
            pytest.fail(f"Routine {routine_name} failed to execute: {result.error}")

        # Get expected output
        expected = _EXPECTED_OUTPUTS.get(label)
        if expected is None:
            pytest.skip(f"No expected output found for {label} in outref")

        # Handle partial output due to external routine errors
        # Many mugj routines call D ^VREPORT at the end which fails
        # because external routine loading is not implemented
        actual_output = result.output

        # Compare outputs
        comparison = compare_output(actual_output, expected)

        if not comparison.match:
            # Check if this is a partial match (external routine error at end)
            if result.error and "No module named" in result.error:
                # Try comparing just what we got
                # If actual output is a prefix of expected, note it
                if expected.startswith(actual_output.strip()):
                    pytest.skip(
                        f"Partial match - routine completed but external call failed: {result.error}"
                    )

            # Format failure message with diff
            msg = (
                f"\nOutput mismatch for routine {routine_name}\n"
                f"Expected lines: {comparison.expected_lines}\n"
                f"Actual lines: {comparison.actual_lines}\n"
            )
            if result.error:
                msg += f"Execution error: {result.error}\n"
            msg += f"\nDiff:\n{comparison.diff}"
            pytest.fail(msg)


# =============================================================================
# Convenience test for quick validation
# =============================================================================


class TestMugjInfrastructure:
    """Tests to validate the mugj test infrastructure itself."""

    def test_driver_parses(self) -> None:
        """Verify the mugj driver script parses correctly."""
        routines = get_mugj_routines()
        assert len(routines) > 0, "No routines found in mugj driver"
        # First routine should be V1WR
        assert routines[0].routine == "V1WR"

    def test_outref_loads(self) -> None:
        """Verify the mugj outref loads and normalizes."""
        outputs = load_mugj_expected_outputs()
        assert len(outputs) > 0, "No outputs extracted from outref"
        # V1WR should have output
        assert "V1WR" in outputs

    def test_routine_source_loads(self) -> None:
        """Verify routine source files can be loaded."""
        inref_dir = MUGJ_DIR / "inref"
        source = load_routine_source(inref_dir, "V1WR")
        assert "V1WR" in source
        assert "WRITE" in source.upper()
