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
