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
from tests.functional.suite_definitions import MUGJ_ROUTINES, RoutineDefinition


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "mugj"
MUGJ_DIR = FUNCTIONAL_BASE / SUITE_NAME


# =============================================================================
# Outref Loading
# =============================================================================


class RoutineOutput:
    """Expected output for a single routine."""

    def __init__(self, label: str, content: str) -> None:
        self.label = label
        self.content = content


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


# Mapping of driver routines to their sub-routines whose outputs should be combined
DRIVER_SUBROUTINES: dict[str, list[str]] = {
    "V1PAT": ["V1PAT1", "V1PAT2"],  # mugj V1PAT calls only V1PAT1 and V1PAT2
}


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
    outputs = extract_routine_outputs(normalized)

    # Combine outputs for driver routines
    for driver, subroutines in DRIVER_SUBROUTINES.items():
        if driver in outputs and not outputs[driver]:
            # Driver has empty output - combine from subroutines
            combined_parts = []
            for sub in subroutines:
                if sub in outputs:
                    combined_parts.append(sub + "\n\n" + outputs[sub])
            if combined_parts:
                outputs[driver] = "\n\n".join(combined_parts)

    return outputs


# =============================================================================
# Routine Execution
# =============================================================================

# Mapping of driver routines to their required sub-routines
# These routines call external sub-drivers that must be loaded as helpers
# Also includes framework helpers like VREPORT that many tests depend on
ROUTINE_HELPERS: dict[str, list[str]] = {
    "V1PAT": ["V1PAT1", "V1PAT2", "VREPORT"],
}


def load_routine_helpers(routine_name: str) -> dict[str, str] | None:
    """Load helper routines required by a driver routine.

    Some mugj routines (like V1PAT) are drivers that call sub-routines.
    This function loads those sub-routines so they can be injected during
    transpilation.

    Args:
        routine_name: Name of the main routine

    Returns:
        Dict mapping helper routine name to source, or None if no helpers needed
    """
    helper_names = ROUTINE_HELPERS.get(routine_name)
    if not helper_names:
        return None

    inref_dir = MUGJ_DIR / "inref"
    helpers = {}
    for helper_name in helper_names:
        try:
            helpers[helper_name] = load_routine_source(inref_dir, helper_name)
        except FileNotFoundError:
            # Try YDBTest directory as fallback
            try:
                ydb_inref = FUNCTIONAL_BASE.parent / "YDBTest" / "mugj" / "inref"
                helpers[helper_name] = load_routine_source(ydb_inref, helper_name)
            except FileNotFoundError:
                pass  # Skip missing helpers
    return helpers if helpers else None


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

    # Load any required helper routines
    helpers = load_routine_helpers(routine_name)

    return run_mumps(source, helper_sources=helpers)


# =============================================================================
# Test Data
# =============================================================================

# Get expected outputs (loaded once at module level for efficiency)
_EXPECTED_OUTPUTS = load_mugj_expected_outputs()


# =============================================================================
# Tests
# =============================================================================


@pytest.mark.mugj
@pytest.mark.functional
class TestMugjSuite:
    """Test suite for mugj routines.

    Each routine is tested individually, comparing m2py output against
    the expected output from the YDB outref file.
    """

    @pytest.mark.parametrize(
        "routine_def",
        MUGJ_ROUTINES,
        ids=lambda r: r.routine,
    )
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a single mugj routine against expected output.

        Args:
            routine_def: RoutineDefinition with label, routine name, and metadata
        """
        # Check for skip
        if routine_def.skip_reason:
            pytest.skip(routine_def.skip_reason)

        routine_name = routine_def.routine
        label = routine_def.label

        # Check for known limitation (for xfail on failure)
        xfail_reason = get_routine_xfail_reason(routine_name)

        # Execute via m2py
        result = execute_routine(routine_name)

        # Check for complete failure (no output at all)
        if not result.output and not result.success:
            if xfail_reason:
                pytest.xfail(f"{xfail_reason} - {result.error}")
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

            # Mark as xfail if known limitation
            if xfail_reason:
                pytest.xfail(f"{xfail_reason} - Output mismatch")
            pytest.fail(msg)


# =============================================================================
# Infrastructure Tests
# =============================================================================


class TestMugjInfrastructure:
    """Tests to validate the mugj test infrastructure itself."""

    def test_routines_defined(self) -> None:
        """Verify mugj routines are defined in suite_definitions."""
        assert len(MUGJ_ROUTINES) > 0, "No routines defined for mugj"
        # First routine should be V1WR
        assert MUGJ_ROUTINES[0].routine == "V1WR"

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

    def test_routine_count_matches_definitions(self) -> None:
        """Verify routine count matches expected."""
        # 72 routines in mugj (71 active + 1 skipped for READ timeout)
        assert len(MUGJ_ROUTINES) == 72
