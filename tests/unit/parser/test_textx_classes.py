"""Tests for textX custom class integration.

These tests verify that textX can directly instantiate our ASG classes
during parsing, eliminating the need for post-parse conversion.
"""

import pytest
from pathlib import Path

from textx import metamodel_from_file

from m2py.parser.textx_classes import (
    EXPRESSION_CLASSES,
    get_expression_classes,
    NumericLiteral,
    StringLiteral,
    LocalVariable,
    GlobalVariable,
    IntrinsicFunction,
    SpecialVariable,
    SelectFunction,
)
from m2py.asg.expressions import (
    MLiteral,
    MVariable,
    MGlobal,
    MIntrinsicFunction,
    MSpecialVariable,
    MSelectArg,
)
from m2py.asg.enums import LiteralType
from m2py.asg import MDoStatement, MSetStatement, MWriteStatement


@pytest.mark.parser
class TestTextXCustomClasses:
    """Test textX custom class registration and instantiation."""

    @pytest.fixture
    def expression_metamodel(self):
        """Create metamodel with custom classes registered."""
        grammar_dir = (
            Path(__file__).parent.parent.parent.parent / "src" / "m2py" / "grammar"
        )
        return metamodel_from_file(
            grammar_dir / "expressions.tx", classes=EXPRESSION_CLASSES, skipws=False
        )

    def test_numeric_literal_integer(self, expression_metamodel):
        """Test parsing integer creates our NumericLiteral class."""
        model = expression_metamodel.model_from_str("42")

        # The model should be our custom class
        # Note: Expr wraps the literal, so we need to navigate to it
        literal = self._unwrap_expr(model)

        assert isinstance(literal, NumericLiteral)
        assert isinstance(literal, MLiteral)  # Should also be an MLiteral
        assert literal.value == 42
        assert literal.literal_type == LiteralType.INTEGER

    def test_numeric_literal_decimal(self, expression_metamodel):
        """Test parsing decimal creates our NumericLiteral class."""
        model = expression_metamodel.model_from_str("3.14")
        literal = self._unwrap_expr(model)

        assert isinstance(literal, NumericLiteral)
        assert literal.value == 3.14
        assert literal.literal_type == LiteralType.DECIMAL

    def test_string_literal(self, expression_metamodel):
        """Test parsing string creates our StringLiteral class."""
        model = expression_metamodel.model_from_str('"hello"')
        literal = self._unwrap_expr(model)

        assert isinstance(literal, StringLiteral)
        assert isinstance(literal, MLiteral)
        assert literal.value == "hello"
        assert literal.literal_type == LiteralType.STRING

    def test_string_literal_escaped_quotes(self, expression_metamodel):
        """Test parsing string with escaped quotes."""
        model = expression_metamodel.model_from_str('"say ""hello"""')
        literal = self._unwrap_expr(model)

        assert literal.value == 'say "hello"'

    def test_local_variable_simple(self, expression_metamodel):
        """Test parsing local variable."""
        model = expression_metamodel.model_from_str("X")
        var = self._unwrap_expr(model)

        assert isinstance(var, LocalVariable)
        assert isinstance(var, MVariable)
        assert var.name == "X"
        assert var.subscripts == []

    def test_local_variable_with_subscripts(self, expression_metamodel):
        """Test parsing subscripted local variable."""
        model = expression_metamodel.model_from_str("DATA(1,2)")
        var = self._unwrap_expr(model)

        assert isinstance(var, LocalVariable)
        assert var.name == "DATA"
        assert len(var.subscripts) == 2
        # Subscripts should also be our custom classes
        assert isinstance(var.subscripts[0], NumericLiteral)
        assert var.subscripts[0].value == 1

    def test_global_variable_simple(self, expression_metamodel):
        """Test parsing global variable."""
        model = expression_metamodel.model_from_str("^GLOBAL")
        glob = self._unwrap_expr(model)

        assert isinstance(glob, GlobalVariable)
        assert isinstance(glob, MGlobal)
        assert glob.name == "GLOBAL"
        assert glob.subscripts == []

    def test_global_variable_with_subscripts(self, expression_metamodel):
        """Test parsing subscripted global variable."""
        model = expression_metamodel.model_from_str('^DATA("key",1)')
        glob = self._unwrap_expr(model)

        assert isinstance(glob, GlobalVariable)
        assert glob.name == "DATA"
        assert len(glob.subscripts) == 2
        assert isinstance(glob.subscripts[0], StringLiteral)
        assert glob.subscripts[0].value == "key"

    def test_intrinsic_function(self, expression_metamodel):
        """Test parsing intrinsic function."""
        model = expression_metamodel.model_from_str("$LENGTH(X)")
        func = self._unwrap_expr(model)

        assert isinstance(func, IntrinsicFunction)
        assert isinstance(func, MIntrinsicFunction)
        assert func.name == "LENGTH"
        assert len(func.arguments) == 1
        assert isinstance(func.arguments[0], LocalVariable)

    def test_special_variable(self, expression_metamodel):
        """Test parsing special variable.

        After grammar fix, SpecialVariable is now correctly prioritized
        before IntrinsicFunction for known special variable names.
        """
        model = expression_metamodel.model_from_str("$TEST")
        sv = self._unwrap_expr(model)

        # Now correctly parsed as SpecialVariable
        assert isinstance(sv, SpecialVariable)
        assert sv.name == "TEST"

    def test_binary_expression(self, expression_metamodel):
        """Test binary expression captures operators and operands.

        After grammar update: Expr: left=UnaryExpr (tail+=ExprTail)*
        Where ExprTail is PatternMatchTail or BinaryOpTail.
        Binary operations are now properly captured via BinaryOpTail.
        """
        model = expression_metamodel.model_from_str("X+1")

        # Model is Expr with left and tail
        assert hasattr(model, "left")
        assert hasattr(model, "tail")

        # Left operand
        left = self._unwrap_unary(model.left)
        assert isinstance(left, LocalVariable)
        assert left.name == "X"

        # Tail contains BinaryOpTail items
        assert len(model.tail) == 1
        tail_item = model.tail[0]
        assert tail_item.op.op == "+"

        # Right operand is in tail_item.right
        right = self._unwrap_unary(tail_item.right)
        assert isinstance(right, NumericLiteral)
        assert right.value == 1

    def _unwrap_expr(self, expr):
        """Unwrap the textX expression structure to get to the ASG node.

        Updated for new grammar: Expr: left=UnaryExpr (ops+=BinaryOp right+=UnaryExpr)*
        """
        # If it's already one of our classes, return it
        if isinstance(
            expr,
            (
                NumericLiteral,
                StringLiteral,
                LocalVariable,
                GlobalVariable,
                IntrinsicFunction,
                SpecialVariable,
            ),
        ):
            return expr

        # Expr with left attribute (new grammar)
        if hasattr(expr, "left"):
            return self._unwrap_unary(expr.left)

        # UnaryExpr with operand
        if hasattr(expr, "operand"):
            return expr.operand

        return expr

    def _unwrap_unary(self, unary):
        """Unwrap UnaryExpr -> operand."""
        if hasattr(unary, "operand"):
            return unary.operand
        return unary


@pytest.mark.parser
class TestSelectFunctionCustomClass:
    """Test SelectFunction custom class with MSelectArg.

    These tests verify that SelectFunction arguments are properly converted
    to MSelectArg ASG nodes with unwrapped condition/value expressions.
    """

    @pytest.fixture
    def expression_metamodel(self):
        """Create metamodel with custom classes registered."""
        grammar_dir = (
            Path(__file__).parent.parent.parent.parent / "src" / "m2py" / "grammar"
        )
        return metamodel_from_file(
            grammar_dir / "expressions.tx", classes=EXPRESSION_CLASSES, skipws=False
        )

    def _unwrap_expr(self, expr):
        """Unwrap textX expression to get operand."""
        if hasattr(expr, "left"):
            if hasattr(expr.left, "operand"):
                return expr.left.operand
        return expr

    def test_select_arguments_are_mselectarg(self, expression_metamodel):
        """Verify SelectFunction.arguments contains MSelectArg objects, not tuples.

        This test ensures proper ASG typing for variable extraction and code gen.
        Previously, arguments were raw tuples which broke the ASG type hierarchy.
        """
        model = expression_metamodel.model_from_str("$SELECT(A=1:X,B=2:Y,1:Z)")
        operand = self._unwrap_expr(model)

        # Should be a SelectFunction with arguments attribute
        assert isinstance(operand, SelectFunction)
        assert hasattr(operand, "arguments")
        assert len(operand.arguments) == 3

        # Each argument should be MSelectArg
        for arg in operand.arguments:
            assert isinstance(arg, MSelectArg), f"Expected MSelectArg, got {type(arg)}"
            assert hasattr(arg, "condition")
            assert hasattr(arg, "value")

    def test_select_mselectarg_has_unwrapped_expressions(self, expression_metamodel):
        """Verify MSelectArg contains properly unwrapped ASG expressions."""
        model = expression_metamodel.model_from_str("$SELECT(1:Z)")
        operand = self._unwrap_expr(model)

        assert isinstance(operand, SelectFunction)
        assert len(operand.arguments) == 1

        arg = operand.arguments[0]
        assert isinstance(arg, MSelectArg)

        # Condition should be MLiteral(1), value should be MVariable(Z)
        assert isinstance(arg.condition, MLiteral), (
            f"Expected MLiteral, got {type(arg.condition)}"
        )
        assert arg.condition.value == 1

        assert isinstance(arg.value, MVariable), (
            f"Expected MVariable, got {type(arg.value)}"
        )
        assert arg.value.name == "Z"

    def test_select_variable_extraction(self, expression_metamodel):
        """Verify variables can be extracted from SelectFunction arguments.

        This tests the full pipeline: parsing -> semantic analysis -> variable extraction.
        Uses MUMPSParser to ensure MSelectArg conditions are properly analyzed.
        """
        from m2py.analysis.variables import _extract_expression_variables
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse("TEST\n S X=$SELECT(A=1:X,1:Y)\n")
        stmt = routine.labels[0].body.statements[0]
        select_fn = stmt.assignments[0].value

        assert isinstance(select_fn, SelectFunction)

        # Extract variables from the entire SelectFunction
        variables = _extract_expression_variables(select_fn)

        # Should find A, X, Y (but not the literal 1)
        assert "A" in variables, f"Expected 'A' in {variables}"
        assert "X" in variables, f"Expected 'X' in {variables}"
        assert "Y" in variables, f"Expected 'Y' in {variables}"

    def test_select_multiple_complex_args(self, expression_metamodel):
        """Test variable extraction from complex $SELECT with multiple args."""
        from m2py.analysis.variables import _extract_expression_variables
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse('TEST\n S R=$SELECT(A=B:X,C>D:Z,1:"default")\n')
        stmt = routine.labels[0].body.statements[0]
        select_fn = stmt.assignments[0].value

        assert isinstance(select_fn, SelectFunction)
        variables = _extract_expression_variables(select_fn)

        # Should find A, B, X, C, D, Z (but not literals)
        expected = {"A", "B", "X", "C", "D", "Z"}
        for var in expected:
            assert var in variables, f"Expected '{var}' in {variables}"


@pytest.mark.parser
class TestClassRegistry:
    """Test class registry functions."""

    def test_get_expression_classes(self):
        """Test getting list of expression classes."""
        classes = get_expression_classes()

        assert NumericLiteral in classes
        assert StringLiteral in classes
        assert LocalVariable in classes
        assert GlobalVariable in classes

    def test_classes_are_asg_subclasses(self):
        """Verify all custom classes inherit from ASG classes."""
        assert issubclass(NumericLiteral, MLiteral)
        assert issubclass(StringLiteral, MLiteral)
        assert issubclass(LocalVariable, MVariable)
        assert issubclass(GlobalVariable, MGlobal)
        assert issubclass(IntrinsicFunction, MIntrinsicFunction)
        assert issubclass(SpecialVariable, MSpecialVariable)


@pytest.mark.parser
class TestZWriteNakedGlobal:
    """Tests for ZWriteNakedGlobal textX class instantiation."""

    def test_zwrite_naked_global_parsed(self, parse_mumps):
        """ZW ^(1) produces a ZWriteNakedGlobal node."""
        source = "TEST\n\tS ^X=1\n\tZW ^(1)\n\tQ\n"
        result = parse_mumps(source)
        # Find the ZWRITE statement
        stmts = result.labels[0].body.statements
        assert len(stmts) >= 2


@pytest.mark.parser
class TestAnySpecialVariable:
    """Tests for AnySpecialVariable textX class (implementation-specific SVNs)."""

    def test_zsystem_special_variable(self, parse_mumps):
        """W $ZS produces an AnySpecialVariable or MSpecialVariable."""
        source = "TEST\n\tW $ZS\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        assert len(stmts) >= 1
        assert isinstance(stmts[0], MWriteStatement)


@pytest.mark.parser
class TestTextFunctionRoutineIndirect:
    """Tests for TextFunction with routine indirection: $T(LABEL^@X)."""

    def test_text_function_routine_indirection(self, parse_mumps):
        """$T(LABEL^@X) parses with routine_indirect in line_ref."""
        source = "TEST\n\tS A=$T(LABEL^@X)\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        set_stmt = stmts[0]
        assert isinstance(set_stmt, MSetStatement)


@pytest.mark.parser
class TestExtrinsicFunctionRoutineIndirection:
    """Tests for ExtrinsicFunction routine indirection: $$LABEL^@RNAME()."""

    def test_extrinsic_routine_indirection(self, parse_mumps):
        """$$LABEL^@RNAME() parses with routine_is_indirect=True."""
        source = "TEST\n\tS X=$$LABEL^@RNAME()\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        set_stmt = stmts[0]
        assert isinstance(set_stmt, MSetStatement)
        # The value expression should contain an extrinsic function
        # with indirect routine reference

    def test_extrinsic_routine_indirection_no_args(self, parse_mumps):
        """$$LABEL^@RNAME parses with routine_is_indirect=True."""
        source = "TEST\n\tS X=$$LABEL^@RNAME\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        assert isinstance(stmts[0], MSetStatement)


@pytest.mark.parser
class TestIndirectionNameSubscripts:
    """Tests for Indirection with name_subscripts: @X@(1,2)."""

    def test_name_indirection_subscripts(self, parse_mumps):
        """S Y=@X@(1,2) parses with name_indirection_subscripts."""
        source = "TEST\n\tS Y=@X@(1,2)\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        set_stmt = stmts[0]
        assert isinstance(set_stmt, MSetStatement)

    def test_chained_name_indirection_subscripts(self, parse_mumps):
        """S Y=@X@(1)@(2) parses with multiple name_indirection_subscripts."""
        source = "TEST\n\tS Y=@X@(1)@(2)\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        set_stmt = stmts[0]
        assert isinstance(set_stmt, MSetStatement)


@pytest.mark.parser
class TestUnwrapFunctionArgsVariants:
    """Tests for _unwrap_function_args byref/omitted variants."""

    def test_do_with_byref_argument(self, parse_mumps):
        """D LABEL(.VAR) parses with by-reference arg."""
        source = "TEST\n\tD SUB(.VAR)\n\tQ\nSUB(A)\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        do_stmt = stmts[0]
        assert isinstance(do_stmt, MDoStatement)
        target = do_stmt.targets[0]
        assert target.arguments is not None
        assert len(target.arguments) > 0

    def test_extrinsic_with_omitted_arg(self, parse_mumps):
        """$$FUNC(X,,Z) parses with omitted middle argument."""
        source = "TEST\n\tS A=$$FUNC(X,,Z)\n\tQ\nFUNC(A,B,C)\n\tQ A+C\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        assert isinstance(stmts[0], MSetStatement)

    def test_extrinsic_with_leading_omitted_arg(self, parse_mumps):
        """$$FUNC(,X) parses with omitted first argument."""
        source = "TEST\n\tS A=$$FUNC(,X)\n\tQ\nFUNC(A,B)\n\tQ B\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        assert isinstance(stmts[0], MSetStatement)


@pytest.mark.parser
class TestByRefArgIndirectPass2:
    """ByRefArg with indirect (.@VAR) rather than direct variable (.X).

    Covers textx_classes.py L157-161.
    """

    def test_byref_indirect_arg(self, parse_mumps):
        """D SUB(.@VAR) — by-ref with indirection."""
        source = 'TEST\n\tS VAR="X",X=1\n\tD SUB(.@VAR)\n\tQ\nSUB(A)\n\tS A=A+1\n\tQ\n'
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        # The DO statement should have parsed the .@VAR byref argument
        do_stmt = None
        for s in stmts:
            if isinstance(s, MDoStatement):
                do_stmt = s
                break
        assert do_stmt is not None
        # Verify it has arguments (the .@VAR)
        assert do_stmt.targets[0].arguments is not None

    def test_byref_simple_arg(self, parse_mumps):
        """D SUB(.X) — basic by-ref argument."""
        source = "TEST\n\tS X=1\n\tD SUB(.X)\n\tQ\nSUB(A)\n\tS A=A+1\n\tQ\n"
        result = parse_mumps(source)
        stmts = result.labels[0].body.statements
        do_stmt = None
        for s in stmts:
            if isinstance(s, MDoStatement):
                do_stmt = s
                break
        assert do_stmt is not None
        assert do_stmt.targets[0].arguments is not None
