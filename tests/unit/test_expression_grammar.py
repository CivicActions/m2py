"""Unit tests for textX expression grammar.

Tests the expression grammar in isolation before integration.
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file


@pytest.fixture
def expr_metamodel():
    """Load the expression grammar metamodel."""
    grammar_path = Path(__file__).parent.parent.parent / "src" / "m2py" / "grammar" / "expressions.tx"
    return metamodel_from_file(str(grammar_path), skipws=True)


class TestNumericLiterals:
    """Test numeric literal parsing."""
    
    def test_integer(self, expr_metamodel):
        """Parse integer literal."""
        model = expr_metamodel.model_from_str('42', 'Expr')
        assert model is not None
    
    def test_decimal(self, expr_metamodel):
        """Parse decimal literal."""
        model = expr_metamodel.model_from_str('3.14', 'Expr')
        assert model is not None
    
    def test_negative_integer(self, expr_metamodel):
        """Parse negative integer (unary minus)."""
        model = expr_metamodel.model_from_str('-42', 'Expr')
        assert model is not None


class TestStringLiterals:
    """Test string literal parsing."""
    
    def test_simple_string(self, expr_metamodel):
        """Parse simple quoted string."""
        model = expr_metamodel.model_from_str('"hello"', 'Expr')
        assert model is not None
    
    def test_empty_string(self, expr_metamodel):
        """Parse empty string."""
        model = expr_metamodel.model_from_str('""', 'Expr')
        assert model is not None
    
    def test_escaped_quote(self, expr_metamodel):
        """Parse string with escaped quote."""
        model = expr_metamodel.model_from_str('"say ""hi"""', 'Expr')
        assert model is not None


class TestLocalVariables:
    """Test local variable parsing."""
    
    def test_simple_variable(self, expr_metamodel):
        """Parse simple variable name."""
        model = expr_metamodel.model_from_str('X', 'Expr')
        assert model is not None
    
    def test_percent_variable(self, expr_metamodel):
        """Parse %-prefixed variable."""
        model = expr_metamodel.model_from_str('%ABC', 'Expr')
        assert model is not None
    
    def test_subscripted_variable(self, expr_metamodel):
        """Parse subscripted variable."""
        model = expr_metamodel.model_from_str('DATA(1,2,3)', 'Expr')
        assert model is not None


class TestGlobalVariables:
    """Test global variable parsing."""
    
    def test_simple_global(self, expr_metamodel):
        """Parse simple global."""
        model = expr_metamodel.model_from_str('^GLOBAL', 'Expr')
        assert model is not None
    
    def test_subscripted_global(self, expr_metamodel):
        """Parse subscripted global."""
        model = expr_metamodel.model_from_str('^DATA(1,2)', 'Expr')
        assert model is not None
    
    def test_naked_global(self, expr_metamodel):
        """Parse naked global reference."""
        model = expr_metamodel.model_from_str('^(1,2)', 'Expr')
        assert model is not None


class TestBinaryOperators:
    """Test binary operator parsing."""
    
    def test_addition(self, expr_metamodel):
        """Parse addition."""
        model = expr_metamodel.model_from_str('1+2', 'Expr')
        assert model is not None
    
    def test_subtraction(self, expr_metamodel):
        """Parse subtraction."""
        model = expr_metamodel.model_from_str('X-Y', 'Expr')
        assert model is not None
    
    def test_multiplication(self, expr_metamodel):
        """Parse multiplication."""
        model = expr_metamodel.model_from_str('A*B', 'Expr')
        assert model is not None
    
    def test_division(self, expr_metamodel):
        """Parse division."""
        model = expr_metamodel.model_from_str('X/Y', 'Expr')
        assert model is not None
    
    def test_integer_division(self, expr_metamodel):
        """Parse integer division."""
        model = expr_metamodel.model_from_str('X\\Y', 'Expr')
        assert model is not None
    
    def test_modulo(self, expr_metamodel):
        """Parse modulo."""
        model = expr_metamodel.model_from_str('X#Y', 'Expr')
        assert model is not None
    
    def test_power(self, expr_metamodel):
        """Parse exponentiation."""
        model = expr_metamodel.model_from_str('X**2', 'Expr')
        assert model is not None
    
    def test_concatenation(self, expr_metamodel):
        """Parse string concatenation."""
        model = expr_metamodel.model_from_str('A_B', 'Expr')
        assert model is not None
    
    def test_equality(self, expr_metamodel):
        """Parse equality comparison."""
        model = expr_metamodel.model_from_str('X=Y', 'Expr')
        assert model is not None
    
    def test_less_than(self, expr_metamodel):
        """Parse less than."""
        model = expr_metamodel.model_from_str('X<Y', 'Expr')
        assert model is not None
    
    def test_greater_than(self, expr_metamodel):
        """Parse greater than."""
        model = expr_metamodel.model_from_str('X>Y', 'Expr')
        assert model is not None
    
    def test_logical_and(self, expr_metamodel):
        """Parse logical AND."""
        model = expr_metamodel.model_from_str('A&B', 'Expr')
        assert model is not None
    
    def test_logical_or(self, expr_metamodel):
        """Parse logical OR."""
        model = expr_metamodel.model_from_str('A!B', 'Expr')
        assert model is not None
    
    def test_not_equal(self, expr_metamodel):
        """Parse not equal."""
        model = expr_metamodel.model_from_str("X'=Y", 'Expr')
        assert model is not None
    
    def test_chain_left_to_right(self, expr_metamodel):
        """Parse chained operators (MUMPS is L-to-R, no precedence)."""
        model = expr_metamodel.model_from_str('1+2*3', 'Expr')
        assert model is not None


class TestUnaryOperators:
    """Test unary operator parsing."""
    
    def test_not(self, expr_metamodel):
        """Parse logical NOT."""
        model = expr_metamodel.model_from_str("'X", 'Expr')
        assert model is not None
    
    def test_positive(self, expr_metamodel):
        """Parse unary plus."""
        model = expr_metamodel.model_from_str('+X', 'Expr')
        assert model is not None
    
    def test_negative(self, expr_metamodel):
        """Parse unary minus."""
        model = expr_metamodel.model_from_str('-X', 'Expr')
        assert model is not None


class TestIntrinsicFunctions:
    """Test intrinsic function parsing."""
    
    def test_length(self, expr_metamodel):
        """Parse $LENGTH function."""
        model = expr_metamodel.model_from_str('$LENGTH(X)', 'Expr')
        assert model is not None
    
    def test_piece(self, expr_metamodel):
        """Parse $PIECE function."""
        model = expr_metamodel.model_from_str('$PIECE(STR,",",1)', 'Expr')
        assert model is not None
    
    def test_extract(self, expr_metamodel):
        """Parse $EXTRACT function."""
        model = expr_metamodel.model_from_str('$EXTRACT(X,1,5)', 'Expr')
        assert model is not None
    
    def test_abbreviated(self, expr_metamodel):
        """Parse abbreviated function ($L for $LENGTH)."""
        model = expr_metamodel.model_from_str('$L(X)', 'Expr')
        assert model is not None


class TestSpecialVariables:
    """Test special variable parsing."""
    
    def test_test(self, expr_metamodel):
        """Parse $TEST."""
        model = expr_metamodel.model_from_str('$TEST', 'Expr')
        assert model is not None
    
    def test_horolog(self, expr_metamodel):
        """Parse $HOROLOG."""
        model = expr_metamodel.model_from_str('$HOROLOG', 'Expr')
        assert model is not None
    
    def test_x(self, expr_metamodel):
        """Parse $X."""
        model = expr_metamodel.model_from_str('$X', 'Expr')
        assert model is not None


class TestIndirection:
    """Test indirection parsing."""
    
    def test_simple_indirection(self, expr_metamodel):
        """Parse simple @variable indirection."""
        model = expr_metamodel.model_from_str('@X', 'Expr')
        assert model is not None
    
    def test_subscript_indirection(self, expr_metamodel):
        """Parse @variable(subscripts) indirection."""
        model = expr_metamodel.model_from_str('@X(1,2)', 'Expr')
        assert model is not None


class TestExtrinsicFunctions:
    """Test extrinsic function parsing."""
    
    def test_local_extrinsic(self, expr_metamodel):
        """Parse $$label() local extrinsic."""
        model = expr_metamodel.model_from_str('$$FUNC(X)', 'Expr')
        assert model is not None
    
    def test_external_extrinsic(self, expr_metamodel):
        """Parse $$label^routine() external extrinsic."""
        model = expr_metamodel.model_from_str('$$FUNC^ROUTINE(X,Y)', 'Expr')
        assert model is not None


class TestParentheses:
    """Test parenthesized expressions."""
    
    def test_simple_parens(self, expr_metamodel):
        """Parse (expr)."""
        model = expr_metamodel.model_from_str('(X+Y)', 'Expr')
        assert model is not None
    
    def test_nested_parens(self, expr_metamodel):
        """Parse nested parentheses."""
        model = expr_metamodel.model_from_str('((X+Y)*Z)', 'Expr')
        assert model is not None


class TestComplexExpressions:
    """Test complex expression parsing."""
    
    def test_complex_arithmetic(self, expr_metamodel):
        """Parse complex arithmetic expression."""
        model = expr_metamodel.model_from_str('A+B*C-D/E', 'Expr')
        assert model is not None
    
    def test_function_in_expression(self, expr_metamodel):
        """Parse function call within expression."""
        model = expr_metamodel.model_from_str('$LENGTH(X)+1', 'Expr')
        assert model is not None
    
    def test_subscripted_in_expression(self, expr_metamodel):
        """Parse subscripted variable in expression."""
        model = expr_metamodel.model_from_str('A(I)+B(J)', 'Expr')
        assert model is not None
