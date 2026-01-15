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

# Spec 010: Import collation key and query helper for $ORDER/$QUERY
from m2py.runtime.helpers import _mumps_collation_key, _find_next_valued_node


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

    def order(self, name: str, subscripts: tuple[str, ...], direction: int = 1) -> str:
        """Return next/previous subscript at level.

        Spec 009 T062: Protocol stub for $ORDER function support.

        Args:
            name: Global name without caret
            subscripts: Current subscript path (last element is starting point)
            direction: 1 for forward, -1 for backward

        Returns:
            Next/previous subscript value at same level, or empty string if none.
        """
        ...

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data.

        Spec 009 T063: Protocol stub for $QUERY function support.

        Args:
            name: Global name without caret
            subscripts: Current subscript path

        Returns:
            Full global reference (e.g., "^G(1,2,3)") of next node with
            a value, or empty string if none.
        """
        ...

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts).

        Spec 009 T064: Protocol stub for $INCREMENT function support.

        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values
            increment: Amount to increment by (default "1")

        Returns:
            New value after increment (as string)

        Side Effects:
            Updates naked indicator
            Creates node with value "0" if undefined before incrementing
        """
        ...

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants.

        Spec 009 T065: Protocol stub for ZKILL/ZWITHDRAW support.

        Unlike kill(), this only removes the value at the specified node
        while keeping all descendant nodes intact.

        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values

        Side Effects:
            Updates naked indicator
            Removes only the value, not descendant nodes
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

    def order(self, name: str, subscripts: tuple[str, ...], direction: int = 1) -> str:
        """Return next/previous subscript in MUMPS collation order.

        Spec 010: Full implementation of $ORDER function.

        Args:
            name: Global name without caret
            subscripts: Tuple where last element is starting point. Use "" to get first/last.
            direction: 1 for forward (next), -1 for reverse (previous)

        Returns:
            Next/previous subscript as string, or "" if no more.

        MUMPS Collation Order:
            1. Negative numbers (most negative first)
            2. Zero
            3. Positive numbers (ascending)
            4. Strings (ASCII order)
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return ""

        if not subscripts:
            return ""

        # Navigate to parent level (all but last subscript)
        parent_subs = subscripts[:-1]
        start_key = subscripts[-1]

        node = self._globals[name]
        for sub in parent_subs:
            if sub not in node._children:
                return ""
            node = node._children[sub]

        # Get all children keys sorted in MUMPS collation order
        keys = sorted(node._children.keys(), key=_mumps_collation_key)

        if direction == -1:
            keys = list(reversed(keys))

        if start_key == "":
            # Empty string means get first key in current direction
            return keys[0] if keys else ""

        # Find next key after start_key in collation order
        start_sort_key = _mumps_collation_key(start_key)

        for key in keys:
            key_sort = _mumps_collation_key(key)
            if direction == 1:
                # Forward: find first key greater than start_key
                if key_sort > start_sort_key:
                    return str(key)
            else:
                # Reverse: find first key less than start_key
                if key_sort < start_sort_key:
                    return str(key)

        return ""

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data.

        Spec 010 Phase 2: Full implementation of $QUERY function.

        Args:
            name: Global name without caret
            subscripts: Current position subscripts. Use ("",) to start from beginning.

        Returns:
            Full variable reference string (e.g., "^G(1,2)"), or "" if no more nodes.
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return ""

        array = self._globals[name]

        # Check if we're starting from empty string (find first valued node)
        if subscripts == ("",) or subscripts == ():
            # Start from beginning - find first valued node in entire tree
            result = _find_next_valued_node(array, [], (), at_start=True)
        else:
            # Find next valued node after the given subscripts
            result = _find_next_valued_node(array, [], subscripts, at_start=False)

        if result is None:
            return ""

        # Format as global reference: "^G(1,2,3)"
        if len(result) == 0:
            return f"^{name}"
        return f"^{name}({','.join(result)})"

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts).

        Spec 009 T066: Stub implementation for $INCREMENT.
        Provides basic increment functionality.
        """
        subscripts = self._canonicalize_subscripts(subscripts)

        # Get current value (default to "0" if undefined)
        current = self.get(name, subscripts)
        if current is None:
            current = "0"

        # Attempt numeric increment
        try:
            current_num = float(current) if "." in current else int(current)
            incr_num = float(increment) if "." in increment else int(increment)
            result = current_num + incr_num
            # Format result: integer if whole number, else float
            if isinstance(result, float) and result == int(result):
                result_str = str(int(result))
            else:
                result_str = str(result)
        except ValueError:
            # Non-numeric value - treat as 0 per MUMPS semantics
            result_str = increment

        self.set(name, subscripts, result_str)
        return result_str

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants.

        Spec 009 T066: Implementation for ZKILL/ZWITHDRAW.
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return  # Nothing to kill

        node = self._globals[name]
        if not subscripts:
            # Kill value at root, preserve children
            node._value = None
            return

        # Navigate to target node
        for sub in subscripts:
            if sub not in node._children:
                return  # Path doesn't exist
            node = node._children[sub]

        # Remove only the value, preserve children
        node._value = None


# =============================================================================
# Backend Stub Classes
# =============================================================================


class YottaDBGlobalStorage:
    """YottaDB global storage backend stub.

    Spec 009 T067: Stub class for YottaDB integration.
    Full implementation will be provided in a future spec.

    Requires the 'yottadb' Python package which provides bindings
    to the YottaDB database engine.
    """

    def __init__(self) -> None:
        """Initialize YottaDB connection.

        Raises:
            ImportError: yottadb package not available
        """
        try:
            import yottadb  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "YottaDB backend requires the 'yottadb' package. "
                "Install with: pip install yottadb"
            ) from e

        self._naked_indicator: tuple[str, tuple[str, ...]] | None = None

    def get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get value at ^NAME(subscripts). Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts). Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and descendants. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def kill_all(self) -> None:
        """Kill all globals. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Get current naked indicator."""
        return self._naked_indicator

    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Set naked indicator explicitly."""
        self._naked_indicator = (name, subscripts)

    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """Resolve naked reference."""
        if self._naked_indicator is None:
            raise RuntimeError("NAKEDERR: Naked reference without prior global access")
        name, base_subscripts = self._naked_indicator
        return (name, base_subscripts + subscripts)

    def order(self, name: str, subscripts: tuple[str, ...], direction: int = 1) -> str:
        """Return next/previous subscript. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return next node reference. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only node value. Stub raises NotImplementedError."""
        raise NotImplementedError("YottaDB backend not yet implemented")


class IRISGlobalStorage:
    """InterSystems IRIS global storage backend stub.

    Spec 009 T068: Stub class for IRIS integration.
    Full implementation will be provided in a future spec.

    Requires the 'intersystems-iris' Python package for connection
    to InterSystems IRIS database.
    """

    def __init__(
        self,
        hostname: str = "localhost",
        port: int = 1972,
        namespace: str = "USER",
        username: str = "_SYSTEM",
        password: str = "",
    ) -> None:
        """Initialize IRIS connection.

        Args:
            hostname: IRIS server hostname
            port: IRIS SuperServer port (default 1972)
            namespace: IRIS namespace to use
            username: IRIS username
            password: IRIS password

        Raises:
            ImportError: intersystems-iris package not available
        """
        try:
            import iris  # noqa: F401
        except ImportError as e:
            raise ImportError(
                "IRIS backend requires the 'intersystems-iris' package. "
                "Install with: pip install intersystems-iris"
            ) from e

        self._hostname = hostname
        self._port = port
        self._namespace = namespace
        self._username = username
        self._password = password
        self._naked_indicator: tuple[str, tuple[str, ...]] | None = None

    def get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get value at ^NAME(subscripts). Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts). Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and descendants. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def kill_all(self) -> None:
        """Kill all globals. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Get current naked indicator."""
        return self._naked_indicator

    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Set naked indicator explicitly."""
        self._naked_indicator = (name, subscripts)

    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """Resolve naked reference."""
        if self._naked_indicator is None:
            raise RuntimeError("NAKEDERR: Naked reference without prior global access")
        name, base_subscripts = self._naked_indicator
        return (name, base_subscripts + subscripts)

    def order(self, name: str, subscripts: tuple[str, ...], direction: int = 1) -> str:
        """Return next/previous subscript. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return next node reference. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only node value. Stub raises NotImplementedError."""
        raise NotImplementedError("IRIS backend not yet implemented")
