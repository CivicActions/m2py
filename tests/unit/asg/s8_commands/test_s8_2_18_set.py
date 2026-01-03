"""Tests for SET command ASG analysis (§8.2.18).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.18
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MSetStatement
from m2py.asg.expressions import (
    MLiteral,
    MVariable,
    MGlobal,
    MNakedGlobal,
    MIntrinsicFunction,
)
from m2py.asg.enums import LiteralType


@pytest.mark.asg
class TestSetCommandAnalysis:
    """ASG-level tests for SET command analysis (§8.2.18)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET variable tracking")
    def test_set_variable_tracking(self, analyze_routine):
        """SET variable is tracked in output_variables (§8.2.18, FR-014)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET multiple targets")
    def test_set_multiple_targets(self, analyze_routine):
        """SET (X,Y)=value multiple targets is analyzed (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET global")
    def test_set_global(self, analyze_routine):
        """SET ^GLOBAL global assignment is tracked (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET $PIECE")
    def test_set_piece(self, analyze_routine):
        """SET $PIECE form is analyzed (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET $EXTRACT")
    def test_set_extract(self, analyze_routine):
        """SET $EXTRACT form is analyzed (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET indirection")
    def test_set_indirection(self, analyze_routine):
        """SET @var indirection is analyzed (§8.2.18)."""
        pytest.fail("Stub - implement test")


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestSetStatementAnalysis:
    """Tests for SET command analysis."""

    def test_simple_set(self):
        """SET X=1 produces MSetStatement with one assignment."""
        stmt = analyze_first_command("S X=1")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 1

        # Check target
        target = stmt.assignments[0].target
        assert isinstance(target, MVariable)
        assert target.name == "X"

        # Check value - should be an expression (MLiteral or unwrapped)
        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.value == 1

    def test_multiple_assignments(self):
        """SET X=1,Y=2 produces two assignments."""
        stmt = analyze_first_command("S X=1,Y=2")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 2

        assert stmt.assignments[0].target.name == "X"
        assert stmt.assignments[1].target.name == "Y"

    def test_set_with_global(self):
        """SET ^GLOBAL=value produces MGlobal target."""
        stmt = analyze_first_command("S ^DATA=100")

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MGlobal)
        assert target.name == "DATA"

    def test_set_string_literal(self):
        """SET X="hello" produces string literal."""
        stmt = analyze_first_command('S X="hello"')

        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.literal_type == LiteralType.STRING
        assert value.value == "hello"

    def test_set_naked_global_target(self):
        """SET ^(1)=value produces MNakedGlobal target (T526 fix)."""
        stmt = analyze_first_command("S ^(1)=100")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 1

        target = stmt.assignments[0].target
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 1

    def test_set_naked_global_multiple_subscripts(self):
        """SET ^(1,2)=value produces MNakedGlobal with 2 subscripts (T526 fix)."""
        stmt = analyze_first_command("S ^(1,2)=100")

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 2

    def test_set_mixed_global_and_naked_global(self):
        """SET ^V1(1)=1,^(2)=2 produces GlobalVariable then NakedGlobal (T526 fix)."""
        stmt = analyze_first_command("S ^V1(1)=1,^(2)=2")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 2

        # First target is GlobalVariable
        target1 = stmt.assignments[0].target
        assert isinstance(target1, MGlobal)
        assert target1.name == "V1"

        # Second target is NakedGlobal
        target2 = stmt.assignments[1].target
        assert isinstance(target2, MNakedGlobal)
        assert len(target2.subscripts) == 1

    def test_set_parenthesized_multi_target_expansion(self):
        """SET (A,B,C)=1 expands into 3 separate MAssignment objects (T537 fix).

        Per data-model.md, MAssignment.target should be a single expression,
        not a list. Multi-assignment with parenthesized targets should expand
        into separate assignments with the same value.
        """
        stmt = analyze_first_command("S (A,B,C)=1")

        assert isinstance(stmt, MSetStatement)
        # Should have 3 assignments, one for each target
        assert len(stmt.assignments) == 3

        # Each assignment has a single target (not a list)
        for i, name in enumerate(["A", "B", "C"]):
            assign = stmt.assignments[i]
            assert isinstance(assign.target, MVariable), (
                f"Assignment {i} target should be MVariable, got {type(assign.target)}"
            )
            assert assign.target.name == name
            # Value should be a literal 1
            assert isinstance(assign.value, MLiteral)
            assert assign.value.value == 1

    def test_set_parenthesized_with_globals(self):
        """SET (A,^B,C)=X expands to 3 assignments with mixed types (T537 fix)."""
        stmt = analyze_first_command("S (A,^B,C)=X")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 3

        # First target is local variable
        assert isinstance(stmt.assignments[0].target, MVariable)
        assert stmt.assignments[0].target.name == "A"

        # Second target is global variable
        assert isinstance(stmt.assignments[1].target, MGlobal)
        assert stmt.assignments[1].target.name == "B"

        # Third target is local variable
        assert isinstance(stmt.assignments[2].target, MVariable)
        assert stmt.assignments[2].target.name == "C"

    def test_set_parenthesized_mixed_with_regular(self):
        """SET (A,B)=1,C=2 produces 3 assignments total (T537 fix)."""
        stmt = analyze_first_command("S (A,B)=1,C=2")

        assert isinstance(stmt, MSetStatement)
        # (A,B)=1 expands to 2 assignments, plus C=2 is 1 more = 3 total
        assert len(stmt.assignments) == 3

        # First two targets from multi-assignment have value 1
        assert stmt.assignments[0].target.name == "A"
        assert stmt.assignments[0].value.value == 1
        assert stmt.assignments[1].target.name == "B"
        assert stmt.assignments[1].value.value == 1

        # Third target is regular assignment with value 2
        assert stmt.assignments[2].target.name == "C"
        assert stmt.assignments[2].value.value == 2

    def test_set_left_hand_piece_simple(self):
        """SET $P(X,"^")="D" - left-hand $PIECE as assignment target (T567 fix).

        MUMPS allows $PIECE on the left side of an assignment to modify
        a specific piece of a string variable.
        """
        stmt = analyze_first_command('S $P(X,"^")="D"')

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 1

        # Target should be MIntrinsicFunction for $PIECE
        target = stmt.assignments[0].target
        assert isinstance(target, MIntrinsicFunction)
        assert target.name.upper() in ("P", "PIECE")

        # Value should be the string "D"
        value = stmt.assignments[0].value
        assert isinstance(value, MLiteral)
        assert value.value == "D"

    def test_set_left_hand_piece_with_positions(self):
        """SET $P(X,"^",2,3)="D" - left-hand $PIECE with position args (T567 fix)."""
        stmt = analyze_first_command('S $P(X,"^",2,3)="D"')

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MIntrinsicFunction)
        assert target.name.upper() in ("P", "PIECE")
        # Should have 4 arguments: var, delimiter, start, end
        assert len(target.arguments) == 4

    def test_set_left_hand_piece_mixed_with_regular(self):
        """SET X="A^B",$P(X,"^")="D" - mixed regular and left-hand $PIECE (T567 fix)."""
        stmt = analyze_first_command('S X="A^B",$P(X,"^")="D"')

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 2

        # First assignment is regular variable
        assert isinstance(stmt.assignments[0].target, MVariable)
        assert stmt.assignments[0].target.name == "X"

        # Second assignment is left-hand $PIECE
        assert isinstance(stmt.assignments[1].target, MIntrinsicFunction)
        assert stmt.assignments[1].target.name.upper() in ("P", "PIECE")


@pytest.mark.asg
class TestParseSetCommand:
    """Test SET command parsing to full-fidelity ASG."""

    def test_simple_set(self):
        """S X=1 creates MSetStatement"""
        cmds = parse_commands_from_line("S X=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.assignments) == 1
        assert stmt.assignments[0].target.name == "X"

    def test_set_multiple(self):
        """S X=1,Y=2 creates two assignments"""
        cmds = parse_commands_from_line("S X=1,Y=2")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert len(stmt.assignments) == 2

    def test_set_global(self):
        """S ^GLOBAL=1 parses global variable"""
        cmds = parse_commands_from_line("S ^GLOBAL=1")
        stmt = analyze_command(cmds[0])
        assert stmt is not None
        assert isinstance(stmt.assignments[0].target, MGlobal)
