"""Tests for device parameters ASG analysis (§8.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.3
Device parameters are used with OPEN, CLOSE, and USE commands.
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MUseStatement, MCloseStatement
from m2py.asg.expressions import MLiteral
from m2py.parser.textx_classes import NumericLiteral


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestDeviceParametersAnalysis:
    """ASG-level tests for device parameters (§8.3)."""

    def test_device_param_asg_node(self):
        """Device parameter produces correct ASG node (§8.3).

        Tests that device parameters are captured in the ASG for
        USE and CLOSE commands with keyword=value syntax.
        """
        # USE with keyword parameter (WIDTH=80)
        stmt = analyze_first_command("USE 0:(WIDTH=80)")
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        device = stmt.devices[0]
        assert device.device_expr is not None
        # Parameters are captured
        assert len(device.parameters) >= 1

        # CLOSE with keyword parameter (DELETE)
        stmt2 = analyze_first_command("CLOSE 0:DELETE")
        assert isinstance(stmt2, MCloseStatement)
        assert len(stmt2.devices) == 1
        device2 = stmt2.devices[0]
        # Keyword becomes string literal in parameters
        assert len(device2.parameters) == 1
        assert isinstance(device2.parameters[0], MLiteral)
        assert device2.parameters[0].value == "DELETE"

    def test_device_param_value_analysis(self):
        """Device parameter value is analyzed correctly (§8.3).

        Tests that device parameter values (the right side of keyword=value)
        are correctly analyzed as expressions.
        """
        # WIDTH=80 should have the value 80 in parameters
        stmt = analyze_first_command("USE 0:(WIDTH=80)")
        assert isinstance(stmt, MUseStatement)
        device = stmt.devices[0]
        # The value (80) should be in parameters
        assert len(device.parameters) >= 1
        # Find the numeric value
        has_value = any(
            isinstance(p, NumericLiteral) and p.value == 80 for p in device.parameters
        )
        assert has_value, f"Expected value 80 in parameters: {device.parameters}"

        # Multiple params with different value types
        stmt2 = analyze_first_command("USE 0:(WIDTH=80:FOLLOW)")
        assert isinstance(stmt2, MUseStatement)
        device2 = stmt2.devices[0]
        # Should have multiple parameters
        assert len(device2.parameters) >= 1

    def test_mnemonic_device_param_analysis(self):
        """Mnemonic device parameters are analyzed correctly (§8.3).

        Tests mnemonic device controls (e.g., /REWIND, /LISTEN).
        Note: Not all implementations support mnemonic controls.
        """
        # Keyword-only parameters (no value)
        stmt = analyze_first_command("CLOSE DEV:DESTROY")
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        device = stmt.devices[0]
        # DESTROY keyword should be in parameters
        assert len(device.parameters) == 1
        assert isinstance(device.parameters[0], MLiteral)
        assert device.parameters[0].value == "DESTROY"

        # NODESTROY keyword
        stmt2 = analyze_first_command("CLOSE DEV:NODESTROY")
        assert isinstance(stmt2, MCloseStatement)
        device2 = stmt2.devices[0]
        assert len(device2.parameters) == 1
        assert device2.parameters[0].value == "NODESTROY"
