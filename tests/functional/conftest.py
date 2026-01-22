"""Pytest configuration and fixtures for functional tests.

Provides infrastructure for running MUMPS test suites via m2py transpilation
and comparing output against YottaDB reference files (outref).

Key Fixtures:
- normalize_outref: Strip YDB infrastructure markers from outref content
- parse_driver: Extract routine execution sequence from test driver scripts
- run_mumps: Execute MUMPS source via m2py and capture output
- compare_output: Byte-for-byte comparison with clear diff reporting
- xfail_limitation: Mark tests as expected failures with limitation IDs
"""

from __future__ import annotations

import difflib
import multiprocessing
import queue
import re
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

# =============================================================================
# Constants
# =============================================================================

FUNCTIONAL_BASE = Path(__file__).parent

# Default timeout for MUMPS execution (seconds)
DEFAULT_TIMEOUT = 30

# YDB infrastructure markers to strip from outref content
YDB_PATH_MARKERS = frozenset(
    [
        "##TEST_PATH##",
        "##SOURCE_PATH##",
        "##REMOTE_TEST_PATH##",
        "##REMOTE_SOURCE_PATH##",
        "##IN_TEST_PATH##",
        "##TEST_AWK##",
    ]
)


# =============================================================================
# T002: Outref Normalization
# =============================================================================


def normalize_outref(content: str) -> str:
    """Strip YDB infrastructure from outref content.

    Removes:
    - Preamble before first YDB> prompt (dbcreate, GDE, mupip output)
    - Path placeholder lines (##TEST_PATH##, etc.)
    - Conditional output blocks (##SUSPEND_OUTPUT...##ALLOW_OUTPUT)
    - YDB> prompts themselves

    Args:
        content: Raw outref file content

    Returns:
        Normalized content suitable for comparison with m2py output
    """
    lines = []
    in_suspended = False
    found_first_prompt = False

    for line in content.splitlines():
        # Skip preamble before first YDB>
        if not found_first_prompt:
            if "YDB>" in line:
                found_first_prompt = True
                # Don't include the YDB> prompt line itself
            continue

        # Handle suspend/allow blocks
        if "##SUSPEND_OUTPUT" in line:
            in_suspended = True
            continue
        if "##ALLOW_OUTPUT" in line:
            in_suspended = False
            continue
        if in_suspended:
            continue

        # Skip path placeholder lines
        if any(marker in line for marker in YDB_PATH_MARKERS):
            continue

        # Skip YDB> prompt lines
        if line.strip() == "YDB>":
            continue

        lines.append(line)

    return "\n".join(lines)


# =============================================================================
# T003: Driver Parser
# =============================================================================


class RoutineCall(NamedTuple):
    """A routine call extracted from a test driver script."""

    label: str  # The label printed before the call (e.g., "V1WR")
    routine: str  # The routine name to execute (e.g., "V1WR")


def parse_driver(driver_content: str) -> list[RoutineCall]:
    """Extract routine execution sequence from a test driver script.

    Parses lines like:
        W !!,"V1WR" D ^V1WR
        W !!,"V1CMT" D ^V1CMT  ;Comment

    Skips:
    - Commented-out lines (starting with ;)
    - Shell/tcsh infrastructure (starting with $ or #)
    - ZC commands (compile only, no output)
    - H/HALT commands

    Args:
        driver_content: Content of a .csh test driver file

    Returns:
        List of RoutineCall tuples in execution order
    """
    routines = []

    # Match lines like: W !!,"LABEL" D ^ROUTINE
    # The pattern captures the label (quoted string) and routine name
    pattern = re.compile(
        r'^W\s+!+,\s*"([^"]+)"\s+D\s+\^(\w+)',
        re.IGNORECASE,
    )

    for line in driver_content.splitlines():
        line = line.strip()

        # Skip empty lines and comments
        if not line or line.startswith(";"):
            continue

        # Skip shell infrastructure
        if line.startswith("$") or line.startswith("#"):
            continue

        # Skip here-doc delimiters
        if line.startswith("\\") or line in ("xyzz", "xyyz"):
            continue

        # Skip standalone commands (ZC, H, HALT)
        upper_line = line.upper()
        if upper_line in ("ZC", "H", "HALT"):
            continue

        # Try to match the routine call pattern
        match = pattern.match(line)
        if match:
            label, routine = match.groups()
            routines.append(RoutineCall(label=label, routine=routine))

    return routines


# =============================================================================
# T004: MUMPS Execution Helper
# =============================================================================


class ExecutionResult(NamedTuple):
    """Result of executing MUMPS code via m2py."""

    output: str
    success: bool
    error: str | None = None


def _run_m2py_worker(
    source: str,
    result_queue: multiprocessing.Queue,
) -> None:
    """Worker function for m2py execution in a subprocess."""
    try:
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        # Generate Python code
        python_code = generate_python(source)

        # Execute and capture output
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)

        result_queue.put(ExecutionResult(output=result.output, success=result.success))
    except Exception as e:
        result_queue.put(
            ExecutionResult(output="", success=False, error=f"{type(e).__name__}: {e}")
        )


def run_mumps(source: str, timeout: int = 30) -> ExecutionResult:
    """Execute MUMPS source via m2py transpilation with timeout protection.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds (process killed if exceeded)

    Returns:
        ExecutionResult with output and status
    """
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_run_m2py_worker,
        args=(source, result_queue),
    )

    try:
        process.start()
        try:
            result = result_queue.get(timeout=timeout)
            process.join(timeout=1)
            return result
        except queue.Empty:
            # Timeout
            pass
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)

    return ExecutionResult(
        output="",
        success=False,
        error=f"Execution timed out after {timeout}s",
    )


# =============================================================================
# T005: Base Test Class/Fixtures for Parametrized Suite Execution
# =============================================================================


class SuiteConfig(NamedTuple):
    """Configuration for a test suite."""

    name: str  # Suite name (e.g., "mugj", "basic")
    inref_dir: Path  # Directory containing .m source files
    outref_path: Path  # Path to reference output file
    driver_path: Path | None  # Path to driver script (.csh), if any


def load_suite_config(suite_name: str) -> SuiteConfig:
    """Load configuration for a test suite.

    Args:
        suite_name: Name of the suite (e.g., "mugj", "basic")

    Returns:
        SuiteConfig with paths resolved

    Raises:
        FileNotFoundError: If required directories/files don't exist
    """
    suite_dir = FUNCTIONAL_BASE / suite_name
    if not suite_dir.exists():
        msg = f"Suite directory not found: {suite_dir}"
        raise FileNotFoundError(msg)

    inref_dir = suite_dir / "inref"
    if not inref_dir.exists():
        msg = f"Suite inref directory not found: {inref_dir}"
        raise FileNotFoundError(msg)

    # Outref can be suite_name.txt or in outref/ subdirectory
    outref_path = suite_dir / "outref" / f"{suite_name}.txt"
    if not outref_path.exists():
        outref_path = suite_dir / f"{suite_name}.txt"

    # Driver script is optional
    driver_path = suite_dir / "u_inref" / f"{suite_name}.csh"
    if not driver_path.exists():
        driver_path = None

    return SuiteConfig(
        name=suite_name,
        inref_dir=inref_dir,
        outref_path=outref_path,
        driver_path=driver_path,
    )


def load_routine_source(inref_dir: Path, routine_name: str) -> str:
    """Load MUMPS source for a routine.

    Args:
        inref_dir: Directory containing .m files
        routine_name: Routine name (without .m extension)

    Returns:
        MUMPS source code

    Raises:
        FileNotFoundError: If routine file doesn't exist
    """
    routine_path = inref_dir / f"{routine_name}.m"
    if not routine_path.exists():
        # Try lowercase
        routine_path = inref_dir / f"{routine_name.lower()}.m"
    if not routine_path.exists():
        msg = f"Routine not found: {routine_name} in {inref_dir}"
        raise FileNotFoundError(msg)
    return routine_path.read_text()


# =============================================================================
# T006: Output Comparison with Clear Diff Reporting
# =============================================================================


class ComparisonResult(NamedTuple):
    """Result of comparing actual vs expected output."""

    match: bool
    diff: str | None  # Unified diff if mismatch, None if match
    actual_lines: int
    expected_lines: int


def compare_output(actual: str, expected: str) -> ComparisonResult:
    """Compare actual output against expected with clear diff reporting.

    Uses unified diff format for easy reading. Normalizes line endings
    before comparison.

    Args:
        actual: Actual output from m2py execution
        expected: Expected output (typically from normalized outref)

    Returns:
        ComparisonResult with match status and diff if mismatched
    """
    # Normalize line endings and trailing whitespace
    actual_lines = [line.rstrip() for line in actual.splitlines()]
    expected_lines = [line.rstrip() for line in expected.splitlines()]

    if actual_lines == expected_lines:
        return ComparisonResult(
            match=True,
            diff=None,
            actual_lines=len(actual_lines),
            expected_lines=len(expected_lines),
        )

    # Generate unified diff
    diff = difflib.unified_diff(
        expected_lines,
        actual_lines,
        fromfile="expected (outref)",
        tofile="actual (m2py)",
        lineterm="",
    )
    diff_text = "\n".join(diff)

    return ComparisonResult(
        match=False,
        diff=diff_text,
        actual_lines=len(actual_lines),
        expected_lines=len(expected_lines),
    )


# =============================================================================
# T007: Timeout Handling (Enhanced)
# =============================================================================

# Timeout handling is built into run_mumps() via the timeout parameter.
# DEFAULT_TIMEOUT constant defined at module level (30 seconds).
# Additional utilities for test-level timeout control:


def run_mumps_with_timeout(
    source: str,
    timeout: int | None = None,
) -> ExecutionResult:
    """Execute MUMPS with explicit timeout.

    Convenience wrapper that uses DEFAULT_TIMEOUT if not specified.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds (None = use DEFAULT_TIMEOUT)

    Returns:
        ExecutionResult with output and status
    """
    if timeout is None:
        timeout = DEFAULT_TIMEOUT
    return run_mumps(source, timeout=timeout)


# =============================================================================
# T008: Xfail Helper Referencing limitations.py IDs
# =============================================================================


def get_limitation_reason(limitation_id: str) -> str:
    """Get xfail reason string from a limitation ID.

    Imports limitations.py to get the canonical limitation description.

    Args:
        limitation_id: Limitation ID (e.g., "LIM-003")

    Returns:
        Formatted reason string for pytest.xfail
    """
    from m2py.limitations import LIMITATIONS

    if limitation_id in LIMITATIONS:
        lim = LIMITATIONS[limitation_id]
        return f"{limitation_id}: {lim.short_description}"
    return f"{limitation_id}: Unknown limitation"


def xfail_limitation(
    limitation_id: str, *, strict: bool = False
) -> pytest.MarkDecorator:
    """Create an xfail marker for a known limitation.

    Usage:
        @xfail_limitation("LIM-003")
        def test_mwapi_ssvn():
            ...

    Args:
        limitation_id: Limitation ID from limitations.py (e.g., "LIM-003")
        strict: If True, unexpected passes will fail the test

    Returns:
        pytest.mark.xfail decorator with reason from limitations.py
    """
    reason = get_limitation_reason(limitation_id)
    return pytest.mark.xfail(reason=reason, strict=strict)


def skip_limitation(limitation_id: str) -> pytest.MarkDecorator:
    """Create a skip marker for a known limitation.

    Use when the test cannot run at all (vs xfail for tests that run but fail).

    Args:
        limitation_id: Limitation ID from limitations.py (e.g., "LIM-003")

    Returns:
        pytest.mark.skip decorator with reason from limitations.py
    """
    reason = get_limitation_reason(limitation_id)
    return pytest.mark.skip(reason=reason)


# =============================================================================
# Pytest Fixtures
# =============================================================================


@pytest.fixture
def outref_normalizer() -> Callable[[str], str]:
    """Fixture providing outref normalization function."""
    return normalize_outref


@pytest.fixture
def driver_parser() -> Callable[[str], list[RoutineCall]]:
    """Fixture providing driver script parser function."""
    return parse_driver


@pytest.fixture
def mumps_runner() -> Callable[[str, int], ExecutionResult]:
    """Fixture providing MUMPS execution function."""
    return run_mumps


@pytest.fixture
def output_comparator() -> Callable[[str, str], ComparisonResult]:
    """Fixture providing output comparison function."""
    return compare_output


@pytest.fixture
def suite_loader() -> Callable[[str], SuiteConfig]:
    """Fixture providing suite configuration loader."""
    return load_suite_config


@pytest.fixture
def routine_loader() -> Callable[[Path, str], str]:
    """Fixture providing routine source loader."""
    return load_routine_source
