"""Unit tests for PrincipalDevice.

Tests the principal device ($PRINCIPAL, device "0") which wraps
stdin/stdout and provides the same I/O behavior as the pre-Phase-4
runtime.

Spec 022: Phase 4 — T012 (US4)
"""

from m2py.runtime import MUMPSRuntime
from m2py.runtime.devices import PrincipalDevice


class TestPrincipalDeviceInit:
    """Test PrincipalDevice initialization."""

    def test_name_is_zero(self):
        """PrincipalDevice name is '0'."""
        dev = PrincipalDevice()
        assert dev.name == "0"

    def test_initial_x_pos(self):
        """$X starts at 0."""
        dev = PrincipalDevice()
        assert dev.x_pos == 0

    def test_initial_y_pos(self):
        """$Y starts at 0."""
        dev = PrincipalDevice()
        assert dev.y_pos == 0

    def test_initial_key(self):
        """$KEY starts empty."""
        dev = PrincipalDevice()
        assert dev.key == ""

    def test_initial_zeof(self):
        """$ZEOF starts False."""
        dev = PrincipalDevice()
        assert dev.zeof is False


class TestPrincipalDeviceWrite:
    """Test PrincipalDevice write operations."""

    def test_write_appends_to_output(self):
        """Write appends data to runtime _output list."""
        rt = MUMPSRuntime()
        rt.write("hello")
        assert "hello" in rt._output

    def test_write_tracks_x_printable(self):
        """$X increments for printable characters (ord >= 32)."""
        rt = MUMPSRuntime()
        rt.write("abc")
        assert rt.x() == 3

    def test_write_x_ignores_control_chars(self):
        """$X does NOT increment for control characters (ord < 32)."""
        rt = MUMPSRuntime()
        rt.write("\x01\x02\x03")
        assert rt.x() == 0

    def test_write_x_mixed(self):
        """$X increments only for printable chars in mixed content."""
        rt = MUMPSRuntime()
        rt.write("A\x00B")
        assert rt.x() == 2

    def test_write_does_not_affect_y(self):
        """$Y is NOT changed by write() — only by format controls."""
        rt = MUMPSRuntime()
        rt.write("hello\nworld")
        assert rt.y() == 0

    def test_write_none_is_empty(self):
        """Writing None produces empty string."""
        rt = MUMPSRuntime()
        rt.write(None)
        assert rt.get_output() == ""

    def test_write_accumulates(self):
        """Multiple writes accumulate."""
        rt = MUMPSRuntime()
        rt.write("a")
        rt.write("b")
        rt.write("c")
        assert rt.get_output() == "abc"


class TestPrincipalDeviceWriteNewline:
    """Test PrincipalDevice write_newline (W !)."""

    def test_newline_resets_x(self):
        """W ! resets $X to 0."""
        rt = MUMPSRuntime()
        rt.write("hello")
        assert rt.x() == 5
        rt.write_newline()
        assert rt.x() == 0

    def test_newline_increments_y(self):
        """W ! increments $Y by 1."""
        rt = MUMPSRuntime()
        rt.write_newline()
        assert rt.y() == 1
        rt.write_newline()
        assert rt.y() == 2

    def test_newline_appends_newline_char(self):
        """W ! outputs newline character."""
        rt = MUMPSRuntime()
        rt.write("hi")
        rt.write_newline()
        assert rt.get_output() == "hi\n"


class TestPrincipalDeviceFormfeed:
    """Test PrincipalDevice write_formfeed (W #)."""

    def test_formfeed_resets_x_and_y(self):
        """W # resets both $X and $Y to 0."""
        rt = MUMPSRuntime()
        rt.write("hello")
        rt.write_newline()
        rt.write_formfeed()
        assert rt.x() == 0
        assert rt.y() == 0

    def test_formfeed_conditional_newline(self):
        """W # adds newline first if $X > 0."""
        rt = MUMPSRuntime()
        rt.write("hello")
        rt.write_formfeed()
        output = rt.get_output()
        assert output == "hello\n\x0c"

    def test_formfeed_no_newline_at_column_zero(self):
        """W # does NOT add newline if $X == 0."""
        rt = MUMPSRuntime()
        rt.write_formfeed()
        output = rt.get_output()
        assert output == "\x0c"


class TestPrincipalDeviceTab:
    """Test PrincipalDevice write_tab (W ?n)."""

    def test_tab_pads_with_spaces(self):
        """W ?5 pads with spaces to column 5."""
        rt = MUMPSRuntime()
        rt.write_tab(5)
        assert rt.get_output() == "     "
        assert rt.x() == 5

    def test_tab_noop_when_past_column(self):
        """W ?3 is no-op if already at or past column 3."""
        rt = MUMPSRuntime()
        rt.write("hello")  # $X = 5
        rt.write_tab(3)
        assert rt.get_output() == "hello"

    def test_tab_from_mid_column(self):
        """W ?10 from column 3 pads with 7 spaces."""
        rt = MUMPSRuntime()
        rt.write("abc")  # $X = 3
        rt.write_tab(10)
        assert rt.x() == 10


class TestPrincipalDeviceClear:
    """Test PrincipalDevice clear."""

    def test_clear_empties_output(self):
        """clear() removes all accumulated output."""
        rt = MUMPSRuntime()
        rt.write("hello")
        rt.write_newline()
        rt.clear()
        assert rt.get_output() == ""

    def test_clear_resets_x_y(self):
        """clear() resets $X and $Y to 0."""
        rt = MUMPSRuntime()
        rt.write("hello")
        rt.write_newline()
        rt.clear()
        assert rt.x() == 0
        assert rt.y() == 0


class TestPrincipalDeviceClose:
    """Test PrincipalDevice close."""

    def test_close_is_noop(self):
        """Closing $PRINCIPAL is a no-op."""
        rt = MUMPSRuntime()
        dev = rt._principal_device
        dev.close()  # Should not raise
        # Device still works
        rt.write("after close")
        assert "after close" in rt.get_output()


class TestPrincipalDeviceViaRuntime:
    """Test PrincipalDevice integration with MUMPSRuntime."""

    def test_runtime_has_principal_device(self):
        """Runtime creates PrincipalDevice on init."""
        rt = MUMPSRuntime()
        assert rt._principal_device is not None
        assert isinstance(rt._principal_device, PrincipalDevice)

    def test_current_device_is_principal(self):
        """Default current device is PrincipalDevice."""
        rt = MUMPSRuntime()
        assert rt._current_device is rt._principal_device

    def test_device_table_has_principal(self):
        """Device table contains '0' → PrincipalDevice."""
        rt = MUMPSRuntime()
        assert "0" in rt._device_table
        assert rt._device_table["0"] is rt._principal_device

    def test_legacy_output_compatibility(self):
        """rt._output = [] still works (backward compat)."""
        rt = MUMPSRuntime()
        rt._output = []
        rt.write("test")
        assert "test" in rt._output

    def test_io_returns_zero_for_principal(self):
        """$IO returns '0' for principal device."""
        rt = MUMPSRuntime()
        assert rt.io() == "0"

    def test_principal_returns_zero(self):
        """$PRINCIPAL returns '0'."""
        rt = MUMPSRuntime()
        assert rt.principal() == "0"

    def test_zeof_returns_zero_for_principal(self):
        """$ZEOF returns 0 for principal device."""
        rt = MUMPSRuntime()
        assert rt.zeof() == 0

    def test_key_initially_empty(self):
        """$KEY is empty initially."""
        rt = MUMPSRuntime()
        assert rt.key() == ""
