"""Tests for TCOMMIT command code generation (§8.2.19).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.19
"""

import pytest


@pytest.mark.codegen
class TestTcommitCommandCodegen:
    """Codegen-level tests for TCOMMIT command code generation (§8.2.19)."""

    def test_tcommit_to_commit(self, generate_python):
        """TCOMMIT generates transaction commit (§8.2.19)."""
        code = """\
TEST
 TCOMMIT
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.transaction_commit()" in result

    def test_tcommit_abbreviated(self, generate_python):
        """TC (abbreviated) generates transaction commit (§8.2.19)."""
        code = """\
TEST
 TC
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.transaction_commit()" in result
