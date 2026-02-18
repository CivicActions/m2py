"""MUMPS I/O device abstraction layer.

Provides the MUMPSDevice abstract base class and concrete device implementations
for the M2PY transpiler runtime. All MUMPS I/O operations (READ, WRITE, OPEN,
USE, CLOSE) are dispatched through this device layer.

Device types:
    - PrincipalDevice: stdin/stdout wrapper ($PRINCIPAL, device "0")
    - FileDevice: Sequential file I/O (OPEN "file":params)
    - TCPDevice: TCP socket client connections (OPEN "host:port":params)

Each device tracks per-device ISVs: $X, $Y, $KEY, $ZEOF.
"""

from __future__ import annotations

import select
import sys
import time
from abc import ABC, abstractmethod
from typing import Any


class MUMPSDevice(ABC):
    """Abstract base class for all MUMPS I/O devices.

    Every MUMPS device supports read, write, and close operations,
    and tracks per-device intrinsic special variables ($X, $Y, $KEY, $ZEOF).

    Subclasses must implement all abstract methods to provide
    device-specific I/O behavior.

    Attributes:
        name: Device identifier (e.g., "0" for $PRINCIPAL, "/tmp/file.txt")
        x_pos: Current $X column position for this device
        y_pos: Current $Y line position for this device
        key: Current $KEY (last READ terminator) for this device
        zeof: Current $ZEOF (end-of-file indicator) for this device
    """

    def __init__(self, name: str) -> None:
        """Initialize device with identifier and default ISV values.

        Args:
            name: Device identifier string.
        """
        self.name = name
        self.x_pos: int = 0
        self.y_pos: int = 0
        self.key: str = ""
        self.zeof: bool = False

    @abstractmethod
    def read(
        self, maxlen: int | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """Read from device.

        Args:
            maxlen: Maximum number of characters to read. None for unlimited.
            timeout: Read timeout in seconds. None for no timeout.

        Returns:
            Tuple of (data, terminator_key) where terminator_key is the
            character that terminated the read (e.g., $C(13) for Enter,
            "" for EOF or maxlen reached).
        """

    @abstractmethod
    def read_char(self) -> str:
        """Read a single character from device.

        MUMPS R *X reads a single character.

        Returns:
            Single character, or empty string on EOF.
        """

    @abstractmethod
    def write(self, data: str) -> None:
        """Write data to device. Updates x_pos for printable characters.

        Args:
            data: String data to write.
        """

    @abstractmethod
    def write_newline(self) -> None:
        """Write a newline to device. Resets x_pos to 0, increments y_pos."""

    @abstractmethod
    def close(self) -> None:
        """Close device and release resources."""

    def write_raw(self, s: str) -> None:
        """Write raw string without $X/$Y tracking.

        Default implementation appends to write buffer without tracking.
        Subclasses may override for device-specific behavior.

        Args:
            s: String to write directly.
        """
        self.write(s)

    def write_tab(self, column: int) -> None:
        """Tab to column position (W ?n format control).

        If current $X < target column, write spaces to reach it.

        Args:
            column: Target column (0-based).
        """
        if self.x_pos < column:
            spaces = column - self.x_pos
            self.write(" " * spaces)

    def write_formfeed(self, debug: bool = False) -> None:
        """Write form feed (W # format control).

        Default implementation: conditional newline, then form feed,
        then reset $X/$Y. Subclasses may override.
        """
        if self.x_pos > 0:
            self.write_newline()
        # Use write() for the formfeed character — but it shouldn't increment $X
        # since chr(12) < 32. write() handles this correctly.
        self.write("\x0c")
        self.x_pos = 0
        self.y_pos = 0

    def device_control(self, keyword: str, *params: Any) -> None:
        """Handle device control mnemonics (W /keyword).

        Device control commands are implementation-specific extensions for
        device I/O: /EOF, /WAIT, /LISTEN, /ACCEPT, /PASS, /CLEAR, /FLUSH, etc.

        VistA uses these primarily for socket and pipe operations. The base
        implementation is a no-op; subclasses can override for device-specific
        control behavior.

        Args:
            keyword: Control keyword (e.g. 'EOF', 'WAIT', 'LISTEN', 'CLEAR')
            *params: Optional parameters for the control command
        """
        pass  # No-op stub — subclasses may override for device-specific behavior


class PrincipalDevice(MUMPSDevice):
    """Principal device ($PRINCIPAL) — stdin/stdout wrapper.

    The principal device is always device "0". It wraps the current
    stdout/_output list for writes and stdin for reads, preserving
    the standard runtime behavior.

    For testing, output is captured in the runtime's ``_output`` list
    and can be retrieved with ``get_output()``. This matches the
    pre-existing M2PY pattern where ``write()`` appends to a list
    and ``get_output()`` joins it.

    The device holds a back-reference to the runtime so that output
    goes to ``runtime._output``. This ensures backward compatibility
    with tests that do ``runtime._output = []`` to reset capture.
    """

    def __init__(self, runtime: Any = None) -> None:
        """Initialize principal device.

        Args:
            runtime: Back-reference to MUMPSRuntime for _output access.
                     If None, uses internal list (for standalone testing).
        """
        super().__init__("0")
        self._runtime = runtime
        # Fallback output list for standalone use (no runtime)
        self._standalone_output: list[str] = []

    @property
    def _output(self) -> list[str]:
        """Access the output list — runtime's if available, standalone otherwise."""
        if self._runtime is not None:
            return self._runtime._output
        return self._standalone_output

    def read(
        self, maxlen: int | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """Read from stdin.

        Supports combinations of maxlen and timeout, matching the
        established behavior of the read helper functions.

        Args:
            maxlen: Maximum characters to read. None = read full line.
            timeout: Timeout in seconds. None = block indefinitely.

        Returns:
            Tuple of (data, terminator_key).
            For timed reads, terminator_key is "" on timeout.
        """
        if maxlen is not None and timeout is not None:
            return self._read_maxlen_timeout(maxlen, timeout)
        elif maxlen is not None:
            return self._read_maxlen(maxlen)
        elif timeout is not None:
            return self._read_timeout(timeout)
        else:
            return self._read_line()

    def _read_line(self) -> tuple[str, str]:
        """Read a full line from stdin (basic READ X)."""
        line = input()
        self.key = "\r"
        return (line, "\r")

    def _read_timeout(self, timeout_seconds: float) -> tuple[str, str]:
        """Read from stdin with timeout (READ X:n)."""
        timeout = float(timeout_seconds)
        readable, _, _ = select.select([sys.stdin], [], [], timeout)
        if readable:
            line = sys.stdin.readline()
            if line.endswith("\n"):
                line = line[:-1]
            self.key = "\r"
            return (line, "\r")
        else:
            self.key = ""
            return ("", "")

    def _read_maxlen(self, maxlen: int) -> tuple[str, str]:
        """Read up to maxlen characters from stdin (READ X#n)."""
        result: list[str] = []
        key = ""
        for _ in range(maxlen):
            ch = sys.stdin.read(1)
            if ch == "" or ch == "\n":
                if ch == "\n":
                    key = ch
                break
            result.append(ch)
        else:
            key = ""
        self.key = key
        return ("".join(result), key)

    def _read_maxlen_timeout(
        self, maxlen: int, timeout_seconds: float
    ) -> tuple[str, str]:
        """Read up to maxlen chars with timeout (READ X#n:t)."""
        timeout = float(timeout_seconds)
        deadline = time.monotonic() + timeout
        result: list[str] = []
        key = ""

        for _ in range(maxlen):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self.key = ""
                return ("".join(result), "")

            readable, _, _ = select.select([sys.stdin], [], [], remaining)
            if not readable:
                self.key = ""
                return ("".join(result), "")

            ch = sys.stdin.read(1)
            if ch == "" or ch == "\n":
                if ch == "\n":
                    key = ch
                break
            result.append(ch)
        else:
            key = ""

        self.key = key
        return ("".join(result), key)

    def read_char(self) -> str:
        """Read a single character from stdin (READ *X)."""
        char = sys.stdin.read(1)
        return char

    def write(self, data: str) -> None:
        """Write data to output buffer, tracking $X.

        Matches established behavior: only printable characters
        (ord >= 32) increment $X. $Y is NOT affected by write().

        Args:
            data: String data to output.
        """
        for char in data:
            if ord(char) >= 32:
                self.x_pos += 1
        self._output.append(data)

    def write_newline(self) -> None:
        """Write newline (W ! format control).

        Outputs newline, resets $X to 0, increments $Y by 1.
        """
        self._output.append("\n")
        self.x_pos = 0
        self.y_pos += 1

    def write_raw(self, s: str) -> None:
        """Write raw string without $X/$Y tracking.

        Used for output that should not affect position tracking.

        Args:
            s: String to write directly.
        """
        self._output.append(s)

    def write_formfeed(self, debug: bool = False) -> None:
        """Write form feed (W # format control).

        MUMPS W # behavior (YDB verified):
        1. If $X > 0, output newline first
        2. Output form feed character (0x0C)
        3. Reset $X and $Y to 0
        """
        if debug:
            print(f"FORMFEED: $X={self.x_pos}, $Y={self.y_pos}")

        if self.x_pos > 0:
            self._output.append("\n")
            self.y_pos += 1
            if debug:
                print(f"  Added conditional newline, $Y now {self.y_pos}")

        self._output.append("\x0c")
        self.x_pos = 0
        self.y_pos = 0

    def write_tab(self, column: int) -> None:
        """Tab to column position (W ?n format control).

        If current $X < target column, write spaces to reach it.

        Args:
            column: Target column (0-based).
        """
        if self.x_pos < column:
            spaces = column - self.x_pos
            self.write(" " * spaces)

    def get_output(self) -> str:
        """Return accumulated output as a single string.

        Returns:
            Concatenated string of all write() calls.
        """
        return "".join(self._output)

    def clear(self) -> None:
        """Clear accumulated output and reset position tracking."""
        self._output.clear()
        self.x_pos = 0
        self.y_pos = 0

    def close(self) -> None:
        """Close principal device (no-op — $PRINCIPAL cannot be closed)."""
        pass


class FileDevice(MUMPSDevice):
    """File device — sequential file I/O.

    Handles OPEN/USE/CLOSE/READ/WRITE for file paths. Each file device
    wraps a Python file object and tracks per-device ISVs.

    Mode mapping from MUMPS device parameters to Python open modes:
        - NEWVERSION / "WN" → "w"  (create/truncate)
        - READONLY  / "R"  → "r"  (read-only)
        - APPEND    / "A"  → "a"  (append)
        - read-write / "RW" → "r+" (read + write, file must exist)
        - default (no params) → "r" (read-only)

    Device parameters:
        - STREAM → disables record-size limits (stored but not enforced yet)
        - RECORDSIZE=n → truncates output lines at n characters (stored, not yet enforced)

    """

    def __init__(self, name: str, file_obj: Any, mode: str = "r") -> None:
        """Initialize file device.

        Args:
            name: Device name (file path).
            file_obj: Open Python file object.
            mode: Python file mode string ("r", "w", "a", "r+").
        """
        super().__init__(name)
        self._file = file_obj
        self._mode = mode
        self._stream: bool = False
        self._record_size: int | None = None

    def read(
        self, maxlen: int | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """Read from file.

        Reads one line from the file. If maxlen is specified, reads at most
        maxlen characters. Timeout is ignored for files (reads are immediate).

        After a successful read of a complete line, $KEY is set to $C(10).
        After EOF, $KEY is set to "" and $ZEOF is set to True.

        Args:
            maxlen: Maximum number of characters to read. None for full line.
            timeout: Ignored for file devices (reads are immediate).

        Returns:
            Tuple of (data, terminator_key).
        """
        if maxlen is not None:
            data = self._file.read(maxlen)
            if not data:
                # EOF
                self.key = ""
                self.zeof = True
                return ("", "")
            # Check if we consumed a newline within maxlen
            if data.endswith("\n"):
                data = data[:-1]
                self.key = chr(10)
            else:
                self.key = ""
            return (data, self.key)
        else:
            line = self._file.readline()
            if not line:
                # EOF
                self.key = ""
                self.zeof = True
                return ("", "")
            # Strip trailing newline
            if line.endswith("\n"):
                line = line[:-1]
                self.key = chr(10)
            else:
                # Last line without trailing newline — still data, but
                # next read will be EOF
                self.key = chr(10)
            return (line, self.key)

    def read_char(self) -> str:
        """Read a single character from file (READ *X).

        Returns:
            Single character, or empty string on EOF.
        """
        ch = self._file.read(1)
        if not ch:
            self.zeof = True
            self.key = ""
            return ""
        return ch

    def write(self, data: str) -> None:
        """Write data to file. Updates $X for printable characters.

        Args:
            data: String data to write.
        """
        self._file.write(data)
        for char in data:
            if ord(char) >= 32:
                self.x_pos += 1

    def write_newline(self) -> None:
        """Write newline to file. Resets $X to 0, increments $Y."""
        self._file.write("\n")
        self.x_pos = 0
        self.y_pos += 1

    def write_raw(self, s: str) -> None:
        """Write raw string to file without $X/$Y tracking.

        Args:
            s: String to write directly.
        """
        self._file.write(s)

    def close(self) -> None:
        """Close the file handle."""
        if self._file and not self._file.closed:
            self._file.close()


class TCPDevice(MUMPSDevice):
    """TCP socket device — client-mode TCP connections.

    Supports MUMPS OPEN "host:port":(CONNECT) for HL7-style communication.
    Reads support delimiter-based termination (e.g., read until newline
    or a specific character).

    Per-device ISVs:
        - $KEY: Set to delimiter that terminated the read, or "" on timeout/EOF
        - $ZEOF: Set to True when socket is closed by remote end
        - $X/$Y: Updated on write as with other devices

    """

    def __init__(self, name: str, sock: Any) -> None:
        """Initialize TCP device wrapping an already-connected socket.

        Args:
            name: Device name ("host:port").
            sock: Connected socket.socket object.
        """
        import socket as socket_mod

        super().__init__(name)
        self._socket: socket_mod.socket = sock
        # Buffer for incremental reads
        self._read_buffer: bytes = b""

    def read(
        self, maxlen: int | None = None, timeout: float | None = None
    ) -> tuple[str, str]:
        """Read from TCP socket.

        Reads data until a delimiter (newline by default), maxlen chars,
        timeout, or connection close.

        Args:
            maxlen: Maximum number of characters to read. None for line-based.
            timeout: Read timeout in seconds. None for blocking.

        Returns:
            Tuple of (data, terminator_key).
            If timeout expires: ("", "").
            If connection closed: ("", ""), zeof=True.
        """

        if timeout is not None:
            self._socket.settimeout(timeout)
        else:
            self._socket.settimeout(None)

        try:
            if maxlen is not None:
                # Read up to maxlen bytes
                data = self._recv_bytes(maxlen)
                if not data:
                    self.key = ""
                    self.zeof = True
                    return ("", "")
                text = data.decode("utf-8", errors="replace")
                if text.endswith("\n"):
                    text = text[:-1]
                    self.key = chr(10)
                else:
                    self.key = ""
                return (text, self.key)
            else:
                # Read until newline (line-based)
                line = self._recv_line()
                if line is None:
                    self.key = ""
                    self.zeof = True
                    return ("", "")
                text = line.decode("utf-8", errors="replace")
                if text.endswith("\r\n"):
                    text = text[:-2]
                    self.key = chr(13)
                elif text.endswith("\n"):
                    text = text[:-1]
                    self.key = chr(10)
                else:
                    self.key = ""
                return (text, self.key)
        except (TimeoutError, OSError) as e:
            if isinstance(e, TimeoutError):
                self.key = ""
                return ("", "")
            self.key = ""
            self.zeof = True
            return ("", "")
        finally:
            self._socket.settimeout(None)

    def _recv_bytes(self, count: int) -> bytes:
        """Receive up to count bytes from socket.

        Args:
            count: Maximum bytes to receive.

        Returns:
            Received bytes, or empty bytes on EOF.
        """
        return self._socket.recv(count)

    def _recv_line(self) -> bytes | None:
        """Receive bytes until newline delimiter.

        Uses an internal read buffer for efficient line-based reads.

        Returns:
            Line bytes including newline, or None on connection close.
        """
        while b"\n" not in self._read_buffer:
            chunk = self._socket.recv(4096)
            if not chunk:
                # Connection closed
                if self._read_buffer:
                    data = self._read_buffer
                    self._read_buffer = b""
                    return data
                return None
            self._read_buffer += chunk

        idx = self._read_buffer.index(b"\n")
        line = self._read_buffer[: idx + 1]
        self._read_buffer = self._read_buffer[idx + 1 :]
        return line

    def read_char(self) -> str:
        """Read a single character from TCP socket.

        Returns:
            Single character, or empty string on EOF/error.
        """
        try:
            data = self._socket.recv(1)
            if not data:
                self.zeof = True
                self.key = ""
                return ""
            return data.decode("utf-8", errors="replace")
        except OSError:
            self.zeof = True
            self.key = ""
            return ""

    def write(self, data: str) -> None:
        """Write data to TCP socket. Updates $X for printable characters.

        Args:
            data: String data to send.
        """
        self._socket.sendall(data.encode("utf-8"))
        for char in data:
            if ord(char) >= 32:
                self.x_pos += 1

    def write_newline(self) -> None:
        """Write newline to TCP socket. Resets $X, increments $Y."""
        self._socket.sendall(b"\n")
        self.x_pos = 0
        self.y_pos += 1

    def write_raw(self, s: str) -> None:
        """Write raw string to TCP socket without $X/$Y tracking.

        Args:
            s: String to send directly.
        """
        self._socket.sendall(s.encode("utf-8"))

    def close(self) -> None:
        """Close the TCP socket."""
        try:
            self._socket.close()
        except OSError:
            pass
