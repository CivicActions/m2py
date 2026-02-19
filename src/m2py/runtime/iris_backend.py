"""IRIS backend implementation for GlobalStorageBackend protocol.

Uses the intersystems-irispython SDK to connect to an InterSystems IRIS
database over TCP. The IRIS container runs via Docker; our code runs locally.

Features:
    - Lazy connection initialization (deferred until first use)
    - Thread-safe via threading.Lock
    - Naked reference tracking (Python-side, matching InMemoryGlobalStorage)
    - MUMPS subscript canonicalization via SubscriptCanonicalizer
    - SDK exception translation to m2py BackendError types
    - Connection parameter reading from environment variables
    - Namespace support for extended global references
"""

from __future__ import annotations

import os
import threading
from typing import TYPE_CHECKING

from m2py.core.subscripts import SubscriptCanonicalizer
from m2py.runtime.helpers import (
    _format_subscript,
    m_format_output,
)

if TYPE_CHECKING:
    from m2py.runtime import MArray


class IRISGlobalStorage:
    """IRIS backend implementation using intersystems-irispython SDK.

    Connects to an IRIS server over TCP to persist globals. Supports
    namespace switching via extended reference syntax ^|"NS"|Global.

    Thread safety: A threading.Lock serializes all IRIS API calls.
    The IRIS connection is not inherently thread-safe.
    """

    def __init__(self) -> None:
        """Initialize IRIS backend (lazy — no connection yet)."""
        self._iris_module = None  # Lazy import of iris module
        self._conn = None  # IRIS connection object
        self._iris = None  # iris.IRIS instance
        self._lock = threading.Lock()

        # Naked indicator (Python-side, same as InMemoryGlobalStorage)
        self._naked_indicator_value: tuple[str, tuple[str, ...]] | None = None

        # Lock tracking: {(name, subscripts): count}
        self._locks_held: dict[tuple[str, tuple[str, ...]], int] = {}

        # Transaction state
        self._tlevel: int = 0

        # $ZREFERENCE
        self._last_global_ref: str = ""

        # Track known global names for kill_all()
        self._known_globals: set[str] = set()

    def _ensure_connected(self) -> None:
        """Lazily connect to IRIS on first use."""
        if self._conn is not None:
            return

        try:
            import iris as iris_module

            self._iris_module = iris_module
        except ImportError as e:
            from m2py.runtime.backend_exceptions import BackendConnectionError

            raise BackendConnectionError(
                "IRIS Python SDK not available. "
                "Install with: uv add intersystems-irispython --optional backend"
            ) from e

        from m2py.runtime.backend_config import IRISConfig

        config = IRISConfig.from_env()

        try:
            self._conn = iris_module.connect(
                config.host,
                config.port,
                config.namespace,
                config.username,
                config.password,
            )
            self._iris = iris_module.createIRIS(self._conn)
        except Exception as e:
            from m2py.runtime.backend_exceptions import BackendConnectionError

            raise BackendConnectionError(
                f"Cannot connect to IRIS at {config.host}:{config.port}: {e}"
            ) from e

    def _make_global_name(self, name: str) -> str:
        """Construct IRIS global name with caret.

        Args:
            name: Global name without caret (e.g., "PATIENT")

        Returns:
            Global name with caret (e.g., "^PATIENT")
        """
        return f"^{name}"

    def _canonicalize_subscript(self, subscript: str | int | float) -> str:
        """Convert subscript to MUMPS canonical string form."""
        return SubscriptCanonicalizer.canonicalize(subscript)

    def _canonicalize_subscripts(
        self, subscripts: tuple[str | int | float, ...]
    ) -> tuple[str, ...]:
        """Convert all subscripts to canonical string form."""
        return tuple(self._canonicalize_subscript(s) for s in subscripts)

    def _update_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Update naked indicator after global access."""
        if subscripts:
            subs_str = ",".join(_format_subscript(s) for s in subscripts)
            self._last_global_ref = f"^{name}({subs_str})"
        else:
            self._last_global_ref = f"^{name}"

        if subscripts:
            self._naked_indicator_value = (name, subscripts[:-1])
        else:
            self._naked_indicator_value = None

    def _translate_exception(self, e: Exception) -> Exception:
        """Translate IRIS exceptions to m2py backend exceptions."""
        from m2py.runtime.backend_exceptions import (
            BackendConnectionError,
            BackendTimeoutError,
            BackendError,
        )

        msg = str(e)
        if "timeout" in msg.lower() or "LOCKTIME" in msg:
            err = BackendTimeoutError(msg)
            err.__cause__ = e
            return err
        elif "connect" in msg.lower() or "connection" in msg.lower():
            err = BackendConnectionError(msg)
            err.__cause__ = e
            return err
        else:
            err = BackendError("IRISERR", msg)
            err.__cause__ = e
            return err

    # =========================================================================
    # Basic CRUD Operations
    # =========================================================================

    def get(
        self, name: str, subscripts: tuple[str, ...], update_naked: bool = True
    ) -> str | None:
        """Get value at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
            self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    val = self._iris.get(gname, *subscripts)
                else:
                    val = self._iris.get(gname)
                if val is None:
                    return None
                return str(val)
            except Exception as e:
                # IRIS raises exception for <UNDEFINED>
                msg = str(e)
                if "UNDEFINED" in msg or "does not exist" in msg.lower():
                    return None
                raise self._translate_exception(e)

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    self._iris.set(value, gname, *subscripts)
                else:
                    self._iris.set(value, gname)
            except Exception as e:
                raise self._translate_exception(e)

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    self._iris.kill(gname, *subscripts)
                else:
                    self._iris.kill(gname)
            except Exception as e:
                # Ignore errors on nonexistent nodes
                msg = str(e)
                if "UNDEFINED" in msg:
                    return
                raise self._translate_exception(e)

    def kill_all(self) -> None:
        """Kill all known globals. Used for testing/reset."""
        with self._lock:
            self._ensure_connected()
            for gname in list(self._known_globals):
                try:
                    self._iris.kill(f"^{gname}")
                except Exception:
                    pass
            self._known_globals.clear()

        self._naked_indicator_value = None
        self._last_global_ref = ""

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value for ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    return self._iris.isDefined(gname, *subscripts)
                else:
                    return self._iris.isDefined(gname)
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return 0
                raise self._translate_exception(e)

    # =========================================================================
    # Naked Reference Support
    # =========================================================================

    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Get current naked indicator."""
        return self._naked_indicator_value

    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Set naked indicator explicitly."""
        self._naked_indicator_value = (name, self._canonicalize_subscripts(subscripts))

    @property
    def last_global_ref(self) -> str:
        """Return the last global reference string ($ZREFERENCE)."""
        return self._last_global_ref

    def set_order_naked(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Pre-set naked indicator for $ORDER evaluation ordering."""
        subs = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subs)

    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """Resolve naked reference ^(subscripts) to full global reference."""
        if self._naked_indicator_value is None:
            raise RuntimeError("NAKEDERR: Naked reference without prior global access")
        name, base_subscripts = self._naked_indicator_value
        subscripts = self._canonicalize_subscripts(subscripts)
        full_subscripts = base_subscripts + subscripts
        return (name, full_subscripts)

    # =========================================================================
    # Traversal Operations
    # =========================================================================

    def order(
        self,
        name: str,
        subscripts: tuple[str, ...],
        direction: int = 1,
        update_naked: bool = True,
    ) -> str:
        """Return next/previous subscript in MUMPS collation order."""
        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
            self._update_naked_indicator(name, subscripts)

        if not subscripts:
            return ""

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                parent_subs = subscripts[:-1]
                start_sub = subscripts[-1]

                reversed_flag = direction != 1
                if parent_subs:
                    result = self._iris.nextSubscript(
                        reversed_flag, gname, *parent_subs, start_sub
                    )
                else:
                    result = self._iris.nextSubscript(reversed_flag, gname, start_sub)

                if result is None or result == "":
                    return ""

                return m_format_output(str(result))
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return ""
                raise self._translate_exception(e)

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data ($QUERY).

        Uses manual tree traversal since IRIS Native API doesn't expose
        $QUERY directly via the Python SDK.
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                result = self._query_next(name, subscripts)
                if result is None:
                    return ""

                result_subs = result
                formatted_subs = [_format_subscript(sub) for sub in result_subs]
                ref = f"^{name}({','.join(formatted_subs)})"

                # Update naked indicator
                self._update_naked_indicator(name, result_subs)

                return ref
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return ""
                raise self._translate_exception(e)

    def _query_next(
        self, name: str, subscripts: tuple[str, ...]
    ) -> tuple[str, ...] | None:
        """Find next valued node after given subscripts (manual $QUERY).

        Implements depth-first traversal to find the next node with a value.
        Handles empty-string subscripts (meaning "from the beginning").
        """
        gname = self._make_global_name(name)

        if not subscripts:
            return None

        # Check if the last subscript is "" (meaning "start from beginning")
        last_sub = subscripts[-1]
        parent_subs = subscripts[:-1]

        if last_sub == "":
            # $QUERY from beginning: find first subscript at this level
            if parent_subs:
                first = self._iris.nextSubscript(False, gname, *parent_subs, "")
            else:
                first = self._iris.nextSubscript(False, gname, "")

            if first is None or first == "":
                return None

            first_subs = parent_subs + (str(first),)
            d = self._iris.isDefined(gname, *first_subs)
            if d in (1, 11):
                return first_subs
            # Has children but no value — descend
            return self._query_next(name, first_subs)

        # Normal case: current subscript is not empty
        # Try to descend into children first
        d = self._iris.isDefined(gname, *subscripts)

        if d in (10, 11):
            # Try to find first child
            if subscripts:
                first_child = self._iris.nextSubscript(False, gname, *subscripts, "")
            else:
                first_child = self._iris.nextSubscript(False, gname, "")

            if first_child is not None and first_child != "":
                child_subs = subscripts + (str(first_child),)
                child_d = self._iris.isDefined(gname, *child_subs)
                if child_d in (1, 11):
                    return child_subs
                # Recurse into this child
                result = self._query_next(name, child_subs)
                if result is not None:
                    return result

        # Try to move to next sibling
        current = subscripts[-1]

        if parent_subs:
            next_sib = self._iris.nextSubscript(False, gname, *parent_subs, current)
        else:
            next_sib = self._iris.nextSubscript(False, gname, current)

        if next_sib is not None and next_sib != "":
            sib_subs = parent_subs + (str(next_sib),)
            sib_d = self._iris.isDefined(gname, *sib_subs)
            if sib_d in (1, 11):
                return sib_subs
            # Recurse into sibling
            result = self._query_next(name, sib_subs)
            if result is not None:
                return result

            # Continue to next siblings
            while True:
                if parent_subs:
                    next_next = self._iris.nextSubscript(
                        False, gname, *parent_subs, str(next_sib)
                    )
                else:
                    next_next = self._iris.nextSubscript(False, gname, str(next_sib))

                if next_next is None or next_next == "":
                    break

                next_sib = next_next
                sib_subs = parent_subs + (str(next_sib),)
                sib_d = self._iris.isDefined(gname, *sib_subs)
                if sib_d in (1, 11):
                    return sib_subs
                result = self._query_next(name, sib_subs)
                if result is not None:
                    return result

        # Move up to parent level and try next
        if parent_subs:
            return self._query_up(name, parent_subs)

        return None

    def _query_up(
        self, name: str, subscripts: tuple[str, ...]
    ) -> tuple[str, ...] | None:
        """Walk up the tree and look for next sibling at each level."""
        gname = self._make_global_name(name)

        parent_subs = subscripts[:-1]
        current = subscripts[-1]

        if parent_subs:
            next_sib = self._iris.nextSubscript(False, gname, *parent_subs, current)
        else:
            next_sib = self._iris.nextSubscript(False, gname, current)

        if next_sib is not None and next_sib != "":
            sib_subs = parent_subs + (str(next_sib),)
            sib_d = self._iris.isDefined(gname, *sib_subs)
            if sib_d in (1, 11):
                return sib_subs
            result = self._query_next(name, sib_subs)
            if result is not None:
                return result

        # Continue up
        if parent_subs:
            return self._query_up(name, parent_subs)

        return None

    # =========================================================================
    # Kill Node (value only)
    # =========================================================================

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants.

        IRIS doesn't have a native kill-node-only operation, so we:
        1. Save all children
        2. Kill the node (which kills children too)
        3. Restore children
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    d = self._iris.isDefined(gname, *subscripts)
                else:
                    d = self._iris.isDefined(gname)

                if d in (0, 10):
                    # No value to kill
                    return

                if d == 1:
                    # Value only, no children — just kill
                    if subscripts:
                        self._iris.kill(gname, *subscripts)
                    else:
                        self._iris.kill(gname)
                    return

                # d == 11: Has value AND children
                # Save the tree, remove value, restore children
                # Actually, we can use the IRIS execute method to run
                # ZKILL which kills only the node value
                # Try using classMethodValue to call $ZKILL or similar
                # For now: save children, kill all, restore children
                children = self._save_children(name, subscripts)
                if subscripts:
                    self._iris.kill(gname, *subscripts)
                else:
                    self._iris.kill(gname)
                self._restore_children(name, subscripts, children)
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return
                raise self._translate_exception(e)

    def _save_children(
        self, name: str, subscripts: tuple[str, ...]
    ) -> list[tuple[tuple[str, ...], str]]:
        """Save all descendant nodes under the given path."""
        result = []
        self._collect_children(name, subscripts, result)
        return result

    def _collect_children(
        self,
        name: str,
        subscripts: tuple[str, ...],
        result: list[tuple[tuple[str, ...], str]],
    ) -> None:
        """Recursively collect all children with values."""
        gname = self._make_global_name(name)
        current = ""
        while True:
            if subscripts:
                next_child = self._iris.nextSubscript(
                    False, gname, *subscripts, current
                )
            else:
                next_child = self._iris.nextSubscript(False, gname, current)

            if next_child is None or next_child == "":
                break

            child_subs = subscripts + (str(next_child),)
            child_d = self._iris.isDefined(gname, *child_subs)

            if child_d in (1, 11):
                val = self._iris.get(gname, *child_subs)
                result.append((child_subs, str(val)))

            if child_d in (10, 11):
                self._collect_children(name, child_subs, result)

            current = str(next_child)

    def _restore_children(
        self,
        name: str,
        parent_subs: tuple[str, ...],
        children: list[tuple[tuple[str, ...], str]],
    ) -> None:
        """Restore saved child nodes."""
        gname = self._make_global_name(name)
        for child_subs, value in children:
            self._iris.set(value, gname, *child_subs)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def get_tree(self, name: str, subscripts: tuple[str, ...]) -> "MArray | None":
        """Get subtree as MArray for MERGE source."""
        from m2py.runtime import MArray

        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                if subscripts:
                    d = self._iris.isDefined(gname, *subscripts)
                else:
                    d = self._iris.isDefined(gname)

                if d == 0:
                    return None

                root = MArray()
                if d in (1, 11):
                    if subscripts:
                        val = self._iris.get(gname, *subscripts)
                    else:
                        val = self._iris.get(gname)
                    if val is not None:
                        root._value = str(val)

                if d in (10, 11):
                    self._build_tree_iris(name, subscripts, root)

                return root
            except Exception as e:
                msg = str(e)
                if "UNDEFINED" in msg:
                    return None
                raise self._translate_exception(e)

    def _build_tree_iris(
        self,
        name: str,
        subscripts: tuple[str, ...],
        parent_marray: "MArray",
    ) -> None:
        """Recursively build MArray from IRIS global using order traversal."""
        from m2py.runtime import MArray

        gname = self._make_global_name(name)
        current = ""
        while True:
            if subscripts:
                next_child = self._iris.nextSubscript(
                    False, gname, *subscripts, current
                )
            else:
                next_child = self._iris.nextSubscript(False, gname, current)

            if next_child is None or next_child == "":
                break

            sub_str = str(next_child)
            child = MArray()
            child_subs = subscripts + (sub_str,)

            d = self._iris.isDefined(gname, *child_subs)
            if d in (1, 11):
                val = self._iris.get(gname, *child_subs)
                if val is not None:
                    child._value = str(val)

            if d in (10, 11):
                self._build_tree_iris(name, child_subs, child)

            if child._value is not None or child._children:
                parent_marray._children[sub_str] = child

            current = sub_str

    def merge_tree(
        self, name: str, subscripts: tuple[str, ...], source: "MArray"
    ) -> None:
        """Merge MArray tree into global at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)
        self._merge_tree_recursive(name, subscripts, source)

    def _merge_tree_recursive(
        self, name: str, subscripts: tuple[str, ...], node: "MArray"
    ) -> None:
        """Recursively merge MArray node into IRIS global."""
        if node._value is not None:
            self.set(name, subscripts, node._value)
        for key, child in node._children.items():
            child_sub = str(key)
            self._merge_tree_recursive(name, subscripts + (child_sub,), child)

    # =========================================================================
    # Atomic Increment
    # =========================================================================

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)

        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(name)
                # IRIS increment returns the new value
                inc_val = int(increment) if "." not in increment else float(increment)
                if subscripts:
                    result = self._iris.increment(inc_val, gname, *subscripts)
                else:
                    result = self._iris.increment(inc_val, gname)
                return m_format_output(str(result))
            except Exception as e:
                raise self._translate_exception(e)

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
        """Acquire or release a lock on ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        lock_key = (name, subscripts)

        if lock_type == "-":
            # Decremental unlock
            if lock_key in self._locks_held:
                self._locks_held[lock_key] -= 1
                if self._locks_held[lock_key] <= 0:
                    del self._locks_held[lock_key]

            with self._lock:
                self._ensure_connected()
                try:
                    lock_name = f"^{name}"
                    if subscripts:
                        self._iris.unlock("", lock_name, *subscripts)
                    else:
                        self._iris.unlock("", lock_name)
                except Exception:
                    pass
            return True

        # Incremental lock (+)
        with self._lock:
            self._ensure_connected()
            try:
                lock_name = f"^{name}"
                timeout_sec = int(timeout) if timeout is not None else 0
                # lock(lockMode, timeout, globalName, subscripts...)
                if subscripts:
                    self._iris.lock("", timeout_sec, lock_name, *subscripts)
                else:
                    self._iris.lock("", timeout_sec, lock_name)

                self._locks_held[lock_key] = self._locks_held.get(lock_key, 0) + 1
                return True
            except Exception as e:
                msg = str(e)
                if "TIMEOUT" in msg or "timeout" in msg.lower():
                    return False
                raise self._translate_exception(e)

    def unlock(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Release a lock on ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        lock_key = (name, subscripts)
        if lock_key in self._locks_held:
            self._locks_held[lock_key] -= 1
            if self._locks_held[lock_key] <= 0:
                del self._locks_held[lock_key]

        with self._lock:
            self._ensure_connected()
            try:
                lock_name = f"^{name}"
                if subscripts:
                    self._iris.unlock("", lock_name, *subscripts)
                else:
                    self._iris.unlock("", lock_name)
            except Exception:
                pass

    def unlock_all(self) -> None:
        """Release all locks held by current process."""
        with self._lock:
            self._ensure_connected()
            try:
                self._iris.releaseAllLocks()
            except Exception:
                pass
        self._locks_held.clear()

    def get_locks(self) -> list[tuple[str, str, int]]:
        """Return all locks held by the current process/thread."""
        import json

        result = []
        for (lock_name, lock_subs), count in self._locks_held.items():
            subs_json = json.dumps(list(lock_subs))
            result.append((lock_name, subs_json, count))
        return result

    # =========================================================================
    # Transaction Operations
    # =========================================================================

    def transaction_start(self) -> None:
        """Begin a transaction (TSTART)."""
        self._tlevel += 1
        if self._tlevel == 1:
            with self._lock:
                self._ensure_connected()
                try:
                    self._iris.tStart()
                except Exception:
                    self._tlevel -= 1
                    raise

    def transaction_commit(self) -> None:
        """Commit current transaction (TCOMMIT)."""
        if self._tlevel == 0:
            raise RuntimeError(
                "M44: Cannot TCOMMIT outside of a transaction ($TLEVEL=0)"
            )
        self._tlevel -= 1
        if self._tlevel == 0:
            with self._lock:
                self._ensure_connected()
                self._iris.tCommit()

    def transaction_rollback(self) -> None:
        """Rollback current transaction (TROLLBACK)."""
        if self._tlevel == 0:
            raise RuntimeError(
                "M44: Cannot TROLLBACK outside of a transaction ($TLEVEL=0)"
            )
        self._tlevel = 0
        with self._lock:
            self._ensure_connected()
            self._iris.tRollback()

    def get_tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL)."""
        return self._tlevel

    # =========================================================================
    # SSVN Operations
    # =========================================================================

    def ssvn_global(self, subscript: str) -> str:
        """Query ^$GLOBAL(name) for global existence."""
        with self._lock:
            self._ensure_connected()
            try:
                gname = self._make_global_name(subscript)
                d = self._iris.isDefined(gname)
                return "1" if d > 0 else ""
            except Exception:
                return ""

    def ssvn_job(self, subscript: str) -> str:
        """Query ^$JOB(pid) for job/process information."""
        try:
            pid = int(subscript)
            if pid <= 0:
                return ""  # PIDs must be positive
            try:
                os.kill(pid, 0)  # Signal 0 = check existence
                return "1"
            except ProcessLookupError:
                return ""  # Process does not exist
            except PermissionError:
                return "1"  # Process exists but we lack permission
        except (ValueError, OverflowError):
            return ""

    def ssvn_lock(self, subscript: str) -> str:
        """Query ^$LOCK(lockname) for lock information."""
        for (lock_name, _), count in self._locks_held.items():
            if lock_name == subscript:
                return str(count)
        return ""

    def ssvn_routine(self, subscript: str) -> str:
        """Query ^$ROUTINE(routinename) for routine metadata.

        Checks if a routine is importable as a Python module under the
        m2py.routines or m2py.runtime.routines namespace, or exists as a
        .m file in the current directory.
        """
        import importlib.util

        if not subscript:
            return ""

        for prefix in ("m2py.routines", "m2py.runtime.routines"):
            try:
                spec = importlib.util.find_spec(f"{prefix}.{subscript}")
                if spec is not None:
                    return "1"
            except (ModuleNotFoundError, ValueError):
                pass

        if os.path.isfile(f"{subscript}.m"):
            return "1"

        return ""

    # =========================================================================
    # Connection Management
    # =========================================================================

    def close(self) -> None:
        """Close the IRIS connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
            self._iris = None

    def __del__(self) -> None:
        """Close connection on garbage collection."""
        self.close()
