"""Unit tests for m2py.core.parsing.

Validates parse_subscripted_name and canonicalize_subscript — the single
source of truth for parsing MUMPS subscripted variable names.
"""

from m2py.core.parsing import canonicalize_subscript, parse_subscripted_name


class TestParseSubscriptedName:
    """Tests for parse_subscripted_name."""

    def test_simple_name(self):
        assert parse_subscripted_name("X") == ("X", [])

    def test_global_name(self):
        assert parse_subscripted_name("^GLO") == ("^GLO", [])

    def test_single_subscript(self):
        assert parse_subscripted_name("A(1)") == ("A", ["1"])

    def test_multiple_subscripts(self):
        assert parse_subscripted_name("ARR(1,2)") == ("ARR", ["1", "2"])

    def test_three_subscripts(self):
        assert parse_subscripted_name("A(1,2,3)") == ("A", ["1", "2", "3"])

    def test_global_with_subscripts(self):
        assert parse_subscripted_name("^GLO(1)") == ("^GLO", ["1"])

    def test_global_multiple_subscripts(self):
        assert parse_subscripted_name("^GLO(X,Y)") == ("^GLO", ["X", "Y"])

    def test_quoted_subscript(self):
        """Quoted subscripts are returned as-is with quotes."""
        assert parse_subscripted_name('A("key")') == ("A", ['"key"'])

    def test_quoted_subscript_with_comma(self):
        """Commas inside quotes don't split subscripts."""
        assert parse_subscripted_name('A("B,C")') == ("A", ['"B,C"'])

    def test_mixed_subscripts(self):
        assert parse_subscripted_name('ARR(1,"A,B",3)') == (
            "ARR",
            ["1", '"A,B"', "3"],
        )

    def test_empty_parens(self):
        """Empty parentheses return no subscripts."""
        assert parse_subscripted_name("A()") == ("A", [])

    def test_no_closing_paren(self):
        """Name with opening paren but no closing paren is treated as plain name."""
        assert parse_subscripted_name("A(1") == ("A(1", [])

    def test_nested_parens_in_subscript(self):
        """Subscript expressions with nested parens are preserved."""
        assert parse_subscripted_name("A($P(X,Y))") == ("A", ["$P(X,Y)"])

    def test_indirection_in_subscript(self):
        """Indirection expressions with parens are preserved."""
        assert parse_subscripted_name("A(@B(1),C)") == ("A", ["@B(1)", "C"])

    def test_expression_not_ending_with_paren(self):
        """Expressions like '@A(1)-1' are NOT subscripted names."""
        assert parse_subscripted_name("@A(1)-1") == ("@A(1)-1", [])

    def test_complex_global_subscripts(self):
        assert parse_subscripted_name("^V1A(A1,@A(1)-1)") == (
            "^V1A",
            ["A1", "@A(1)-1"],
        )

    def test_deeply_nested_expression(self):
        assert parse_subscripted_name("^V1A(@A(1),^V1A(A2),3-A1)") == (
            "^V1A",
            ["@A(1)", "^V1A(A2)", "3-A1"],
        )


class TestCanonicalizeSubscript:
    """Tests for canonicalize_subscript."""

    def test_integer(self):
        assert canonicalize_subscript("1") == 1
        assert isinstance(canonicalize_subscript("1"), int)

    def test_negative_integer(self):
        assert canonicalize_subscript("-5") == -5

    def test_zero(self):
        assert canonicalize_subscript("0") == 0

    def test_float(self):
        assert canonicalize_subscript("3.14") == 3.14
        assert isinstance(canonicalize_subscript("3.14"), float)

    def test_negative_float(self):
        assert canonicalize_subscript("-1.5") == -1.5

    def test_string(self):
        assert canonicalize_subscript("hello") == "hello"
        assert isinstance(canonicalize_subscript("hello"), str)

    def test_quoted_string(self):
        """Quoted strings stay as strings — no type conversion."""
        assert canonicalize_subscript('"key"') == '"key"'

    def test_empty_string(self):
        assert canonicalize_subscript("") == ""

    def test_leading_zeros(self):
        """Python int() strips leading zeros."""
        assert canonicalize_subscript("02") == 2

    def test_float_leading_zero(self):
        assert canonicalize_subscript("1.0") == 1.0
