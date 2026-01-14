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
