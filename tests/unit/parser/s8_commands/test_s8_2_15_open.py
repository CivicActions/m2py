"""Tests for OPEN command parsing (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15
"""

import pytest


@pytest.mark.parser
class TestOpenCommandParsing:
    """Parser-level tests for OPEN command (§8.2.15)."""

    def test_open_basic(self, parse_line):
        """OPEN device parses correctly (§8.2.15).

        Per MUMPS spec §8.2.15: OPEN command obtains ownership of a device.
        Basic form: O[PEN] device
        """
        from m2py.asg import MOpenStatement

        result = parse_line(" O DEV")
        label = result.labels[0]
        assert len(label.body.statements) >= 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "DEV"

    def test_open_with_parameters(self, parse_line):
        """OPEN device:(params) parses correctly (§8.2.15).

        Per MUMPS spec: OPEN device:(deviceparameters)
        Device parameters specify how the device should be opened.
        """
        from m2py.asg import MOpenStatement

        result = parse_line(' O DEV:("RW")')
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "DEV"
        assert len(stmt.devices[0].parameters) == 1

    def test_open_with_timeout(self, parse_line):
        """OPEN device::timeout parses correctly (§8.2.15).

        Per MUMPS spec: timeout specifies max wait time in seconds.
        Double colon (::) means no parameters, just timeout.
        If timeout present, $TEST is affected by success of ownership.
        """
        from m2py.asg import MOpenStatement

        result = parse_line(" O DEV::30")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "DEV"
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 30
        # Double colon means no parameters
        assert stmt.devices[0].parameters == []

    def test_open_with_mnemonic(self, parse_line):
        """OPEN device:(params):timeout:mnemonicspace parses correctly (§8.2.15).

        Per MUMPS spec: mnemonicspace specifies controlmnemonics set
        for subsequent Read/Write commands. Format:
        OPEN device:(params):timeout:mnemonicspec
        """
        from m2py.asg import MOpenStatement

        result = parse_line(" O DEV:(PARAMS):10:MNE")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "DEV"
        assert stmt.devices[0].timeout is not None
        assert stmt.devices[0].timeout.value == 10

    def test_open_multiple(self, parse_line):
        """OPEN dev1,dev2 multiple devices parses correctly (§8.2.15).

        Per MUMPS spec: OPEN accepts comma-separated list of devices.
        Each openargument is processed in left-to-right order.
        """
        from m2py.asg import MOpenStatement

        result = parse_line(" O DEV1,DEV2,DEV3")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 3
        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"
        assert stmt.devices[2].device_expr.name == "DEV3"


@pytest.mark.parser
class TestOpenDeviceParametersGrammar:
    """Test OPEN command with device parameters via MUMPSParser."""

    def test_open_simple(self):
        """O device should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_timeout(self):
        """O device:timeout should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV:10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_params(self):
        """O device:(params) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV:(1)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_multiple_params(self):
        """O device:(param:param:param) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tO DEV:("AVL4":0:2048)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_params_and_timeout(self):
        """O device:(params):timeout should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tO DEV:("RW"):30\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1


@pytest.mark.parser
class TestOpenMnemonicGrammar:
    """Test OPEN with 4th mnemonic argument via MUMPSParser.

    Per MUMPS 1995 spec 8.2.15: OPEN dev:params:timeout:mnemonicspec
    """

    def test_open_with_mnemonic(self):
        """OPEN DEV:(params):10:MNEMONIC should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV:(PARAMS):10:MNE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_empty_params_with_mnemonic(self):
        """OPEN DEV::10:MNEMONIC should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV::10:MNE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_mnemonic_only(self):
        """OPEN DEV:::MNEMONIC should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV:::MNE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_without_mnemonic_still_works(self):
        """OPEN DEV:(params):10 should still work."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tO DEV:(PARAMS):10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
