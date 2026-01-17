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

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: argument postcondition independence"
    )
    def test_argument_postconditions_independent(self):
        """Argument postconditions are evaluated independently (§8.1.4).

        DO L1:0,L2:1  # Only L2 should execute (FR-049)
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Codegen not yet implemented: postcondition eval order")
    def test_postcondition_evaluation_order(self):
        """Command postcondition evaluated before argument postconditions (§8.1.4).

        DO:0 L1:1,L2:1  # Neither should execute (command gates first)
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Codegen not yet implemented: postcondition side effects")
    def test_postcondition_side_effects(self):
        """Postcondition expressions can have side effects (§8.1.4).

        SET X=0 SET:$$INC^RT() Y=1  # X may be modified by postcondition
        """
        pytest.fail("Stub - requires codegen runtime execution")

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
