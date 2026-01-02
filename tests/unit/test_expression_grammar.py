"""Tests for the expression grammar (expressions.tx).

Low-level tests that verify the textX expression grammar directly.
Tests literals, variables, operators, functions, and special constructs.

For semantic analysis of expressions, see test_semantic_analyzer.py.
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture
def expr_metamodel():
    """Load the expression grammar metamodel with custom classes.

    The custom classes (LocalVariable, GlobalVariable, etc.) ensure proper
    inheritance from ASG base classes (MVariable, MExpr). This is required
    for tests that use SemanticAnalyzer, which dispatches based on isinstance
    checks against these base classes.
    """
    grammar_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


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


class TestExtendedGlobalReferences:
    """Test extended global reference parsing (^|"env"|name and ^["gld"]name).

    Extended global references allow specifying an environment or global
    directory for the global variable, enabling cross-environment access.
    """

    def test_pipe_extended_global(self, expr_metamodel):
        """Parse pipe-delimited extended global: ^|"env"|name."""
        model = expr_metamodel.model_from_str('^|"env"|global', "Expr")
        assert model is not None

    def test_pipe_extended_global_subscripted(self, expr_metamodel):
        """Parse pipe-delimited extended global with subscripts."""
        model = expr_metamodel.model_from_str('^|"db"|data(1,2)', "Expr")
        assert model is not None

    def test_bracket_extended_global(self, expr_metamodel):
        """Parse bracket-delimited extended global: ^["gld"]name."""
        model = expr_metamodel.model_from_str('^["mumps.gld"]global', "Expr")
        assert model is not None

    def test_bracket_extended_global_subscripted(self, expr_metamodel):
        """Parse bracket-delimited extended global with subscripts."""
        model = expr_metamodel.model_from_str('^["gld"]data(1,2,3)', "Expr")
        assert model is not None

    def test_pipe_extended_global_empty_env(self, expr_metamodel):
        """Parse pipe-delimited extended global with empty environment."""
        model = expr_metamodel.model_from_str('^|""|global', "Expr")
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


class TestZFunctionsAndISVs:
    """Test YottaDB/GT.M Z-function and Z-ISV parsing.

    Z-functions are parsed via IntrinsicFunction (with args) or IntrinsicFunctionNoArgs (without args).
    Z-ISVs that can be SET/NEW are parsed as SpecialVariable (in SVARNAME pattern).

    The distinction is important:
    - Functions: $ZCHAR(x), $ZWRITE(x) - callable with args
    - Settable ISVs: $ZTRAP, $ZGBLDIR - can be SET or NEW'd
    - Read-only ISVs: $ZCHSET, $ZYSQLNULL - implementation-specific, not settable
    """

    # Settable Z-ISVs (parsed as SpecialVariable)
    def test_ztrap_isv(self, expr_metamodel):
        """Parse $ZTRAP Z-ISV for error trapping."""
        model = expr_metamodel.model_from_str("$ZTRAP", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZTRAP"

    def test_zstatus_isv(self, expr_metamodel):
        """Parse $ZSTATUS Z-ISV for status information."""
        model = expr_metamodel.model_from_str("$ZSTATUS", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZSTATUS"

    def test_zlevel_isv(self, expr_metamodel):
        """Parse $ZLEVEL Z-ISV for stack level."""
        model = expr_metamodel.model_from_str("$ZLEVEL", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZLEVEL"

    def test_zposition_isv(self, expr_metamodel):
        """Parse $ZPOSITION Z-ISV for position information."""
        model = expr_metamodel.model_from_str("$ZPOSITION", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZPOSITION"

    def test_zeof_isv(self, expr_metamodel):
        """Parse $ZEOF Z-ISV for end of file."""
        model = expr_metamodel.model_from_str("$ZEOF", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZEOF"

    def test_zcmdline_isv(self, expr_metamodel):
        """Parse $ZCMDLINE Z-ISV for command line."""
        model = expr_metamodel.model_from_str("$ZCMDLINE", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZCMDLINE"

    def test_zgbldir_isv(self, expr_metamodel):
        """Parse $ZGBLDIR Z-ISV for global directory."""
        model = expr_metamodel.model_from_str("$ZGBLDIR", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZGBLDIR"

    def test_zjob_isv(self, expr_metamodel):
        """Parse $ZJOB Z-ISV for job ID."""
        model = expr_metamodel.model_from_str("$ZJOB", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable"
        assert operand.name == "ZJOB"

    # Read-only Z-ISVs (parsed as IntrinsicFunctionNoArgs - not in SVARNAME)
    def test_zchset_isv(self, expr_metamodel):
        """Parse $ZCHSET Z-ISV for character set (read-only)."""
        model = expr_metamodel.model_from_str("$ZCHSET", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZCHSET"

    def test_zsystem_isv(self, expr_metamodel):
        """Parse $ZSYSTEM Z-ISV for OS return code (read-only)."""
        model = expr_metamodel.model_from_str("$ZSYSTEM", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZSYSTEM"

    def test_zysqlnull_isv(self, expr_metamodel):
        """Parse $ZYSQLNULL Z-ISV for SQL null handling (read-only)."""
        model = expr_metamodel.model_from_str("$ZYSQLNULL", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "ZYSQLNULL"

    # HIGH/MEDIUM priority Z-functions (from YDBTest analysis)
    def test_zchar_function(self, expr_metamodel):
        """Parse $ZCHAR Z-function for extended character handling."""
        model = expr_metamodel.model_from_str("$ZCHAR(65)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCHAR"
        assert len(operand.args.args) == 1

    def test_zwrite_function(self, expr_metamodel):
        """Parse $ZWRITE Z-function for write format."""
        model = expr_metamodel.model_from_str("$ZWRITE(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZWRITE"
        assert len(operand.args.args) == 1

    def test_zprevious_function(self, expr_metamodel):
        """Parse $ZPREVIOUS Z-function for previous in order."""
        model = expr_metamodel.model_from_str("$ZPREVIOUS(^DATA)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPREVIOUS"
        assert len(operand.args.args) == 1

    def test_zextract_function(self, expr_metamodel):
        """Parse $ZEXTRACT Z-function for extended extract."""
        model = expr_metamodel.model_from_str("$ZEXTRACT(STR,1,5)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZEXTRACT"
        assert len(operand.args.args) == 3

    def test_zpiece_function(self, expr_metamodel):
        """Parse $ZPIECE Z-function for extended piece."""
        model = expr_metamodel.model_from_str('$ZPIECE(STR,",",1)', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPIECE"
        assert len(operand.args.args) == 3

    def test_ztranslate_function(self, expr_metamodel):
        """Parse $ZTRANSLATE Z-function for extended translate."""
        model = expr_metamodel.model_from_str('$ZTRANSLATE(STR,"abc","xyz")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZTRANSLATE"
        assert len(operand.args.args) == 3

    def test_zparse_function(self, expr_metamodel):
        """Parse $ZPARSE Z-function for file path parsing."""
        model = expr_metamodel.model_from_str('$ZPARSE("/path/to/file")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZPARSE"
        assert len(operand.args.args) == 1

    def test_zsearch_function(self, expr_metamodel):
        """Parse $ZSEARCH Z-function for file search."""
        model = expr_metamodel.model_from_str('$ZSEARCH("*.m")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZSEARCH"
        assert len(operand.args.args) == 1

    def test_zgetjpi_function(self, expr_metamodel):
        """Parse $ZGETJPI Z-function for job/process info."""
        model = expr_metamodel.model_from_str('$ZGETJPI(0,"PID")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZGETJPI"
        assert len(operand.args.args) == 2

    def test_zconvert_function(self, expr_metamodel):
        """Parse $ZCONVERT Z-function for character conversion."""
        model = expr_metamodel.model_from_str('$ZCONVERT(STR,"L")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZCONVERT"
        assert len(operand.args.args) == 2

    def test_zascii_function(self, expr_metamodel):
        """Parse $ZASCII Z-function for extended ASCII."""
        model = expr_metamodel.model_from_str("$ZASCII(STR)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZASCII"
        assert len(operand.args.args) == 1

    def test_zlength_function(self, expr_metamodel):
        """Parse $ZLENGTH Z-function for extended length."""
        model = expr_metamodel.model_from_str("$ZLENGTH(STR)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZLENGTH"
        assert len(operand.args.args) == 1

    def test_zfind_function(self, expr_metamodel):
        """Parse $ZFIND Z-function for extended find."""
        model = expr_metamodel.model_from_str('$ZFIND(STR,"pattern")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ZFIND"
        assert len(operand.args.args) == 2


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
        """Parse $H as abbreviated $HOROLOG (single-letter forms allowed per MUMPS spec)."""
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
        """Parse $S as abbreviated $STORAGE (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$S", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "S"

    def test_abbreviated_test(self, expr_metamodel):
        """Parse $T as abbreviated $TEST (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$T", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "T"

    def test_abbreviated_job(self, expr_metamodel):
        """Parse $J as abbreviated $JOB (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$J", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "J"

    def test_abbreviated_io(self, expr_metamodel):
        """Parse $I as abbreviated $IO (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$I", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "I"

    def test_abbreviated_device(self, expr_metamodel):
        """Parse $D as abbreviated $DEVICE (single-letter forms allowed per MUMPS spec)."""
        model = expr_metamodel.model_from_str("$D", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SpecialVariable", (
            f"Expected SpecialVariable, got {operand.__class__.__name__}"
        )
        assert operand.name == "D"

    def test_select_function_still_works(self, expr_metamodel):
        """Parse $SELECT(cond:val) as SelectFunction, not special variable.

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
    """Test indirection parsing including multi-level indirection (@@, @@@).

    Multi-level indirection is parsed recursively - @@X becomes @(@X) where the
    outer @ has an Indirection as its expr attribute.
    """

    def test_simple_indirection(self, expr_metamodel):
        """Parse simple @variable indirection."""
        model = expr_metamodel.model_from_str("@X", "Expr")
        assert model is not None

    def test_subscript_indirection(self, expr_metamodel):
        """Parse @variable(subscripts) indirection."""
        model = expr_metamodel.model_from_str("@X(1,2)", "Expr")
        assert model is not None

    def test_double_indirection(self, expr_metamodel):
        """Parse @@X double indirection (Phase 102 Part E)."""
        model = expr_metamodel.model_from_str("@@X", "Expr")
        assert model is not None
        # Outer indirection
        outer = model.left.operand
        assert outer.__class__.__name__ == "Indirection"
        # Inner indirection (expr contains another Indirection)
        inner = outer.expr
        assert inner.__class__.__name__ == "Indirection"
        # Innermost is the variable
        assert inner.expr.name == "X"

    def test_triple_indirection(self, expr_metamodel):
        """Parse @@@X triple indirection (Phase 102 Part E)."""
        model = expr_metamodel.model_from_str("@@@X", "Expr")
        assert model is not None
        outer = model.left.operand
        assert outer.__class__.__name__ == "Indirection"
        middle = outer.expr
        assert middle.__class__.__name__ == "Indirection"
        inner = middle.expr
        assert inner.__class__.__name__ == "Indirection"
        assert inner.expr.name == "X"

    def test_double_indirection_with_string(self, expr_metamodel):
        """Parse @@"literal" double indirection with string literal."""
        model = expr_metamodel.model_from_str('@@"^V1A"', "Expr")
        assert model is not None
        outer = model.left.operand
        inner = outer.expr
        assert inner.__class__.__name__ == "Indirection"
        # Innermost is a string literal
        assert inner.expr.__class__.__name__ == "StringLiteral"

    def test_double_indirection_with_subscripts(self, expr_metamodel):
        """Parse @@X(1,2) double indirection - subscripts apply to innermost variable.

        In MUMPS, @@X(1,2) means: evaluate X(1,2), then indirect twice.
        The subscripts attach to the innermost variable reference.
        """
        model = expr_metamodel.model_from_str("@@X(1,2)", "Expr")
        assert model is not None
        outer = model.left.operand
        inner = outer.expr
        # Subscripts are on the innermost variable X
        innermost = inner.expr
        assert innermost.__class__.__name__ == "LocalVariable"
        assert len(innermost.subscripts) == 2

    def test_triple_indirection_with_subscripts(self, expr_metamodel):
        """Parse @@@B("AB",2.4) triple indirection - subscripts apply to innermost variable.

        In MUMPS, @@@B("AB",2.4) means: evaluate B("AB",2.4), then indirect three times.
        """
        model = expr_metamodel.model_from_str('@@@B("AB",2.4)', "Expr")
        assert model is not None
        outer = model.left.operand
        middle = outer.expr
        inner = middle.expr
        innermost = inner.expr
        assert innermost.__class__.__name__ == "LocalVariable"
        assert innermost.name == "B"
        assert len(innermost.subscripts) == 2

    def test_name_indirection_with_subscripts(self, expr_metamodel):
        """Parse @B@(1) name indirection with subscripts (from task examples)."""
        model = expr_metamodel.model_from_str("@B@(1)", "Expr")
        assert model is not None
        ind = model.left.operand
        assert ind.__class__.__name__ == "Indirection"
        # name_subscripts captures the @(1) part
        assert ind.name_subscripts is not None
        assert len(ind.name_subscripts) == 1


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


class TestExternalFunctions:
    """Test external function parsing (Phase 103 fix).

    External functions call C functions linked into the MUMPS runtime.
    Syntax: $&name(args) or $&package.name(args)
    """

    def test_external_function_simple(self, expr_metamodel):
        """Parse $&RAND(1) - external function without package."""
        model = expr_metamodel.model_from_str("$&RAND(1)", "Expr")
        assert model is not None
        # The result is an ExternalFunction wrapped in UnaryExpr
        assert model.left.operand.__class__.__name__ == "ExternalFunction"
        assert model.left.operand.name == "RAND"
        assert model.left.operand.package is None

    def test_external_function_byref_arg(self, expr_metamodel):
        """Parse $&RAND(.var) - external function with by-reference argument."""
        model = expr_metamodel.model_from_str("$&RAND(.x)", "Expr")
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.name == "RAND"
        # Check that the argument is a by-ref arg
        assert ext_func.args.first.byref is not None

    def test_external_function_with_package(self, expr_metamodel):
        """Parse $&pkg.func(1) - external function with package prefix."""
        model = expr_metamodel.model_from_str("$&ydbposix.signalval(1)", "Expr")
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.package == "ydbposix"
        assert ext_func.name == "signalval"

    def test_external_function_complex_args(self, expr_metamodel):
        """Parse $&ydbposix.signalval("SIGTERM",.val) - with string and by-ref."""
        model = expr_metamodel.model_from_str(
            '$&ydbposix.signalval("SIGTERM",.val)', "Expr"
        )
        assert model is not None
        ext_func = model.left.operand
        assert ext_func.__class__.__name__ == "ExternalFunction"
        assert ext_func.package == "ydbposix"
        assert ext_func.name == "signalval"
        # First arg is string, second is by-ref
        assert ext_func.args.first.expr is not None  # string arg
        assert len(ext_func.args.rest) == 1
        assert ext_func.args.rest[0].arg.byref is not None  # by-ref arg


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
