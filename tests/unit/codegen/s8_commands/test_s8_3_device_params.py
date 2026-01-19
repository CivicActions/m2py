"""Tests for §8.3 device parameters code generation.

Reference: MUMPS 1995 ANSI Standard, Section 8.3
"""

import pytest


@pytest.mark.codegen
class TestDeviceParamsCodegen:
    """Codegen-level tests for device parameters code generation (§8.3)."""

    def test_open_with_device_params(self, generate_python):
        """OPEN with device parameters generates proper Python call (§8.3).

        Per MUMPS spec: OPEN device:(params) passes parameters to device handler.
        Device parameters like NEWVERSION, READONLY, etc. are treated as string
        keywords in the generated code.
        """
        mumps = 'TEST O "file.txt":(NEWVERSION) Q'
        python = generate_python(mumps)
        # Should generate open_device call with params list
        assert "_rt.open_device(" in python
        assert '["NEWVERSION"]' in python or "['NEWVERSION']" in python

    def test_open_with_multiple_device_params(self, generate_python):
        """OPEN with multiple device parameters (§8.3)."""
        mumps = 'TEST O "file.txt":(NEWVERSION:NOWRAP) Q'
        python = generate_python(mumps)
        assert "_rt.open_device(" in python
        # Both params should be in the list
        assert "NEWVERSION" in python
        assert "NOWRAP" in python

    def test_close_with_device_params(self, generate_python):
        """CLOSE with device parameters generates proper Python call (§8.3)."""
        mumps = 'TEST C "file.txt":DELETE Q'
        python = generate_python(mumps)
        assert "_rt.close_device(" in python
        assert "DELETE" in python

    def test_use_with_device_params(self, generate_python):
        """USE with device parameters generates proper Python call (§8.3)."""
        mumps = 'TEST U "file.txt":(NOWRAP) Q'
        python = generate_python(mumps)
        assert "_rt.use_device(" in python
        assert "NOWRAP" in python
