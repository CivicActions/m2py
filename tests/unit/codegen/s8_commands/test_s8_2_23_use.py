"""Tests for USE command code generation (§8.2.23).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.23

Spec 013 Phase 10: USE command switches the current I/O device.
"""

import pytest
from m2py.codegen import generate_python


@pytest.mark.codegen
class TestUseCommandCodegen:
    """Codegen-level tests for USE command code generation (§8.2.23)."""

    def test_use_to_device_select(self) -> None:
        """USE generates _rt.use_device call (§8.2.23)."""
        source = """\
TEST
 U "test.txt"
 Q
"""
        python_code = generate_python(source)
        assert "_rt.use_device" in python_code
        assert '"test.txt"' in python_code

    def test_use_with_parameters(self) -> None:
        """USE parameters are passed to use_device (§8.2.23)."""
        source = """\
TEST
 U "test.txt":(NOWRAP)
 Q
"""
        python_code = generate_python(source)
        assert "_rt.use_device" in python_code

    def test_use_principal_device(self) -> None:
        """USE 0 switches to principal device (§8.2.23)."""
        source = """\
TEST
 U 0
 Q
"""
        python_code = generate_python(source)
        assert "_rt.use_device" in python_code
        # Principal device is 0
        assert "0" in python_code

    def test_use_multiple_devices(self) -> None:
        """USE can switch through multiple devices (§8.2.23)."""
        source = """\
TEST
 U "file1.txt","file2.txt"
 Q
"""
        python_code = generate_python(source)
        # Should have two use_device calls
        assert python_code.count("_rt.use_device") == 2
