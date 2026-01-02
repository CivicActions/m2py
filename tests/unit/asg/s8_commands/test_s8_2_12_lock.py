"""Tests for LOCK command ASG analysis (§8.2.12).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12

Migrated from: tests/unit/test_io_commands.py::TestLockCommand
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MLockStatement


@pytest.mark.asg
class TestLockCommandAnalysis:
    """ASG-level tests for LOCK command analysis (§8.2.12)."""

    def test_lock_command_simple(self):
        """LOCK variable produces MLockStatement (§8.2.12).

        Migrated from: test_io_commands.py::TestLockCommand::test_lock_command_simple
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_command_with_timeout(self):
        """LOCK variable:timeout handles timeout (§8.2.12).

        Migrated from: test_io_commands.py::TestLockCommand::test_lock_command_with_timeout
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL:5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_increment(self):
        """LOCK +variable produces incremental lock (§8.2.12).

        Migrated from: test_io_commands.py::TestLockCommand::test_lock_increment
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L +^GLOBAL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        assert stmt.lock_type == "+"

    def test_lock_decrement(self):
        """LOCK -variable produces decremental lock (§8.2.12).

        Migrated from: test_io_commands.py::TestLockCommand::test_lock_decrement
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L -^GLOBAL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        assert stmt.lock_type == "-"

    def test_lock_release_all(self):
        """LOCK without arguments releases all locks (§8.2.12).

        Migrated from: test_io_commands.py::TestLockCommand::test_lock_release_all
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert stmt.targets == []
