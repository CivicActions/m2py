"""Cross-cutting tests for postconditions (§8.1.4).

Postconditions are a language feature that spans all commands.
This file tests the cross-cutting behavior of postconditions at
both command-level and argument-level.

Key distinction (FR-049):
- Command-level: SET:C X=1,Y=2 - condition gates entire command
- Argument-level: DO L1:C1,L2:C2 - each argument has independent condition

Per MUMPS 1995 spec §8.1.4 (1995__a108005.md, notes__a108005.md):
- All commands EXCEPT Else, For, and If may have postconditions
- Only Do, Goto, and Xecute support argument-level postconditions
- The postcond includes the colon separator (e.g., ":X=1")

Reference: MUMPS 1995 ANSI Standard, Section 8.1.4
See also: FR-005 (cross-cutting features need dedicated tests)
         FR-049 (command vs argument postconditions)
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import (
    MSetStatement,
    MWriteStatement,
    MDoStatement,
    MXecuteStatement,
    MGotoStatement,
)
from m2py.asg.expressions import MBinaryOp
from m2py.parser.textx_classes import LocalVariable, NumericLiteral


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


# =============================================================================
# Command-Level Postcondition Tests (Parser Level) - D9 Batch
# =============================================================================


@pytest.mark.parser
class TestCommandPostconditionsParser:
    """Parser tests for command-level postconditions.

    Command-level postconditions apply to the entire command.
    Format: COMMAND:CONDITION arguments
    If condition is false, entire command (all arguments) is skipped.

    Per §8.1.4: All commands except Else, For, and If may have postconditions.

    Reference: §8.1.4
    """

    def test_set_with_postcondition(self):
        """SET:COND X=1 parses command-level postcondition (§8.1.4).

        Per notes__a108005.md: All commands except Else, For, If may have postconditions.
        """
        stmt = analyze_first_command("S:X Y=1")

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        # Postcondition is the variable X
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "X"

    def test_write_with_postcondition(self):
        """WRITE:COND X parses command-level postcondition (§8.1.4)."""
        stmt = analyze_first_command("W:OK X")

        assert isinstance(stmt, MWriteStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "OK"


# =============================================================================
# Argument-Level Postcondition Tests (Parser Level) - D10 Batch
# =============================================================================


@pytest.mark.parser
class TestArgumentPostconditionsParser:
    """Parser tests for argument-level postconditions.

    Argument-level postconditions apply to individual arguments.
    Format: COMMAND ARG1:COND1,ARG2:COND2
    Each argument has independent condition evaluation.

    Per §8.1.4: Only Do, Goto, and Xecute support argument postconditions.

    Reference: §8.1.4
    """

    def test_goto_with_argument_postconditions(self):
        """GOTO L1:C1,L2:C2 parses argument-level postconditions (§8.1.4).

        Computed GOTO pattern - first true postcondition wins.
        """
        stmt = analyze_first_command("G L1:X=1,L2:X=2,L3")

        assert isinstance(stmt, MGotoStatement)
        assert stmt.postcondition is None  # No command postcondition
        assert len(stmt.targets) == 3

        # First two have postconditions
        assert stmt.targets[0].postcondition is not None
        assert stmt.targets[1].postcondition is not None
        # Third has no postcondition (default/fallback)
        assert stmt.targets[2].postcondition is None

    def test_xecute_with_argument_postconditions(self):
        """XECUTE CODE1:C1,CODE2:C2 parses argument postconditions (§8.1.4).

        XECUTE can have multiple code strings with postconditions.
        """
        stmt = analyze_first_command('X "S A=1":X,"S B=2":Y')

        assert isinstance(stmt, MXecuteStatement)
        assert stmt.postcondition is None  # No command postcondition
        # XECUTE has code_expressions with postconditions
        assert len(stmt.code_expressions) == 2

    def test_do_with_expression_postcondition(self):
        """DO LABEL:X>0 parses expression postcondition (§8.1.4).

        Argument postconditions can be complex expressions.
        """
        stmt = analyze_first_command("D PROC:N>0")

        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]

        assert target.postcondition is not None
        assert isinstance(target.postcondition, MBinaryOp)
        assert target.postcondition.operator == ">"


# =============================================================================
# Mixed Postcondition Tests (Parser Level) - D10 Batch (continued)
# =============================================================================


@pytest.mark.parser
class TestMixedPostconditionsParser:
    """Parser tests for combined command and argument postconditions.

    Commands can have both command-level and argument-level postconditions.
    Command-level is evaluated first; if false, no arguments execute.

    Reference: §8.1.4
    """

    pass


# =============================================================================
# Postcondition Tests (ASG Level) - D11 Batch
#
# The tests below cover additional edge cases not in spec-aligned files.
# =============================================================================


@pytest.mark.asg
class TestPostconditionsASG:
    """ASG tests for postcondition semantic analysis.

    ASG analysis must distinguish command-level vs argument-level
    postconditions and track their conditions.

    This class contains additional edge cases and expression analysis tests.

    Reference: §8.1.4
    """

    def test_postcondition_expression_analyzed(self):
        """Postcondition expression is fully analyzed (§8.1.4).

        Complex expressions in postconditions should have full ASG structure.
        MUMPS uses strict left-to-right evaluation (no operator precedence),
        so X>0&Y<10 parses as ((X>0)&Y)<10.
        """
        stmt = analyze_first_command("W:X>0&Y<10 DATA")

        assert isinstance(stmt, MWriteStatement)
        pc = stmt.postcondition
        assert pc is not None

        # Due to left-to-right evaluation: ((X>0)&Y)<10
        # Top level: < operator
        assert isinstance(pc, MBinaryOp)
        assert pc.operator == "<"
        # Right side: 10
        assert isinstance(pc.right, NumericLiteral)
        assert pc.right.value == 10
        # Left side: (X>0)&Y
        assert isinstance(pc.left, MBinaryOp)
        assert pc.left.operator == "&"

    def test_postcondition_with_function_call(self):
        """Postcondition with intrinsic function in comparison (§8.1.4).

        $LENGTH in a comparison expression - tests nested function calls.
        This is different from test_postcondition_with_intrinsic_function which
        tests a bare function call as postcondition.
        """
        from m2py.asg.expressions import MIntrinsicFunction

        stmt = analyze_first_command("S:$L(X)>0 Y=X")

        assert isinstance(stmt, MSetStatement)
        pc = stmt.postcondition
        assert pc is not None

        # Should be MBinaryOp: $L(X) > 0
        assert isinstance(pc, MBinaryOp)
        assert pc.operator == ">"
        # Left side is the function call
        assert isinstance(pc.left, MIntrinsicFunction)
        assert pc.left.name.upper() in ("L", "LENGTH")


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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Codegen not yet implemented: postcondition runtime gate")
    def test_command_postcondition_gates_all_arguments(self):
        """False command postcondition skips all arguments (§8.1.4).

        SET:0 X=1,Y=2  # Neither X nor Y should be set
        """
        pytest.fail("Stub - requires codegen runtime execution")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Codegen not yet implemented: postcondition truthiness")
    def test_postcondition_truthiness(self):
        """Postcondition truthiness follows MUMPS rules (§8.1.4).

        Non-zero/non-empty = true, zero/empty = false
        """
        pytest.fail("Stub - requires codegen runtime execution")
