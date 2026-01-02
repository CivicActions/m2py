"""Tests for OPEN command parsing (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15

Migrated from:
- tests/unit/test_grammar.py::TestOpenDeviceParametersGrammar
- tests/unit/test_grammar.py::TestOpenMnemonicGrammar
- tests/unit/test_io_commands.py (OPEN tests)
- tests/unit/test_multi_arg_commands.py::TestMultiOpen
"""

import pytest

from m2py.asg import MRoutine, MOpenStatement
from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestOpenCommandParsing:
    """Parser-level tests for OPEN command (§8.2.15)."""

    def test_open_basic(self):
        """OPEN device parses correctly (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_simple
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr is not None

    def test_open_with_timeout(self):
        """OPEN device:timeout parses correctly (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_with_timeout
        """
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

    def test_open_with_double_colon_timeout(self):
        """OPEN device::timeout parses correctly (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_with_double_colon_timeout
        """
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

    def test_open_with_params(self):
        """OPEN device:(params) parses correctly (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_with_params
        """
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

    def test_open_with_params_and_timeout(self):
        """OPEN device:(params):timeout parses correctly (§8.2.15).

        Migrated from: test_io_commands.py::test_open_command_with_params_and_timeout
        """
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

    def test_open_multiple_devices(self):
        """OPEN dev1,dev2 multiple devices parses correctly (§8.2.15).

        Migrated from: test_multi_arg_commands.py::TestMultiOpen::test_multi_open
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_open_with_params_multiple(self):
        """OPEN with parameters on multiple devices (§8.2.15).

        Migrated from: test_multi_arg_commands.py::TestMultiOpen::test_open_with_params_multiple
        """
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


@pytest.mark.parser
class TestOpenDeviceParametersGrammar:
    """Test OPEN command with device parameters (§8.2.15).

    Migrated from: tests/unit/test_grammar.py::TestOpenDeviceParametersGrammar
    """

    def test_open_simple(self):
        """O device should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_timeout(self):
        """O device:timeout should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV:10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_params(self):
        """O device:(params) should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV:(1)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_multiple_params(self):
        """O device:(param:param:param) should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV:("AVL4":0:2048)\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MOpenStatement"

    def test_open_with_params_and_timeout(self):
        """O device:(params):timeout should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = 'LABEL\tO DEV:("RW"):30\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1


@pytest.mark.parser
class TestOpenMnemonicGrammar:
    """Test OPEN with 4th mnemonic argument (§8.2.15).

    Per MUMPS 1995 spec 8.2.15: OPEN dev:params:timeout:mnemonicspec

    Migrated from: tests/unit/test_grammar.py::TestOpenMnemonicGrammar
    """

    def test_open_with_mnemonic(self):
        """OPEN DEV:(params):10:MNEMONIC should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV:(PARAMS):10:MNE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_empty_params_with_mnemonic(self):
        """OPEN DEV::10:MNEMONIC should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV::10:MNE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_mnemonic_only(self):
        """OPEN DEV:::MNEMONIC should parse (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV:::MNE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_open_without_mnemonic_still_works(self):
        """OPEN DEV:(params):10 should still work (§8.2.15)."""
        parser = MUMPSParser()
        source = "LABEL\tO DEV:(PARAMS):10\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
