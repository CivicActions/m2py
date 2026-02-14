"""Variable System Core Components.

This module provides the shared foundation for MUMPS variable semantics,
ensuring consistent behavior across compile-time (codegen) and runtime
(dynamic resolution) paths.

Components:
    NameTranslator: Bidirectional MUMPS ↔ Python name translation
    SubscriptCanonicalizer: Subscript value canonicalization per MUMPS rules
    CurrentScope: Unified variable access abstraction
    IndirectionResolver: Runtime @-expression resolution
    IndirectionContext: Enum for indirection context types
    VarExpectedError: Error for invalid variable name in NAME context
    LVUNDEFError: Error for undefined local variable (M6 error)
"""

from m2py.core.exceptions import LVUNDEFError, VarExpectedError
from m2py.core.names import NameTranslator
from m2py.core.subscripts import SubscriptCanonicalizer
from m2py.core.scope import CurrentScope
from m2py.core.indirection import (
    IndirectionResolver,
    IndirectionContext,
)

__all__ = [
    "NameTranslator",
    "SubscriptCanonicalizer",
    "CurrentScope",
    "IndirectionResolver",
    "IndirectionContext",
    "VarExpectedError",
    "LVUNDEFError",
]
