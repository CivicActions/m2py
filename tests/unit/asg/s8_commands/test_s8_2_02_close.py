"""Tests for CLOSE command ASG analysis (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MCloseStatement


@pytest.mark.asg
class TestCloseCommandAnalysis:
    """ASG-level tests for CLOSE command analysis (§8.2.2)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE command node")
    def test_close_command_node(self, analyze_routine):
        """CLOSE command creates correct ASG node (§8.2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: CLOSE device tracking")
    def test_close_device_tracking(self, analyze_routine):
        """CLOSE device expression is tracked (§8.2.2)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestCloseStatementASG:
    """Tests for CLOSE command ASG generation."""

    def test_close_command_simple(self):
        """Test CLOSE command with simple device."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None


@pytest.mark.asg
class TestMultiClose:
    """Tests for CLOSE command with multiple devices."""

    def test_single_close(self):
        """Single CLOSE device works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_close(self):
        """CLOSE with multiple devices captures all devices."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_close_with_params(self):
        """CLOSE device:(params) parses parameters."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n C DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1
