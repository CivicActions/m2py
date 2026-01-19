"""Tests for ZSHOW command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZshowCodegen:
    """Codegen-level tests for ZSHOW command (YDB)."""

    def test_zshow_generates_state_display(self, generate_python):
        """ZSHOW generates state/variable display."""
        code = generate_python('TEST ZSHOW "V" Q')
        assert "_rt.zshow(" in code
        assert '"V"' in code

    def test_zshow_v_shows_variables(self, execute_mumps):
        """ZSHOW V displays local variables."""
        result = execute_mumps('TEST S X=1 ZSHOW "V" Q')
        assert result.success
        assert "X=1" in result.output

    def test_zshow_multiple_codes(self, generate_python):
        """ZSHOW with multiple codes."""
        code = generate_python('TEST ZSHOW "VI" Q')
        assert "_rt.zshow(" in code
        assert '"VI"' in code
