"""Tests for Operators parsing (§7.2).

Tests verify the textX grammar correctly captures operator syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.2
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture(scope="module")
def expr_metamodel():
    """Create expression metamodel for parsing."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
class TestBinaryOperators:
    """Test binary operator parsing (§7.2)."""

    def test_addition_operator(self, expr_metamodel):
        """Addition + operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("1+2", "Expr")
        assert model is not None

    def test_subtraction_operator(self, expr_metamodel):
        """Subtraction - operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X-Y", "Expr")
        assert model is not None

    def test_multiplication_operator(self, expr_metamodel):
        """Multiplication * operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("A*B", "Expr")
        assert model is not None

    def test_division_operator(self, expr_metamodel):
        """Division / operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X/Y", "Expr")
        assert model is not None

    def test_integer_division_operator(self, expr_metamodel):
        """Integer division \\ operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X\\Y", "Expr")
        assert model is not None

    def test_modulo_operator(self, expr_metamodel):
        """Modulo # operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X#Y", "Expr")
        assert model is not None

    def test_exponentiation_operator(self, expr_metamodel):
        """Exponentiation ** operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X**2", "Expr")
        assert model is not None

    def test_concatenation_operator(self, expr_metamodel):
        """Concatenation _ operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("A_B", "Expr")
        assert model is not None

    def test_equality_operator(self, expr_metamodel):
        """Equality = operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X=Y", "Expr")
        assert model is not None

    def test_less_than_operator(self, expr_metamodel):
        """Less than < operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X<Y", "Expr")
        assert model is not None

    def test_greater_than_operator(self, expr_metamodel):
        """Greater than > operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X>Y", "Expr")
        assert model is not None

    def test_logical_and_operator(self, expr_metamodel):
        """Logical AND & operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("A&B", "Expr")
        assert model is not None

    def test_logical_or_operator(self, expr_metamodel):
        """Logical OR ! operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("A!B", "Expr")
        assert model is not None

    def test_not_equal_operator(self, expr_metamodel):
        """Not equal '= operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X'=Y", "Expr")
        assert model is not None

    def test_left_to_right_evaluation(self, expr_metamodel):
        """Left-to-right evaluation order parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("1+2*3", "Expr")
        assert model is not None

    # ---- Remaining operators not covered by migrated tests ----

    def test_contains_operator(self, expr_metamodel):
        """Contains [ operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X[Y", "Expr")
        assert model is not None
        # Verify binary operator with [ operand
        assert len(model.tail) == 1
        assert model.tail[0].op is not None

    def test_follows_operator(self, expr_metamodel):
        """Follows ] operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X]Y", "Expr")
        assert model is not None
        assert len(model.tail) == 1
        assert model.tail[0].op is not None

    def test_sorts_after_operator(self, expr_metamodel):
        """Sorts after ]] operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X]]Y", "Expr")
        assert model is not None
        assert len(model.tail) == 1
        assert model.tail[0].op is not None

    def test_not_contains_operator(self, expr_metamodel):
        """Not contains '[ operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("X'[Y", "Expr")
        assert model is not None
        assert len(model.tail) == 1
        assert model.tail[0].op is not None


@pytest.mark.parser
class TestUnaryOperators:
    """Test unary operator parsing (§7.2)."""

    def test_logical_not_operator(self, expr_metamodel):
        """Logical NOT ' operator parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("'X", "Expr")
        assert model is not None

    def test_unary_plus(self, expr_metamodel):
        """Unary plus +X parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("+X", "Expr")
        assert model is not None

    def test_unary_minus(self, expr_metamodel):
        """Unary minus -X parses correctly (§7.2)."""
        model = expr_metamodel.model_from_str("-X", "Expr")
        assert model is not None

    def test_double_negative(self, expr_metamodel):
        """Parse double unary minus (chained unary operators are valid MUMPS syntax)."""
        model = expr_metamodel.model_from_str("--X", "Expr")
        assert model is not None
        # Verify we got two unary operators
        assert hasattr(model, "left")
        assert hasattr(model.left, "operators")
        assert len(model.left.operators) == 2

    def test_triple_negative(self, expr_metamodel):
        """Parse triple unary minus."""
        model = expr_metamodel.model_from_str("---X", "Expr")
        assert model is not None
        assert len(model.left.operators) == 3

    def test_double_not(self, expr_metamodel):
        """Parse double logical NOT (chained unary operators are valid MUMPS syntax)."""
        model = expr_metamodel.model_from_str("''X", "Expr")
        assert model is not None
        assert len(model.left.operators) == 2

    def test_mixed_unary_plus_minus(self, expr_metamodel):
        """Parse mixed unary +- operators."""
        model = expr_metamodel.model_from_str("+-X", "Expr")
        assert model is not None
        assert len(model.left.operators) == 2

    def test_not_then_minus(self, expr_metamodel):
        """Parse NOT followed by minus."""
        model = expr_metamodel.model_from_str("'-X", "Expr")
        assert model is not None
        assert len(model.left.operators) == 2


@pytest.mark.parser
class TestChainedUnarySemantics:
    """Test that chained unary operators produce correct ASG structure (§7.2)."""

    def test_double_negative_asg(self, expr_metamodel):
        """Verify --X produces nested MUnaryOp nodes."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("--X", "Expr")
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

    def test_double_not_asg(self, expr_metamodel):
        """Verify ''X produces nested MUnaryOp nodes."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("''X", "Expr")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Should be MUnaryOp("'", MUnaryOp("'", Variable))
        assert isinstance(result, MUnaryOp)
        assert result.operator == "'"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "'"
        # The innermost operand is a LocalVariable (textX class)
        assert result.operand.operand.name == "X"

    def test_triple_negative_asg(self, expr_metamodel):
        """Verify ---X produces 3 nested MUnaryOp nodes (from V1UO4B)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("---2", "Expr")
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

    def test_triple_not_asg(self, expr_metamodel):
        """Verify '''0 produces 3 nested MUnaryOp nodes (from V1UO4B)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("'''0", "Expr")
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

    def test_mixed_negate_not_asg(self, expr_metamodel):
        """Verify -'0 produces MUnaryOp('-', MUnaryOp("'", Literal)) (from V1UO4A)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("-'0", "Expr")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Outer is negate, inner is not
        assert isinstance(result, MUnaryOp)
        assert result.operator == "-"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "'"
        # value is int 0, not string "0"
        assert result.operand.operand.value == 0

    def test_mixed_not_negate_asg(self, expr_metamodel):
        """Verify '-0 produces MUnaryOp("'", MUnaryOp('-', Literal)) (from V1UO4A)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("'-0", "Expr")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Outer is not, inner is negate
        assert isinstance(result, MUnaryOp)
        assert result.operator == "'"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "-"
        # value is int 0, not string "0"
        assert result.operand.operand.value == 0

    def test_mixed_positive_not_asg(self, expr_metamodel):
        """Verify +'0 produces MUnaryOp('+', MUnaryOp("'", Literal)) (from V1UO4A)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("+'0", "Expr")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Outer is positive, inner is not
        assert isinstance(result, MUnaryOp)
        assert result.operator == "+"
        assert isinstance(result.operand, MUnaryOp)
        assert result.operand.operator == "'"
        # value is int 0, not string "0"
        assert result.operand.operand.value == 0

    def test_complex_chain_asg(self, expr_metamodel):
        """Verify -'+'-'+'-4.5 produces 9 nested MUnaryOp nodes (from V1UO4B)."""
        from m2py.analysis.semantic_analyzer import SemanticAnalyzer
        from m2py.asg.expressions import MUnaryOp

        model = expr_metamodel.model_from_str("-'+'-'+'-4.5", "Expr")
        analyzer = SemanticAnalyzer()
        result = analyzer.analyze(model, None)

        # Count depth and collect operators
        depth = 0
        node = result
        ops = []
        while isinstance(node, MUnaryOp):
            ops.append(node.operator)
            depth += 1
            node = node.operand

        # Should have 9 operators: -, ', +, ', -, ', +, ', -
        assert depth == 9
        assert ops == ["-", "'", "+", "'", "-", "'", "+", "'", "-"]
        # Innermost should be 4.5 (float, not string)
        assert node.value == 4.5


@pytest.mark.parser
class TestParentheses:
    """Test parenthesized expressions (§7.2)."""

    def test_simple_parens(self, expr_metamodel):
        """Parse (expr)."""
        model = expr_metamodel.model_from_str("(X+Y)", "Expr")
        assert model is not None

    def test_nested_parens(self, expr_metamodel):
        """Parse nested parentheses."""
        model = expr_metamodel.model_from_str("((X+Y)*Z)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestComplexExpressions:
    """Test complex expression parsing (§7.2)."""

    def test_complex_arithmetic(self, expr_metamodel):
        """Parse complex arithmetic expression."""
        model = expr_metamodel.model_from_str("A+B*C-D/E", "Expr")
        assert model is not None

    def test_function_in_expression(self, expr_metamodel):
        """Parse function call within expression."""
        model = expr_metamodel.model_from_str("$LENGTH(X)+1", "Expr")
        assert model is not None

    def test_subscripted_in_expression(self, expr_metamodel):
        """Parse subscripted variable in expression."""
        model = expr_metamodel.model_from_str("A(I)+B(J)", "Expr")
        assert model is not None


@pytest.mark.parser
class TestNotContainsOperatorGrammar:
    """Test 'not contains' operator '[ via MUMPSParser."""

    def test_not_contains_variables(self):
        """X'[Y should parse as not-contains binary op."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tI X'[Y\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MIfStatement"

    def test_not_contains_string(self):
        """'"12345678"'[ans should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tI "12345678"\'[ans\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
