"""Tests for LOCK command ASG analysis (§8.2.12).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MLockStatement


@pytest.mark.asg
class TestLockCommandAnalysis:
    """ASG-level tests for LOCK command analysis (§8.2.12)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK command node")
    def test_lock_command_node(self, analyze_routine):
        """LOCK command creates correct ASG node (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK incremental/decremental")
    def test_lock_increment_decrement(self, analyze_routine):
        """LOCK +/- forms are analyzed (§8.2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK timeout")
    def test_lock_timeout(self, analyze_routine):
        """LOCK timeout expression is analyzed (§8.2.12)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestLockStatementASG:
    """Tests for LOCK command ASG field population."""

    def test_lock_command_simple(self):
        """LOCK variable produces MLockStatement."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_command_with_timeout(self):
        """LOCK variable:timeout handles timeout."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL:5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_increment(self):
        """LOCK +variable produces incremental lock."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L +^GLOBAL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        assert stmt.lock_type == "+"

    def test_lock_decrement(self):
        """LOCK -variable produces decremental lock."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L -^GLOBAL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        assert stmt.lock_type == "-"

    def test_lock_release_all(self):
        """LOCK without arguments releases all locks."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert stmt.targets == []
