"""Tests for ZALLOCATE/ZDEALLOCATE command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MZAllocateStatement, MZDeallocateStatement


@pytest.mark.asg
@pytest.mark.ydb
class TestZallocateAsg:
    """ASG-level tests for ZALLOCATE/ZDEALLOCATE command (YDB)."""

    def test_zallocate_asg_node(self):
        """ZALLOCATE creates proper ASG node with targets and lockop."""
        from m2py.asg import MLockTarget

        stmt = analyze_first_command("za X")

        assert isinstance(stmt, MZAllocateStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MLockTarget)
        assert target.lockop == "+"
        # Verify target is a variable
        assert target.name == "X"

    def test_zdeallocate_asg_node(self):
        """ZDEALLOCATE creates proper ASG node with targets and lockop."""
        from m2py.asg import MLockTarget

        stmt = analyze_first_command("zd X")

        assert isinstance(stmt, MZDeallocateStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MLockTarget)
        assert target.lockop == "-"
        # Verify target is a variable
        assert target.name == "X"


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
@pytest.mark.ydb
class TestZdeallocatePostcondition:
    """Tests for ZDEALLOCATE with postcondition."""

    def test_zdeallocate_with_postcondition(self):
        """Zdeallocate:'(i#2) X produces MZDeallocateStatement with postcondition."""
        stmt = analyze_first_command("Zdeallocate:'(i#2) X")

        assert isinstance(stmt, MZDeallocateStatement)
        assert stmt.postcondition is not None
        assert len(stmt.targets) == 1
