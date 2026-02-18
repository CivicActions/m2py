"""Global variable storage backends for MUMPS global references.

Provides GlobalStorageBackend protocol and implementations for
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

from typing import TYPE_CHECKING, Protocol, runtime_checkable

# Import collation key and query helper for $ORDER/$QUERY
from m2py.runtime.helpers import (
    _mumps_collation_key,
    _find_next_valued_node,
    m_format_output,
)

# Use SubscriptCanonicalizer for proper subscript handling
from m2py.core.subscripts import SubscriptCanonicalizer

if TYPE_CHECKING:
    from m2py.runtime import MArray


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

    def get(
        self, name: str, subscripts: tuple[str, ...], update_naked: bool = True
    ) -> str | None:
        """Get value at ^NAME(subscripts).

        Args:
            name: Global name without caret (e.g., "PATIENT")
            subscripts: Tuple of string subscript values, may be empty
            update_naked: If True, update the naked indicator (default).
                If False, skip naked update (caller handled it).

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

    @property
    def last_global_ref(self) -> str:
        """Return the last global reference string ($ZREFERENCE).

        Returns:
            Formatted reference like "^NAME(sub1,sub2)" or "" if no
            global has been accessed yet.
        """
        ...

    def set_order_naked(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Pre-set naked indicator for $ORDER evaluation ordering.

        Sets the naked indicator as if ^NAME(subscripts) had been accessed.
        Used by $ORDER codegen to ensure correct naked state when the
        direction argument contains global references that override naked.

        Args:
            name: Global name without caret
            subscripts: Full subscript path (last element stripped per naked rules)
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

    def order(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        update_naked: bool = True,
    ) -> str:
        """Return next/previous subscript at level.

        Args:
            name: Global name without caret
            subscripts: Current subscript path (last element is starting point)
            direction: 1 for forward, -1 for backward
            update_naked: If True, update the naked indicator (default).
                If False, skip naked update (caller handled it).

        Returns:
            Next/previous subscript value at same level, or empty string if none.
        """
        ...

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data.

        Args:
            name: Global name without caret
            subscripts: Current subscript path

        Returns:
            Full global reference (e.g., "^G(1,2,3)") of next node with
            a value, or empty string if none.
        """
        ...

    def get_tree(self, name: str, subscripts: tuple[str, ...]) -> "MArray | None":
        """Get subtree as MArray for MERGE source.

        Protocol for MERGE global-to-local and global-to-global.

        Args:
            name: Global name without caret
            subscripts: Path to the subtree root

        Returns:
            MArray containing the subtree, or None if undefined.
        """
        ...

    def merge_tree(
        self, name: str, subscripts: tuple[str, ...], source: "MArray"
    ) -> None:
        """Merge MArray tree into global at ^NAME(subscripts).

        Protocol for MERGE local-to-global and global-to-global.

        Args:
            name: Global name without caret
            subscripts: Path to the destination root
            source: MArray containing the source tree to merge
        """
        ...

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts).

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

    # =========================================================================
    # Lock Operations
    # =========================================================================

    def lock(
        self,
        name: str,
        subscripts: tuple[str, ...],
        timeout: float | None = None,
        lock_type: str = "+",
    ) -> bool:
        """Acquire or release a lock on ^NAME(subscripts).

        Args:
            name: Global/lock name without caret (e.g., "PATIENT")
            subscripts: Tuple of string subscript values
            timeout: Timeout in seconds, None for indefinite wait
            lock_type: "+" for increment (acquire), "-" for decrement (release)

        Returns:
            True if lock acquired/released successfully, False on timeout

        Side Effects:
            Sets $TEST to 1 on success, 0 on timeout (when timeout specified)
        """
        ...

    def unlock(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Release a lock on ^NAME(subscripts).

        Args:
            name: Global/lock name without caret
            subscripts: Tuple of string subscript values

        Behavior:
            Decrements lock count, releases when count reaches 0.
        """
        ...

    def unlock_all(self) -> None:
        """Release all locks held by current process."""
        ...

    def get_locks(self) -> list[tuple[str, str, int]]:
        """Return all locks held by the current process/thread.

        Returns list of (lock_name, json_subscripts, lock_count) tuples.

        Returns:
            List of (name, subscripts_json, count) for current owner
        """
        ...

    # =========================================================================
    # Transaction Operations
    # =========================================================================

    def transaction_start(self) -> None:
        """Begin a transaction (TSTART).

        Initiates a new transaction or increments
        transaction nesting level.

        Behavior:
            - Increments $TLEVEL
            - Takes snapshot for rollback (Memory backend)
            - Begins native transaction (YDB/IRIS backends)
        """
        ...

    def transaction_commit(self) -> None:
        """Commit current transaction (TCOMMIT).

        Commits or decrements transaction level.

        Behavior:
            - If $TLEVEL = 1, commits the transaction
            - If $TLEVEL > 1, decrements $TLEVEL only

        Raises:
            RuntimeError: If $TLEVEL = 0 (M44 error)
        """
        ...

    def transaction_rollback(self) -> None:
        """Rollback current transaction (TROLLBACK).

        Reverts changes since matching TSTART.

        Behavior:
            - Reverts changes since TSTART
            - Sets $TLEVEL = 0

        Raises:
            RuntimeError: If $TLEVEL = 0 (M44 error)
        """
        ...

    def get_tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL).

        Returns:
            Current transaction nesting level (0 = no transaction)
        """
        ...

    # =========================================================================
    # SSVN Queries
    # =========================================================================

    def ssvn_global(self, subscript: str) -> str:
        """Query ^$GLOBAL(name) for global existence.

        Args:
            subscript: Global name to query

        Returns:
            Non-empty string if global exists, empty string otherwise
        """
        ...

    def ssvn_job(self, subscript: str) -> str:
        """Query ^$JOB(pid) for job/process information.

        Args:
            subscript: Process ID to query

        Returns:
            Process information string
        """
        ...

    def ssvn_lock(self, subscript: str) -> str:
        """Query ^$LOCK(lockname) for lock information.

        Args:
            subscript: Lock name to query

        Returns:
            Lock owner/status information
        """
        ...

    def ssvn_routine(self, subscript: str) -> str:
        """Query ^$ROUTINE(routinename) for routine metadata.

        Args:
            subscript: Routine name to query

        Returns:
            Routine metadata (source path, compile date, etc.)
        """
        ...


# =============================================================================
# InMemoryGlobalStorage Implementation
# =============================================================================


class InMemoryGlobalStorage:
    """In-memory global storage for testing and standalone execution.

    Implements GlobalStorageBackend protocol using
    MArray structures for hierarchical storage.

    Includes lock table, transaction support, and SSVN queries.

    Lock operations are simple single-process dict operations. For cross-process
    lock semantics (blocking, timeout, process isolation), use SQLiteGlobalStorage.

    The naked indicator tracks the base for naked references:
    - After ^G(1,2,3): indicator = ("G", ("1", "2")) -> ^(4) = ^G(1,2,4)
    - After ^G(1): indicator = ("G", ()) -> ^(2) = ^G(2)
    - After ^G (no subscripts): indicator = None (naked refs illegal)
    """

    def __init__(self) -> None:
        """Initialize empty global storage."""
        self._globals: dict[str, MArray] = {}
        # Naked indicator (single-process, no threading needed)
        self._naked_indicator_value: tuple[str, tuple[str, ...]] | None = None

        # Lock table - maps (name, subscripts) to (owner_pid, count)
        # Simple dict — no blocking, no threading. Single-process only.
        self._lock_table: dict[tuple[str, tuple[str, ...]], tuple[int, int]] = {}

        # Transaction support
        self._tlevel: int = 0
        self._transaction_snapshots: list[dict[str, MArray]] = []

        # $ZREFERENCE — last global reference string (e.g. "^ZZTEST(1,2)")
        self._last_global_ref: str = ""

    @property
    def _naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Naked indicator for global reference resolution."""
        return self._naked_indicator_value

    @_naked_indicator.setter
    def _naked_indicator(self, value: tuple[str, tuple[str, ...]] | None) -> None:
        self._naked_indicator_value = value

    @property
    def last_global_ref(self) -> str:
        """Return the last global reference string ($ZREFERENCE)."""
        return self._last_global_ref

    def _canonicalize_subscript(self, subscript: str | int | float) -> str:
        """Convert subscript to MUMPS canonical string form.

        MUMPS subscripts are always strings internally. Numbers are
        converted to their MUMPS canonical string representation
        (e.g., 0.001 → ".001", 1.0 → "1").

        Non-canonical numeric strings like "01" are PRESERVED because
        they represent different nodes than their canonical equivalents.
        e.g., ^A("01") is a different node than ^A(1).

        Uses SubscriptCanonicalizer for proper MUMPS semantics.
        """
        return SubscriptCanonicalizer.canonicalize(subscript)

    def _canonicalize_subscripts(
        self, subscripts: tuple[str | int | float, ...]
    ) -> tuple[str, ...]:
        """Convert all subscripts to canonical string form."""
        return tuple(self._canonicalize_subscript(s) for s in subscripts)

    def _update_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Update naked indicator after global access.

        Also updates $ZREFERENCE (last global reference string).

        Args:
            name: Global name
            subscripts: Full subscript path

        The naked indicator becomes (name, subscripts[:-1]) for use
        in subsequent naked references. If subscripts is empty,
        the naked indicator becomes None (naked refs are illegal after
        accessing a global with no subscripts).
        """
        # Update $ZREFERENCE — format as ^NAME or ^NAME(sub1,sub2,...)
        if subscripts:
            subs_str = ",".join(
                f'"{s}"' if not s.lstrip("-").isdigit() else s for s in subscripts
            )
            self._last_global_ref = f"^{name}({subs_str})"
        else:
            self._last_global_ref = f"^{name}"

        if subscripts:
            # After ^G(1,2,3): indicator = ("G", ("1", "2"))
            self._naked_indicator = (name, subscripts[:-1])
        else:
            # After ^G (no subscripts): naked refs are illegal
            self._naked_indicator = None

    def get(
        self, name: str, subscripts: tuple[str, ...], update_naked: bool = True
    ) -> str | None:
        """Get value at ^NAME(subscripts)."""

        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
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
        """Kill node and all descendants at ^NAME(subscripts).

        After killing, cleans up empty ancestor nodes (nodes with no value
        and no children). This is required by MUMPS semantics - after
        KILL ^V1(2,1), if ^V1(2) has no value and no other children,
        $DATA(^V1(2)) should return 0.
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return  # Nothing to kill

        if not subscripts:
            # Kill entire global
            del self._globals[name]
            return

        # Collect path of nodes for cleanup
        path: list[tuple["MArray", str]] = []  # (parent, child_key)
        node = self._globals[name]

        # Navigate to parent of target, collecting path
        for sub in subscripts[:-1]:
            if sub not in node._children:
                return  # Path doesn't exist
            path.append((node, sub))
            node = node._children[sub]

        # Remove target and all its descendants
        last_sub = subscripts[-1]
        if last_sub in node._children:
            del node._children[last_sub]

        # Clean up empty ancestor nodes (reverse order - leaf to root)
        # Node is empty if it has no value AND no children
        while path:
            parent, child_key = path.pop()
            child = parent._children[child_key]
            if child._value is None and not child._children:
                del parent._children[child_key]
            else:
                break  # Stop if we hit a non-empty node

        # Finally, check if the global root itself is now empty
        root = self._globals[name]
        if root._value is None and not root._children:
            del self._globals[name]

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

    def set_order_naked(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Pre-set naked indicator for $ORDER evaluation ordering."""
        subs = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subs)

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

    def order(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        update_naked: bool = True,
    ) -> str:
        """Return next/previous subscript in MUMPS collation order.

        Full implementation of $ORDER function.

        Args:
            name: Global name without caret
            subscripts: Tuple where last element is starting point. Use "" to get first/last.
            direction: 1 for forward (next), -1 for reverse (previous)
            update_naked: If True, update the naked indicator (default).
                If False, skip naked update (caller handled it).

        Returns:
            Next/previous subscript as string, or "" if no more.

        MUMPS Collation Order:
            1. Negative numbers (most negative first)
            2. Zero
            3. Positive numbers (ascending)
            4. Strings (ASCII order)
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
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
            return m_format_output(keys[0]) if keys else ""

        # Find next key after start_key in collation order
        start_sort_key = _mumps_collation_key(start_key)

        for key in keys:
            key_sort = _mumps_collation_key(key)
            if direction == 1:
                # Forward: find first key greater than start_key
                if key_sort > start_sort_key:
                    return m_format_output(key)
            else:
                # Reverse: find first key less than start_key
                if key_sort < start_sort_key:
                    return m_format_output(key)

        return ""

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data.

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

        # Format as global reference: "^G(1,2,3)" with proper quoting
        from m2py.runtime.helpers import _format_subscript

        if len(result) == 0:
            return f"^{name}"
        formatted_subs = [_format_subscript(sub) for sub in result]
        return f"^{name}({','.join(formatted_subs)})"

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants."""
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

    def get_tree(self, name: str, subscripts: tuple[str, ...]) -> "MArray | None":
        """Get subtree rooted at ^NAME(subscripts) as MArray for MERGE.

        Args:
            name: Global name without caret
            subscripts: Path to the subtree root (empty for root)

        Returns:
            MArray containing the subtree, or None if path doesn't exist
        """

        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if name not in self._globals:
            return None

        node = self._globals[name]
        if subscripts:
            for sub in subscripts:
                if sub not in node._children:
                    return None
                node = node._children[sub]

        # Deep copy the subtree
        return self._deep_copy_tree(node)

    def merge_tree(
        self, name: str, subscripts: tuple[str, ...], source: "MArray"
    ) -> None:
        """Merge MArray tree into global at ^NAME(subscripts).

        Copies all nodes with values from source tree into global destination.
        Does not delete existing nodes - only adds/overwrites values.

        Args:
            name: Global name without caret
            subscripts: Path to the destination root (empty for root)
            source: MArray containing the source tree to merge
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        # Recursively merge source tree into global
        self._merge_tree_recursive(name, subscripts, source)

    def _merge_tree_recursive(
        self, name: str, subscripts: tuple[str, ...], node: "MArray"
    ) -> None:
        """Recursively merge MArray node into global storage.

        Args:
            name: Global name without caret
            subscripts: Current subscript path
            node: MArray node to merge
        """
        # If this node has a value, set it in the global
        if node._value is not None:
            self.set(name, subscripts, node._value)

        # Recursively merge children
        for key, child in node._children.items():
            # Convert key to string for global subscript
            child_sub = str(key)
            self._merge_tree_recursive(name, subscripts + (child_sub,), child)

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts).

        Single-process: no locking needed.

        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values
            increment: Amount to increment by (default "1")

        Returns:
            New value after increment (as string, MUMPS canonical form)

        Side Effects:
            Updates naked indicator
            Creates node with value "0" if undefined before incrementing
        """
        from m2py.core.values import m_num, m_str

        subscripts = self._canonicalize_subscripts(subscripts)

        # Get current value (default to "0" if undefined)
        current = self.get(name, subscripts)
        if current is None:
            current = "0"

        # MUMPS numeric coercion + addition
        current_num = m_num(current)
        incr_num = m_num(increment)
        result = current_num + incr_num  # type: ignore[operator]

        # Normalize: integer if whole number
        if isinstance(result, float) and result == int(result):
            result = int(result)

        result_str = m_str(result)
        self.set(name, subscripts, result_str)
        return result_str

    def kill_all(self) -> None:
        """Kill all globals. Used for testing/reset.

        Side Effects:
            Clears all global data
            Clears naked indicator
        """
        self._globals.clear()
        self._update_naked_indicator("", ())

    # =========================================================================
    # Lock Operations
    # =========================================================================

    def lock(
        self,
        name: str,
        subscripts: tuple[str, ...],
        timeout: float | None = None,
        lock_type: str = "+",
    ) -> bool:
        """Acquire or release a lock on ^NAME(subscripts).

        Simple single-process lock implementation.
        Locks are owned by os.getpid(). No blocking — in a single-process
        environment, all locks are owned by the same PID and always succeed.

        For cross-process lock semantics with blocking and timeout,
        use SQLiteGlobalStorage instead.

        Args:
            name: Global/lock name without caret
            subscripts: Tuple of string subscript values
            timeout: Seconds to wait for lock (ignored in single-process mode)
            lock_type: "+" for increment (acquire), "-" for decrement (release)

        Returns:
            True if lock acquired/released, False on timeout
        """
        import os

        subscripts = self._canonicalize_subscripts(subscripts)
        key = (name, subscripts)
        owner = os.getpid()

        if lock_type == "-":
            # Decrement lock count (release)
            current = self._lock_table.get(key)
            if current is not None and current[0] == owner:
                new_count = current[1] - 1
                if new_count <= 0:
                    del self._lock_table[key]
                else:
                    self._lock_table[key] = (owner, new_count)
            return True

        # Acquire (increment)
        current = self._lock_table.get(key)
        if current is None or current[0] == owner:
            # Lock is free or already owned by us — acquire
            count = (current[1] if current else 0) + 1
            self._lock_table[key] = (owner, count)
            return True

        # Held by another PID (shouldn't happen in single-process mode)
        return False

    def unlock(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Release a lock on ^NAME(subscripts).

        Only releases locks owned by the current process.
        """
        import os

        subscripts = self._canonicalize_subscripts(subscripts)
        key = (name, subscripts)
        owner = os.getpid()

        current = self._lock_table.get(key)
        if current is not None and current[0] == owner:
            new_count = current[1] - 1
            if new_count <= 0:
                del self._lock_table[key]
            else:
                self._lock_table[key] = (owner, new_count)

    def unlock_all(self) -> None:
        """Release all locks held by the current process.

        Argumentless LOCK releases all locks.
        """
        import os

        owner = os.getpid()
        keys_to_remove = [k for k, v in self._lock_table.items() if v[0] == owner]
        for k in keys_to_remove:
            del self._lock_table[k]

    def get_locks(self) -> list[tuple[str, str, int]]:
        """Return all locks held by the current process.

        Used by ZSHOW "L".

        Returns:
            List of (lock_name, subscripts_json, lock_count) tuples
        """
        import json
        import os

        owner = os.getpid()
        rows: list[tuple[str, str, int]] = []
        for (name, subs), (own, count) in self._lock_table.items():
            if own == owner:
                rows.append((name, json.dumps(list(subs)), count))
        rows.sort(key=lambda r: (r[0], r[1]))
        return rows

    # =========================================================================
    # Transaction Operations
    # =========================================================================

    def transaction_start(self) -> None:
        """Begin a transaction (TSTART).

        Saves a deep copy snapshot of globals for rollback.
        """

        # Deep copy the entire globals dictionary
        snapshot = {}
        for name, array in self._globals.items():
            snapshot[name] = self._deep_copy_tree(array)

        self._transaction_snapshots.append(snapshot)
        self._tlevel += 1

    def transaction_commit(self) -> None:
        """Commit current transaction (TCOMMIT).

        Decrements level and discards snapshot on full commit.

        Raises:
            RuntimeError: If $TLEVEL = 0 (M44 error)
        """
        if self._tlevel == 0:
            raise RuntimeError("M44: TCOMMIT without matching TSTART")

        # Discard the snapshot (commit the changes)
        self._transaction_snapshots.pop()
        self._tlevel -= 1

    def transaction_rollback(self) -> None:
        """Rollback current transaction (TROLLBACK).

        Restores globals from snapshot.
        Per MUMPS spec 8.2.21: Argumentless TROLLBACK rolls back ALL levels.

        Raises:
            RuntimeError: If $TLEVEL = 0 (M44 error)
        """
        if self._tlevel == 0:
            raise RuntimeError("M44: TROLLBACK without matching TSTART")

        # Per MUMPS spec: Argumentless TROLLBACK rolls back ALL transaction levels
        # Restore from the FIRST snapshot (outermost transaction)
        while len(self._transaction_snapshots) > 1:
            self._transaction_snapshots.pop()
        self._globals = self._transaction_snapshots.pop()
        self._tlevel = 0

    def get_tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL).

        Returns:
            Current transaction nesting level (0 = no transaction)
        """
        return self._tlevel

    # =========================================================================
    # SSVN Query Operations
    # =========================================================================

    def ssvn_global(self, subscript: str) -> str:
        """Query ^$GLOBAL(name) for global existence.

        Returns "1" if global exists, "" otherwise.
        """
        return "1" if subscript in self._globals else ""

    def ssvn_job(self, subscript: str) -> str:
        """Query ^$JOB(pid) for job/process information.

        Returns "1" if the process with the
        given PID exists and is alive, "" otherwise.
        For the current process, always returns "1".
        For other processes, uses os.kill(pid, 0) to probe liveness.
        """
        import os

        try:
            pid = int(subscript)
            if pid <= 0:
                return ""  # PIDs must be positive
            if pid == os.getpid():
                return "1"  # Current process always exists
            # Probe liveness of other processes
            try:
                os.kill(pid, 0)
                return "1"  # Process exists
            except ProcessLookupError:
                return ""  # Process does not exist
            except PermissionError:
                return "1"  # Process exists but we lack permission
        except (ValueError, OverflowError):
            pass
        return ""

    def ssvn_lock(self, subscript: str) -> str:
        """Query ^$LOCK(lockname) for lock information.

        Returns lock count if locked, empty if not.
        """
        # Parse subscript as (name, subscripts) key
        # For simplicity, treat subscript as global name with no subscripts
        key = (subscript, ())
        entry = self._lock_table.get(key)
        count = entry[1] if entry else 0
        return str(count) if count > 0 else ""

    def ssvn_routine(self, subscript: str) -> str:
        """Query ^$ROUTINE(routinename) for routine metadata.

        Checks if a routine is importable
        as a Python module under the m2py namespace, or exists as a
        .m file in the current directory.

        Returns:
            "1" if the routine is available, "" otherwise.
        """
        import importlib.util
        import os

        if not subscript:
            return ""

        # Check if the routine is importable as a Python module
        try:
            spec = importlib.util.find_spec(f"m2py.routines.{subscript}")
            if spec is not None:
                return "1"
        except (ModuleNotFoundError, ValueError):
            pass

        # Check if .m file exists in current directory or common paths
        if os.path.isfile(f"{subscript}.m"):
            return "1"

        return ""

    def _deep_copy_tree(self, source: "MArray") -> "MArray":
        """Deep copy an MArray tree.

        Args:
            source: Source MArray to copy

        Returns:
            New MArray with same structure and values
        """
        from m2py.runtime import MArray

        result = MArray()
        result._value = source._value

        for key, child in source._children.items():
            # Keys are already canonical strings, just copy them
            result._children[str(key)] = self._deep_copy_tree(child)

        return result

    # =========================================================================
    # Namespace-aware Global Operations
    # =========================================================================

    def _ns_name(self, name: str, namespace: str) -> str:
        """Generate namespace-qualified global name.

        Args:
            name: Global name without ^
            namespace: Namespace identifier (empty = default)

        Returns:
            Namespace-prefixed name for internal storage
        """
        if namespace:
            return f"{namespace}:{name}"
        return name

    def set_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        value: str,
        namespace: str = "",
    ) -> None:
        """Set a global variable in a specific namespace.

        For extended global references.

        Args:
            name: Global name (without ^)
            subscripts: Subscript tuple
            value: Value to set
            namespace: Namespace identifier. Empty = default namespace.
        """
        self.set(self._ns_name(name, namespace), subscripts, value)

    def get_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        namespace: str = "",
    ) -> str | None:
        """Get a global variable from a specific namespace.

        For extended global references.

        Args:
            name: Global name (without ^)
            subscripts: Subscript tuple
            namespace: Namespace identifier. Empty = default namespace.

        Returns:
            Value string, or None if undefined
        """
        return self.get(self._ns_name(name, namespace), subscripts)

    def data_ns(
        self, name: str, subscripts: tuple[str, ...], namespace: str = ""
    ) -> int:
        """$DATA for namespace-qualified global."""
        return self.data(self._ns_name(name, namespace), subscripts)

    def order_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        namespace: str = "",
    ) -> str:
        """$ORDER for namespace-qualified global."""
        return self.order(self._ns_name(name, namespace), subscripts, direction)

    def kill_ns(
        self, name: str, subscripts: tuple[str, ...], namespace: str = ""
    ) -> None:
        """KILL for namespace-qualified global."""
        self.kill(self._ns_name(name, namespace), subscripts)

    def query_ns(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        namespace: str = "",
    ) -> str:
        """$QUERY for namespace-qualified global."""
        return self.query(self._ns_name(name, namespace), subscripts)
