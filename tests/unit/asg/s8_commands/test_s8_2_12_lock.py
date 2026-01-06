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
        # Verify timeout value is captured (consolidated from cross_cutting/test_timeouts.py)
        target = stmt.targets[0]
        assert target.get("timeout") is not None
        assert target["timeout"].value == 5

    def test_lock_release_all(self, analyze_routine):
        """LOCK without arguments releases all locks."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n L\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert stmt.targets == []

    def test_lock_naked_global(self):
        """LOCK ^(sub) uses naked global reference (§7.1.2.4).

        Lock targets can use naked references. Lock targets are returned
        as dicts with 'lockop' and 'target' keys.
        """
        from m2py.asg.expressions import MNakedGlobal
        from m2py.parser.line_parser import parse_commands_from_line
        from m2py.analysis.semantic_analyzer import analyze_command

        cmds = parse_commands_from_line("L ^(1)")
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        # Lock targets are dicts with 'lockop' and 'target' keys
        target_dict = stmt.targets[0]
        assert isinstance(target_dict, dict)
        assert "target" in target_dict
        assert isinstance(target_dict["target"], MNakedGlobal)
        assert len(target_dict["target"].subscripts) == 1
