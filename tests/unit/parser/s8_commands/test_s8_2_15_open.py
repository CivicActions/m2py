"""Tests for OPEN command parsing (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15
"""

import pytest


@pytest.mark.parser
class TestOpenCommandParsing:
    """Parser-level tests for OPEN command (§8.2.15)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN basic form")
    def test_open_basic(self, parse_line):
        """OPEN device parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN with parameters")
    def test_open_with_parameters(self, parse_line):
        """OPEN device:(params) parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN with timeout")
    def test_open_with_timeout(self, parse_line):
        """OPEN device::timeout parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN with mnemonic space")
    def test_open_with_mnemonic(self, parse_line):
        """OPEN device:(params):timeout:\"SOCKET\" parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: OPEN multiple devices")
    def test_open_multiple(self, parse_line):
        """OPEN dev1,dev2 multiple devices parses correctly (§8.2.15)."""
        pytest.fail("Stub - implement test")


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
