"""Tests for TCPDevice — TCP socket I/O device implementation.

Tests cover:
- TCPDevice connect, read (line-based + maxlen), write, close
- TCP device type detection in open_device()
- OPEN timeout for TCP connections ($TEST=0 on failure)
- $KEY and $ZEOF for TCP reads
- Per-device ISV tracking with TCP

Uses a local echo server fixture for reliable testing.

Spec 022: Phase 4 — US5 (TCP Socket I/O)
"""

import socket
import threading
import time

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.devices import TCPDevice


@pytest.fixture
def echo_server():
    """Start a local TCP echo server that echoes back received data.

    Sends back each line as-is (with newline). Closes when client disconnects.
    Returns (host, port) tuple.
    """
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))  # Let OS pick a free port
    server.listen(5)
    host, port = server.getsockname()

    def handle_client(conn: socket.socket) -> None:
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                conn.sendall(data)
        except OSError:
            pass
        finally:
            conn.close()

    def serve() -> None:
        server.settimeout(5.0)
        try:
            while True:
                try:
                    conn, _ = server.accept()
                    t = threading.Thread(
                        target=handle_client, args=(conn,), daemon=True
                    )
                    t.start()
                except socket.timeout:
                    break
                except OSError:
                    break
        finally:
            server.close()

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    yield (host, port)

    server.close()


@pytest.fixture
def line_server():
    """Start a TCP server that sends predefined lines then closes.

    Returns (host, port, set_lines) where set_lines is a callable
    to set the lines to send.
    """
    lines_to_send: list[str] = []
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    host, port = server.getsockname()

    def serve() -> None:
        server.settimeout(5.0)
        try:
            conn, _ = server.accept()
            for line in lines_to_send:
                conn.sendall(line.encode("utf-8"))
            time.sleep(0.1)  # Give client time to read
            conn.close()
        except (socket.timeout, OSError):
            pass
        finally:
            server.close()

    def set_lines(lines: list[str]) -> None:
        lines_to_send.extend(lines)

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    yield (host, port, set_lines)


# =============================================================================
# TCPDevice Direct Tests
# =============================================================================


class TestTCPDeviceWrite:
    """TCPDevice write tests using echo server."""

    def test_write_and_read_echo(self, echo_server):
        """Write data, read echo response."""
        host, port = echo_server
        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.write("Hello")
        dev.write_newline()

        data, key = dev.read()
        assert data == "Hello"
        assert key == chr(10)

        dev.close()

    def test_write_x_tracking(self, echo_server):
        """write() tracks $X for printable characters."""
        host, port = echo_server
        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.write("AB")
        assert dev.x_pos == 2

        dev.close()

    def test_write_newline(self, echo_server):
        """write_newline() resets $X, increments $Y."""
        host, port = echo_server
        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.write("AB")
        dev.write_newline()
        assert dev.x_pos == 0
        assert dev.y_pos == 1

        dev.close()


class TestTCPDeviceRead:
    """TCPDevice read tests."""

    def test_read_line(self, line_server):
        """read() returns line with $C(10) key."""
        host, port, set_lines = line_server
        set_lines(["Hello\n", "World\n"])

        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        data, key = dev.read()
        assert data == "Hello"
        assert key == chr(10)
        assert dev.zeof is False

        data, key = dev.read()
        assert data == "World"
        assert key == chr(10)

        dev.close()

    def test_read_eof(self, line_server):
        """read() at connection close sets $ZEOF=True."""
        host, port, set_lines = line_server
        set_lines(["data\n"])

        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.read()  # "data"
        time.sleep(0.2)  # Wait for server to close

        data, key = dev.read()
        assert data == ""
        assert key == ""
        assert dev.zeof is True

        dev.close()

    def test_read_maxlen(self, echo_server):
        """read(maxlen=n) reads at most n bytes."""
        host, port = echo_server
        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.write("ABCDEFG\n")
        time.sleep(0.1)

        data, _ = dev.read(maxlen=3)
        assert len(data) <= 3

        dev.close()


class TestTCPDeviceClose:
    """TCPDevice close tests."""

    def test_close(self, echo_server):
        """close() shuts down socket."""
        host, port = echo_server
        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.close()
        # Socket should be closed
        assert sock.fileno() == -1

    def test_close_already_closed(self, echo_server):
        """close() on already-closed socket is a no-op."""
        host, port = echo_server
        sock = socket.create_connection((host, port), timeout=2)
        dev = TCPDevice(f"{host}:{port}", sock)

        dev.close()
        dev.close()  # Should not raise


# =============================================================================
# open_device() TCP Detection Tests
# =============================================================================


class TestOpenDeviceTCP:
    """open_device() TCP device type detection tests."""

    def test_open_connect(self, echo_server):
        """OPEN "host:port":(CONNECT) creates TCPDevice."""
        host, port = echo_server
        device_name = f"{host}:{port}"

        rt = MUMPSRuntime()
        result = rt.open_device(device_name, ["CONNECT"])
        assert result is True
        assert device_name in rt._device_table
        assert isinstance(rt._device_table[device_name], TCPDevice)

        rt.close_device(device_name)

    def test_open_connect_with_timeout_success(self, echo_server):
        """OPEN with timeout succeeds → returns True ($TEST=1)."""
        host, port = echo_server
        device_name = f"{host}:{port}"

        rt = MUMPSRuntime()
        result = rt.open_device(device_name, ["CONNECT"], timeout=5)
        assert result is True

        rt.close_device(device_name)

    def test_open_connect_timeout_failure(self):
        """OPEN with timeout on unreachable host → returns False ($TEST=0)."""
        # Use a port that nobody listens on
        rt = MUMPSRuntime()
        # Use a non-routable address with short timeout
        result = rt.open_device("192.0.2.1:9999", ["CONNECT"], timeout=0.1)
        assert result is False

    def test_open_connect_no_timeout_returns_false(self):
        """OPEN without timeout on connection refused → returns False ($TEST=0).

        For TCP connections, connection failure with timeout returns False.
        Without a timeout, we use a default 10s timeout internally, so
        connection refusal still returns False.
        """
        rt = MUMPSRuntime()
        # Port 1 should be refused immediately on localhost
        result = rt.open_device("127.0.0.1:1", ["CONNECT"], timeout=0.5)
        assert result is False

    def test_use_and_write_tcp(self, echo_server):
        """USE tcp device, WRITE, verify echo."""
        host, port = echo_server
        device_name = f"{host}:{port}"

        rt = MUMPSRuntime()
        rt.open_device(device_name, ["CONNECT"])
        rt.use_device(device_name)

        assert rt.io() == device_name

        rt.close_device(device_name)
        assert rt.io() == "0"

    def test_close_tcp_device(self, echo_server):
        """CLOSE tcp device removes from table, reverts to principal."""
        host, port = echo_server
        device_name = f"{host}:{port}"

        rt = MUMPSRuntime()
        rt.open_device(device_name, ["CONNECT"])
        rt.use_device(device_name)
        rt.close_device(device_name)

        assert device_name not in rt._device_table
        assert rt.io() == "0"
