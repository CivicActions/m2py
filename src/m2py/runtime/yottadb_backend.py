"""YottaDB backend implementation for GlobalStorageBackend protocol.

Uses the yottadb Python wrapper (C extension linked against libyottadb.so).
Must run inside the YDB container via utils/ydb.sh.

Features:
    - Lazy SDK import (deferred until first use)
    - Thread-safe via threading.Lock
    - Naked reference tracking (Python-side, matching InMemoryGlobalStorage)
    - MUMPS subscript canonicalization via SubscriptCanonicalizer
    - SDK exception translation to m2py BackendError types
    - Tracks known globals for reliable kill_all()
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


class YottaDBGlobalStorage:
    """YottaDB backend implementation using yottadb Python wrapper.

    All operations go through the YottaDB C Simple API (via the Python wrapper).
    The naked indicator is maintained Python-side (YDB doesn't expose it).

    Thread safety: A threading.Lock serializes all YDB API calls. The YottaDB
    C API has limited thread safety, so we use coarse-grained locking.
    """

    def __init__(self) -> None:
        """Initialize YottaDB backend (lazy - no SDK import yet)."""
        self._ydb = None  # Lazy import of yottadb module
        self._lock = threading.Lock()

        # Naked indicator (Python-side, same as InMemoryGlobalStorage)
        self._naked_indicator_value: tuple[str, tuple[str, ...]] | None = None

        # Lock tracking: {(name, subscripts): count}
        self._locks_held: dict[tuple[str, tuple[str, ...]], int] = {}

        # Transaction state
        self._tlevel: int = 0
        self._transaction_journal: list[list[tuple]] = []  # Stack of change logs
        # Lock snapshot for TROLLBACK — per spec §6.3.2, ROLLBACK removes
        # any nrefs from the Lock-LIST not present when the TRANSACTION started
        self._lock_snapshot: dict[tuple[str, tuple[str, ...]], int] | None = None

        # $ZREFERENCE
        self._last_global_ref: str = ""

        # Track known global names for kill_all()
        self._known_globals: set[str] = set()

    def _ensure_initialized(self) -> None:
        """Lazily import yottadb SDK on first use."""
        if self._ydb is None:
            try:
                import yottadb

                self._ydb = yottadb
            except ImportError as e:
                from m2py.runtime.backend_exceptions import BackendConnectionError

                raise BackendConnectionError(
                    "YottaDB Python wrapper not available. "
                    "Run inside the YDB container: bash utils/ydb.sh <command>"
                ) from e

    def _make_key(self, name: str, subscripts: tuple[str, ...] = ()):
        """Create a yottadb.Key for ^NAME(subscripts).

        Args:
            name: Global name without caret (e.g., "PATIENT")
            subscripts: Tuple of canonical string subscripts
        """
        self._ensure_initialized()
        ydb = self._ydb
        key = ydb.Key(f"^{name}")
        for sub in subscripts:
            key = key[sub]
        return key

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
        # Update $ZREFERENCE
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
        """Translate YottaDB exceptions to m2py backend exceptions."""
        from m2py.runtime.backend_exceptions import (
            BackendTimeoutError,
            BackendError,
        )

        ydb = self._ydb
        if ydb is not None and isinstance(e, ydb.YDBError):
            msg = str(e)
            if "TIME" in msg or "LOCKTIME" in msg:
                err = BackendTimeoutError(msg)
                err.__cause__ = e
                return err
            else:
                err = BackendError("YDBERR", msg)
                err.__cause__ = e
                return err
        return e

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
            self._ensure_initialized()
            try:
                key = self._make_key(name, subscripts)
                d = key.data
                if d == 0 or d == 10:
                    # No value at this node
                    return None
                val = key.get()
                if val is None:
                    return None
                return val.decode("utf-8") if isinstance(val, bytes) else str(val)
            except Exception as e:
                ydb = self._ydb
                if ydb is not None and isinstance(e, ydb.YDBError):
                    msg = str(e)
                    if "GVUNDEF" in msg or "LVUNDEF" in msg:
                        return None
                raise self._translate_exception(e)

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._known_globals.add(name)

        with self._lock:
            self._ensure_initialized()
            try:
                key = self._make_key(name, subscripts)
                # Journal old value for transaction rollback
                if self._tlevel > 0:
                    old_val = self._safe_get(name, subscripts)
                    self._transaction_journal[-1].append(
                        ("set", name, subscripts, old_val)
                    )
                key.value = value.encode("utf-8")
            except Exception as e:
                raise self._translate_exception(e)

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_initialized()
            try:
                # Journal subtree for transaction rollback
                if self._tlevel > 0:
                    subtree = self._snapshot_subtree(name, subscripts)
                    self._transaction_journal[-1].append(
                        ("kill", name, subscripts, subtree)
                    )
                key = self._make_key(name, subscripts)
                key.delete_tree()
            except Exception as e:
                ydb = self._ydb
                if ydb is not None and isinstance(e, ydb.YDBError):
                    return
                raise self._translate_exception(e)

    def kill_all(self) -> None:
        """Kill all known globals. Used for testing/reset."""
        with self._lock:
            self._ensure_initialized()
            ydb = self._ydb
            for gname in list(self._known_globals):
                try:
                    ydb.Key(f"^{gname}").delete_tree()
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
            self._ensure_initialized()
            try:
                key = self._make_key(name, subscripts)
                return key.data
            except Exception as e:
                ydb = self._ydb
                if ydb is not None and isinstance(e, ydb.YDBError):
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
            self._ensure_initialized()
            try:
                parent_subs = subscripts[:-1]
                start_sub = subscripts[-1]

                key = self._make_key(name, parent_subs + (start_sub,))

                if direction == 1:
                    result = key.subscript_next()
                else:
                    result = key.subscript_previous()

                if result is None or result == b"":
                    return ""

                if isinstance(result, bytes):
                    result = result.decode("utf-8")

                return m_format_output(result)
            except Exception as e:
                ydb = self._ydb
                if ydb is not None:
                    import _yottadb

                    # YDBNodeEnd means end of subscript list → return ""
                    if isinstance(e, _yottadb.YDBNodeEnd):
                        return ""
                    if isinstance(e, ydb.YDBError):
                        return ""
                raise self._translate_exception(e)

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data ($QUERY).

        Uses yottadb.node_next() for $QUERY equivalent.
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_initialized()
            ydb = self._ydb
            try:
                varname = f"^{name}"
                sub_list = list(subscripts)
                result = ydb.node_next(varname, sub_list)
                if result is None or result == []:
                    return ""

                if isinstance(result, (list, tuple)):
                    decoded = []
                    for s in result:
                        if isinstance(s, bytes):
                            decoded.append(s.decode("utf-8"))
                        else:
                            decoded.append(str(s))

                    if not decoded:
                        return ""

                    formatted_subs = [_format_subscript(sub) for sub in decoded]
                    ref = f"^{name}({','.join(formatted_subs)})"

                    # Update naked indicator for the result
                    result_subs = tuple(decoded)
                    self._update_naked_indicator(name, result_subs)

                    return ref
                return ""
            except Exception as e:
                ydb_mod = self._ydb
                if ydb_mod is not None:
                    import _yottadb

                    if isinstance(e, (_yottadb.YDBNodeEnd, ydb_mod.YDBError)):
                        return ""
                raise self._translate_exception(e)

    # =========================================================================
    # Kill Node (value only)
    # =========================================================================

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_initialized()
            try:
                key = self._make_key(name, subscripts)
                key.delete_node()
            except Exception as e:
                ydb = self._ydb
                if ydb is not None and isinstance(e, ydb.YDBError):
                    return
                raise self._translate_exception(e)

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    def get_tree(self, name: str, subscripts: tuple[str, ...]) -> "MArray | None":
        """Get subtree as MArray for MERGE source."""
        from m2py.runtime import MArray

        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        with self._lock:
            self._ensure_initialized()
            try:
                key = self._make_key(name, subscripts)
                d = key.data
                if d == 0:
                    return None

                root = MArray()
                if d in (1, 11):
                    val = key.get()
                    if val is not None:
                        root._value = (
                            val.decode("utf-8") if isinstance(val, bytes) else str(val)
                        )

                if d in (10, 11):
                    self._build_tree(key, root, name, subscripts)

                return root
            except Exception as e:
                ydb = self._ydb
                if ydb is not None and isinstance(e, ydb.YDBError):
                    return None
                raise self._translate_exception(e)

    def _build_tree(
        self,
        parent_key,
        parent_marray: "MArray",
        name: str,
        subscripts: tuple[str, ...],
    ) -> None:
        """Recursively build MArray from YDB key using order traversal."""
        from m2py.runtime import MArray
        import _yottadb

        # Use order traversal: start from "" to get first child
        current_sub = ""
        while True:
            child_key = parent_key[current_sub]
            try:
                next_sub = child_key.subscript_next()
            except _yottadb.YDBNodeEnd:
                break
            if next_sub is None or next_sub == b"":
                break

            sub_str = (
                next_sub.decode("utf-8")
                if isinstance(next_sub, bytes)
                else str(next_sub)
            )
            child = MArray()

            child_ydb_key = parent_key[sub_str]
            d = child_ydb_key.data
            if d in (1, 11):
                val = child_ydb_key.get()
                if val is not None:
                    child._value = (
                        val.decode("utf-8") if isinstance(val, bytes) else str(val)
                    )

            if d in (10, 11):
                self._build_tree(child_ydb_key, child, name, subscripts + (sub_str,))

            if child._value is not None or child._children:
                parent_marray._children[sub_str] = child

            current_sub = sub_str

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
        """Recursively merge MArray node into YDB global."""
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
            self._ensure_initialized()
            try:
                key = self._make_key(name, subscripts)
                # Journal old value for transaction rollback
                if self._tlevel > 0:
                    old_val = self._safe_get(name, subscripts)
                    self._transaction_journal[-1].append(
                        ("incr", name, subscripts, old_val)
                    )
                result = key.incr(increment)
                if isinstance(result, bytes):
                    return m_format_output(result.decode("utf-8"))
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
                self._ensure_initialized()
                ydb = self._ydb
                try:
                    ydb.lock_decr(
                        f"^{name}",
                        list(subscripts),
                    )
                except Exception:
                    pass
            return True

        # Incremental lock (+)
        with self._lock:
            self._ensure_initialized()
            ydb = self._ydb
            try:
                timeout_nsec = int(timeout * 1_000_000_000) if timeout is not None else 0
                ydb.lock_incr(
                    f"^{name}",
                    list(subscripts),
                    timeout_nsec=timeout_nsec,
                )
                self._locks_held[lock_key] = self._locks_held.get(lock_key, 0) + 1
                return True
            except Exception as e:
                ydb_mod = self._ydb
                if ydb_mod is not None:
                    import _yottadb

                    if isinstance(e, ydb_mod.YDBError):
                        msg = str(e)
                        if "TIME" in msg or "LOCKTIME" in msg:
                            return False
                    if isinstance(e, _yottadb.YDBLockTimeoutError):
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
            self._ensure_initialized()
            ydb = self._ydb
            try:
                ydb.lock_decr(
                    f"^{name}",
                    list(subscripts),
                )
            except Exception:
                pass

    def unlock_all(self) -> None:
        """Release all locks held by current process."""
        self._locks_held.clear()
        with self._lock:
            self._ensure_initialized()
            ydb = self._ydb
            try:
                ydb.lock()
            except Exception:
                pass

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

    def _safe_get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get value without updating naked indicator (for journaling)."""
        try:
            key = self._make_key(name, subscripts)
            d = key.data
            if d == 0 or d == 10:
                return None
            val = key.get()
            if val is None:
                return None
            return val.decode("utf-8") if isinstance(val, bytes) else str(val)
        except Exception:
            return None

    def _snapshot_subtree(
        self, name: str, subscripts: tuple[str, ...]
    ) -> list[tuple[tuple[str, ...], str | None]]:
        """Snapshot all nodes in a subtree for rollback."""
        nodes: list[tuple[tuple[str, ...], str | None]] = []
        try:
            key = self._make_key(name, subscripts)
            d = key.data
            if d in (1, 11):
                val = key.get()
                v = val.decode("utf-8") if isinstance(val, bytes) else str(val) if val is not None else None
                nodes.append((subscripts, v))
            elif d == 0:
                nodes.append((subscripts, None))
            else:
                nodes.append((subscripts, None))
            # Walk children via $ORDER
            self._snapshot_children(name, subscripts, nodes)
        except Exception:
            pass
        return nodes

    def _snapshot_children(
        self,
        name: str,
        subscripts: tuple[str, ...],
        nodes: list[tuple[tuple[str, ...], str | None]],
    ) -> None:
        """Walk children recursively to snapshot values."""
        import _yottadb

        current_sub = ""
        parent_key = self._make_key(name, subscripts)
        while True:
            child_key = parent_key[current_sub]
            try:
                next_sub_b = child_key.subscript_next()
            except _yottadb.YDBNodeEnd:
                break
            if next_sub_b is None or next_sub_b == b"":
                break
            sub_str = next_sub_b.decode("utf-8") if isinstance(next_sub_b, bytes) else str(next_sub_b)
            child_subs = subscripts + (sub_str,)
            child_ydb = parent_key[sub_str]
            d = child_ydb.data
            if d in (1, 11):
                val = child_ydb.get()
                v = val.decode("utf-8") if isinstance(val, bytes) else str(val) if val is not None else None
                nodes.append((child_subs, v))
            if d in (10, 11):
                self._snapshot_children(name, child_subs, nodes)
            current_sub = sub_str

    def transaction_start(self) -> None:
        """Begin a transaction (TSTART).

        Journals all modifications so rollback can undo them.
        Per spec §6.3.2: also snapshots Lock-LIST for TROLLBACK.
        """
        # Snapshot lock state at outermost TSTART only
        if self._tlevel == 0:
            self._lock_snapshot = dict(self._locks_held)

        self._transaction_journal.append([])
        self._tlevel += 1

    def transaction_commit(self) -> None:
        """Commit current transaction (TCOMMIT)."""
        if self._tlevel == 0:
            raise RuntimeError(
                "M44: Cannot TCOMMIT outside of a transaction ($TLEVEL=0)"
            )
        self._transaction_journal.pop()
        self._tlevel -= 1

        # Clear lock snapshot on outermost commit
        if self._tlevel == 0:
            self._lock_snapshot = None

    def transaction_rollback(self) -> None:
        """Rollback current transaction (TROLLBACK).

        Replays journal entries in reverse to restore original state.
        Per MUMPS spec: argumentless TROLLBACK rolls back ALL levels.
        """
        if self._tlevel == 0:
            raise RuntimeError(
                "M44: Cannot TROLLBACK outside of a transaction ($TLEVEL=0)"
            )
        # Collect all journal entries from all nested levels
        all_entries: list[tuple] = []
        for journal in self._transaction_journal:
            all_entries.extend(journal)
        self._transaction_journal.clear()
        self._tlevel = 0

        # Replay in reverse to restore original state
        with self._lock:
            self._ensure_initialized()
            for entry in reversed(all_entries):
                op = entry[0]
                try:
                    if op == "set":
                        _, name, subscripts, old_val = entry
                        key = self._make_key(name, subscripts)
                        if old_val is None:
                            # Node didn't exist before — delete it
                            key.delete_node()
                        else:
                            key.value = old_val.encode("utf-8")
                    elif op == "kill":
                        _, name, subscripts, subtree = entry
                        # Restore all nodes from snapshot
                        for subs, val in subtree:
                            if val is not None:
                                key = self._make_key(name, subs)
                                key.value = val.encode("utf-8")
                    elif op == "incr":
                        _, name, subscripts, old_val = entry
                        key = self._make_key(name, subscripts)
                        if old_val is None:
                            key.delete_node()
                        else:
                            key.value = old_val.encode("utf-8")
                except Exception:
                    pass  # Best-effort rollback

            # Restore lock state to what it was at outermost TSTART
            if self._lock_snapshot is not None:
                # Release native locks that were acquired during the transaction
                for lock_key, count in self._locks_held.items():
                    if lock_key not in self._lock_snapshot:
                        # This lock was acquired during the txn — release it
                        name, subs = lock_key
                        for _ in range(count):
                            try:
                                self._ydb.lock_decr(f"^{name}", list(subs))
                            except Exception:
                                pass
                    else:
                        # Lock existed before, but count may have grown
                        orig_count = self._lock_snapshot[lock_key]
                        extra = count - orig_count
                        if extra > 0:
                            name, subs = lock_key
                            for _ in range(extra):
                                try:
                                    self._ydb.lock_decr(f"^{name}", list(subs))
                                except Exception:
                                    pass
                # Restore the Python-side lock tracking dict
                self._locks_held = dict(self._lock_snapshot)
                self._lock_snapshot = None

    def get_tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL)."""
        return self._tlevel

    # =========================================================================
    # SSVN Operations
    # =========================================================================

    def ssvn_global(self, subscript: str) -> str:
        """Query ^$GLOBAL(name) for global existence."""
        with self._lock:
            self._ensure_initialized()
            try:
                key = self._make_key(subscript)
                d = key.data
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
        """Close the backend (no-op for in-process YDB)."""
        pass
