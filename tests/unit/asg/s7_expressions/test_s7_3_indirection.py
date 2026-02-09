"""Tests for Indirection ASG analysis (§7.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.3
"""

import pytest

from m2py.asg.enums import IndirectionType
from m2py.asg.statements import MSetStatement
from m2py.parser.textx_classes import Indirection, LocalVariable
from tests.helpers.parsing import parse_expression


@pytest.mark.asg
class TestIndirectionAnalysis:
    """ASG-level tests for indirection in expressions analysis (§7.3)."""

    def test_name_indirection(self, analyze_expression):
        """Name indirection (@var) is correctly analyzed (§7.3).

        Per 1995__a901027.md: "Set X='ABC' IF 123+@X=456"
        Name indirection creates an Indirection node with IndirectionType.NAME
        and the dereferenced variable in expression.
        """
        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, Indirection)
        assert result.indirection_type == IndirectionType.NAME
        assert isinstance(result.expression, LocalVariable)
        assert result.expression.name == "X"

    def test_subscript_indirection(self, analyze_expression):
        """Subscript indirection (@var@(subs)) is correctly analyzed (§7.3).

        Per 1984 addition (1995__a901027.md): @ARRAY@(1,2,3) resolves ARRAY
        to a name, then appends subscripts. Captured in name_indirection_subscripts.
        """
        expr = parse_expression("@X@(1,2)")
        result = analyze_expression(expr)

        assert isinstance(result, Indirection)
        assert isinstance(result.expression, LocalVariable)
        assert result.expression.name == "X"
        # Subscripts are captured in name_indirection_subscripts
        assert result.name_indirection_subscripts is not None
        assert len(result.name_indirection_subscripts) == 1  # One subscript list
        assert len(result.name_indirection_subscripts[0]) == 2  # Two subscripts

    def test_argument_indirection(self, analyze_expression):
        """Argument indirection is correctly analyzed (§7.3).

        Per 1995__a901027.md: "Write @$Select(ENOUGH:SPACE,1:PAGE)"
        Argument indirection uses @ where the expression evaluates to
        command arguments. In expressions, this is still an Indirection node.
        """
        expr = parse_expression("@ARGS")
        result = analyze_expression(expr)

        assert isinstance(result, Indirection)
        assert result.indirection_type == IndirectionType.NAME
        assert isinstance(result.expression, LocalVariable)
        assert result.expression.name == "ARGS"

    def test_indirection_limitations(self, analyze_routine):
        """Indirection static analysis limitations are tracked (§7.3).

        Indirection generally requires runtime evaluation and cannot be
        statically resolved unless the expression is a constant.
        """
        routine = analyze_routine("TEST\n S X=@A\n Q")

        stmt = routine.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, Indirection)
        # Cannot resolve statically without constant propagation
        assert value.can_resolve_statically is False
        assert value.resolved_value is None

    def test_nested_indirection(self, analyze_expression):
        """Nested indirection is correctly analyzed (§7.3).

        Per YDBTest/indirection/inref/indlcl.m: "set @@variable='PASSED'"
        Nested indirection is dereferenced twice at runtime.
        """
        expr = parse_expression("@@X")
        result = analyze_expression(expr)

        # Outer indirection
        assert isinstance(result, Indirection)
        assert result.indirection_type == IndirectionType.NAME
        # Inner indirection
        assert isinstance(result.expression, Indirection)
        assert result.expression.indirection_type == IndirectionType.NAME
        # Innermost is the variable X
        assert isinstance(result.expression.expression, LocalVariable)
        assert result.expression.expression.name == "X"

    def test_triple_indirection(self, analyze_expression):
        """Triple indirection @@@X is correctly analyzed (§7.3).

        Triple indirection dereferences the variable three times at runtime.
        This is rare but valid MUMPS syntax.

        GAP-003e: Coverage gap for lines 1268-1271 in semantic_analyzer.py.
        """
        expr = parse_expression("@@@X")
        result = analyze_expression(expr)

        # Outer indirection
        assert isinstance(result, Indirection)
        assert result.indirection_type == IndirectionType.NAME
        # Middle indirection
        assert isinstance(result.expression, Indirection)
        assert result.expression.indirection_type == IndirectionType.NAME
        # Inner indirection
        assert isinstance(result.expression.expression, Indirection)
        assert result.expression.expression.indirection_type == IndirectionType.NAME
        # Innermost is the variable X
        assert isinstance(result.expression.expression.expression, LocalVariable)
        assert result.expression.expression.expression.name == "X"

    def test_indirection_side_effects(self, analyze_routine):
        """Indirection side effects are tracked (§7.3).

        When indirection is used as a SET target, the routine cannot
        determine statically which variable is modified.
        """
        routine = analyze_routine("TEST\n S @VAR=1,Y=2\n Q")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 2

        # First assignment uses indirection
        first = stmt.assignments[0]
        assert isinstance(first.target, Indirection)

        # Second assignment is a direct variable
        second = stmt.assignments[1]
        assert isinstance(second.target, LocalVariable)
        assert second.target.name == "Y"


@pytest.mark.asg
class TestIndirectionASG:
    """Test MIndirection ASG node structure."""

    def test_indirection_subscripted(self):
        """@X(1) creates MIndirection with subscripts."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MIndirection

        expr = parse_expression("@X(1)")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.expression is not None


@pytest.mark.asg
class TestIndirectionClassification:
    """Tests for indirection type classification and static resolution."""

    def test_indirection_static_resolution_string(self):
        """@"VARNAME" should resolve statically."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIndirection

        expr = parse_expression('@"VARNAME"')
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.can_resolve_statically is True
        assert result.resolved_value == "VARNAME"


@pytest.mark.asg
class TestIndirectionSubscriptAnalysis:
    """Tests for MIndirection subscript analysis."""

    def test_indirection_expression_subscripts_analyzed(self):
        """Variables in @A(B,C) have subscripts on the expression, not indirection.

        The grammar @A(B,C) is parsed as @(A(B,C)) - indirection of subscripted A.
        The subscripts are on the inner expression, and they should be analyzed.
        """
        from m2py.parser import MUMPSParser
        from m2py.asg import MIndirection

        parser = MUMPSParser()
        routine = parser.parse("TEST\n S @A(B,C)=1\n")

        stmt = routine.labels[0].body.statements[0]
        target = stmt.assignments[0].target

        # The target should be an indirection
        assert isinstance(target, MIndirection)

        # The expression is A(B,C) - a subscripted variable
        inner = target.expression
        assert inner.name == "A"
        assert len(inner.subscripts) == 2

        # Subscripts should be analyzed expressions
        assert inner.subscripts[0].name == "B"
        assert inner.subscripts[1].name == "C"
