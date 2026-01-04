"""Tests for LOCK command ASG analysis (§8.2.12).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MLockStatement


@pytest.mark.asg
class TestLockCommandAnalysis:
    """ASG-level tests for LOCK command analysis (§8.2.12)."""

    def test_lock_command_node(self, analyze_routine):
        """LOCK command creates correct ASG node (§8.2.12)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_increment_decrement(self, analyze_routine):
        """LOCK +/- forms are analyzed (§8.2.12)."""
        parser = MUMPSParser()
        # Incremental
        routine_inc = parser.parse("TEST\n L +^GLOBAL\n")
        stmt_inc = routine_inc.labels[0].body.statements[0]
        assert isinstance(stmt_inc, MLockStatement)
        assert len(stmt_inc.targets) >= 1
        assert stmt_inc.lock_type == "+"

        # Decremental
        routine_dec = parser.parse("TEST\n L -^GLOBAL\n")
        stmt_dec = routine_dec.labels[0].body.statements[0]
        assert isinstance(stmt_dec, MLockStatement)
        assert len(stmt_dec.targets) >= 1
        assert stmt_dec.lock_type == "-"

    def test_lock_timeout(self, analyze_routine):
        """LOCK timeout expression is analyzed (§8.2.12)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL:5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_release_all(self, analyze_routine):
        """LOCK without arguments releases all locks."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert stmt.targets == []
