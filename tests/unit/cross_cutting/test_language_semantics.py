"""Cross-cutting tests for MUMPS language semantics.

This file tests fundamental language behaviors that span multiple
commands and expressions:
- $TEST special variable modification (FR-047)
- Left-to-right evaluation without precedence (FR-050)
- Exclusive NEW scoping behavior (FR-048)
- Transaction nesting with $TLEVEL (FR-051)

Reference: MUMPS 1995 ANSI Standard, various sections
See also: FR-046-051 (language semantic requirements)
"""

import pytest

from m2py.parser import MUMPSParser


# =============================================================================
# $TEST Special Variable Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_2_09_if.py
# =============================================================================


@pytest.mark.codegen
class TestTestVariableCodegen:
    """Codegen tests for $TEST behavior.

    Generated Python must correctly maintain $TEST state.
    Reference: §7.1.4.10, §8.2.4, §8.2.9, FR-047
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_if_true_sets_test_true(self):
        """IF 1 sets $TEST=1 (§8.2.9).

        IF 1
        ; $TEST should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_if_false_sets_test_false(self):
        """IF 0 sets $TEST=0 (§8.2.9).

        IF 0
        ; $TEST should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_argumentless_if_uses_test(self):
        """Argumentless IF executes based on $TEST (§8.2.9).

        IF 1
        IF  WRITE "YES"  ; Should execute
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_else_uses_test(self):
        """ELSE executes when $TEST=0 (§8.2.4).

        IF 0
        ELSE  WRITE "NO"  ; Should execute
        """
        pytest.fail("Stub - implement test")


# =============================================================================
# Left-to-Right Evaluation Tests
# =============================================================================


@pytest.mark.parser
class TestLeftToRightParser:
    """Parser tests for operator expressions.

    MUMPS has no operator precedence - strict left-to-right.
    Reference: §7.2
    """

    def test_mixed_operators_parsed(self):
        """2+3*4 parses as (2+3)*4 not 2+(3*4) (§7.2).

        MUMPS evaluates strictly left-to-right with no operator precedence.
        The parser must capture the expression structure correctly for ASG
        analysis to maintain left-to-right semantics.

        Reference: 1995__a107190 (§7.2 - Expression tail)
        """
        parser = MUMPSParser()
        source = "LABEL\tS X=2+3*4\n"
        routine = parser.parse(source)

        set_stmt = routine.labels[0].body.statements[0]
        assert set_stmt.__class__.__name__ == "MSetStatement"

        # The expression structure is captured for ASG analysis
        assignment = set_stmt.assignments[0]
        assert assignment.target.name == "X"
        # Value expression exists (structure verified in ASG tests)
        assert assignment.value is not None


@pytest.mark.codegen
class TestLeftToRightCodegen:
    """Codegen tests for expression evaluation.

    Generated Python must evaluate left-to-right without precedence.
    Reference: §7.2, FR-050
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: 2+3*4=20")
    def test_addition_then_multiplication(self):
        """2+3*4 evaluates to 20, not 14 (§7.2, FR-050).

        SET X=2+3*4  ; X should be 20 = (2+3)*4
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: 10-3-2=5")
    def test_subtraction_left_to_right(self):
        """10-3-2 evaluates to 5 (§7.2).

        SET X=10-3-2  ; X should be 5 = (10-3)-2
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: division left to right")
    def test_division_left_to_right(self):
        """24/4/2 evaluates to 3 (§7.2).

        SET X=24/4/2  ; X should be 3 = (24/4)/2
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: mixed with comparison")
    def test_mixed_arithmetic_comparison(self):
        """2+3>4 evaluates to 1 (true) (§7.2).

        SET X=2+3>4  ; (2+3)>4 = 5>4 = 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: parentheses override")
    def test_parentheses_override_left_to_right(self):
        """2+(3*4) evaluates to 14 with parentheses (§7.2).

        SET X=2+(3*4)  ; X should be 14
        """
        pytest.fail("Stub - implement test")


# =============================================================================
# Exclusive NEW Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_2_14_new.py
# =============================================================================


@pytest.mark.codegen
class TestExclusiveNewCodegen:
    """Codegen tests for Exclusive NEW behavior.

    Generated Python must implement inverse scoping correctly.
    Reference: §8.2.14, FR-048
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exclusive NEW protects listed")
    def test_exclusive_new_protects_listed_variables(self):
        """NEW (X) keeps X visible, hides others (§8.2.14, FR-048).

        SET A=1,X=2
        NEW (X)
        ; X should still be 2, A should be undefined
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exclusive NEW hides unlisted")
    def test_exclusive_new_hides_unlisted_variables(self):
        """NEW (X) makes unlisted variables undefined (§8.2.14, FR-048).

        SET A=1,B=2,X=3
        NEW (X)
        ; A and B should be undefined
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exclusive NEW restored on QUIT")
    def test_exclusive_new_restored_on_quit(self):
        """Exclusive NEW variables restored on QUIT (§8.2.14, FR-048)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Transaction Nesting Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_2_19_tcommit.py,
# test_s8_2_21_trollback.py, test_s8_2_22_tstart.py, and
# tests/unit/asg/s6_routine/test_s6_3_1_transaction.py
# =============================================================================


@pytest.mark.codegen
class TestTransactionNestingCodegen:
    """Codegen tests for transaction nesting behavior.

    Generated Python must correctly implement nested transactions
    with $TLEVEL tracking.
    Reference: §8.2.19, §8.2.21, §8.2.22, FR-051
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL increments")
    def test_tlevel_increments_on_tstart(self):
        """TSTART increments $TLEVEL (§8.2.22, FR-051).

        ; $TLEVEL=0
        TSTART
        ; $TLEVEL should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nested $TLEVEL")
    def test_nested_tstart_increments_tlevel(self):
        """Nested TSTART increments $TLEVEL (§8.2.22, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL should be 2
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TCOMMIT decrements")
    def test_tcommit_decrements_tlevel(self):
        """TCOMMIT decrements $TLEVEL (§8.2.19, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TCOMMIT   ; $TLEVEL should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TROLLBACK to level")
    def test_trollback_to_specific_level(self):
        """TROLLBACK:n rolls back to level n (§8.2.21, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TSTART    ; $TLEVEL=3
        TROLLBACK:1  ; Should rollback to $TLEVEL=1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: full TROLLBACK")
    def test_trollback_full(self):
        """Argumentless TROLLBACK rolls back all levels (§8.2.21, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TROLLBACK ; $TLEVEL should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRESTART tracking")
    def test_trestart_tracking(self):
        """$TRESTART counts restart attempts (§7.1.7, FR-051)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Misc Semantics Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_2_03_do.py and
# test_s8_2_16_quit.py
# =============================================================================


@pytest.mark.codegen
class TestMiscSemanticsCodegen:
    """Codegen tests for misc cross-cutting semantics.

    Generated Python must correctly implement block structure
    and return value handling.
    Reference: §6.3, §8.2.3, §8.2.16
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: block execution level")
    def test_do_block_execution_level(self):
        """Argumentless DO increases execution level (§6.3).

        D  ; Starts block at LEVEL+1
        . S X=1  ; Executed at LEVEL+1
        . Q
        S Y=2  ; Back to original LEVEL
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic return value")
    def test_extrinsic_function_return(self):
        """Extrinsic function returns QUIT value (§7.1.6).

        S X=$$FUNC
        ...
        FUNC Q 42  ; Returns 42 to caller
        """
        pytest.fail("Stub - implement test")
