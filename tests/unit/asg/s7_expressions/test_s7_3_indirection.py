"""Tests for Indirection ASG analysis (§7.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.3
"""

import pytest


@pytest.mark.asg
class TestIndirectionAnalysis:
    """ASG-level tests for indirection in expressions analysis (§7.3)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: name indirection")
    def test_name_indirection(self, analyze_expression):
        """Name indirection (@var) is correctly analyzed (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript indirection")
    def test_subscript_indirection(self, analyze_expression):
        """Subscript indirection (@var@(subs)) is correctly analyzed (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection")
    def test_argument_indirection(self, analyze_expression):
        """Argument indirection is correctly analyzed (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: indirection in SET")
    def test_indirection_in_set(self, analyze_routine):
        """Indirection in SET command is correctly analyzed (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: indirection limitations")
    def test_indirection_limitations(self, analyze_routine):
        """Indirection static analysis limitations are tracked (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nested indirection")
    def test_nested_indirection(self, analyze_expression):
        """Nested indirection is correctly analyzed (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: indirection side effects")
    def test_indirection_side_effects(self, analyze_routine):
        """Indirection side effects are tracked (§7.3)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestIndirectionASG:
    """Test MIndirection ASG node structure."""

    def test_indirection_simple(self):
        """@X creates MIndirection with expression."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MIndirection
        from m2py.asg.expressions import MVariable

        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.expression is not None
        assert isinstance(result.expression, MVariable)
        assert result.expression.name == "X"

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

    def test_indirection_default_type(self):
        """@X should have IndirectionType.NAME by default."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIndirection
        from m2py.asg.enums import IndirectionType

        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.indirection_type == IndirectionType.NAME

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

    def test_indirection_variable_not_static(self):
        """@X should not resolve statically."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg.expressions import MIndirection

        expr = parse_expression("@X")
        result = analyze_expression(expr)

        assert isinstance(result, MIndirection)
        assert result.can_resolve_statically is False
        assert result.resolved_value is None


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

    def test_indirection_requires_runtime(self):
        """MIndirection has requires_runtime_eval=True."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MIndirection

        parser = MUMPSParser()
        routine = parser.parse("TEST\n S X=@A\n")

        stmt = routine.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, MIndirection)
        assert value.requires_runtime_eval is True
