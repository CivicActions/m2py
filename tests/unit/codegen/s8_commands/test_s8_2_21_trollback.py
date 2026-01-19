"""Tests for TROLLBACK command code generation (§8.2.21).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
Limitation: docs/limitations.md - LIM-016: TROLLBACK:n has zero VistA usage
"""

import pytest

from m2py.codegen import generate_python


@pytest.mark.codegen
class TestTrollbackCommandCodegen:
    """Codegen-level tests for TROLLBACK command code generation (§8.2.21)."""

    def test_trollback_generates_rollback(self):
        """TROLLBACK generates transaction rollback (§8.2.21)."""
        code = generate_python("TEST\n TROLLBACK\n Q")
        assert "_rt.globals.transaction_rollback()" in code


@pytest.mark.codegen
class TestTrollbackLevelCodegen:
    """Codegen tests for TROLLBACK:n (LIM-016).

    TROLLBACK:n (rollback to specific transaction level) has zero VistA usage.
    Codegen should raise NotImplementedError explicitly.

    Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
    Limitation: docs/limitations.md - LIM-016: Zero-VistA-Usage Deferred Features
    """

    def test_lim016_trollback_level_raises_error(self):
        """TROLLBACK:n should raise NotImplementedError (LIM-016).

        TROLLBACK:n has zero VistA usage. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="LIM-016"):
            generate_python("TEST\n TROLLBACK 1\n Q")
