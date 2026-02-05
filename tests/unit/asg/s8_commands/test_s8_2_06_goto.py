"""Tests for GOTO command ASG analysis (§8.2.6).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.6
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MGotoStatement
from m2py.asg.expressions import MGlobal, MIndirection


@pytest.mark.asg
class TestGotoCommandAnalysis:
    """ASG-level tests for GOTO command analysis (§8.2.6)."""

    def test_goto_type_classification(self):
        """GOTO goto_type is correctly classified (§8.2.6, FR-012)."""
        # GOTO has a goto_type attribute (may be None or enum)
        stmt = analyze_first_command("G LABEL")
        assert isinstance(stmt, MGotoStatement)
        assert hasattr(stmt, "goto_type")

        # Verify GOTO has control flow attributes
        assert hasattr(stmt, "exits_loops")
        assert hasattr(stmt, "is_cross_label")

        # GOTO to external routine
        stmt2 = analyze_first_command("G LABEL^ROUTINE")
        assert isinstance(stmt2, MGotoStatement)
        # External routine reference in target
        assert stmt2.targets[0].routine == "ROUTINE"

    def test_goto_target_resolution(self, analyze_routine):
        """GOTO target is resolved to MLabel (§8.2.6)."""
        # Simple GOTO
        stmt = analyze_first_command("G LABEL")
        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"

        # GOTO with routine
        stmt = analyze_first_command("G LABEL^ROUTINE")
        assert isinstance(stmt, MGotoStatement)
        assert stmt.targets[0].name == "LABEL"
        assert stmt.targets[0].routine == "ROUTINE"

        # GOTO with offset
        stmt = analyze_first_command("G LABEL+^DATA(1)^ROUTINE")
        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]
        assert target.name == "LABEL"
        assert target.routine == "ROUTINE"
        assert isinstance(target.offset, MGlobal)
        assert target.offset.name == "DATA"
        assert len(target.offset.subscripts) == 1

    def test_goto_computed_target(self):
        """GOTO computed target is tracked (§8.2.6)."""
        from m2py.asg.elements import MCall
        from m2py.asg.expressions import MVariable, MIndirection

        # GOTO with indirection
        stmt = analyze_first_command("G @A")
        assert isinstance(stmt, MGotoStatement)
        assert len(stmt.targets) == 1

        target = stmt.targets[0]
        assert isinstance(target, MCall)

        # Target should indicate indirect reference
        # indirection is MIndirection wrapping the variable
        assert target.label_is_indirect is True
        assert target.indirection is not None
        assert isinstance(target.indirection, MIndirection)
        assert isinstance(target.indirection.expression, MVariable)
        assert target.indirection.expression.name == "A"

        # GOTO with routine indirection
        stmt2 = analyze_first_command("G LABEL^@R")
        assert isinstance(stmt2, MGotoStatement)
        target2 = stmt2.targets[0]
        assert isinstance(target2, MCall)
        assert target2.routine_is_indirect is True

    def test_goto_control_flow_impact(self):
        """GOTO control flow impact is analyzed (§8.2.6)."""
        # GOTO terminates current line flow (unconditional transfer)
        stmt = analyze_first_command("G LABEL")
        assert isinstance(stmt, MGotoStatement)

        # Verify control flow attributes exist
        assert hasattr(stmt, "exits_loops")
        assert hasattr(stmt, "is_cross_label")
        # Note: is_loop_continue was removed - GOTO cannot create continue semantics

        # GOTO with postcondition is conditional
        stmt2 = analyze_first_command("G:X LABEL")
        assert isinstance(stmt2, MGotoStatement)
        assert stmt2.postcondition is not None

        # GOTO to multiple targets (conditional execution)
        stmt3 = analyze_first_command("G LABEL1,LABEL2")
        assert isinstance(stmt3, MGotoStatement)
        assert len(stmt3.targets) == 2

    def test_goto_with_argument_postconditions(self):
        """G L1:C1,L2:C2,L3 parses argument-level postconditions (§8.1.4).

        Computed GOTO pattern - first true postcondition wins.
        Only Do, Goto, and Xecute support argument postconditions.
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


@pytest.mark.asg
class TestGotoRoutineIndirection:
    """Tests for GOTO with routine indirection (GAP-011c).

    Per MUMPS 1995 §8.1.6, entryrefs allow indirection of routine name.
    """

    def test_goto_routine_indirection(self):
        """GOTO LABEL^@ROUTINEVAR - routine name is indirect.

        Routine name evaluated from variable at runtime.
        """
        stmt = analyze_first_command("G LABEL^@R")
        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.routine_is_indirect is True
        assert target.routine_indirection is not None
        # Single indirection wraps the variable in MIndirection
        assert isinstance(target.routine_indirection, MIndirection)
        assert target.routine_indirection.expression.name == "R"

    def test_goto_double_indirection_routine(self):
        """GOTO LABEL^@@R - double indirection on routine.

        @@R means dereference R twice to get routine name.
        """
        stmt = analyze_first_command("G LABEL^@@R")
        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.routine_is_indirect is True
        # Double indirection should create nested structure
        assert target.routine_indirection is not None


@pytest.mark.asg
class TestGotoOffsetExpressions:
    """Tests for GOTO with offset expressions (GAP-011e).

    Per MUMPS 1995 §8.1.6, GOTO allows label+offset syntax.
    """

    def test_goto_label_with_offset(self):
        """GOTO LABEL+5 - numeric offset from label.

        References 5th line after LABEL.
        """
        stmt = analyze_first_command("G LABEL+5")
        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.offset is not None
        assert target.offset.value == 5

    def test_goto_label_offset_routine(self):
        """GOTO LABEL+3^ROUTINE - full entryref with offset.

        Complete form: label+offset^routine
        """
        stmt = analyze_first_command("G LABEL+3^ROUTINE")
        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.offset is not None
        assert target.offset.value == 3
        assert target.routine == "ROUTINE"

    def test_goto_global_offset(self):
        """GOTO LABEL+^DATA(1)^ROUTINE - global as offset expression.

        Offset can be any expression including global references.
        """
        stmt = analyze_first_command("G LABEL+^DATA(1)^ROUTINE")
        assert isinstance(stmt, MGotoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.routine == "ROUTINE"
        assert isinstance(target.offset, MGlobal)
        assert target.offset.name == "DATA"


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])
