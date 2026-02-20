"""Pytest configuration and fixtures for m2py tests.

Provides fixtures for loading MUMPS test files from multiple test suites:
- MUGJ: MUMPS User Group Japan validation suite (376 files)
- MVTS: MUMPS Validation Test Suite (714 files)
- basic: Core language tests (107 files)
- merge: MERGE command tests (54 files)
- indirection: Indirection operator tests (9 files)
- m_commands: M command tests including Z-commands (27 files)
- io: I/O operation tests (116 files)
- tp: Transaction processing tests (109 files)
- triggers: Trigger tests (101 files)
- longname: Long variable name tests (34 files)
- unicode: Unicode handling tests (47 files)

Supports pluggable global storage backends via ``--backend``:
- ``inmemory`` (default): Fast in-process storage
- ``sqlite``: Cross-process storage for JOB/LOCK tests
- ``yottadb``: YottaDB database backend (requires ``yottadb`` package)
- ``iris``: InterSystems IRIS backend (requires ``intersystems-iris`` package)

Usage::

    uv run pytest tests/ -o "addopts="                    # default (inmemory)
    uv run pytest tests/ -o "addopts=" --backend sqlite   # SQLite everywhere
    uv run pytest tests/ -o "addopts=" --backend yottadb  # YottaDB backend
"""

import warnings
from pathlib import Path
from typing import Callable, Iterator

import pytest


# =============================================================================
# Smart Defaults (replaces pyproject.toml addopts)
# =============================================================================


def _has_cli_opt(args: tuple, short: str, long: str) -> bool:
    """Check whether a CLI option was explicitly passed by the user.

    Handles short forms (``-n``, ``-n0``, ``-nauto``), long forms
    (``--numprocesses``, ``--numprocesses=4``), and the two-arg form
    (``-n 4``).
    """
    for arg in args:
        # Short flag: exact match or combined value (-n0, -nauto)
        if arg == short or (arg.startswith(short) and not arg.startswith("--")):
            return True
        # Long flag: exact match or with = (--numprocesses=4)
        if arg == long or arg.startswith(long + "="):
            return True
    return False


# =============================================================================
# Pytest Marker Registration (T007)
# =============================================================================


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    """Register custom markers, apply smart defaults, and propagate --backend."""
    config.addinivalue_line("markers", "parser: Tests at textX grammar/parser level")
    config.addinivalue_line("markers", "asg: Tests at ASG semantic analysis level")
    config.addinivalue_line("markers", "codegen: Tests at Python code generation level")
    config.addinivalue_line(
        "markers", "stub: Placeholder test, expected to fail until implemented"
    )
    config.addinivalue_line("markers", "slow: Long-running test, skipped by default")
    config.addinivalue_line("markers", "pre1995: Tests pre-1995 MUMPS syntax")
    config.addinivalue_line("markers", "ydb: YottaDB-specific extension test")

    # ── Smart defaults ────────────────────────────────────────────────
    # Formerly handled by addopts = "-n 4 -m 'not slow'" in
    # pyproject.toml.  Now applied programmatically so users never need
    # the awkward -o "addopts=" escape hatch.
    #
    # • -n 4   → parallel via pytest-xdist (skip if user passed -n)
    # • -m 'not slow' → skip slow-marked tests (skip if user passed -m)
    import os

    user_args = config.invocation_params.args

    if not _has_cli_opt(user_args, "-n", "--numprocesses"):
        if hasattr(config.option, "numprocesses"):  # xdist installed
            num_workers = os.cpu_count() or 1
            config.option.numprocesses = num_workers
            # xdist also needs dist mode enabled (defaults to "no"
            # when -n is absent from the CLI)
            if getattr(config.option, "dist", "no") == "no":
                config.option.dist = "load"
            # xdist requires tx (test execution environments) to be populated
            # with one entry per worker to actually create the workers
            if getattr(config.option, "tx", None) == []:
                config.option.tx = ["popen"] * num_workers

    if not _has_cli_opt(user_args, "-m", "--markexpr"):
        config.option.markexpr = "not slow"

    # ── Backend propagation ───────────────────────────────────────────
    # Propagate --backend to the M2PY_GLOBAL_BACKEND env var so that
    # MUMPSRuntime() picks up the backend automatically — including in
    # subprocess workers spawned by run_mumps().
    backend = config.getoption("--backend", default=None)
    if backend and backend != "inmemory":
        os.environ["M2PY_GLOBAL_BACKEND"] = backend


def pytest_addoption(parser):
    """Add --backend CLI option for selecting the global storage backend."""
    parser.addoption(
        "--backend",
        action="store",
        default="inmemory",
        choices=["inmemory", "sqlite", "yottadb", "iris"],
        help=(
            "Global storage backend for tests. "
            "Default: inmemory. "
            "Use 'yottadb' or 'iris' to validate against a real database."
        ),
    )


# =============================================================================
# Marker Validation Hook (T009)
# =============================================================================

# Directories that require category markers (parser, asg, codegen)
_SPEC_ALIGNED_DIRS = frozenset(["parser", "asg", "codegen"])

# Directories that do NOT require category markers (internal algorithms, tooling)
_NON_SPEC_DIRS = frozenset(["analysis", "meta", "cross_cutting"])


def pytest_collection_modifyitems(session, config, items):
    """Warn during migration if tests in spec-aligned directories lack category markers."""
    category_markers = {"parser", "asg", "codegen"}

    for item in items:
        # Get the path relative to tests/unit/
        try:
            rel_path = Path(item.fspath).relative_to(Path(__file__).parent / "unit")
            top_dir = rel_path.parts[0] if rel_path.parts else ""
        except (ValueError, IndexError):
            continue

        # Only check spec-aligned directories
        if top_dir not in _SPEC_ALIGNED_DIRS:
            continue

        # Check if item has any category marker
        item_markers = {m.name for m in item.iter_markers()}
        if not item_markers & category_markers:
            warnings.warn(
                f"Test '{item.nodeid}' missing category marker "
                f"(@pytest.mark.parser, @pytest.mark.asg, or @pytest.mark.codegen)",
                UserWarning,
                stacklevel=1,
            )


# =============================================================================
# Global Storage Backend Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def m2py_backend(request) -> str:
    """Return the --backend CLI option value (session-scoped).

    Values: 'inmemory', 'sqlite', 'yottadb', 'iris'.

    Usage::

        def test_something(m2py_backend):
            if m2py_backend == "yottadb":
                pytest.skip("Not supported on YottaDB")
    """
    return request.config.getoption("--backend")


def get_test_backend(config) -> str:
    """Get the --backend value from a pytest config object.

    Useful in module-level functions (like parametrize generators)
    that don't have access to fixtures.
    """
    return config.getoption("--backend", default="inmemory")


def make_storage(backend: str, *, db_path: str | None = None):
    """Create a GlobalStorageBackend for the given backend name.

    Args:
        backend: One of 'inmemory', 'sqlite', 'yottadb', 'iris'.
        db_path: Optional database path (used by sqlite backend).

    Returns:
        A GlobalStorageBackend instance.

    Raises:
        ImportError: If the requested backend package is not installed.
        ValueError: If the backend name is not recognized.
    """
    from m2py.runtime import get_global_storage

    if backend == "sqlite" and db_path:
        from m2py.runtime.sqlite_storage import SQLiteGlobalStorage

        return SQLiteGlobalStorage(db_path)
    return get_global_storage(backend)


def is_external_backend(backend: str) -> bool:
    """Return True if backend is an external database (not inmemory/sqlite)."""
    return backend not in ("inmemory", "sqlite")


# Base path for all functional test suites
FUNCTIONAL_BASE = Path(__file__).parent / "functional"

# Test suite directories
TEST_SUITES = {
    "mugj": FUNCTIONAL_BASE / "mugj" / "inref",
    "mvts": FUNCTIONAL_BASE / "mvts_inref",
    "basic": FUNCTIONAL_BASE / "basic_inref",
    "merge": FUNCTIONAL_BASE / "merge_inref",
    "indirection": FUNCTIONAL_BASE / "indirection_inref",
    "m_commands": FUNCTIONAL_BASE / "m_commands_inref",
    "io": FUNCTIONAL_BASE / "io_inref",
    "tp": FUNCTIONAL_BASE / "tp_inref",
    "triggers": FUNCTIONAL_BASE / "triggers_inref",
    "longname": FUNCTIONAL_BASE / "longname_inref",
    "unicode": FUNCTIONAL_BASE / "unicode_inref",
}

# Legacy constants for backward compatibility
MUGJ_BASE = FUNCTIONAL_BASE / "mugj"
MUGJ_INREF = MUGJ_BASE / "inref"
MUGJ_OUTREF = MUGJ_BASE / "outref"
MUGJ_U_INREF = MUGJ_BASE / "u_inref"


# =============================================================================
# Generic Test Suite Fixtures
# =============================================================================


def _make_suite_dir_fixture(suite_name: str):
    """Factory to create a fixture returning the path to a test suite directory."""

    @pytest.fixture
    def suite_dir() -> Path:
        return TEST_SUITES[suite_name]

    suite_dir.__doc__ = f"Return the path to the {suite_name} test suite directory."
    return suite_dir


def _make_suite_file_fixture(suite_name: str):
    """Factory to create a fixture for loading files from a test suite."""

    @pytest.fixture
    def suite_file() -> Callable[[str], str]:
        def _load_file(filename: str) -> str:
            file_path = TEST_SUITES[suite_name] / filename
            if not file_path.exists():
                raise FileNotFoundError(f"{suite_name} file not found: {file_path}")
            return file_path.read_text(encoding="utf-8", errors="replace")

        return _load_file

    suite_file.__doc__ = (
        f"Factory fixture to load a specific {suite_name} .m file by name."
    )
    return suite_file


def _make_suite_files_fixture(suite_name: str):
    """Factory to create a fixture for iterating over all files in a test suite."""

    @pytest.fixture
    def suite_files() -> Callable[[], Iterator[tuple[str, str]]]:
        def _iter_files():
            suite_dir = TEST_SUITES[suite_name]
            for path in sorted(suite_dir.glob("*.m")):
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                    yield path.name, content
                except Exception:
                    # Skip files that can't be read
                    continue

        return _iter_files

    suite_files.__doc__ = f"Factory fixture to iterate over all {suite_name} .m files."
    return suite_files


# =============================================================================
# MUGJ Test Suite Fixtures (Primary validation suite)
# =============================================================================


@pytest.fixture
def mugj_dir() -> Path:
    """Return the path to the MUGJ test suite directory."""
    return MUGJ_BASE


@pytest.fixture
def mugj_inref_dir() -> Path:
    """Return the path to the MUGJ inref directory containing .m files."""
    return MUGJ_INREF


@pytest.fixture
def mugj_file() -> Callable[[str], str]:
    """Factory fixture to load a specific MUGJ .m file by name.

    Usage:
        def test_parse_v1fora(mugj_file):
            source = mugj_file("V1FORA.m")
            # ... parse and validate
    """

    def _load_mugj_file(filename: str) -> str:
        file_path = MUGJ_INREF / filename
        if not file_path.exists():
            raise FileNotFoundError(f"MUGJ file not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    return _load_mugj_file


@pytest.fixture
def mugj_files() -> Callable[[], Iterator[tuple[str, str]]]:
    """Factory fixture to get an iterator over all MUGJ .m files."""

    def _iter_mugj_files():
        for path in sorted(MUGJ_INREF.glob("*.m")):
            yield path.name, path.read_text(encoding="utf-8")

    return _iter_mugj_files


# =============================================================================
# MVTS Test Suite Fixtures
# =============================================================================

mvts_inref_dir = _make_suite_dir_fixture("mvts")
mvts_file = _make_suite_file_fixture("mvts")
mvts_files = _make_suite_files_fixture("mvts")


# =============================================================================
# Basic Test Suite Fixtures
# =============================================================================

basic_inref_dir = _make_suite_dir_fixture("basic")
basic_file = _make_suite_file_fixture("basic")
basic_files = _make_suite_files_fixture("basic")


# =============================================================================
# Merge Test Suite Fixtures
# =============================================================================

merge_inref_dir = _make_suite_dir_fixture("merge")
merge_file = _make_suite_file_fixture("merge")
merge_files = _make_suite_files_fixture("merge")


# =============================================================================
# Indirection Test Suite Fixtures
# =============================================================================

indirection_inref_dir = _make_suite_dir_fixture("indirection")
indirection_file = _make_suite_file_fixture("indirection")
indirection_files = _make_suite_files_fixture("indirection")


# =============================================================================
# M Commands Test Suite Fixtures
# =============================================================================

m_commands_inref_dir = _make_suite_dir_fixture("m_commands")
m_commands_file = _make_suite_file_fixture("m_commands")
m_commands_files = _make_suite_files_fixture("m_commands")


# =============================================================================
# IO Test Suite Fixtures
# =============================================================================

io_inref_dir = _make_suite_dir_fixture("io")
io_file = _make_suite_file_fixture("io")
io_files = _make_suite_files_fixture("io")


# =============================================================================
# Transaction Processing Test Suite Fixtures
# =============================================================================

tp_inref_dir = _make_suite_dir_fixture("tp")
tp_file = _make_suite_file_fixture("tp")
tp_files = _make_suite_files_fixture("tp")


# =============================================================================
# Triggers Test Suite Fixtures
# =============================================================================

triggers_inref_dir = _make_suite_dir_fixture("triggers")
triggers_file = _make_suite_file_fixture("triggers")
triggers_files = _make_suite_files_fixture("triggers")


# =============================================================================
# Long Name Test Suite Fixtures
# =============================================================================

longname_inref_dir = _make_suite_dir_fixture("longname")
longname_file = _make_suite_file_fixture("longname")
longname_files = _make_suite_files_fixture("longname")


# =============================================================================
# Unicode Test Suite Fixtures
# =============================================================================

unicode_inref_dir = _make_suite_dir_fixture("unicode")
unicode_file = _make_suite_file_fixture("unicode")
unicode_files = _make_suite_files_fixture("unicode")


# =============================================================================
# External Calls Test Fixtures (Spec 008)
# =============================================================================

# Path to external call test fixtures
EXTERNAL_FIXTURES = Path(__file__).parent / "fixtures" / "external"


@pytest.fixture
def external_fixtures_path() -> Path:
    """Return the path to the external call test fixtures directory."""
    return EXTERNAL_FIXTURES


@pytest.fixture
def external_sys_path(tmp_path: Path) -> Iterator[Path]:
    """Fixture that adds external fixtures to sys.path for module imports.

    This fixture:
    1. Adds tests/fixtures/external/ to sys.path
    2. Yields the path for test use
    3. Removes the path and clears cached modules on cleanup

    Usage:
        def test_external_do(external_sys_path):
            # sys.path now includes external fixtures
            import ext2  # Can import transpiled external routines
    """
    import sys

    # Add fixtures directory to sys.path
    fixtures_str = str(EXTERNAL_FIXTURES)
    sys.path.insert(0, fixtures_str)

    yield EXTERNAL_FIXTURES

    # Cleanup: remove from sys.path
    if fixtures_str in sys.path:
        sys.path.remove(fixtures_str)

    # Clear any cached modules from fixtures directory
    to_remove = [
        name
        for name, mod in sys.modules.items()
        if hasattr(mod, "__file__")
        and mod.__file__
        and EXTERNAL_FIXTURES.as_posix() in mod.__file__
    ]
    for name in to_remove:
        del sys.modules[name]


@pytest.fixture
def external_file() -> Callable[[str], str]:
    """Factory fixture to load a specific external fixture .m file by name.

    Usage:
        def test_parse_ext1(external_file):
            source = external_file("ext1.m")
            # ... parse and validate
    """

    def _load_external_file(filename: str) -> str:
        file_path = EXTERNAL_FIXTURES / filename
        if not file_path.exists():
            raise FileNotFoundError(f"External fixture not found: {file_path}")
        return file_path.read_text(encoding="utf-8")

    return _load_external_file


# =============================================================================
# Legacy MUGJ-Specific Fixtures
# =============================================================================


@pytest.fixture
def v1fora_source(mugj_file) -> str:
    """Load V1FORA.m source - the primary FOR command test file."""
    return mugj_file("V1FORA.m")


@pytest.fixture
def v1fora1_source(mugj_file) -> str:
    """Load V1FORA1.m source - FOR command test cases part 1."""
    return mugj_file("V1FORA1.m")


@pytest.fixture
def v1fora2_source(mugj_file) -> str:
    """Load V1FORA2.m source - FOR command test cases part 2."""
    return mugj_file("V1FORA2.m")
