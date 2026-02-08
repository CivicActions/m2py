"""Cross-cutting tests for postconditions RUNTIME behavior (§8.1.4).

Postconditions are a language feature that spans all commands.
This file tests the cross-cutting RUNTIME behavior of postconditions.

Key distinction (FR-049):
- Command-level: SET:C X=1,Y=2 - condition gates entire command
- Argument-level: DO L1:C1,L2:C2 - each argument has independent condition

Per MUMPS 1995 spec §8.1.4 (1995__a108005.md, notes__a108005.md):
- All commands EXCEPT Else, For, and If may have postconditions
- Only Do, Goto, and Xecute support argument-level postconditions
- The postcond includes the colon separator (e.g., ":X=1")

Parser/ASG tests are in tests/unit/asg/s8_commands/test_s8_1_general_rules.py

Reference: MUMPS 1995 ANSI Standard, Section 8.1.4
See also: FR-005 (cross-cutting features need dedicated tests)
         FR-049 (command vs argument postconditions)
"""

import pytest


# =============================================================================
# Postcondition Tests (Codegen Level) - Runtime execution behavior
# =============================================================================


@pytest.mark.codegen
class TestPostconditionsCodegen:
    """Codegen tests for postcondition execution.

    Generated Python must correctly implement postcondition
    semantics: command-level gates all arguments, argument-level
    is independent per argument.

    Reference: §8.1.4
    """

    def test_command_postcondition_gates_all_arguments(self, execute_mumps):
        """False command postcondition skips all arguments (§8.1.4).

        Spec 011 Phase 8: SET:0 X=1,Y=2 - Neither X nor Y should be set.
        """
        source = 'TEST S:0 X=1,Y=2 W $G(X,"x"),$G(Y,"y"),! Q'
        result = execute_mumps(source)
        assert result.output == "xy\n"

    def test_command_postcondition_true_executes(self, execute_mumps):
        """True command postcondition executes all arguments (§8.1.4).

        Spec 011 Phase 8: SET:1 X=1,Y=2 - Both X and Y should be set.
        """
        source = "TEST S:1 X=1,Y=2 W X,Y,! Q"
        result = execute_mumps(source)
        assert result.output == "12\n"

    def test_argument_postconditions_independent(self, execute_mumps):
        """Argument postconditions are evaluated independently (§8.1.4).

        DO L1:0,L2:1  # Only L2 should execute (FR-049)

        Each argument's postcondition is evaluated independently:
        - L1:0 - false postcondition, L1 not called
        - L2:1 - true postcondition, L2 called

        Spec 014 (T076): Argument postconditions independent.
        """
        source = """TEST S X=0 D L1:0,L2:1 W X,! Q
L1 S X=X+10 Q
L2 S X=X+1 Q"""
        result = execute_mumps(source)
        assert result.output == "1\n"  # Only L2 executed, X=0+1=1

    def test_postcondition_evaluation_order(self, execute_mumps):
        """Command postcondition evaluated before argument postconditions (§8.1.4).

        DO:0 L1:1,L2:1  # Neither should execute (command gates first)

        When command postcondition is false, the entire command is skipped
        and argument postconditions are never evaluated.

        Spec 014 (T077): Command postcondition gates first.
        """
        source = """TEST S X=0 D:0 L1:1,L2:1 W X,! Q
L1 S X=X+10 Q
L2 S X=X+1 Q"""
        result = execute_mumps(source)
        assert result.output == "0\n"  # Neither executed, X=0

    def test_postcondition_side_effects(self, execute_mumps):
        """Postcondition expressions can have side effects (§8.1.4).

        Postcondition expressions (both command and argument level) are
        evaluated and their side effects are visible even if the condition
        is false.

        Spec 014 (T078): Postcondition side effects visible.
        """
        # Command postcondition with side effect: $$SETX sets X=1 and returns 1
        source = """TEST S X=0,Y=0 D:$$SETX L1:$$SETY W X,Y,! Q
SETX() S X=1 Q 1
SETY() S Y=1 Q 1
L1 Q"""
        result = execute_mumps(source)
        # Both SETX and SETY are called (postconditions evaluated), both return 1 (true)
        # L1 is also called (both postconditions true)
        assert result.output == "11\n"  # X=1 from SETX, Y=1 from SETY

        # Command postcondition false - argument postcondition NOT evaluated
        source = """TEST S X=0,Y=0 D:0 L1:$$SETY W X,Y,! Q
SETY() S Y=1 Q 1
L1 Q"""
        result = execute_mumps(source)
        # SETY is NOT called because command postcondition (0) is false
        assert (
            result.output == "00\n"
        )  # X=0, Y=0 (neither postcondition function called)

    def test_postcondition_truthiness(self, execute_mumps):
        """Postcondition truthiness follows MUMPS rules (§8.1.4).

        Spec 011 Phase 8: Non-zero/non-empty = true, zero/empty = false.
        """
        # Empty string is false
        source = 'TEST S C="" S:C X=1 W $G(X,"none"),! Q'
        result = execute_mumps(source)
        assert result.output == "none\n"

        # Non-zero string is true
        source = 'TEST S C="1" S:C X=1 W $G(X,"none"),! Q'
        result = execute_mumps(source)
        assert result.output == "1\n"

    def test_xecute_argument_postconditions(self, execute_mumps):
        """XECUTE argument postconditions are evaluated independently (T075q).

        X "code1","code2":0,"code3"  # Only code1 and code3 should execute

        Per MUMPS spec 8.1.4, XECUTE supports argument-level postconditions.
        Each argument's postcondition is evaluated independently.
        """
        source = 'TEST S X=0 X "S X=X+1","S X=X+10":0,"S X=X+100" W X,! Q'
        result = execute_mumps(source)
        # code1 runs (+1), code2 skipped (postcond=0), code3 runs (+100)
        assert result.output == "101\n"  # X=0+1+100=101

    def test_xecute_argument_postconditions_all_true(self, execute_mumps):
        """XECUTE argument postconditions all true execute all (T075q).

        X "code1":1,"code2":1  # Both should execute
        """
        source = 'TEST S X=0 X "S X=X+1":1,"S X=X+10":1 W X,! Q'
        result = execute_mumps(source)
        assert result.output == "11\n"  # X=0+1+10=11

    def test_xecute_mixed_command_and_argument_postconditions(self, execute_mumps):
        """XECUTE with both command and argument postconditions (T075r).

        X:1 "code1":0,"code2":1  # Command true, code1 skipped, code2 runs

        Command postcondition must be true for any execution to occur.
        Then each argument's postcondition controls that argument.
        """
        source = 'TEST S X=0 X:1 "S X=X+1":0,"S X=X+10":1 W X,! Q'
        result = execute_mumps(source)
        # Command postcond=1 (true), so proceed
        # code1 postcond=0 (false), skip
        # code2 postcond=1 (true), run (+10)
        assert result.output == "10\n"  # X=0+10=10

    def test_xecute_command_postcondition_false_skips_all(self, execute_mumps):
        """XECUTE command postcondition false skips all arguments (T075r).

        X:0 "code1":1,"code2":1  # Command false, nothing executes

        When command postcondition is false, entire command is skipped.
        """
        source = 'TEST S X=0 X:0 "S X=X+1":1,"S X=X+10":1 W X,! Q'
        result = execute_mumps(source)
        # Command postcond=0, nothing runs
        assert result.output == "0\n"  # X stays 0
