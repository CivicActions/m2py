"""Integration tests for YottaDB test suite files.

Tests parsing of YDBTest validation files across all test suites:
- mugj: MUMPS User Group Japan validation suite (376 files)
- mvts: MUMPS Validation Test Suite (714 files)
- basic: Core language tests (107 files)
- merge: MERGE command tests (54 files)
- indirection: Indirection operator tests (9 files)
- m_commands: M command tests including Z-commands (27 files)
- io: I/O operation tests (116 files)
- tp: Transaction processing tests (109 files)
- triggers: Trigger tests (101 files)
- longname: Long variable name tests (34 files)
- unicode: Unicode handling tests (47 files)

Goal: 100% parse success across ALL suites with codegen-ready ASG (zero parse_errors).

Usage:
    # Run all file parsing tests
    uv run pytest tests/integration/test_ydb_suites.py -v

    # Run just the summary report
    uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_all_suites_summary -v -s --no-skip

    # Run a specific suite's files
    uv run pytest tests/integration/test_ydb_suites.py -k mugj -v
"""

from typing import NamedTuple

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MRoutine
from tests.conftest import TEST_SUITES


# =============================================================================
# Parse Result Tracking
# =============================================================================


class ParseResult(NamedTuple):
    """Result of parsing a single file."""

    filename: str
    success: bool  # True if parsed without exception
    error_count: int  # Number of parse_errors in the routine
    exception: str | None  # Exception message if failed


class SuiteParseResults(NamedTuple):
    """Aggregate results for a test suite."""

    suite_name: str
    total_files: int
    parsed_count: int  # Files that parsed (may have errors)
    clean_count: int  # Files with zero parse_errors
    results: list[ParseResult]

    @property
    def success_rate(self) -> float:
        """Percentage of files that parsed without exception."""
        return (
            (self.parsed_count / self.total_files * 100)
            if self.total_files > 0
            else 0.0
        )

    @property
    def clean_rate(self) -> float:
        """Percentage of files with zero parse_errors."""
        return (
            (self.clean_count / self.total_files * 100) if self.total_files > 0 else 0.0
        )

    @property
    def files_with_errors(self) -> list[ParseResult]:
        """Files that parsed but have parse_errors."""
        return [r for r in self.results if r.success and r.error_count > 0]

    @property
    def files_that_failed(self) -> list[ParseResult]:
        """Files that raised exceptions during parsing."""
        return [r for r in self.results if not r.success]


def parse_suite(suite_name: str, parser: MUMPSParser) -> SuiteParseResults:
    """Parse all .m files in a test suite and collect results.

    Args:
        suite_name: Name of the test suite (key in TEST_SUITES)
        parser: MUMPSParser instance to use

    Returns:
        SuiteParseResults with detailed parsing information
    """
    suite_dir = TEST_SUITES.get(suite_name)
    if suite_dir is None or not suite_dir.exists():
        return SuiteParseResults(suite_name, 0, 0, 0, [])

    m_files = sorted(suite_dir.glob("*.m"))
    results = []
    parsed_count = 0
    clean_count = 0

    for filepath in m_files:
        try:
            routine = parser.parse_file(filepath)
            if isinstance(routine, MRoutine):
                error_count = len(routine.parse_errors) if routine.parse_errors else 0
                results.append(ParseResult(filepath.name, True, error_count, None))
                parsed_count += 1
                if error_count == 0:
                    clean_count += 1
            else:
                results.append(
                    ParseResult(filepath.name, False, 0, "Did not return MRoutine")
                )
        except Exception as e:
            results.append(ParseResult(filepath.name, False, 0, str(e)[:200]))

    return SuiteParseResults(
        suite_name, len(m_files), parsed_count, clean_count, results
    )


# =============================================================================
# File Collection for Parametrization
# =============================================================================

# Files with intentionally invalid syntax (excluded from test collection)
KNOWN_INVALID_FILES = {
    "badcompile.m",  # triggers suite: contains "badcommand" to test compiler error handling
}


def _collect_all_m_files():
    """Collect all .m files from all test suites for parametrization.

    Files listed in KNOWN_INVALID_FILES are excluded as they contain
    intentionally invalid syntax for error handling tests.
    """
    files = []
    for suite_name, suite_dir in TEST_SUITES.items():
        if suite_dir.exists():
            for filepath in sorted(suite_dir.glob("*.m")):
                if filepath.name not in KNOWN_INVALID_FILES:
                    files.append((suite_name, filepath))
    return files


# Collect files at module load time for parametrization
_ALL_M_FILES = _collect_all_m_files()


# =============================================================================
# YDB Suite Tests
# =============================================================================


class TestYDBSuites:
    """Tests for parsing all .m files across YDB test suites.

    Each .m file is tested individually for better parallelization with
    pytest-xdist. Use pytest -k to filter by suite name:

        # All files
        uv run pytest tests/integration/test_ydb_suites.py -v

        # Specific suite
        uv run pytest tests/integration/test_ydb_suites.py -k mugj -v

        # Specific file
        uv run pytest tests/integration/test_ydb_suites.py -k "mugj/V1FN001" -v
    """

    @pytest.fixture(scope="class")
    def parser(self):
        """Shared parser instance for the test class."""
        return MUMPSParser()

    @pytest.mark.parametrize(
        "suite_name,filepath",
        _ALL_M_FILES,
        ids=[f"{s}/{f.name}" for s, f in _ALL_M_FILES],
    )
    def test_file_parses(self, parser, suite_name, filepath):
        """Each .m file should parse without exceptions.

        This is the authoritative test that all .m files in each suite
        can be parsed. Files are tested individually for better parallel
        execution with pytest-xdist.

        Files with intentionally invalid syntax (like badcompile.m) are
        excluded from test collection in _collect_all_m_files().
        """
        routine = parser.parse_file(filepath)
        assert isinstance(routine, MRoutine), f"Failed to parse {filepath.name}"
