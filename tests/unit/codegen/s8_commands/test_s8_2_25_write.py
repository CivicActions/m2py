"""Tests for WRITE command code generation (§8.2.25).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.25
"""

import pytest


@pytest.mark.codegen
class TestWriteCommandCodegen:
    """Codegen-level tests for WRITE command code generation (§8.2.25)."""

    def test_write_to_print(self, generate_python):
        """WRITE generates _rt.write() call (§8.2.25)."""
        code = generate_python('TEST\n W "HELLO"\n Q\n')
        assert "_rt.write" in code

    def test_write_string_literal(self, execute_mumps):
        """WRITE outputs string literal directly (§8.2.25).

        User Story 1 acceptance scenario 2:
        Given: TEST W "PASS" Q
        When: generated and executed
        Then: output is "PASS"
        """
        result = execute_mumps('TEST\n W "PASS"\n Q\n')
        assert result.output == "PASS"
        assert result.success is True

    def test_write_format_controls(self, execute_mumps):
        """WRITE !, # generate newlines/form feeds (§8.2.25).

        YDB verified: W "A",!,"B" → "A\\nB"
        """
        result = execute_mumps('TEST\n W "A",!,"B"\n Q\n')
        assert result.output == "A\nB"
        assert result.success is True

    def test_write_column(self, execute_mumps):
        """WRITE ?n generates column positioning (§8.2.25).

        YDB verified: W ?5,"X" → "     X"
        """
        result = execute_mumps('TEST\n W ?5,"X"\n Q\n')
        assert result.output == "     X"
        assert result.success is True

    def test_write_char_code(self, execute_mumps):
        """WRITE *n generates char output (§8.2.25).

        YDB verified: W *65 → "A"
        """
        result = execute_mumps("TEST\n W *65\n Q\n")
        assert result.output == "A"
        assert result.success is True

    def test_write_device_control_not_supported(self, generate_python):
        """WRITE device control (/mnemonic) raises NotImplementedError.

        Device control mnemonics like /CUP(row,col) are terminal-specific
        sequences that cannot be transpiled to pure Python.

        Spec 015: Document that device control mnemonics are not supported.
        """
        code = "TEST\n W /CUP(10,5)\n Q\n"
        with pytest.raises(NotImplementedError, match="DeviceControl"):
            generate_python(code)

    def test_write_device_control_with_string_raises_not_implemented(
        self, generate_python
    ):
        """WRITE with device control mnemonic and string raises NotImplementedError."""
        code = 'TEST\n W /BOLD,"text",/NORMAL\n Q\n'
        with pytest.raises(NotImplementedError, match="DeviceControl"):
            generate_python(code)
