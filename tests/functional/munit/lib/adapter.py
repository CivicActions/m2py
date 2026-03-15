"""pytest adapter for running transpiled M-Unit tests.

Provides:
- ``transpile_and_execute()``: Transpile a MUMPS routine and run it via M-Unit

The adapter loads all MASH Utilities routines (framework + self-tests) and any
package-specific routines into a shared MUMPSRuntime, then invokes ``EN^%ut``
for each test routine and parses the output.
"""

from __future__ import annotations

import logging
import sys
import time
import types
from collections.abc import Callable
from pathlib import Path

from .models import (
    MUnitResult,
    TestRoutineConfig,
)
from .parser import parse_munit_output

logger = logging.getLogger(__name__)


# =============================================================================
# Exceptions
# =============================================================================


class MUnitTranspileError(Exception):
    """Raised when a MUMPS routine fails to transpile."""

    def __init__(self, routine: str, detail: str) -> None:
        self.routine = routine
        self.detail = detail
        super().__init__(f"Failed to transpile {routine}: {detail}")


class MUnitDependencyError(Exception):
    """Raised when a required dependency routine cannot be loaded."""

    def __init__(self, routine: str, missing_dep: str) -> None:
        self.routine = routine
        self.missing_dep = missing_dep
        super().__init__(f"{routine} requires {missing_dep} which could not be loaded")


# =============================================================================
# Module Name Helpers
# =============================================================================


def _mumps_name_to_python_module(routine_name: str) -> str:
    """Convert a MUMPS routine name to the Python module name used by codegen.

    MUMPS ``%``-prefixed routines become ``_pct_``-prefixed Python modules.

    Examples:
        ``%ut``  → ``_pct_ut``
        ``%utt1`` → ``_pct_utt1``
        ``MXMLBLD`` → ``MXMLBLD``
    """
    if routine_name.startswith("%"):
        return "_pct_" + routine_name[1:]
    return routine_name


def _filename_to_module_name(filename_stem: str) -> str:
    """Convert a ``.m`` filename stem to the Python module name.

    On disk, ``%ut`` is stored as ``ut.m`` (VistA-M convention) or
    ``_ut.m`` (OSEHRA convention).  Codegen generates ``import _pct_ut``.
    """
    if filename_stem.startswith("_"):
        return "_pct_" + filename_stem[1:]
    return filename_stem


# =============================================================================
# Routine Loading
# =============================================================================


def _load_routine(
    source_path: Path,
    routine_name: str,
    *,
    register_only: bool = False,
) -> tuple[str, types.ModuleType]:
    """Transpile a MUMPS source file and register it in sys.modules.

    Args:
        source_path: Path to the ``.m`` file.
        routine_name: MUMPS routine name (e.g. ``%ut``).
        register_only: If True, exec the code but do not call any entry point.

    Returns:
        Tuple of (python_code, module).

    Raises:
        MUnitTranspileError: If transpilation fails.
    """
    import warnings

    from m2py.codegen import generate_python

    source = source_path.read_text()
    try:
        # Suppress "UNRESOLVED GOTO" warnings — these are non-fatal
        # advisory messages.  With filterwarnings=["error"] in pyproject.toml
        # they'd be promoted to exceptions, killing transpilation of routines
        # that are otherwise perfectly functional.
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="UNRESOLVED GOTO")
            python_code = generate_python(source)
    except Exception as e:
        raise MUnitTranspileError(routine_name, str(e)) from e

    py_module_name = _mumps_name_to_python_module(routine_name)
    module = types.ModuleType(py_module_name)
    # Register early so @dataclass and other metaclasses can find the module
    # via sys.modules[cls.__module__] during exec().  On failure we clean up.
    sys.modules[py_module_name] = module
    try:
        # Temporarily raise the recursion limit for exec/compile.
        # Python's compiler is recursive and large generated routines
        # (e.g. DIP5) need more than 500 frames to compile, even though
        # the MUMPS runtime rarely nests beyond ~50 frames.
        _prev = sys.getrecursionlimit()
        sys.setrecursionlimit(max(_prev, 2000))
        try:
            exec(python_code, module.__dict__)  # noqa: S102
        finally:
            sys.setrecursionlimit(_prev)
    except Exception as e:
        del sys.modules[py_module_name]
        raise MUnitTranspileError(routine_name, f"exec failed: {e}") from e

    # Also register under the MUMPS name (used by runtime._get_module_safe)
    sys.modules[routine_name] = module

    return python_code, module


def load_mash_routines(
    mash_routines_dir: Path,
) -> dict[str, types.ModuleType]:
    """Load all MASH Utilities routines (M-Unit framework + self-tests).

    This must be called before any M-Unit test execution so that cross-routine
    calls (``D EN^%ut``, ``D CHKTF^%ut``, etc.) can resolve.

    Args:
        mash_routines_dir: Path to MASH Utilities Routines directory

    Returns:
        Dict mapping routine name → module.
    """
    # Load order matters: framework first, then tests
    routine_files = [
        "ut.m",
        "ut1.m",  # Framework
        "utt1.m",
        "utt2.m",
        "utt3.m",
        "utt4.m",
        "utt5.m",
        "utt6.m",
        "utt7.m",
        "uttcovr.m",  # Self-tests
        "utcover.m",  # Coverage utility
    ]

    modules: dict[str, types.ModuleType] = {}
    for filename in routine_files:
        source_path = mash_routines_dir / filename
        if not source_path.exists():
            logger.warning("Routine file not found: %s", source_path)
            continue

        # Derive MUMPS routine name: ut.m → %ut, utt1.m → %utt1
        stem = source_path.stem
        routine_name = f"%{stem}"

        try:
            _, module = _load_routine(source_path, routine_name)
            modules[routine_name] = module
            logger.debug("Loaded %s from %s", routine_name, source_path)
        except MUnitTranspileError:
            logger.exception("Failed to load %s", routine_name)

    return modules


def load_package_routines(
    package_dir: Path,
    routine_names: list[str] | None = None,
) -> dict[str, types.ModuleType]:
    """Load routines from a VistA package directory.

    Loads all ``.m`` files in the directory, or only those in *routine_names*
    if specified.

    Args:
        package_dir: Path to a directory containing ``.m`` files.
        routine_names: Optional list of routine names to load.

    Returns:
        Dict mapping routine name → module.
    """
    modules: dict[str, types.ModuleType] = {}

    m_files = sorted(package_dir.glob("*.m"))
    for source_path in m_files:
        stem = source_path.stem
        # Determine MUMPS routine name
        if stem.startswith("_"):
            routine_name = "%" + stem[1:]
        else:
            routine_name = stem

        if routine_names is not None and routine_name not in routine_names:
            continue

        try:
            _, module = _load_routine(source_path, routine_name)
            modules[routine_name] = module
        except MUnitTranspileError:
            logger.exception("Failed to load %s", routine_name)

    return modules


# =============================================================================
# I/O state cleanup
# =============================================================================


def _reset_io(runtime: "MUMPSRuntime") -> None:  # noqa: F821
    """Close non-principal devices and reset $IO to $PRINCIPAL.

    After a test routine runs, it may have left file devices open or
    switched $IO to a non-principal device (e.g. via OPEN/USE).  This
    causes subsequent tests to fail with ``UnsupportedOperation: not
    writable`` when they try to WRITE via a stale device.
    """
    principal = runtime._principal_device
    # Close all non-principal devices in the device table
    to_close = [
        name for name, dev in runtime._device_table.items() if dev is not principal
    ]
    for name in to_close:
        try:
            dev = runtime._device_table.pop(name)
            if hasattr(dev, "close"):
                dev.close()
        except Exception:
            logger.debug("Error closing device %s", name, exc_info=True)
    # Reset current device to principal
    runtime._current_device = principal


class _ResolvedEntry:
    """Result of resolving a MUMPS invocation string to a callable.

    Attributes:
        func: The Python function to call.
        args: List of MArray arguments to pass as positional args.
        description: Human-readable description for logging.
    """

    __slots__ = ("func", "args", "description")

    def __init__(
        self, func: Callable, args: list | None = None, description: str = ""
    ) -> None:
        self.func = func
        self.args = args or []
        self.description = description


def _resolve_entry_function(
    module: types.ModuleType | None,
    invocation: str,
    routine_name: str,
) -> _ResolvedEntry | None:
    """Determine the Python function to call from a MUMPS invocation string.

    Handles the common invocation patterns found in M-Unit TestList files:

    - ``D ^ROUTINE``              → module._entry_function
    - ``D LABEL^ROUTINE``         → module.LABEL
    - ``D EN^%ut("ROUTINE")``     → %ut.EN with routine name as argument
    - ``D LABEL^ROUTINE("args")`` → LABEL on target with string args

    For the ``D EN^%ut("ROUTINE")`` pattern, this correctly resolves to the
    ``EN`` label on the ``%ut`` framework module and passes the routine name
    as the first argument.  This is critical because many test routines
    (``%utt2``, ``%utt3``, etc.) are designed to be invoked *by* the
    framework, not to self-invoke it from their first line.

    Args:
        module: The transpiled Python module for the routine.
        invocation: MUMPS invocation string (e.g. "D TEST^MXMLBLD").
        routine_name: Routine name for logging.

    Returns:
        A _ResolvedEntry with the callable and arguments, or None if not found.
    """
    import re

    from m2py.runtime import MArray

    # Pattern: D LABEL^%ut("ROUTINE"[,verb[,break]])  — M-Unit framework call
    m = re.match(
        r'D\s+(\w+)\^%ut\(\s*"([^"]+)"(?:\s*,\s*(\d+))?(?:\s*,\s*(\d+))?\s*\)',
        invocation,
    )
    if m:
        label = m.group(1)
        target_routine = m.group(2)
        verbosity = m.group(3)
        brk = m.group(4)

        # Look up the label on the %ut framework module
        ut_module = sys.modules.get("_pct_ut")
        if ut_module is None:
            logger.error("Cannot resolve %s — %%ut framework not loaded", invocation)
            return None

        func = getattr(ut_module, label, None)
        if func is None:
            logger.error("Label %s not found in %%ut", label)
            return None

        # Build MArray arguments matching EN(%utRNAM,%utVERB,%utBREAK)
        args: list[MArray] = []
        _rnam = MArray()
        _rnam.value = target_routine
        args.append(_rnam)

        if verbosity is not None:
            _verb = MArray()
            _verb.value = verbosity
            args.append(_verb)

        if brk is not None:
            _brk = MArray()
            _brk.value = brk
            args.append(_brk)

        logger.debug(
            "Resolved %s → %%ut.%s(%s) (framework call)",
            invocation,
            label,
            target_routine,
        )
        return _ResolvedEntry(
            func=func,
            args=args,
            description=f"%ut.{label}({target_routine})",
        )

    if module is None:
        return None

    # Pattern: D LABEL^ROUTINE  (label call)
    m = re.match(r"D\s+(\w+)\^", invocation)
    if m:
        label = m.group(1)
        func = getattr(module, label, None)
        if func is not None:
            logger.debug(
                "Resolved %s → %s.%s (label call)", invocation, routine_name, label
            )
            return _ResolvedEntry(func=func, description=f"{routine_name}.{label}")
        # Label not found — fall through to _entry_function
        logger.warning(
            "Label %s not found in %s, falling back to _entry_function",
            label,
            routine_name,
        )

    # Default: call _entry_function (routine's first label)
    func = getattr(module, "_entry_function", None)
    if func is not None:
        logger.debug("Resolved %s → %s._entry_function", invocation, routine_name)
        return _ResolvedEntry(func=func, description=f"{routine_name}._entry_function")
    return None


# =============================================================================
# Transpile and Execute
# =============================================================================


def transpile_and_execute(
    config: TestRoutineConfig,
    runtime: "MUMPSRuntime",  # noqa: F821 — imported at call time
) -> MUnitResult:
    """Transpile a test routine and execute it through the M-Unit framework.

    Calls the test routine's own entry function (``D ^ROUTINE``), which
    typically runs a preamble (setting IO, DT via ``DT^DICRW``, etc.) and
    then invokes ``EN^%ut`` internally.  This matches the real MUMPS
    invocation where the preamble sets kernel variables before M-Unit
    discovers and calls individual ``@TEST`` entry points.

    Args:
        config: Routine configuration (name, package, source path, etc.)
        runtime: Shared MUMPSRuntime instance.

    Returns:
        Parsed MUnitResult from the M-Unit framework output.
    """
    from m2py.runtime import run_with_goto_support

    routine_name = config.routine_name
    py_module_name = _mumps_name_to_python_module(routine_name)

    # Ensure the test routine is loaded
    if py_module_name not in sys.modules:
        if not config.source_path or not Path(config.source_path).exists():
            return MUnitResult(
                routine=routine_name,
                package=config.package_name,
                status="error",
                error_message=f"Source not found: {config.source_path}",
            )
        try:
            _load_routine(Path(config.source_path), routine_name)
        except MUnitTranspileError as e:
            return MUnitResult(
                routine=routine_name,
                package=config.package_name,
                status="error",
                error_message=str(e),
            )

    # Ensure M-Unit framework is loaded
    ut_module = sys.modules.get("_pct_ut")
    if ut_module is None:
        return MUnitResult(
            routine=routine_name,
            package=config.package_name,
            status="error",
            error_message="%ut framework not loaded — call load_mash_routines() first",
        )

    # Get the test module's entry function — this runs the preamble
    # (IO, DT^DICRW, etc.) and calls EN^%ut internally.
    test_module = sys.modules.get(py_module_name)

    # Determine the correct entry point from the invocation pattern:
    #   D ^ROUTINE             → _entry_function (routine's first label)
    #   D LABEL^ROUTINE        → LABEL function within the module
    #   D EN^%ut("NAME")       → %ut.EN with routine name as argument
    resolved = _resolve_entry_function(test_module, config.invocation, routine_name)
    if resolved is None:
        return MUnitResult(
            routine=routine_name,
            package=config.package_name,
            status="error",
            error_message=f"Cannot resolve entry function for {config.invocation}",
        )

    # Clear output buffer and execute
    runtime.clear()

    # Release any locks left over from a previous test (real backends only).
    # InMemory locks always succeed; on YDB/IRIS stale locks from crashed
    # tests can block subsequent LOCK attempts (e.g., L +^TMP("MXMLDOM",$J):5
    # in EN^MXMLDOM) causing cascading failures.
    runtime.globals.unlock_all()

    # Reset I/O state: close any file devices left open by previous tests
    # and switch back to $PRINCIPAL.  Without this, a test that OPENs a file
    # device (or changes $IO) can pollute the runtime for subsequent tests.
    _reset_io(runtime)

    start = time.monotonic()
    try:
        # Bootstrap VistA Kernel standard variables that routines expect:
        #   U = "^"  — piece delimiter, set by Kernel during MUMPS login
        from m2py.runtime import MArray

        scope: dict[str, MArray] = {}
        _u = MArray()
        _u.value = "^"
        scope["U"] = _u

        # Call the resolved entry function.
        #
        # For D ^ROUTINE or D LABEL^ROUTINE: calls the routine's own
        # entry point directly (runs preamble, then invokes EN^%ut
        # internally).
        #
        # For D EN^%ut("ROUTINE"): calls the %ut framework's EN label
        # directly with the routine name as argument.  This is the
        # correct invocation for routines like %utt2, %utt3 that are
        # designed to be *called by* the framework, not to self-invoke.
        if resolved.args:
            run_with_goto_support(
                resolved.func,
                runtime,
                scope,
                _args=resolved.args,
            )
        else:
            run_with_goto_support(
                resolved.func,
                runtime,
                scope,
            )
    except Exception as e:
        elapsed = time.monotonic() - start
        output = runtime.get_output()
        logger.debug("Exception running %s: %s", routine_name, e)
        # Try to parse partial output
        result = parse_munit_output(output, routine_name, config.package_name)
        if result.status == "skip":
            result.status = "error"
        result.error_message = f"Runtime exception: {type(e).__name__}: {e}"
        result.duration_seconds = elapsed
        result.raw_output = output
        return result
    elapsed = time.monotonic() - start
    output = runtime.get_output()

    result = parse_munit_output(output, routine_name, config.package_name)
    result.duration_seconds = elapsed
    result.raw_output = output
    return result
