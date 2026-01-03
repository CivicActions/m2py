"""Tests for OPEN command ASG analysis (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MOpenStatement


@pytest.mark.asg
class TestOpenCommandAnalysis:
    """ASG-level tests for OPEN command analysis (§8.2.15)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN command node")
    def test_open_command_node(self, analyze_routine):
        """OPEN command creates correct ASG node (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN device expression")
    def test_open_device_expression(self, analyze_routine):
        """OPEN device expression is analyzed (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN parameters")
    def test_open_parameters(self, analyze_routine):
        """OPEN parameters are analyzed (§8.2.15)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestOpenStatementASG:
    """Tests for OPEN command ASG generation."""

    def test_open_command_simple(self):
        """Test OPEN command with simple device."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None

    def test_open_command_with_timeout(self):
        """Test OPEN command with timeout (single colon syntax)."""
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

    def test_open_command_with_double_colon_timeout(self):
        """Test OPEN command with double colon timeout (::timeout syntax)."""
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

    def test_open_command_with_params(self):
        """Test OPEN command with parameters."""
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

    def test_open_command_with_params_and_timeout(self):
        """Test OPEN command with parameters and timeout."""
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


@pytest.mark.asg
class TestMultiOpen:
    """Tests for OPEN command with multiple devices."""

    def test_single_open(self):
        """Single OPEN device works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_open(self):
        """OPEN with multiple devices captures all devices."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_open_with_params_multiple(self):
        """OPEN with parameters on multiple devices."""
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
