"""Tests for out-of-scope commands parsing.

These commands are part of the ANSI spec but are explicitly out of scope
for the M2PY transpiler project.
"""

import pytest


@pytest.mark.parser
class TestOutOfScopeCommands:
    """Parser-level tests for commands that are out of scope."""

    @pytest.mark.skip(reason="Out of scope: ESTART is primarily for embedded MUMPS")
    def test_estart_command(self):
        """ESTART command is out of scope (§8.3)."""
        pass

    @pytest.mark.skip(reason="Out of scope: ESTOP is primarily for embedded MUMPS")
    def test_estop_command(self):
        """ESTOP command is out of scope (§8.3)."""
        pass

    @pytest.mark.skip(reason="Out of scope: ETRIGGER is primarily for embedded MUMPS")
    def test_etrigger_command(self):
        """ETRIGGER command is out of scope (§8.3)."""
        pass

    @pytest.mark.skip(
        reason="Out of scope: RLOAD is primarily for binary routine loading"
    )
    def test_rload_command(self):
        """RLOAD command is out of scope (§8.3)."""
        pass

    @pytest.mark.skip(
        reason="Out of scope: RSAVE is primarily for binary routine saving"
    )
    def test_rsave_command(self):
        """RSAVE command is out of scope (§8.3)."""
        pass

    @pytest.mark.xfail(reason="Used in VistA: ZALLOCATE (8 uses)")
    def test_zallocate_command(self):
        """ZALLOCATE command is implementation-defined but used in VistA."""
        pytest.fail("Stub - implement test")

    @pytest.mark.xfail(reason="Used in VistA: ZDEALLOCATE (with ZALLOCATE)")
    def test_zdeallocate_command(self):
        """ZDEALLOCATE command is implementation-defined but used with ZALLOCATE."""
        pytest.fail("Stub - implement test")
