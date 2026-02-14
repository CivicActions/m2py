"""Tests for FileDevice — file I/O device implementation.

Tests cover:
- FileDevice read/write/close with different modes
- Device parameter mapping (NEWVERSION, READONLY, APPEND, STREAM, RECORDSIZE)
- $ZEOF state tracking during reads
- $KEY for file reads ($C(10) for line-terminated, "" for EOF)
- $X/$Y per-device tracking with file writes
- OPEN/USE/CLOSE lifecycle via MUMPSRuntime
- DEVOPENFAIL error for non-existent files
- OPEN timeout/$TEST semantics

Spec 022: Phase 4 — US2, US3, US9, US10, US11
"""

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.devices import FileDevice
from m2py.runtime.exceptions import DeviceOpenFailError


# =============================================================================
# T028: FileDevice Unit Tests (read, write, append, close, mode mapping)
# =============================================================================


class TestFileDeviceWrite:
    """FileDevice write mode tests."""

    def test_write_newversion(self, tmp_path):
        """OPEN file:(NEWVERSION) creates/truncates file."""
        f = tmp_path / "test.txt"
        f.write_text("old content")

        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")
        dev.write("new content")
        dev.close()

        assert f.read_text() == "new content"

    def test_write_append(self, tmp_path):
        """OPEN file:(APPEND) appends to existing file."""
        f = tmp_path / "test.txt"
        f.write_text("line1\n")

        file_obj = open(f, "a")
        dev = FileDevice(str(f), file_obj, "a")
        dev.write("line2")
        dev.close()

        assert f.read_text() == "line1\nline2"

    def test_write_newline(self, tmp_path):
        """write_newline() outputs \\n, resets $X, increments $Y."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        dev.write("Hello")
        assert dev.x_pos == 5
        assert dev.y_pos == 0

        dev.write_newline()
        assert dev.x_pos == 0
        assert dev.y_pos == 1

        dev.close()
        assert f.read_text() == "Hello\n"

    def test_write_x_tracking(self, tmp_path):
        """write() tracks $X for printable characters only."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        dev.write("AB")
        assert dev.x_pos == 2

        # Control character (< 32) should NOT increment $X
        dev.write("\x07")  # BEL
        assert dev.x_pos == 2

        dev.close()

    def test_write_raw(self, tmp_path):
        """write_raw() writes data to file without tracking."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        dev.write_raw("raw data")
        dev.close()

        assert f.read_text() == "raw data"

    def test_write_tab(self, tmp_path):
        """write_tab() pads with spaces to reach column."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        dev.write("AB")  # $X = 2
        dev.write_tab(5)  # Pad to column 5
        assert dev.x_pos == 5

        dev.close()
        assert f.read_text() == "AB   "

    def test_write_formfeed(self, tmp_path):
        """write_formfeed() outputs conditional newline + formfeed."""
        f = tmp_path / "test.txt"
        file_obj = open(f, "w")
        dev = FileDevice(str(f), file_obj, "w")

        dev.write("AB")
        dev.write_formfeed()
        assert dev.x_pos == 0
        assert dev.y_pos == 0

        dev.close()
        content = f.read_text()
        # Should have: "AB" + newline (conditional) + formfeed
        assert content == "AB\n\x0c"


class TestFileDeviceRead:
    """FileDevice read mode tests."""

    def test_read_line(self, tmp_path):
        """read() returns line data with $C(10) key."""
        f = tmp_path / "test.txt"
        f.write_text("Hello\nWorld\n")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read()
        assert data == "Hello"
        assert key == chr(10)  # $C(10)
        assert dev.key == chr(10)
        assert dev.zeof is False

        data, key = dev.read()
        assert data == "World"
        assert key == chr(10)
        assert dev.zeof is False

        dev.close()

    def test_read_eof(self, tmp_path):
        """read() at EOF returns empty data, sets $ZEOF=1."""
        f = tmp_path / "test.txt"
        f.write_text("only line\n")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        dev.read()  # Read "only line"

        data, key = dev.read()  # EOF
        assert data == ""
        assert key == ""
        assert dev.key == ""
        assert dev.zeof is True

        dev.close()

    def test_read_maxlen(self, tmp_path):
        """read(maxlen=n) reads at most n characters."""
        f = tmp_path / "test.txt"
        f.write_text("ABCDEFGHIJ\n")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read(maxlen=3)
        assert data == "ABC"
        assert dev.zeof is False

        dev.close()

    def test_read_maxlen_with_newline(self, tmp_path):
        """read(maxlen=n) where newline falls within n chars.

        Python file.read(n) reads exactly n bytes without stopping at newlines.
        The newline is consumed as part of the bytes, and since it's the last
        char we check for, it gets stripped and $KEY is set to $C(10).
        """
        f = tmp_path / "test.txt"
        f.write_text("AB\nCD\n")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        # read(maxlen=3) reads "AB\n" — newline at end gets stripped
        data, key = dev.read(maxlen=3)
        assert data == "AB"
        assert key == chr(10)

        dev.close()

    def test_read_last_line_no_trailing_newline(self, tmp_path):
        """read() of last line without trailing newline still returns data."""
        f = tmp_path / "test.txt"
        f.write_text("last line")  # No trailing newline

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read()
        assert data == "last line"
        assert key == chr(10)  # Still $C(10) — line was terminated by EOF
        assert dev.zeof is False  # Not yet at EOF

        # Next read hits EOF
        data, key = dev.read()
        assert data == ""
        assert dev.zeof is True

        dev.close()

    def test_read_char(self, tmp_path):
        """read_char() reads single character from file."""
        f = tmp_path / "test.txt"
        f.write_text("ABC")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        assert dev.read_char() == "A"
        assert dev.read_char() == "B"
        assert dev.read_char() == "C"
        assert dev.read_char() == ""  # EOF
        assert dev.zeof is True

        dev.close()

    def test_read_empty_file(self, tmp_path):
        """read() on empty file immediately hits EOF."""
        f = tmp_path / "test.txt"
        f.write_text("")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        data, key = dev.read()
        assert data == ""
        assert key == ""
        assert dev.zeof is True

        dev.close()


class TestFileDeviceReadWrite:
    """FileDevice read-write mode tests."""

    def test_readwrite_mode(self, tmp_path):
        """read-write mode ("r+") supports both read and write."""
        f = tmp_path / "test.txt"
        f.write_text("Hello\n")

        file_obj = open(f, "r+")
        dev = FileDevice(str(f), file_obj, "r+")

        data, _ = dev.read()
        assert data == "Hello"

        dev.write("World")
        dev.close()

        # File should now contain "Hello\nWorld"
        assert f.read_text() == "Hello\nWorld"


class TestFileDeviceClose:
    """FileDevice close tests."""

    def test_close(self, tmp_path):
        """close() closes file handle."""
        f = tmp_path / "test.txt"
        f.write_text("")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        assert not file_obj.closed
        dev.close()
        assert file_obj.closed

    def test_close_already_closed(self, tmp_path):
        """close() on already-closed file is a no-op."""
        f = tmp_path / "test.txt"
        f.write_text("")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        dev.close()
        dev.close()  # Should not raise


class TestFileDeviceISVs:
    """FileDevice per-device ISV tracking tests."""

    def test_name(self, tmp_path):
        """FileDevice.name is the file path."""
        f = tmp_path / "test.txt"
        f.write_text("")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")
        assert dev.name == str(f)
        dev.close()

    def test_initial_isvs(self, tmp_path):
        """Initial ISV values: $X=0, $Y=0, $KEY="", $ZEOF=False."""
        f = tmp_path / "test.txt"
        f.write_text("")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        assert dev.x_pos == 0
        assert dev.y_pos == 0
        assert dev.key == ""
        assert dev.zeof is False

        dev.close()

    def test_key_after_read(self, tmp_path):
        """$KEY = $C(10) after line-terminated read, "" after EOF."""
        f = tmp_path / "test.txt"
        f.write_text("line1\n")

        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")

        dev.read()
        assert dev.key == chr(10)  # After reading "line1"

        dev.read()  # EOF
        assert dev.key == ""  # After EOF

        dev.close()

    def test_stream_mode(self, tmp_path):
        """STREAM parameter is stored on device."""
        f = tmp_path / "test.txt"
        f.write_text("")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")
        dev._stream = True
        assert dev._stream is True
        dev.close()

    def test_record_size(self, tmp_path):
        """RECORDSIZE parameter is stored on device."""
        f = tmp_path / "test.txt"
        f.write_text("")
        file_obj = open(f, "r")
        dev = FileDevice(str(f), file_obj, "r")
        dev._record_size = 132
        assert dev._record_size == 132
        dev.close()


# =============================================================================
# T029: Device Parameter Tests (via MUMPSRuntime.open_device)
# =============================================================================


class TestOpenDeviceParams:
    """open_device() parameter mapping tests."""

    def test_open_newversion(self, tmp_path):
        """NEWVERSION creates/truncates file."""
        f = tmp_path / "test.txt"
        f.write_text("old")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))
        rt.write("new")
        rt.close_device(str(f))

        assert f.read_text() == "new"

    def test_open_readonly(self, tmp_path):
        """READONLY opens for reading."""
        f = tmp_path / "test.txt"
        f.write_text("data\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))
        # Device is open — we can read from it via the device table
        dev = rt._device_table[str(f)]
        data, _ = dev.read()
        assert data == "data"
        rt.close_device(str(f))

    def test_open_append(self, tmp_path):
        """APPEND opens for appending."""
        f = tmp_path / "test.txt"
        f.write_text("line1\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["APPEND"])
        rt.use_device(str(f))
        rt.write("line2")
        rt.close_device(str(f))

        assert f.read_text() == "line1\nline2"

    def test_open_write_rw(self, tmp_path):
        """WRITE (alias RW) opens in read-write mode."""
        f = tmp_path / "test.txt"
        f.write_text("Hello\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["WRITE"])
        assert str(f) in rt._device_table
        rt.close_device(str(f))

    def test_open_case_insensitive(self, tmp_path):
        """Device parameters are case-insensitive."""
        f = tmp_path / "test.txt"
        f.write_text("old")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["newversion"])
        rt.use_device(str(f))
        rt.write("new")
        rt.close_device(str(f))

        assert f.read_text() == "new"

    def test_open_wn_alias(self, tmp_path):
        """WN is shorthand for NEWVERSION."""
        f = tmp_path / "test.txt"
        f.write_text("old")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["WN"])
        rt.use_device(str(f))
        rt.write("new")
        rt.close_device(str(f))

        assert f.read_text() == "new"

    def test_open_stream_param(self, tmp_path):
        """STREAM parameter is stored on FileDevice."""
        f = tmp_path / "test.txt"
        f.write_text("")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY", "STREAM"])
        dev = rt._device_table[str(f)]
        assert dev._stream is True
        rt.close_device(str(f))

    def test_open_recordsize_param(self, tmp_path):
        """RECORDSIZE=n parameter is stored on FileDevice."""
        f = tmp_path / "test.txt"
        f.write_text("")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY", "RECORDSIZE=132"])
        dev = rt._device_table[str(f)]
        assert dev._record_size == 132
        rt.close_device(str(f))

    def test_open_already_open_noop(self, tmp_path):
        """Re-opening an already-open device is a no-op."""
        f = tmp_path / "test.txt"
        f.write_text("data")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        result = rt.open_device(str(f), ["NEWVERSION"])  # Should be no-op
        assert result is True
        # Original file content unchanged
        rt.close_device(str(f))
        assert f.read_text() == "data"

    def test_open_devopenfail_not_found(self, tmp_path):
        """OPEN non-existent file raises DEVOPENFAIL."""
        rt = MUMPSRuntime()
        with pytest.raises(DeviceOpenFailError) as exc_info:
            rt.open_device(str(tmp_path / "nonexistent.txt"), ["READONLY"])
        assert exc_info.value.code == "DEVOPENFAIL"
        assert "file not found" in exc_info.value.reason

    def test_open_devopenfail_ignores_timeout(self, tmp_path):
        """DEVOPENFAIL is raised regardless of timeout (YDB-validated)."""
        rt = MUMPSRuntime()
        with pytest.raises(DeviceOpenFailError):
            rt.open_device(str(tmp_path / "nonexistent.txt"), ["READONLY"], timeout=5)

    def test_open_default_readonly(self, tmp_path):
        """Default mode (no params) is read-only."""
        f = tmp_path / "test.txt"
        f.write_text("data\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f))
        dev = rt._device_table[str(f)]
        assert dev._mode == "r"
        rt.close_device(str(f))


# =============================================================================
# T030: $ZEOF Unit Tests
# =============================================================================


class TestZEOFTracking:
    """$ZEOF state tracking tests."""

    def test_zeof_before_read(self, tmp_path):
        """$ZEOF = 0 before any read."""
        f = tmp_path / "test.txt"
        f.write_text("line1\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))

        assert rt.zeof() == 0

        rt.close_device(str(f))

    def test_zeof_during_reads(self, tmp_path):
        """$ZEOF = 0 during reads that return data."""
        f = tmp_path / "test.txt"
        f.write_text("line1\nline2\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))

        dev = rt._device_table[str(f)]
        dev.read()
        assert rt.zeof() == 0

        dev.read()
        assert rt.zeof() == 0

        rt.close_device(str(f))

    def test_zeof_after_eof(self, tmp_path):
        """$ZEOF = 1 after reading past last data."""
        f = tmp_path / "test.txt"
        f.write_text("only\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))

        dev = rt._device_table[str(f)]
        dev.read()  # Read "only"
        assert rt.zeof() == 0

        dev.read()  # EOF
        assert rt.zeof() == 1

        rt.close_device(str(f))

    def test_zeof_reset_on_new_file(self, tmp_path):
        """$ZEOF resets to 0 when opening a new file."""
        f1 = tmp_path / "file1.txt"
        f1.write_text("line\n")
        f2 = tmp_path / "file2.txt"
        f2.write_text("data\n")

        rt = MUMPSRuntime()

        # Read to EOF on file1
        rt.open_device(str(f1), ["READONLY"])
        rt.use_device(str(f1))
        dev1 = rt._device_table[str(f1)]
        dev1.read()
        dev1.read()  # EOF
        assert rt.zeof() == 1

        # Open and USE file2 — $ZEOF is per-device, so new device starts at 0
        rt.open_device(str(f2), ["READONLY"])
        rt.use_device(str(f2))
        assert rt.zeof() == 0

        rt.close_device(str(f1))
        rt.close_device(str(f2))

    def test_zeof_principal_device(self):
        """$ZEOF on $PRINCIPAL is always 0."""
        rt = MUMPSRuntime()
        assert rt.zeof() == 0


# =============================================================================
# T025: $X/$Y per-device tracking assertion tests
# =============================================================================


class TestPerDeviceXYTracking:
    """$X/$Y track independently per device."""

    def test_write_updates_file_device_xy(self, tmp_path):
        """WRITE on file device updates that device's $X."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))

        rt.write("AB")
        assert rt.x() == 2
        assert rt.y() == 0

        rt.close_device(str(f))

    def test_use_switches_xy_context(self, tmp_path):
        """USE switches $X/$Y to the target device's values."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])

        # Write to principal
        rt.write("ABC")
        assert rt.x() == 3

        # Switch to file device — $X should be 0 (fresh device)
        rt.use_device(str(f))
        assert rt.x() == 0

        # Write on file device
        rt.write("XY")
        assert rt.x() == 2

        # Switch back to principal — $X should be 3 (preserved)
        rt.use_device("0")
        assert rt.x() == 3

        rt.close_device(str(f))

    def test_y_tracks_per_device(self, tmp_path):
        """$Y incremented per device on write_newline."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])

        # Principal: write newlines
        rt.write_newline()
        rt.write_newline()
        assert rt.y() == 2

        # File: fresh $Y=0
        rt.use_device(str(f))
        assert rt.y() == 0
        rt.write_newline()
        assert rt.y() == 1

        # Back to principal — $Y=2 preserved
        rt.use_device("0")
        assert rt.y() == 2

        rt.close_device(str(f))


# =============================================================================
# T026: $KEY for file reads — $C(10) for line-terminated, "" for EOF
# =============================================================================


class TestFileDeviceKey:
    """$KEY tracking for file reads."""

    def test_key_after_line_read(self, tmp_path):
        """$KEY = $C(10) after reading a complete line."""
        f = tmp_path / "test.txt"
        f.write_text("Hello\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))

        dev = rt._device_table[str(f)]
        dev.read()
        assert rt.key() == chr(10)

        rt.close_device(str(f))

    def test_key_after_eof(self, tmp_path):
        """$KEY = "" after reading at EOF."""
        f = tmp_path / "test.txt"
        f.write_text("data\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))

        dev = rt._device_table[str(f)]
        dev.read()  # "data"
        dev.read()  # EOF
        assert rt.key() == ""

        rt.close_device(str(f))

    def test_key_per_device(self, tmp_path):
        """$KEY is per-device — switching USE switches $KEY context."""
        f1 = tmp_path / "file1.txt"
        f1.write_text("line1\n")
        f2 = tmp_path / "file2.txt"
        f2.write_text("line2\n")

        rt = MUMPSRuntime()
        rt.open_device(str(f1), ["READONLY"])
        rt.open_device(str(f2), ["READONLY"])

        # Read from file1 — sets $KEY on file1
        rt.use_device(str(f1))
        dev1 = rt._device_table[str(f1)]
        dev1.read()
        assert rt.key() == chr(10)

        # Read EOF on file2 — sets $KEY on file2
        rt.use_device(str(f2))
        dev2 = rt._device_table[str(f2)]
        dev2.read()
        dev2.read()  # EOF
        assert rt.key() == ""

        # Switch back to file1 — $KEY should be chr(10) (preserved)
        rt.use_device(str(f1))
        assert rt.key() == chr(10)

        rt.close_device(str(f1))
        rt.close_device(str(f2))


# =============================================================================
# T027: $IO tracking assertion tests
# =============================================================================


class TestIOTrackingWithFiles:
    """$IO tracking during file OPEN/USE/CLOSE."""

    def test_io_during_use(self, tmp_path):
        """$IO = file path during USE of file device."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])

        assert rt.io() == "0"

        rt.use_device(str(f))
        assert rt.io() == str(f)

        rt.close_device(str(f))

    def test_io_after_close(self, tmp_path):
        """$IO = "0" after CLOSE of current device."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))

        assert rt.io() == str(f)

        rt.close_device(str(f))
        assert rt.io() == "0"

    def test_io_after_use_zero(self, tmp_path):
        """$IO = "0" after USE 0."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))

        rt.use_device("0")
        assert rt.io() == "0"

        rt.close_device(str(f))

    def test_close_non_current_preserves_io(self, tmp_path):
        """CLOSE of a non-current device doesn't change $IO."""
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"

        rt = MUMPSRuntime()
        rt.open_device(str(f1), ["NEWVERSION"])
        rt.open_device(str(f2), ["NEWVERSION"])

        rt.use_device(str(f1))
        assert rt.io() == str(f1)

        rt.close_device(str(f2))  # Close non-current
        assert rt.io() == str(f1)  # Unchanged

        rt.close_device(str(f1))


# =============================================================================
# T031: File I/O Integration Tests (OPEN → USE → WRITE → CLOSE → OPEN → READ)
# =============================================================================


class TestFileIOEndToEnd:
    """End-to-end file I/O lifecycle tests."""

    def test_write_then_read(self, tmp_path):
        """Write to file, close, reopen for reading, verify content."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()

        # Write
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))
        rt.write("Hello")
        rt.write_newline()
        rt.write("World")
        rt.write_newline()
        rt.close_device(str(f))

        # Read back
        rt.open_device(str(f), ["READONLY"])
        rt.use_device(str(f))
        dev = rt._device_table[str(f)]

        data1, _ = dev.read()
        assert data1 == "Hello"

        data2, _ = dev.read()
        assert data2 == "World"

        data3, _ = dev.read()
        assert data3 == ""
        assert dev.zeof is True

        rt.close_device(str(f))

    def test_append_to_existing(self, tmp_path):
        """Append to existing file preserves original content."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()

        # Create
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))
        rt.write("line1")
        rt.write_newline()
        rt.close_device(str(f))

        # Append
        rt.open_device(str(f), ["APPEND"])
        rt.use_device(str(f))
        rt.write("line2")
        rt.write_newline()
        rt.close_device(str(f))

        # Verify
        assert f.read_text() == "line1\nline2\n"

    def test_principal_output_unaffected(self, tmp_path):
        """Writing to file does not affect principal output."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()

        rt.write("principal1")
        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))
        rt.write("file data")
        rt.use_device("0")
        rt.write("principal2")
        rt.close_device(str(f))

        # Principal output should only have principal writes
        assert rt.get_output() == "principal1principal2"
        # File should only have file writes
        assert f.read_text() == "file data"

    def test_close_reverts_to_principal(self, tmp_path):
        """CLOSE of current device switches I/O to principal."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()

        rt.open_device(str(f), ["NEWVERSION"])
        rt.use_device(str(f))
        rt.close_device(str(f))

        # Now on principal
        rt.write("after close")
        assert rt.get_output() == "after close"

    def test_multiple_files(self, tmp_path):
        """Multiple files open simultaneously."""
        f1 = tmp_path / "file1.txt"
        f2 = tmp_path / "file2.txt"
        rt = MUMPSRuntime()

        rt.open_device(str(f1), ["NEWVERSION"])
        rt.open_device(str(f2), ["NEWVERSION"])

        rt.use_device(str(f1))
        rt.write("file1 data")

        rt.use_device(str(f2))
        rt.write("file2 data")

        rt.close_device(str(f1))
        rt.close_device(str(f2))

        assert f1.read_text() == "file1 data"
        assert f2.read_text() == "file2 data"

    def test_close_principal_noop(self):
        """CLOSE 0 is a no-op."""
        rt = MUMPSRuntime()
        rt.close_device("0")  # Should not raise
        assert rt.io() == "0"

    def test_use_after_close_errors(self, tmp_path):
        """USE of closed device falls through (legacy compat)."""
        f = tmp_path / "test.txt"
        rt = MUMPSRuntime()
        rt.open_device(str(f), ["NEWVERSION"])
        rt.close_device(str(f))

        # USE of a closed device — not in device_table, not in _devices
        # Currently falls through silently (legacy behavior)
        rt.use_device(str(f))
        # $IO should still be on whatever it was before
