"""Test Phase 1 implementations."""

from tests.functional.conftest import (
    ExecutionResult,
    RoutineCall,
    normalize_outref,
    parse_driver,
    run_mumps,
)


class TestNormalizeOutref:
    """Test outref normalization function."""

    def test_strips_preamble_before_ydb_prompt(self):
        """Preamble before first YDB> should be stripped."""
        content = """Files Created in ##TEST_PATH##:
Using: ##SOURCE_PATH##/mumps -run GDE
mumps.gld

YDB>

V1WR
Test output
"""
        result = normalize_outref(content)
        assert "Files Created" not in result
        assert "V1WR" in result
        assert "Test output" in result

    def test_strips_suspend_allow_blocks(self):
        """Suspended output blocks should be stripped."""
        content = """YDB>

Real output
##SUSPEND_OUTPUT  NON_REPLIC
This should be hidden
More hidden
##ALLOW_OUTPUT  NON_REPLIC
More real output
"""
        result = normalize_outref(content)
        assert "Real output" in result
        assert "This should be hidden" not in result
        assert "More hidden" not in result
        assert "More real output" in result

    def test_strips_path_markers(self):
        """Lines with path markers should be stripped."""
        content = """YDB>

V1WR
##TEST_PATH##/some/path
Real output
##SOURCE_PATH##/other
More output
"""
        result = normalize_outref(content)
        assert "V1WR" in result
        assert "Real output" in result
        assert "##TEST_PATH##" not in result
        assert "##SOURCE_PATH##" not in result

    def test_strips_ydb_prompts(self):
        """YDB> prompts should be stripped."""
        content = """YDB>

V1WR

YDB>

V1CMT
"""
        result = normalize_outref(content)
        assert "YDB>" not in result
        assert "V1WR" in result
        assert "V1CMT" in result


class TestParseDriver:
    """Test driver script parser."""

    def test_extracts_routine_calls(self):
        """Should extract W/D routine call patterns."""
        content = """$GTM << xyyz
W !!,"V1WR" D ^V1WR
W !!,"V1CMT" D ^V1CMT
H
xyyz
"""
        result = parse_driver(content)
        assert len(result) == 2
        assert result[0] == RoutineCall("V1WR", "V1WR")
        assert result[1] == RoutineCall("V1CMT", "V1CMT")

    def test_skips_commented_lines(self):
        """Commented-out routine calls should be skipped."""
        content = """W !!,"V1WR" D ^V1WR
;;;;;;;;;W !!,"V1READ" D ^V1READ
W !!,"V1CMT" D ^V1CMT
"""
        result = parse_driver(content)
        assert len(result) == 2
        assert result[0].routine == "V1WR"
        assert result[1].routine == "V1CMT"

    def test_skips_shell_infrastructure(self):
        """Shell commands should be skipped."""
        content = """#! /usr/local/bin/tcsh -f
$gtm_tst/com/dbcreate.csh . . 125 500
W !!,"V1WR" D ^V1WR
"""
        result = parse_driver(content)
        assert len(result) == 1
        assert result[0].routine == "V1WR"

    def test_handles_comments_after_routine(self):
        """Comments after the routine call should not affect parsing."""
        content = """W !!,"V1WR" D ^V1WR ;This is a comment
W !!,"VV2CS" D ^VV2CS ;Command space
"""
        result = parse_driver(content)
        assert len(result) == 2
        assert result[0].routine == "V1WR"
        assert result[1].routine == "VV2CS"


class TestRunMumps:
    """Test MUMPS execution helper."""

    def test_simple_write(self):
        """Should execute simple WRITE command."""
        source = """TEST
 W "Hello",!
 Q
"""
        result = run_mumps(source, timeout=10)
        assert result.success
        assert "Hello" in result.output

    def test_returns_result(self):
        """Should return ExecutionResult with correct fields."""
        source = """TEST
 W "Test",!
 Q
"""
        result = run_mumps(source, timeout=5)
        assert isinstance(result, ExecutionResult)
        assert hasattr(result, "output")
        assert hasattr(result, "success")
        assert hasattr(result, "error")
