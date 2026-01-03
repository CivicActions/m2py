"""Tests for USE command ASG analysis (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MUseStatement


@pytest.mark.asg
class TestUseCommandAnalysis:
    """ASG-level tests for USE command analysis (§8.2.23)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE command node")
    def test_use_command_node(self, analyze_routine):
        """USE command creates correct ASG node (§8.2.23)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE $IO modification")
    def test_use_io_modification(self, analyze_routine):
        """USE modifies $IO (§8.2.23)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: USE parameters")
    def test_use_parameters(self, analyze_routine):
        """USE parameters are analyzed (§8.2.23)."""
        pytest.fail("Stub - implement test")


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
