"""Unified variable access abstraction.

This module provides the CurrentScope class for unified variable access
across different storage mechanisms (Python locals, _scope dict, state._locals),
Constitution VII: All variable access (static or indirected) uses the same path,
preventing "variable not found" bugs that occur when codegen uses Python locals
but runtime uses _scope dict.

Feature: 018-unified-variable-system
Requirements: FR-025 (LVUNDEF), FR-036, FR-037, FR-038 (CurrentScope)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from m2py.core.exceptions import LVUNDEFError
from m2py.core.names import NameTranslator
from m2py.core.parsing import parse_subscripted_name
from m2py.core.subscripts import SubscriptCanonicalizer


class CurrentScope:
    """Unified variable access abstraction.

    This adapter unifies:
    - Python locals (PURE_FUNCTION strategy)
    - _scope dict (FUNCTION_WITH_OUTPUTS, SUBROUTINE strategies)
    - state._locals (REQUIRES_RUNTIME strategy)

    FR-036, FR-037: Provides the "Current Scope" abstraction from spec.
    FR-038: Automatically extracts .value from MArray objects.
    FR-025: Raises LVUNDEF in strict mode when accessing undefined variables.
    """

    def __init__(
        self,
        scope_dict: Optional[Dict[str, Any]] = None,
        name_translator: Optional[NameTranslator] = None,
        strict_mode: bool = False,
    ):
        """Initialize scope with available storage mechanisms.

        Args:
            scope_dict: The _scope dict passed through generated code
            name_translator: Optional custom translator (defaults to standard)
            strict_mode: If True, raises LVUNDEFError on undefined variable access

        At least one storage mechanism should be provided for useful operation.
        """
        self._scope_dict = scope_dict
        self._name_translator = name_translator or NameTranslator()
        self._strict_mode = strict_mode

    def get(self, name: str, default: Any = "") -> Any:
        """Get variable value by MUMPS name.

        Args:
            name: MUMPS variable name (e.g., "X", "%FOO", "A(1,2)")
            default: Value to return if not found (MUMPS undefined = "")

        Returns:
            Variable value, or default if undefined

        Raises:
            LVUNDEFError: In strict mode, if local variable is undefined

        Note: Handles subscripted names by parsing and traversing.
        FR-025: In strict mode, raises LVUNDEF for undefined local variables.
        FR-038: Extracts .value from MArray objects automatically.
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)
            return self.get_subscripted(base_name, subscripts, default)

        # Translate MUMPS name to Python identifier
        py_name = NameTranslator.to_python(name)

        # Look up in storage mechanisms - try both MUMPS and Python names
        value = self._lookup(py_name, _SENTINEL, mumps_name=name)

        # Check for undefined in strict mode
        if value is _SENTINEL:
            if self._strict_mode:
                raise LVUNDEFError(name)
            return default

        # Extract .value from MArray if needed
        return self._extract_value(value)

    def get_subscripted(
        self, name: str, subscripts: List[Any], default: Any = ""
    ) -> Any:
        """Get subscripted variable value.

        Args:
            name: Base MUMPS variable name (no subscripts)
            subscripts: List of subscript values
            default: Value to return if not found

        Returns:
            Value at NAME(subscripts), or default

        Raises:
            LVUNDEFError: In strict mode, if subscripted variable is undefined

        Example:
            get_subscripted("A", [1, 2]) → value of A(1,2)
        """
        py_name = NameTranslator.to_python(name)
        base = self._lookup(py_name, None, mumps_name=name)

        if base is None:
            if self._strict_mode:
                # Format subscripts for error message
                subs_str = ",".join(str(s) for s in subscripts)
                raise LVUNDEFError(f"{name}({subs_str})")
            return default

        # For MArray, use defined() to check existence before navigation
        # This handles MUMPS auto-vivification properly
        if hasattr(base, "defined"):
            canonical_subs = [
                SubscriptCanonicalizer.canonicalize(s) for s in subscripts
            ]
            data_code = base.defined(*canonical_subs)
            # data_code: 0=none, 1=value, 10=descendants, 11=both
            # LVUNDEF should fire if there's no value (data_code in 0, 10)
            if data_code in (0, 10):
                if self._strict_mode:
                    subs_str = ",".join(str(s) for s in subscripts)
                    raise LVUNDEFError(f"{name}({subs_str})")
                return default
            # Navigate to get the actual value
            current = base
            for sub in canonical_subs:
                current = current[sub]
            return self._extract_value(current)

    def is_defined(self, name: str, subscripts: Optional[List[Any]] = None) -> bool:
        """Check if a variable is defined (has a value).

        Args:
            name: MUMPS variable name (base name only)
            subscripts: Optional list of subscript values

        Returns:
            True if variable is defined, False otherwise

        Note: This checks for $DATA style existence - a variable is defined
        if it has a value at the specified location.
        """
        # Translate MUMPS name to Python identifier
        py_name = NameTranslator.to_python(name)

        # Look up base variable
        base = self._lookup(py_name, _SENTINEL, mumps_name=name)

        if base is _SENTINEL:
            return False

        # If no subscripts, check if base has a value
        if subscripts is None or len(subscripts) == 0:
            # Check if it's a defined scalar or MArray with value
            from m2py.runtime import MArray

            if isinstance(base, MArray):
                # MArray is "defined" if it has a _value (not None)
                # Note: we check _value, not .value, because .value returns ""
                # for undefined (None) which would always be truthy
                return base._value is not None
            return True  # Simple value exists

        # Traverse subscripts to check if target location exists
        current = base
        from m2py.runtime import MArray

        if isinstance(current, MArray):
            for i, sub in enumerate(subscripts):
                canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
                if canonical_sub in current:
                    current = current[canonical_sub]
                else:
                    return False
            # Check if final node has a value
            if isinstance(current, MArray):
                return current._value is not None
            return True  # Simple value exists
        else:
            # Not an MArray, can't have subscripts
            return False

    def set(self, name: str, value: Any) -> None:
        """Set variable value by MUMPS name.

        Args:
            name: MUMPS variable name (may include subscripts)
            value: Value to set (scalar value or MArray)

        Creates intermediate MArray structures as needed for subscripted vars.
        For simple (non-subscripted) variables, wraps value in MArray for
        consistency with generated code which expects .value attribute.
        If value is already an MArray, stores it directly.
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)
            self.set_subscripted(base_name, subscripts, value)
            return

        # Translate MUMPS name to Python identifier
        py_name = NameTranslator.to_python(name)

        from m2py.runtime import MArray

        # If value is already an MArray, store it directly
        if isinstance(value, MArray):
            self._store(py_name, value)
            return

        # Wrap in MArray for consistency with generated code
        # (generated code expects _scope[key].value)
        existing = self._lookup(py_name, None, mumps_name=name)
        if existing is not None and isinstance(existing, MArray):
            # Update existing MArray
            existing.value = value
        else:
            # Create new MArray with value
            arr = MArray()
            arr.value = value
            self._store(py_name, arr)

    def set_subscripted(self, name: str, subscripts: List[Any], value: Any) -> None:
        """Set subscripted variable value.

        Args:
            name: Base MUMPS variable name
            subscripts: List of subscript values
            value: Value to set

        Creates intermediate MArray structures as needed.
        """
        py_name = NameTranslator.to_python(name)

        # Get or create base array
        base = self._lookup(py_name, None, mumps_name=name)

        # If base doesn't exist or isn't subscriptable, create MArray
        if base is None or not self._is_array_like(base):
            # Import MArray here to avoid circular import at module level
            from m2py.runtime import MArray

            base = MArray()
            self._store(py_name, base)

        # Navigate/create path and set value
        current = base
        for i, sub in enumerate(subscripts[:-1]):
            canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
            if hasattr(current, "__getitem__"):
                try:
                    next_node = current[canonical_sub]
                    if not self._is_array_like(next_node):
                        # Need to create intermediate node
                        from m2py.runtime import MArray

                        next_node = MArray()
                        current[canonical_sub] = next_node
                    current = next_node
                except (KeyError, IndexError):
                    # Create intermediate node
                    from m2py.runtime import MArray

                    next_node = MArray()
                    current[canonical_sub] = next_node
                    current = next_node

        # Set final value
        final_sub = SubscriptCanonicalizer.canonicalize(subscripts[-1])
        current[final_sub] = value

    def exists(self, name: str) -> bool:
        """Check if variable is defined.

        Args:
            name: MUMPS variable name

        Returns:
            True if variable has a value (not just descendants)

        Corresponds to $DATA(name) in {1, 11} (has value)
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)
            return self._exists_subscripted(base_name, subscripts)

        py_name = NameTranslator.to_python(name)
        return self._lookup(py_name, _SENTINEL, mumps_name=name) is not _SENTINEL

    def _exists_subscripted(self, name: str, subscripts: List[Any]) -> bool:
        """Check if subscripted variable exists (has value)."""
        py_name = NameTranslator.to_python(name)
        base = self._lookup(py_name, None, mumps_name=name)

        if base is None:
            return False

        # Use MArray's defined() if available - it understands MUMPS semantics
        if hasattr(base, "defined"):
            # defined() returns 0, 1, 10, 11
            # exists means has value = 1 or 11
            canonical_subs = [
                SubscriptCanonicalizer.canonicalize(s) for s in subscripts
            ]
            data_code = base.defined(*canonical_subs)
            return data_code in (1, 11)

        return False

    def kill(self, name: str) -> None:
        """Remove variable and all descendants.

        Args:
            name: MUMPS variable name (may include subscripts)

        KILL A removes A and all A(subs)
        KILL A(1) removes A(1) and all A(1,subs) but not A or A(2)
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)
            self._kill_subscripted(base_name, subscripts)
            return

        py_name = NameTranslator.to_python(name)
        self._delete(py_name)

    def _kill_subscripted(self, name: str, subscripts: List[Any]) -> None:
        """Kill a subscripted variable node."""
        py_name = NameTranslator.to_python(name)
        base = self._lookup(py_name, None, mumps_name=name)

        if base is None:
            return

        # Use MArray's kill() if available - it properly removes the subtree
        if hasattr(base, "kill"):
            canonical_subs = [
                SubscriptCanonicalizer.canonicalize(s) for s in subscripts
            ]
            base.kill(*canonical_subs)

    @staticmethod
    def from_generated_context(
        _scope: Dict[str, Any], _locals: Optional[Dict[str, Any]] = None
    ) -> "CurrentScope":
        """Factory for use in generated code.

        Creates CurrentScope from the context available in generated functions.

        Args:
            _scope: The _scope parameter passed to generated functions
            _locals: Unused, kept for backward compatibility

        Returns:
            CurrentScope configured for the execution context
        """
        return CurrentScope(scope_dict=_scope)

    # Private helper methods

    def _lookup(self, py_name: str, default: Any, mumps_name: str | None = None) -> Any:
        """Look up a Python name in available storage mechanisms.

        Args:
            py_name: Python-translated variable name (e.g., '_pct_FOO')
            default: Value to return if not found
            mumps_name: Original MUMPS name (e.g., '%FOO') - try this first

        Returns:
            Variable value or default if not found

        Note: Some code paths store using MUMPS names, others use Python names.
        We try both to handle mixed conventions.
        """
        if self._scope_dict is not None:
            # Try MUMPS name first (for code that stores using MUMPS names)
            if mumps_name is not None and mumps_name in self._scope_dict:
                return self._scope_dict[mumps_name]
            # Then try Python name
            if py_name in self._scope_dict:
                return self._scope_dict[py_name]

        return default

    def _store(self, py_name: str, value: Any) -> None:
        """Store a value in the primary storage mechanism."""
        if self._scope_dict is not None:
            self._scope_dict[py_name] = value
        else:
            # No storage available - create scope_dict
            self._scope_dict = {}
            self._scope_dict[py_name] = value

    def _delete(self, py_name: str) -> None:
        """Delete a value from storage mechanisms."""
        if self._scope_dict is not None and py_name in self._scope_dict:
            del self._scope_dict[py_name]

    def _extract_value(self, obj: Any) -> Any:
        """Extract value from MArray if needed (FR-038)."""
        if obj is None:
            return ""  # MUMPS undefined = empty string

        if hasattr(obj, "value"):
            v = obj.value
            # Don't recurse if value is self (prevent infinite loop)
            if v is not obj:
                return self._extract_value(v)
            return v

        return obj

    def _is_array_like(self, obj: Any) -> bool:
        """Check if object supports subscript access."""
        return hasattr(obj, "__getitem__") and hasattr(obj, "__setitem__")

    def _parse_subscripted_name(self, name: str) -> Tuple[str, List[str]]:
        """Parse 'A(1,2)' into ('A', ['1', '2']).

        Delegates to core.parsing.parse_subscripted_name for the parsing,
        then strips MUMPS-style quotes from string subscripts.

        Examples:
            'A(1,2)' -> ('A', ['1', '2'])
            'B("key")' -> ('B', ['key'])
            'B("key","sub")' -> ('B', ['key', 'sub'])
        """
        base_name, raw_subs = parse_subscripted_name(name)
        # Strip MUMPS-style quotes from string subscripts
        return (base_name, [self._strip_subscript_quotes(s) for s in raw_subs])

    @staticmethod
    def _strip_subscript_quotes(s: str) -> str:
        """Strip surrounding double quotes and unescape doubled quotes.

        MUMPS subscript strings are quoted: '"key"' → 'key'.
        Escaped quotes ('""') are unescaped to single quotes.
        Non-quoted values are returned as-is.
        """
        if len(s) >= 2 and s.startswith('"') and s.endswith('"'):
            return s[1:-1].replace('""', '"')
        return s


# Sentinel for distinguishing "not found" from None
_SENTINEL = object()


__all__ = ["CurrentScope"]
