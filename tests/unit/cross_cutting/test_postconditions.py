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
    MKillStatement,
    MQuitStatement,
    MXecuteStatement,
    MGotoStatement,
)
from m2py.asg.expressions import MBinaryOp, MUnaryOp
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

    def test_do_with_postcondition(self):
        """DO:COND LABEL parses command-level postcondition (§8.1.4)."""
        stmt = analyze_first_command("D:READY PROC")

        assert isinstance(stmt, MDoStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "READY"

    def test_kill_with_postcondition(self):
        """KILL:COND VAR parses command-level postcondition (§8.1.4)."""
        stmt = analyze_first_command("K:CLEANUP X")

        assert isinstance(stmt, MKillStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "CLEANUP"

    def test_complex_postcondition_expression(self):
        """SET:(X>0)&(Y<10) Z=1 parses complex postcondition (§8.1.4).

        Postcondition can be any truthvalue expression (tvexpr).
        Complex boolean expressions with & (AND) are allowed.
        """
        stmt = analyze_first_command("S:(X>0)&(Y<10) Z=1")

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        # Complex expression should be MBinaryOp with & operator
        assert isinstance(stmt.postcondition, MBinaryOp)
        assert stmt.postcondition.operator == "&"

    def test_postcondition_with_function(self):
        """SET:$D(X) Y=X parses postcondition with intrinsic function (§8.1.4).

        $DATA returns 0 if variable doesn't exist, non-zero otherwise.
        This is a common pattern to check if variable is defined.
        """
        from m2py.asg.expressions import MIntrinsicFunction

        stmt = analyze_first_command("S:$D(X) Y=X")

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, MIntrinsicFunction)
        assert stmt.postcondition.name.upper() in ("D", "DATA")

    def test_quit_with_postcondition(self):
        """QUIT:COND parses command-level postcondition (§8.1.4).

        QUIT can have postcondition, allowing conditional return.
        """
        stmt = analyze_first_command("Q:DONE")

        assert isinstance(stmt, MQuitStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "DONE"


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

    def test_do_with_argument_postconditions(self):
        """DO L1:C1,L2:C2 parses argument-level postconditions (§8.1.4).

        Per 1995__a108005.md: "The postcond may also be used to conditionalize
        the arguments of Do, Goto, and Xecute."
        """
        stmt = analyze_first_command("D L1:X,L2:Y")

        assert isinstance(stmt, MDoStatement)
        assert stmt.postcondition is None  # No command-level postcondition
        assert len(stmt.targets) == 2

        # Each target (MCall) has its own postcondition
        assert stmt.targets[0].postcondition is not None
        assert isinstance(stmt.targets[0].postcondition, LocalVariable)
        assert stmt.targets[0].postcondition.name == "X"

        assert stmt.targets[1].postcondition is not None
        assert isinstance(stmt.targets[1].postcondition, LocalVariable)
        assert stmt.targets[1].postcondition.name == "Y"

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

    def test_goto_mixed_postconditions(self):
        """GOTO L1,L2:C,L3 parses some args with postconditions (§8.1.4).

        Not all arguments need postconditions.
        """
        stmt = analyze_first_command("G L1,L2:COND,L3")

        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 3

        # Only middle argument has postcondition
        assert stmt.targets[0].postcondition is None
        assert stmt.targets[1].postcondition is not None
        assert stmt.targets[2].postcondition is None

    def test_do_with_routine_and_postcondition(self):
        """DO LABEL^ROUTINE:C parses routine reference with postcondition (§8.1.4).

        Postcondition can follow full label^routine reference.
        """
        stmt = analyze_first_command("D PROC^UTIL:OK")

        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        assert target.name == "PROC"
        assert target.routine == "UTIL"
        assert target.postcondition is not None
        assert isinstance(target.postcondition, LocalVariable)
        assert target.postcondition.name == "OK"

    def test_do_with_params_and_postcondition(self):
        """DO LABEL(X,Y):C parses parameters with postcondition (§8.1.4).

        Postcondition follows the parameter list.
        """
        stmt = analyze_first_command("D PROC(A,B):READY")

        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        assert target.name == "PROC"
        assert len(target.arguments) == 2
        assert target.postcondition is not None
        assert target.postcondition.name == "READY"


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

    def test_command_and_argument_postconditions(self):
        """DO:CMD L1:ARG1,L2:ARG2 parses both levels (§8.1.4).

        Command postcondition gates all; argument postconditions are independent.
        """
        stmt = analyze_first_command("D:OK PROC1:X,PROC2:Y")

        assert isinstance(stmt, MDoStatement)
        # Command-level postcondition
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "OK"

        # Argument-level postconditions
        assert len(stmt.targets) == 2
        assert stmt.targets[0].postcondition is not None
        assert stmt.targets[0].postcondition.name == "X"
        assert stmt.targets[1].postcondition is not None
        assert stmt.targets[1].postcondition.name == "Y"

    def test_goto_command_and_argument_postconditions(self):
        """GOTO:CMD L1:A,L2:B parses both levels (§8.1.4)."""
        stmt = analyze_first_command("G:PROCEED L1:X=1,L2:X=2")

        assert isinstance(stmt, MGotoStatement)
        # Command postcondition
        assert stmt.postcondition is not None
        assert stmt.postcondition.name == "PROCEED"

        # Argument postconditions
        assert len(stmt.targets) == 2
        assert stmt.targets[0].postcondition is not None
        assert stmt.targets[1].postcondition is not None


# =============================================================================
# Postcondition Tests (ASG Level) - D11 Batch
# =============================================================================


@pytest.mark.asg
class TestPostconditionsASG:
    """ASG tests for postcondition semantic analysis.

    ASG analysis must distinguish command-level vs argument-level
    postconditions and track their conditions.

    Reference: §8.1.4
    """

    def test_command_postcondition_in_asg(self):
        """Command postcondition is stored in ASG node (§8.1.4).

        The postcondition expression should be fully analyzed.
        """
        stmt = analyze_first_command("S:X=1 Y=2")

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        # Postcondition is analyzed as MBinaryOp
        assert isinstance(stmt.postcondition, MBinaryOp)
        assert stmt.postcondition.operator == "="
        assert isinstance(stmt.postcondition.left, LocalVariable)
        assert stmt.postcondition.left.name == "X"

    def test_argument_postcondition_in_asg(self):
        """Argument postconditions are stored per-argument (§8.1.4).

        Each MCall in DO targets has its own postcondition.
        """
        stmt = analyze_first_command("D L1:A=1,L2:B=2")

        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 2

        # First target postcondition
        pc1 = stmt.targets[0].postcondition
        assert pc1 is not None
        assert isinstance(pc1, MBinaryOp)
        assert pc1.left.name == "A"

        # Second target postcondition
        pc2 = stmt.targets[1].postcondition
        assert pc2 is not None
        assert isinstance(pc2, MBinaryOp)
        assert pc2.left.name == "B"

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

    def test_combined_postcondition_structure(self):
        """Combined postconditions have correct ASG structure (§8.1.4).

        Both command and argument postconditions are captured.
        """
        stmt = analyze_first_command("D:READY PROC1:A,PROC2:B")

        assert isinstance(stmt, MDoStatement)

        # Command postcondition
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, LocalVariable)
        assert stmt.postcondition.name == "READY"

        # Argument postconditions on MCall objects
        assert len(stmt.targets) == 2
        assert stmt.targets[0].name == "PROC1"
        assert stmt.targets[0].postcondition.name == "A"
        assert stmt.targets[1].name == "PROC2"
        assert stmt.targets[1].postcondition.name == "B"

    def test_postcondition_with_negation(self):
        """Postcondition with NOT operator is analyzed (§8.1.4).

        Negated conditions use unary NOT (').
        """
        stmt = analyze_first_command("Q:'DONE")

        assert isinstance(stmt, MQuitStatement)
        pc = stmt.postcondition
        assert pc is not None

        # Should be MUnaryOp with NOT operator
        assert isinstance(pc, MUnaryOp)
        assert pc.operator == "'"

    def test_postcondition_with_function_call(self):
        """Postcondition with intrinsic function is analyzed (§8.1.4).

        $DATA, $LENGTH, etc. can appear in postconditions.
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

    def test_postcondition_numeric_literal(self):
        """Postcondition with numeric literal works (§8.1.4).

        SET:1 X=1 always executes (1 is truthy).
        SET:0 X=1 never executes (0 is falsy).
        """
        # Truthy postcondition
        stmt1 = analyze_first_command("S:1 X=1")
        assert isinstance(stmt1, MSetStatement)
        assert stmt1.postcondition is not None
        assert isinstance(stmt1.postcondition, NumericLiteral)
        assert stmt1.postcondition.value == 1

        # Falsy postcondition
        stmt2 = analyze_first_command("S:0 X=1")
        assert isinstance(stmt2, MSetStatement)
        assert stmt2.postcondition is not None
        assert isinstance(stmt2.postcondition, NumericLiteral)
        assert stmt2.postcondition.value == 0


# =============================================================================
# Postcondition Tests (Codegen Level) - ASG structure for runtime semantics
# =============================================================================


@pytest.mark.codegen
class TestPostconditionsCodegen:
    """Codegen tests for postcondition execution.

    These tests verify ASG captures correct structure for codegen to
    implement postcondition semantics: command-level gates all arguments,
    argument-level is independent per argument.

    Reference: §8.1.4
    """

    def test_command_postcondition_gates_all_arguments(self):
        """Command postcondition ASG captures gating pattern (§8.1.4).

        SET:0 X=1,Y=2 - ASG must have postcondition=0 and both assignments
        so codegen can implement gating (neither X nor Y set when 0 is false).
        """
        stmt = analyze_first_command("S:0 X=1,Y=2")

        assert isinstance(stmt, MSetStatement)
        # Command-level postcondition is captured
        assert stmt.postcondition is not None
        assert stmt.postcondition.value == 0  # The gating condition
        # All assignments are captured (codegen will gate them)
        assert len(stmt.assignments) == 2
        assert stmt.assignments[0].target.name == "X"
        assert stmt.assignments[1].target.name == "Y"

    def test_argument_postconditions_independent(self):
        """Argument postconditions ASG captures independence (§8.1.4).

        DO L1:0,L2:1 - ASG must have per-argument postconditions
        so codegen can execute each independently (FR-049).
        """
        stmt = analyze_first_command("D L1:0,L2:1")

        assert isinstance(stmt, MDoStatement)
        assert stmt.postcondition is None  # No command-level
        assert len(stmt.targets) == 2

        # Each target has independent postcondition
        assert stmt.targets[0].postcondition is not None
        assert stmt.targets[0].postcondition.value == 0  # L1 won't execute
        assert stmt.targets[1].postcondition is not None
        assert stmt.targets[1].postcondition.value == 1  # L2 will execute

    def test_postcondition_evaluation_order(self):
        """Command postcondition ASG captures hierarchy (§8.1.4).

        DO:0 L1:1,L2:1 - ASG must have command postcondition=0
        plus argument postconditions, enabling codegen to gate command first.
        """
        stmt = analyze_first_command("D:0 L1:1,L2:1")

        assert isinstance(stmt, MDoStatement)
        # Command-level postcondition
        assert stmt.postcondition is not None
        assert stmt.postcondition.value == 0  # Gates entire command
        # Argument postconditions also captured
        assert len(stmt.targets) == 2
        assert stmt.targets[0].postcondition.value == 1
        assert stmt.targets[1].postcondition.value == 1

    def test_postcondition_side_effects(self):
        """Extrinsic function postcondition ASG captures call (§8.1.4).

        SET:$$INC^RT() Y=1 - postcondition is extrinsic function call
        that may have side effects. ASG must capture for codegen.
        """
        from m2py.parser.textx_classes import ExtrinsicFunction

        stmt = analyze_first_command("S:$$INC^RT() Y=1")

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        # Postcondition is an extrinsic function call
        assert isinstance(stmt.postcondition, ExtrinsicFunction)
        # ExtrinsicFunction wraps an MCall target with name and routine
        assert stmt.postcondition.target.name == "INC"
        assert stmt.postcondition.target.routine == "RT"

    def test_postcondition_truthiness(self):
        """Postcondition ASG captures truthiness values (§8.1.4).

        ASG captures literal values for codegen to apply MUMPS truthiness:
        non-zero/non-empty = true, zero/empty = false.
        """
        # Truthy: non-zero
        stmt1 = analyze_first_command("S:1 X=1")
        assert stmt1.postcondition.value == 1

        # Falsy: zero
        stmt2 = analyze_first_command("S:0 X=1")
        assert stmt2.postcondition.value == 0

        # Truthy: non-empty string (parses as postcondition expression)
        stmt3 = analyze_first_command('W:"YES" X')
        assert stmt3.postcondition is not None
        assert stmt3.postcondition.value == "YES"

        # Falsy: empty string
        stmt4 = analyze_first_command('W:"" X')
        assert stmt4.postcondition is not None
        assert stmt4.postcondition.value == ""
