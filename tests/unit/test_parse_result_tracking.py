"""Unit tests for YDB suite parse result tracking.

Tests the ParseResult and SuiteParseResults classes used to track
parsing status across YDB test suites.
"""

import pytest
from unittest.mock import MagicMock

from tests.integration.test_ydb_suites import (
    ParseResult,
    SuiteParseResults,
    parse_suite,
)


class TestParseResult:
    """Tests for the ParseResult named tuple."""

    def test_successful_parse_no_errors(self):
        """A successful parse with no errors."""
        result = ParseResult("test.m", success=True, error_count=0, exception=None)
        assert result.filename == "test.m"
        assert result.success is True
        assert result.error_count == 0
        assert result.exception is None

    def test_successful_parse_with_errors(self):
        """A successful parse that contains parse_errors."""
        result = ParseResult("test.m", success=True, error_count=3, exception=None)
        assert result.success is True
        assert result.error_count == 3

    def test_failed_parse(self):
        """A parse that raised an exception."""
        result = ParseResult(
            "test.m", success=False, error_count=0, exception="Syntax error at line 5"
        )
        assert result.success is False
        assert result.error_count == 0
        assert result.exception == "Syntax error at line 5"


class TestSuiteParseResults:
    """Tests for the SuiteParseResults aggregate class."""

    def test_empty_suite(self):
        """An empty suite with no files."""
        results = SuiteParseResults("empty", 0, 0, 0, [])
        assert results.suite_name == "empty"
        assert results.total_files == 0
        assert results.success_rate == 0.0
        assert results.clean_rate == 0.0
        assert results.files_with_errors == []
        assert results.files_that_failed == []

    def test_all_clean(self):
        """All files parsed cleanly with no errors."""
        results = SuiteParseResults(
            "clean_suite",
            total_files=3,
            parsed_count=3,
            clean_count=3,
            results=[
                ParseResult("a.m", True, 0, None),
                ParseResult("b.m", True, 0, None),
                ParseResult("c.m", True, 0, None),
            ],
        )
        assert results.success_rate == 100.0
        assert results.clean_rate == 100.0
        assert results.files_with_errors == []
        assert results.files_that_failed == []

    def test_mixed_results(self):
        """Mix of clean, with-errors, and failed files."""
        results = SuiteParseResults(
            "mixed_suite",
            total_files=5,
            parsed_count=4,
            clean_count=2,
            results=[
                ParseResult("clean1.m", True, 0, None),
                ParseResult("clean2.m", True, 0, None),
                ParseResult("errors1.m", True, 3, None),
                ParseResult("errors2.m", True, 1, None),
                ParseResult("failed.m", False, 0, "Parse failed"),
            ],
        )
        assert results.success_rate == 80.0  # 4/5 parsed
        assert results.clean_rate == 40.0  # 2/5 clean
        assert len(results.files_with_errors) == 2
        assert len(results.files_that_failed) == 1
        assert results.files_with_errors[0].filename == "errors1.m"
        assert results.files_that_failed[0].filename == "failed.m"

    def test_files_with_errors_property(self):
        """files_with_errors returns only parsed files with error_count > 0."""
        results = SuiteParseResults(
            "test",
            total_files=3,
            parsed_count=2,
            clean_count=1,
            results=[
                ParseResult("clean.m", True, 0, None),
                ParseResult("errors.m", True, 5, None),
                ParseResult("failed.m", False, 0, "Error"),
            ],
        )
        with_errors = results.files_with_errors
        assert len(with_errors) == 1
        assert with_errors[0].filename == "errors.m"
        assert with_errors[0].error_count == 5

    def test_files_that_failed_property(self):
        """files_that_failed returns only files where success=False."""
        results = SuiteParseResults(
            "test",
            total_files=4,
            parsed_count=2,
            clean_count=2,
            results=[
                ParseResult("ok1.m", True, 0, None),
                ParseResult("ok2.m", True, 0, None),
                ParseResult("fail1.m", False, 0, "Error 1"),
                ParseResult("fail2.m", False, 0, "Error 2"),
            ],
        )
        failed = results.files_that_failed
        assert len(failed) == 2
        assert failed[0].filename == "fail1.m"
        assert failed[1].filename == "fail2.m"


class TestParseSuite:
    """Tests for the parse_suite function."""

    def test_nonexistent_suite(self):
        """parse_suite returns empty results for unknown suite."""
        mock_parser = MagicMock()
        results = parse_suite("nonexistent_suite", mock_parser)
        assert results.total_files == 0
        assert results.parsed_count == 0
        assert results.clean_count == 0

    def test_parse_suite_with_indirection(self):
        """parse_suite correctly parses a real suite (indirection is small)."""
        from m2py.parser import MUMPSParser
        from tests.conftest import TEST_SUITES

        # Only run if indirection suite exists
        if "indirection" not in TEST_SUITES:
            pytest.skip("indirection suite not available")

        parser = MUMPSParser()
        results = parse_suite("indirection", parser)

        # Indirection suite should exist and have files
        assert results.total_files > 0
        # All files should parse (indirection suite is 100% clean)
        assert results.parsed_count == results.total_files
        # Verify results list matches totals
        assert len(results.results) == results.total_files

    def test_error_tracking_math(self):
        """Verify error tracking calculations are correct."""
        # Test with synthetic data to verify the math works
        results = SuiteParseResults(
            "test_suite",
            total_files=10,
            parsed_count=8,
            clean_count=5,
            results=[
                ParseResult("clean1.m", True, 0, None),
                ParseResult("clean2.m", True, 0, None),
                ParseResult("clean3.m", True, 0, None),
                ParseResult("clean4.m", True, 0, None),
                ParseResult("clean5.m", True, 0, None),
                ParseResult("errors1.m", True, 2, None),
                ParseResult("errors2.m", True, 1, None),
                ParseResult("errors3.m", True, 3, None),
                ParseResult("failed1.m", False, 0, "Error"),
                ParseResult("failed2.m", False, 0, "Error"),
            ],
        )
        # Verify the relationship: parsed - clean = files_with_errors
        expected_with_errors = results.parsed_count - results.clean_count
        assert len(results.files_with_errors) == expected_with_errors
        assert expected_with_errors == 3
        # Verify files_that_failed = total - parsed
        assert (
            len(results.files_that_failed) == results.total_files - results.parsed_count
        )
        assert len(results.files_that_failed) == 2
