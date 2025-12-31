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
    # Run all suite tests (summary + validation)
    uv run pytest tests/integration/test_ydb_suites.py -v

    # Run just the summary report
    uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_all_suites_summary -v -s

    # Run a specific suite's validation
    uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_suite_parses[mugj] -v
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
# YDB Suite Tests - Single Test Class for All Suites
# =============================================================================


class TestYDBSuites:
    """Tests for parsing status across all YDB test suites.

    This single class handles all suite parsing validation. Use pytest
    parametrization to run specific suites:

        # All suites
        uv run pytest tests/integration/test_ydb_suites.py -v

        # Specific suite
        uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_suite_parses[mugj] -v
    """

    @pytest.fixture
    def parser(self):
        """Create a fresh parser instance."""
        return MUMPSParser()

    def test_all_suites_summary(self, parser):
        """Report parsing status across all test suites."""
        print("\n" + "=" * 70)
        print("YDBTest Suite Parsing Summary")
        print("=" * 70)
        print(f"{'Suite':<15} {'Parsed':>8} {'Clean':>8} {'Total':>8} {'Clean%':>8}")
        print("-" * 70)

        total_parsed = 0
        total_clean = 0
        total_files = 0

        for suite_name in sorted(TEST_SUITES.keys()):
            results = parse_suite(suite_name, parser)
            total_parsed += results.parsed_count
            total_clean += results.clean_count
            total_files += results.total_files

            status = (
                "✓"
                if results.clean_rate == 100
                else "○"
                if results.clean_rate >= 80
                else "✗"
            )
            print(
                f"{suite_name:<15} {results.parsed_count:>8} {results.clean_count:>8} "
                f"{results.total_files:>8} {results.clean_rate:>7.1f}% {status}"
            )

        print("-" * 70)
        overall_rate = (total_clean / total_files * 100) if total_files > 0 else 0
        print(
            f"{'TOTAL':<15} {total_parsed:>8} {total_clean:>8} "
            f"{total_files:>8} {overall_rate:>7.1f}%"
        )
        print("=" * 70)
        print("Legend: ✓ = 100% clean, ○ = ≥80% clean, ✗ = <80% clean")
        print("=" * 70)

    @pytest.mark.parametrize("suite_name", list(TEST_SUITES.keys()))
    def test_suite_parses(self, parser, suite_name):
        """Each suite should parse all files without exceptions.

        This is the authoritative test that all .m files in each suite
        can be parsed. Individual suite results are also shown in the
        summary test above.
        """
        results = parse_suite(suite_name, parser)

        # Verify directory exists and has files
        suite_dir = TEST_SUITES[suite_name]
        assert suite_dir.exists(), f"{suite_name} directory not found: {suite_dir}"
        assert results.total_files > 0, (
            f"{suite_name} directory should contain .m files"
        )

        # All files must parse without exceptions
        failed = results.files_that_failed
        if failed:
            details = "\n".join(f"  {r.filename}: {r.exception}" for r in failed[:10])
            if len(failed) > 10:
                details += f"\n  ... and {len(failed) - 10} more"
            pytest.fail(
                f"{suite_name}: {len(failed)}/{results.total_files} files "
                f"failed to parse:\n{details}"
            )
