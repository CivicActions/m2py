"""Tests for Operators parsing (§7.2).

Tests verify the textX grammar correctly captures operator syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.2

Migrated from:
- tests/unit/test_expression_grammar.py::TestBinaryOperators
- tests/unit/test_expression_grammar.py::TestUnaryOperators
- tests/unit/test_expression_grammar.py::TestChainedUnarySemantics
- tests/unit/test_grammar.py::TestNotContainsOperatorGrammar
- tests/unit/test_special_constructs.py::TestComplexExpressions
"""

import pytest

from m2py.asg import MRoutine
from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestBinaryOperators:
    """Test binary operator parsing (§7.2).

    Migrated from test_expression_grammar.py::TestBinaryOperators
    """

    def test_addition(self, parse_expression):
        """Parse addition (§7.2)."""
        model = parse_expression("1+2")
        assert model is not None

    def test_subtraction(self, parse_expression):
        """Parse subtraction (§7.2)."""
        model = parse_expression("X-Y")
        assert model is not None

    def test_multiplication(self, parse_expression):
        """Parse multiplication (§7.2)."""
        model = parse_expression("A*B")
        assert model is not None

    def test_division(self, parse_expression):
        """Parse division (§7.2)."""
        model = parse_expression("X/Y")
        assert model is not None

    def test_integer_division(self, parse_expression):
        """Parse integer division (§7.2)."""
        model = parse_expression("X\\Y")
        assert model is not None

    def test_modulo(self, parse_expression):
        """Parse modulo (§7.2)."""
        model = parse_expression("X#Y")
        assert model is not None

    def test_power(self, parse_expression):
        """Parse exponentiation (§7.2)."""
        model = parse_expression("X**2")
        assert model is not None

    def test_concatenation(self, parse_expression):
        """Parse string concatenation (§7.2)."""
        model = parse_expression("A_B")
        assert model is not None

    def test_equality(self, parse_expression):
        """Parse equality comparison (§7.2)."""
        model = parse_expression("X=Y")
        assert model is not None

    def test_less_than(self, parse_expression):
        """Parse less than (§7.2)."""
        model = parse_expression("X<Y")
        assert model is not None

    def test_greater_than(self, parse_expression):
        """Parse greater than (§7.2)."""
        model = parse_expression("X>Y")
        assert model is not None

    def test_logical_and(self, parse_expression):
        """Parse logical AND (§7.2)."""
        model = parse_expression("A&B")
        assert model is not None

    def test_logical_or(self, parse_expression):
        """Parse logical OR (§7.2)."""
        model = parse_expression("A!B")
        assert model is not None

    def test_not_equal(self, parse_expression):
        """Parse not equal (§7.2)."""
        model = parse_expression("X'=Y")
        assert model is not None

    def test_chain_left_to_right(self, parse_expression):
        """Parse chained operators (MUMPS is L-to-R, no precedence) (§7.2)."""
        model = parse_expression("1+2*3")
        assert model is not None


@pytest.mark.parser
class TestUnaryOperators:
    """Test unary operator parsing (§7.2).

    Migrated from test_expression_grammar.py::TestUnaryOperators
    """

    def test_not(self, parse_expression):
        """Parse logical NOT (§7.2)."""
        model = parse_expression("'X")
        assert model is not None

    def test_positive(self, parse_expression):
        """Parse unary plus (§7.2)."""
        model = parse_expression("+X")
        assert model is not None

    def test_negative(self, parse_expression):
        """Parse unary minus (§7.2)."""
        model = parse_expression("-X")
        assert model is not None

    def test_double_negative(self, parse_expression):
        """Parse double unary minus (chained unary operators are valid MUMPS syntax) (§7.2)."""
        model = parse_expression("--X")
        assert model is not None
        # Verify we got two unary operators
        assert hasattr(model, "left")
        assert hasattr(model.left, "operators")
        assert len(model.left.operators) == 2

    def test_triple_negative(self, parse_expression):
        """Parse triple unary minus (§7.2)."""
        model = parse_expression("---X")
        assert model is not None
        assert len(model.left.operators) == 3

    def test_double_not(self, parse_expression):
        """Parse double logical NOT (chained unary operators are valid MUMPS syntax) (§7.2)."""
        model = parse_expression("''X")
        assert model is not None
        assert len(model.left.operators) == 2

    def test_mixed_unary_plus_minus(self, parse_expression):
        """Parse mixed unary +- operators (§7.2)."""
        model = parse_expression("+-X")
        assert model is not None
        assert len(model.left.operators) == 2

    def test_not_then_minus(self, parse_expression):
        """Parse NOT followed by minus (§7.2)."""
        model = parse_expression("'-X")
        assert model is not None
        assert len(model.left.operators) == 2


@pytest.mark.parser
class TestChainedUnarySemantics:
    """Test that chained unary operators produce correct ASG structure (§7.2).

    Migrated from test_expression_grammar.py::TestChainedUnarySemantics
    """

    def test_double_negative_asg(self, parse_expression):
        """Verify --X produces nested MUnaryOp nodes (§7.2)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = parse_expression("--X")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Should be MUnaryOp('-', MUnaryOp('-', Variable))
        assert isinstance(result, MUnaryOp)
        assert result.operator == "-"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "-"
        # The innermost operand is a LocalVariable (textX class)
        # It has a name attribute we can check
        assert result.operand.operand.name == "X"

    def test_double_not_asg(self, parse_expression):
        """Verify ''X produces nested MUnaryOp nodes (§7.2)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = parse_expression("''X")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Should be MUnaryOp("'", MUnaryOp("'", Variable))
        assert isinstance(result, MUnaryOp)
        assert result.operator == "'"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "'"
        # The innermost operand is a LocalVariable (textX class)
        assert result.operand.operand.name == "X"

    def test_triple_negative_asg(self, parse_expression):
        """Verify ---X produces 3 nested MUnaryOp nodes (from V1UO4B) (§7.2)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = parse_expression("---2")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Should be MUnaryOp('-', MUnaryOp('-', MUnaryOp('-', Literal)))
        assert isinstance(result, MUnaryOp)
        assert result.operator == "-"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "-"
        assert isinstance(result.operand.operand, MUnaryOp)
        assert result.operand.operand.operator == "-"
        # Innermost is the numeric literal (value is int, not string)
        assert result.operand.operand.operand.value == 2

    def test_triple_not_asg(self, parse_expression):
        """Verify '''0 produces 3 nested MUnaryOp nodes (from V1UO4B) (§7.2)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = parse_expression("'''0")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Should be MUnaryOp("'", MUnaryOp("'", MUnaryOp("'", Literal)))
        assert isinstance(result, MUnaryOp)
        assert result.operator == "'"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "'"
        assert isinstance(result.operand.operand, MUnaryOp)
        assert result.operand.operand.operator == "'"
        # value is int 0, not string "0"
        assert result.operand.operand.operand.value == 0


@pytest.mark.parser
class TestNotContainsOperatorGrammar:
    """Test 'not contains' operator '[ (§7.2).

    Migrated from: tests/unit/test_grammar.py::TestNotContainsOperatorGrammar
    """

    def test_not_contains_variables(self):
        """X'[Y should parse as not-contains binary op (§7.2)."""
        parser = MUMPSParser()
        source = "LABEL\tI X'[Y\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MIfStatement"

    def test_not_contains_string(self):
        """'\"12345678\"'[ans should parse (§7.2)."""
        parser = MUMPSParser()
        source = 'LABEL\tI "12345678"\'[ans\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestComplexExpressions:
    """Tests for complex expression combinations (§7.2).

    Migrated from: tests/unit/test_special_constructs.py::TestComplexExpressions
    """

    def test_function_in_subscript(self, parse_expression):
        """^DATA($ORDER(^DATA(\"\"))) (§7.2).

        Migrated from: tests/unit/test_special_constructs.py::TestComplexExpressions
        """
        model = parse_expression('^DATA($ORDER(^DATA("")))')
        assert model is not None

    def test_piece_concatenation(self, parse_expression):
        """$PIECE(X,\"^\",1)_\"-\"_$PIECE(X,\"^\",2) (§7.2).

        Migrated from: tests/unit/test_special_constructs.py::TestComplexExpressions
        """
        model = parse_expression('$PIECE(X,"^",1)_"-"_$PIECE(X,"^",2)')
        assert model is not None

    def test_conditional_in_function(self, parse_expression):
        """$SELECT with simple expressions (§7.2).

        Migrated from: tests/unit/test_special_constructs.py::TestComplexExpressions
        """
        model = parse_expression("$SELECT(A,B,C)")
        assert model is not None

    def test_indirection_in_function(self, parse_expression):
        """$DATA(@X) (§7.2).

        Migrated from: tests/unit/test_special_constructs.py::TestComplexExpressions
        """
        model = parse_expression("$DATA(@X)")
        assert model is not None

    def test_extrinsic_in_expression(self, parse_expression):
        """A+$$FUNC(B)*C (§7.2).

        Migrated from: tests/unit/test_special_constructs.py::TestComplexExpressions
        """
        model = parse_expression("A+$$FUNC(B)*C")
        assert model is not None
