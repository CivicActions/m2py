"""Tests for Routine Body ASG analysis (§6.2).

Reference: MUMPS 1995 ANSI Standard, Section 6.2

Key concepts from spec:
- §6.2.1 Level line: A line without formallist, LEVEL = number of dots + 1
- §6.2.2 Formal line: Contains label AND formallist (parameter list)
- §6.2.3 Label: Defining occurrence to left of ls (label separator)
- §6.2.4 Label separator (ls): One or more spaces before linebody
- §6.2.5 Line body: Sequence of commands and optional comment
"""

import pytest

from m2py.asg.elements import MLabel
from m2py.asg.statements import MSetStatement, MDoStatement, MQuitStatement


@pytest.mark.asg
class TestRoutineBodyAnalysis:
    """ASG-level tests for routine body analysis (§6.2)."""

    def test_level_line_analysis(self, analyze_routine):
        """Level lines are correctly represented in ASG (§6.2.1).

        From spec: A levelline is a line that does not contain a formallist.
        The LEVEL of a line is the number plus one of li (level indicators/dots).

        Lines with dots (. prefix) are at higher levels and are captured
        within the body of argumentless DO statements.
        """
        source = """TEST
 S X=1
 D
 . S Y=2
 . S Z=3
 Q
"""
        routine = analyze_routine(source)

        # First label TEST should exist
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "TEST"

        # Body should have: SET, DO (with nested block), QUIT
        assert len(label.body.statements) == 3
        assert isinstance(label.body.statements[0], MSetStatement)
        assert isinstance(label.body.statements[1], MDoStatement)
        assert isinstance(label.body.statements[2], MQuitStatement)

        # The DO statement should contain the dot-level statements
        do_stmt = label.body.statements[1]
        assert do_stmt.body is not None
        assert len(do_stmt.body.statements) == 2
        # Both are SET statements for Y and Z
        assert isinstance(do_stmt.body.statements[0], MSetStatement)
        assert isinstance(do_stmt.body.statements[1], MSetStatement)

    def test_formal_line_analysis(self, analyze_routine):
        """Formal lines are correctly represented in ASG (§6.2.2).

        From spec: A formalline contains both a label and a formallist
        which is a (possibly empty) list of variable names. These names
        may contain data passed to this subroutine.
        """
        source = """MYFUNC(A,B,C)
 S R=A+B+C
 Q R
"""
        routine = analyze_routine(source)

        # Label with formal parameters
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "MYFUNC"

        # Formal list should contain the parameters
        assert label.formal_list is not None
        assert label.formal_list == ["A", "B", "C"]

    def test_formal_line_empty_params(self, analyze_routine):
        """Formal line with empty parameter list (§6.2.2).

        A formallist can be empty: LABEL()
        """
        source = """NOPARAM()
 S X=1
 Q
"""
        routine = analyze_routine(source)

        label = routine.labels[0]
        assert label.name == "NOPARAM"
        # Empty formal list
        assert label.formal_list == []

    def test_label_extraction(self, analyze_routine):
        """Labels are extracted and indexed in ASG (§6.2.3).

        From spec: Each occurrence of a label to the left of ls in
        a line is called a defining occurrence of label.
        """
        source = """FIRST
 S X=1
 Q
SECOND
 S Y=2
 Q
THIRD(P)
 S Z=P
 Q
"""
        routine = analyze_routine(source)

        # All labels should be extracted
        assert len(routine.labels) == 3

        # Check label names
        label_names = [label.name for label in routine.labels]
        assert "FIRST" in label_names
        assert "SECOND" in label_names
        assert "THIRD" in label_names

        # Labels should be retrievable by name
        first = routine.get_label("FIRST")
        assert first is not None
        assert isinstance(first, MLabel)
        assert first.name == "FIRST"

    def test_label_reference_resolution(self, analyze_routine):
        """Label references are resolved to MLabel nodes (§6.2.3).

        When a DO or GOTO references a label, the ASG should capture
        the reference with the correct target label name.
        """
        source = """TEST
 D HELPER
 Q
HELPER
 S X=1
 Q
"""
        routine = analyze_routine(source)

        # Get the DO statement
        test_label = routine.get_label("TEST")
        do_stmt = test_label.body.statements[0]
        assert isinstance(do_stmt, MDoStatement)

        # DO targets should contain a reference
        assert len(do_stmt.targets) == 1
        target = do_stmt.targets[0]

        # The target should reference HELPER label by name
        assert target.name == "HELPER"
        # No routine specified (same routine)
        assert target.routine is None

        # HELPER label should exist and be retrievable
        helper_label = routine.get_label("HELPER")
        assert helper_label is not None
        assert helper_label.name == "HELPER"

    def test_line_body_analysis(self, analyze_routine):
        """Line bodies contain correct command sequences (§6.2.5).

        From spec: The linebody consists of an optional sequence of
        commands and an optional comment. Individual commands are
        separated by one or more spaces.
        """
        source = """TEST
 S X=1 S Y=2 S Z=3
 Q
"""
        routine = analyze_routine(source)

        label = routine.labels[0]
        # Multiple commands on same line should all be captured
        # Line has: S X=1, S Y=2, S Z=3, then Q on next line
        # Total: 4 statements (3 SET + 1 QUIT)
        assert len(label.body.statements) == 4
        assert isinstance(label.body.statements[0], MSetStatement)
        assert isinstance(label.body.statements[1], MSetStatement)
        assert isinstance(label.body.statements[2], MSetStatement)
        assert isinstance(label.body.statements[3], MQuitStatement)

    def test_block_structure(self, analyze_routine):
        """Block structure (DO-level blocks) is correctly represented (§6.2).

        Argumentless DO starts a block. Lines with dot prefix (level > 1)
        are contained within the block scope.
        """
        source = """TEST
 S A=1
 D
 . S B=2
 . D
 . . S C=3
 . S D=4
 S E=5
 Q
"""
        routine = analyze_routine(source)

        label = routine.labels[0]
        # Top level: SET A, DO (block), SET E, QUIT
        assert len(label.body.statements) == 4

        # First DO has nested block
        outer_do = label.body.statements[1]
        assert isinstance(outer_do, MDoStatement)
        assert outer_do.body is not None

        # Outer block contains: SET B, DO (inner), SET D
        assert len(outer_do.body.statements) == 3
        inner_do = outer_do.body.statements[1]
        assert isinstance(inner_do, MDoStatement)

        # Inner block contains: SET C
        assert inner_do.body is not None
        assert len(inner_do.body.statements) == 1
        assert isinstance(inner_do.body.statements[0], MSetStatement)

    def test_comment_handling(self, analyze_routine):
        """Comments are correctly handled in ASG (§6.2).

        Comments start with ; and continue to end of line.
        They should not affect command parsing.
        """
        source = """TEST ; label comment
 S X=1 ; inline comment
 ; full line comment (no commands)
 S Y=2
 Q
"""
        routine = analyze_routine(source)

        label = routine.labels[0]
        # Should have: SET X, SET Y, QUIT (comment-only line skipped)
        assert len(label.body.statements) == 3
        assert isinstance(label.body.statements[0], MSetStatement)
        assert isinstance(label.body.statements[1], MSetStatement)
        assert isinstance(label.body.statements[2], MQuitStatement)

        # Verify values are correct (comments didn't interfere)
        set_x = label.body.statements[0]
        assert set_x.assignments[0].target.name == "X"

        set_y = label.body.statements[1]
        assert set_y.assignments[0].target.name == "Y"
