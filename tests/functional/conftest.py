"""Pytest configuration and fixtures for functional tests.

Provides infrastructure for running MUMPS test suites via m2py transpilation
and comparing output against YottaDB reference files (outref).

Key Fixtures:
- normalize_outref: Strip YDB infrastructure markers from outref content
- parse_driver: Extract routine execution sequence from test driver scripts
- run_mumps: Execute MUMPS source via m2py and capture output
- compare_output: Byte-for-byte comparison with clear diff reporting
"""

from __future__ import annotations

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
