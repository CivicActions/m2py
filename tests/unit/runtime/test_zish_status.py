"""Tests for the $$STATUS^%ZISH implementation in zish_impl.py.

The STATUS function returns the $ZEOF status of the current device
as a MUMPS numeric string: "1" at EOF, "0" otherwise.

Key bugs fixed:
1. Used ``device._zeof`` (wrong attribute) instead of ``device.zeof``
2. Used ``str(bool)`` which returns "True"/"False" not "1"/"0" —
   MUMPS ``m_truth("True")`` returns False, causing infinite loops.

These tests validate the fix and edge cases.
"""

from unittest.mock import MagicMock


# Import the function under test
from tests.functional.munit.lib.zish_impl import STATUS

from m2py.runtime import MUMPSRuntime
from m2py.runtime.devices import FileDevice


class TestStatusBasic:
    """STATUS returns correct MUMPS numeric strings."""

    def test_status_returns_1_at_eof(self):
        """STATUS returns "1" when device.zeof is True."""
        rt = MUMPSRuntime()

        # Create a mock device with zeof=True
        mock_device = MagicMock()
        mock_device.zeof = True
        rt._current_device = mock_device

        result = STATUS(rt)
        assert result == "1"
        assert isinstance(result, str)

    def test_status_returns_0_not_at_eof(self):
        """STATUS returns "0" when device.zeof is False."""
        rt = MUMPSRuntime()

        mock_device = MagicMock()
        mock_device.zeof = False
        rt._current_device = mock_device

        result = STATUS(rt)
        assert result == "0"
        assert isinstance(result, str)

    def test_status_never_returns_true_false_strings(self):
        """STATUS must never return "True" or "False" (Python str(bool) bug)."""
        rt = MUMPSRuntime()

        for zeof_val in (True, False):
            mock_device = MagicMock()
            mock_device.zeof = zeof_val
            rt._current_device = mock_device

            result = STATUS(rt)
            assert result not in ("True", "False"), (
                f"STATUS returned '{result}' for zeof={zeof_val} — "
                "must return '1' or '0', not Python bool string"
            )

    def test_status_returns_mumps_truthful_values(self):
        """Returned values must be MUMPS-truthy/falsy correctly."""
        from m2py.codegen.helpers import m_truth

        rt = MUMPSRuntime()

        # zeof=True → "1" → m_truth("1") should be True
        mock_device = MagicMock()
        mock_device.zeof = True
        rt._current_device = mock_device
        assert m_truth(STATUS(rt)) is True

        # zeof=False → "0" → m_truth("0") should be False
        mock_device.zeof = False
        assert m_truth(STATUS(rt)) is False


class TestStatusWithRealDevices:
    """STATUS with actual FileDevice and PrincipalDevice instances."""

    def test_status_with_file_device_before_eof(self, tmp_path):
        """STATUS returns "0" for a readable file before EOF."""
        f = tmp_path / "test.txt"
        f.write_text("hello\n")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        rt = MUMPSRuntime()
        rt._current_device = dev

        assert STATUS(rt) == "0"
        file_obj.close()

    def test_status_with_file_device_at_eof(self, tmp_path):
        """STATUS returns "1" for a file device that has reached EOF."""
        f = tmp_path / "test.txt"
        f.write_text("hello\n")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        # Read past EOF
        dev.read()  # "hello"
        dev.read()  # EOF

        rt = MUMPSRuntime()
        rt._current_device = dev

        assert STATUS(rt) == "1"
        file_obj.close()

    def test_status_with_write_only_file_after_read(self, tmp_path):
        """STATUS returns "1" after reading from a write-only file (EOF)."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        # Reading from write-only file triggers EOF
        dev.read()

        rt = MUMPSRuntime()
        rt._current_device = dev

        assert STATUS(rt) == "1"
        file_obj.close()

    def test_status_with_principal_device(self):
        """STATUS returns "0" for the principal device (stdin not at EOF)."""
        rt = MUMPSRuntime()
        # Principal device should have zeof=False by default
        assert STATUS(rt) == "0"


class TestStatusEdgeCases:
    """Edge cases for STATUS function."""

    def test_status_no_current_device(self):
        """STATUS returns "0" when _current_device is None."""
        rt = MUMPSRuntime()
        rt._current_device = None  # type: ignore

        result = STATUS(rt)
        assert result == "0"

    def test_status_device_without_zeof(self):
        """STATUS returns "0" when device lacks zeof attribute (exception path)."""
        rt = MUMPSRuntime()
        rt._current_device = object()  # type: ignore  — no zeof attribute

        result = STATUS(rt)
        assert result == "0"

    def test_status_with_scope_param(self):
        """STATUS accepts optional _scope parameter."""
        rt = MUMPSRuntime()
        mock_device = MagicMock()
        mock_device.zeof = True
        rt._current_device = mock_device

        # Should work with or without _scope
        assert STATUS(rt, _scope={"IO": "/dev/null"}) == "1"
        assert STATUS(rt, _scope=None) == "1"
        assert STATUS(rt) == "1"
