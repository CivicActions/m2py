"""Unit tests for M-Unit output parsing and TestList parsing."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from tests.functional.munit.lib.models import TestRoutineConfig
from tests.functional.munit.lib.parser import parse_munit_output, parse_testlist


class TestParseMUnitOutputPassing:
    """Tests for all-pass output parsing."""

    def test_simple_passing(self):
        raw = (
            ".........\n"
            "Ran 1 Routine(s), 5 Entry Tag(s)\n"
            "Checked 9 tests, with 0 failures and encountered 0 errors."
        )
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.status == "pass"
        assert result.total_tests == 9
        assert result.failures == 0
        assert result.errors == 0
        assert result.routines_ran == 1
        assert result.entry_tags == 5
        assert result.failure_details == []

    def test_singular_test(self):
        raw = (
            ".\n"
            "Ran 1 Routine(s), 1 Entry Tag(s)\n"
            "Checked 1 test, with 0 failure and encountered 0 error."
        )
        result = parse_munit_output(raw, "MXMLBLD", "M XML Parser")
        assert result.status == "pass"
        assert result.total_tests == 1

    def test_multiple_routines(self):
        raw = (
            "...............\n"
            "Ran 3 Routine(s), 10 Entry Tag(s)\n"
            "Checked 15 tests, with 0 failures and encountered 0 errors."
        )
        result = parse_munit_output(raw, "%utt6", "MASH Utilities")
        assert result.routines_ran == 3
        assert result.entry_tags == 10


class TestParseMUnitOutputFailures:
    """Tests for failure output parsing."""

    def test_chktf_failure(self):
        raw = (
            "...\n"
            "T1^%utt1 - Test 1 - Expected TRUE but got FALSE\n"
            "Ran 1 Routine(s), 3 Entry Tag(s)\n"
            "Checked 4 tests, with 1 failure and encountered 0 errors."
        )
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.status == "fail"
        assert result.total_tests == 4
        assert result.failures == 1
        assert result.errors == 0
        assert len(result.failure_details) == 1
        fd = result.failure_details[0]
        assert fd.entry_tag == "T1"
        assert fd.routine == "%utt1"
        assert fd.test_name == "Test 1"
        assert fd.message == "Expected TRUE but got FALSE"
        assert fd.kind == "failure"
        assert fd.expected is None
        assert fd.actual is None

    def test_chkeq_failure(self):
        raw = (
            "T1^%utt1 - Test 1 - <hello> vs <world> - Values differ\n"
            "Ran 1 Routine(s), 1 Entry Tag(s)\n"
            "Checked 1 test, with 1 failure and encountered 0 errors."
        )
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.failures == 1
        assert len(result.failure_details) == 1
        fd = result.failure_details[0]
        assert fd.expected == "hello"
        assert fd.actual == "world"
        assert fd.message == "Values differ"
        assert fd.kind == "failure"

    def test_chkeq_empty_values(self):
        raw = (
            "T1^%utt1 - Test 1 - <> vs <something> - Expected empty\n"
            "Checked 1 test, with 1 failure and encountered 0 errors."
        )
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        fd = result.failure_details[0]
        assert fd.expected == ""
        assert fd.actual == "something"

    def test_multiple_failures(self):
        raw = (
            ".\n"
            "T1^MXMLBLD - Build Test - <A> vs <B> - tag mismatch\n"
            "..\n"
            "T2^MXMLBLD - Parse Test - Expected TRUE but got FALSE\n"
            "Ran 1 Routine(s), 3 Entry Tag(s)\n"
            "Checked 4 tests, with 2 failures and encountered 0 errors."
        )
        result = parse_munit_output(raw, "MXMLBLD", "M XML Parser")
        assert result.failures == 2
        assert len(result.failure_details) == 2
        assert result.failure_details[0].entry_tag == "T1"
        assert result.failure_details[1].entry_tag == "T2"


class TestParseMUnitOutputErrors:
    """Tests for error output parsing."""

    def test_error_line(self):
        raw = (
            "T1^%utt1 - Test 1 - Error: 150374082,Z,%utt1+5^%utt1\n"
            "Ran 1 Routine(s), 1 Entry Tag(s)\n"
            "Checked 1 test, with 0 failures and encountered 1 error."
        )
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.errors == 1
        assert len(result.failure_details) == 1
        fd = result.failure_details[0]
        assert fd.kind == "error"
        assert fd.message == "150374082,Z,%utt1+5^%utt1"
        assert fd.entry_tag == "T1"

    def test_mixed_failures_and_errors(self):
        raw = (
            "T1^%utt1 - Test 1 - Expected TRUE but got FALSE\n"
            "..\n"
            "T3^%utt1 - Test 3 - Error: 150374082,Z,%utt1+10^%utt1\n"
            "Ran 1 Routine(s), 3 Entry Tag(s)\n"
            "Checked 4 tests, with 1 failure and encountered 1 error."
        )
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.failures == 1
        assert result.errors == 1
        assert len(result.failure_details) == 2
        assert result.failure_details[0].kind == "failure"
        assert result.failure_details[1].kind == "error"


class TestParseMUnitOutputEdgeCases:
    """Tests for error handling and edge cases."""

    def test_empty_output(self):
        result = parse_munit_output("", "%utt1", "MASH Utilities")
        assert result.status == "error"
        assert result.error_message == "No output captured"

    def test_whitespace_only(self):
        result = parse_munit_output("   \n  \n  ", "%utt1", "MASH Utilities")
        assert result.status == "error"
        assert result.error_message == "No output captured"

    def test_partial_output_no_summary(self):
        raw = "...\nT1^%utt1 - Test 1 - Something failed\n"
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.status == "error"
        assert result.error_message == "No summary line found in output"
        assert len(result.failure_details) == 1
        assert result.failure_details[0].test_name == "Test 1"

    def test_raw_output_preserved(self):
        raw = ".........\nChecked 9 tests, with 0 failures and encountered 0 errors."
        result = parse_munit_output(raw, "%utt1", "MASH Utilities")
        assert result.raw_output == raw

    def test_routine_and_package_preserved(self):
        raw = ".\nChecked 1 test, with 0 failures and encountered 0 errors."
        result = parse_munit_output(raw, "MXMLBLD", "M XML Parser")
        assert result.routine == "MXMLBLD"
        assert result.package == "M XML Parser"

    def test_dots_inline_with_failures(self):
        """M-Unit writes dots without newlines; test that dots mixed with failure lines parse."""
        raw = (
            "...T1^%utt4 - CHKEQ should fail - <hello> vs <world> - no failure message provided\n"
            "....\n"
            "Ran 1 Routine(s), 3 Entry Tag(s)\n"
            "Checked 8 tests, with 1 failure and encountered 0 errors."
        )
        result = parse_munit_output(raw, "%utt4", "MASH Utilities")
        assert result.failures == 1
        assert len(result.failure_details) == 1
        assert result.failure_details[0].expected == "hello"
        assert result.failure_details[0].actual == "world"


class TestParseTestList:
    """Tests for OSEHRA TestList file parsing."""

    def test_xml_parser_testlist(self):
        """Parse M XML Parser TestList (mix of D TAG^ROUTINE and D ^ROUTINE)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            # Create TestList
            testlist = tdir / "TestList"
            testlist.write_text(
                "D TEST^MXMLBLD\nD TEST^MXMLTMPT\nD TEST^MXMLPATT\nD ^MXMLDOMT\n"
            )
            # Create matching .m files
            for name in ["MXMLBLD", "MXMLTMPT", "MXMLPATT", "MXMLDOMT"]:
                (tdir / f"{name}.m").write_text(f"; {name}\n")

            configs = parse_testlist(str(testlist), "M XML Parser")
            assert len(configs) == 4
            assert all(isinstance(c, TestRoutineConfig) for c in configs)

            # Check routine names extracted correctly
            names = [c.routine_name for c in configs]
            assert "MXMLBLD" in names
            assert "MXMLTMPT" in names
            assert "MXMLPATT" in names
            assert "MXMLDOMT" in names

            # Check invocations preserved
            assert configs[0].invocation == "D TEST^MXMLBLD"
            assert configs[3].invocation == "D ^MXMLDOMT"

            # Check tier assigned from package name
            assert all(c.tier == 2 for c in configs)

            # Check package name
            assert all(c.package_name == "M XML Parser" for c in configs)

    def test_simple_do_routine(self):
        """Parse TestList with D ^ROUTINE entries (Scheduling, VA FileMan style)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            testlist = tdir / "TestList"
            testlist.write_text("D ^ZZUTGETAPPT\nD ^ZZRGUSD1\n")
            (tdir / "ZZUTGETAPPT.m").write_text("; test\n")
            (tdir / "ZZRGUSD1.m").write_text("; test\n")

            configs = parse_testlist(str(testlist), "Scheduling")
            assert len(configs) == 2
            assert configs[0].routine_name == "ZZUTGETAPPT"
            assert configs[1].routine_name == "ZZRGUSD1"
            assert all(c.tier == 4 for c in configs)

    def test_missing_source_file(self):
        """Missing .m source file produces config with empty source_path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            testlist = tdir / "TestList"
            testlist.write_text("D ^MISSING\n")

            configs = parse_testlist(str(testlist), "VA FileMan")
            assert len(configs) == 1
            assert configs[0].source_path == ""
            assert configs[0].routine_name == "MISSING"

    def test_missing_testlist(self):
        """Missing TestList file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parse_testlist("/nonexistent/TestList", "test")

    def test_empty_and_comment_lines(self):
        """Empty lines and comment lines are skipped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tdir = Path(tmpdir)
            testlist = tdir / "TestList"
            testlist.write_text("; This is a comment\n\nD ^ZZTEST\n\n")
            (tdir / "ZZTEST.m").write_text("; test\n")

            configs = parse_testlist(str(testlist), "MASH Utilities")
            assert len(configs) == 1
            assert configs[0].routine_name == "ZZTEST"
