"""Unit tests for MScope.walk_statements recursive walker.

Validates that walk_statements visits every statement exactly once,
including statements nested inside IF then/else bodies, FOR bodies,
and DO blocks (S-10, FR-010).
"""

import pytest

from m2py.asg.elements import MScope
from m2py.asg.statements import (
    MDoStatement,
    MForStatement,
    MIfStatement,
    MWriteStatement,
)
from m2py.parser import MUMPSParser

pytestmark = pytest.mark.asg


class TestWalkStatementsBasic:
    """Basic walk_statements behavior."""

    def test_empty_scope(self):
        """Empty scope yields no statements."""
        scope = MScope()
        assert list(scope.walk_statements()) == []

    def test_flat_statements(self):
        """Flat list of statements yields them in order."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tW 1\n\tW 2\n\tW 3\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # 3 WRITE + 1 QUIT = 4 statements
        assert len(stmts) == 4

    def test_single_statement(self):
        """Single statement scope yields one item."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        assert len(stmts) == 1


class TestWalkStatementsIfElse:
    """Walking into IF then_scope and ELSE body."""

    def test_if_then_scope(self):
        """Statements inside IF then_scope are visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tI 1 W 1\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # IF + nested WRITE + QUIT = 3
        assert len(stmts) == 3
        # First is IF, then WRITE (inside then_scope), then QUIT
        assert isinstance(stmts[0], MIfStatement)
        assert isinstance(stmts[1], MWriteStatement)

    def test_else_body(self):
        """Statements inside ELSE body are visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tI 1 W 1\n\tE  W 2\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # IF + WRITE(in then) + ELSE + WRITE(in else body) + QUIT = 5
        assert len(stmts) == 5
        write_stmts = [s for s in stmts if isinstance(s, MWriteStatement)]
        assert len(write_stmts) == 2


class TestWalkStatementsFor:
    """Walking into FOR body."""

    def test_for_body(self):
        """Statements inside FOR body are visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tF I=1:1:3 W I\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # FOR + WRITE(in body) + QUIT = 3
        assert len(stmts) == 3
        assert isinstance(stmts[0], MForStatement)
        assert isinstance(stmts[1], MWriteStatement)

    def test_nested_for(self):
        """Nested FOR loops: all inner statements visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tF I=1:1:2 F J=1:1:2 W I\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # outer FOR + inner FOR + WRITE + QUIT = 4
        assert len(stmts) == 4


class TestWalkStatementsDoBlock:
    """Walking into DO block body."""

    def test_do_block(self):
        """Statements inside argumentless DO block are visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tD\n\t. W 1\n\t. W 2\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # DO + WRITE + WRITE + QUIT = 4
        assert len(stmts) == 4
        assert isinstance(stmts[0], MDoStatement)
        assert isinstance(stmts[1], MWriteStatement)
        assert isinstance(stmts[2], MWriteStatement)


class TestWalkStatementsComplex:
    """Complex nesting patterns."""

    def test_if_for_combination(self):
        """IF containing FOR: all statements visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tI 1 F I=1:1:2 W I\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # IF + FOR(in then) + WRITE(in for body) + QUIT = 4
        assert len(stmts) == 4

    def test_for_containing_if(self):
        """FOR containing IF: all statements visited."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tF I=1:1:3 I I=2 W I\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # FOR + IF(in body) + WRITE(in then) + QUIT = 4
        assert len(stmts) == 4

    def test_uniqueness(self):
        """Each statement is visited exactly once (no duplicates)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tI 1 W 1\n\tE  W 2\n\tF I=1:1:2 W I\n\tQ\n")
        label = routine.get_label("TEST")
        stmts = list(label.body.walk_statements())
        # All statements should have unique id() values
        ids = [id(s) for s in stmts]
        assert len(ids) == len(set(ids)), "Duplicate statements in walk"

    def test_counting_visitor(self):
        """Acceptance scenario: counting visitor visits every statement once.

        Given a routine with nested IF, FOR, and DO blocks,
        When walk_statements() is called with a counting visitor,
        Then it visits every statement exactly once.
        """
        parser = MUMPSParser()
        source = "TEST\n\tI 1 W 1\n\tE  W 2\n\tF I=1:1:2 W I\n\tD\n\t. W 3\n\tQ\n"
        routine = parser.parse(source)
        label = routine.get_label("TEST")

        # Count statements by type
        counts: dict[str, int] = {}
        for stmt in label.body.walk_statements():
            name = type(stmt).__name__
            counts[name] = counts.get(name, 0) + 1

        # Verify each statement type was visited
        assert counts.get("MIfStatement", 0) >= 1
        assert counts.get("MElseStatement", 0) >= 1
        assert counts.get("MForStatement", 0) >= 1
        assert counts.get("MDoStatement", 0) >= 1
        assert counts.get("MWriteStatement", 0) >= 3  # W 1, W 2, W I, W 3
