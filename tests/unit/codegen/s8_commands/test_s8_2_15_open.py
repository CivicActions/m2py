"""Tests for OPEN command code generation (§8.2.15).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.15

Spec 013 Phase 10: OPEN command opens devices/files for I/O.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
class TestOpenCommandCodegen:
    """Codegen-level tests for OPEN command code generation (§8.2.15)."""

    def test_open_to_file_open(self) -> None:
        """OPEN generates _rt.open_device call (§8.2.15)."""
        source = """\
TEST
 O "test.txt"
 Q
"""
        python_code = generate_python(source)
        assert "_rt.open_device" in python_code
        assert '"test.txt"' in python_code

    def test_open_with_parameters(self) -> None:
        """OPEN parameters are passed to open_device (§8.2.15)."""
        source = """\
TEST
 O "test.txt":NEWVERSION
 Q
"""
        python_code = generate_python(source)
        assert "_rt.open_device" in python_code
        # NEWVERSION should be treated as a keyword parameter
        assert "'NEWVERSION'" in python_code or '"NEWVERSION"' in python_code

    def test_open_with_parenthesized_params(self) -> None:
        """OPEN with parenthesized parameters (§8.2.15)."""
        source = """\
TEST
 O "test.txt":(NEWVERSION)
 Q
"""
        python_code = generate_python(source)
        assert "_rt.open_device" in python_code

    def test_open_with_timeout_sets_test(self) -> None:
        """OPEN with timeout sets $TEST (§8.2.15)."""
        source = """\
TEST
 O "test.txt":(NEWVERSION):5
 Q
"""
        python_code = generate_python(source)
        assert "_rt.open_device" in python_code
        assert "_test =" in python_code  # Timed OPEN sets $TEST
        assert "5" in python_code  # Timeout value


@pytest.mark.codegen
class TestOpenE2E:
    """E2E file I/O tests (coverage: codegen L5740-5875, runtime device paths)."""

    def test_open_write_read_close(self, execute_mumps, tmp_path):
        """Full file I/O cycle: OPEN → USE → WRITE → CLOSE → reopen → READ."""
        f = tmp_path / "test.txt"
        result = execute_mumps(
            "TEST\n"
            f' S F="{f}"\n'
            ' O F:("NEWVERSION")\n'
            " U F\n"
            ' W "hello from MUMPS",!\n'
            " C F\n"
            ' O F:("READONLY")\n'
            " U F\n"
            " R X\n"
            " C F\n"
            " U 0\n"
            " W X,!\n"
            " Q\n"
        )
        assert "hello from MUMPS" in result.output
