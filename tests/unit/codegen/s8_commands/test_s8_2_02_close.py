"""Tests for CLOSE command code generation (§8.2.2).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.2

Spec 013 Phase 10: CLOSE command closes devices/files.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
class TestCloseCommandCodegen:
    """Codegen-level tests for CLOSE command code generation (§8.2.2)."""

    def test_close_codegen(self) -> None:
        """CLOSE generates _rt.close_device call (§8.2.2)."""
        source = """\
TEST
 C "test.txt"
 Q
"""
        python_code = generate_python(source)
        assert "_rt.close_device" in python_code
        assert '"test.txt"' in python_code

    def test_close_multiple_devices(self) -> None:
        """CLOSE can close multiple devices (§8.2.2)."""
        source = """\
TEST
 C "file1.txt","file2.txt"
 Q
"""
        python_code = generate_python(source)
        # Should have two close_device calls
        assert python_code.count("_rt.close_device") == 2
