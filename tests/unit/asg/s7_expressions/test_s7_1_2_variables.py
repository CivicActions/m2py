"""Tests for Variables ASG analysis (§7.1.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2

Migrated from: tests/unit/test_semantic_analyzer.py::TestAnalyzeExpression (partial)
"""

import pytest
from tests.helpers.parsing import parse_expression
from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg.expressions import MVariable, MGlobal, MSpecialVariable


@pytest.mark.asg
class TestVariablesAnalysis:
    """ASG-level tests for variables analysis (§7.1.2).

    Migrated from: TestAnalyzeExpression
    """

    def test_analyze_local_variable(self):
        """Local variable analysis produces MVariable node (§7.1.2)."""
        expr = parse_expression("X")
        result = analyze_expression(expr)

        assert isinstance(result, MVariable)
        assert result.name == "X"

    def test_analyze_global_variable(self):
        """Global variable analysis produces MGlobal node (§7.1.2)."""
        expr = parse_expression("^GLOBAL")
        result = analyze_expression(expr)

        assert isinstance(result, MGlobal)
        assert result.name == "GLOBAL"

    def test_analyze_special_variable(self):
        """Special variable analysis produces MSpecialVariable node (§7.1.2)."""
        expr = parse_expression("$TEST")
        result = analyze_expression(expr)

        assert isinstance(result, MSpecialVariable)
        assert result.name == "TEST"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: naked global reference")
    def test_naked_global_reference(self, analyze_routine):
        """Naked global references are correctly tracked (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: variable scope analysis")
    def test_variable_scope_analysis(self, analyze_routine):
        """Variable scope (input/output) is correctly analyzed (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscripted variable")
    def test_subscripted_variable(self, analyze_routine):
        """Subscripted variables are correctly represented (§7.1.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: glvn unification")
    def test_glvn_unification(self, analyze_routine):
        """GLVN (local or global) is unified in ASG (§7.1.2)."""
        pytest.fail("Stub - implement test")
