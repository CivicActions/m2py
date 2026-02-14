"""MUMPS runtime exceptions.

Provides exception classes for MUMPS runtime errors that have specific
error codes. These mirror YottaDB error codes for compatibility.
"""


class MRuntimeError(Exception):
    """MUMPS runtime error with error code.

    This exception is raised for MUMPS-specific runtime errors that
    have defined error codes. The code is used for error identification
    and matches YottaDB error naming conventions.

    Attributes:
        code: Error code string (e.g., "SELECTFALSE", "RANDARGNEG")
        message: Optional detailed error message

    Usage:
        raise MRuntimeError("SELECTFALSE")
        raise MRuntimeError("RANDARGNEG", "$RANDOM argument must be positive")

    Error Codes:
        SELECTFALSE - $SELECT with no true condition
        RANDARGNEG - $RANDOM with argument ≤ 0
    """

    def __init__(self, code: str, message: str = "") -> None:
        """Initialize MUMPS runtime error.

        Args:
            code: Error code (e.g., "SELECTFALSE", "RANDARGNEG")
            message: Optional detailed error message
        """
        self.code = code
        self.message = message
        # Format: "M-CODE: message" or just "M-CODE" if no message
        full_message = f"M-{code}: {message}" if message else f"M-{code}"
        super().__init__(full_message)

    def __repr__(self) -> str:
        """Return repr showing code and message."""
        if self.message:
            return f"MRuntimeError({self.code!r}, {self.message!r})"
        return f"MRuntimeError({self.code!r})"


class DeviceError(MRuntimeError):
    """Base class for device-related runtime errors.

    Raised when I/O device operations fail. Subclasses provide
    specific error codes for different failure modes.
    """

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(code, message)


class DeviceNotOpenError(DeviceError):
    """Raised when USE or READ/WRITE targets a device that is not open.

    MUMPS error code: DEVNOTOPEN
    Corresponds to YottaDB %SYSTEM-E-DEVNOTOPEN error.

    Example:
        USE "nonexistent.txt"  ; raises DeviceNotOpenError
    """

    def __init__(self, device_name: str) -> None:
        super().__init__("DEVNOTOPEN", f"Device not open: {device_name}")
        self.device_name = device_name


class DeviceOpenFailError(DeviceError):
    """Raised when OPEN fails to open a device.

    MUMPS error code: DEVOPENFAIL
    Corresponds to YottaDB %SYSTEM-E-DEVOPENFAIL error.

    This is raised for errors like file-not-found or permission denied,
    regardless of whether a timeout was specified on the OPEN command.

    Example:
        OPEN "/nonexistent/path.txt"  ; raises DeviceOpenFailError
    """

    def __init__(self, device_name: str, reason: str = "") -> None:
        message = f"Cannot open device: {device_name}"
        if reason:
            message += f" ({reason})"
        super().__init__("DEVOPENFAIL", message)
        self.device_name = device_name
        self.reason = reason
