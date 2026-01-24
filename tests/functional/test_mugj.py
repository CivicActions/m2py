"""MUGJ (MUMPS User Group Japan) test suite.

This test runs ALL mugj routines in the exact same order as the YDB driver,
preserving shared state ($Y, $X, globals) across routines. This matches how
YDBTest executes the suite and ensures byte-for-byte output compatibility.

Key features:
- Exact match to YDB execution model (serial execution in driver order)
- Form feeds and whitespace match naturally (no normalization needed)
- Fast execution (~15s total including transpilation)

Usage:
    uv run pytest tests/functional/test_mugj.py -v
"""

from __future__ import annotations

import re
import sys
import types
from pathlib import Path

import pytest

from m2py.codegen import generate_python
from m2py.codegen.names import translate_name
from m2py.runtime import MUMPSRuntime

# =============================================================================
# Configuration
# =============================================================================

FUNCTIONAL_BASE = Path(__file__).parent
MUGJ_DIR = FUNCTIONAL_BASE / "mugj"
INREF_DIR = MUGJ_DIR / "inref"
OUTREF_PATH = MUGJ_DIR / "outref" / "mugj.txt"
DRIVER_PATH = MUGJ_DIR / "u_inref" / "mugj.csh"


# =============================================================================
# Driver Parsing
# =============================================================================


def parse_driver() -> list[tuple[str, str]]:
    """Parse the mugj driver script to get routine execution order.

    Returns:
        List of (label, routine_name) tuples in execution order
    """
    content = DRIVER_PATH.read_text()
    routines = []
    for line in content.splitlines():
        # Match: W !!,"LABEL" D ^ROUTINE
        match = re.match(r'^W\s+!!,"([^"]+)"\s+D\s+\^(\w+)', line.strip())
        if match:
            label, routine = match.groups()
            routines.append((label, routine))
    return routines


# =============================================================================
# Routine Loading and Transpilation
# =============================================================================


def discover_dependencies(source: str, inref_dir: Path) -> set[str]:
    """Discover external routine dependencies from source code.

    Args:
        source: MUMPS source code
        inref_dir: Directory containing .m files

    Returns:
        Set of routine names that are called via D ^ROUTINE
    """
    deps = set()
    # Find all DO ^ROUTINE calls (case-insensitive, abbreviated or full form)
    # Routine names: % alone, %followed by alphanumerics, or alpha followed by alphanumerics
    # Pattern: %\w* matches % or %1A or %FOO; [a-zA-Z]\w* matches V or V1 or ROUTINE
    for match in re.finditer(
        r"\bD(?:O)?\s+\^(%\w*|[a-zA-Z]\w*)", source, re.IGNORECASE
    ):
        routine_name = match.group(1)
        if (inref_dir / f"{routine_name}.m").exists():
            deps.add(routine_name)
    # Also find comma-separated routine calls: D ^A,^B,^C
    for match in re.finditer(r",\^(%\w*|[a-zA-Z]\w*)", source, re.IGNORECASE):
        routine_name = match.group(1)
        if (inref_dir / f"{routine_name}.m").exists():
            deps.add(routine_name)
    # Also find GOTO ^ROUTINE calls (case-insensitive, abbreviated or full form)
    for match in re.finditer(
        r"\bG(?:OTO)?\s+\^(%\w*|[a-zA-Z]\w*)", source, re.IGNORECASE
    ):
        routine_name = match.group(1)
        if (inref_dir / f"{routine_name}.m").exists():
            deps.add(routine_name)
    return deps


def load_all_routines(
    driver_routines: list[tuple[str, str]],
    *,
    verbose: bool = True,
) -> dict[str, str]:
    """Transpile all routines and their dependencies.

    Args:
        driver_routines: List of (label, routine_name) from driver
        verbose: If True, print progress to stderr

    Returns:
        Dict mapping routine name to generated Python code
    """
    import time

    modules: dict[str, str] = {}
    to_process = set(routine for _, routine in driver_routines)
    processed = set()

    if verbose:
        print(
            f"Transpiling {len(to_process)} driver routines (+ dependencies)...",
            file=sys.stderr,
        )

    start_time = time.time()
    count = 0

    while to_process:
        routine = to_process.pop()
        if routine in processed:
            continue
        processed.add(routine)

        source_file = INREF_DIR / f"{routine}.m"
        if not source_file.exists():
            if verbose:
                print(f"  [{count + 1}] {routine}... FILE NOT FOUND", file=sys.stderr)
            continue

        count += 1
        if verbose:
            print(f"  [{count}] {routine}...", end="", file=sys.stderr, flush=True)
        routine_start = time.time()

        source = source_file.read_text()
        try:
            python_code = generate_python(source)
            modules[routine] = python_code

            if verbose:
                print(f" {time.time() - routine_start:.2f}s", file=sys.stderr)

            # Discover and queue dependencies
            deps = discover_dependencies(source, INREF_DIR)
            for dep in deps:
                if dep not in processed:
                    to_process.add(dep)
        except Exception as e:
            # Log but continue - some routines may use unsupported features
            if verbose:
                print(f" ERROR: {e}", file=sys.stderr)
            else:
                print(f"Warning: Failed to transpile {routine}: {e}")

    if verbose:
        print(
            f"  Total: {len(modules)} routines in {time.time() - start_time:.2f}s",
            file=sys.stderr,
        )

    return modules

    return modules


# =============================================================================
# Outref Loading
# =============================================================================


def load_expected_output() -> str:
    """Load and normalize the expected output from outref.

    Removes YDB infrastructure (preamble, prompts) but preserves
    all whitespace including form feeds since serial execution matches YDB.

    Returns:
        Normalized expected output string
    """
    raw_content = OUTREF_PATH.read_text()

    lines = []
    in_suspended = False
    found_first_prompt = False

    # YDB infrastructure markers to strip
    path_markers = frozenset(
        [
            "##TEST_PATH##",
            "##SOURCE_PATH##",
            "##REMOTE_TEST_PATH##",
            "##REMOTE_SOURCE_PATH##",
            "##IN_TEST_PATH##",
            "##TEST_AWK##",
        ]
    )

    for line in raw_content.splitlines():
        # Skip preamble before first YDB>
        if not found_first_prompt:
            if "YDB>" in line:
                found_first_prompt = True
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
        if any(marker in line for marker in path_markers):
            continue

        # Skip YDB> prompt lines
        if line.strip() == "YDB>":
            continue

        lines.append(line)

    return "\n".join(lines)


# =============================================================================
# Serial Execution
# =============================================================================


def execute_serial_suite(
    driver_routines: list[tuple[str, str]],
    modules: dict[str, str],
    *,
    verbose: bool = True,
    timeout_per_routine: float = 5.0,
) -> tuple[str, list[str]]:
    """Execute all routines serially with shared runtime state.

    Args:
        driver_routines: List of (label, routine_name) in execution order
        modules: Dict mapping routine name to generated Python code
        verbose: If True, print progress to stderr
        timeout_per_routine: Max seconds per routine before skipping

    Returns:
        Tuple of (full_output, list_of_errors)
    """
    import signal
    import time

    class TimeoutError(Exception):
        pass

    def timeout_handler(signum, frame):
        raise TimeoutError("Routine execution timed out")

    errors: list[str] = []

    # Create single runtime instance for all routines
    runtime = MUMPSRuntime()
    runtime._capture_output = True
    runtime.clear()

    # Inject all modules into sys.modules first
    # Use translated names for % routines since codegen emits `import _pct_FOO`
    if verbose:
        print(f"Injecting {len(modules)} modules...", file=sys.stderr)
    inject_start = time.time()
    for routine_name, code in modules.items():
        try:
            # Translate routine name to Python module name (%FOO → _pct_FOO)
            python_module_name = translate_name(routine_name)
            module = types.ModuleType(python_module_name)
            sys.modules[python_module_name] = module
            exec(code, module.__dict__)
        except Exception as e:
            errors.append(f"Module injection {routine_name}: {e}")
    if verbose:
        print(f"  Done in {time.time() - inject_start:.2f}s", file=sys.stderr)

    # Execute routines in driver order
    if verbose:
        print(f"Executing {len(driver_routines)} routines...", file=sys.stderr)

    for i, (label, routine) in enumerate(driver_routines):
        if routine not in modules:
            errors.append(f"Missing routine: {routine}")
            continue

        if verbose:
            print(
                f"  [{i + 1}/{len(driver_routines)}] {routine}...",
                end="",
                file=sys.stderr,
                flush=True,
            )

        routine_start = time.time()

        # Mimic driver's W !!,"label" before each D ^ROUTINE
        runtime.write(f"\n\n{label}")

        # Execute the routine with timeout
        try:
            # Use translated name to get module (%FOO → _pct_FOO)
            python_module_name = translate_name(routine)
            module = sys.modules.get(python_module_name)
            if module is None:
                errors.append(f"Module not found: {routine}")
                if verbose:
                    print(" MODULE NOT FOUND", file=sys.stderr)
                continue

            # When a routine has a labelless first line, codegen emits _preamble()
            # which executes line 1 before falling through to the named label.
            # D ^ROUTINE in MUMPS starts at line 1, so we call _preamble if present.
            entry_func = getattr(module, "_preamble", None)
            if entry_func is None:
                # Also translate the entry function name (%FOO → _pct_FOO)
                entry_func = getattr(module, python_module_name, None)
            if entry_func is None:
                errors.append(f"Entry point not found: {routine}")
                if verbose:
                    print(" NO ENTRY POINT", file=sys.stderr)
                continue

            if callable(entry_func):
                _scope: dict = {}
                # Set up timeout (Unix only)
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.setitimer(signal.ITIMER_REAL, timeout_per_routine)
                try:
                    entry_func(runtime, _scope=_scope)
                finally:
                    signal.setitimer(signal.ITIMER_REAL, 0)
                    signal.signal(signal.SIGALRM, old_handler)

            if verbose:
                print(f" {time.time() - routine_start:.2f}s", file=sys.stderr)
        except TimeoutError:
            errors.append(f"{routine}: TIMEOUT after {timeout_per_routine}s")
            if verbose:
                print(f" TIMEOUT ({timeout_per_routine}s)", file=sys.stderr)
        except Exception as e:
            # Log error but continue to next routine
            errors.append(f"{routine}: {type(e).__name__}: {e}")
            if verbose:
                print(f" ERROR: {type(e).__name__}", file=sys.stderr)

    return runtime.get_output(), errors


# =============================================================================
# Test
# =============================================================================


@pytest.mark.mugj
@pytest.mark.functional
class TestMugjSuite:
    """Full suite test for mugj, executing routines in YDB driver order."""

    def test_full_suite(self) -> None:
        """Execute all mugj routines serially and compare against outref.

        This test runs all routines in the exact order specified by the
        YDB driver script, preserving shared state across routines.
        """
        # Parse driver for routine order
        driver_routines = parse_driver()
        assert len(driver_routines) > 0, "No routines found in driver"

        # Load and transpile all routines
        modules = load_all_routines(driver_routines)
        assert len(modules) > 0, "No routines transpiled"

        # Load expected output
        expected = load_expected_output()
        assert len(expected) > 0, "No expected output loaded"

        # Execute suite
        actual, errors = execute_serial_suite(driver_routines, modules)

        # Report any execution errors (but don't fail just for those)
        if errors:
            print(f"\nExecution errors ({len(errors)}):")
            for err in errors[:10]:  # Show first 10
                print(f"  - {err}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more")

        # Compare outputs
        # Normalize line endings and strip trailing whitespace per line
        actual_lines = [line.rstrip() for line in actual.splitlines()]
        expected_lines = [line.rstrip() for line in expected.splitlines()]

        # Strip leading/trailing blank lines
        while actual_lines and not actual_lines[0]:
            actual_lines.pop(0)
        while actual_lines and not actual_lines[-1]:
            actual_lines.pop()
        while expected_lines and not expected_lines[0]:
            expected_lines.pop(0)
        while expected_lines and not expected_lines[-1]:
            expected_lines.pop()

        if actual_lines != expected_lines:
            # Generate diff for debugging
            import difflib

            diff = difflib.unified_diff(
                expected_lines,
                actual_lines,
                fromfile="expected (outref)",
                tofile="actual (m2py)",
                lineterm="",
            )
            diff_text = "\n".join(list(diff)[:100])  # First 100 lines of diff

            pytest.fail(
                f"\nOutput mismatch!\n"
                f"Expected lines: {len(expected_lines)}\n"
                f"Actual lines: {len(actual_lines)}\n"
                f"\nDiff (first 100 lines):\n{diff_text}"
            )


# =============================================================================
# Infrastructure Tests
# =============================================================================


class TestMugjInfrastructure:
    """Test the test infrastructure (driver parsing, transpilation, etc)."""

    def test_driver_parsed(self) -> None:
        """Driver script is parsed correctly."""
        routines = parse_driver()
        assert len(routines) == 72, f"Expected 72 routines, got {len(routines)}"
        assert routines[0] == ("V1WR", "V1WR")
        assert routines[-1] == ("VV2SS2", "VV2SS2")

    def test_outref_loads(self) -> None:
        """Outref file loads and has content."""
        expected = load_expected_output()
        assert len(expected) > 10000, "Expected substantial outref content"
        assert "V1WR" in expected
        assert "VV2SS2" in expected

    def test_routines_transpile(self) -> None:
        """All driver routines can be transpiled."""
        driver_routines = parse_driver()
        modules = load_all_routines(driver_routines)

        # Should have most routines (some may fail due to unsupported features)
        driver_names = {r for _, r in driver_routines}
        transpiled = set(modules.keys())
        missing = driver_names - transpiled

        # Allow up to 10% missing (unsupported features)
        max_missing = len(driver_routines) * 0.1
        assert len(missing) <= max_missing, (
            f"Too many routines failed to transpile: {missing}"
        )
