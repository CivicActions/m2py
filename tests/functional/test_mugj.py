"""Functional tests for the mugj (MUMPS User Group Japan) test suite.

The MUGJ suite runs all routines serially in a single process, matching
the YDB driver pattern exactly. This preserves shared state ($Y, $X, globals)
across routines for byte-for-byte output comparison.

Usage:
    uv run pytest tests/functional/test_mugj.py -v
    uv run pytest tests/functional/test_mugj.py::TestMugjSerialExecution -v
"""

from __future__ import annotations

import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    compare_output,
    load_routine_source,
    normalize_outref,
)
from tests.functional.suite_definitions import MUGJ_ROUTINES


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "mugj"
MUGJ_DIR = FUNCTIONAL_BASE / SUITE_NAME


# =============================================================================
# Serial Suite Execution Test (T084)
# =============================================================================

# Routines that must be skipped in serial execution due to infrastructure issues
SERIAL_SKIP_ROUTINES: dict[str, str] = {
    # Routines that hang due to infinite loops or external goto issues
    "V1PC": "Depends on untranspiled V1PC1 helper routine",
    # Routines that require interactive input
    "V1BR": "BREAK command enters debugger",
    "VV2READ": "READ commands wait for user input",
}


def load_full_outref() -> str:
    """Load and normalize the full MUGJ outref for serial comparison.

    Returns the complete expected output with:
    - Preamble stripped (everything before first YDB>)
    - YDB> prompts removed
    - Path placeholders stripped
    - Suspend/allow blocks handled

    Does NOT normalize whitespace - byte-for-byte comparison required.
    """
    outref_path = MUGJ_DIR / "outref" / "mugj.txt"
    raw_content = outref_path.read_text()

    # Use normalize_outref with normalize_formfeed=False for byte-exact comparison
    return normalize_outref(raw_content, normalize_formfeed=False)


@pytest.mark.mugj
@pytest.mark.functional
class TestMugjSerialExecution:
    """Serial execution test matching YDB driver behavior.

    This test runs all MUGJ routines in sequence in a single process,
    exactly matching the YDB driver pattern:
    - W !!,"LABEL" D ^ROUTINE for each routine
    - Shared globals/state across all routines
    - Byte-for-byte output comparison (no whitespace normalization)

    The test is currently xfail because there are known failures that
    need to be addressed in tasks T085-T090:
    - T085: Multi-target GOTO xfails
    - T086: GotoExternal xfails
    - T087: Subscript indirection context fix
    - T088: Argument indirection command lists
    - T089: FOR step=0 edge case
    - T090: Final MUGJ validation
    """

    @pytest.mark.xfail(
        reason="MUGJ serial execution has known failures (T085-T090)",
        strict=False,
    )
    def test_full_suite_serial(self) -> None:
        """Execute all MUGJ routines serially and compare to full outref.

        This is the authoritative test for MUGJ suite correctness.
        """
        import sys
        import types
        from io import StringIO

        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        inref_dir = MUGJ_DIR / "inref"

        # First pass: transpile ALL routines from inref and inject into sys.modules
        # This includes helper routines like VREPORT, sub-routines like V1WR1, etc.
        all_routine_files = list(inref_dir.glob("*.m"))
        routine_modules: dict[str, types.ModuleType | None] = {}
        transpile_errors: dict[str, str] = {}

        for source_path in all_routine_files:
            routine_name = source_path.stem
            source = source_path.read_text()

            try:
                python_code = generate_python(source)
                module = types.ModuleType(routine_name)
                sys.modules[routine_name] = module
                exec(python_code, module.__dict__)
                routine_modules[routine_name] = module
            except Exception as e:
                # Mark routine as failed to transpile
                routine_modules[routine_name] = None
                transpile_errors[routine_name] = str(e)

        # Create runtime with shared state
        runtime = MUMPSRuntime()
        runtime._capture_output = True
        runtime.clear()

        # Execute driver routines in sequence (as specified in MUGJ_ROUTINES)
        output_parts: list[str] = []

        for routine_def in MUGJ_ROUTINES:
            routine_name = routine_def.routine
            label = routine_def.label

            # Skip routines with skip_reason in definition
            if routine_def.skip_reason:
                continue

            # Skip routines that hang or require interaction
            if routine_name in SERIAL_SKIP_ROUTINES:
                continue

            module = routine_modules.get(routine_name)
            if module is None:
                # Routine failed to transpile - output error marker
                output_parts.append(f"\n\n{label}")
                error_msg = transpile_errors.get(routine_name, "Unknown error")
                output_parts.append(
                    f"\n*** TRANSPILATION ERROR: {routine_name}: {error_msg} ***"
                )
                continue

            # Output W !!,"LABEL" equivalent: two newlines + label
            # This matches: W !!,"V1WR" which outputs \n\n followed by V1WR
            output_parts.append(f"\n\n{label}")

            # Set up runtime context
            runtime._current_routine = getattr(module, "_routine_name", routine_name)
            runtime._current_source_lines = getattr(module, "_source_lines", [])
            runtime._current_label_lines = getattr(module, "_label_lines", {})

            # Get entry function
            entry_func = getattr(module, routine_name, None)
            if not entry_func or not callable(entry_func):
                output_parts.append(f"\n*** NO ENTRY POINT: {routine_name} ***")
                continue

            # Clear output buffer for this routine but preserve globals
            runtime._output_buffer = StringIO()

            try:
                # run_with_goto_support expects func(rt, _scope=scope)
                run_with_goto_support(entry_func, runtime, {})
                routine_output = runtime.get_output()
                if routine_output:
                    output_parts.append(routine_output)
            except Exception as e:
                output_parts.append(f"\n*** RUNTIME ERROR: {routine_name}: {e} ***")

        # Combine all output
        actual_output = "".join(output_parts)

        # Load expected output
        expected_output = load_full_outref()

        # Compare byte-for-byte
        comparison = compare_output(actual_output, expected_output)

        if not comparison.match:
            # Generate detailed failure message
            msg = (
                f"\nFull suite output mismatch\n"
                f"Expected lines: {comparison.expected_lines}\n"
                f"Actual lines: {comparison.actual_lines}\n"
                f"\nFirst difference at line ~{self._find_first_diff_line(expected_output, actual_output)}\n"
                f"\nDiff (first 200 lines):\n"
            )
            # Limit diff output
            diff_lines = comparison.diff.splitlines()[:200]
            msg += "\n".join(diff_lines)
            pytest.fail(msg)

    def _find_first_diff_line(self, expected: str, actual: str) -> int:
        """Find the line number where expected and actual first differ."""
        expected_lines = expected.splitlines()
        actual_lines = actual.splitlines()

        for i, (exp, act) in enumerate(zip(expected_lines, actual_lines), 1):
            if exp != act:
                return i

        # Difference is in line count
        return min(len(expected_lines), len(actual_lines)) + 1


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
        outref_path = MUGJ_DIR / "outref" / "mugj.txt"
        assert outref_path.exists(), f"Outref not found: {outref_path}"
        content = outref_path.read_text()
        assert len(content) > 0, "Outref is empty"
        # Should contain V1WR output
        assert "V1WR" in content

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

    def test_serial_skip_routines_in_definitions(self) -> None:
        """Verify all SERIAL_SKIP_ROUTINES are in MUGJ_ROUTINES."""
        routine_names = {r.routine for r in MUGJ_ROUTINES}
        for skip_routine in SERIAL_SKIP_ROUTINES:
            assert skip_routine in routine_names, (
                f"{skip_routine} in SERIAL_SKIP_ROUTINES but not in MUGJ_ROUTINES"
            )
