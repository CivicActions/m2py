"""MUMPS runtime exceptions.

Provides exception classes for MUMPS runtime errors that have specific
error codes. These mirror YottaDB error codes for compatibility.

Spec 010: Initial implementation for intrinsic function errors.
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
