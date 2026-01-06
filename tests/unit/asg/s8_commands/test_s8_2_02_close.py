"""Tests for CLOSE command ASG analysis (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MCloseStatement


@pytest.mark.asg
class TestCloseCommandAnalysis:
    """ASG-level tests for CLOSE command analysis (§8.2.2)."""

    def test_close_command_node(self, analyze_routine):
        """CLOSE command creates correct ASG node (§8.2.2)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None
        assert stmt.devices[0].device_expr.name == "X"

    def test_close_device_tracking(self):
        """CLOSE device expression is tracked (§8.2.2).

        Should verify that CLOSE device expressions are tracked for
        semantic analysis (e.g., input_variables, output_variables tracking).
        """
        from m2py.asg.expressions import MVariable

        parser = MUMPSParser()
        routine = parser.parse("TEST\n C DEV\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)

        # Verify device expressions are available for tracking
        assert len(stmt.devices) == 1
        device = stmt.devices[0]

        # Device expression should be analyzable (e.g., variable name extraction)
        assert device.device_expr is not None
        assert isinstance(device.device_expr, MVariable)
        assert device.device_expr.name == "DEV"

        # Multiple devices should all be tracked
        routine2 = parser.parse("TEST\n C A,B,C\n")
        stmt2 = routine2.labels[0].body.statements[0]
        assert len(stmt2.devices) == 3
        device_names = [d.device_expr.name for d in stmt2.devices]
        assert device_names == ["A", "B", "C"]

    def test_close_multiple_devices(self, analyze_routine):
        """CLOSE with multiple devices captures all devices (§8.2.2)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_close_device_parameters(self, analyze_routine):
        """CLOSE device:(params) parses parameters (§8.2.2)."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n C DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1

    def test_close_with_keyword_parameters(self):
        """CLOSE file:delete and file:(params) syntax (§8.2.2)."""
        parser = MUMPSParser()

        # C file:delete
        routine = parser.parse("TEST\n C file:delete\n")
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        # Verify it parsed (structural check depends on ASG mapping of keywords)

        # C file:(DELETE)
        routine = parser.parse("TEST\n C file:(DELETE)\n")
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)

        # C file:(RENAME=newfile)
        routine = parser.parse("TEST\n C file:(RENAME=newfile)\n")
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
