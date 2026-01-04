"""Tests for USE command parsing (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23
"""

import pytest

from m2py.asg import MUseStatement


@pytest.mark.parser
class TestUseCommandParsing:
    """Parser-level tests for USE command (§8.2.23)."""

    def test_use_basic(self, parse_mumps):
        """USE device parses correctly (§8.2.23).

        USE switches the principal device.
        """
        result = parse_mumps("TEST\n U 0\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1

    def test_use_with_parameters(self, parse_mumps):
        """USE device:params parses correctly (§8.2.23).

        Device parameters control device behavior.
        """
        result = parse_mumps("TEST\n U 0:NOWRAP\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        # Device has parameters
        assert stmt.devices[0].parameters is not None

    def test_use_with_mnemonic(self, parse_mumps):
        """USE device:(params):mnemonicspace parses correctly (§8.2.23).

        Mnemonic space specifies device type.
        """
        result = parse_mumps('TEST\n U 0:("NOWRAP")\n Q')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1

    def test_use_abbreviated(self, parse_mumps):
        """U abbreviation parses correctly (§8.2.23).

        U is the standard abbreviation for USE.
        """
        result = parse_mumps("TEST\n U 5\n Q")
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
