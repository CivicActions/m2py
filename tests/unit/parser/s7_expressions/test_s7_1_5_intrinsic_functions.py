"""Tests for Intrinsic Functions parsing (§7.1.5).

Tests verify the textX grammar correctly captures intrinsic function syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
Migrated from:
- tests/unit/test_expression_grammar.py::TestIntrinsicFunctions
- tests/unit/test_grammar.py::TestIntrinsicFunctionGrammar
"""

import pytest

from m2py.asg import MRoutine
from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestIntrinsicFunctionsParsing:
    """Parser-level tests for Intrinsic Functions (§7.1.5).

    Migrated from: tests/unit/test_expression_grammar.py::TestIntrinsicFunctions
    """

    # ---- String Functions ----

    def test_length_function(self, parse_expression):
        """$LENGTH(X) parses correctly (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestIntrinsicFunctions
        """
        model = parse_expression("$LENGTH(X)")
        assert model is not None

    def test_piece_function(self, parse_expression):
        """$PIECE(string,delimiter,from) parses correctly (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestIntrinsicFunctions
        """
        model = parse_expression('$PIECE(STR,",",1)')
        assert model is not None

    def test_extract_function(self, parse_expression):
        """$EXTRACT(string,from,to) parses correctly (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestIntrinsicFunctions
        """
        model = parse_expression("$EXTRACT(X,1,5)")
        assert model is not None

    def test_abbreviated_function(self, parse_expression):
        """$L for $LENGTH - abbreviated function forms allowed (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestIntrinsicFunctions
        """
        model = parse_expression("$L(X)")
        assert model is not None

    def test_ascii_function(self, parse_expression):
        """$ASCII(string) parses correctly (§7.1.5)."""
        model = parse_expression("$ASCII(X)")
        assert model is not None

    def test_char_function(self, parse_expression):
        """$CHAR(code) parses correctly (§7.1.5)."""
        model = parse_expression("$CHAR(65)")
        assert model is not None

    def test_find_function(self, parse_expression):
        """$FIND(string,target) parses correctly (§7.1.5)."""
        model = parse_expression('$FIND(STR,"ABC")')
        assert model is not None

    def test_justify_function(self, parse_expression):
        """$JUSTIFY(expr,width,decimal) parses correctly (§7.1.5)."""
        model = parse_expression("$JUSTIFY(X,10,2)")
        assert model is not None

    def test_reverse_function(self, parse_expression):
        """$REVERSE(string) parses correctly (§7.1.5)."""
        model = parse_expression("$REVERSE(X)")
        assert model is not None

    def test_translate_function(self, parse_expression):
        """$TRANSLATE(string,from,to) parses correctly (§7.1.5)."""
        model = parse_expression('$TRANSLATE(X,"abc","xyz")')
        assert model is not None

    # ---- Numeric Functions ----

    def test_fnumber_function(self, parse_expression):
        """$FNUMBER(num,format,digits) parses correctly (§7.1.5)."""
        model = parse_expression('$FNUMBER(X,",",2)')
        assert model is not None

    def test_random_function(self, parse_expression):
        """$RANDOM(limit) parses correctly (§7.1.5)."""
        model = parse_expression("$RANDOM(100)")
        assert model is not None

    # ---- Data Functions ----

    def test_data_function(self, parse_expression):
        """$DATA(var) parses correctly (§7.1.5)."""
        model = parse_expression("$DATA(X)")
        assert model is not None

    def test_get_function(self, parse_expression):
        """$GET(var,default) parses correctly (§7.1.5)."""
        model = parse_expression('$GET(X,"default")')
        assert model is not None

    def test_order_function(self, parse_expression):
        """$ORDER(var,direction) parses correctly (§7.1.5)."""
        model = parse_expression("$ORDER(X)")
        assert model is not None

    def test_query_function(self, parse_expression):
        """$QUERY(var) parses correctly (§7.1.5)."""
        model = parse_expression("$QUERY(X)")
        assert model is not None

    # ---- Name Functions ----

    def test_name_function(self, parse_expression):
        """$NAME(var,level) parses correctly (§7.1.5)."""
        model = parse_expression("$NAME(X)")
        assert model is not None

    def test_qlength_function(self, parse_expression):
        """$QLENGTH(name) parses correctly (§7.1.5)."""
        model = parse_expression("$QLENGTH(NAME)")
        assert model is not None

    def test_qsubscript_function(self, parse_expression):
        """$QSUBSCRIPT(name,position) parses correctly (§7.1.5)."""
        model = parse_expression("$QSUBSCRIPT(NAME,1)")
        assert model is not None

    # ---- Stack Functions ----

    def test_stack_function(self, parse_expression):
        """$STACK(level,code) parses correctly (§7.1.5)."""
        model = parse_expression("$STACK(1)")
        assert model is not None

    # ---- Text Function ----
    # These tests migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar

    def test_text_function_with_label(self):
        """$T(label) - TEXT function with label only (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label)\n")
        assert not routine.parse_errors

    def test_text_function_with_label_routine(self):
        """$T(label^routine) - TEXT function with label and routine (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label^routine)\n")
        assert not routine.parse_errors

    def test_text_function_with_offset(self):
        """$T(label+5) - TEXT function with label and offset (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label+5)\n")
        assert not routine.parse_errors

    def test_text_function_with_full_spec(self):
        """$T(label+5^routine) - TEXT function with full specification (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(label+5^routine)\n")
        assert not routine.parse_errors

    def test_text_function_with_indirection(self):
        """$T(@VAR) - TEXT function with indirection (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(@VAR)\n")
        assert not routine.parse_errors

    def test_text_function_with_routine_indirection(self):
        """$T(^@VAR) - TEXT function with routine indirection (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$T(^@VAR)\n")
        assert not routine.parse_errors

    def test_text_full_keyword(self):
        """$TEXT(label) - full TEXT keyword (§7.1.5).

        Migrated from: tests/unit/test_command_grammar.py::TestTextFunctionGrammar
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse(" S X=$TEXT(label)\n")
        assert not routine.parse_errors

    # ---- Type Function ----

    def test_type_function(self, parse_expression):
        """$TYPE(value) parses correctly (§7.1.5)."""
        model = parse_expression("$TYPE(X)")
        assert model is not None


@pytest.mark.parser
class TestDeprecatedFunctions:
    """Deprecated intrinsic functions (pre-1995)."""

    @pytest.mark.pre1995
    def test_next_function_deprecated(self, parse_expression):
        """$NEXT(var) parses correctly - deprecated, use $ORDER (§7.1.5)."""
        model = parse_expression("$NEXT(X)")
        assert model is not None


@pytest.mark.parser
class TestImplementationDefinedFunctions:
    """Implementation-defined $Z... functions."""

    @pytest.mark.xfail(reason="Used in VistA: $VIEW function (190+ uses)")
    def test_view_function(self):
        """$VIEW is implementation-defined but used in VistA."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestCacheSpecificFunctions:
    """Test Caché/IRIS-specific function parsing (§7.1.5).

    These are implementation-specific functions found in VistA codebase.
    The grammar accepts them via the generic FUNCNAME pattern.

    Migrated from: tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions
    """

    def test_li_list_abbreviation(self, parse_expression):
        """$LI parses as Caché $LIST abbreviation (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions
        """
        model = parse_expression("$LI(X,1)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "LI"
        assert len(operand.args.args) == 2

    def test_listget_function(self, parse_expression):
        """$LISTGET parses as Caché function (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions
        """
        model = parse_expression("$LISTGET(X,2,0)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "LISTGET"
        assert len(operand.args.args) == 3

    def test_increment_function(self, parse_expression):
        """$INCREMENT parses as Caché atomic increment function (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions
        """
        model = parse_expression("$INCREMENT(^CTR)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "IntrinsicFunction"
        assert operand.name == "INCREMENT"
        assert len(operand.args.args) == 1

    def test_namespace_special_var(self, parse_expression):
        """$NAMESPACE parses as Caché special variable (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions
        """
        model = parse_expression("$NAMESPACE")
        assert model is not None
        operand = model.left.operand
        # NAMESPACE is not a standard MUMPS special variable,
        # so it parses as IntrinsicFunctionNoArgs
        assert operand.__class__.__name__ == "IntrinsicFunctionNoArgs"
        assert operand.name == "NAMESPACE"

    def test_eref_special_var(self, parse_expression):
        """$EREF parses as Caché external reference variable (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions
        """
        model = parse_expression("$EREF")
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

    Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
    """

    def test_select_simple(self, parse_expression):
        """$SELECT(1:1) - simplest form (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$SELECT(1:1)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"
        assert operand.name.upper() in ("SELECT", "S")

    def test_select_abbreviated(self, parse_expression):
        """$s(1:1) - abbreviated form (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$s(1:1)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"

    def test_select_multiple_pairs(self, parse_expression):
        """$SELECT with multiple condition:value pairs (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$SELECT(A=1:X,B=2:Y,1:Z)")
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"
        # Check we have 3 pairs
        assert len(operand.args.args) == 3

    def test_select_with_expressions(self, parse_expression):
        """$SELECT with complex expressions (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression('$s(ABC="abc":"abc",1:1)')
        assert model is not None
        operand = model.left.operand
        assert operand.__class__.__name__ == "SelectFunction"

    def test_select_chained(self, parse_expression):
        """Expression with multiple $SELECT concatenated (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression(
            '$select(ABC="ABC":"abc",1:1)_$Select(ABC=1:"EFG",1:2)'
        )
        assert model is not None

    def test_select_uppercase(self, parse_expression):
        """$SELECT (uppercase) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$SELECT(1:1)")
        assert model is not None

    def test_select_lowercase(self, parse_expression):
        """$select (lowercase) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$select(1:1)")
        assert model is not None

    def test_select_mixedcase(self, parse_expression):
        """$Select (mixed case) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$Select(1:1)")
        assert model is not None

    def test_select_abbrev_se(self, parse_expression):
        """$se (2 char abbreviation) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$se(1:1)")
        assert model is not None

    def test_select_abbrev_sel(self, parse_expression):
        """$sel (3 char abbreviation) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$sel(1:1)")
        assert model is not None

    def test_select_abbrev_sele(self, parse_expression):
        """$sele (4 char abbreviation) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$sele(1:1)")
        assert model is not None

    def test_select_abbrev_selec(self, parse_expression):
        """$selec (5 char abbreviation) (§7.1.5).

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        model = parse_expression("$selec(1:1)")
        assert model is not None

    def test_select_name_preserves_casing(self, parse_expression):
        """SelectFunction preserves original name casing (§7.1.5).

        Function names are stored as-is in the ASG for consistency with
        IntrinsicFunction. Code generators normalize to uppercase as needed.

        Migrated from: tests/unit/test_expression_grammar.py::TestSelectFunction
        """
        # Lowercase
        model = parse_expression("$select(1:1)")
        operand = model.left.operand
        assert operand.name == "select", f"Expected 'select', got '{operand.name}'"

        # Uppercase
        model = parse_expression("$SELECT(1:1)")
        operand = model.left.operand
        assert operand.name == "SELECT", f"Expected 'SELECT', got '{operand.name}'"

        # Mixed case
        model = parse_expression("$Select(1:1)")
        operand = model.left.operand
        assert operand.name == "Select", f"Expected 'Select', got '{operand.name}'"

        # Abbreviated
        model = parse_expression("$s(1:1)")
        operand = model.left.operand
        assert operand.name == "s", f"Expected 's', got '{operand.name}'"

    def test_select_function_still_works(self, parse_expression):
        """$SELECT(cond:val) as SelectFunction, not special variable (§7.1.5).

        $S alone is $STORAGE special variable, but $S(cond:val) is $SELECT function.
        $SELECT uses special syntax with condition:value pairs.

        Migrated from: tests/unit/test_expression_grammar.py::TestSpecialVariables
        """
        model = parse_expression("$SELECT(1:1)")
        assert model is not None
        operand = model.left.operand
        # Should be SelectFunction since it has condition:value arguments
        assert operand.__class__.__name__ == "SelectFunction", (
            f"Expected SelectFunction, got {operand.__class__.__name__}"
        )
        assert operand.name in ("SELECT", "S")


@pytest.mark.parser
class TestIntrinsicFunctionGrammar:
    """Test intrinsic function parsing full-routine acceptance (§7.1.5).

    Migrated from: tests/unit/test_grammar.py::TestIntrinsicFunctionGrammar
    """

    def test_piece_function(self):
        """$PIECE function should parse (§7.1.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$PIECE(STR,"^",1)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_piece_function_abbreviated(self):
        """$P abbreviation should parse (§7.1.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$P(STR,",",2)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_select_function(self):
        """$SELECT function should parse (§7.1.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS X=$SELECT(A=1:B,1:C)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_select_function_abbreviated(self):
        """$S abbreviation should parse (§7.1.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$S(X>0:"positive",1:"other")\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_length_function(self):
        """$LENGTH function should parse (§7.1.5)."""
        parser = MUMPSParser()
        source = "LABEL\tS LEN=$LENGTH(STR)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_nested_functions(self):
        """Nested function calls should parse (§7.1.5)."""
        parser = MUMPSParser()
        source = 'LABEL\tS X=$LENGTH($PIECE(STR,"^",1))\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
