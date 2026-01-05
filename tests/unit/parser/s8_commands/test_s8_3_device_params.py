"""Tests for device parameters parsing (§8.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.3
"""

import pytest

from m2py.asg import MOpenStatement


@pytest.mark.parser
class TestDeviceParametersParsing:
    """Parser-level tests for device parameters (§8.3)."""

    def test_device_param_basic(self, parse_line):
        """Device parameter basic form parses correctly (§8.3).

        Per MUMPS spec §8.2.15/8.2.2: deviceparameters may be used
        with OPEN and CLOSE commands in parentheses.
        """
        # OPEN with single device parameter
        result = parse_line(' O DEV:("RW")')
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1

    def test_device_param_with_value(self, parse_line):
        """Device parameter=value parses correctly (§8.3).

        Per MUMPS spec: device parameters may include expressions
        that specify configuration values.
        """
        # OPEN with parameter as expression
        result = parse_line(" O DEV:(1024)")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices[0].parameters) == 1

    def test_device_param_list(self, parse_line):
        """Multiple device parameters parse correctly (§8.3).

        Per MUMPS spec: Multiple parameters can be specified with
        colon separators inside parentheses: device:(p1:p2:p3)
        """
        # OPEN with multiple colon-separated parameters
        result = parse_line(' O DEV:("A":0:2048)')
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        # Should have 3 parameters
        assert len(stmt.devices[0].parameters) == 3

    def test_mnemonic_device_params(self, parse_line):
        """Mnemonic device parameters parse correctly (§8.3).

        Per MUMPS spec §8.2.15: Format is device:(params):timeout:mnemonicspec
        The 4th position (after 3 colons) specifies the mnemonicspace.
        """
        # OPEN with mnemonic space (4th position)
        result = parse_line(" O DEV:(PARAMS):10:MNE")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        # Should parse the mnemonic space
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 10
