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
    get_class_for_rule,
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
)
from m2py.asg.enums import LiteralType


class TestTextXCustomClasses:
    """Test textX custom class registration and instantiation."""

    @pytest.fixture
    def expression_metamodel(self):
        """Create metamodel with custom classes registered."""
        grammar_dir = Path(__file__).parent.parent.parent / "src" / "m2py" / "grammar"
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


class TestSelectFunctionCustomClass:
    """Test SelectFunction custom class with MSelectArg.

    These tests verify that SelectFunction arguments are properly converted
    to MSelectArg ASG nodes with unwrapped condition/value expressions.
    """

    @pytest.fixture
    def expression_metamodel(self):
        """Create metamodel with custom classes registered."""
        grammar_dir = Path(__file__).parent.parent.parent / "src" / "m2py" / "grammar"
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
        from m2py.asg.expressions import MSelectArg

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
        from m2py.asg.expressions import MSelectArg, MVariable, MLiteral

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


class TestClassRegistry:
    """Test class registry functions."""

    def test_get_expression_classes(self):
        """Test getting list of expression classes."""
        classes = get_expression_classes()

        assert NumericLiteral in classes
        assert StringLiteral in classes
        assert LocalVariable in classes
        assert GlobalVariable in classes

    def test_get_class_for_rule(self):
        """Test getting class by rule name."""
        assert get_class_for_rule("NumericLiteral") is NumericLiteral
        assert get_class_for_rule("LocalVariable") is LocalVariable
        assert get_class_for_rule("UnknownRule") is None

    def test_classes_are_asg_subclasses(self):
        """Verify all custom classes inherit from ASG classes."""
        assert issubclass(NumericLiteral, MLiteral)
        assert issubclass(StringLiteral, MLiteral)
        assert issubclass(LocalVariable, MVariable)
        assert issubclass(GlobalVariable, MGlobal)
        assert issubclass(IntrinsicFunction, MIntrinsicFunction)
        assert issubclass(SpecialVariable, MSpecialVariable)
