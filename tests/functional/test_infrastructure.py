"""Test functional test infrastructure implementations."""

import pytest

from tests.functional.conftest import (
    ExecutionResult,
    RoutineCall,
    SuiteConfig,
    compare_output,
    get_limitation_reason,
    load_routine_source,
    load_suite_config,
    normalize_outref,
    parse_driver,
    run_mumps,
    run_mumps_with_timeout,
    xfail_limitation,
    skip_limitation,
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

    def test_config_aware_suspend_non_matching(self):
        """SUSPEND with non-matching config label should NOT suspend."""
        content = """YDB>

Real output
##SUSPEND_OUTPUT GT.CM
GT.CM specific stuff
##ALLOW_OUTPUT GT.CM
Still real output
"""
        result = normalize_outref(content)
        # GT.CM doesn't match our config, so its content passes through
        assert "Real output" in result
        assert "GT.CM specific stuff" in result
        assert "Still real output" in result

    def test_config_aware_suspend_non_collation(self):
        """SUSPEND NON_COLLATION should suppress for our config."""
        content = """YDB>

Output before
##SUSPEND_OUTPUT NON_COLLATION
This is for collation configs only
##ALLOW_OUTPUT NON_COLLATION
Output after
"""
        result = normalize_outref(content)
        assert "Output before" in result
        assert "This is for collation configs only" not in result
        assert "Output after" in result

    def test_config_aware_suspend_notrigger(self):
        """SUSPEND NOTRIGGER should suppress for our config (no triggers)."""
        content = """YDB>

Before
##SUSPEND_OUTPUT NOTRIGGER
Trigger-only output
##ALLOW_OUTPUT NOTRIGGER
After
"""
        result = normalize_outref(content)
        assert "Before" in result
        assert "Trigger-only output" not in result
        assert "After" in result

    def test_strips_infrastructure_text(self):
        """Known infrastructure text lines should be stripped."""
        content = """YDB>

Real output line 1
DATABASE EXTRACT PASSED
No errors detected by integ.
Real output line 2
"""
        result = normalize_outref(content)
        assert "Real output line 1" in result
        assert "Real output line 2" in result
        assert "DATABASE EXTRACT PASSED" not in result
        assert "No errors detected by integ." not in result

    def test_strips_bare_db_filenames(self):
        """Bare database filenames like 'mumps.dat' should be stripped."""
        content = """YDB>

Real output
a.dat
mumps.gld
More output
"""
        result = normalize_outref(content)
        assert "Real output" in result
        assert "More output" in result
        assert "a.dat" not in result
        assert "mumps.gld" not in result

    def test_strips_regex_path_markers(self):
        """Regex-based ##MARKER## patterns should be stripped."""
        content = """YDB>

Real output
Some text ##TEST_REMOTE_NODE_PATH_GTCM## more text
##GT.CM## server path
More output
"""
        result = normalize_outref(content)
        assert "Real output" in result
        assert "More output" in result
        assert "##TEST_REMOTE_NODE_PATH_GTCM##" not in result
        assert "##GT.CM##" not in result

    def test_strips_gde_segment_lines(self):
        """GDE segment definition lines should be stripped."""
        content = """YDB>

Real output
DEFAULT\tmumps.dat
ASEG\ta.dat
More output
"""
        result = normalize_outref(content)
        assert "Real output" in result
        assert "More output" in result
        assert "ASEG" not in result
        # DEFAULT followed by tab is stripped
        lines = result.strip().split("\n")
        assert not any(line.startswith("DEFAULT\t") for line in lines)


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


# =============================================================================
# Phase 2 Tests
# =============================================================================


class TestSuiteConfig:
    """Test suite configuration loading (T005)."""

    def test_load_suite_config_returns_config(self):
        """Should return SuiteConfig for valid suite."""
        # mugj is a known suite in the tests/functional directory
        config = load_suite_config("mugj")
        assert isinstance(config, SuiteConfig)
        assert config.name == "mugj"
        assert config.inref_dir.exists()

    def test_load_suite_config_invalid_suite(self):
        """Should raise FileNotFoundError for invalid suite."""
        with pytest.raises(FileNotFoundError, match="Suite directory not found"):
            load_suite_config("nonexistent_suite_xyz")

    def test_load_routine_source_loads_file(self):
        """Should load .m file content."""
        config = load_suite_config("mugj")
        # V1WR should exist in mugj suite
        source = load_routine_source(config.inref_dir, "V1WR")
        assert len(source) > 0
        assert "V1WR" in source or "v1wr" in source.lower()

    def test_load_routine_source_not_found(self):
        """Should raise FileNotFoundError for missing routine."""
        config = load_suite_config("mugj")
        with pytest.raises(FileNotFoundError, match="Routine not found"):
            load_routine_source(config.inref_dir, "NONEXISTENT_ROUTINE_XYZ")


class TestCompareOutput:
    """Test output comparison (T006)."""

    def test_matching_output(self):
        """Identical output should match."""
        actual = "Line 1\nLine 2\nLine 3"
        expected = "Line 1\nLine 2\nLine 3"
        result = compare_output(actual, expected)
        assert result.match is True
        assert result.diff is None
        assert result.actual_lines == 3
        assert result.expected_lines == 3

    def test_mismatched_output(self):
        """Different output should not match and provide diff."""
        actual = "Line 1\nLine 2 modified\nLine 3"
        expected = "Line 1\nLine 2\nLine 3"
        result = compare_output(actual, expected)
        assert result.match is False
        assert result.diff is not None
        assert "Line 2" in result.diff
        assert "-Line 2" in result.diff  # Expected line removed
        assert "+Line 2 modified" in result.diff  # Actual line added

    def test_trailing_whitespace_ignored(self):
        """Trailing whitespace should be ignored."""
        actual = "Line 1  \nLine 2\t\nLine 3"
        expected = "Line 1\nLine 2\nLine 3"
        result = compare_output(actual, expected)
        assert result.match is True

    def test_different_line_counts(self):
        """Reports correct line counts for different lengths."""
        actual = "Line 1\nLine 2"
        expected = "Line 1\nLine 2\nLine 3\nLine 4"
        result = compare_output(actual, expected)
        assert result.match is False
        assert result.actual_lines == 2
        assert result.expected_lines == 4

    def test_strip_internal_blanks_removes_all_blank_lines(self):
        """strip_internal_blanks=True removes ALL blank lines."""
        actual = "Line 1\nLine 2\nLine 3"
        expected = "Line 1\n\nLine 2\n\n\nLine 3"
        # Without strip_internal_blanks, these don't match
        result = compare_output(actual, expected)
        assert result.match is False

        # With strip_internal_blanks, they match
        result = compare_output(actual, expected, strip_internal_blanks=True)
        assert result.match is True

    def test_strip_internal_blanks_both_sides(self):
        """strip_internal_blanks removes blanks from both actual and expected."""
        actual = "A\n\nB\nC"
        expected = "A\nB\n\nC"
        result = compare_output(actual, expected, strip_internal_blanks=True)
        assert result.match is True

    def test_strip_internal_blanks_preserves_content(self):
        """strip_internal_blanks only removes blank lines, not content."""
        actual = "Line 1\nLine 2"
        expected = "Line 1\nLine DIFFERENT"
        result = compare_output(actual, expected, strip_internal_blanks=True)
        assert result.match is False


class TestTimeoutHandling:
    """Test timeout handling (T007)."""

    def test_run_mumps_with_timeout_uses_default(self):
        """Should use DEFAULT_TIMEOUT when not specified."""
        source = """TEST
 W "Quick",!
 Q
"""
        # Just verify it runs without timeout error
        result = run_mumps_with_timeout(source)
        assert result.success
        assert "Quick" in result.output

    def test_run_mumps_with_explicit_timeout(self):
        """Should use explicit timeout when specified."""
        source = """TEST
 W "Quick",!
 Q
"""
        result = run_mumps_with_timeout(source, timeout=10)
        assert result.success


class TestXfailHelper:
    """Test xfail/skip helpers (T008)."""

    def test_get_limitation_reason_known_id(self):
        """Should return formatted reason for known limitation."""
        reason = get_limitation_reason("LIM-003")
        assert "LIM-003" in reason
        # Should include the short description from limitations.py
        assert len(reason) > len("LIM-003: ")

    def test_get_limitation_reason_unknown_id(self):
        """Should return fallback for unknown limitation."""
        reason = get_limitation_reason("LIM-999")
        assert "LIM-999" in reason
        assert "Unknown limitation" in reason

    def test_xfail_limitation_returns_marker(self):
        """Should return a pytest mark decorator."""
        marker = xfail_limitation("LIM-003")
        # Verify it's a mark decorator
        assert hasattr(marker, "mark")

    def test_skip_limitation_returns_marker(self):
        """Should return a pytest skip marker."""
        marker = skip_limitation("LIM-003")
        assert hasattr(marker, "mark")
