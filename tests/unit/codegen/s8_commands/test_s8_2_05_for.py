"""Tests for FOR command code generation (§8.2.5).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.5
"""

import pytest


@pytest.mark.codegen
class TestForCommandCodegen:
    """Codegen-level tests for FOR command code generation (§8.2.5)."""

    def test_for_counted_to_range(self, generate_python):
        """FOR counted generates Python range loop (§8.2.5)."""
        code = generate_python("TEST\n F I=1:1:3 W I\n Q\n")
        assert "for I in range(" in code
        assert "_for_step" in code
        assert "_for_end" in code

    def test_for_list_to_for_in(self, generate_python):
        """FOR list generates Python for-in loop (§8.2.5)."""
        code = generate_python('TEST\n F I="A","B","C" W I\n Q\n')
        assert 'for I in ["A", "B", "C"]:' in code

    def test_for_bounded_iteration(self, execute_mumps):
        """FOR bounded range outputs correct values.

        User Story 3 acceptance scenario 1 (T036):
        Given: F I=1:1:3 W I
        When: generated and executed
        Then: output is "123" (end-inclusive)
        """
        result = execute_mumps("TEST\n F I=1:1:3 W I\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_for_decrement_iteration(self, execute_mumps):
        """FOR decrement range outputs correct values.

        User Story 3 acceptance scenario 2 (T037):
        Given: F I=5:-1:3 W I
        When: generated and executed
        Then: output is "543" (end-inclusive, negative step)
        """
        result = execute_mumps("TEST\n F I=5:-1:3 W I\n Q\n")
        assert result.output == "543"
        assert result.success is True

    def test_for_string_list_iteration(self, execute_mumps):
        """FOR string list outputs correct values.

        User Story 3 acceptance scenario 3 (T038):
        Given: F I="A","B","C" W I
        When: generated and executed
        Then: output is "ABC"
        """
        result = execute_mumps('TEST\n F I="A","B","C" W I\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

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
