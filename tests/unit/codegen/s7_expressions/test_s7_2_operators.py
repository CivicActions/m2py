"""Tests for Operators code generation (§7.2).

Reference: MUMPS 1995 ANSI Standard, Section 7.2
"""

import pytest


@pytest.mark.codegen
class TestOperatorsCodegen:
    """Codegen-level tests for operators code generation (§7.2)."""

    def test_addition(self, execute_mumps):
        """Addition generates Python + with numeric coercion (§7.2).

        User Story 1 acceptance scenario 3:
        Given: TEST W 2+3 Q
        When: generated and executed
        Then: output is "5"
        """
        result = execute_mumps("TEST\n W 2+3\n Q\n")
        assert result.output == "5"
        assert result.success is True

    def test_subtraction(self, execute_mumps):
        """Subtraction generates Python - with numeric coercion (§7.2)."""
        result = execute_mumps("TEST\n W 5-3\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_multiplication(self, execute_mumps):
        """Multiplication generates Python * with numeric coercion (§7.2).

        YDB verified: W 3*4 → 12
        """
        result = execute_mumps("TEST\n W 3*4\n Q\n")
        assert result.output == "12"
        assert result.success is True

    def test_division(self, execute_mumps):
        """Division generates Python / with numeric coercion (§7.2).

        YDB verified: W 10/4 → 2.5
        """
        result = execute_mumps("TEST\n W 10/4\n Q\n")
        assert result.output == "2.5"
        assert result.success is True

    def test_integer_division(self, execute_mumps):
        """Integer division generates Python int(x/y) for truncation (§7.2).

        User Story 5 acceptance scenario 2:
        YDB verified: 7\3 → 2
        """
        result = execute_mumps("TEST\n W 7\\3\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_integer_division_second(self, execute_mumps):
        """Integer division acceptance scenario 4.

        YDB verified: 10\4 → 2
        """
        result = execute_mumps("TEST\n W 10\\4\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_integer_division_negative(self, execute_mumps):
        """Integer division with negative number uses truncation towards zero.

        YDB verified: -7\3 → -2 (not -3 as floor division would give)
        """
        result = execute_mumps("TEST\n W -7\\3\n Q\n")
        assert result.output == "-2"
        assert result.success is True

    def test_modulo(self, execute_mumps):
        """Modulo generates Python % (§7.2).

        User Story 5 acceptance scenario 1:
        YDB verified: 7#3 → 1
        """
        result = execute_mumps("TEST\n W 7#3\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_modulo_second(self, execute_mumps):
        """Modulo acceptance scenario 3.

        YDB verified: 10#4 → 2
        """
        result = execute_mumps("TEST\n W 10#4\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_modulo_negative_dividend(self, execute_mumps):
        """Modulo with negative dividend.

        YDB verified: -7#3 → 2
        """
        result = execute_mumps("TEST\n W -7#3\n Q\n")
        assert result.output == "2"
        assert result.success is True

    def test_modulo_zero_dividend(self, execute_mumps):
        """Modulo with zero dividend.

        YDB verified: 0#5 → 0
        """
        result = execute_mumps("TEST\n W 0#5\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_exponentiation(self, execute_mumps):
        """Exponentiation operator ** (§7.2).

        YDB verified: 2**3 → 8
        """
        result = execute_mumps("TEST\n W 2**3\n Q\n")
        assert result.output == "8"
        assert result.success is True

    def test_exponentiation_zero_exponent(self, execute_mumps):
        """Any non-zero number to the power 0 is 1 (§7.2).

        YDB verified: 10**0 → 1
        """
        result = execute_mumps("TEST\n W 10**0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_exponentiation_negative_base(self, execute_mumps):
        """Negative base with integer exponent (§7.2).

        YDB verified: (-2)**3 → -8
        """
        result = execute_mumps("TEST\n W (-2)**3\n Q\n")
        assert result.output == "-8"
        assert result.success is True

    def test_exponentiation_negative_exponent(self, execute_mumps):
        """Negative exponent produces reciprocal (§7.2).

        YDB verified: 2**-1 → .5
        """
        result = execute_mumps("TEST\n W 2**-1\n Q\n")
        assert result.output == ".5"
        assert result.success is True

    def test_exponentiation_zero_to_zero(self, execute_mumps):
        """0**0 is defined as 1 in MUMPS (§7.2).

        YDB verified: 0**0 → 1
        """
        result = execute_mumps("TEST\n W 0**0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_exponentiation_fractional_base(self, execute_mumps):
        """Fractional base with integer exponent (§7.2).

        YDB verified: 2.5**2 → 6.25
        """
        result = execute_mumps("TEST\n W 2.5**2\n Q\n")
        assert result.output == "6.25"
        assert result.success is True

    def test_concatenation_strings(self, execute_mumps):
        """Concatenation joins strings correctly (§7.2).

        YDB verified: "A"_"B"_"C" → "ABC"
        """
        result = execute_mumps('TEST\n W "A"_"B"_"C"\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

    def test_concatenation_with_number(self, execute_mumps):
        """Concatenation coerces numbers to strings (§7.2).

        YDB verified: "X"_1_"Y" → "X1Y"
        """
        result = execute_mumps('TEST\n W "X"_1_"Y"\n Q\n')
        assert result.output == "X1Y"
        assert result.success is True

    def test_concatenation_with_variable(self, execute_mumps):
        """Concatenation works with variables (§7.2).

        YDB verified: S X="Hello" W X_" World" → "Hello World"
        """
        result = execute_mumps('TEST\n S X="Hello" W X_" World"\n Q\n')
        assert result.output == "Hello World"
        assert result.success is True

    def test_concatenation_numbers_only(self, execute_mumps):
        """Concatenation of numbers coerces all to strings (§7.2).

        YDB verified: 1_2_3 → "123"
        """
        result = execute_mumps("TEST\n W 1_2_3\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_equals(self, execute_mumps):
        """Equals generates Python == comparison (§7.2).

        YDB verified: W 5=5 → 1
        """
        result = execute_mumps("TEST\n W 5=5\n Q\n")
        assert result.output == "1"
        assert result.success is True

    # =========================================================================
    # Negated Comparison Operators Tests
    # =========================================================================

    def test_negated_equals_same_value(self, execute_mumps):
        """Negated equals returns 0 for equal values (§7.2).

        YDB verified: 5'=5 → 0
        """
        result = execute_mumps("TEST\n W 5'=5\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_negated_equals_different_values(self, execute_mumps):
        """Negated equals returns 1 for different values (§7.2).

        YDB verified: 5'=6 → 1
        """
        result = execute_mumps("TEST\n W 5'=6\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_negated_less_than(self, execute_mumps):
        """Negated less-than (>=) returns correct value (§7.2).

        YDB verified: 10'<5 → 1 (10 is not less than 5)
        """
        result = execute_mumps("TEST\n W 10'<5\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_negated_greater_than(self, execute_mumps):
        """Negated greater-than (<=) returns correct value (§7.2).

        YDB verified: 5'>10 → 1 (5 is not greater than 10)
        """
        result = execute_mumps("TEST\n W 5'>10\n Q\n")
        assert result.output == "1"
        assert result.success is True

    # =========================================================================
    # Negated Contains, Follows, and Logical Operators Tests
    # =========================================================================

    def test_not_contains_true(self, execute_mumps):
        """Not-contains operator returns 1 when substring not found (§7.2).

        YDB verified: "ABC"'["X" → 1
        """
        result = execute_mumps('TEST\n W "ABC"\'["X"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_not_contains_false(self, execute_mumps):
        """Not-contains operator returns 0 when substring found (§7.2).

        YDB verified: "ABC"'["B" → 0
        """
        result = execute_mumps('TEST\n W "ABC"\'["B"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_not_follows_true(self, execute_mumps):
        """Not-follows operator returns 1 when left does not sort after right (§7.2).

        YDB verified: "A"']"B" → 1
        """
        result = execute_mumps('TEST\n W "A"\']"B"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_not_follows_false(self, execute_mumps):
        """Not-follows operator returns 0 when left sorts after right (§7.2).

        YDB verified: "B"']"A" → 0
        """
        result = execute_mumps('TEST\n W "B"\']"A"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_not_sorts_after_true(self, execute_mumps):
        """Not-sorts-after operator returns 1 when left does not strictly sort after right (§7.2).

        YDB verified: "A"']]"A" → 1 (same values)
        """
        result = execute_mumps('TEST\n W "A"\']]"A"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_not_sorts_after_false(self, execute_mumps):
        """Not-sorts-after operator returns 0 when left strictly sorts after right (§7.2).

        YDB verified: "B"']]"A" → 0
        """
        result = execute_mumps('TEST\n W "B"\']]"A"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_not_and_true(self, execute_mumps):
        """Not-and operator returns 1 when either operand is falsy (§7.2).

        '& is NAND: returns 1 unless both operands are truthy.

        YDB verified: 1'&0 → 1
        """
        result = execute_mumps("TEST\n W 1'&0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_not_and_false(self, execute_mumps):
        """Not-and operator returns 0 when both operands are truthy (§7.2).

        YDB verified: 1'&1 → 0
        """
        result = execute_mumps("TEST\n W 1'&1\n Q\n")
        assert result.output == "0"
        assert result.success is True

    def test_not_or_true(self, execute_mumps):
        """Not-or operator returns 1 when both operands are falsy (§7.2).

        '! is NOR: returns 1 only when both operands are falsy.

        YDB verified: 0'!0 → 1
        """
        result = execute_mumps("TEST\n W 0'!0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_not_or_false(self, execute_mumps):
        """Not-or operator returns 0 when either operand is truthy (§7.2).

        YDB verified: 1'!0 → 0
        """
        result = execute_mumps("TEST\n W 1'!0\n Q\n")
        assert result.output == "0"
        assert result.success is True

    # =========================================================================
    # Contains and Follows Operators Tests (Spec 011 Phase 10)
    # =========================================================================

    def test_contains_match(self, execute_mumps):
        """Contains operator returns 1 when substring found (§7.2).

        YDB verified: "ABC"["B" → 1
        """
        result = execute_mumps('TEST\n W "ABC"["B"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_contains_no_match(self, execute_mumps):
        """Contains operator returns 0 when substring not found (§7.2).

        YDB verified: "ABC"["X" → 0
        """
        result = execute_mumps('TEST\n W "ABC"["X"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_contains_empty_string(self, execute_mumps):
        """Contains operator: empty string is in any string (§7.2).

        YDB verified: "ABC"["" → 1
        """
        result = execute_mumps('TEST\n W "ABC"[""\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_follows_true(self, execute_mumps):
        """Follows operator returns 1 when left sorts after right (§7.2).

        YDB verified: "B"]"A" → 1
        """
        result = execute_mumps('TEST\n W "B"]"A"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_follows_false(self, execute_mumps):
        """Follows operator returns 0 when left does not sort after right (§7.2).

        YDB verified: "A"]"B" → 0
        """
        result = execute_mumps('TEST\n W "A"]"B"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_sorts_after_true(self, execute_mumps):
        """Sorts-after operator returns 1 when left strictly sorts after right (§7.2).

        YDB verified: "B"]]"A" → 1
        """
        result = execute_mumps('TEST\n W "B"]]"A"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_sorts_after_same_value(self, execute_mumps):
        """Sorts-after operator returns 0 for equal values (§7.2).

        YDB verified: "A"]]"A" → 0
        """
        result = execute_mumps('TEST\n W "A"]]"A"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_sorts_after_empty_string(self, execute_mumps):
        """Sorts-after: empty string never sorts after anything (§7.2).

        YDB verified: ""]]"A" → 0
        """
        result = execute_mumps('TEST\n W ""]]"A"\n Q\n')
        assert result.output == "0"
        assert result.success is True

    def test_sorts_after_numeric_collation(self, execute_mumps):
        """Sorts-after uses MUMPS collation, not string comparison (§7.2).

        MUMPS collation: numerics sort before strings, and numeric
        values are compared numerically. This differs from ] (follows)
        which uses simple string comparison.

        YDB verified: 10]]9 → 1 (numeric comparison)
        YDB verified: "10"]]"9" → 1 (numeric string comparison)
        Contrast: "10"]"9" → 0 (string comparison, "10" < "9")
        """
        result = execute_mumps("TEST\n W 10]]9\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_sorts_after_mixed_types(self, execute_mumps):
        """Sorts-after: strings sort after numbers in MUMPS collation (§7.2).

        YDB verified: "ABC"]]"9" → 1 (non-numeric string after numeric)
        YDB verified: "9"]]"ABC" → 0 (numeric sorts before string)
        """
        result = execute_mumps('TEST\n W "ABC"]]"9"\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_logical_and(self, execute_mumps):
        """Logical AND returns 1 if both operands are true (§7.2).

        YDB verified: W 1&1 → 1
        """
        result = execute_mumps("TEST\n W 1&1\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_logical_or(self, execute_mumps):
        """Logical OR returns 1 if either operand is true (§7.2).

        YDB verified: W 1!0 → 1
        """
        result = execute_mumps("TEST\n W 1!0\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_left_to_right_evaluation(self, execute_mumps):
        """Operators evaluate left-to-right without precedence (§7.2).

        MUMPS: 2+3*4 = (2+3)*4 = 5*4 = 20
        NOT: 2+(3*4) = 2+12 = 14 (C/Python precedence)

        YDB verified: W 2+3*4 → 20
        """
        result = execute_mumps("TEST\n W 2+3*4\n Q\n")
        assert result.output == "20"
        assert result.success is True


# =============================================================================
# Parenthesized Expressions (024-vista-transpilation-fixes, Contract 1)
# =============================================================================


@pytest.mark.codegen
class TestParenExpr:
    """Contract 1: Parenthesized expressions must be handled in codegen.

    Validates FR-001: ParenExpr codegen fallback.
    """

    def test_paren_expr_grouping(self, execute_mumps):
        """(X+Y)*2 must group correctly — Contract 1 happy path."""
        code = "PAREN\n S X=3,Y=4\n S Z=(X+Y)*2\n W Z,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "14\n"

    def test_paren_expr_double_wrapped(self, execute_mumps):
        """((X+Y)) double-parenthesized expression."""
        code = "PAREN\n S X=3,Y=4\n S A=((X+Y))\n W A,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "7\n"

    def test_paren_expr_nested_operations(self, execute_mumps):
        """((A+B)*(C-D)) nested parentheses with multiple ops."""
        code = "TEST\n S A=2,B=3,C=10,D=4\n W ((A+B)*(C-D)),!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "30\n"

    def test_paren_expr_in_condition(self, execute_mumps):
        """Parenthesized expression in IF condition."""
        code = 'TEST\n S X=5 I (X>3) W "yes",!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "yes\n"

    def test_paren_expr_single_value(self, execute_mumps):
        """(X) single-value parenthesized expression."""
        code = "TEST\n S X=42 W (X),!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "42\n"

    def test_paren_expr_in_function_arg(self, execute_mumps):
        """Parenthesized expression as function argument."""
        code = 'TEST\n S X="hello" W $L((X)),!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "5\n"

    def test_paren_expr_postconditioned_quit(self, generate_python):
        """Q:X=""!(Y="") — postconditioned QUIT with parenthesized OR (PRCACV10 pattern)."""
        code = 'TEST\n S X="",Y="hello"\n Q:X=""!(Y="")\n W "not reached",!\n Q\n'
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")

    def test_paren_expr_unary_plus_concat(self, generate_python):
        """+(expr) — unary plus on parenthesized concatenation (PRCACV10 pattern)."""
        code = 'TEST\n S A="1",B="2"\n W +($G(A)_$G(B)),!\n Q\n'
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")

    def test_paren_expr_complex_if_condition(self, generate_python):
        """I cond1,(cond2!cond3) — parenthesized OR in multi-condition IF (DGMTXE2 pattern)."""
        code = 'TEST\n S DV="FK",Y="12345678901234567890"\n'
        code += ' I $L(Y)>19,(DV["F"!(DV["K")) W "match",!\n Q\n'
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")


# =============================================================================
# Unary Prefix Expressions (024-vista-transpilation-fixes, Contract 20)
# =============================================================================


@pytest.mark.codegen
class TestUnaryPrefixedExpr:
    """Contract 20: UnaryPrefixedExpr and Expr wrapper nodes in codegen."""

    def test_unary_not_operator(self, execute_mumps):
        """'X (NOT) operator via UnaryPrefixedExpr path."""
        code = "TEST\n S X=0 W 'X,!\n S X=1 W 'X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "1\n0\n"

    def test_unary_negation(self, execute_mumps):
        """Unary minus via UnaryPrefixedExpr path."""
        code = "TEST\n S X=5 W -X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "-5\n"

    def test_unary_plus(self, execute_mumps):
        """Unary plus (numeric coercion) via UnaryPrefixedExpr path."""
        code = 'TEST\n S X="3abc" W +X,!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "3\n"

    def test_double_not(self, execute_mumps):
        """Double negation ''X."""
        code = "TEST\n S X=5 W ''X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "1\n"

    def test_not_zero_string(self, execute_mumps):
        """Unary NOT of zero-valued string."""
        code = 'TEST\n S X="0abc" W \'X,!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "1\n"

    def test_unary_not_in_postcondition(self, generate_python):
        """Q:'CRNR!('$T) — unary NOT on variable and $TEST (GMRCIAC2 pattern)."""
        code = "TEST\n S CRNR=0\n Q:'CRNR!('$T)\n W \"should not reach\",!\n Q\n"
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")


# =============================================================================
# Comparison Operators >= <= (024-vista-transpilation-fixes, Contract 4)
# =============================================================================


@pytest.mark.codegen
class TestComparisonOperators:
    """Contract 4: >= and <= operators must work correctly."""

    def test_gte_true(self, execute_mumps):
        """5>=3 is true."""
        result = execute_mumps('CMPOP\n I 5>=3 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_gte_false(self, execute_mumps):
        """3>=5 is false."""
        result = execute_mumps('CMPOP\n I 3>=5 W "yes",!\n Q\n')
        assert result.output == ""

    def test_gte_equal(self, execute_mumps):
        """5>=5 is true."""
        result = execute_mumps('CMPOP\n I 5>=5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_true(self, execute_mumps):
        """3<=5 is true."""
        result = execute_mumps('CMPOP\n I 3<=5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_false(self, execute_mumps):
        """5<=3 is false."""
        result = execute_mumps('CMPOP\n I 5<=3 W "yes",!\n Q\n')
        assert result.output == ""

    def test_lte_equal(self, execute_mumps):
        """5<=5 is true."""
        result = execute_mumps('CMPOP\n I 5<=5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_contract_4_full(self, execute_mumps):
        """Full Contract 4 scenario."""
        code = (
            "CMPOP\n"
            ' I 5>=3 W "5>=3:yes",!\n'
            ' I 3>=5 W "3>=5:yes",!\n'
            ' I 5>=5 W "5>=5:yes",!\n'
            ' I 3<=5 W "3<=5:yes",!\n'
            ' I 5<=3 W "5<=3:yes",!\n'
            ' I 5<=5 W "5<=5:yes",!\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "5>=3:yes\n5>=5:yes\n3<=5:yes\n5<=5:yes\n"

    def test_gte_with_string_coercion(self, execute_mumps):
        """>=/<= with string operands use MUMPS numeric coercion."""
        result = execute_mumps('TEST\n I "5">="3" W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_negative_numbers(self, execute_mumps):
        """-3<=-1 is true."""
        result = execute_mumps('TEST\n I -3<=-1 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_gte_with_zero(self, execute_mumps):
        """0>=0 is true."""
        result = execute_mumps('TEST\n I 0>=0 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_with_decimals(self, execute_mumps):
        """1.5<=2.5 is true."""
        result = execute_mumps('TEST\n I 1.5<=2.5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_in_if_condition(self, execute_mumps):
        """I +X<=0 — <= in IF with unary plus (ICDSELDS pattern)."""
        code = 'TEST\n S X=-3\n I +X<=0 W "yes",!\n Q\n'
        result = execute_mumps(code)
        assert result.output == "yes\n"

    def test_lte_in_postconditioned_set(self, execute_mumps):
        """S:(X<=DAYS) Q=1 — <= in postconditioned SET (DVBACER1 pattern)."""
        code = "TEST\n S X=5,DAYS=10,Q=0\n S:(X<=DAYS) Q=1\n W Q,!\n Q\n"
        result = execute_mumps(code)
        assert result.output == "1\n"
