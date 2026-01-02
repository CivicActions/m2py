"""Tests for Intrinsic Functions parsing (§7.1.5).

Tests verify the textX grammar correctly captures intrinsic function syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
"""

import pytest


@pytest.mark.parser
class TestIntrinsicFunctionsParsing:
    """Parser-level tests for Intrinsic Functions (§7.1.5).

    Per-function stubs for all standard intrinsic functions.
    """

    # ---- String Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ASCII function parsing")
    def test_ascii_function(self, parse_expression):
        """$ASCII(string) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $CHAR function parsing")
    def test_char_function(self, parse_expression):
        """$CHAR(code) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $EXTRACT function parsing")
    def test_extract_function(self, parse_expression):
        """$EXTRACT(string,from,to) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $FIND function parsing")
    def test_find_function(self, parse_expression):
        """$FIND(string,target) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $JUSTIFY function parsing")
    def test_justify_function(self, parse_expression):
        """$JUSTIFY(expr,width,decimal) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $LENGTH function parsing")
    def test_length_function(self, parse_expression):
        """$LENGTH(string,delimiter) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PIECE function parsing")
    def test_piece_function(self, parse_expression):
        """$PIECE(string,delimiter,from,to) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $REVERSE function parsing")
    def test_reverse_function(self, parse_expression):
        """$REVERSE(string) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRANSLATE function parsing")
    def test_translate_function(self, parse_expression):
        """$TRANSLATE(string,from,to) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Numeric Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $FNUMBER function parsing")
    def test_fnumber_function(self, parse_expression):
        """$FNUMBER(num,format,digits) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $RANDOM function parsing")
    def test_random_function(self, parse_expression):
        """$RANDOM(limit) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Data Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DATA function parsing")
    def test_data_function(self, parse_expression):
        """$DATA(var) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $GET function parsing")
    def test_get_function(self, parse_expression):
        """$GET(var,default) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ORDER function parsing")
    def test_order_function(self, parse_expression):
        """$ORDER(var,direction) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QUERY function parsing")
    def test_query_function(self, parse_expression):
        """$QUERY(var) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Name Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $NAME function parsing")
    def test_name_function(self, parse_expression):
        """$NAME(var,level) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QLENGTH function parsing")
    def test_qlength_function(self, parse_expression):
        """$QLENGTH(name) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $QSUBSCRIPT function parsing")
    def test_qsubscript_function(self, parse_expression):
        """$QSUBSCRIPT(name,position) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Control Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $SELECT function parsing")
    def test_select_function(self, parse_expression):
        """$SELECT(cond:val,...) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Stack Functions ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $STACK function parsing")
    def test_stack_function(self, parse_expression):
        """$STACK(level,code) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Text Function ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT function parsing")
    def test_text_function(self, parse_expression):
        """$TEXT(label+offset^routine) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- Type Function ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TYPE function parsing")
    def test_type_function(self, parse_expression):
        """$TYPE(value) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- MUMPS Function ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $MUMPS function parsing")
    def test_mumps_function(self, parse_expression):
        """$MUMPS(code) parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")

    # ---- HOROLOG Function Form ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $HOROLOG function form parsing")
    def test_horolog_function_form(self, parse_expression):
        """$HOROLOG function form parses correctly (§7.1.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestDeprecatedFunctions:
    """Deprecated intrinsic functions (pre-1995)."""

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $NEXT deprecated function")
    def test_next_function_deprecated(self, parse_expression):
        """$NEXT(var) parses correctly - deprecated, use $ORDER (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DEXTRACT deprecated function")
    def test_dextract_function_deprecated(self, parse_expression):
        """$DEXTRACT parses correctly - deprecated (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DPIECE deprecated function")
    def test_dpiece_function_deprecated(self, parse_expression):
        """$DPIECE parses correctly - deprecated (§7.1.5)."""
        pytest.fail("Stub - implement test")


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
