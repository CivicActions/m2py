"""Tests for CLOSE command code generation (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2

Spec 013 Phase 10: CLOSE command closes devices/files.
"""

import pytest


@pytest.mark.codegen
class TestCloseCommandCodegen:
    """Codegen-level tests for CLOSE command code generation (§8.2.2)."""

    def test_close_codegen(self, generate_python) -> None:
        """CLOSE generates _rt.close_device call (§8.2.2)."""
        source = """\
TEST
 C "test.txt"
 Q
"""
        python_code = generate_python(source)
        assert "_rt.close_device" in python_code
        assert '"test.txt"' in python_code

    def test_close_multiple_devices(self, generate_python) -> None:
        """CLOSE can close multiple devices (§8.2.2)."""
        source = """\
TEST
 C "file1.txt","file2.txt"
 Q
"""
        python_code = generate_python(source)
        # Should have two close_device calls
        assert python_code.count("_rt.close_device") == 2

    def test_close_file_device(self, execute_mumps, tmp_path):
        """C device — close file device (coverage: codegen L5860-5875)."""
        f = tmp_path / "test.txt"
        source = (
            "TEST\n"
            f' S F="{f}"\n'
            ' O F:("NEWVERSION")\n'
            ' U F W "data",!\n'
            " C F\n"
            " U 0\n"
            ' W "closed",!\n'
            " Q\n"
        )
        result = execute_mumps(source)
        assert "closed" in result.output
