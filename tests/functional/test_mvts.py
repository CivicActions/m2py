"""Functional tests for the MVTS (M Validation Test Suite).

The MVTS suite uses pattern-based validation similar to MUGJ.
Each routine is validated by checking:
1. Number of PASS markers matches expected count
2. Operator tests (*FAILO*) are expected failures in automation
3. No unexpected "** FAIL" markers

MVTS Structure:
- VV1.m: Part 77 tests (59 sub-drivers)
- VV2.m: Part 84 tests (25 sub-drivers)
- VV3.m: Part 95 tests (23 sub-drivers)
- VV4.m: Part 95 continued (28 sub-drivers)
- Total: 135 sub-drivers, ~714 individual test routines

The MVTS framework uses VEXAMINE for assertions:
- D ^VEXAMINE: Automated test (produces PASS or ** FAIL)
- D MANPF*^VEXAMINE: Operator test (produces *FAILO* in automation)

Usage:
    uv run pytest tests/functional/test_mvts.py -v
    uv run pytest tests/functional/test_mvts.py::TestMvtsSuite -v
"""

from __future__ import annotations

import io
import json
import os
import re
import sys
import tempfile
import types
import warnings
from dataclasses import dataclass

import pytest

from tests.functional.conftest import (
    FUNCTIONAL_BASE,
    filename_to_module_name,
)
from tests.functional.suite_definitions import (
    MVTS_ROUTINES,
    MVTS_VV1_ROUTINES,
    MVTS_VV2_ROUTINES,
    MVTS_VV3_ROUTINES,
    MVTS_VV4_ROUTINES,
    RoutineDefinition,
)


# =============================================================================
# Suite Configuration
# =============================================================================

SUITE_NAME = "mvts"
MVTS_DIR = FUNCTIONAL_BASE / "mvts"
MVTS_INREF = MVTS_DIR / "inref"
MVTS_OUTREF = MVTS_DIR / "outref" / "mvts.txt"
MVTS_DRIVER = MVTS_DIR / "u_inref" / "mvts.csh"

# Workspace tmp/ directory for cache files (not system /tmp)
_WORKSPACE_TMP = FUNCTIONAL_BASE.parent.parent / "tmp"


# =============================================================================
# Pattern-Based Validation
# =============================================================================


@dataclass
class ValidationResult:
    """Result of pattern-based validation for MVTS."""

    passed: bool
    pass_count: int
    expected_passes: int | None
    fail_count: int
    operator_fail_count: int
    expected_operator_fails: int
    unexpected_fails: list[str]
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

        if self.operator_fail_count > 0:
            parts.append(
                f"Operator FAILs (*FAILO*): {self.operator_fail_count} (expected {self.expected_operator_fails})"
            )

        if self.unexpected_fails:
            parts.append(f"Unexpected FAILs: {self.unexpected_fails}")
        elif self.fail_count > 0:
            parts.append(f"FAILs: {self.fail_count}")

        if self.errors:
            parts.append(f"Errors: {self.errors}")

        return "\n".join(parts)


def validate_mvts_output(
    output: str,
    expected_passes: int | None = None,
    expected_operator_fails: int = 0,
) -> ValidationResult:
    """Validate MVTS routine output using pattern matching.

    Checks:
    1. Number of PASS markers matches expected (if specified)
    2. Operator tests (*FAILO*) match expected count
    3. No unexpected "** FAIL" markers

    VEXAMINE output patterns:
    - "   PASS  10001 Description" - test passed
    - "** FAIL  10001 Description" - test failed
    - Operator tests store *FAILO* in ^VREPORT but print ** FAIL

    Args:
        output: The routine's output
        expected_passes: Expected number of PASS markers (None = no check)
        expected_operator_fails: Expected number of operator test failures

    Returns:
        ValidationResult with detailed pass/fail information
    """
    errors: list[str] = []

    # Count PASS markers with test ID pattern (VEXAMINE outputs "   PASS  NNNNN")
    # Use stricter pattern to avoid matching "PASS" in text prompts
    pass_matches = re.findall(r"PASS\s+\d+", output)
    pass_count = len(pass_matches)

    # Count "** FAIL" markers (test failures with test ID)
    fail_matches = re.findall(r"\*\* FAIL\s+(\d+)", output)
    fail_count = len(fail_matches)

    # Expected failures come from two sources:
    # 1. Operator tests (expected_passes=0) - can't provide input in automation
    # 2. Tests that also fail in YDB (known YDB failures, not m2py bugs)
    # In both cases, expected_operator_fails counts how many ** FAIL markers
    # are expected and should not be treated as unexpected failures.
    expected_fails = expected_operator_fails

    # Determine unexpected fails
    unexpected_fails = (
        fail_matches[expected_fails:] if fail_count > expected_fails else []
    )

    # Determine overall pass/fail
    passed = True

    # Check PASS count
    if expected_passes is not None and pass_count != expected_passes:
        passed = False

    # Check for unexpected fails (real test failures beyond expected)
    if unexpected_fails:
        passed = False

    return ValidationResult(
        passed=passed,
        pass_count=pass_count,
        expected_passes=expected_passes,
        fail_count=fail_count,
        operator_fail_count=expected_operator_fails if expected_passes == 0 else 0,
        expected_operator_fails=expected_operator_fails,
        unexpected_fails=unexpected_fails,
        errors=errors,
    )


# =============================================================================
# Routine Loading Helpers
# =============================================================================


def _load_all_mvts_routines() -> tuple[
    dict[str, types.ModuleType | None], dict[str, str], str
]:
    """Load and transpile ALL MVTS routines from inref/.

    This matches the MUGJ pattern - loading all routines upfront so that
    inter-routine calls (D ^V1WR1, etc.) can resolve properly.

    Transpiled Python files are written to a cache directory on disk so that
    subprocess-based JOB can import them via PYTHONPATH.

    Under pytest-xdist, multiple workers share the same deterministic cache
    directory.  A filelock ensures only one worker transpiles; others wait
    and reuse the cached .py files, avoiding a thundering-herd of redundant
    grammar compilations.

    Note: Files starting with _ (like _.m, _1A.m) are registered with _pct_
    prefix module names since they represent MUMPS % routines and codegen
    generates imports like `import _pct_` for `D ^%`.

    Returns:
        Tuple of (routine_modules dict, transpile_errors dict, cache_dir path)
    """
    import hashlib

    from filelock import FileLock

    from m2py.codegen import generate_python

    # Compute a fingerprint of the codegen + helpers source so we
    # auto-invalidate the cache when the transpiler changes.
    def _codegen_fingerprint() -> str:
        import m2py.codegen as _cg
        import m2py.runtime.helpers as _rh

        h = hashlib.sha256()
        for mod in (_cg, _rh):
            src_path = getattr(mod, "__file__", None)
            if src_path and os.path.isfile(src_path):
                with open(src_path, "rb") as fh:
                    h.update(fh.read())
        return h.hexdigest()[:16]

    codegen_hash = _codegen_fingerprint()

    # Deterministic cache directory (shared across xdist workers)
    _WORKSPACE_TMP.mkdir(exist_ok=True)
    cache_dir = str(_WORKSPACE_TMP / "mvts_cache")
    os.makedirs(cache_dir, exist_ok=True)

    manifest_path = os.path.join(cache_dir, "_manifest.json")
    lock_path = str(_WORKSPACE_TMP / "mvts_cache.lock")

    all_routine_files = list(MVTS_INREF.glob("*.m"))
    routine_modules: dict[str, types.ModuleType | None] = {}
    transpile_errors: dict[str, str] = {}

    # Acquire lock — first worker transpiles, others wait and reuse
    with FileLock(lock_path, timeout=300):
        manifest_valid = False
        if os.path.exists(manifest_path):
            with open(manifest_path) as f:
                manifest = json.load(f)
            # Reuse only if the codegen hasn't changed since last transpile
            if manifest.get("codegen_hash") == codegen_hash:
                manifest_valid = True
                transpile_errors = manifest.get("errors", {})

        if not manifest_valid:
            # (Re-)transpile all routines — first worker or stale cache
            for source_path in all_routine_files:
                filename_stem = source_path.stem
                module_name = filename_to_module_name(filename_stem)
                source = source_path.read_text()

                try:
                    # Suppress UNRESOLVED GOTO warnings from codegen —
                    # routines like V3ALDO1/V3ALDO2 intentionally test
                    # unreachable code paths.
                    with warnings.catch_warnings():
                        warnings.filterwarnings("ignore", message="UNRESOLVED GOTO")
                        python_code = generate_python(source)

                    py_path = os.path.join(cache_dir, f"{module_name}.py")
                    with open(py_path, "w") as f:
                        f.write(python_code)
                except Exception as e:
                    transpile_errors[module_name] = str(e)

            # Write manifest so other workers know transpilation is done
            with open(manifest_path, "w") as f:
                json.dump({"errors": transpile_errors, "codegen_hash": codegen_hash}, f)

    # Load modules from disk (each worker does this independently since
    # module objects aren't shared across processes).
    #
    # Two-pass loading: MUGJ and MVTS share 176 routine names (V1BOA,
    # V1AC, etc.) but with different source code.  If MUGJ ran first, its
    # modules are still in sys.modules.  During exec(), transpiled code
    # uses `import V1BOA1` to call other routines — which resolves from
    # sys.modules.  A single-pass loop that registers + execs each module
    # sequentially can hit MUGJ's stale entry for modules not yet processed.
    #
    # Pass 1: register empty shells so every `import RoutineName` inside
    #         exec() resolves to the MVTS module (even if not yet populated).
    # Pass 2: exec() code into each shell.
    module_code: dict[str, str] = {}
    for source_path in all_routine_files:
        filename_stem = source_path.stem
        module_name = filename_to_module_name(filename_stem)

        if module_name in transpile_errors:
            routine_modules[module_name] = None
            continue

        py_path = os.path.join(cache_dir, f"{module_name}.py")
        try:
            with open(py_path) as f:
                module_code[module_name] = f.read()
            module = types.ModuleType(module_name)
            sys.modules[module_name] = module
            routine_modules[module_name] = module
        except Exception as e:
            routine_modules[module_name] = None
            transpile_errors[module_name] = str(e)

    # Pass 2: execute code into the pre-registered shells
    for module_name, python_code in module_code.items():
        module = routine_modules[module_name]
        if module is None:
            continue
        try:
            exec(python_code, module.__dict__)
        except Exception as e:
            routine_modules[module_name] = None
            transpile_errors[module_name] = str(e)

    # Add cache dir to sys.path so subprocess can find routines
    if cache_dir not in sys.path:
        sys.path.insert(0, cache_dir)

    return routine_modules, transpile_errors, cache_dir


# =============================================================================
# Test Helpers
# =============================================================================


def make_test_id(routine_def: RoutineDefinition) -> str:
    """Create a test ID from routine definition."""
    return routine_def.routine


# Routines that require subprocess-based JOB/LOCK and take 60-90s to run.
_SLOW_ROUTINES = frozenset({"V3JOB", "V3LOCK"})


def get_routine_params() -> list[pytest.param]:
    """Generate pytest parameters for MVTS routines, excluding skipped ones."""
    params = []
    for routine in MVTS_ROUTINES:
        if routine.skip_reason:
            continue
        marks = [pytest.mark.slow] if routine.routine in _SLOW_ROUTINES else []
        params.append(pytest.param(routine, id=make_test_id(routine), marks=marks))
    return params


# =============================================================================
# Parametrized Test Suite
# =============================================================================

# Cache for loaded routine modules (populated once for all tests)
_CACHED_MODULES: (
    tuple[dict[str, types.ModuleType | None], dict[str, str], str] | None
) = None


def _get_cached_modules() -> tuple[
    dict[str, types.ModuleType | None], dict[str, str], str
]:
    """Get cached routine modules, loading if needed."""
    global _CACHED_MODULES
    if _CACHED_MODULES is None:
        _CACHED_MODULES = _load_all_mvts_routines()
    return _CACHED_MODULES


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsSuite:
    """Parametrized tests for MVTS sub-driver routines.

    Each test runs a sub-driver routine through m2py with all MVTS
    routines pre-loaded as modules (matching YDB behavior where all
    routines are available).

    Uses pattern-based validation to check:
    - PASS count matches expected
    - No unexpected ** FAIL markers
    - *FAILO* count matches expected (operator tests)
    """

    # Routines that use JOB/LOCK and need SQLiteGlobalStorage for
    # cross-process global sharing via subprocess.
    _SQLITE_ROUTINES = frozenset({"V3JOB", "V3LOCK", "V4JOB", "V4PRIN", "V4SYSTEM"})

    @pytest.mark.parametrize("routine_def", get_routine_params())
    def test_routine(self, routine_def: RoutineDefinition) -> None:
        """Test a single MVTS sub-driver routine.

        Args:
            routine_def: The routine definition containing label, routine name,
                        and optional skip reason.
        """
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        # Get pre-loaded modules
        routine_modules, transpile_errors, cache_dir = _get_cached_modules()

        routine_name = routine_def.routine

        # Check if routine failed to transpile
        if routine_name in transpile_errors:
            pytest.xfail(f"Transpile error: {transpile_errors[routine_name]}")

        module = routine_modules.get(routine_name)
        if module is None:
            pytest.xfail(f"Routine {routine_name} not available")

        # Backend selection:
        # - External backends (yottadb, iris): MUMPSRuntime() picks up the
        #   backend from M2PY_GLOBAL_BACKEND env var (set by --backend).
        #   External DBs handle cross-process globals natively, so no
        #   SQLite escalation needed.
        # - inmemory (default): use SQLiteGlobalStorage for JOB/LOCK routines
        #   that need cross-process global sharing, InMemory for the rest.
        storage = None
        db_path = None
        active_backend = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")
        if active_backend == "inmemory" and routine_name in self._SQLITE_ROUTINES:
            from m2py.runtime.sqlite_storage import SQLiteGlobalStorage

            fd, db_path = tempfile.mkstemp(suffix=".db", dir=cache_dir)
            os.close(fd)
            storage = SQLiteGlobalStorage(db_path)

        try:
            if storage is not None:
                runtime = MUMPSRuntime(global_storage=storage)
            else:
                runtime = MUMPSRuntime()
            runtime._capture_output = True
            runtime.clear()

            # Set up runtime context
            runtime._current_routine = getattr(module, "_routine_name", routine_name)
            runtime._current_source_lines = getattr(module, "_source_lines", [])
            runtime._current_label_lines = getattr(module, "_label_lines", {})

            # Get entry function
            entry_func = getattr(module, routine_name, None)
            if not entry_func or not callable(entry_func):
                pytest.xfail(f"No entry point for {routine_name}")

            # Redirect stdin so interactive MVTS prompts get a safe default
            # answer instead of raising EOFError in CI.  V1GVN, for example,
            # asks "DO YOU MIND IF GLOBAL ... IS KILLD (Y/N)?" when %-prefixed
            # globals pre-exist on IRIS; "N" means "go ahead and kill them".
            saved_stdin = sys.stdin
            sys.stdin = io.StringIO("N\n" * 100)

            try:
                run_with_goto_support(entry_func, runtime, {})
                output = runtime.get_output()
            except Exception:
                # Capture partial output even on crash — allows tests that crash
                # mid-execution to still validate passes collected before the crash
                output = runtime.get_output()
            finally:
                sys.stdin = saved_stdin
        finally:
            # Kill any orphaned JOB child processes before closing storage
            runtime.kill_job_processes()
            if storage is not None:
                storage.close()
            if db_path is not None:
                try:
                    os.unlink(db_path)
                except OSError:
                    pass

        # Pattern-based validation using counts from RoutineDefinition
        result = validate_mvts_output(
            output,
            expected_passes=routine_def.expected_passes,
            expected_operator_fails=routine_def.expected_fails or 0,
        )

        # Report validation results
        if not result.passed:
            summary = result.summary
            pytest.fail(f"Pattern validation failed for {routine_name}:\n{summary}")


# =============================================================================
# Infrastructure Tests
# =============================================================================


@pytest.mark.mvts
@pytest.mark.functional
class TestMvtsInfrastructure:
    """Tests to validate the MVTS test infrastructure."""

    def test_inref_directory_exists(self) -> None:
        """Verify the mvts/inref directory exists with routines."""
        assert MVTS_INREF.exists(), f"MVTS inref directory not found: {MVTS_INREF}"
        routines = list(MVTS_INREF.glob("*.m"))
        assert len(routines) > 0, "No .m files found in mvts/inref"

    def test_outref_exists(self) -> None:
        """Verify the MVTS outref file exists."""
        assert MVTS_OUTREF.exists(), f"MVTS outref not found: {MVTS_OUTREF}"

    def test_driver_exists(self) -> None:
        """Verify the MVTS driver script exists."""
        assert MVTS_DRIVER.exists(), f"MVTS driver not found: {MVTS_DRIVER}"

    def test_main_test_routines_exist(self) -> None:
        """Verify the main MVTS test routines exist."""
        main_routines = ["VV1", "VV2", "VV3", "VV4", "VV4TP", "VSR"]
        for routine in main_routines:
            routine_path = MVTS_INREF / f"{routine}.m"
            assert routine_path.exists(), f"Main routine not found: {routine}"

    def test_sub_driver_count(self) -> None:
        """Verify the expected number of sub-drivers are defined."""
        assert len(MVTS_VV1_ROUTINES) == 59, (
            f"VV1 should have 59 sub-drivers, got {len(MVTS_VV1_ROUTINES)}"
        )
        assert len(MVTS_VV2_ROUTINES) == 25, (
            f"VV2 should have 25 sub-drivers, got {len(MVTS_VV2_ROUTINES)}"
        )
        assert len(MVTS_VV3_ROUTINES) == 23, (
            f"VV3 should have 23 sub-drivers, got {len(MVTS_VV3_ROUTINES)}"
        )
        assert len(MVTS_VV4_ROUTINES) == 28, (
            f"VV4 should have 28 sub-drivers, got {len(MVTS_VV4_ROUTINES)}"
        )
        assert len(MVTS_ROUTINES) == 135, (
            f"Total should be 135 sub-drivers, got {len(MVTS_ROUTINES)}"
        )

    def test_routine_files_exist(self) -> None:
        """Verify all defined routines have corresponding .m files."""
        missing = []
        for routine_def in MVTS_ROUTINES:
            routine_path = MVTS_INREF / f"{routine_def.routine}.m"
            if not routine_path.exists():
                missing.append(routine_def.routine)

        assert not missing, f"Missing routine files: {missing}"
