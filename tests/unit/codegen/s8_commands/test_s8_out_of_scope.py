"""Tests for out-of-scope command code generation.

These commands are explicitly out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard, various sections
"""

import pytest


@pytest.mark.codegen
class TestOutOfScopeCommandCodegen:
    """Codegen tests for out-of-scope commands (FR-055)."""

    @pytest.mark.skip(reason="Out of scope: ESTART/ESTOP event processing per FR-055")
    def test_estart_estop_codegen(self, generate_python):
        """ESTART/ESTOP event processing not in scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: RLOAD/RSAVE routine loading per FR-055")
    def test_rload_rsave_codegen(self, generate_python):
        """RLOAD/RSAVE routine management not in scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: ZALLOCATE/ZDEALLOCATE per FR-055")
    def test_zallocate_codegen(self, generate_python):
        """ZALLOCATE/ZDEALLOCATE not in scope."""
        pass
