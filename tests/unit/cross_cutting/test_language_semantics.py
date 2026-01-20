"""Cross-cutting tests for MUMPS language semantics.

This file tests fundamental language behaviors that span multiple
commands and expressions:
- $TEST special variable modification (FR-047)
- Left-to-right evaluation without precedence (FR-050)
- Exclusive NEW scoping behavior (FR-048)

Reference: MUMPS 1995 ANSI Standard, various sections
See also: FR-046-051 (language semantic requirements)

Note: Transaction nesting tests are in s6_routine/test_s6_3_1_transaction.py
"""

import pytest


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

    def test_if_true_sets_test_true(self, execute_mumps):
        """IF 1 sets $TEST=1 (§8.2.9).

        IF 1
        ; $TEST should be 1
        """
        result = execute_mumps("TEST I 1 W $T Q")
        assert result.output == "1"

    def test_if_false_sets_test_false(self, execute_mumps):
        """IF 0 sets $TEST=0 (§8.2.9).

        IF 0
        ; $TEST should be 0
        """
        source = """TEST
 I 0
 W $T Q"""
        result = execute_mumps(source)
        assert result.output == "0"

    def test_argumentless_if_uses_test(self, execute_mumps):
        """Argumentless IF executes based on $TEST (§8.2.9).

        IF 1
        IF  WRITE "YES"  ; Should execute
        """
        source = """TEST
 I 1
 I  W "YES" Q
 Q"""
        result = execute_mumps(source)
        assert result.output == "YES"

    def test_else_uses_test(self, execute_mumps):
        """ELSE executes when $TEST=0 (§8.2.4).

        IF 0
        ELSE  WRITE "NO"  ; Should execute
        """
        source = """TEST
 I 0
 E  W "NO" Q
 Q"""
        result = execute_mumps(source)
        assert result.output == "NO"


@pytest.mark.codegen
class TestTestStackSemanticsCodegen:
    """Codegen tests for $TEST stacking behavior.

    $TEST Stacking Rules (verified against YottaDB):
    - Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack $TEST
    - DO blocks (D followed by dot lines) DO stack $TEST
    - Extrinsic calls ($$func) DO stack $TEST
    - XECUTE does NOT stack $TEST

    Note: "Argumentless DO" can be ambiguous - it means DO blocks (with dots),
    NOT label calls without arguments.

    Reference: §7.1.4.10, §8.2.3, verified against YottaDB
    """

    def test_test_stacked_for_do_block(self, execute_mumps):
        """DO blocks stack $TEST, restored on block exit.

        T080: DO blocks preserve caller's $TEST value.

        IF 1           ; $TEST=1
        D              ; Starts DO block - stacks $TEST
        . IF 0         ; $TEST=0 inside block
        W $T           ; Should output 1 - $TEST restored after DO block
        """
        source = """TEST I 1 D  W $T Q
 . I 0"""
        result = execute_mumps(source)
        # After DO block, $TEST should be restored to 1 (from IF 1)
        assert result.output == "1"
        assert result.success is True

    def test_test_stacked_for_extrinsic(self, execute_mumps):
        """Extrinsic calls stack $TEST, restored on QUIT.

        T067: Extrinsic function $TEST changes don't leak to caller.
        Validated against YottaDB: output is '111' (1 before, 1 return, 1 after).

        IF 1           ; $TEST=1
        W $T,$$FUNC,$T ; Stacks $TEST for extrinsic call
        ; FUNC sets $TEST=0 internally but caller's $TEST is restored
        """
        # Multi-line routine: FUNC contains IF 0 to set $TEST=0 internally
        source = """TEST I 1 W $T,$$FUNC(),$T Q
FUNC()
 I 0
 Q 1"""
        result = execute_mumps(source)

        # Output should be "111":
        # - First $T is 1 (from IF 1)
        # - $$FUNC() returns 1
        # - Second $T is 1 (restored, even though FUNC did IF 0)
        assert result.output == "111"

    def test_test_not_stacked_for_label_call(self, execute_mumps):
        """Label calls do NOT stack $TEST - callee changes visible.

        IF 1           ; $TEST=1
        D SUB          ; Does NOT stack $TEST
        ; SUB sets $TEST=0, it IS visible to caller
        W $T           ; Should output 0 (callee's IF 0 affected caller)

        Verified against YottaDB.
        """
        source = """TEST
 I 1 D SUB W $T Q
SUB
 I 0 Q"""
        result = execute_mumps(source)
        # After D SUB where SUB does IF 0, caller's $TEST should be 0
        assert result.output == "0"
        assert result.success is True

    def test_test_not_stacked_for_do_with_args(self, execute_mumps):
        """DO with arguments does NOT stack $TEST (same as D SUB).

        IF 1           ; $TEST=1
        D SUB(1)       ; Does NOT stack $TEST (same behavior as D SUB)
        ; If SUB sets $TEST=0, it affects caller
        W $T           ; Should output 0 (callee's IF 0 affected caller)

        Verified against YottaDB.
        """
        source = """TEST
 I 1 D SUB(1) W $T Q
SUB(X)
 I 0 Q"""
        result = execute_mumps(source)
        # After D SUB(1) where SUB does IF 0, caller's $TEST should be 0
        assert result.output == "0"
        assert result.success is True

    def test_test_not_stacked_for_xecute(self, execute_mumps):
        """XECUTE does NOT stack $TEST.

        IF 1                ; $TEST=1
        X "IF 0"            ; $TEST=0, visible to caller
        W $T                ; Should output 0

        Verified against YottaDB.
        """
        source = 'TEST I 1 X "I 0" W $T Q'
        result = execute_mumps(source)
        # After XECUTE "IF 0", $TEST should be 0
        assert result.output == "0"
        assert result.success is True

    def test_postcondition_does_not_update_test(self, execute_mumps):
        """Postconditions do NOT update $TEST.

        T068: Postconditions evaluate their condition but don't set $TEST.
        Validated against YottaDB: output is '1' ($TEST still 1).

        IF 1           ; $TEST=1
        S:0 X=1        ; Postcondition is false, but $TEST stays 1
        W $T           ; Should output 1
        """
        source = "TEST I 1 S:0 X=1 W $T Q"
        result = execute_mumps(source)

        # $TEST should still be 1 (postcondition didn't change it)
        assert result.output == "1"


# =============================================================================
# Left-to-Right Evaluation Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s7_expressions/test_s7_2_operators.py
# =============================================================================


@pytest.mark.codegen
class TestLeftToRightCodegen:
    """Codegen tests for expression evaluation.

    Generated Python must evaluate left-to-right without precedence.
    Reference: §7.2, FR-050
    """

    def test_addition_then_multiplication(self, execute_mumps):
        """2+3*4 evaluates to 20, not 14 (§7.2, FR-050).

        SET X=2+3*4  ; X should be 20 = (2+3)*4
        """
        result = execute_mumps("TEST W 2+3*4 Q")
        assert result.output == "20"

    def test_subtraction_left_to_right(self, execute_mumps):
        """10-3-2 evaluates to 5 (§7.2).

        SET X=10-3-2  ; X should be 5 = (10-3)-2
        """
        result = execute_mumps("TEST W 10-3-2 Q")
        assert result.output == "5"

    def test_division_left_to_right(self, execute_mumps):
        """24/4/2 evaluates to 3 (§7.2).

        SET X=24/4/2  ; X should be 3 = (24/4)/2
        """
        result = execute_mumps("TEST W 24/4/2 Q")
        assert result.output == "3"

    def test_mixed_arithmetic_comparison(self, execute_mumps):
        """2+3>4 evaluates to 1 (true) (§7.2).

        SET X=2+3>4  ; (2+3)>4 = 5>4 = 1
        """
        result = execute_mumps("TEST W 2+3>4 Q")
        assert result.output == "1"

    def test_parentheses_override_left_to_right(self, execute_mumps):
        """2+(3*4) evaluates to 14 with parentheses (§7.2).

        SET X=2+(3*4)  ; X should be 14
        """
        result = execute_mumps("TEST W 2+(3*4) Q")
        assert result.output == "14"


# =============================================================================
# Exclusive NEW Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_2_14_new.py
# =============================================================================


@pytest.mark.codegen
class TestExclusiveNewCodegen:
    """Codegen tests for Exclusive NEW behavior.

    Generated Python must implement inverse scoping correctly.
    Reference: §8.2.14, FR-048

    Exclusive NEW (N (X)) preserves only listed variables and
    creates new empty scope for all others.
    """

    def test_exclusive_new_protects_listed_variables(self, execute_mumps):
        """NEW (X) keeps X visible, hides others (§8.2.14, FR-048).

        SET A=1,X=2
        NEW (X)
        ; X should still be 2 ($D=1), A should be undefined ($D=0)
        """
        result = execute_mumps('TEST\n S A=1,X=2\n N (X)\n W $D(X)," ",$D(A)\n Q')
        assert result.output == "1 0"

    def test_exclusive_new_preserves_value(self, execute_mumps):
        """NEW (X) preserves the actual value of X (§8.2.14, FR-048).

        SET X=42
        NEW (X)
        ; X should still equal 42
        """
        result = execute_mumps("TEST\n S X=42\n N (X)\n W X\n Q")
        assert result.output == "42"

    def test_exclusive_new_hides_unlisted_variables(self, execute_mumps):
        """NEW (X) makes unlisted variables undefined (§8.2.14, FR-048).

        SET A=1,B=2,X=3
        NEW (X)
        ; A and B should be undefined ($D=0)
        """
        result = execute_mumps("TEST\n S A=1,B=2,X=3\n N (X)\n W $D(A),$D(B)\n Q")
        assert result.output == "00"

    def test_exclusive_new_multiple_preserved(self, execute_mumps):
        """NEW (X,Y) preserves multiple variables (§8.2.14, FR-048).

        SET A=1,X=2,Y=3
        NEW (X,Y)
        ; X and Y preserved, A hidden
        """
        result = execute_mumps(
            "TEST\n S A=1,X=2,Y=3\n N (X,Y)\n W $D(X),$D(Y),$D(A)\n Q"
        )
        assert result.output == "110"

    def test_exclusive_new_with_quit_restores(self, execute_mumps):
        """Exclusive NEW variables restored on QUIT (§8.2.14, FR-048).

        A outer value should be restored after SUB returns.
        SUB does N (Z) which creates new scope for A (and all except Z).
        After SUB returns, A should be restored to its outer value.
        """
        result = execute_mumps(
            "TEST\n S A=1,Z=0\n D SUB\n W A\n Q\nSUB\n N (Z)\n S A=99\n Q"
        )
        # After SUB returns, A should be restored to 1
        assert result.output == "1"


# =============================================================================
# Argumentless NEW Tests - Codegen Only
# Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_2_14_new.py
# =============================================================================


@pytest.mark.codegen
class TestArgumentlessNewCodegen:
    """Codegen tests for Argumentless NEW behavior.

    Generated Python must implement new scope for all local variables.
    Reference: §8.2.14, FR-048

    Argumentless NEW (N with no args) creates a new empty scope for
    ALL local variables. After the NEW, all locals are undefined.
    On subroutine exit, all original values are restored.

    Note: N () (empty exclusive NEW) is invalid MUMPS syntax.
    YDB rejects it with %YDB-E-VAREXPECTED.
    """

    def test_argumentless_new_hides_all_variables(self, execute_mumps):
        """Argumentless NEW hides all local variables (§8.2.14).

        SET X=1,Y=2
        NEW
        ; Both X and Y should be undefined ($D=0)
        """
        result = execute_mumps("TEST\n S X=1,Y=2\n N  W $D(X),$D(Y)\n Q")
        assert result.output == "00"

    def test_argumentless_new_with_two_spaces(self, execute_mumps):
        """Argumentless NEW with two spaces followed by command (§8.2.14).

        S X=1
        N  W $D(X)  ; Two spaces between N and W
        ; X should be undefined after N
        """
        result = execute_mumps("TEST\n S X=1\n N  W $D(X)\n Q")
        assert result.output == "0"

    def test_argumentless_new_in_subroutine_restores(self, execute_mumps):
        """Argumentless NEW variables restored on subroutine QUIT (§8.2.14).

        SET X=1
        DO SUB
        ; After SUB returns, X should be restored to 1

        SUB
         NEW  ; Argumentless NEW - hides all variables
         SET X=99  ; This is a new local X, shadows outer
         QUIT
        """
        result = execute_mumps("TEST\n S X=1\n D SUB\n W X\n Q\nSUB\n N\n S X=99\n Q")
        # After SUB returns, X should be restored to 1
        assert result.output == "1"

    def test_argumentless_new_multiple_variables(self, execute_mumps):
        """Argumentless NEW hides multiple variables (§8.2.14).

        SET A=1,B=2,C=3
        NEW
        ; All should be undefined
        """
        result = execute_mumps("TEST\n S A=1,B=2,C=3\n N  W $D(A),$D(B),$D(C)\n Q")
        assert result.output == "000"


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

    def test_do_block_execution_level(self, execute_mumps):
        """Argumentless DO increases execution level (§6.3).

        D  ; Starts block at LEVEL+1
        . S X=1  ; Executed at LEVEL+1
        . Q
        S Y=2  ; Back to original LEVEL

        $STACK returns the execution level which increases inside DO blocks.
        Verified against YottaDB.
        """
        source = """TEST
 W "L0=",$STACK,!
 D
 . W "L1=",$STACK,!
 . D
 . . W "L2=",$STACK,!
 . W "L1 again=",$STACK,!
 W "L0 again=",$STACK,!"""
        result = execute_mumps(source)
        assert result.output == "L0=0\nL1=1\nL2=2\nL1 again=1\nL0 again=0\n"
        assert result.success is True

    def test_extrinsic_function_return(self, execute_mumps):
        """Extrinsic function returns QUIT value (§7.1.6).

        S X=$$FUNC()
        ; X should be 42
        FUNC() Q 42  ; Returns 42 to caller

        Verified against YottaDB.
        """
        source = """TEST
 S X=$$FUNC()
 W X Q
FUNC()
 Q 42"""
        result = execute_mumps(source)
        assert result.output == "42"
        assert result.success is True
