"""Tests for ASG elements.py LIVE coverage gaps.

Covers:
- MLabel.has_explicit_exit — all-unreachable branch
- MRoutine.get_label() — not-found path
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.elements import MLabel, MScope
from m2py.asg.statements import (
    MWriteStatement,
)


pytestmark = pytest.mark.asg


# =============================================================================
# has_explicit_exit
# =============================================================================


class TestHasExplicitExit:
    """Tests for MLabel.has_explicit_exit property."""

    def test_quit_is_explicit_exit(self):
        """Label ending with unconditional QUIT → True."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tW 1\n\tQ\n")
        label = routine.get_label("TEST")
        assert label.has_explicit_exit is True

    def test_goto_is_explicit_exit(self):
        """Label ending with unconditional GOTO → True."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tG OTHER\n\tQ\nOTHER\n\tQ\n")
        label = routine.get_label("TEST")
        assert label.has_explicit_exit is True

    def test_halt_is_explicit_exit(self):
        """Label ending with HALT → True."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tH\n")
        label = routine.get_label("TEST")
        assert label.has_explicit_exit is True

    def test_write_not_explicit_exit(self):
        """Label ending with non-exit statement → False."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tW 1\n")
        label = routine.get_label("TEST")
        assert label.has_explicit_exit is False

    def test_empty_body_not_explicit_exit(self):
        """Label with empty body → False."""
        label = MLabel(name="EMPTY", body=MScope())
        assert label.has_explicit_exit is False

    def test_no_body_not_explicit_exit(self):
        """Label with no body → False."""
        label = MLabel(name="EMPTY")
        assert label.has_explicit_exit is False

    def test_conditional_quit_not_explicit_exit(self):
        """Label ending with conditional QUIT (Q:X) → False."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tQ:X\n")
        label = routine.get_label("TEST")
        assert label.has_explicit_exit is False

    def test_all_unreachable_not_explicit_exit(self):
        """All statements marked unreachable → False (the uncovered branch)."""
        label = MLabel(name="TEST", body=MScope())
        stmt = MWriteStatement()
        stmt.is_unreachable = True
        label.body.statements = [stmt]
        assert label.has_explicit_exit is False


# =============================================================================
# get_label
# =============================================================================


class TestGetLabel:
    """Tests for MRoutine.get_label()."""

    def test_get_existing_label(self):
        """get_label returns MLabel for existing name."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tQ\nOTHER\n\tQ\n")
        label = routine.get_label("TEST")
        assert label is not None
        assert label.name == "TEST"

    def test_get_nonexistent_label(self):
        """get_label returns None for nonexistent name."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n\tQ\n")
        label = routine.get_label("NOTFOUND")
        assert label is None

    def test_get_label_multiple(self):
        """get_label returns correct label from multiple."""
        parser = MUMPSParser()
        routine = parser.parse("A\n\tQ\nB\n\tQ\nC\n\tQ\n")
        assert routine.get_label("A").name == "A"
        assert routine.get_label("B").name == "B"
        assert routine.get_label("C").name == "C"
