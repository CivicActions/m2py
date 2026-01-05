"""Tests for CLOSE command parsing (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2
"""

import pytest


@pytest.mark.parser
class TestCloseCommandParsing:
    """Parser-level tests for CLOSE command (§8.2.2)."""

    def test_close_basic(self, parse_line):
        """CLOSE device parses correctly (§8.2.2).

        Per MUMPS spec §8.2.2: CLOSE releases ownership of a device.
        Basic form: C[LOSE] device
        Device parameters in effect at Close time are retained.
        """
        from m2py.asg import MCloseStatement

        result = parse_line(" C DEV")
        label = result.labels[0]
        assert len(label.body.statements) >= 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "DEV"

    def test_close_with_parameters(self, parse_line):
        """CLOSE device:params parses correctly (§8.2.2).

        Per MUMPS spec: deviceparameters may specify termination
        procedures or other info associated with relinquishing ownership.
        """
        from m2py.asg import MCloseStatement

        result = parse_line(' C DEV:("PARAM")')
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "DEV"
        assert len(stmt.devices[0].parameters) == 1

    def test_close_multiple_devices(self, parse_line):
        """CLOSE dev1,dev2 parses correctly (§8.2.2).

        Per MUMPS spec: Each designated device is released from ownership.
        Devices not owned at Close time are unaffected.
        """
        from m2py.asg import MCloseStatement

        result = parse_line(" C DEV1,DEV2")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 2
        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"
