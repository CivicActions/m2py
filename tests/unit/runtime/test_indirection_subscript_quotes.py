"""Tests for MUMPS-style subscript quote stripping in indirection paths.

When resolve_to_name() evaluates subscripts in a global name (e.g.,
^UTILITY(U,$J,IX) → ^UTILITY("^",77795,1009.802)), it uses _append_subscripts()
which adds double-quotes around string subscripts (MUMPS name syntax).

When those formatted names are re-parsed by _parse_subscripted_name(), the
quotes become part of the subscript string. The _strip_mumps_sub_quotes()
helper removes them so that the backend stores subscripts consistently
regardless of whether the SET came from compiled code or indirection.

Bug: Without quote stripping, ^UTILITY("^",...) would store subscript '"^"'
(3 chars with quotes) while compiled code stores "^" (1 char). This caused
data written via indirection to be invisible to direct reads and vice versa.
"""

import pytest

from m2py.runtime import MUMPSRuntime, _strip_mumps_sub_quotes


# =============================================================================
# Unit tests for _strip_mumps_sub_quotes helper
# =============================================================================


class TestStripMumpsSubQuotes:
    """Test the _strip_mumps_sub_quotes helper function."""

    def test_plain_string_unchanged(self):
        """Plain strings without MUMPS quotes pass through."""
        assert _strip_mumps_sub_quotes("hello") == "hello"

    def test_numeric_string_unchanged(self):
        """Numeric strings pass through."""
        assert _strip_mumps_sub_quotes("42") == "42"
        assert _strip_mumps_sub_quotes("3.14") == "3.14"
        assert _strip_mumps_sub_quotes("0") == "0"

    def test_empty_string_unchanged(self):
        """Empty string passes through."""
        assert _strip_mumps_sub_quotes("") == ""

    def test_single_char_unchanged(self):
        """Single character strings pass through even if it's a quote."""
        assert _strip_mumps_sub_quotes('"') == '"'
        assert _strip_mumps_sub_quotes("x") == "x"

    def test_simple_quoted_string(self):
        """Simple double-quoted strings are unquoted."""
        assert _strip_mumps_sub_quotes('"hello"') == "hello"

    def test_quoted_caret(self):
        """The ^ subscript from UTILITY globals is properly unquoted."""
        assert _strip_mumps_sub_quotes('"^"') == "^"

    def test_quoted_with_escaped_quotes(self):
        """Doubled quotes inside are unescaped."""
        assert _strip_mumps_sub_quotes('"FOO""BAR"') == 'FOO"BAR'

    def test_quoted_with_multiple_escaped_quotes(self):
        """Multiple doubled quotes inside are all unescaped."""
        assert _strip_mumps_sub_quotes('"A""B""C"') == 'A"B"C'

    def test_quoted_empty_content(self):
        """Quoted empty string becomes empty string."""
        assert _strip_mumps_sub_quotes('""') == ""

    def test_quoted_single_space(self):
        """Quoted space is unquoted."""
        assert _strip_mumps_sub_quotes('" "') == " "

    def test_unbalanced_quote_start_only(self):
        """Strings starting with quote but not ending: unchanged."""
        assert _strip_mumps_sub_quotes('"hello') == '"hello'

    def test_unbalanced_quote_end_only(self):
        """Strings ending with quote but not starting: unchanged."""
        assert _strip_mumps_sub_quotes('hello"') == 'hello"'


# =============================================================================
# Integration: indirection SET then direct GET consistency
# =============================================================================


class TestIndirectionSubscriptConsistency:
    """Test that data written via indirection is readable by direct code."""

    @pytest.fixture
    def execute_mumps(self):
        from m2py.codegen import generate_python

        def _execute(source: str, *, global_storage=None):
            python_code = generate_python(source)
            runtime = MUMPSRuntime(global_storage=global_storage)
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_set_via_indirection_read_direct(self, execute_mumps):
        """SET via @X where X has string subscripts, then read directly.

        This is the core bug scenario: indirection SET must store under the
        same subscripts that direct code uses.
        """
        code = 'TEST\n S X="^GLO(""key"")" S @X=42\n W ^GLO("key")\n Q'
        result = execute_mumps(code)
        assert result.output == "42"

    def test_set_direct_read_via_indirection(self, execute_mumps):
        """SET directly, then read via @X with string subscripts."""
        code = 'TEST\n S ^GLO("key")=99\n S X="^GLO(""key"")" W @X\n Q'
        result = execute_mumps(code)
        assert result.output == "99"

    def test_caret_subscript_via_indirection(self, execute_mumps):
        """The ^ character as a subscript is the DMUFINIT scenario.

        A variable contains "^" as its value, which becomes a subscript via
        indirection. The formatted string has ^UTIL("^",...) which must be
        stored as subscript "^" (1 char), not '"^"' (3 chars).
        """
        code = (
            "TEST\n"
            ' S U="^",J=123\n'
            ' S X="^UTIL("_""""_U_""""_","_J_")"\n'
            " S @X=1\n"
            ' W ^UTIL("^",123)\n'
            " Q"
        )
        result = execute_mumps(code)
        assert result.output == "1"

    def test_numeric_subscript_via_indirection(self, execute_mumps):
        """Numeric subscripts don't get MUMPS quotes, should be fine."""
        code = 'TEST\n S X="^GLO" S @X@(1,2,3)=42\n W ^GLO(1,2,3)\n Q'
        result = execute_mumps(code)
        assert result.output == "42"

    def test_data_via_indirection_with_string_sub(self, execute_mumps):
        """$DATA through indirection with string subscripts."""
        code = 'TEST\n S ^GLO("key")=42\n S X="^GLO(""key"")" W $D(@X)\n Q'
        result = execute_mumps(code)
        assert result.output == "1"

    def test_kill_via_indirection_with_string_sub(self, execute_mumps):
        """KILL via indirection with string subscripts.

        After KILL, $DATA should return 0.
        """
        code = (
            'TEST\n S ^GLO("key")=42\n S X="^GLO(""key"")" K @X\n W $D(^GLO("key"))\n Q'
        )
        result = execute_mumps(code)
        assert result.output == "0"

    def test_multi_level_string_subscripts(self, execute_mumps):
        """Multiple string subscripts at different levels."""
        code = (
            "TEST\n"
            ' S ^GLO("a","b","c")=1\n'
            ' S X="^GLO" S @X@("a","b","c")=99\n'
            ' W ^GLO("a","b","c")\n'
            " Q"
        )
        result = execute_mumps(code)
        assert result.output == "99"


# =============================================================================
# Regression: DMUFINIT-like indirection pattern
# =============================================================================


class TestDmufinitPattern:
    """Test the specific indirection pattern from DMUFINIT.

    DMUFINIT uses a pattern where:
    1. A variable U contains "^" (the uparrow used as a delimiter)
    2. U is used as a subscript in a global SET via indirection
    3. Later, direct code reads the same global with "^" subscript

    Without quote stripping, step 2 stores under '"^"' and step 3
    reads from "^" — a mismatch.
    """

    @pytest.fixture
    def execute_mumps(self):
        from m2py.codegen import generate_python

        def _execute(source: str, *, global_storage=None):
            python_code = generate_python(source)
            runtime = MUMPSRuntime(global_storage=global_storage)
            return runtime.execute(python_code, capture_output=True)

        return _execute

    def test_utility_pattern_set_read(self, execute_mumps):
        """Simulate UTILITY global SET via indirection + direct read.

        Like DMUFINIT: S @DN@(U,$J,IX,...)=val then direct reads.
        """
        code = (
            "TEST\n"
            ' S U="^",IX=1009.801\n'
            ' S DN="^UTILITY"\n'
            " S @DN@(U,$J,IX)=42\n"
            ' W ^UTILITY("^",$J,1009.801)\n'
            " Q"
        )
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "42"

    def test_utility_pattern_query(self, execute_mumps):
        """$QUERY after indirection SET should find the data."""
        code = (
            "TEST\n"
            ' S U="^",IX=1009.801\n'
            ' S DN="^UTILITY"\n'
            ' S @DN@(U,$J,IX,"A")=1\n'
            ' S @DN@(U,$J,IX,"B")=2\n'
            ' S Q=$Q(^UTILITY("^",$J,IX,""))\n'
            " W Q\n"
            " Q"
        )
        result = execute_mumps(code)
        assert result.success is True
        # Should find the first subscript after ""
        assert "1009.801" in result.output
        assert '"A"' in result.output or "A" in result.output
