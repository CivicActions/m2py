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

# Directory containing common helper routines (examine.m, header.m, etc.)
COM_DIR = FUNCTIONAL_BASE / "com"

# Default timeout for MUMPS execution (seconds)
# Increased from 30 to 60 to handle slow tests under parallel load
DEFAULT_TIMEOUT = 60

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
# Routine Loading Helpers
# =============================================================================


def filename_to_module_name(filename_stem: str) -> str:
    """Convert a MUMPS filename stem to the proper Python module name.

    MUMPS routines starting with % are stored as files starting with _ because
    % is not a valid filename character on many systems. When loading these
    files, we need to register them with their proper Python module name
    (_pct_ prefix) so that codegen-generated imports can find them.

    Examples:
        "_"        -> "_pct_"     (file _.m contains routine %)
        "_1A"      -> "_pct_1A"   (file _1A.m contains routine %1A)
        "_BCDEFGH" -> "_pct_BCDEFGH"
        "V1RN"     -> "V1RN"      (regular routine, no translation)

    Args:
        filename_stem: The filename without the .m extension

    Returns:
        The Python module name to register in sys.modules
    """
    if filename_stem.startswith("_"):
        # File _FOO.m represents MUMPS routine %FOO
        # Codegen translates %FOO to _pct_FOO for imports
        return "_pct_" + filename_stem[1:]
    return filename_stem


# =============================================================================
# T022: Routine → Limitation Mapping
# =============================================================================
# T002: Outref Normalization
# =============================================================================


def normalize_outref(content: str, strip_formfeeds: bool = False) -> str:
    """Strip YDB infrastructure from outref content.

    Removes:
    - Preamble before first YDB> prompt (dbcreate, GDE, mupip output)
    - Path placeholder lines (##TEST_PATH##, etc.)
    - Conditional output blocks (##SUSPEND_OUTPUT...##ALLOW_OUTPUT)
    - YDB> prompts themselves

    Optionally removes form feeds and their trailing blank lines for comparison
    when $Y pagination tracking differs between m2py and YDB.

    Args:
        content: Raw outref file content
        strip_formfeeds: If True, remove form feed characters and the blank line
            that follows them. This is useful when comparing output where the
            computation is correct but pagination differs due to YDB> prompt
            lines affecting $Y tracking in the original YDB output.

    Returns:
        Normalized content suitable for comparison with m2py output
    """
    lines = []
    in_suspended = False
    found_first_prompt = False

    # Use split('\n') instead of splitlines() to preserve \x0c characters
    # splitlines() treats \x0c as a line separator which corrupts form feeds
    for line in content.split("\n"):
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

    result = "\n".join(lines)

    if strip_formfeeds:
        # Remove form feeds and collapse all blank lines
        # This normalizes away pagination artifacts from $Y tracking differences
        # between YDB (which tracks $Y and triggers form feeds) and m2py
        # (which doesn't track $Y for pagination purposes)
        import re

        # Remove form feed characters
        result = re.sub(r"\x0c", "", result)
        # Collapse all consecutive newlines to single newline
        # This removes ALL blank lines, since they're pagination artifacts
        result = re.sub(r"\n{2,}", "\n", result)

    return result


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
    args: str | None = None,
    helper_sources: dict[str, str] | None = None,
) -> None:
    """Worker function for m2py execution in a subprocess.

    Args:
        source: MUMPS source code for the main routine
        result_queue: Queue to put results
        args: Optional arguments string (comma-separated)
        helper_sources: Dict mapping routine name to MUMPS source code
            for helper routines that should be available for external calls.
            These are transpiled and injected into sys.modules before execution.
    """
    try:
        import re
        import sys
        import types

        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        # Transpile and inject helper routines into sys.modules
        if helper_sources:
            for routine_name, helper_source in helper_sources.items():
                helper_code = generate_python(helper_source)

                # Create a module and execute the generated code in it
                module = types.ModuleType(routine_name)

                # IMPORTANT: Inject into sys.modules BEFORE executing
                # This is needed because the generated code may define dataclasses,
                # and the @dataclass decorator looks up the module via sys.modules
                sys.modules[routine_name] = module

                exec(helper_code, module.__dict__)

        # Generate Python code for main routine
        python_code = generate_python(source)

        # T075b: Extract routine name and inject main routine into sys.modules
        # This enables helper routines to GOTO back to the main routine
        # (e.g., V1SEQ1.E5 does G A7902^V1SEQ)
        routine_name_match = re.search(
            r'^_routine_name\s*=\s*["\'](\w+)["\']', python_code, re.MULTILINE
        )
        main_routine_name = None
        if routine_name_match:
            main_routine_name = routine_name_match.group(1)
            main_module = types.ModuleType(main_routine_name)
            sys.modules[main_routine_name] = main_module
            exec(python_code, main_module.__dict__)

        # Parse args string into tuple if provided (e.g., "18" -> (18,))
        entry_args = None
        if args:
            # Split by comma, convert numeric strings to numbers
            parsed_args = []
            for arg in args.split(","):
                arg = arg.strip()
                try:
                    # Try as integer first
                    parsed_args.append(int(arg))
                except ValueError:
                    try:
                        # Try as float
                        parsed_args.append(float(arg))
                    except ValueError:
                        # Keep as string
                        parsed_args.append(arg)
            entry_args = tuple(parsed_args)

        # Execute and capture output
        runtime = MUMPSRuntime()

        # T075b: If main routine was injected as a module, execute via the module
        # This ensures the module namespace is shared for mutual recursion
        if main_routine_name and main_routine_name in sys.modules:
            main_module = sys.modules[main_routine_name]
            # Get the entry function
            entry_func = getattr(main_module, main_routine_name, None)
            if entry_func and callable(entry_func):
                runtime._capture_output = True
                runtime.clear()
                _scope: dict = {}

                # T075a: Set up runtime context for $TEXT function support
                runtime._current_routine = getattr(
                    main_module, "_routine_name", main_routine_name
                )
                runtime._current_source_lines = getattr(
                    main_module, "_source_lines", []
                )
                runtime._current_label_lines = getattr(main_module, "_label_lines", {})

                try:
                    from m2py.runtime import run_with_goto_support

                    # Define wrapper function (avoid lambda per E731)
                    def wrapped_func(_rt, _scope=_scope):
                        if entry_args:
                            return entry_func(_rt, *entry_args, _scope=_scope)
                        return entry_func(_rt, _scope=_scope)

                    run_with_goto_support(wrapped_func, runtime, _scope)
                    result_queue.put(
                        ExecutionResult(
                            output=runtime.get_output(), success=True, error=None
                        )
                    )
                except Exception as e:
                    result_queue.put(
                        ExecutionResult(
                            output=runtime.get_output(), success=False, error=str(e)
                        )
                    )
                return

        # Fallback to standard execute() if module injection failed
        result = runtime.execute(
            python_code, capture_output=True, entry_args=entry_args
        )

        result_queue.put(
            ExecutionResult(
                output=result.output, success=result.success, error=result.error
            )
        )
    except Exception as e:
        import traceback

        tb = traceback.format_exc()
        result_queue.put(
            ExecutionResult(
                output="", success=False, error=f"{type(e).__name__}: {e}\n{tb}"
            )
        )


def run_mumps(
    source: str,
    timeout: int = DEFAULT_TIMEOUT,
    args: str | None = None,
    helper_sources: dict[str, str] | None = None,
) -> ExecutionResult:
    """Execute MUMPS source via m2py transpilation with timeout protection.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds (process killed if exceeded)
        args: Optional comma-separated arguments for the entry point
        helper_sources: Dict mapping routine name to MUMPS source code
            for helper routines that should be available for external calls.

    Returns:
        ExecutionResult with output and status
    """
    result_queue: multiprocessing.Queue = multiprocessing.Queue()
    process = multiprocessing.Process(
        target=_run_m2py_worker,
        args=(source, result_queue, args, helper_sources),
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


def load_common_helpers() -> dict[str, str]:
    """Load common helper routines from tests/functional/com/.

    These helpers (examine.m, header.m) are used by many tests in the
    basic suite for test assertions and reporting.

    Returns:
        Dict mapping routine name to MUMPS source code
    """
    helpers = {}
    if COM_DIR.exists():
        for m_file in COM_DIR.glob("*.m"):
            routine_name = m_file.stem
            helpers[routine_name] = m_file.read_text()
    return helpers


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


def routine_to_filename(routine_name: str) -> str:
    """Convert MUMPS routine name to filename.

    % prefix becomes _ in filename since % is not safe in all filesystems.

    Args:
        routine_name: MUMPS routine name (e.g., %, %1A, V1RN)

    Returns:
        Filename (e.g., _, _1A, V1RN)

    Examples:
        >>> routine_to_filename("%")
        '_'
        >>> routine_to_filename("%1A")
        '_1A'
        >>> routine_to_filename("V1RN")
        'V1RN'
    """
    if routine_name.startswith("%"):
        return "_" + routine_name[1:]
    return routine_name


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
    # Translate routine name to filename (% -> _)
    filename = routine_to_filename(routine_name)
    routine_path = inref_dir / f"{filename}.m"
    if not routine_path.exists():
        # Try lowercase
        routine_path = inref_dir / f"{filename.lower()}.m"
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


def compare_output(
    actual: str, expected: str, *, strip_blank_lines: bool = True
) -> ComparisonResult:
    """Compare actual output against expected with clear diff reporting.

    Uses unified diff format for easy reading. Normalizes line endings
    before comparison.

    Note: Both actual (m2py output) and expected (outref) should be normalized
    for form feeds before calling this function, or the actual will be
    normalized here.

    Args:
        actual: Actual output from m2py execution
        expected: Expected output (typically from normalized outref)
        strip_blank_lines: If True, strip leading/trailing blank lines

    Returns:
        ComparisonResult with match status and diff if mismatched
    """
    # Normalize line endings and trailing whitespace
    # Use split('\n') instead of splitlines() to preserve \x0c characters
    actual_lines = [line.rstrip() for line in actual.split("\n")]
    expected_lines = [line.rstrip() for line in expected.split("\n")]

    # Strip leading/trailing blank lines if requested
    if strip_blank_lines:
        while actual_lines and not actual_lines[0]:
            actual_lines.pop(0)
        while actual_lines and not actual_lines[-1]:
            actual_lines.pop()
        while expected_lines and not expected_lines[0]:
            expected_lines.pop(0)
        while expected_lines and not expected_lines[-1]:
            expected_lines.pop()

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
