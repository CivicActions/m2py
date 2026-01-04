"""Tests for OPEN command ASG analysis (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MOpenStatement


@pytest.mark.asg
class TestOpenCommandAnalysis:
    """ASG-level tests for OPEN command analysis (§8.2.15)."""

    def test_open_command_simple(self):
        """OPEN command creates correct ASG node (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None

    def test_open_device_expression(self):
        """OPEN device expression is analyzed (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_open_parameters(self):
        """OPEN parameters are analyzed (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n O X:("ABC")\n')

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None
        assert stmt.devices[0].device_expr.name == "X"
        assert stmt.devices[0].timeout is None
        assert len(stmt.devices[0].parameters) == 1

    def test_open_with_timeout_single_colon(self):
        """OPEN command with timeout (single colon syntax O X:5) (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X:5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None
        assert stmt.devices[0].device_expr.name == "X"
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 5
        assert stmt.devices[0].parameters == []

    def test_open_with_timeout_double_colon(self):
        """OPEN command with double colon timeout (::timeout syntax) (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X::10\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None
        assert stmt.devices[0].device_expr.name == "X"
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 10
        assert stmt.devices[0].parameters == []

    def test_open_with_params_and_timeout(self):
        """OPEN command with parameters and timeout (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n O X:("A":0:2048):5\n')

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None
        assert stmt.devices[0].device_expr.name == "X"
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 5
        assert len(stmt.devices[0].parameters) == 3

    def test_open_multiple_devices_with_params(self):
        """OPEN with parameters on multiple devices (§8.2.15)."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n O DEV1:("A"):5,DEV2:("B")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        # First device has params and timeout
        assert stmt.devices[0].device_expr.name == "DEV1"
        assert len(stmt.devices[0].parameters) == 1
        assert stmt.devices[0].timeout is not None

        # Second device has params only
        assert stmt.devices[1].device_expr.name == "DEV2"
        assert len(stmt.devices[1].parameters) == 1
