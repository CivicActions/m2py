"""Unit tests for device abstraction layer.

Tests the device table, current_device switching, USE command behavior,
and device lifecycle management.

Spec 022: Phase 4 — T013 (US4)
"""

import pytest
from m2py.runtime import MUMPSRuntime
from m2py.runtime.devices import MUMPSDevice, PrincipalDevice


class TestDeviceTable:
    """Test device table initialization and management."""

    def test_device_table_contains_principal(self):
        """Device table has '0' mapped to PrincipalDevice at startup."""
        rt = MUMPSRuntime()
        assert "0" in rt._device_table
        assert isinstance(rt._device_table["0"], PrincipalDevice)

    def test_current_device_starts_as_principal(self):
        """Current device is PrincipalDevice at startup."""
        rt = MUMPSRuntime()
        assert rt._current_device is rt._principal_device

    def test_principal_cannot_be_closed(self):
        """CLOSE '0' is a no-op — $PRINCIPAL cannot be closed."""
        rt = MUMPSRuntime()
        rt.close_device("0")
        assert "0" in rt._device_table
        assert rt._current_device is rt._principal_device
        assert rt.io() == "0"


class TestUseDevice:
    """Test USE command (device switching)."""

    def test_use_zero_stays_principal(self):
        """USE 0 keeps current device as principal."""
        rt = MUMPSRuntime()
        rt.use_device("0")
        assert rt._current_device is rt._principal_device
        assert rt.io() == "0"

    def test_use_principal_string(self):
        """USE $P (principal device name) switches to principal."""
        rt = MUMPSRuntime()
        # Simulate being on a different device first
        from m2py.runtime.devices import PrincipalDevice

        mock_dev = PrincipalDevice(runtime=rt)
        mock_dev.name = "some_device"
        rt._device_table["some_device"] = mock_dev
        rt._current_device = mock_dev
        rt.use_device("0")
        assert rt.io() == "0"
        assert rt._current_device is rt._principal_device

    def test_use_syncs_x_y(self):
        """USE syncs $X/$Y from the target device."""
        rt = MUMPSRuntime()
        # Write to principal to set $X
        rt.write("hello")
        assert rt.x() == 5
        # USE 0 should keep $X consistent
        rt.use_device("0")
        assert rt.x() == rt._current_device.x_pos


class TestCloseDevice:
    """Test CLOSE command behavior."""

    def test_close_principal_is_noop(self):
        """CLOSE on $PRINCIPAL does nothing."""
        rt = MUMPSRuntime()
        rt.close_device("0")
        # Still works
        rt.write("still works")
        assert "still works" in rt.get_output()

    def test_close_nonexistent_device_no_error(self):
        """CLOSE on non-existent device doesn't raise."""
        rt = MUMPSRuntime()
        rt.close_device("nonexistent")  # Should not raise


class TestIOTracking:
    """Test $IO tracking during device operations."""

    def test_io_starts_at_zero(self):
        """$IO starts at '0'."""
        rt = MUMPSRuntime()
        assert rt.io() == "0"

    def test_use_updates_io(self):
        """USE updates $IO."""
        rt = MUMPSRuntime()
        # Create a device entry in device_table
        from m2py.runtime.devices import PrincipalDevice

        mock_dev = PrincipalDevice(runtime=rt)
        mock_dev.name = "test_dev"
        rt._device_table["test_dev"] = mock_dev
        rt.use_device("test_dev")
        assert rt.io() == "test_dev"

    def test_close_reverts_io_to_zero(self):
        """CLOSE current device reverts $IO to '0'."""
        rt = MUMPSRuntime()
        # Set up a device in device_table
        from m2py.runtime.devices import PrincipalDevice

        mock_dev = PrincipalDevice(runtime=rt)
        mock_dev.name = "test_dev"
        rt._device_table["test_dev"] = mock_dev
        rt.use_device("test_dev")
        assert rt.io() == "test_dev"
        rt.close_device("test_dev")
        assert rt.io() == "0"


class TestXYPerDevice:
    """Test $X/$Y per-device tracking."""

    def test_x_tracks_current_device(self):
        """$X returns current device's x_pos."""
        rt = MUMPSRuntime()
        rt.write("abc")
        assert rt.x() == 3

    def test_y_tracks_current_device(self):
        """$Y returns current device's y_pos."""
        rt = MUMPSRuntime()
        rt.write_newline()
        rt.write_newline()
        assert rt.y() == 2

    def test_x_y_reset_on_clear(self):
        """clear() resets $X and $Y."""
        rt = MUMPSRuntime()
        rt.write("hello")
        rt.write_newline()
        rt.clear()
        assert rt.x() == 0
        assert rt.y() == 0


class TestKeyPerDevice:
    """Test $KEY per-device tracking."""

    def test_key_starts_empty(self):
        """$KEY starts empty."""
        rt = MUMPSRuntime()
        assert rt.key() == ""

    def test_key_returns_current_device_key(self):
        """$KEY returns the current device's key value."""
        rt = MUMPSRuntime()
        rt._current_device.key = "\r"
        assert rt.key() == "\r"


class TestZeofAccessor:
    """Test $ZEOF accessor."""

    def test_zeof_starts_zero(self):
        """$ZEOF returns 0 initially."""
        rt = MUMPSRuntime()
        assert rt.zeof() == 0

    def test_zeof_returns_one_when_set(self):
        """$ZEOF returns 1 when device is at EOF."""
        rt = MUMPSRuntime()
        rt._current_device.zeof = True
        assert rt.zeof() == 1

    def test_zeof_returns_int(self):
        """$ZEOF returns int (not bool)."""
        rt = MUMPSRuntime()
        result = rt.zeof()
        assert isinstance(result, int)


class TestMUMPSDeviceABC:
    """Test MUMPSDevice abstract base class."""

    def test_cannot_instantiate_abc(self):
        """MUMPSDevice is abstract — cannot instantiate directly."""
        with pytest.raises(TypeError):
            MUMPSDevice("test")

    def test_subclass_must_implement_read(self):
        """Subclass must implement read()."""

        class BadDevice(MUMPSDevice):
            def read_char(self) -> str:
                return ""

            def write(self, data: str) -> None:
                pass

            def write_newline(self) -> None:
                pass

            def close(self) -> None:
                pass

        with pytest.raises(TypeError):
            BadDevice("test")

    def test_concrete_subclass_works(self):
        """Fully implemented subclass can be instantiated."""

        class TestDevice(MUMPSDevice):
            def read(self, maxlen=None, timeout=None):
                return ("", "")

            def read_char(self) -> str:
                return ""

            def write(self, data: str) -> None:
                pass

            def write_newline(self) -> None:
                pass

            def close(self) -> None:
                pass

        dev = TestDevice("test_dev")
        assert dev.name == "test_dev"
        assert dev.x_pos == 0
        assert dev.y_pos == 0
        assert dev.key == ""
        assert dev.zeof is False
