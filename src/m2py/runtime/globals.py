"""Global variable storage backends for MUMPS global references.

Spec 009: Provides GlobalStorageBackend protocol and implementations for
persisting global variables (^NAME). Default is InMemoryGlobalStorage
for testing and standalone execution.

Backend selection via M2PY_GLOBAL_BACKEND environment variable:
- 'inmemory' (default): In-memory storage using MArray
- 'yottadb': YottaDB native backend (requires yottadb package)
- 'iris': InterSystems IRIS backend (requires intersystems-iris package)

Production backends (yottadb, iris) are stubs that raise ImportError
until integration specs implement them.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class GlobalStorageBackend(Protocol):
    """Protocol for MUMPS global variable storage backends.

    Implementations must provide persistent (or in-memory) storage
    for global variables with support for hierarchical subscripts,
    $DATA introspection, KILL operations, and naked reference tracking.

    Naked Indicator Semantics:
        After ^G(1,2,3):
            naked_indicator = ("G", ("1", "2"))  # First n-1 subscripts
        ^(4) resolves to ^G(1,2,4)

        After ^G (no subscripts):
            naked_indicator = ("G", ())
        ^(1) resolves to ^G(1)
    """

    def get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get value at ^NAME(subscripts).

        Args:
            name: Global name without caret (e.g., "PATIENT")
            subscripts: Tuple of string subscript values, may be empty

        Returns:
            String value if defined, None if undefined

        Side Effects:
            Updates naked indicator to (name, subscripts[:-1]) if subscripts
            non-empty, else (name, ())
        """
        ...

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts).

        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values, may be empty
            value: String value to store (MUMPS values are always strings)

        Side Effects:
            Updates naked indicator to (name, subscripts[:-1]) if subscripts
            non-empty, else (name, ())
            Creates intermediate nodes if needed (auto-vivification)
        """
        ...

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants at ^NAME(subscripts).

        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values
                       Empty tuple kills entire global tree

        Side Effects:
            Updates naked indicator
            Removes value AND all descendant nodes
        """
        ...

    def kill_all(self) -> None:
        """Kill all globals. Used for testing/reset.

        Side Effects:
            Clears all global data
            Clears naked indicator
        """
        ...

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value for ^NAME(subscripts).

        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values

        Returns:
            0 - Undefined, no descendants
            1 - Defined, no descendants
            10 - Undefined, has descendants
            11 - Defined AND has descendants

        Side Effects:
            Updates naked indicator
        """
        ...

    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Get current naked indicator for ^(subscripts) resolution.

        Returns:
            Tuple of (global_name, base_subscripts) or None if no prior
            global access in current context.
        """
        ...

    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Set naked indicator explicitly.

        Args:
            name: Global name to set as base
            subscripts: Base subscripts (first n-1 of full subscript path)
        """
        ...

    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """Resolve naked reference ^(subscripts) to full global reference.

        Args:
            subscripts: Subscripts from naked reference ^(subscripts)

        Returns:
            Tuple of (global_name, full_subscripts)

        Raises:
            RuntimeError: If no prior global access (naked indicator not set)
        """
        ...


# =============================================================================
# InMemoryGlobalStorage Implementation
# =============================================================================


class InMemoryGlobalStorage:
    """In-memory global storage for testing and standalone execution.

    Spec 009 (T006-T007): Implements GlobalStorageBackend protocol using
    MArray structures for hierarchical storage. Not thread-safe.

    The naked indicator tracks the base for naked references:
    - After ^G(1,2,3): indicator = ("G", ("1", "2")) -> ^(4) = ^G(1,2,4)
    - After ^G(1): indicator = ("G", ()) -> ^(2) = ^G(2)
    - After ^G (no subscripts): indicator = None (naked refs illegal)
    """

    def __init__(self) -> None:
        """Initialize empty global storage."""
        from m2py.runtime import MArray

        self._globals: dict[str, MArray] = {}
        self._naked_indicator: tuple[str, tuple[str, ...]] | None = None

    def _canonicalize_subscript(self, subscript: str | int | float) -> str:
        """Convert subscript to canonical string form.

        MUMPS subscripts are always strings internally. Numbers are
        converted to their canonical string representation.
        """
        return str(subscript)

    def _canonicalize_subscripts(
        self, subscripts: tuple[str | int | float, ...]
    ) -> tuple[str, ...]:
        """Convert all subscripts to canonical string form."""
        return tuple(self._canonicalize_subscript(s) for s in subscripts)

    def _update_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Update naked indicator after global access.

        Args:
            name: Global name
            subscripts: Full subscript path

        The naked indicator becomes (name, subscripts[:-1]) for use
        in subsequent naked references. If subscripts is empty,
        the naked indicator becomes None (naked refs are illegal after
        accessing a global with no subscripts).
        """
        if subscripts:
            # After ^G(1,2,3): indicator = ("G", ("1", "2"))
            self._naked_indicator = (name, subscripts[:-1])
        else:
            # After ^G (no subscripts): naked refs are illegal
            self._naked_indicator = None

    def get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get value at ^NAME(subscripts)."""

        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return None

        node = self._globals[name]
        if not subscripts:
            return node._value

        # Navigate to subscript path
        for sub in subscripts:
            if sub not in node._children:
                return None
            node = node._children[sub]

        return node._value

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts)."""
        from m2py.runtime import MArray

        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        # Auto-vivify global if not exists
        if name not in self._globals:
            self._globals[name] = MArray()

        node = self._globals[name]
        if not subscripts:
            node._value = value
            return

        # Navigate to subscript path, auto-vivifying as needed
        for sub in subscripts[:-1]:
            if sub not in node._children:
                node._children[sub] = MArray()
            node = node._children[sub]

        # Set value at final subscript
        last_sub = subscripts[-1]
        if last_sub not in node._children:
            node._children[last_sub] = MArray()
        node._children[last_sub]._value = value

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return  # Nothing to kill

        if not subscripts:
            # Kill entire global
            del self._globals[name]
            return

        # Navigate to parent of target
        node = self._globals[name]
        for sub in subscripts[:-1]:
            if sub not in node._children:
                return  # Path doesn't exist
            node = node._children[sub]

        # Remove target and all its descendants
        last_sub = subscripts[-1]
        if last_sub in node._children:
            del node._children[last_sub]

    def kill_all(self) -> None:
        """Kill all globals and reset naked indicator."""
        self._globals.clear()
        self._naked_indicator = None

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value for ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return 0

        node = self._globals[name]
        if subscripts:
            for sub in subscripts:
                if sub not in node._children:
                    return 0
                node = node._children[sub]

        has_value = node._value is not None
        has_children = bool(node._children)

        if has_value and has_children:
            return 11
        elif has_children:
            return 10
        elif has_value:
            return 1
        else:
            return 0

    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Get current naked indicator."""
        return self._naked_indicator

    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Set naked indicator explicitly."""
        self._naked_indicator = (name, self._canonicalize_subscripts(subscripts))

    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """Resolve naked reference ^(subscripts) to full global reference.

        Args:
            subscripts: Subscripts from naked reference

        Returns:
            Tuple of (name, full_subscripts)

        Raises:
            RuntimeError: If naked indicator is not set
        """
        if self._naked_indicator is None:
            raise RuntimeError("NAKEDERR: Naked reference without prior global access")

        name, base_subscripts = self._naked_indicator
        subscripts = self._canonicalize_subscripts(subscripts)
        full_subscripts = base_subscripts + subscripts
        return (name, full_subscripts)
