"""Exceptions for the MUMPS variable system."""


class LVUNDEFError(Exception):
    """Raised when accessing an undefined local variable (M6 error).

    MUMPS error: %YDB-E-LVUNDEF, Undefined local variable: <name>

    This error is unconditionally raised when an undefined local
    variable is accessed during GET operations.
    """

    def __init__(self, name: str, message: str = ""):
        self.name = name
        self.message = message or f"LVUNDEF: Undefined local variable: {name}"
        super().__init__(self.message)


class VarExpectedError(Exception):
    """Raised when NAME context requires a variable name but got expression.

    MUMPS error: %YDB-E-VAREXPECTED

    This occurs during name indirection when the resolved value is not
    a valid MUMPS variable name (e.g., "1+1" instead of "A").
    """

    def __init__(self, value: str, message: str = ""):
        self.value = value
        self.message = message or f"VAREXPECTED: '{value}' is not a valid variable name"
        super().__init__(self.message)


__all__ = ["LVUNDEFError", "VarExpectedError"]
