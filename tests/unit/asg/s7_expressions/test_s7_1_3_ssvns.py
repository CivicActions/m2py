"""Tests for SSVNs ASG analysis (§7.1.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3
"""

import pytest


@pytest.mark.asg
class TestSsvnsAnalysis:
    """ASG-level tests for structured system variables analysis (§7.1.3)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$GLOBAL SSVN")
    def test_ssvn_global(self, analyze_expression):
        """^$GLOBAL SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$JOB SSVN")
    def test_ssvn_job(self, analyze_expression):
        """^$JOB SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$LOCK SSVN")
    def test_ssvn_lock(self, analyze_expression):
        """^$LOCK SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$ROUTINE SSVN")
    def test_ssvn_routine(self, analyze_expression):
        """^$ROUTINE SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$SYSTEM SSVN")
    def test_ssvn_system(self, analyze_expression):
        """^$SYSTEM SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$DEVICE SSVN")
    def test_ssvn_device(self, analyze_expression):
        """^$DEVICE SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$CHARACTER SSVN")
    def test_ssvn_character(self, analyze_expression):
        """^$CHARACTER SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$DISPLAY SSVN")
    def test_ssvn_display(self, analyze_expression):
        """^$DISPLAY SSVN is correctly analyzed (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.skip(reason="Out of scope: ^$LIBRARY SSVN per FR-055")
    def test_ssvn_library(self):
        """^$LIBRARY SSVN is out of scope (§7.1.3)."""
        pass

    @pytest.mark.skip(reason="Out of scope: ^$EVENT SSVN per FR-055")
    def test_ssvn_event(self):
        """^$EVENT SSVN is out of scope (§7.1.3)."""
        pass
