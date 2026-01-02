"""Tests for Special Variables ASG analysis (§7.1.7).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7
"""

import pytest


@pytest.mark.asg
class TestSpecialVariablesAnalysis:
    """ASG-level tests for special variables analysis (§7.1.7)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DEVICE")
    def test_sv_device(self, analyze_expression):
        """$DEVICE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ECODE")
    def test_sv_ecode(self, analyze_expression):
        """$ECODE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ESTACK")
    def test_sv_estack(self, analyze_expression):
        """$ESTACK special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ETRAP")
    def test_sv_etrap(self, analyze_expression):
        """$ETRAP special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $HOROLOG")
    def test_sv_horolog(self, analyze_expression):
        """$HOROLOG special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $IO")
    def test_sv_io(self, analyze_expression):
        """$IO special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $JOB")
    def test_sv_job(self, analyze_expression):
        """$JOB special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $KEY")
    def test_sv_key(self, analyze_expression):
        """$KEY special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PRINCIPAL")
    def test_sv_principal(self, analyze_expression):
        """$PRINCIPAL special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT")
    def test_sv_quit(self, analyze_expression):
        """$QUIT special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $REFERENCE")
    def test_sv_reference(self, analyze_expression):
        """$REFERENCE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STACK")
    def test_sv_stack(self, analyze_expression):
        """$STACK special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STORAGE")
    def test_sv_storage(self, analyze_expression):
        """$STORAGE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $SYSTEM")
    def test_sv_system(self, analyze_expression):
        """$SYSTEM special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEST")
    def test_sv_test(self, analyze_expression):
        """$TEST special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL")
    def test_sv_tlevel(self, analyze_expression):
        """$TLEVEL special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRESTART")
    def test_sv_trestart(self, analyze_expression):
        """$TRESTART special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $X")
    def test_sv_x(self, analyze_expression):
        """$X special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $Y")
    def test_sv_y(self, analyze_expression):
        """$Y special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")
