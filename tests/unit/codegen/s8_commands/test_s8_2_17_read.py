"""Tests for READ command code generation (§8.2.17).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.17
"""

import pytest


@pytest.mark.codegen
class TestReadCommandCodegen:
    """Codegen-level tests for READ command code generation (§8.2.17)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ to input")
    def test_read_to_input(self, generate_python):
        """READ generates input() or file read (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ with prompt")
    def test_read_with_prompt(self, generate_python):
        """READ with prompt generates print then input (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ timeout")
    def test_read_timeout(self, generate_python):
        """READ timeout generates timeout wrapper (§8.2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: READ single char")
    def test_read_single_char(self, generate_python):
        """READ *X generates single char read (§8.2.17)."""
        pytest.fail("Stub - implement test")
