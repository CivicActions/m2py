"""Tests for device-routed READ methods on MUMPSRuntime.

Spec 022 Phase 9 Gap 1 (T103): Validates that READ operations route
through the current device, so that after USE "file", READ X reads
from the file, not stdin.
"""

from __future__ import annotations


from m2py.runtime import MUMPSRuntime


class TestReadLineFromPrincipal:
    """Test read_line() from the principal device (stdin)."""

    def test_read_line_returns_string(self, monkeypatch):
        """read_line() returns input from current device."""
        rt = MUMPSRuntime()
        # Monkey-patch the principal device's read to avoid stdin
        rt._principal_device.read = lambda **kw: ("hello", "\r")
        result = rt.read_line()
        assert result == "hello"

    def test_read_line_timeout_success(self):
        """read_line_timeout returns (data, 1) on success."""
        rt = MUMPSRuntime()
        rt._principal_device.read = lambda **kw: ("data", "\r")
        data, test = rt.read_line_timeout(5.0)
        assert data == "data"
        assert test == 1

    def test_read_line_timeout_expired(self):
        """read_line_timeout returns ('', 0) on timeout."""
        rt = MUMPSRuntime()
        rt._principal_device.read = lambda **kw: ("", "")
        data, test = rt.read_line_timeout(0.01)
        assert data == ""
        assert test == 0

    def test_read_char_returns_ascii_code(self):
        """read_char() returns ASCII code as string."""
        rt = MUMPSRuntime()
        rt._principal_device.read_char = lambda: "A"
        result = rt.read_char()
        assert result == "65"

    def test_read_char_eof_returns_minus_one(self):
        """read_char() returns '-1' on EOF."""
        rt = MUMPSRuntime()
        rt._principal_device.read_char = lambda: ""
        result = rt.read_char()
        assert result == "-1"

    def test_read_maxlen(self):
        """read_maxlen(n) returns (data, key) from current device."""
        rt = MUMPSRuntime()
        rt._principal_device.read = lambda **kw: ("hel", "")
        data, key = rt.read_maxlen(3)
        assert data == "hel"
        assert key == ""

    def test_read_maxlen_timeout_success(self):
        """read_maxlen_timeout returns (data, key, 1) on success."""
        rt = MUMPSRuntime()
        rt._principal_device.read = lambda **kw: ("ab", "\n")
        data, key, test = rt.read_maxlen_timeout(5, 10.0)
        assert data == "ab"
        assert key == "\n"
        assert test == 1

    def test_read_maxlen_timeout_expired(self):
        """read_maxlen_timeout returns ('', '', 0) on timeout."""
        rt = MUMPSRuntime()
        rt._principal_device.read = lambda **kw: ("", "")
        data, key, test = rt.read_maxlen_timeout(5, 0.01)
        assert data == ""
        assert key == ""
        assert test == 0


class TestReadFromFileDevice:
    """Test that READ routes through FileDevice after USE."""

    def test_read_line_from_file(self, tmp_path):
        """After USE file, read_line() reads from the file, not stdin."""
        # Create a file with content
        test_file = tmp_path / "test.txt"
        test_file.write_text("line1\nline2\nline3\n")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        # read_line should read from the file
        result = rt.read_line()
        assert result == "line1"

        result2 = rt.read_line()
        assert result2 == "line2"

    def test_read_line_updates_key_on_device(self, tmp_path):
        """read_line() updates $KEY on the current device, not _rt._key."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello\n")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        rt.read_line()
        # $KEY should reflect the file device's key, not _rt._key
        # FileDevice sets key to "\n" for newline-terminated lines
        assert rt.key() != ""  # key accessor reads from current device

    def test_read_maxlen_from_file(self, tmp_path):
        """read_maxlen reads limited chars from file device."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("abcdefgh\n")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        data, key = rt.read_maxlen(3)
        assert data == "abc"

    def test_read_switches_back_to_principal(self, tmp_path):
        """After USE 0, reads go back to principal device."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("file_data\n")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        # Read from file
        file_result = rt.read_line()
        assert file_result == "file_data"

        # Switch back to principal
        rt.use_device("0")

        # Now reads should go to principal again
        assert rt._current_device is rt._principal_device

    def test_read_char_from_file(self, tmp_path):
        """read_char() reads single char from file and returns ASCII code."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("A")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        result = rt.read_char()
        assert result == "65"  # ASCII code of 'A'

    def test_read_tracks_zeof(self, tmp_path):
        """$ZEOF is set when file is exhausted."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("only\n")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        rt.read_line()  # Read the only line
        # After reading past EOF, $ZEOF should be set
        rt.read_line()  # This should hit EOF
        assert rt._current_device.zeof is True


class TestReadLineTimeoutFromFile:
    """Test read_line_timeout with file devices."""

    def test_file_read_timeout_returns_data(self, tmp_path):
        """File reads always succeed immediately, so timeout returns (data, 1)."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("data\n")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        data, test = rt.read_line_timeout(5.0)
        assert data == "data"
        assert test == 1

    def test_file_read_timeout_eof(self, tmp_path):
        """At EOF, file read returns empty data."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("")

        rt = MUMPSRuntime()
        rt.open_device(str(test_file), ["READONLY"], None)
        rt.use_device(str(test_file))

        data, test = rt.read_line_timeout(5.0)
        # At EOF: empty data, depends on device implementation
        # FileDevice returns ("", "") at EOF
        assert data == ""
