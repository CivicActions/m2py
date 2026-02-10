"""Unit tests for m2py.core.tokenizer.split_at_toplevel.

Validates the single source of truth for delimiter-aware string splitting
that respects parenthesis nesting and MUMPS double-quote semantics.
"""

from m2py.core.tokenizer import split_at_toplevel


class TestSplitAtToplevel:
    """Core splitting behavior."""

    def test_empty_string(self):
        assert split_at_toplevel("") == [""]

    def test_no_delimiter(self):
        assert split_at_toplevel("ABC") == ["ABC"]

    def test_simple_split(self):
        assert split_at_toplevel("A,B,C") == ["A", "B", "C"]

    def test_two_parts(self):
        assert split_at_toplevel("X,Y") == ["X", "Y"]

    def test_trailing_comma(self):
        assert split_at_toplevel("A,B,") == ["A", "B", ""]

    def test_leading_comma(self):
        assert split_at_toplevel(",A,B") == ["", "A", "B"]

    def test_consecutive_commas(self):
        assert split_at_toplevel("A,,B") == ["A", "", "B"]

    def test_single_comma(self):
        assert split_at_toplevel(",") == ["", ""]


class TestParenthesisNesting:
    """Commas inside parentheses must not split."""

    def test_simple_nested_parens(self):
        assert split_at_toplevel("A(1,2),B") == ["A(1,2)", "B"]

    def test_nested_parens_multiple(self):
        assert split_at_toplevel("A(1,2),B(3,4)") == ["A(1,2)", "B(3,4)"]

    def test_deeply_nested_parens(self):
        assert split_at_toplevel("$P(A(1,2),3),B") == ["$P(A(1,2),3)", "B"]

    def test_function_call(self):
        assert split_at_toplevel("$P(X,Y),Z") == ["$P(X,Y)", "Z"]

    def test_no_split_inside_parens(self):
        assert split_at_toplevel("F(A,B,C)") == ["F(A,B,C)"]

    def test_paren_depth_tracking(self):
        """Nested parens at depth > 1 don't cause premature splitting."""
        assert split_at_toplevel("A(B(1,2),C(3,4)),D") == [
            "A(B(1,2),C(3,4))",
            "D",
        ]


class TestQuoteHandling:
    """Commas inside MUMPS double-quoted strings must not split."""

    def test_quoted_comma(self):
        assert split_at_toplevel('"A,B"') == ['"A,B"']

    def test_quoted_and_unquoted(self):
        assert split_at_toplevel('"A,B",C') == ['"A,B"', "C"]

    def test_multiple_quoted(self):
        assert split_at_toplevel('"X,Y","A,B"') == ['"X,Y"', '"A,B"']

    def test_mumps_escaped_quotes(self):
        """MUMPS doubles quotes to embed a literal quote: ""."""
        assert split_at_toplevel('"A""B",C') == ['"A""B"', "C"]

    def test_mumps_escaped_quote_with_comma(self):
        """Comma after escaped quote should NOT split inside string."""
        assert split_at_toplevel('"A"",""B",C') == ['"A"",""B"', "C"]

    def test_empty_quoted_string(self):
        assert split_at_toplevel('"",A') == ['""', "A"]

    def test_respect_quotes_false(self):
        """When respect_quotes=False, commas inside quotes DO split."""
        assert split_at_toplevel('"A,B",C', respect_quotes=False) == [
            '"A',
            'B"',
            "C",
        ]


class TestMumpsExpressions:
    """Real-world MUMPS expression patterns."""

    def test_subscripted_global(self):
        result = split_at_toplevel("^V1A(A1,@A(1)-1),^V1A(@A(1),^V1A(A2),3-A1)")
        assert result == [
            "^V1A(A1,@A(1)-1)",
            "^V1A(@A(1),^V1A(A2),3-A1)",
        ]

    def test_write_format_args(self):
        assert split_at_toplevel('!?3,"AB"') == ["!?3", '"AB"']

    def test_indirection_args(self):
        assert split_at_toplevel("@B(2),@B(3)") == ["@B(2)", "@B(3)"]

    def test_kill_args_simple(self):
        assert split_at_toplevel("A,B,C(1,2)") == ["A", "B", "C(1,2)"]

    def test_set_multiple_targets(self):
        assert split_at_toplevel("(A,B,C)=1") == ["(A,B,C)=1"]

    def test_dollar_piece(self):
        assert split_at_toplevel('$P("A|B|C","|",I),X') == [
            '$P("A|B|C","|",I)',
            "X",
        ]

    def test_arithmetic_in_subscript(self):
        assert split_at_toplevel("A(I+1),B(J-1)") == ["A(I+1)", "B(J-1)"]


class TestCustomDelimiter:
    """Non-comma delimiters."""

    def test_space_delimiter(self):
        assert split_at_toplevel("A B C", delimiter=" ") == ["A", "B", "C"]

    def test_pipe_delimiter(self):
        assert split_at_toplevel("A|B|C", delimiter="|") == ["A", "B", "C"]

    def test_paren_nesting_with_custom(self):
        assert split_at_toplevel("A(1 2) B", delimiter=" ") == ["A(1 2)", "B"]
