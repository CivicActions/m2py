"""Tests for Extrinsic Functions ASG analysis (§7.1.6).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6

Migrated from: tests/unit/test_semantic_analyzer.py::TestExtrinsicFunctionASG
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg import MExtrinsicFunction
from m2py.asg.expressions import MActualParameter
from m2py.asg.enums import PassingMode


@pytest.mark.asg
class TestExtrinsicFunctionsAnalysis:
    """ASG-level tests for extrinsic functions analysis (§7.1.6).

    Migrated from: TestExtrinsicFunctionASG
    """

    def test_extrinsic_simple(self):
        """$$FUNC creates MExtrinsicFunction with target (§7.1.6)."""
        expr = parse_expression("$$MYFUNC")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "MYFUNC"

    def test_extrinsic_with_routine(self):
        """$$FUNC^ROUTINE has routine reference in target (§7.1.6)."""
        expr = parse_expression("$$CALC^UTILS")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "CALC"
        assert result.target.routine == "UTILS"

    def test_extrinsic_with_args(self):
        """$$FUNC(a,b) has arguments list (§7.1.6)."""
        expr = parse_expression("$$ADD(1,2)")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 2

    def test_extrinsic_with_byref_args(self):
        """$$FUNC(.X,Y,.Z) preserves by-reference passing mode (§7.1.6).

        MUMPS spec 8.1.7: .actualname = call-by-reference format.
        """
        expr = parse_expression("$$CALC(.A,B,.C)")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 3

        # First arg: .A is by-reference
        assert isinstance(result.arguments[0], MActualParameter)
        assert result.arguments[0].passing_mode == PassingMode.BY_REFERENCE
        assert result.arguments[0].variable_name == "A"

        # Second arg: B is by-value
        assert isinstance(result.arguments[1], MActualParameter)
        assert result.arguments[1].passing_mode == PassingMode.BY_VALUE

        # Third arg: .C is by-reference
        assert isinstance(result.arguments[2], MActualParameter)
        assert result.arguments[2].passing_mode == PassingMode.BY_REFERENCE
        assert result.arguments[2].variable_name == "C"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic function return")
    def test_extrinsic_function_return(self, analyze_routine):
        """Extrinsic function return value is tracked (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic special variable")
    def test_extrinsic_special_variable(self, analyze_routine):
        """Extrinsic special variables ($$) are correctly analyzed (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: external routine reference")
    def test_external_routine_reference(self, analyze_routine):
        """External routine references are tracked (§7.1.6)."""
        pytest.fail("Stub - implement test")
