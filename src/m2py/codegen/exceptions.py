"""Exception classes for code generation.

Extracted to a separate module to avoid circular imports between
codegen/__init__.py and codegen/statements.py.
"""


class CodegenError(Exception):
    """Base exception for code generation errors."""

    pass


class UnsupportedFeatureError(CodegenError):
    """Raised when attempting to generate code for unsupported feature."""

    pass
