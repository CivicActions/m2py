"""Backend-specific exceptions for database storage backends.

These exceptions translate native SDK errors (YottaDB YDBError, IRIS exceptions)
into m2py-specific exception types, preserving the original exception via __cause__.
"""

from m2py.runtime.exceptions import MRuntimeError


class BackendError(MRuntimeError):
    """Base class for backend operation errors.

    All backend-specific exceptions inherit from this class AND from
    MRuntimeError, so existing MUMPS error handling code works seamlessly.
    """

    def __init__(self, code: str = "BACKEND", message: str = "") -> None:
        super().__init__(code, message)


class BackendConnectionError(BackendError):
    """Backend connection failure (network, authentication, missing SDK).

    Raised when:
    - SDK package is not installed (ImportError for yottadb or intersystems-irispython)
    - Database connection cannot be established (network, auth failure)
    - Required environment variables are missing ($ydb_dist, IRIS_HOST, etc.)
    """

    def __init__(self, message: str = "") -> None:
        super().__init__("BACKENDCONN", message)


class BackendPermissionError(BackendError):
    """Backend permission denied (insufficient privileges).

    Raised when:
    - IRIS user lacks required privileges for namespace/global access
    - YottaDB file permissions prevent database access
    """

    def __init__(self, message: str = "") -> None:
        super().__init__("BACKENDPERM", message)


class BackendTimeoutError(BackendError):
    """Backend operation timeout (lock acquisition, query execution).

    Raised when:
    - Lock acquisition exceeds specified timeout
    - Database operation exceeds configured timeout
    """

    def __init__(self, message: str = "") -> None:
        super().__init__("BACKENDTIME", message)


class BackendConfigurationError(BackendError):
    """Backend configuration error (missing env vars, invalid parameters).

    Raised when:
    - Required environment variables are not set
    - Connection parameters are invalid (bad port, unknown host)
    - Backend name is not recognized
    """

    def __init__(self, message: str = "") -> None:
        super().__init__("BACKENDCONF", message)
