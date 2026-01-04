"""Tests for Intrinsic Functions parsing (§7.1.5).

Tests verify the textX grammar correctly captures intrinsic function syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
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
class TestIntrinsicFunctionsParsing:
    """Parser-level tests for Intrinsic Functions (§7.1.5).

    Per-function stubs for all standard intrinsic functions.
    """

    # ---- String Functions ----

    def test_length_function(self, expr_metamodel):
        """$LENGTH(string,delimiter) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$LENGTH(X)", "Expr")
        assert model is not None

    def test_piece_function(self, expr_metamodel):
        """$PIECE(string,delimiter,from,to) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str('$PIECE(STR,",",1)', "Expr")
        assert model is not None

    def test_extract_function(self, expr_metamodel):
        """$EXTRACT(string,from,to) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$EXTRACT(X,1,5)", "Expr")
        assert model is not None

    def test_abbreviated_function(self, expr_metamodel):
        """Parse abbreviated function ($L for $LENGTH)."""
        model = expr_metamodel.model_from_str("$L(X)", "Expr")
        assert model is not None

    def test_ascii_function(self, expr_metamodel):
        """$ASCII(string) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$ASCII(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ASCII"
        assert len(operand.args.args) == 1

    def test_char_function(self, expr_metamodel):
        """$CHAR(code) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$CHAR(65)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "CHAR"
        assert len(operand.args.args) == 1

    def test_find_function(self, expr_metamodel):
        """$FIND(string,target) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str('$FIND(STR,"X")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "FIND"
        assert len(operand.args.args) == 2

    def test_justify_function(self, expr_metamodel):
        """$JUSTIFY(expr,width,decimal) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$JUSTIFY(X,10,2)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "JUSTIFY"
        assert len(operand.args.args) == 3

    def test_reverse_function(self, expr_metamodel):
        """$REVERSE(string) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$REVERSE(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "REVERSE"
        assert len(operand.args.args) == 1

    def test_translate_function(self, expr_metamodel):
        """$TRANSLATE(string,from,to) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str('$TRANSLATE(X,"abc","ABC")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "TRANSLATE"
        assert len(operand.args.args) == 3

    # ---- Numeric Functions ----

    def test_fnumber_function(self, expr_metamodel):
        """$FNUMBER(num,format,digits) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str('$FNUMBER(X,",")', "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "FNUMBER"
        assert len(operand.args.args) == 2

    def test_random_function(self, expr_metamodel):
        """$RANDOM(limit) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$RANDOM(100)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "RANDOM"
        assert len(operand.args.args) == 1

    # ---- Data Functions ----

    def test_data_function(self, expr_metamodel):
        """$DATA(var) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$DATA(X)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "DATA"
        assert len(operand.args.args) == 1

    def test_get_function(self, expr_metamodel):
        """$GET(var,default) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$GET(X,0)", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "GET"
        assert len(operand.args.args) == 2

    def test_order_function(self, expr_metamodel):
        """$ORDER(var,direction) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$ORDER(X(I))", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "ORDER"
        assert len(operand.args.args) == 1

    def test_query_function(self, expr_metamodel):
        """$QUERY(var) parses correctly (§7.1.5)."""
        model = expr_metamodel.model_from_str("$QUERY(^DATA(I))", "Expr")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "QUERY"
        assert len(operand.args.args) == 1

    # ---- Name Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $NAME function parsing")
    def test_name_function(self, expr_metamodel):
        """$NAME(var,level) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QLENGTH function parsing")
    def test_qlength_function(self, expr_metamodel):
        """$QLENGTH(name) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QSUBSCRIPT function parsing")
    def test_qsubscript_function(self, expr_metamodel):
        """$QSUBSCRIPT(name,position) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Stack Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STACK function parsing")
    def test_stack_function(self, expr_metamodel):
        """$STACK(level,code) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Text Function ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT function parsing")
    def test_text_function(self, expr_metamodel):
        """$TEXT(label+offset^routine) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Type Function ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TYPE function parsing")
    def test_type_function(self, expr_metamodel):
        """$TYPE(value) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- MUMPS Function ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $MUMPS function parsing")
    def test_mumps_function(self, expr_metamodel):
        """$MUMPS(code) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- HOROLOG Function Form ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $HOROLOG function form parsing")
    def test_horolog_function_form(self, expr_metamodel):
        """$HOROLOG function form parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestDeprecatedFunctions:
    """Deprecated intrinsic functions (pre-1995)."""

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $NEXT deprecated function")
    def test_next_function_deprecated(self, expr_metamodel):
        """$NEXT(var) parses correctly - deprecated, use $ORDER (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DEXTRACT deprecated function")
    def test_dextract_function_deprecated(self, expr_metamodel):
        """$DEXTRACT parses correctly - deprecated (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DPIECE deprecated function")
    def test_dpiece_function_deprecated(self, expr_metamodel):
        """$DPIECE parses correctly - deprecated (§7.1.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestCacheSpecificFunctions:
    """Test Caché/IRIS-specific function parsing (§7.1.5).

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


@pytest.mark.parser
class TestSelectFunction:
    """Test $SELECT function parsing - uses special condition:value syntax (§7.1.5).

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


@pytest.mark.parser
class TestImplementationDefinedFunctions:
    """Implementation-defined $Z... functions."""

    @pytest.mark.skip(
        reason="Implementation-defined: $VIEW behavior varies by implementation"
    )
    def test_view_function(self):
        """$VIEW is implementation-defined."""
        pass

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $Z... implementation-defined functions"
    )
    def test_z_functions(self, parse_expression):
        """$Z... implementation-defined functions parse correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestTextFunctionGrammar:
    """Tests for $TEXT function special grammar.

    $TEXT takes a line reference argument, not a regular expression.
    These tests verify the TextFunction grammar works correctly.
    """

    def test_text_function_with_label(self):
        """$T(label) - TEXT function with label only."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label)\n")
        assert not routine.parse_errors

    def test_text_function_with_label_routine(self):
        """$T(label^routine) - TEXT function with label and routine."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label^routine)\n")
        assert not routine.parse_errors

    def test_text_function_with_offset(self):
        """$T(label+5) - TEXT function with label and offset."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label+5)\n")
        assert not routine.parse_errors

    def test_text_function_with_full_spec(self):
        """$T(label+5^routine) - TEXT function with full specification."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label+5^routine)\n")
        assert not routine.parse_errors

    def test_text_function_with_indirection(self):
        """$T(@VAR) - TEXT function with indirection."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(@VAR)\n")
        assert not routine.parse_errors

    def test_text_function_with_routine_indirection(self):
        """$T(^@VAR) - TEXT function with routine indirection."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(^@VAR)\n")
        assert not routine.parse_errors

    def test_text_full_keyword(self):
        """$TEXT(label) - full TEXT keyword."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$TEXT(label)\n")
        assert not routine.parse_errors


@pytest.mark.parser
class TestIntrinsicFunctionGrammar:
    """Test intrinsic function parsing via MUMPSParser."""

    def test_piece_function(self):
        """$PIECE function should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS X=$PIECE(STR,"^",1)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_piece_function_abbreviated(self):
        """$P abbreviation should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS X=$P(STR,",",2)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_select_function(self):
        """$SELECT function should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS X=$SELECT(A=1:B,1:C)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_select_function_abbreviated(self):
        """$S abbreviation should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS X=$S(X>0:"positive",1:"other")\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_length_function(self):
        """$LENGTH function should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS LEN=$LENGTH(STR)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_nested_functions(self):
        """Nested function calls should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tS X=$LENGTH($PIECE(STR,"^",1))\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
