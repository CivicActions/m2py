"""Tests for out-of-scope command code generation.

These commands are explicitly out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, various sections
"""

import pytest


@pytest.mark.codegen
class TestOutOfScopeCommandCodegen:
    """Codegen tests for out-of-scope commands (FR-055)."""

    @pytest.mark.skip(reason="Out of scope: ESTART/ESTOP event processing (0 uses)")
    def test_estart_estop_codegen(self, generate_python):
        """ESTART/ESTOP event processing not in scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: RLOAD/RSAVE routine loading (0 uses)")
    def test_rload_rsave_codegen(self, generate_python):
        """RLOAD/RSAVE routine management not in scope."""
        pass

    @pytest.mark.xfail(reason="Used in VistA: ZALLOCATE/ZDEALLOCATE (8 uses)")
    def test_zallocate_codegen(self, generate_python):
        """ZALLOCATE/ZDEALLOCATE is used in VistA."""
        pytest.fail("Stub - implement test")
