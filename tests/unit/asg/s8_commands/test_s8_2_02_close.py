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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE device tracking")
    def test_close_device_tracking(self, analyze_routine):
        """CLOSE device expression is tracked (§8.2.2).

        Should verify that CLOSE device expressions are tracked for
        semantic analysis (e.g., input_variables, output_variables tracking).
        """
        pytest.fail(
            "Stub - implement test for device expression tracking in semantic analysis"
        )

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
