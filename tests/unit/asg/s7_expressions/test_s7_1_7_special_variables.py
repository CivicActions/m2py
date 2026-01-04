"""Tests for Special Variables ASG analysis (§7.1.4.10).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.4.10 - Intrinsic special variable names

Special variables from spec: D[EVICE], EC[ODE], ES[TACK], ET[RAP], H[OROLOG],
I[O], J[OB], K[EY], P[RINCIPAL], Q[UIT], R[EFERENCE], ST[ACK], S[TORAGE],
SY[STEM], T[EST], TL[EVEL], TR[ESTART], X, Y
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg import MSpecialVariable


@pytest.mark.asg
class TestSpecialVariablesFull:
    """Complete tests for all intrinsic special variables (§7.1.4.10).

    Each test verifies:
    1. Full name produces MSpecialVariable with correct name
    2. Abbreviation (where applicable) produces MSpecialVariable
    """

    def test_device_variable(self):
        """$DEVICE creates MSpecialVariable (§7.1.4.10 D[EVICE])."""
        expr = parse_expression("$DEVICE")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "DEVICE"

    def test_device_abbreviated(self):
        """$D creates MSpecialVariable (§7.1.4.10 D[EVICE])."""
        expr = parse_expression("$D")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "D"

    def test_ecode_variable(self):
        """$ECODE creates MSpecialVariable (§7.1.4.10 EC[ODE])."""
        expr = parse_expression("$ECODE")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "ECODE"

    def test_ecode_abbreviated(self):
        """$EC creates MSpecialVariable (§7.1.4.10 EC[ODE])."""
        expr = parse_expression("$EC")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "EC"

    def test_estack_variable(self):
        """$ESTACK creates MSpecialVariable (§7.1.4.10 ES[TACK])."""
        expr = parse_expression("$ESTACK")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "ESTACK"

    def test_estack_abbreviated(self):
        """$ES creates MSpecialVariable (§7.1.4.10 ES[TACK])."""
        expr = parse_expression("$ES")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "ES"

    def test_etrap_variable(self):
        """$ETRAP creates MSpecialVariable (§7.1.4.10 ET[RAP])."""
        expr = parse_expression("$ETRAP")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "ETRAP"

    def test_etrap_abbreviated(self):
        """$ET creates MSpecialVariable (§7.1.4.10 ET[RAP])."""
        expr = parse_expression("$ET")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "ET"

    def test_horolog_variable(self):
        """$HOROLOG creates MSpecialVariable (§7.1.4.10 H[OROLOG])."""
        expr = parse_expression("$HOROLOG")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "HOROLOG"

    def test_horolog_abbreviated(self):
        """$H creates MSpecialVariable (§7.1.4.10 H[OROLOG])."""
        expr = parse_expression("$H")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "H"

    def test_io_variable(self):
        """$IO creates MSpecialVariable (§7.1.4.10 I[O])."""
        expr = parse_expression("$IO")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "IO"

    def test_io_abbreviated(self):
        """$I creates MSpecialVariable (§7.1.4.10 I[O])."""
        expr = parse_expression("$I")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "I"

    def test_job_variable(self):
        """$JOB creates MSpecialVariable (§7.1.4.10 J[OB])."""
        expr = parse_expression("$JOB")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "JOB"

    def test_job_abbreviated(self):
        """$J creates MSpecialVariable (§7.1.4.10 J[OB])."""
        expr = parse_expression("$J")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "J"

    def test_key_variable(self):
        """$KEY creates MSpecialVariable (§7.1.4.10 K[EY])."""
        expr = parse_expression("$KEY")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "KEY"

    def test_key_abbreviated(self):
        """$K creates MSpecialVariable (§7.1.4.10 K[EY])."""
        expr = parse_expression("$K")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "K"

    def test_principal_variable(self):
        """$PRINCIPAL creates MSpecialVariable (§7.1.4.10 P[RINCIPAL])."""
        expr = parse_expression("$PRINCIPAL")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "PRINCIPAL"

    def test_principal_abbreviated(self):
        """$P creates MSpecialVariable (§7.1.4.10 P[RINCIPAL])."""
        expr = parse_expression("$P")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "P"

    def test_quit_variable(self):
        """$QUIT creates MSpecialVariable (§7.1.4.10 Q[UIT])."""
        expr = parse_expression("$QUIT")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "QUIT"

    def test_quit_abbreviated(self):
        """$Q creates MSpecialVariable (§7.1.4.10 Q[UIT])."""
        expr = parse_expression("$Q")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "Q"

    def test_reference_variable(self):
        """$REFERENCE creates MSpecialVariable (§7.1.4.10 R[EFERENCE])."""
        expr = parse_expression("$REFERENCE")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "REFERENCE"

    def test_reference_abbreviated(self):
        """$R creates MSpecialVariable (§7.1.4.10 R[EFERENCE])."""
        expr = parse_expression("$R")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "R"

    def test_stack_variable(self):
        """$STACK creates MSpecialVariable (§7.1.4.10 ST[ACK])."""
        expr = parse_expression("$STACK")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "STACK"

    def test_stack_abbreviated(self):
        """$ST creates MSpecialVariable (§7.1.4.10 ST[ACK])."""
        expr = parse_expression("$ST")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "ST"

    def test_storage_variable(self):
        """$STORAGE creates MSpecialVariable (§7.1.4.10 S[TORAGE])."""
        expr = parse_expression("$STORAGE")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "STORAGE"

    def test_storage_abbreviated(self):
        """$S creates MSpecialVariable (§7.1.4.10 S[TORAGE])."""
        expr = parse_expression("$S")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "S"

    def test_system_variable(self):
        """$SYSTEM creates MSpecialVariable (§7.1.4.10 SY[STEM])."""
        expr = parse_expression("$SYSTEM")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "SYSTEM"

    def test_system_abbreviated(self):
        """$SY creates MSpecialVariable (§7.1.4.10 SY[STEM])."""
        expr = parse_expression("$SY")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "SY"

    def test_test_variable(self):
        """$TEST creates MSpecialVariable (§7.1.4.10 T[EST])."""
        expr = parse_expression("$TEST")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TEST"

    def test_test_abbreviated(self):
        """$T creates MSpecialVariable (§7.1.4.10 T[EST])."""
        expr = parse_expression("$T")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "T"

    def test_tlevel_variable(self):
        """$TLEVEL creates MSpecialVariable (§7.1.4.10 TL[EVEL])."""
        expr = parse_expression("$TLEVEL")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TLEVEL"

    def test_tlevel_abbreviated(self):
        """$TL creates MSpecialVariable (§7.1.4.10 TL[EVEL])."""
        expr = parse_expression("$TL")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TL"

    def test_trestart_variable(self):
        """$TRESTART creates MSpecialVariable (§7.1.4.10 TR[ESTART])."""
        expr = parse_expression("$TRESTART")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TRESTART"

    def test_trestart_abbreviated(self):
        """$TR creates MSpecialVariable (§7.1.4.10 TR[ESTART])."""
        expr = parse_expression("$TR")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TR"

    def test_x_variable(self):
        """$X creates MSpecialVariable (§7.1.4.10 X)."""
        expr = parse_expression("$X")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "X"

    def test_y_variable(self):
        """$Y creates MSpecialVariable (§7.1.4.10 Y)."""
        expr = parse_expression("$Y")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "Y"
