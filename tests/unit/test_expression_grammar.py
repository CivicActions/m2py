"""Tests for the expression grammar (expressions.tx).

Low-level tests that verify the textX expression grammar directly.
Tests literals, variables, operators, functions, and special constructs.

For semantic analysis of expressions, see test_semantic_analyzer.py.
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file


@pytest.fixture
def expr_metamodel():
    """Load the expression grammar metamodel."""
    grammar_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(str(grammar_path), skipws=True)


class TestNumericLiterals:
    """Test numeric literal parsing."""

    def test_integer(self, expr_metamodel):
        """Parse integer literal."""
        model = expr_metamodel.model_from_str("42", "Expr")
        assert model is not None

    def test_decimal(self, expr_metamodel):
        """Parse decimal literal."""
        model = expr_metamodel.model_from_str("3.14", "Expr")
        assert model is not None

    def test_negative_integer(self, expr_metamodel):
        """Parse negative integer (unary minus)."""
        model = expr_metamodel.model_from_str("-42", "Expr")
        assert model is not None


class TestStringLiterals:
    """Test string literal parsing."""

    def test_simple_string(self, expr_metamodel):
        """Parse simple quoted string."""
        model = expr_metamodel.model_from_str('"hello"', "Expr")
        assert model is not None

    def test_empty_string(self, expr_metamodel):
        """Parse empty string."""
        model = expr_metamodel.model_from_str('""', "Expr")
        assert model is not None

    def test_escaped_quote(self, expr_metamodel):
        """Parse string with escaped quote."""
        model = expr_metamodel.model_from_str('"say ""hi"""', "Expr")
        assert model is not None


class TestLocalVariables:
    """Test local variable parsing."""

    def test_simple_variable(self, expr_metamodel):
        """Parse simple variable name."""
        model = expr_metamodel.model_from_str("X", "Expr")
        assert model is not None

    def test_percent_variable(self, expr_metamodel):
        """Parse %-prefixed variable."""
        model = expr_metamodel.model_from_str("%ABC", "Expr")
        assert model is not None

    def test_subscripted_variable(self, expr_metamodel):
        """Parse subscripted variable."""
        model = expr_metamodel.model_from_str("DATA(1,2,3)", "Expr")
        assert model is not None


class TestGlobalVariables:
    """Test global variable parsing."""

    def test_simple_global(self, expr_metamodel):
        """Parse simple global."""
        model = expr_metamodel.model_from_str("^GLOBAL", "Expr")
        assert model is not None

    def test_subscripted_global(self, expr_metamodel):
        """Parse subscripted global."""
        model = expr_metamodel.model_from_str("^DATA(1,2)", "Expr")
        assert model is not None

    def test_naked_global(self, expr_metamodel):
        """Parse naked global reference."""
        model = expr_metamodel.model_from_str("^(1,2)", "Expr")
        assert model is not None


class TestBinaryOperators:
    """Test binary operator parsing."""

    def test_addition(self, expr_metamodel):
        """Parse addition."""
        model = expr_metamodel.model_from_str("1+2", "Expr")
        assert model is not None

    def test_subtraction(self, expr_metamodel):
        """Parse subtraction."""
        model = expr_metamodel.model_from_str("X-Y", "Expr")
        assert model is not None

    def test_multiplication(self, expr_metamodel):
        """Parse multiplication."""
        model = expr_metamodel.model_from_str("A*B", "Expr")
        assert model is not None

    def test_division(self, expr_metamodel):
        """Parse division."""
        model = expr_metamodel.model_from_str("X/Y", "Expr")
        assert model is not None

    def test_integer_division(self, expr_metamodel):
        """Parse integer division."""
        model = expr_metamodel.model_from_str("X\\Y", "Expr")
        assert model is not None

    def test_modulo(self, expr_metamodel):
        """Parse modulo."""
        model = expr_metamodel.model_from_str("X#Y", "Expr")
        assert model is not None

    def test_power(self, expr_metamodel):
        """Parse exponentiation."""
        model = expr_metamodel.model_from_str("X**2", "Expr")
        assert model is not None

    def test_concatenation(self, expr_metamodel):
        """Parse string concatenation."""
        model = expr_metamodel.model_from_str("A_B", "Expr")
        assert model is not None

    def test_equality(self, expr_metamodel):
        """Parse equality comparison."""
        model = expr_metamodel.model_from_str("X=Y", "Expr")
        assert model is not None

    def test_less_than(self, expr_metamodel):
        """Parse less than."""
        model = expr_metamodel.model_from_str("X<Y", "Expr")
        assert model is not None

    def test_greater_than(self, expr_metamodel):
        """Parse greater than."""
        model = expr_metamodel.model_from_str("X>Y", "Expr")
        assert model is not None

    def test_logical_and(self, expr_metamodel):
        """Parse logical AND."""
        model = expr_metamodel.model_from_str("A&B", "Expr")
        assert model is not None

    def test_logical_or(self, expr_metamodel):
        """Parse logical OR."""
        model = expr_metamodel.model_from_str("A!B", "Expr")
        assert model is not None

    def test_not_equal(self, expr_metamodel):
        """Parse not equal."""
        model = expr_metamodel.model_from_str("X'=Y", "Expr")
        assert model is not None

    def test_chain_left_to_right(self, expr_metamodel):
        """Parse chained operators (MUMPS is L-to-R, no precedence)."""
        model = expr_metamodel.model_from_str("1+2*3", "Expr")
        assert model is not None


class TestUnaryOperators:
    """Test unary operator parsing."""

    def test_not(self, expr_metamodel):
        """Parse logical NOT."""
        model = expr_metamodel.model_from_str("'X", "Expr")
        assert model is not None

    def test_positive(self, expr_metamodel):
        """Parse unary plus."""
        model = expr_metamodel.model_from_str("+X", "Expr")
        assert model is not None

    def test_negative(self, expr_metamodel):
        """Parse unary minus."""
        model = expr_metamodel.model_from_str("-X", "Expr")
        assert model is not None

    def test_double_negative(self, expr_metamodel):
        """Parse double unary minus (BUG-002 fix)."""
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
        """Parse double logical NOT (BUG-002 fix)."""
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


class TestChainedUnarySemantics:
    """Test that chained unary operators produce correct ASG structure."""

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
        # Innermost is the numeric literal
        assert result.operand.operand.operand.value == "2"

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
        assert result.operand.operand.operand.value == "0"

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
        assert result.operand.operand.value == "0"

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
        assert result.operand.operand.value == "0"

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
        assert result.operand.operand.value == "0"

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
        # Innermost should be 4.5
        assert node.value == "4.5"


class TestIntrinsicFunctions:
    """Test intrinsic function parsing."""

    def test_length(self, expr_metamodel):
        """Parse $LENGTH function."""
        model = expr_metamodel.model_from_str("$LENGTH(X)", "Expr")
        assert model is not None

    def test_piece(self, expr_metamodel):
        """Parse $PIECE function."""
        model = expr_metamodel.model_from_str('$PIECE(STR,",",1)', "Expr")
        assert model is not None

    def test_extract(self, expr_metamodel):
        """Parse $EXTRACT function."""
        model = expr_metamodel.model_from_str("$EXTRACT(X,1,5)", "Expr")
        assert model is not None

    def test_abbreviated(self, expr_metamodel):
        """Parse abbreviated function ($L for $LENGTH)."""
        model = expr_metamodel.model_from_str("$L(X)", "Expr")
        assert model is not None


class TestCacheSpecificFunctions:
    """Test Caché/IRIS-specific function parsing.

    These are implementation-specific functions found in VistA codebase.
    The grammar accepts them via the generic FUNCNAME pattern.
    """

    def test_li_list_abbreviation(self, expr_metamodel):
        """Parse $LI as Caché $LIST abbreviation."""
        model = expr_metamodel.model_from_str("$LI(X,1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "LI"
        assert len(operand.args.args) == 2

    def test_listget_function(self, expr_metamodel):
        """Parse $LISTGET Caché function."""
        model = expr_metamodel.model_from_str("$LISTGET(X,2,0)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "LISTGET"
        assert len(operand.args.args) == 3

    def test_increment_function(self, expr_metamodel):
        """Parse $INCREMENT Caché atomic increment function."""
        model = expr_metamodel.model_from_str("$INCREMENT(^CTR)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "INCREMENT"
        assert len(operand.args.args) == 1

    def test_namespace_special_var(self, expr_metamodel):
        """Parse $NAMESPACE Caché special variable."""
        model = expr_metamodel.model_from_str("$NAMESPACE", "Expr")
        assert model is not None
        operand = model.left.operand
        # NAMESPACE is not a standard MUMPS special variable,
        # so it parses as IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "NAMESPACE"

    def test_eref_special_var(self, expr_metamodel):
        """Parse $EREF Caché external reference variable."""
        model = expr_metamodel.model_from_str("$EREF", "Expr")
        assert model is not None
        operand = model.left.operand
        # EREF is a Caché-specific variable, parses as IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "EREF"


class TestSpecialVariables:
    """Test special variable parsing."""

    def test_test(self, expr_metamodel):
        """Parse $TEST."""
        model = expr_metamodel.model_from_str("$TEST", "Expr")
        assert model is not None

    def test_horolog(self, expr_metamodel):
        """Parse $HOROLOG."""
        model = expr_metamodel.model_from_str("$HOROLOG", "Expr")
        assert model is not None

    def test_x(self, expr_metamodel):
        """Parse $X."""
        model = expr_metamodel.model_from_str("$X", "Expr")
        assert model is not None

    def test_abbreviated_horolog(self, expr_metamodel):
        """Parse $H as abbreviated $HOROLOG (T538 fix)."""
        model = expr_metamodel.model_from_str("$H", "Expr")
        assert model is not None
        # Navigate: Expr -> left (UnaryExpr) -> operand (PrimaryExpr)
        # PrimaryExpr should be SpecialVariable
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "H"

    def test_abbreviated_storage(self, expr_metamodel):
        """Parse $S as abbreviated $STORAGE (T538 fix)."""
        model = expr_metamodel.model_from_str("$S", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "S"

    def test_abbreviated_test(self, expr_metamodel):
        """Parse $T as abbreviated $TEST (T538 fix)."""
        model = expr_metamodel.model_from_str("$T", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "T"

    def test_abbreviated_job(self, expr_metamodel):
        """Parse $J as abbreviated $JOB (T538 fix)."""
        model = expr_metamodel.model_from_str("$J", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "J"

    def test_abbreviated_io(self, expr_metamodel):
        """Parse $I as abbreviated $IO (T538 fix)."""
        model = expr_metamodel.model_from_str("$I", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "I"

    def test_abbreviated_device(self, expr_metamodel):
        """Parse $D as abbreviated $DEVICE (T538 fix)."""
        model = expr_metamodel.model_from_str("$D", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "D"

    def test_select_function_still_works(self, expr_metamodel):
        """Parse $SELECT(cond:val) as SelectFunction, not special variable (T538 fix).

        $S alone is $STORAGE special variable, but $S(cond:val) is $SELECT function.
        $SELECT uses special syntax with condition:value pairs.
        """
        model = expr_metamodel.model_from_str("$SELECT(1:1)", "Expr")
        assert model is not None
        operand = model.left.operand
        # Should be SelectFunction since it has condition:value arguments
        assert operand.__class__.__name__ == "SelectFunction", (
            f"Expected SelectFunction, got {operand.__class__.__name__}"
        )
        assert operand.name in ("SELECT", "S")


class TestSelectFunction:
    """Test $SELECT function parsing - uses special condition:value syntax.

    $SELECT is unique in MUMPS because it uses colon (:) as a separator
    between conditions and values rather than as an operator.
    Syntax: $S[ELECT](tvexpr:expr, tvexpr:expr, ...)
    """

    def test_select_simple(self, expr_metamodel):
        """Parse $SELECT(1:1) - simplest form."""
        model = expr_metamodel.model_from_str("$SELECT(1:1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"
        assert operand.name.upper() in ("SELECT", "S")

    def test_select_abbreviated(self, expr_metamodel):
        """Parse $s(1:1) - abbreviated form."""
        model = expr_metamodel.model_from_str("$s(1:1)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"

    def test_select_multiple_pairs(self, expr_metamodel):
        """Parse $SELECT with multiple condition:value pairs."""
        model = expr_metamodel.model_from_str("$SELECT(A=1:X,B=2:Y,1:Z)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"
        # Check we have 3 pairs
        assert len(operand.args.args) == 3

    def test_select_with_expressions(self, expr_metamodel):
        """Parse $SELECT with complex expressions."""
        model = expr_metamodel.model_from_str('$s(ABC="abc":"abc",1:1)', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"

    def test_select_chained(self, expr_metamodel):
        """Parse expression with multiple $SELECT concatenated."""
        model = expr_metamodel.model_from_str(
            '$select(ABC="ABC":"abc",1:1)_$Select(ABC=1:"EFG",1:2)', "Expr"
        )
        assert model is not None

    def test_select_uppercase(self, expr_metamodel):
        """Parse $SELECT (uppercase)."""
        model = expr_metamodel.model_from_str("$SELECT(1:1)", "Expr")
        assert model is not None

    def test_select_lowercase(self, expr_metamodel):
        """Parse $select (lowercase)."""
        model = expr_metamodel.model_from_str("$select(1:1)", "Expr")
        assert model is not None

    def test_select_mixedcase(self, expr_metamodel):
        """Parse $Select (mixed case)."""
        model = expr_metamodel.model_from_str("$Select(1:1)", "Expr")
        assert model is not None

    def test_select_abbrev_se(self, expr_metamodel):
        """Parse $se (2 char abbreviation)."""
        model = expr_metamodel.model_from_str("$se(1:1)", "Expr")
        assert model is not None

    def test_select_abbrev_sel(self, expr_metamodel):
        """Parse $sel (3 char abbreviation)."""
        model = expr_metamodel.model_from_str("$sel(1:1)", "Expr")
        assert model is not None

    def test_select_abbrev_sele(self, expr_metamodel):
        """Parse $sele (4 char abbreviation)."""
        model = expr_metamodel.model_from_str("$sele(1:1)", "Expr")
        assert model is not None

    def test_select_abbrev_selec(self, expr_metamodel):
        """Parse $selec (5 char abbreviation)."""
        model = expr_metamodel.model_from_str("$selec(1:1)", "Expr")
        assert model is not None

    def test_select_name_preserves_casing(self, expr_metamodel):
        """Verify SelectFunction preserves original name casing.

        Function names are stored as-is in the ASG for consistency with
        IntrinsicFunction. Code generators normalize to uppercase as needed.
        """
        # Lowercase
        model = expr_metamodel.model_from_str("$select(1:1)", "Expr")
        operand = model.left.operand
        assert operand.name == "select", f"Expected 'select', got '{operand.name}'"

        # Uppercase
        model = expr_metamodel.model_from_str("$SELECT(1:1)", "Expr")
        operand = model.left.operand
        assert operand.name == "SELECT", f"Expected 'SELECT', got '{operand.name}'"

        # Mixed case
        model = expr_metamodel.model_from_str("$Select(1:1)", "Expr")
        operand = model.left.operand
        assert operand.name == "Select", f"Expected 'Select', got '{operand.name}'"

        # Abbreviated
        model = expr_metamodel.model_from_str("$s(1:1)", "Expr")
        operand = model.left.operand
        assert operand.name == "s", f"Expected 's', got '{operand.name}'"


class TestIndirection:
    """Test indirection parsing."""

    def test_simple_indirection(self, expr_metamodel):
        """Parse simple @variable indirection."""
        model = expr_metamodel.model_from_str("@X", "Expr")
        assert model is not None

    def test_subscript_indirection(self, expr_metamodel):
        """Parse @variable(subscripts) indirection."""
        model = expr_metamodel.model_from_str("@X(1,2)", "Expr")
        assert model is not None


class TestExtrinsicFunctions:
    """Test extrinsic function parsing."""

    def test_local_extrinsic(self, expr_metamodel):
        """Parse $$label() local extrinsic."""
        model = expr_metamodel.model_from_str("$$FUNC(X)", "Expr")
        assert model is not None

    def test_external_extrinsic(self, expr_metamodel):
        """Parse $$label^routine() external extrinsic."""
        model = expr_metamodel.model_from_str("$$FUNC^ROUTINE(X,Y)", "Expr")
        assert model is not None


class TestParentheses:
    """Test parenthesized expressions."""

    def test_simple_parens(self, expr_metamodel):
        """Parse (expr)."""
        model = expr_metamodel.model_from_str("(X+Y)", "Expr")
        assert model is not None

    def test_nested_parens(self, expr_metamodel):
        """Parse nested parentheses."""
        model = expr_metamodel.model_from_str("((X+Y)*Z)", "Expr")
        assert model is not None


class TestComplexExpressions:
    """Test complex expression parsing."""

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
