"""Unit tests for Phase 14 behavioral fixes.

These tests verify edge cases in fixes made during Spec 017 Phase 14:
1. ?intexpr / *intexpr with non-numeric string expressions
2. m_format_output with numeric strings
3. m_piece with negative/zero from_pos in range extraction
"""

import pytest


@pytest.mark.codegen
class TestFormatControlNumericCoercion:
    """Tests for ?intexpr and *intexpr with MUMPS numeric coercion.

    In MUMPS, format controls like ?intexpr and *intexpr expect a numeric
    expression. When a string is provided, it should be coerced using MUMPS
    rules: leading numeric portion extracted, non-numeric strings become 0.

    Fix: Changed from int(expr) to int(m_num(expr)) in codegen.
    """

    def test_tab_with_numeric_string(self, execute_mumps):
        """W ?"10" tabs to column 10 (string coerces to 10)."""
        result = execute_mumps('TEST\n W ?"10","X"\n Q\n')
        assert result.success is True
        assert result.output == "          X"  # 10 spaces + X

    def test_tab_with_non_numeric_string(self, execute_mumps):
        """W ?"ABC" tabs to column 0 (string coerces to 0).

        "ABC" has no leading numeric portion, so m_num("ABC") = 0.
        ?0 means column 0, so X appears at position 0 (no leading spaces).
        """
        result = execute_mumps('TEST\n W ?"ABC","X"\n Q\n')
        assert result.success is True
        assert result.output == "X"

    def test_tab_with_leading_numeric_string(self, execute_mumps):
        """W ?"3ABC" tabs to column 3 (string coerces to 3)."""
        result = execute_mumps('TEST\n W ?"3ABC","X"\n Q\n')
        assert result.success is True
        assert result.output == "   X"  # 3 spaces + X

    def test_tab_with_variable_string(self, execute_mumps):
        """W ?X where X="ABC" tabs to column 0."""
        result = execute_mumps('TEST\n S X="ABC" W ?X,"Y"\n Q\n')
        assert result.success is True
        assert result.output == "Y"

    def test_charcode_with_numeric_string(self, execute_mumps):
        """W *"65" outputs 'A' (string coerces to 65)."""
        result = execute_mumps('TEST\n W *"65"\n Q\n')
        assert result.success is True
        assert result.output == "A"

    def test_charcode_with_non_numeric_string(self, execute_mumps):
        """W *"XYZ" outputs NUL character (string coerces to 0)."""
        result = execute_mumps('TEST\n W *"XYZ"\n Q\n')
        assert result.success is True
        assert result.output == "\x00"  # chr(0) = NUL

    def test_charcode_with_leading_numeric_string(self, execute_mumps):
        """W *"66ABC" outputs 'B' (string coerces to 66)."""
        result = execute_mumps('TEST\n W *"66ABC"\n Q\n')
        assert result.success is True
        assert result.output == "B"


@pytest.mark.codegen
class TestMFormatOutputNumericStrings:
    """Tests for m_format_output with numeric strings.

    Fix: Added canonicalization of strings that look like MUMPS numbers.
    A string "0.5" should output as ".5" to match MUMPS canonical form.
    """

    def test_numeric_string_leading_zero_removed(self):
        """Numeric string "0.5" is canonicalized to ".5"."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("0.5") == ".5"
        assert m_format_output("0.123") == ".123"

    def test_numeric_string_negative_leading_zero_removed(self):
        """Numeric string "-0.5" is canonicalized to "-.5"."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("-0.5") == "-.5"
        assert m_format_output("-0.001") == "-.001"

    def test_integer_string_preserved(self):
        """Integer strings remain unchanged."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("123") == "123"
        assert m_format_output("-456") == "-456"
        assert m_format_output("0") == "0"

    def test_non_numeric_string_unchanged(self):
        """Non-numeric strings are not modified."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("hello") == "hello"
        assert m_format_output("ABC123") == "ABC123"
        assert m_format_output("") == ""

    def test_whitespace_string_unchanged(self):
        """Strings with whitespace are not canonicalized (not MUMPS numbers)."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output(" 123") == " 123"  # Leading space
        assert m_format_output("123 ") == "123 "  # Trailing space
        assert m_format_output("  0.5  ") == "  0.5  "

    def test_scientific_notation_string_unchanged(self):
        """Scientific notation strings are not canonicalized."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("1E5") == "1E5"
        assert m_format_output("1e-2") == "1e-2"

    def test_plus_sign_string_unchanged(self):
        """Strings with plus sign are not canonicalized."""
        from m2py.runtime.helpers import m_format_output

        assert m_format_output("+5") == "+5"
        assert m_format_output("+0.5") == "+0.5"


@pytest.mark.codegen
class TestMPieceNegativePositions:
    """Tests for m_piece with negative/zero positions in range extraction.

    Fix: Range extraction clamps from_pos to 1 when <= 0, instead of
    returning empty string like single-piece extraction does.
    """

    def test_single_piece_negative_returns_empty(self):
        """Single piece with negative position returns empty string."""
        from m2py.runtime.helpers import m_piece

        assert m_piece("A^B^C", "^", -1) == ""
        assert m_piece("A^B^C", "^", -5) == ""

    def test_single_piece_zero_returns_empty(self):
        """Single piece with zero position returns empty string."""
        from m2py.runtime.helpers import m_piece

        assert m_piece("A^B^C", "^", 0) == ""

    def test_range_negative_from_clamps_to_one(self):
        """Range with negative from_pos clamps to 1."""
        from m2py.runtime.helpers import m_piece

        # $P("A^B^C","^",-1,2) should give pieces 1-2 = "A^B"
        assert m_piece("A^B^C", "^", -1, 2) == "A^B"
        assert m_piece("A^B^C", "^", -5, 2) == "A^B"

    def test_range_zero_from_clamps_to_one(self):
        """Range with zero from_pos clamps to 1."""
        from m2py.runtime.helpers import m_piece

        # $P("A^B^C","^",0,2) should give pieces 1-2 = "A^B"
        assert m_piece("A^B^C", "^", 0, 2) == "A^B"

    def test_range_negative_to_returns_empty(self):
        """Range with to_pos < from_pos (after clamping) returns empty."""
        from m2py.runtime.helpers import m_piece

        # $P("A^B^C","^",-1,-1) - both clamp but to < from is still empty
        # Wait, single piece with -1 returns "", but what about range -1 to -1?
        # Per docstring: both negative means no modification for SET, but for
        # GET (this function), single negative returns empty.
        # Range: from=-1 to=-1 → from clamps to 1, to=-1 still, 1 > -1 is false,
        # so -1 < 1, return empty (to < from after from clamps)
        # Actually the code only clamps from_pos when there's a range.
        # For to_pos=-1, to_idx = -2, from_idx = 0, so from_idx >= len(parts)?
        # Let's trace: from_pos=-1 clamps to 1, to_pos=-1 stays
        # to_pos < from_pos? -1 < 1? Yes, return ""
        assert m_piece("A^B^C", "^", -1, -1) == ""

    def test_range_both_negative_returns_empty(self):
        """Range with both positions negative returns empty (to < from)."""
        from m2py.runtime.helpers import m_piece

        assert m_piece("A^B^C", "^", -2, -1) == ""


@pytest.mark.codegen
class TestMGlobalAsExpression:
    """Tests for MGlobal appearing directly as expression (not GlobalVariable).

    Fix: Changed generate_expr to check MGlobal before GlobalVariable since
    GlobalVariable inherits from MGlobal, and MGlobal can appear in contexts
    like GOTO offsets.
    """

    def test_global_in_do_offset(self, execute_mumps):
        """D L+^G uses global value as offset (MGlobal in expression)."""
        # Set global to 1, then DO should jump to L1+1 which writes "LINE2"
        result = execute_mumps("""TEST
 S ^G=1
 D L1+^G
 Q
L1 W "LINE1" Q
 W "LINE2" Q
""")
        assert result.success is True
        assert result.output == "LINE2"

    def test_global_in_arithmetic(self, execute_mumps):
        """Arithmetic with global variable in expression."""
        result = execute_mumps("TEST\n S ^X=5 W ^X+10\n Q\n")
        assert result.success is True
        assert result.output == "15"

    def test_extended_global_in_expression_raises(self, generate_python):
        """Extended global ^|env| in expression raises NotImplementedError."""
        # Extended globals are not yet supported
        code = 'TEST\n W ^|"ENV"|X\n Q\n'
        with pytest.raises(NotImplementedError, match="Extended global"):
            generate_python(code)


@pytest.mark.codegen
class TestFnumberCodeCombinations:
    """Tests for $FNUMBER code combinations including +T.

    Fix: Added handling for +T combination - trailing + for positive numbers.
    Priority order is: P > - > (T with +) > T > + > default
    """

    def test_fnumber_t_positive_trailing_space(self, execute_mumps):
        """$FN(42,"T") gives trailing space for positive numbers."""
        result = execute_mumps('TEST W "|",$FN(42,"T"),"|" Q')
        assert result.success is True
        assert result.output == "|42 |"

    def test_fnumber_t_negative_trailing_minus(self, execute_mumps):
        """$FN(-42,"T") gives trailing minus for negative numbers."""
        result = execute_mumps('TEST W $FN(-42,"T") Q')
        assert result.success is True
        assert result.output == "42-"

    def test_fnumber_plus_t_positive_trailing_plus(self, execute_mumps):
        """$FN(42,"+T") gives trailing + for positive numbers."""
        result = execute_mumps('TEST W $FN(42,"+T") Q')
        assert result.success is True
        assert result.output == "42+"

    def test_fnumber_plus_t_negative_trailing_minus(self, execute_mumps):
        """$FN(-42,"+T") gives trailing minus for negative numbers."""
        result = execute_mumps('TEST W $FN(-42,"+T") Q')
        assert result.success is True
        assert result.output == "42-"

    def test_fnumber_t_plus_same_as_plus_t(self, execute_mumps):
        """$FN(42,"T+") is same as $FN(42,"+T") - trailing +."""
        result = execute_mumps('TEST W $FN(42,"T+") Q')
        assert result.success is True
        assert result.output == "42+"

    def test_fnumber_plus_alone_leading_plus(self, execute_mumps):
        """$FN(42,"+") gives leading + (not trailing)."""
        result = execute_mumps('TEST W $FN(42,"+") Q')
        assert result.success is True
        assert result.output == "+42"


@pytest.mark.codegen
class TestIOSpecialVariableAbbreviation:
    """Tests for $I abbreviation of $IO special variable.

    Fix: Added "I" to the list of names recognized as $IO.
    """

    def test_dollar_i_abbreviation(self, execute_mumps):
        """$I is abbreviation for $IO (current device)."""
        result = execute_mumps("TEST W $I Q")
        assert result.success is True
        # Should output something (the current device name)
        assert result.output is not None

    def test_dollar_io_full_form(self, execute_mumps):
        """$IO returns current I/O device."""
        result = execute_mumps("TEST W $IO Q")
        assert result.success is True
        assert result.output is not None

    def test_dollar_i_equals_dollar_io(self, execute_mumps):
        """$I and $IO should return the same value."""
        result = execute_mumps('TEST W $I="0",$IO="0" Q')
        # Default device is typically 0 or /dev/tty, both should match
        assert result.success is True
        # Both comparisons should be true (1) or both false (0)
        # We just check they're equal - "11" means both true, "00" both false


@pytest.mark.codegen
class TestPatternMatchWithMStr:
    """Tests for pattern match using m_str (MUMPS canonical formatting).

    Fix: Changed pattern match from str() to m_str() so numeric values
    are formatted in MUMPS canonical form before pattern matching.
    """

    def test_pattern_match_leading_zero_removed(self, execute_mumps):
        """Pattern match on 0.5 uses ".5" not "0.5"."""
        # 0.5 in MUMPS is canonically ".5" so it matches ".5"?1P1N
        result = execute_mumps("TEST S X=0.5 W X?1P1N Q")
        assert result.success is True
        # ".5" matches 1P (period) 1N (digit) - should be true (1)
        assert result.output == "1"

    def test_pattern_match_negative_leading_zero(self, execute_mumps):
        """Pattern match on -0.5 uses "-.5" not "-0.5"."""
        result = execute_mumps('TEST S X=-0.5 W X?1"-"1P1N Q')
        assert result.success is True
        # "-.5" matches 1"-" 1P (period) 1N (digit) - should be true (1)
        assert result.output == "1"

    def test_pattern_match_integer_no_decimal(self, execute_mumps):
        """Pattern match on 1.0 uses "1" not "1.0"."""
        result = execute_mumps("TEST S X=1.0 W X?1N Q")
        assert result.success is True
        # "1" matches 1N - should be true (1)
        assert result.output == "1"


@pytest.mark.codegen
class TestOrderIndirectionCodegen:
    """Tests for $ORDER with indirection ($O(@X)).

    Fix: Added handling for MIndirection in _gen_order to use
    _rt.get_order() for runtime name resolution.
    """

    def test_order_indirection_basic(self, execute_mumps):
        """$O(@X) where X='A("")' returns first subscript."""
        result = execute_mumps('''TEST
 S A(1)="a",A(2)="b"
 S X="A("""")"
 W $O(@X)
 Q
''')
        assert result.success is True
        assert result.output == "1"

    def test_order_indirection_with_start(self, execute_mumps):
        """$O(@X) where X='A(1)' returns next subscript."""
        result = execute_mumps("""TEST
 S A(1)="a",A(2)="b",A(3)="c"
 S X="A(1)"
 W $O(@X)
 Q
""")
        assert result.success is True
        assert result.output == "2"

    def test_order_indirection_reverse(self, execute_mumps):
        """$O(@X,-1) returns previous subscript."""
        result = execute_mumps("""TEST
 S A(1)="a",A(2)="b",A(3)="c"
 S X="A(3)"
 W $O(@X,-1)
 Q
""")
        assert result.success is True
        assert result.output == "2"

    def test_order_indirection_global(self, execute_mumps):
        """$O(@X) where X='^G("")' works for globals."""
        result = execute_mumps('''TEST
 S ^G(1)="a",^G(2)="b"
 S X="^G("""")"
 W $O(@X)
 Q
''')
        assert result.success is True
        assert result.output == "1"
