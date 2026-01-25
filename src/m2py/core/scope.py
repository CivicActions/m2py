"""Unified variable access abstraction.

This module provides the CurrentScope class for unified variable access
across different storage mechanisms (Python locals, _scope dict, state._locals),
and the VarRef dataclass for structured variable references.

Constitution VII: All variable access (static or indirected) uses the same path,
preventing "variable not found" bugs that occur when codegen uses Python locals
but runtime uses _scope dict.

Feature: 018-unified-variable-system
Requirements: FR-001 (VarRef), FR-036, FR-037, FR-038 (CurrentScope)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from m2py.core.names import NameTranslator
from m2py.core.subscripts import SubscriptCanonicalizer


@dataclass
class VarRef:
    """Unified variable reference representation.

    Captures all forms of MUMPS variable references:
    - Local: X, X(1,2)
    - Global: ^GLO, ^GLO(1,2), ^(subs) (naked)

    This structure is used by:
    1. Codegen: To determine generation strategy (inline vs runtime call)
    2. Runtime: To resolve variable access at execution time
    """

    # Base identification
    name: Optional[str] = None  # Variable name (None if purely indirected)
    is_global: bool = False  # True for ^NAME
    is_naked: bool = False  # True for ^(subs) naked reference

    # Subscripts
    subscripts: List[Any] = field(default_factory=list)

    # Pre-computed Python identifier (set during construction or analysis)
    python_name: Optional[str] = None

    def __post_init__(self) -> None:
        """Compute python_name if not provided."""
        if self.python_name is None and self.name:
            self.python_name = NameTranslator.to_python(self.name)

    def to_access_string(self) -> str:
        """Convert to MUMPS-style access string for runtime.

        Examples:
            VarRef(name="X") → "X"
            VarRef(name="X", subscripts=[1,2]) → "X(1,2)"
            VarRef(is_global=True, name="GLO") → "^GLO"
            VarRef(is_global=True, is_naked=True, subscripts=[1]) → "^(1)"
        """
        parts = []

        # Global prefix
        if self.is_global:
            parts.append("^")

        # Name (unless naked reference)
        if self.is_naked:
            pass  # No name for naked references
        elif self.name:
            parts.append(self.name)

        # Subscripts
        if self.subscripts:
            subs_str = ",".join(
                SubscriptCanonicalizer.canonicalize(s) for s in self.subscripts
            )
            parts.append(f"({subs_str})")

        return "".join(parts)

    def with_subscripts(self, additional_subscripts: List[Any]) -> "VarRef":
        """Return a new VarRef with additional subscripts appended."""
        return VarRef(
            name=self.name,
            is_global=self.is_global,
            is_naked=self.is_naked,
            subscripts=self.subscripts + additional_subscripts,
            python_name=self.python_name,
        )


class CurrentScope:
    """Unified variable access abstraction.

    This adapter unifies:
    - Python locals (PURE_FUNCTION strategy)
    - _scope dict (FUNCTION_WITH_OUTPUTS, SUBROUTINE strategies)
    - state._locals (REQUIRES_RUNTIME strategy)

    FR-036, FR-037: Provides the "Current Scope" abstraction from spec.
    FR-038: Automatically extracts .value from MArray objects.
    """

    def __init__(
        self,
        scope_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None,
        state_locals: Optional[Any] = None,  # MArray type
        name_translator: Optional[NameTranslator] = None,
    ):
        """Initialize scope with available storage mechanisms.

        Args:
            scope_dict: The _scope dict passed through generated code
            locals_dict: Python locals() for PURE_FUNCTION access
            state_locals: state._locals MArray for REQUIRES_RUNTIME
            name_translator: Optional custom translator (defaults to standard)

        At least one storage mechanism should be provided for useful operation.
        Lookup order: scope_dict > locals_dict > state_locals
        """
        self._scope_dict = scope_dict
        self._locals_dict = locals_dict
        self._state_locals = state_locals
        self._name_translator = name_translator or NameTranslator()

        # Primary storage is first non-None mechanism
        self._primary = (
            scope_dict
            if scope_dict is not None
            else (locals_dict if locals_dict is not None else state_locals)
        )

    def get(self, name: str, default: Any = "") -> Any:
        """Get variable value by MUMPS name.

        Args:
            name: MUMPS variable name (e.g., "X", "%FOO", "A(1,2)")
            default: Value to return if not found (MUMPS undefined = "")

        Returns:
            Variable value, or default if undefined

        Note: Handles subscripted names by parsing and traversing.
        FR-038: Extracts .value from MArray objects automatically.
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)
            return self.get_subscripted(base_name, subscripts, default)

        # Translate MUMPS name to Python identifier
        py_name = NameTranslator.to_python(name)

        # Look up in storage mechanisms
        value = self._lookup(py_name, default)

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

        Example:
            get_subscripted("A", [1, 2]) → value of A(1,2)
        """
        py_name = NameTranslator.to_python(name)
        base = self._lookup(py_name, None)

        if base is None:
            return default

        # Navigate through subscripts
        current = base
        for sub in subscripts:
            canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
            if hasattr(current, "__getitem__"):
                try:
                    current = current[canonical_sub]
                except (KeyError, IndexError, TypeError):
                    return default
            elif hasattr(current, "get"):
                current = current.get(canonical_sub, None)
                if current is None:
                    return default
            else:
                return default

        return self._extract_value(current)

    def set(self, name: str, value: Any) -> None:
        """Set variable value by MUMPS name.

        Args:
            name: MUMPS variable name (may include subscripts)
            value: Value to set

        Creates intermediate MArray structures as needed for subscripted vars.
        """
        # Handle subscripted names
        if "(" in name:
            base_name, subscripts = self._parse_subscripted_name(name)
            self.set_subscripted(base_name, subscripts, value)
            return

        # Translate MUMPS name to Python identifier
        py_name = NameTranslator.to_python(name)

        # Store in primary storage
        self._store(py_name, value)

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
        base = self._lookup(py_name, None)

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
            else:
                # Can't navigate further
                raise ValueError(f"Cannot set subscript on non-array value at {name}")

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
        return self._lookup(py_name, _SENTINEL) is not _SENTINEL

    def _exists_subscripted(self, name: str, subscripts: List[Any]) -> bool:
        """Check if subscripted variable exists (has value)."""
        py_name = NameTranslator.to_python(name)
        base = self._lookup(py_name, None)

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

        # Fallback for regular dicts/other structures
        current = base
        for sub in subscripts:
            canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
            if hasattr(current, "__contains__"):
                if canonical_sub not in current:
                    return False
                current = current[canonical_sub]
            elif hasattr(current, "get"):
                current = current.get(canonical_sub, _SENTINEL)
                if current is _SENTINEL:
                    return False
            else:
                return False

        # For MArray nodes, check if it has a value (not just children)
        if hasattr(current, "_value"):
            return current._value is not None

        return True

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
        base = self._lookup(py_name, None)

        if base is None:
            return

        # Use MArray's kill() if available - it properly removes the subtree
        if hasattr(base, "kill"):
            canonical_subs = [
                SubscriptCanonicalizer.canonicalize(s) for s in subscripts
            ]
            base.kill(*canonical_subs)
            return

        # Fallback for regular dicts/other structures
        # Navigate to parent
        current = base
        for sub in subscripts[:-1]:
            canonical_sub = SubscriptCanonicalizer.canonicalize(sub)
            if hasattr(current, "__getitem__"):
                try:
                    current = current[canonical_sub]
                except (KeyError, IndexError):
                    return  # Path doesn't exist
            else:
                return

        # Delete final node
        final_sub = SubscriptCanonicalizer.canonicalize(subscripts[-1])
        if hasattr(current, "__delitem__"):
            try:
                del current[final_sub]
            except (KeyError, IndexError):
                pass  # Already doesn't exist

    @staticmethod
    def from_generated_context(
        _scope: Dict[str, Any], _locals: Optional[Dict[str, Any]] = None
    ) -> "CurrentScope":
        """Factory for use in generated code.

        Creates CurrentScope from the context available in generated functions.

        Args:
            _scope: The _scope parameter passed to generated functions
            _locals: Result of locals() call, if available

        Returns:
            CurrentScope configured for the execution context
        """
        return CurrentScope(scope_dict=_scope, locals_dict=_locals)

    # Private helper methods

    def _lookup(self, py_name: str, default: Any) -> Any:
        """Look up a Python name in available storage mechanisms."""
        # Check scope_dict first
        if self._scope_dict is not None:
            if py_name in self._scope_dict:
                return self._scope_dict[py_name]

        # Check locals_dict second
        if self._locals_dict is not None:
            if py_name in self._locals_dict:
                return self._locals_dict[py_name]

        # Check state_locals last
        if self._state_locals is not None:
            if hasattr(self._state_locals, "__contains__"):
                if py_name in self._state_locals:
                    return self._state_locals[py_name]

        return default

    def _store(self, py_name: str, value: Any) -> None:
        """Store a value in the primary storage mechanism."""
        if self._scope_dict is not None:
            self._scope_dict[py_name] = value
        elif self._locals_dict is not None:
            self._locals_dict[py_name] = value
        elif self._state_locals is not None:
            self._state_locals[py_name] = value
        else:
            # No storage available - create scope_dict
            self._scope_dict = {}
            self._scope_dict[py_name] = value

    def _delete(self, py_name: str) -> None:
        """Delete a value from storage mechanisms."""
        if self._scope_dict is not None and py_name in self._scope_dict:
            del self._scope_dict[py_name]
        if self._locals_dict is not None and py_name in self._locals_dict:
            del self._locals_dict[py_name]
        if self._state_locals is not None:
            if hasattr(self._state_locals, "__delitem__"):
                try:
                    del self._state_locals[py_name]
                except (KeyError, AttributeError):
                    pass

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

        Handles simple cases. Complex nested parentheses or quoted strings
        would need more sophisticated parsing.
        """
        paren_idx = name.find("(")
        if paren_idx == -1:
            return (name, [])

        base_name = name[:paren_idx]

        # Extract content between outer parentheses
        if not name.endswith(")"):
            # Malformed - return as-is
            return (name, [])

        subs_str = name[paren_idx + 1 : -1]

        # Simple split by comma (doesn't handle nested parens in subscripts)
        # For complex cases, would need recursive parsing
        if not subs_str:
            return (base_name, [])

        subscripts = [s.strip() for s in subs_str.split(",")]
        return (base_name, subscripts)


# Sentinel for distinguishing "not found" from None
_SENTINEL = object()


__all__ = ["CurrentScope", "VarRef"]
