"""Tests for Special Variables ASG analysis (§7.1.7).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.7

Migrated from: tests/unit/test_semantic_analyzer.py::TestSpecialVariableASG
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg import MSpecialVariable


@pytest.mark.asg
class TestSpecialVariablesAnalysis:
    """ASG-level tests for special variables analysis (§7.1.7).

    Migrated from: TestSpecialVariableASG
    """

    def test_test_variable(self):
        """$TEST creates MSpecialVariable with name (§7.1.7)."""
        expr = parse_expression("$TEST")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TEST"

    def test_horolog_variable(self):
        """$HOROLOG creates MSpecialVariable (§7.1.7)."""
        expr = parse_expression("$HOROLOG")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "HOROLOG"

    def test_job_variable(self):
        """$JOB creates MSpecialVariable (§7.1.7)."""
        expr = parse_expression("$JOB")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "JOB"

    def test_abbreviated_horolog(self):
        """$H creates MSpecialVariable with name 'H' (single-letter abbreviation) (§7.1.7)."""
        expr = parse_expression("$H")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "H"

    def test_abbreviated_storage(self):
        """$S creates MSpecialVariable with name 'S' (single-letter abbreviation) (§7.1.7)."""
        expr = parse_expression("$S")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "S"

    def test_abbreviated_test(self):
        """$T creates MSpecialVariable with name 'T' (single-letter abbreviation) (§7.1.7)."""
        expr = parse_expression("$T")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "T"

    def test_abbreviated_job(self):
        """$J creates MSpecialVariable with name 'J' (single-letter abbreviation) (§7.1.7)."""
        expr = parse_expression("$J")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "J"

    # ---- Stub tests for unimplemented special variables ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DEVICE")
    def test_sv_device(self):
        """$DEVICE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ECODE")
    def test_sv_ecode(self):
        """$ECODE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ESTACK")
    def test_sv_estack(self):
        """$ESTACK special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ETRAP")
    def test_sv_etrap(self):
        """$ETRAP special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $IO")
    def test_sv_io(self):
        """$IO special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $KEY")
    def test_sv_key(self):
        """$KEY special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PRINCIPAL")
    def test_sv_principal(self):
        """$PRINCIPAL special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUIT")
    def test_sv_quit(self):
        """$QUIT special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $REFERENCE")
    def test_sv_reference(self):
        """$REFERENCE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STACK")
    def test_sv_stack(self):
        """$STACK special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STORAGE")
    def test_sv_storage(self):
        """$STORAGE special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $SYSTEM")
    def test_sv_system(self):
        """$SYSTEM special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL")
    def test_sv_tlevel(self):
        """$TLEVEL special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRESTART")
    def test_sv_trestart(self):
        """$TRESTART special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $X")
    def test_sv_x(self):
        """$X special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $Y")
    def test_sv_y(self):
        """$Y special variable is correctly analyzed (§7.1.7)."""
        pytest.fail("Stub - implement test")
