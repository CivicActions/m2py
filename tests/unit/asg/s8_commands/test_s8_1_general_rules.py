"""Tests for Command General Rules ASG analysis (§8.1).

Reference: MUMPS 1995 ANSI Standard, Section 8.1

Key concepts tested:
- Postconditions: Conditional execution based on truthvalue (§8.1.4)
- Timeouts: Time limits on I/O operations (§8.1.5)
- Line references: Label^Routine targeting for DO/GOTO (§8.1.6)
- Parameter passing: BY_VALUE vs BY_REFERENCE modes (§8.1.7)
- Command abbreviation: All abbreviated forms normalize to same ASG type
"""

import pytest
from m2py.asg import (
    MBinaryOp,
    MCall,
    MActualParameter,
    PassingMode,
    MSetStatement,
    MDoStatement,
    MReadStatement,
)
from m2py.parser.textx_classes import NumericLiteral, LocalVariable


@pytest.mark.asg
class TestCommandGeneralRulesAnalysis:
    """ASG-level tests for command general rules analysis (§8.1)."""

    def test_postcondition_analysis(self, analyze_routine):
        """Command postconditions are correctly analyzed (§8.1).

        MUMPS: SET:X=1 Y=2  (execute SET only if X=1 is true)
        The postcondition expression should be analyzed as MBinaryOp.
        """
        routine = analyze_routine("TEST\n S:X=1 Y=2")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, MBinaryOp)
        assert stmt.postcondition.operator == "="
        assert isinstance(stmt.postcondition.left, LocalVariable)
        assert stmt.postcondition.left.name == "X"
        assert isinstance(stmt.postcondition.right, NumericLiteral)
        assert stmt.postcondition.right.value == 1

    def test_timeout_analysis(self, analyze_routine):
        """Command timeouts are correctly analyzed (§8.1).

        MUMPS: READ X:5  (read with 5 second timeout)
        The timeout should be captured as a NumericLiteral on the read target.
        """
        routine = analyze_routine("TEST\n R X:5")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MReadStatement)
        assert len(stmt.arguments) == 1
        read_target = stmt.arguments[0]
        assert read_target.timeout is not None
        assert isinstance(read_target.timeout, NumericLiteral)
        assert read_target.timeout.value == 5

    def test_line_reference_resolution(self, analyze_routine):
        """Line references are resolved to targets (§8.1).

        MUMPS: DO LABEL^ROUTINE
        The target should be an MCall with name='LABEL' and routine='ROUTINE'.
        """
        routine = analyze_routine("TEST\n D LABEL^ROUTINE")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MCall)
        assert target.name == "LABEL"
        assert target.routine == "ROUTINE"

    def test_parameter_passing_analysis(self, analyze_routine):
        """Parameter passing modes (byref, byval) are analyzed (§8.1).

        MUMPS: DO LABEL(.X,Y)
        .X is passed BY_REFERENCE, Y is passed BY_VALUE.
        """
        routine = analyze_routine("TEST\n D LABEL(.X,Y)")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]
        assert isinstance(target, MCall)
        assert len(target.arguments) == 2

        # First param: .X is BY_REFERENCE
        param1 = target.arguments[0]
        assert isinstance(param1, MActualParameter)
        assert param1.passing_mode == PassingMode.BY_REFERENCE
        assert param1.variable_name == "X"

        # Second param: Y is BY_VALUE
        param2 = target.arguments[1]
        assert isinstance(param2, MActualParameter)
        assert param2.passing_mode == PassingMode.BY_VALUE

    def test_argument_postcondition_in_do(self, analyze_routine):
        """Argument postconditions on DO targets are analyzed (§8.1.4).

        Per 1995__a108005.md: "The postcond may also be used to conditionalize
        the arguments of Do, Goto, and Xecute."
        Each MCall target has its own postcondition field.
        """
        from m2py.parser.textx_classes import LocalVariable

        routine = analyze_routine("TEST\n D L1:A,L2:B")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MDoStatement)
        assert stmt.postcondition is None  # No command-level postcondition
        assert len(stmt.targets) == 2

        # Each target has its own argument postcondition
        assert stmt.targets[0].postcondition is not None
        assert isinstance(stmt.targets[0].postcondition, LocalVariable)
        assert stmt.targets[0].postcondition.name == "A"

        assert stmt.targets[1].postcondition is not None
        assert isinstance(stmt.targets[1].postcondition, LocalVariable)
        assert stmt.targets[1].postcondition.name == "B"

    def test_complex_postcondition_expression(self, analyze_routine):
        """SET:(X>0)&(Y<10) Z=1 parses complex postcondition (§8.1.4).

        Postcondition can be any truthvalue expression (tvexpr).
        Complex boolean expressions with & (AND) are allowed.
        """
        routine = analyze_routine("TEST\n S:(X>0)&(Y<10) Z=1")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        # Complex expression should be MBinaryOp with & operator
        assert isinstance(stmt.postcondition, MBinaryOp)
        assert stmt.postcondition.operator == "&"

    def test_postcondition_with_intrinsic_function(self, analyze_routine):
        """SET:$D(X) Y=X parses postcondition with intrinsic function (§8.1.4).

        $DATA returns 0 if variable doesn't exist, non-zero otherwise.
        This is a common pattern to check if variable is defined.
        """
        from m2py.asg.expressions import MIntrinsicFunction

        routine = analyze_routine("TEST\n S:$D(X) Y=X")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        assert isinstance(stmt.postcondition, MIntrinsicFunction)
        assert stmt.postcondition.name.upper() in ("D", "DATA")

    def test_postcondition_left_to_right_evaluation(self, analyze_routine):
        """W:X>0&Y<10 DATA - postcondition with left-to-right evaluation (§8.1.4).

        MUMPS uses strict left-to-right evaluation (no operator precedence),
        so X>0&Y<10 parses as ((X>0)&Y)<10.
        """
        from m2py.asg.statements import MWriteStatement
        from m2py.parser.textx_classes import NumericLiteral

        routine = analyze_routine("TEST\n W:X>0&Y<10 DATA")
        stmt = routine.labels[0].body.statements[0]

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

    def test_postcondition_function_in_comparison(self, analyze_routine):
        """S:$L(X)>0 Y=X - intrinsic function in comparison postcondition (§8.1.4).

        $LENGTH in a comparison expression - tests nested function calls.
        """
        from m2py.asg.expressions import MIntrinsicFunction

        routine = analyze_routine("TEST\n S:$L(X)>0 Y=X")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MSetStatement)
        pc = stmt.postcondition
        assert pc is not None

        # Should be MBinaryOp: $L(X) > 0
        assert isinstance(pc, MBinaryOp)
        assert pc.operator == ">"
        # Left side is the function call
        assert isinstance(pc.left, MIntrinsicFunction)
        assert pc.left.name.upper() in ("L", "LENGTH")

    def test_combined_command_and_argument_postconditions(self, analyze_routine):
        """Both command and argument postconditions are captured (§8.1.4).

        DO:CMD L1:ARG1,L2:ARG2 has command-level postcondition that gates
        all execution, plus independent argument-level postconditions.
        """
        from m2py.parser.textx_classes import LocalVariable

        routine = analyze_routine("TEST\n D:READY PROC1:A,PROC2:B")
        stmt = routine.labels[0].body.statements[0]

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

    def test_command_abbreviation_normalization(self, analyze_routine):
        """Command abbreviations are normalized in ASG (§8.1).

        Both 'S X=1' and 'SET X=1' should produce MSetStatement.
        The ASG type normalizes regardless of source abbreviation.
        """
        routine_abbrev = analyze_routine("TEST\n S X=1")
        routine_full = analyze_routine("TEST\n SET X=1")

        stmt_abbrev = routine_abbrev.labels[0].body.statements[0]
        stmt_full = routine_full.labels[0].body.statements[0]

        # Both produce the same ASG type
        assert isinstance(stmt_abbrev, MSetStatement)
        assert isinstance(stmt_full, MSetStatement)

        # Both have identical structure
        assert len(stmt_abbrev.assignments) == len(stmt_full.assignments)
        assert stmt_abbrev.assignments[0].target.name == "X"
        assert stmt_full.assignments[0].target.name == "X"

    def test_postcondition_with_negation(self, analyze_routine):
        """Q:'DONE - postcondition with NOT operator (§8.1.4).

        Negated conditions use unary NOT (').
        """
        from m2py.asg.expressions import MUnaryOp
        from m2py.asg.statements import MQuitStatement

        routine = analyze_routine("TEST\n Q:'DONE")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MQuitStatement)
        pc = stmt.postcondition
        assert pc is not None
        # Should be MUnaryOp with NOT operator
        assert isinstance(pc, MUnaryOp)
        assert pc.operator == "'"

    def test_postcondition_numeric_literal(self, analyze_routine):
        """SET:1 X=1 and SET:0 X=1 - numeric literal postconditions (§8.1.4).

        SET:1 X=1 always executes (1 is truthy).
        SET:0 X=1 never executes (0 is falsy).
        """
        # Truthy postcondition
        routine1 = analyze_routine("TEST\n S:1 X=1")
        stmt1 = routine1.labels[0].body.statements[0]
        assert isinstance(stmt1, MSetStatement)
        assert stmt1.postcondition is not None
        assert stmt1.postcondition.value == 1

        # Falsy postcondition
        routine2 = analyze_routine("TEST\n S:0 X=1")
        stmt2 = routine2.labels[0].body.statements[0]
        assert isinstance(stmt2, MSetStatement)
        assert stmt2.postcondition is not None
        assert stmt2.postcondition.value == 0

    def test_postcondition_string_literal(self, analyze_routine):
        """W:\"YES\" X and W:\"\" X - string literal postconditions (§8.1.4).

        Non-empty string is truthy, empty string is falsy.

        """
        from m2py.asg.statements import MWriteStatement

        # Truthy: non-empty string
        routine1 = analyze_routine('TEST\n W:"YES" X')
        stmt1 = routine1.labels[0].body.statements[0]
        assert isinstance(stmt1, MWriteStatement)
        assert stmt1.postcondition is not None
        assert stmt1.postcondition.value == "YES"

        # Falsy: empty string
        routine2 = analyze_routine('TEST\n W:"" X')
        stmt2 = routine2.labels[0].body.statements[0]
        assert isinstance(stmt2, MWriteStatement)
        assert stmt2.postcondition is not None
        assert stmt2.postcondition.value == ""

    def test_postcondition_extrinsic_function(self, analyze_routine):
        """SET:$$INC^RT() Y=1 - extrinsic function in postcondition (§8.1.4).

        Postcondition is extrinsic function call that may have side effects.
        """
        from m2py.parser.textx_classes import ExtrinsicFunction

        routine = analyze_routine("TEST\n S:$$INC^RT() Y=1")
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MSetStatement)
        assert stmt.postcondition is not None
        # Postcondition is an extrinsic function call
        assert isinstance(stmt.postcondition, ExtrinsicFunction)
        # ExtrinsicFunction wraps an MCall target with name and routine
        assert stmt.postcondition.target.name == "INC"
        assert stmt.postcondition.target.routine == "RT"
