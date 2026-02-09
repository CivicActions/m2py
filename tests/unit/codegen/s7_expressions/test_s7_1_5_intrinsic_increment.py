"""Tests for $INCREMENT intrinsic function code generation.

MUMPS $INCREMENT ($I, $INCR) atomically reads, adds, and writes back
a variable value. If the variable is undefined, it treats the current
value as 0 before incrementing.

Syntax:
    $INCREMENT(variable)         ; increment by 1
    $INCREMENT(variable, amount) ; increment by amount

Valid abbreviations: $I, $INCR, $INCREMENT
"""

import pytest


@pytest.mark.codegen
class TestIncrementBasicLocal:
    """$INCREMENT on local variables — basic operations."""

    def test_increment_undefined_default(self, execute_mumps):
        """$I on undefined variable treats as 0, increments by 1."""
        result = execute_mumps("TEST W $I(X),! W X Q")
        assert result.output == "1\n1"

    def test_increment_defined_default(self, execute_mumps):
        """$I on defined variable increments by 1."""
        result = execute_mumps("TEST S X=5 W $I(X),! W X Q")
        assert result.output == "6\n6"

    def test_increment_with_amount(self, execute_mumps):
        """$I with explicit increment amount."""
        result = execute_mumps("TEST S X=5 W $I(X,3),! W X Q")
        assert result.output == "8\n8"

    def test_increment_negative(self, execute_mumps):
        """$I with negative increment (decrement)."""
        result = execute_mumps("TEST S X=10 W $I(X,-3),! W X Q")
        assert result.output == "7\n7"

    def test_increment_decimal(self, execute_mumps):
        """$I with decimal increment amount."""
        result = execute_mumps("TEST K Y W $I(Y,2.5),! W Y Q")
        assert result.output == "2.5\n2.5"

    def test_increment_nonnumeric_string(self, execute_mumps):
        """$I on non-numeric string variable treats as 0."""
        result = execute_mumps('TEST S Z="abc" W $I(Z),! W Z Q')
        assert result.output == "1\n1"

    def test_increment_returns_new_value(self, execute_mumps):
        """$I returns the new value (not old)."""
        result = execute_mumps("TEST S X=100 W $I(X,50) Q")
        assert result.output == "150"

    def test_increment_multiple_times(self, execute_mumps):
        """$I called multiple times accumulates."""
        result = execute_mumps("TEST K X W $I(X),! W $I(X),! W $I(X),! W X Q")
        assert result.output == "1\n2\n3\n3"

    def test_increment_zero(self, execute_mumps):
        """$I with amount 0 is a no-op (just returns current value)."""
        result = execute_mumps("TEST S X=42 W $I(X,0),! W X Q")
        assert result.output == "42\n42"


@pytest.mark.codegen
class TestIncrementAbbreviations:
    """$INCREMENT abbreviation forms."""

    def test_dollar_i_with_args(self, execute_mumps):
        """$I(var) is $INCREMENT when arguments are present."""
        result = execute_mumps("TEST S X=0 W $I(X),! W X Q")
        assert result.output == "1\n1"

    def test_dollar_incr(self, execute_mumps):
        """$INCR is a valid abbreviation for $INCREMENT."""
        result = execute_mumps("TEST S X=0 W $INCR(X),! W X Q")
        assert result.output == "1\n1"

    def test_dollar_increment_full(self, execute_mumps):
        """$INCREMENT is the full form."""
        result = execute_mumps("TEST S X=0 W $INCREMENT(X),! W X Q")
        assert result.output == "1\n1"


@pytest.mark.codegen
class TestIncrementSubscripted:
    """$INCREMENT on subscripted local variables."""

    def test_subscripted_undefined(self, execute_mumps):
        """$I on undefined subscripted variable creates it."""
        result = execute_mumps("TEST W $I(X(1,2)),! W X(1,2) Q")
        assert result.output == "1\n1"

    def test_subscripted_defined(self, execute_mumps):
        """$I on defined subscripted variable increments."""
        result = execute_mumps("TEST S X(1,2)=5 W $I(X(1,2),10),! W X(1,2) Q")
        assert result.output == "15\n15"

    def test_subscripted_preserves_parent(self, execute_mumps):
        """$I on subscripted var doesn't affect parent node."""
        result = execute_mumps('TEST S X="root" W $I(X(1)),! W X,! W X(1) Q')
        assert result.output == "1\nroot\n1"


@pytest.mark.codegen
class TestIncrementGlobal:
    """$INCREMENT on global variables."""

    def test_global_undefined(self, execute_mumps):
        """$I on undefined global treats as 0."""
        result = execute_mumps("TEST K ^G W $I(^G),! W ^G Q")
        assert result.output == "1\n1"

    def test_global_defined(self, execute_mumps):
        """$I on defined global increments."""
        result = execute_mumps("TEST S ^G=10 W $I(^G),! W ^G Q")
        assert result.output == "11\n11"

    def test_global_with_amount(self, execute_mumps):
        """$I on global with explicit amount."""
        result = execute_mumps("TEST S ^G=10 W $I(^G,-5),! W ^G Q")
        assert result.output == "5\n5"

    def test_global_subscripted(self, execute_mumps):
        """$I on subscripted global."""
        result = execute_mumps("TEST S ^G(1)=5 W $I(^G(1),10),! W ^G(1) Q")
        assert result.output == "15\n15"


@pytest.mark.codegen
class TestIncrementNakedGlobal:
    """$INCREMENT on naked global references."""

    def test_naked_global(self, execute_mumps):
        """$I on naked global after setting naked indicator."""
        result = execute_mumps("TEST S ^G(1)=5 W $I(^(1),100),! W ^G(1) Q")
        assert result.output == "105\n105"


@pytest.mark.codegen
class TestIncrementIndirection:
    """$INCREMENT with indirection (@)."""

    def test_simple_indirection(self, execute_mumps):
        """$I(@A) where A contains variable name."""
        result = execute_mumps('TEST S A="X" W $I(@A),! W X Q')
        assert result.output == "1\n1"

    def test_indirection_on_global(self, execute_mumps):
        """$I(@A) where A contains global variable name."""
        result = execute_mumps('TEST S A="^G" W $I(@A),! W ^G Q')
        assert result.output == "1\n1"


@pytest.mark.codegen
class TestIncrementInExpression:
    """$INCREMENT used within larger expressions."""

    def test_increment_in_set(self, execute_mumps):
        """$I result used in SET."""
        result = execute_mumps("TEST S X=0 S Y=$I(X) W X,! W Y Q")
        assert result.output == "1\n1"

    def test_increment_in_arithmetic(self, execute_mumps):
        """$I result used in arithmetic."""
        result = execute_mumps("TEST S X=5 W $I(X)+10 Q")
        assert result.output == "16"

    def test_increment_in_if(self, execute_mumps):
        """$I in IF condition — side effect occurs."""
        result = execute_mumps("TEST S X=0 I $I(X) W X Q")
        assert result.output == "1"


@pytest.mark.codegen
class TestIncrementEdgeCases:
    """$INCREMENT edge cases and MUMPS-specific behavior."""

    def test_increment_numeric_string(self, execute_mumps):
        """$I on a string that starts with a number."""
        result = execute_mumps('TEST S X="3abc" W $I(X),! W X Q')
        assert result.output == "4\n4"

    def test_increment_large_number(self, execute_mumps):
        """$I with large numbers."""
        result = execute_mumps("TEST S X=999999 W $I(X),! W X Q")
        assert result.output == "1000000\n1000000"

    def test_increment_expression_amount(self, execute_mumps):
        """$I with computed increment amount."""
        result = execute_mumps("TEST S X=0,Y=5 W $I(X,Y+3),! W X Q")
        assert result.output == "8\n8"
