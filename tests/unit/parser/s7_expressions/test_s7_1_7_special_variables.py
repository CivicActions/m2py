"""Tests for Special Variables parsing (§7.1.7).

Tests verify the textX grammar correctly captures special variable syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7
"""

import pytest


@pytest.mark.parser
class TestSpecialVariablesParsing:
    """Parser-level tests for Special Variables (§7.1.7).

    Per-variable stubs for all standard special variables.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DEVICE special variable")
    def test_device_variable(self, parse_expression):
        """$DEVICE parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ECODE special variable")
    def test_ecode_variable(self, parse_expression):
        """$ECODE parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $EREF special variable")
    def test_eref_variable(self, parse_expression):
        """$EREF parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ESTACK special variable")
    def test_estack_variable(self, parse_expression):
        """$ESTACK parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ETRAP special variable")
    def test_etrap_variable(self, parse_expression):
        """$ETRAP parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $HOROLOG special variable")
    def test_horolog_variable(self, parse_expression):
        """$HOROLOG parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $IO special variable")
    def test_io_variable(self, parse_expression):
        """$IO parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $IOREFERENCE special variable")
    def test_ioreference_variable(self, parse_expression):
        """$IOREFERENCE parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $JOB special variable")
    def test_job_variable(self, parse_expression):
        """$JOB parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $KEY special variable")
    def test_key_variable(self, parse_expression):
        """$KEY parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PDISPLAY special variable")
    def test_pdisplay_variable(self, parse_expression):
        """$PDISPLAY parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PIOREFERENCE special variable")
    def test_pioreference_variable(self, parse_expression):
        """$PIOREFERENCE parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PRINCIPAL special variable")
    def test_principal_variable(self, parse_expression):
        """$PRINCIPAL parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT special variable")
    def test_quit_variable(self, parse_expression):
        """$QUIT parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $REFERENCE special variable")
    def test_reference_variable(self, parse_expression):
        """$REFERENCE parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STACK special variable")
    def test_stack_variable(self, parse_expression):
        """$STACK parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STORAGE special variable")
    def test_storage_variable(self, parse_expression):
        """$STORAGE parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $SYSTEM special variable")
    def test_system_variable(self, parse_expression):
        """$SYSTEM parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEST special variable")
    def test_test_variable(self, parse_expression):
        """$TEST parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL special variable")
    def test_tlevel_variable(self, parse_expression):
        """$TLEVEL parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRESTART special variable")
    def test_trestart_variable(self, parse_expression):
        """$TRESTART parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $X special variable")
    def test_x_variable(self, parse_expression):
        """$X parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $Y special variable")
    def test_y_variable(self, parse_expression):
        """$Y parses correctly (§7.1.7)."""
        pytest.fail("Stub - implement test")
