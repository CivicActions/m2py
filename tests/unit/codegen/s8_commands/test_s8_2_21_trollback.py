"""Tests for TROLLBACK command code generation (§8.2.21).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
Limitation: docs/limitations.md - LIM-016: TROLLBACK:n has zero VistA usage
"""

import pytest


@pytest.mark.codegen
class TestTrollbackCommandCodegen:
    """Codegen-level tests for TROLLBACK command code generation (§8.2.21)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TROLLBACK to rollback")
    def test_trollback_to_rollback(self, generate_python):
        """TROLLBACK generates transaction rollback (§8.2.21)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestTrollbackLevelCodegen:
    """Codegen tests for TROLLBACK:n (LIM-016).

    TROLLBACK:n (rollback to specific transaction level) has zero VistA usage.
    Codegen should raise NotImplementedError explicitly.

    Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
    Limitation: docs/limitations.md - LIM-016: Zero-VistA-Usage Deferred Features
    """

    @pytest.mark.xfail(
        reason="LIM-016: TROLLBACK:n codegen not yet raising NotImplementedError"
    )
    def test_lim016_trollback_level_raises_error(self, generate_python):
        """TROLLBACK:n should raise NotImplementedError (LIM-016).

        TROLLBACK:n has zero VistA usage. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="TROLLBACK"):
            generate_python("TEST TROLLBACK:1 Q")
