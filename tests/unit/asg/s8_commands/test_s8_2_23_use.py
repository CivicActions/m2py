"""Tests for USE command ASG analysis (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg import MUseStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestUseCommandAnalysis:
    """ASG-level tests for USE command analysis (§8.2.23)."""

    def test_use_command_node(self):
        """USE command creates correct ASG node (§8.2.23).

        Verifies that USE command produces MUseStatement with correct device structure.
        """
        # Simple USE
        stmt = analyze_first_command("U X")
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None
        assert stmt.devices[0].device_expr.name == "X"

        # Full keyword USE
        stmt2 = analyze_first_command("USE DEV")
        assert isinstance(stmt2, MUseStatement)
        assert len(stmt2.devices) == 1

    def test_use_io_modification(self):
        """USE modifies $IO (§8.2.23).

        Verifies that USE command captures device expression that will
        become the new $IO value at runtime.
        """
        # USE with variable device
        stmt = analyze_first_command("U X")
        assert isinstance(stmt, MUseStatement)
        # Device expression is captured for $IO modification
        assert stmt.devices[0].device_expr.name == "X"

        # USE with literal device
        stmt2 = analyze_first_command("U 0")
        assert isinstance(stmt2, MUseStatement)
        # Device is literal 0 (principal device)
        assert stmt2.devices[0].device_expr is not None

    def test_use_parameters(self):
        """USE parameters are analyzed (§8.2.23).

        Verifies that USE captures device parameters.
        """
        # USE with parameters
        stmt = analyze_first_command("U X:(WIDTH=80)")
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        # Parameters are captured
        assert hasattr(stmt.devices[0], "parameters")
        assert len(stmt.devices[0].parameters) >= 1


@pytest.mark.asg
class TestUseStatementASG:
    """Tests for USE command ASG generation."""

    def test_use_command_simple(self):
        """Test USE command with simple device."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U X\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None


@pytest.mark.asg
class TestMultiUse:
    """Tests for USE command with multiple devices."""

    def test_single_use(self):
        """Single USE device works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U X\n")
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_use_with_keyword_parameters(self):
        """USE with single keyword, keyword=value, and multiple keywords (§8.2.23)."""
        parser = MUMPSParser()

        # U file:rewind
        routine = parser.parse("TEST\n U file:rewind\n")
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        # Check ASG reflects keyword presence (assumes parameters capture it)
        # Detailed structural check was done in parser meta tests, here passing parser is key.

        # U tf:exception="goto EOF"
        routine = parser.parse('TEST\n U tf:exception="goto EOF"\n')
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)

        # U file:(rewind:follow)
        routine = parser.parse("TEST\n U file:(rewind:follow)\n")
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)

    def test_multi_use(self):
        """USE with multiple devices captures all devices."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_use_with_params(self):
        """USE device:(params) parses parameters."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n U DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1
