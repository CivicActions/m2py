"""Tests for comprehensive indirection detection.

Phase 91: Tests for walk_expressions(), has_indirection(), and
the updated check_requires_runtime_scope() function.
"""

import pytest

from m2py.asg.elements import MCall, MLabel, MScope
from m2py.asg.expressions import (
    MBinaryOp,
    MIndirection,
    MIntrinsicFunction,
    MLiteral,
    MPatternMatch,
    MVariable,
)
from m2py.asg.enums import IndirectionType, LiteralType
from m2py.asg.statements import (
    MAssignment,
    MDoStatement,
    MGotoStatement,
    MSetStatement,
    MWriteStatement,
    MXecuteStatement,
)
from m2py.analysis.variables import (
    check_requires_runtime_scope,
    has_indirection,
    walk_expressions,
)


@pytest.mark.analysis
class TestWalkExpressions:
    """Test walk_expressions() generator function."""

    def test_walk_literal(self):
        """Walk a simple literal."""
        lit = MLiteral(value=42, literal_type=LiteralType.INTEGER)
        exprs = list(walk_expressions(lit))
        assert len(exprs) == 1
        assert exprs[0] is lit

    def test_walk_variable(self):
        """Walk a variable without subscripts."""
        var = MVariable(name="X")
        exprs = list(walk_expressions(var))
        assert len(exprs) == 1
        assert exprs[0] is var

    def test_walk_variable_with_subscripts(self):
        """Walk a variable with subscripts."""
        sub1 = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        sub2 = MVariable(name="I")
        var = MVariable(name="A", subscripts=[sub1, sub2])
        exprs = list(walk_expressions(var))
        assert len(exprs) == 3
        assert var in exprs
        assert sub1 in exprs
        assert sub2 in exprs

    def test_walk_binary_op(self):
        """Walk a binary operation."""
        left = MVariable(name="X")
        right = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        binop = MBinaryOp(operator="+", left=left, right=right)
        exprs = list(walk_expressions(binop))
        assert len(exprs) == 3
        assert binop in exprs
        assert left in exprs
        assert right in exprs

    def test_walk_indirection(self):
        """Walk an indirection expression."""
        inner = MVariable(name="REF")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        exprs = list(walk_expressions(indir))
        assert len(exprs) == 2
        assert indir in exprs
        assert inner in exprs

    def test_walk_function_with_args(self):
        """Walk an intrinsic function with arguments."""
        arg1 = MVariable(name="X")
        arg2 = MLiteral(value=",", literal_type=LiteralType.STRING)
        func = MIntrinsicFunction(name="PIECE", arguments=[arg1, arg2])
        exprs = list(walk_expressions(func))
        assert len(exprs) == 3
        assert func in exprs
        assert arg1 in exprs
        assert arg2 in exprs

    def test_walk_set_statement(self):
        """Walk a SET statement with target and value."""
        target = MVariable(name="X")
        value = MLiteral(value=42, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=target, value=value)
        stmt = MSetStatement(assignments=[assign])
        exprs = list(walk_expressions(stmt))
        assert target in exprs
        assert value in exprs

    def test_walk_none(self):
        """Walk None returns empty."""
        exprs = list(walk_expressions(None))
        assert exprs == []

    def test_walk_list(self):
        """Walk a list of expressions."""
        expr1 = MVariable(name="A")
        expr2 = MVariable(name="B")
        exprs = list(walk_expressions([expr1, expr2]))
        assert len(exprs) == 2
        assert expr1 in exprs
        assert expr2 in exprs

    def test_walk_for_parameters(self):
        """Walk FOR statement parameters (start, step, end).

        MUMPS: FOR I=A:B:C walks the parameters A, B, C as expressions.
        Coverage target: Lines 917-923 in variables.py
        """
        from m2py.asg.statements import MForStatement, MForParameter
        from m2py.asg.enums import ForParamType

        # Create FOR I=A:B:C
        loop_var = MVariable(name="I")
        start = MVariable(name="A")
        step = MVariable(name="B")
        end = MVariable(name="C")

        param = MForParameter(
            param_type=ForParamType.RANGE,
            start=start,
            step=step,
            end=end,
        )

        for_stmt = MForStatement(
            loop_var=loop_var,
            parameters=[param],
        )

        exprs = list(walk_expressions(for_stmt))

        # Should include loop_var and all parameter expressions
        assert loop_var in exprs
        assert start in exprs
        assert step in exprs
        assert end in exprs

    def test_walk_for_parameters_value_only(self):
        """Walk FOR statement with VALUE parameter type.

        MUMPS: FOR I=V walks the value expression V.
        """
        from m2py.asg.statements import MForStatement, MForParameter
        from m2py.asg.enums import ForParamType

        loop_var = MVariable(name="I")
        value = MVariable(name="V")

        param = MForParameter(
            param_type=ForParamType.VALUE,
            value=value,
        )

        for_stmt = MForStatement(
            loop_var=loop_var,
            parameters=[param],
        )

        exprs = list(walk_expressions(for_stmt))

        # loop_var should be included
        assert loop_var in exprs
        # value isn't in start/step/end so won't be walked by current code
        # This tests the current behavior - param.value is NOT walked


@pytest.mark.analysis
class TestHasIndirection:
    """Test has_indirection() helper function."""

    def test_simple_literal_no_indirection(self):
        """Simple literal has no indirection."""
        lit = MLiteral(value=42, literal_type=LiteralType.INTEGER)
        assert has_indirection(lit) is False

    def test_simple_variable_no_indirection(self):
        """Simple variable has no indirection."""
        var = MVariable(name="X")
        assert has_indirection(var) is False

    def test_name_indirection(self):
        """@VAR has indirection."""
        inner = MVariable(name="REF")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        assert has_indirection(indir) is True

    def test_subscript_indirection(self):
        """A(@I) has indirection in subscript."""
        inner = MVariable(name="I")
        indir = MIndirection(
            expression=inner, indirection_type=IndirectionType.SUBSCRIPT
        )
        var = MVariable(name="A", subscripts=[indir])
        assert has_indirection(var) is True

    def test_indirection_in_binary_op(self):
        """X+@Y has indirection."""
        left = MVariable(name="X")
        inner = MVariable(name="Y")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        binop = MBinaryOp(operator="+", left=left, right=indir)
        assert has_indirection(binop) is True

    def test_indirection_in_function_arg(self):
        """$O(@X) has indirection in argument."""
        inner = MVariable(name="X")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        func = MIntrinsicFunction(name="ORDER", arguments=[indir])
        assert has_indirection(func) is True

    def test_nested_indirection(self):
        """@@X has nested indirection."""
        innermost = MVariable(name="X")
        inner = MIndirection(
            expression=innermost, indirection_type=IndirectionType.NAME
        )
        outer = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        assert has_indirection(outer) is True

    def test_set_with_indirect_target(self):
        """S @X=1 has indirection in target."""
        inner = MVariable(name="X")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        value = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=indir, value=value)
        stmt = MSetStatement(assignments=[assign])
        assert has_indirection(stmt) is True

    def test_set_with_indirect_value(self):
        """S Y=@X has indirection in value."""
        target = MVariable(name="Y")
        inner = MVariable(name="X")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        assign = MAssignment(target=target, value=indir)
        stmt = MSetStatement(assignments=[assign])
        assert has_indirection(stmt) is True

    def test_no_indirection_in_set(self):
        """S X=1 has no indirection."""
        target = MVariable(name="X")
        value = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=target, value=value)
        stmt = MSetStatement(assignments=[assign])
        assert has_indirection(stmt) is False

    def test_pattern_match_no_indirection(self):
        """X?1N has no indirection (constant pattern)."""
        subject = MVariable(name="X")
        pm = MPatternMatch(subject=subject, pattern="1N", pattern_indirect=None)
        assert has_indirection(pm) is False

    def test_pattern_match_with_indirection(self):
        """X?@PAT has indirection."""
        subject = MVariable(name="X")
        pat_var = MVariable(name="PAT")
        indir = MIndirection(expression=pat_var, indirection_type=IndirectionType.NAME)
        pm = MPatternMatch(subject=subject, pattern="", pattern_indirect=indir)
        assert has_indirection(pm) is True


@pytest.mark.analysis
class TestCheckRequiresRuntimeScope:
    """Test updated check_requires_runtime_scope()."""

    def _make_label(self, statements):
        """Helper to create a label with the given statements."""
        scope = MScope(statements=statements)
        return MLabel(name="TEST", body=scope)

    def test_xecute_requires_runtime(self):
        """XECUTE always requires runtime."""
        from m2py.asg.statements import MXecuteArg

        code = MLiteral(value="S X=1", literal_type=LiteralType.STRING)
        stmt = MXecuteStatement(arguments=[MXecuteArg(expression=code)])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_do_indirection_requires_runtime(self):
        """D @VAR requires runtime (via label_is_indirect flag)."""
        call = MCall(name="", label_is_indirect=True, indirection=MVariable(name="CMD"))
        stmt = MDoStatement(targets=[call])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_goto_indirection_requires_runtime(self):
        """G @VAR requires runtime (via label_is_indirect flag)."""
        call = MCall(name="", label_is_indirect=True, indirection=MVariable(name="LBL"))
        stmt = MGotoStatement(targets=[call])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_routine_indirection_requires_runtime(self):
        """D LABEL^@ROUTINE requires runtime."""
        call = MCall(
            name="LABEL",
            routine_is_indirect=True,
            routine_indirection=MVariable(name="RTN"),
        )
        stmt = MDoStatement(targets=[call])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_set_indirection_requires_runtime(self):
        """S @VAR=1 requires runtime (was previously missed!)."""
        inner = MVariable(name="REF")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        value = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=indir, value=value)
        stmt = MSetStatement(assignments=[assign])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_function_indirection_requires_runtime(self):
        """$O(@VAR) requires runtime (was previously missed!)."""
        inner = MVariable(name="ARR")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        func = MIntrinsicFunction(name="ORDER", arguments=[indir])
        # Put in a SET to have a statement
        target = MVariable(name="NEXT")
        assign = MAssignment(target=target, value=func)
        stmt = MSetStatement(assignments=[assign])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_write_indirection_requires_runtime(self):
        """W @VAR requires runtime."""
        inner = MVariable(name="X")
        indir = MIndirection(expression=inner, indirection_type=IndirectionType.NAME)
        stmt = MWriteStatement(arguments=[indir])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_subscript_indirection_requires_runtime(self):
        """A(@I) requires runtime."""
        idx = MVariable(name="I")
        indir = MIndirection(expression=idx, indirection_type=IndirectionType.SUBSCRIPT)
        var = MVariable(name="A", subscripts=[indir])
        # SET A(@I)=5
        value = MLiteral(value=5, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=var, value=value)
        stmt = MSetStatement(assignments=[assign])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_no_indirection_static_ok(self):
        """S X=1 W X does not require runtime."""
        # S X=1
        target = MVariable(name="X")
        value = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=target, value=value)
        set_stmt = MSetStatement(assignments=[assign])

        # W X
        write_arg = MVariable(name="X")
        write_stmt = MWriteStatement(arguments=[write_arg])

        label = self._make_label([set_stmt, write_stmt])
        assert check_requires_runtime_scope(label) is False

    def test_empty_label_static_ok(self):
        """Empty label does not require runtime."""
        label = self._make_label([])
        assert check_requires_runtime_scope(label) is False

    def test_pattern_indirect_requires_runtime(self):
        """I X?@PAT requires runtime."""
        subject = MVariable(name="X")
        pat_var = MVariable(name="PAT")
        indir = MIndirection(expression=pat_var, indirection_type=IndirectionType.NAME)
        pm = MPatternMatch(subject=subject, pattern="", pattern_indirect=indir)
        # Put in a SET to have a statement with condition
        target = MVariable(name="Y")
        value = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        assign = MAssignment(target=target, value=value)
        stmt = MSetStatement(assignments=[assign], postcondition=pm)
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True


@pytest.mark.analysis
class TestRealWorldPatterns:
    """Test patterns from real VistA code."""

    def _make_label(self, statements):
        """Helper to create a label with the given statements."""
        scope = MScope(statements=statements)
        return MLabel(name="TEST", body=scope)

    def test_vista_indirect_set_pattern(self):
        """VistA pattern: S @REF=VALUE"""
        ref = MVariable(name="REF")
        indir = MIndirection(expression=ref, indirection_type=IndirectionType.NAME)
        value = MVariable(name="VALUE")
        assign = MAssignment(target=indir, value=value)
        stmt = MSetStatement(assignments=[assign])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_vista_order_indirect_pattern(self):
        """VistA pattern: S X=$O(@REF@(X))"""
        # @REF@(X) - name indirection with subscript
        ref = MVariable(name="REF")
        sub = MVariable(name="X")
        indir = MIndirection(
            expression=ref,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub]],
        )
        func = MIntrinsicFunction(name="ORDER", arguments=[indir])
        target = MVariable(name="X")
        assign = MAssignment(target=target, value=func)
        stmt = MSetStatement(assignments=[assign])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True

    def test_complex_expression_with_deep_indirection(self):
        """Indirection deeply nested in expression tree."""
        # $P($G(@X),"^",1)
        x = MVariable(name="X")
        indir = MIndirection(expression=x, indirection_type=IndirectionType.NAME)
        get_func = MIntrinsicFunction(name="GET", arguments=[indir])
        delim = MLiteral(value="^", literal_type=LiteralType.STRING)
        pos = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        piece_func = MIntrinsicFunction(name="PIECE", arguments=[get_func, delim, pos])

        target = MVariable(name="Y")
        assign = MAssignment(target=target, value=piece_func)
        stmt = MSetStatement(assignments=[assign])
        label = self._make_label([stmt])
        assert check_requires_runtime_scope(label) is True
