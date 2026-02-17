"""Unit tests for device classes — TCPDevice, PrincipalDevice read paths, FileDevice edges.

Tests uncovered code paths in m2py.runtime.devices:
- TCPDevice: read, read_char, write, write_newline, write_raw, close, _recv_line
- PrincipalDevice: _read_maxlen_timeout, _read_timeout, write_raw
- FileDevice: write_raw, close edge cases
- MUMPSDevice: write_raw default implementation
"""

from __future__ import annotations

import socket
from unittest.mock import MagicMock, patch

import pytest

from m2py.runtime.devices import (
    FileDevice,
    MUMPSDevice,
    PrincipalDevice,
    TCPDevice,
)


# =============================================================================
# TCPDevice Tests
# =============================================================================


class TestTCPDevice:
    """Tests for TCPDevice socket-based I/O."""

    @pytest.fixture
    def mock_socket(self):
        """Create a mock socket."""
        sock = MagicMock(spec=socket.socket)
        sock.recv = MagicMock()
        sock.sendall = MagicMock()
        sock.close = MagicMock()
        sock.settimeout = MagicMock()
        return sock

    @pytest.fixture
    def tcp_device(self, mock_socket):
        """Create a TCPDevice with a mock socket."""
        return TCPDevice("localhost:9999", mock_socket)

    def test_init(self, tcp_device, mock_socket):
        """TCPDevice stores socket and name."""
        assert tcp_device.name == "localhost:9999"
        assert tcp_device._socket is mock_socket

    def test_read_maxlen(self, tcp_device, mock_socket):
        """Read with maxlen returns up to N bytes."""
        mock_socket.recv.return_value = b"hello"
        mock_socket.settimeout = MagicMock()
        data, key = tcp_device.read(maxlen=5)
        assert data == "hello"
        assert key == ""

    def test_read_maxlen_with_newline(self, tcp_device, mock_socket):
        """Read with maxlen strips trailing newline, sets $KEY."""
        mock_socket.recv.return_value = b"hello\n"
        data, key = tcp_device.read(maxlen=10)
        assert data == "hello"
        assert key == chr(10)

    def test_read_maxlen_eof(self, tcp_device, mock_socket):
        """Read with maxlen returns empty on EOF, sets zeof."""
        mock_socket.recv.return_value = b""
        data, key = tcp_device.read(maxlen=5)
        assert data == ""
        assert key == ""
        assert tcp_device.zeof is True

    def test_read_line_newline(self, tcp_device, mock_socket):
        """Read line-based returns text up to newline."""
        mock_socket.recv.return_value = b"data line\n"
        data, key = tcp_device.read()
        assert data == "data line"
        assert key == chr(10)

    def test_read_line_crlf(self, tcp_device, mock_socket):
        """Read line strips \\r\\n and sets $KEY to CR.."""
        mock_socket.recv.return_value = b"data\r\n"
        data, key = tcp_device.read()
        assert data == "data"
        assert key == chr(13)

    def test_read_line_eof(self, tcp_device, mock_socket):
        """Read line returns empty on connection close."""
        mock_socket.recv.return_value = b""
        data, key = tcp_device.read()
        assert data == ""
        assert key == ""
        assert tcp_device.zeof is True

    def test_read_line_partial_then_close(self, tcp_device, mock_socket):
        """Read line returns buffered data on partial + close."""
        mock_socket.recv.side_effect = [b"partial", b""]
        data, key = tcp_device.read()
        assert data == "partial"
        assert key == ""

    def test_read_timeout(self, tcp_device, mock_socket):
        """Read with timeout returns empty on timeout."""
        mock_socket.settimeout = MagicMock()
        mock_socket.recv.side_effect = TimeoutError("timed out")
        data, key = tcp_device.read(timeout=1.0)
        assert data == ""
        assert key == ""

    def test_read_oserror(self, tcp_device, mock_socket):
        """Read handles OSError by setting zeof."""
        mock_socket.settimeout = MagicMock()
        mock_socket.recv.side_effect = OSError("connection reset")
        data, key = tcp_device.read()
        assert data == ""
        assert tcp_device.zeof is True

    def test_read_char(self, tcp_device, mock_socket):
        """read_char returns single character."""
        mock_socket.recv.return_value = b"A"
        ch = tcp_device.read_char()
        assert ch == "A"

    def test_read_char_eof(self, tcp_device, mock_socket):
        """read_char returns empty string on EOF."""
        mock_socket.recv.return_value = b""
        ch = tcp_device.read_char()
        assert ch == ""
        assert tcp_device.zeof is True

    def test_read_char_oserror(self, tcp_device, mock_socket):
        """read_char handles OSError gracefully."""
        mock_socket.recv.side_effect = OSError("broken pipe")
        ch = tcp_device.read_char()
        assert ch == ""
        assert tcp_device.zeof is True

    def test_write(self, tcp_device, mock_socket):
        """write sends UTF-8 encoded data and tracks $X."""
        tcp_device.write("hello")
        mock_socket.sendall.assert_called_once_with(b"hello")
        assert tcp_device.x_pos == 5

    def test_write_newline(self, tcp_device, mock_socket):
        """write_newline sends newline, resets $X, increments $Y."""
        tcp_device.x_pos = 10
        tcp_device.y_pos = 3
        tcp_device.write_newline()
        mock_socket.sendall.assert_called_once_with(b"\n")
        assert tcp_device.x_pos == 0
        assert tcp_device.y_pos == 4

    def test_write_raw(self, tcp_device, mock_socket):
        """write_raw sends data without $X/$Y tracking."""
        tcp_device.x_pos = 5
        tcp_device.write_raw("raw data")
        mock_socket.sendall.assert_called_once_with(b"raw data")
        # $X not updated for raw writes
        assert tcp_device.x_pos == 5

    def test_close(self, tcp_device, mock_socket):
        """close() closes the socket."""
        tcp_device.close()
        mock_socket.close.assert_called_once()

    def test_close_oserror(self, tcp_device, mock_socket):
        """close() ignores OSError."""
        mock_socket.close.side_effect = OSError("already closed")
        tcp_device.close()  # Should not raise

    def test_recv_line_multi_chunk(self, tcp_device, mock_socket):
        """_recv_line buffers multiple chunks until newline."""
        mock_socket.recv.side_effect = [b"hel", b"lo\nworld"]
        line = tcp_device._recv_line()
        assert line == b"hello\n"
        # Remainder stays in buffer
        assert tcp_device._read_buffer == b"world"

    def test_recv_line_complete_close(self, tcp_device, mock_socket):
        """_recv_line returns None on clean close with empty buffer."""
        mock_socket.recv.return_value = b""
        line = tcp_device._recv_line()
        assert line is None


# =============================================================================
# PrincipalDevice Extra Tests
# =============================================================================


class TestPrincipalDeviceReadPaths:
    """Test PrincipalDevice read code paths that aren't covered."""

    def test_read_timeout_success(self):
        """_read_timeout returns data on success."""
        dev = PrincipalDevice()
        with patch("select.select", return_value=([True], [], [])):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.readline.return_value = "hello\n"
                data, key = dev._read_timeout(5.0)
        assert data == "hello"
        assert key == "\r"

    def test_read_timeout_expires(self):
        """_read_timeout returns empty on timeout."""
        dev = PrincipalDevice()
        with patch("select.select", return_value=([], [], [])):
            data, key = dev._read_timeout(0.01)
        assert data == ""
        assert key == ""

    def test_read_maxlen_timeout_success(self):
        """_read_maxlen_timeout reads chars within deadline."""
        dev = PrincipalDevice()
        chars = iter(["a", "b", "c"])
        with patch("select.select", return_value=([True], [], [])):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.side_effect = lambda n: next(chars)
                data, key = dev._read_maxlen_timeout(3, 5.0)
        assert data == "abc"

    def test_read_maxlen_timeout_expires(self):
        """_read_maxlen_timeout returns partial data on timeout."""
        dev = PrincipalDevice()
        call_count = [0]

        def fake_select(rlist, wlist, xlist, timeout):
            call_count[0] += 1
            if call_count[0] <= 1:
                return ([True], [], [])
            return ([], [], [])

        with patch("select.select", side_effect=fake_select):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.return_value = "x"
                data, key = dev._read_maxlen_timeout(3, 0.01)
        # Got at least partial data
        assert "x" in data
        assert key == ""

    def test_read_maxlen_timeout_newline(self):
        """_read_maxlen_timeout handles newline mid-read."""
        dev = PrincipalDevice()
        chars = iter(["a", "\n"])
        with patch("select.select", return_value=([True], [], [])):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.side_effect = lambda n: next(chars)
                data, key = dev._read_maxlen_timeout(5, 5.0)
        assert data == "a"
        assert key == "\n"

    def test_read_maxlen_timeout_eof(self):
        """_read_maxlen_timeout handles EOF mid-read."""
        dev = PrincipalDevice()
        chars = iter(["a", ""])
        with patch("select.select", return_value=([True], [], [])):
            with patch("sys.stdin") as mock_stdin:
                mock_stdin.read.side_effect = lambda n: next(chars)
                data, key = dev._read_maxlen_timeout(5, 5.0)
        assert data == "a"

    def test_write_raw(self):
        """PrincipalDevice write_raw appends without tracking."""
        dev = PrincipalDevice()
        dev.x_pos = 5
        dev.write_raw("raw")
        assert dev.get_output() == "raw"
        # x_pos unchanged
        assert dev.x_pos == 5

    def test_read_dispatches_maxlen_timeout(self):
        """read() with both maxlen and timeout calls _read_maxlen_timeout."""
        dev = PrincipalDevice()
        with patch.object(dev, "_read_maxlen_timeout", return_value=("data", "\r")):
            data, key = dev.read(maxlen=5, timeout=1.0)
        assert data == "data"

    def test_read_dispatches_maxlen_only(self):
        """read() with maxlen only calls _read_maxlen."""
        dev = PrincipalDevice()
        with patch.object(dev, "_read_maxlen", return_value=("abc", "")):
            data, key = dev.read(maxlen=3)
        assert data == "abc"

    def test_read_dispatches_timeout_only(self):
        """read() with timeout only calls _read_timeout."""
        dev = PrincipalDevice()
        with patch.object(dev, "_read_timeout", return_value=("line", "\r")):
            data, key = dev.read(timeout=5.0)
        assert data == "line"


# =============================================================================
# FileDevice Extra Tests
# =============================================================================


class TestFileDeviceEdgePaths:
    """Test FileDevice edge paths."""

    def test_write_raw(self, tmp_path):
        """FileDevice write_raw writes without $X tracking."""
        f = tmp_path / "test.txt"
        fh = open(f, "w")
        dev = FileDevice(str(f), fh, "w")
        dev.x_pos = 5
        dev.write_raw("no track")
        assert dev.x_pos == 5  # Not updated
        dev.close()
        assert f.read_text() == "no track"

    def test_close_already_closed(self, tmp_path):
        """FileDevice close() on already-closed file is safe."""
        f = tmp_path / "test.txt"
        fh = open(f, "w")
        dev = FileDevice(str(f), fh, "w")
        dev.close()
        dev.close()  # Should not raise


# =============================================================================
# MUMPSDevice ABC — write_raw default
# =============================================================================


class TestMUMPSDeviceWriteRawDefault:
    """Test MUMPSDevice.write_raw default implementation."""

    def test_write_raw_delegates_to_write(self):
        """Default write_raw calls write()."""

        class TrackingDevice(MUMPSDevice):
            def __init__(self):
                super().__init__("track")
                self.written = []

            def read(self, maxlen=None, timeout=None):
                return ("", "")

            def read_char(self):
                return ""

            def write(self, data):
                self.written.append(data)

            def write_newline(self):
                pass

            def close(self):
                pass

        dev = TrackingDevice()
        # Call write_raw on the ABC — should delegate to write()
        MUMPSDevice.write_raw(dev, "test")
        assert dev.written == ["test"]
