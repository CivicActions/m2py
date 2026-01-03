"""Tests for regression fixes.

Tests that ensure specific bugs remain fixed across codebase changes.

MUMPS 1995 Reference: Various sections
"""

from m2py.parser import MUMPSParser


class TestPhase74Fixes:
    """Tests for Phase 74 regression fixes."""

    def test_phase74_label_with_comment_no_commands(self):
        """Phase74: Label with only comment should have empty body.statements."""
        parser = MUMPSParser()
        routine = parser.parse("MAIN ; just a comment\n")
        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert label.name == "MAIN"
        # Body should be empty (comment is not a statement)
        assert len(label.body.statements) == 0

    def test_phase74_multiple_continuation_lines(self):
        """Phase74: Multiple continuation lines should all be captured."""
        parser = MUMPSParser()
        source = """MAIN
\tS X=1
\tS Y=2
\tS Z=3
\tQ
"""
        routine = parser.parse(source)
        assert len(routine.labels) == 1
        label = routine.labels[0]
        # Should have all 4 statements (3 SET + 1 QUIT)
        assert len(label.body.statements) == 4

    def test_phase74_comment_line_in_body(self):
        """Phase74: Comment-only continuation line should not create statement."""
        parser = MUMPSParser()
        source = """MAIN
\tS X=1
\t; this is a comment
\tS Y=2
\tQ
"""
        routine = parser.parse(source)
        label = routine.labels[0]
        # Should have 3 statements (2 SET + 1 QUIT), not 4
        # Comment lines don't create statements
        assert len(label.body.statements) == 3

    def test_phase74_empty_continuation_line(self):
        """Phase74: Empty continuation line should be handled gracefully."""
        parser = MUMPSParser()
        source = "MAIN\n\tS X=1\n\t\n\tQ\n"  # Line 3 is just tab
        routine = parser.parse(source)
        # Should parse without error
        assert len(routine.labels) == 1

    def test_phase74_quit_with_value_preserves_expression(self):
        """Phase74: QUIT with return value should preserve the expression."""
        parser = MUMPSParser()
        routine = parser.parse("FUNC(X)\tQ X*2\n")
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        quit_stmt = label.body.statements[0]
        # Should have a return value (the attribute is named return_value)
        assert hasattr(quit_stmt, "return_value")
        assert quit_stmt.return_value is not None
