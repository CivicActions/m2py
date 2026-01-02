"""Pytest configuration and fixtures for M2PY tests.

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
"""

import warnings
from pathlib import Path
from typing import Callable, Iterator

import pytest


# =============================================================================
# Pytest Marker Registration (T007)
# =============================================================================


def pytest_configure(config):
    """Register custom markers for spec-aligned test organization."""
    config.addinivalue_line("markers", "parser: Tests at textX grammar/parser level")
    config.addinivalue_line("markers", "asg: Tests at ASG semantic analysis level")
    config.addinivalue_line("markers", "codegen: Tests at Python code generation level")
    config.addinivalue_line(
        "markers", "stub: Placeholder test, expected to fail until implemented"
    )
    config.addinivalue_line("markers", "slow: Long-running test, skipped by default")
    config.addinivalue_line("markers", "pre1995: Tests pre-1995 MUMPS syntax")
    config.addinivalue_line("markers", "ydb: YottaDB-specific extension test")


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
