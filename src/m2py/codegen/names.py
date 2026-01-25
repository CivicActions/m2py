"""Name translation between MUMPS identifiers and Python identifiers.

MUMPS names can contain characters that are invalid in Python identifiers:
- % prefix (valid MUMPS, invalid Python)
- Pure numeric names like "01" (valid MUMPS label, invalid Python)
- Python keywords (if, for, etc.)

This module provides reversible translation between MUMPS and Python names.

# UNIFIED_VAR_DEPRECATED: This entire module will be replaced by core/names.py
# Spec: 018-unified-variable-system, Phase 2 (T011)
# Migration status: COMPLETE - Now re-exports from core/names.py
"""

# Re-export from the unified core module for backward compatibility
from m2py.core.names import NameTranslator, translate_name, reverse_name

__all__ = ["NameTranslator", "translate_name", "reverse_name"]
