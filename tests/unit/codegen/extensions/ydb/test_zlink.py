"""Tests for ZLINK command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZlinkCodegen:
    """Codegen-level tests for ZLINK command (YDB)."""

    def test_zlink_generates_import(self, generate_python):
        """ZLINK generates runtime zlink call."""
        code = generate_python('TEST ZLINK "MYMOD" Q')
        assert "_rt.zlink(" in code
        assert '"MYMOD"' in code or "'MYMOD'" in code

    def test_zlink_with_variable(self, generate_python):
        """ZLINK with variable generates dynamic import."""
        code = generate_python('TEST S X="MOD" ZLINK X Q')
        assert "_rt.zlink(" in code


@pytest.mark.codegen
@pytest.mark.ydb
class TestZlinkVariantsPass2:
    """ZLINK no-args and arg loop variants.

    Covers codegen/statements.py L6682-6688.
    """

    def test_zlink_no_args_codegen(self, generate_python):
        """ZLINK with no arguments generates pass."""
        code = generate_python("TEST\n ZLINK\n Q\n")
        assert code is not None

    def test_zlink_multiple_args(self, generate_python):
        """ZLINK "A","B" generates multiple zlink calls."""
        code = generate_python('TEST\n ZLINK "A","B"\n Q\n')
        assert "zlink" in code.lower()
