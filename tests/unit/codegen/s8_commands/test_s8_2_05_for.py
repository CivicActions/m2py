"""Tests for FOR command code generation (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest


@pytest.mark.codegen
class TestForCommandCodegen:
    """Codegen-level tests for FOR command code generation (§8.2.5)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR counted to for-range")
    def test_for_counted_to_range(self, generate_python):
        """FOR counted generates Python range loop (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR list to for-in")
    def test_for_list_to_for_in(self, generate_python):
        """FOR list generates Python for-in loop (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR infinite to while")
    def test_for_infinite_to_while(self, generate_python):
        """FOR infinite generates while True (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR with QUIT")
    def test_for_with_quit(self, generate_python):
        """FOR with QUIT generates break (§8.2.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FOR nested")
    def test_for_nested(self, generate_python):
        """Nested FOR generates nested Python loops (§8.2.5)."""
        pytest.fail("Stub - implement test")
