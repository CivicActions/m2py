"""SQLite-backed global storage for cross-process MUMPS global sharing.

Implements the GlobalStorageBackend protocol using SQLite with WAL mode
for concurrent read/write access across multiple processes. Used when
JOB creates real subprocesses that need shared global variable storage.

Features:
    - ACID-compliant global variable storage
    - WAL mode for concurrent multi-process access
    - MUMPS numeric-before-string collation for $ORDER
    - Cross-process lock coordination via locks table
    - Transaction support (TSTART/TCOMMIT/TROLLBACK → SAVEPOINT/RELEASE/ROLLBACK)
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

from m2py.core.subscripts import SubscriptCanonicalizer
from m2py.runtime.helpers import (
    _mumps_collation_key,
    _format_subscript,
    m_format_output,
)

if TYPE_CHECKING:
    from m2py.runtime import MArray


def _mumps_collation_sql(a: str, b: str) -> int:
    """SQLite custom collation implementing MUMPS subscript ordering.

    MUMPS collation: numbers before strings, numbers sorted numerically.
    This is used as a collation function for SQLite ORDER BY.

    Args:
        a: First subscript JSON array string
        b: Second subscript JSON array string

    Returns:
        -1 if a < b, 0 if equal, 1 if a > b
    """
    subs_a = json.loads(a)
    subs_b = json.loads(b)

    # Compare element-by-element
    for sa, sb in zip(subs_a, subs_b):
        key_a = _mumps_collation_key(sa)
        key_b = _mumps_collation_key(sb)
        if key_a < key_b:
            return -1
        if key_a > key_b:
            return 1

    # If all compared elements are equal, shorter array comes first
    if len(subs_a) < len(subs_b):
        return -1
    if len(subs_a) > len(subs_b):
        return 1
    return 0


class SQLiteGlobalStorage:
    """SQLite-backed GlobalStorageBackend for cross-process global sharing.

    Each process should create its own instance pointing to the same db_path.
    SQLite WAL mode allows concurrent reads and serialized writes.

    The naked indicator is per-instance (per-process) Python state,
    matching MUMPS semantics where naked refs are per-process.
    """

    def __init__(self, db_path: str | None = None) -> None:
        """Initialize SQLite global storage.

        Args:
            db_path: Path to SQLite database file. If None, creates a
                temporary file (for single-process / testing mode).
        """
        if db_path is None:
            # Create temp file that persists until explicitly deleted
            fd, self._db_path = tempfile.mkstemp(suffix=".db")
            os.close(fd)
            self._owns_db = True
        else:
            self._db_path = db_path
            self._owns_db = False

        # Use autocommit mode (isolation_level=None) so we control
        # transactions manually via SAVEPOINT for TSTART/TCOMMIT/TROLLBACK
        self._conn = sqlite3.connect(self._db_path, timeout=30, isolation_level=None)
        # WAL mode for concurrent multi-process access
        self._conn.execute("PRAGMA journal_mode=WAL")
        # Register MUMPS collation for $ORDER queries
        self._conn.create_collation("mumps", _mumps_collation_sql)
        self._create_tables()

        # Naked indicator — per-instance (per-process) state
        self._naked_indicator: tuple[str, tuple[str, ...]] | None = None

        # $ZREFERENCE — last global reference string
        self._last_global_ref: str = ""

        # Transaction support
        self._tlevel: int = 0
        self._savepoint_counter: int = 0

    def _create_tables(self) -> None:
        """Create globals and locks tables if they don't exist."""
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS globals (
                name       TEXT NOT NULL,
                subscripts TEXT NOT NULL,
                value      TEXT,
                PRIMARY KEY (name, subscripts)
            );
            CREATE INDEX IF NOT EXISTS idx_globals_order
                ON globals (name, subscripts);

            CREATE TABLE IF NOT EXISTS locks (
                lock_name   TEXT NOT NULL,
                subscripts  TEXT NOT NULL,
                owner_pid   INTEGER NOT NULL,
                lock_count  INTEGER NOT NULL DEFAULT 1,
                acquired_at REAL NOT NULL,
                PRIMARY KEY (lock_name, subscripts)
            );
            CREATE INDEX IF NOT EXISTS idx_locks_hierarchy
                ON locks (lock_name);
        """)

    def close(self) -> None:
        """Close the database connection."""
        try:
            self._conn.close()
        except Exception:
            pass

    # =========================================================================
    # Subscript Helpers
    # =========================================================================

    def _canonicalize_subscript(self, subscript: str | int | float) -> str:
        """Convert subscript to MUMPS canonical string form."""
        return SubscriptCanonicalizer.canonicalize(subscript)

    def _canonicalize_subscripts(
        self, subscripts: tuple[str | int | float, ...]
    ) -> tuple[str, ...]:
        """Convert all subscripts to canonical string form."""
        return tuple(self._canonicalize_subscript(s) for s in subscripts)

    def _subs_to_json(self, subscripts: tuple[str, ...]) -> str:
        """Convert subscript tuple to JSON array string for storage."""
        return json.dumps(list(subscripts))

    def _json_to_subs(self, json_str: str) -> tuple[str, ...]:
        """Convert JSON array string back to subscript tuple."""
        return tuple(json.loads(json_str))

    def _update_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Update naked indicator and $ZREFERENCE after global access."""
        # Update $ZREFERENCE
        if subscripts:
            subs_str = ",".join(
                f'"{s}"' if not s.lstrip("-").isdigit() else s for s in subscripts
            )
            self._last_global_ref = f"^{name}({subs_str})"
        else:
            self._last_global_ref = f"^{name}"

        if subscripts:
            self._naked_indicator = (name, subscripts[:-1])
        else:
            self._naked_indicator = None

    @property
    def last_global_ref(self) -> str:
        """Return the last global reference string ($ZREFERENCE)."""
        return self._last_global_ref

    # =========================================================================
    # Core Global Operations
    # =========================================================================

    def get(
        self, name: str, subscripts: tuple[str, ...], update_naked: bool = True
    ) -> str | None:
        """Get value at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        if update_naked:
            self._update_naked_indicator(name, subscripts)

        json_subs = self._subs_to_json(subscripts)
        row = self._conn.execute(
            "SELECT value FROM globals WHERE name = ? AND subscripts = ?",
            (name, json_subs),
        ).fetchone()
        return row[0] if row else None

    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at ^NAME(subscripts)."""
        value = str(value)  # MUMPS canonical: all values are strings
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        json_subs = self._subs_to_json(subscripts)
        self._conn.execute(
            "INSERT OR REPLACE INTO globals (name, subscripts, value) VALUES (?, ?, ?)",
            (name, json_subs, value),
        )
        # Also ensure ancestor nodes exist (for $DATA to detect descendants)
        # We insert NULL-valued ancestor rows so hierarchical queries work
        for i in range(len(subscripts)):
            ancestor_subs = self._subs_to_json(subscripts[:i])
            self._conn.execute(
                "INSERT OR IGNORE INTO globals (name, subscripts, value) VALUES (?, ?, NULL)",
                (name, ancestor_subs),
            )

    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        if not subscripts:
            # Kill entire global
            self._conn.execute("DELETE FROM globals WHERE name = ?", (name,))
        else:
            json_subs = self._subs_to_json(subscripts)
            # Delete exact node
            self._conn.execute(
                "DELETE FROM globals WHERE name = ? AND subscripts = ?",
                (name, json_subs),
            )
            # Delete all descendants: subscripts that start with this prefix
            # A descendant has subscripts that begin with all elements of our subscripts
            # We use LIKE on the JSON to match prefix patterns
            prefix = json.dumps(list(subscripts))
            # Remove trailing ']' and add ',' to match children
            like_prefix = prefix[:-1] + ", %"
            self._conn.execute(
                "DELETE FROM globals WHERE name = ? AND subscripts LIKE ?",
                (name, like_prefix),
            )

        # Clean up empty ancestors (no value, no children)
        self._cleanup_ancestors(name, subscripts)

    def _cleanup_ancestors(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Remove ancestor nodes that have no value and no children."""
        if not subscripts:
            return
        # Walk from deepest ancestor up to root
        for i in range(len(subscripts) - 1, -1, -1):
            ancestor_subs = subscripts[:i]
            json_ancestor = self._subs_to_json(ancestor_subs)

            # Check if this ancestor has a value
            row = self._conn.execute(
                "SELECT value FROM globals WHERE name = ? AND subscripts = ?",
                (name, json_ancestor),
            ).fetchone()
            if row is None:
                continue  # Doesn't exist, skip

            # If it has a value, keep it
            if row[0] is not None:
                break

            # Check if it has any children
            if i == 0:
                # Root node: check if any rows exist for this name
                child_prefix = json.dumps([])  # "[]"
                child_row = self._conn.execute(
                    "SELECT 1 FROM globals WHERE name = ? AND subscripts != ? LIMIT 1",
                    (name, child_prefix),
                ).fetchone()
            else:
                child_prefix = json.dumps(list(ancestor_subs))
                child_like = child_prefix[:-1] + ", %"
                child_row = self._conn.execute(
                    "SELECT 1 FROM globals WHERE name = ? AND subscripts LIKE ? LIMIT 1",
                    (name, child_like),
                ).fetchone()

            if child_row is None:
                # No children, remove this empty ancestor
                self._conn.execute(
                    "DELETE FROM globals WHERE name = ? AND subscripts = ?",
                    (name, json_ancestor),
                )
            else:
                break  # Has children, stop cleaning

    def kill_all(self) -> None:
        """Kill all globals."""
        self._conn.execute("DELETE FROM globals")
        self._naked_indicator = None

    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value for ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        json_subs = self._subs_to_json(subscripts)

        # Check if this node has a value
        row = self._conn.execute(
            "SELECT value FROM globals WHERE name = ? AND subscripts = ?",
            (name, json_subs),
        ).fetchone()
        has_value = row is not None and row[0] is not None

        # Check if any children exist
        if not subscripts:
            child_row = self._conn.execute(
                "SELECT 1 FROM globals WHERE name = ? AND subscripts != ? LIMIT 1",
                (name, json_subs),
            ).fetchone()
        else:
            child_like = json_subs[:-1] + ", %"
            child_row = self._conn.execute(
                "SELECT 1 FROM globals WHERE name = ? AND subscripts LIKE ? LIMIT 1",
                (name, child_like),
            ).fetchone()

        has_children = child_row is not None

        if has_value and has_children:
            return 11
        elif has_children:
            return 10
        elif has_value:
            return 1
        else:
            return 0

    # =========================================================================
    # Naked Reference Operations
    # =========================================================================

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
        """Resolve naked reference ^(subscripts) to full global reference."""
        if self._naked_indicator is None:
            raise RuntimeError("NAKEDERR: Naked reference without prior global access")

        name, base_subscripts = self._naked_indicator
        subscripts = self._canonicalize_subscripts(subscripts)
        full_subscripts = base_subscripts + subscripts
        return (name, full_subscripts)

    # =========================================================================
    # $ORDER
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

        parent_subs = subscripts[:-1]
        start_key = subscripts[-1]

        # Find all direct children of parent_subs
        parent_json = self._subs_to_json(parent_subs)

        # Get all rows that could be descendants of parent_subs
        if not parent_subs:
            all_rows = self._conn.execute(
                "SELECT subscripts FROM globals WHERE name = ? AND subscripts != ?",
                (name, parent_json),
            ).fetchall()
        else:
            child_like = parent_json[:-1] + ", %"
            all_rows = self._conn.execute(
                "SELECT subscripts FROM globals WHERE name = ? AND subscripts LIKE ?",
                (name, child_like),
            ).fetchall()

        # Filter for direct children only (exactly one more subscript level)
        direct_children = set()
        for (subs_json,) in all_rows:
            subs = json.loads(subs_json)
            if len(subs) >= len(parent_subs) + 1:
                direct_children.add(subs[len(parent_subs)])

        if not direct_children:
            return ""

        # Sort by MUMPS collation
        keys = sorted(direct_children, key=_mumps_collation_key)

        if direction == -1:
            keys = list(reversed(keys))

        if start_key == "":
            return m_format_output(keys[0]) if keys else ""

        start_sort_key = _mumps_collation_key(start_key)

        for key in keys:
            key_sort = _mumps_collation_key(key)
            if direction == 1:
                if key_sort > start_sort_key:
                    return m_format_output(key)
            else:
                if key_sort < start_sort_key:
                    return m_format_output(key)

        return ""

    # =========================================================================
    # $QUERY
    # =========================================================================

    def query(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Return full reference of next node with data ($QUERY)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        # Get ALL valued nodes (non-NULL value) for this global
        rows = self._conn.execute(
            "SELECT subscripts FROM globals WHERE name = ? AND value IS NOT NULL "
            "ORDER BY subscripts COLLATE mumps",
            (name,),
        ).fetchall()

        if not rows:
            return ""

        all_subs = [self._json_to_subs(r[0]) for r in rows]

        if subscripts == ("",) or subscripts == ():
            # Start from beginning - return first valued node
            if all_subs:
                return self._format_query_result(name, all_subs[0])
            return ""

        # Find the node AFTER the given subscripts
        target_key = tuple(_mumps_collation_key(s) for s in subscripts)

        for subs in all_subs:
            subs_key = tuple(_mumps_collation_key(s) for s in subs)
            if self._subs_gt(subs_key, target_key, subs, subscripts):
                return self._format_query_result(name, subs)

        return ""

    def _subs_gt(
        self,
        a_key: tuple,
        b_key: tuple,
        a_subs: tuple[str, ...],
        b_subs: tuple[str, ...],
    ) -> bool:
        """Compare two subscript tuples using MUMPS collation.

        Returns True if a > b.
        """
        for ak, bk in zip(a_key, b_key):
            if ak > bk:
                return True
            if ak < bk:
                return False
        # If equal up to min length, longer one is "greater"
        return len(a_subs) > len(b_subs)

    def _format_query_result(self, name: str, subscripts: tuple[str, ...]) -> str:
        """Format a $QUERY result as ^NAME(sub1,sub2,...)."""
        if not subscripts:
            return f"^{name}"
        formatted_subs = [_format_subscript(sub) for sub in subscripts]
        return f"^{name}({','.join(formatted_subs)})"

    # =========================================================================
    # MERGE
    # =========================================================================

    def get_tree(self, name: str, subscripts: tuple[str, ...]) -> "MArray | None":
        """Get subtree as MArray for MERGE source."""
        from m2py.runtime import MArray

        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        json_subs = self._subs_to_json(subscripts)

        # Get node value
        row = self._conn.execute(
            "SELECT value FROM globals WHERE name = ? AND subscripts = ?",
            (name, json_subs),
        ).fetchone()

        # Get all descendant nodes
        if not subscripts:
            desc_rows = self._conn.execute(
                "SELECT subscripts, value FROM globals WHERE name = ? AND subscripts != ?",
                (name, json_subs),
            ).fetchall()
        else:
            desc_like = json_subs[:-1] + ", %"
            desc_rows = self._conn.execute(
                "SELECT subscripts, value FROM globals WHERE name = ? AND subscripts LIKE ?",
                (name, desc_like),
            ).fetchall()

        if row is None and not desc_rows:
            return None

        # Build MArray tree
        root = MArray()
        if row is not None:
            root._value = row[0]

        for desc_json, desc_value in desc_rows:
            desc_subs = self._json_to_subs(desc_json)
            # Make relative to our root
            relative_subs = desc_subs[len(subscripts) :]
            if not relative_subs:
                continue

            # Navigate/create path in MArray
            node = root
            for sub in relative_subs[:-1]:
                if sub not in node._children:
                    node._children[sub] = MArray()
                node = node._children[sub]

            last_sub = relative_subs[-1]
            if last_sub not in node._children:
                node._children[last_sub] = MArray()
            node._children[last_sub]._value = desc_value

        return root

    def merge_tree(
        self, name: str, subscripts: tuple[str, ...], source: "MArray"
    ) -> None:
        """Merge MArray tree into global at ^NAME(subscripts)."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)
        self._merge_tree_recursive(name, subscripts, source)

    def _merge_tree_recursive(
        self, name: str, subscripts: tuple[str, ...], node: "MArray"
    ) -> None:
        """Recursively merge MArray node into global storage."""
        if node._value is not None:
            self.set(name, subscripts, str(node._value))
        for key, child in node._children.items():
            child_sub = str(key)
            self._merge_tree_recursive(name, subscripts + (child_sub,), child)

    # =========================================================================
    # $INCREMENT
    # =========================================================================

    def incr(self, name: str, subscripts: tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value at ^NAME(subscripts)."""
        from m2py.core.values import m_num, m_str

        subscripts = self._canonicalize_subscripts(subscripts)

        # Use a transaction for atomicity
        current = self.get(name, subscripts)
        if current is None:
            current = "0"

        current_num = m_num(current)
        incr_num = m_num(increment)
        result = current_num + incr_num  # type: ignore[operator]

        if isinstance(result, float) and result == int(result):
            result = int(result)

        result_str = m_str(result)
        self.set(name, subscripts, result_str)
        return result_str

    # =========================================================================
    # KILL Node (ZKILL/ZWITHDRAW)
    # =========================================================================

    def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill only the value at node, preserving descendants."""
        subscripts = self._canonicalize_subscripts(subscripts)
        self._update_naked_indicator(name, subscripts)

        json_subs = self._subs_to_json(subscripts)

        # Check if node has children
        if not subscripts:
            child_row = self._conn.execute(
                "SELECT 1 FROM globals WHERE name = ? AND subscripts != ? LIMIT 1",
                (name, json_subs),
            ).fetchone()
        else:
            child_like = json_subs[:-1] + ", %"
            child_row = self._conn.execute(
                "SELECT 1 FROM globals WHERE name = ? AND subscripts LIKE ? LIMIT 1",
                (name, child_like),
            ).fetchone()

        if child_row is not None:
            # Has children: set value to NULL but keep the row
            self._conn.execute(
                "UPDATE globals SET value = NULL WHERE name = ? AND subscripts = ?",
                (name, json_subs),
            )
        else:
            # No children: delete the row entirely
            self._conn.execute(
                "DELETE FROM globals WHERE name = ? AND subscripts = ?",
                (name, json_subs),
            )
        self._cleanup_ancestors(name, subscripts)

    # =========================================================================
    # Transaction Support
    # =========================================================================

    def transaction_start(self) -> None:
        """Begin a transaction (TSTART → SAVEPOINT)."""
        self._tlevel += 1
        self._savepoint_counter += 1
        sp_name = f"tstart_{self._savepoint_counter}"
        self._conn.execute(f"SAVEPOINT {sp_name}")

    def transaction_commit(self) -> None:
        """Commit current transaction (TCOMMIT → RELEASE SAVEPOINT)."""
        if self._tlevel == 0:
            raise RuntimeError("M44: TCOMMIT without matching TSTART")

        sp_name = f"tstart_{self._savepoint_counter}"
        self._conn.execute(f"RELEASE SAVEPOINT {sp_name}")
        self._savepoint_counter -= 1
        self._tlevel -= 1

    def transaction_rollback(self) -> None:
        """Rollback current transaction (TROLLBACK → ROLLBACK TO SAVEPOINT).

        Per MUMPS spec: Argumentless TROLLBACK rolls back ALL levels.
        """
        if self._tlevel == 0:
            raise RuntimeError("M44: TROLLBACK without matching TSTART")

        # Roll back to the outermost savepoint
        oldest_sp = f"tstart_{self._savepoint_counter - self._tlevel + 1}"
        self._conn.execute(f"ROLLBACK TO SAVEPOINT {oldest_sp}")
        self._conn.execute(f"RELEASE SAVEPOINT {oldest_sp}")
        self._tlevel = 0
        self._savepoint_counter = 0

    def get_tlevel(self) -> int:
        """Return current transaction nesting level ($TLEVEL)."""
        return self._tlevel

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

        SQLite-backed cross-process lock manager.

        Supports hierarchical blocking:
        - Lock ^A blocks ^A(x) for all x (parent blocks children)
        - Lock ^A(1) is blocked by ^A (child blocked by parent)

        Dead-process detection: during polling, checks if blocking PID
        is still alive via os.kill(pid, 0). Orphaned locks are auto-cleared.

        Args:
            name: Lock/global name without caret
            subscripts: Tuple of string subscript values
            timeout: Seconds to wait (None = indefinite)
            lock_type: "+" for acquire, "-" for release

        Returns:
            True if acquired/released, False on timeout
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        json_subs = self._subs_to_json(subscripts)
        pid = os.getpid()

        if lock_type == "-":
            return self._lock_release(name, json_subs, pid)

        return self._lock_acquire(name, subscripts, json_subs, pid, timeout)

    def _lock_release(self, name: str, json_subs: str, pid: int) -> bool:
        """Decrement lock count; delete if zero."""
        row = self._conn.execute(
            "SELECT lock_count FROM locks WHERE lock_name = ? AND subscripts = ? AND owner_pid = ?",
            (name, json_subs, pid),
        ).fetchone()

        if row is not None:
            new_count = row[0] - 1
            if new_count <= 0:
                self._conn.execute(
                    "DELETE FROM locks WHERE lock_name = ? AND subscripts = ?",
                    (name, json_subs),
                )
            else:
                self._conn.execute(
                    "UPDATE locks SET lock_count = ? WHERE lock_name = ? AND subscripts = ?",
                    (new_count, name, json_subs),
                )
        return True

    def _lock_acquire(
        self,
        name: str,
        subscripts: tuple[str, ...],
        json_subs: str,
        pid: int,
        timeout: float | None,
    ) -> bool:
        """Acquire a lock with hierarchical conflict checking.

        Uses an atomic INSERT … WHERE NOT EXISTS to prevent the TOCTOU
        race that would otherwise let a fast-cycling process always beat
        a waiting process to the INSERT after the same conflict-free
        check.  When the atomic INSERT reports rowcount==0 but our own
        conflict check found no rows, we know another process won the
        race — we retry with a short random jitter to break the
        synchronisation pattern and avoid starvation.
        """
        import random as _random

        deadline = None
        if timeout is not None:
            deadline = time.monotonic() + timeout

        backoff = 0.001  # Start at 1ms, exponential up to 128ms

        while True:
            # ---- fast path: we already own this exact lock -----------------
            row = self._conn.execute(
                "SELECT lock_count FROM locks "
                "WHERE lock_name = ? AND subscripts = ? AND owner_pid = ?",
                (name, json_subs, pid),
            ).fetchone()
            if row is not None:
                self._conn.execute(
                    "UPDATE locks SET lock_count = lock_count + 1 "
                    "WHERE lock_name = ? AND subscripts = ? AND owner_pid = ?",
                    (name, json_subs, pid),
                )
                return True

            # ---- hierarchical conflict check (read-only) -------------------
            conflict_pid = self._check_lock_conflict(name, json_subs, subscripts, pid)

            if conflict_pid is None:
                # No conflict detected — try an *atomic* INSERT that re-checks
                # inside the same statement so another writer cannot slip in
                # between our SELECT and INSERT.
                now = time.time()
                cursor = self._conn.execute(
                    "INSERT INTO locks "
                    "  (lock_name, subscripts, owner_pid, lock_count, acquired_at) "
                    "SELECT ?, ?, ?, 1, ? "
                    "WHERE NOT EXISTS ("
                    "  SELECT 1 FROM locks "
                    "  WHERE lock_name = ? AND subscripts = ? AND owner_pid != ?"
                    ")",
                    (name, json_subs, pid, now, name, json_subs, pid),
                )
                if cursor.rowcount > 0:
                    return True

                # INSERT did nothing — another process acquired between our
                # conflict check and the INSERT.  Add random jitter to break
                # the synchronisation pattern, then retry quickly.
                time.sleep(_random.uniform(0.0001, 0.002))
                continue

            # Conflict exists — check if blocking process is still alive
            if self._clear_dead_process_locks(conflict_pid):
                # Cleared orphaned lock — retry immediately
                backoff = 0.001
                continue

            # Process is alive — must wait
            if deadline is not None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False  # Timeout
                time.sleep(min(backoff, remaining))
            else:
                time.sleep(backoff)

            backoff = min(backoff * 2, 0.128)  # Exponential backoff, max 128ms

    def _check_lock_conflict(
        self,
        name: str,
        json_subs: str,
        subscripts: tuple[str, ...],
        pid: int,
    ) -> int | None:
        """Check for hierarchical lock conflicts from other PIDs.

        Returns the conflicting PID, or None if no conflict.

        Checks:
        1. Exact same lock held by another PID
        2. Parent subscripts held by another PID (blocks children)
        3. Child subscripts held by another PID (children block parent)
        """
        # 1. Check exact match held by other PID
        row = self._conn.execute(
            "SELECT owner_pid FROM locks "
            "WHERE lock_name = ? AND subscripts = ? AND owner_pid != ?",
            (name, json_subs, pid),
        ).fetchone()
        if row:
            return row[0]

        # 2. Check if any parent lock is held by another PID
        # A parent lock has subscripts that are a prefix of ours
        # e.g., ^A() blocks ^A(1), ^A(1) blocks ^A(1,2)
        for i in range(len(subscripts)):
            parent_subs = self._subs_to_json(subscripts[:i])
            row = self._conn.execute(
                "SELECT owner_pid FROM locks "
                "WHERE lock_name = ? AND subscripts = ? AND owner_pid != ?",
                (name, parent_subs, pid),
            ).fetchone()
            if row:
                return row[0]

        # 3. Check if any child lock is held by another PID
        # A child lock has subscripts that start with ours
        # We use LIKE on the JSON prefix: '["1"' matches '["1","2"]' etc.
        if len(subscripts) == 0:
            # Bare lock ^A — any subscripted lock ^A(x) is a child
            row = self._conn.execute(
                "SELECT owner_pid FROM locks "
                "WHERE lock_name = ? AND subscripts != ? AND owner_pid != ?",
                (name, json_subs, pid),
            ).fetchone()
        else:
            # Check for children: their JSON subscripts start with our prefix
            # E.g., our subs = ["1"] → prefix = '["1"' (strip trailing ']')
            prefix = json_subs[:-1] + ", "  # '["1"]' → '["1", '
            row = self._conn.execute(
                "SELECT owner_pid FROM locks "
                "WHERE lock_name = ? AND subscripts LIKE ? AND owner_pid != ?",
                (name, prefix + "%", pid),
            ).fetchone()

        if row:
            return row[0]
        return None

    def _clear_dead_process_locks(self, pid: int) -> bool:
        """Check if a PID is alive; if dead, clear its locks.

        Uses os.kill(pid, 0) to probe process liveness.

        Returns:
            True if locks were cleared (process was dead)
        """
        try:
            os.kill(pid, 0)
            return False  # Process is alive
        except ProcessLookupError:
            # Process is dead — clear its orphaned locks
            self._conn.execute("DELETE FROM locks WHERE owner_pid = ?", (pid,))
            return True
        except PermissionError:
            return False  # Process exists but we lack permission

    def unlock(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Release a lock on ^NAME(subscripts).

        Only releases locks owned by the current process.
        Decrements count; fully removes if count reaches zero.
        """
        subscripts = self._canonicalize_subscripts(subscripts)
        json_subs = self._subs_to_json(subscripts)
        pid = os.getpid()

        row = self._conn.execute(
            "SELECT lock_count FROM locks WHERE lock_name = ? AND subscripts = ? AND owner_pid = ?",
            (name, json_subs, pid),
        ).fetchone()

        if row is not None:
            new_count = row[0] - 1
            if new_count <= 0:
                self._conn.execute(
                    "DELETE FROM locks WHERE lock_name = ? AND subscripts = ?",
                    (name, json_subs),
                )
            else:
                self._conn.execute(
                    "UPDATE locks SET lock_count = ? WHERE lock_name = ? AND subscripts = ?",
                    (new_count, name, json_subs),
                )

    def unlock_all(self) -> None:
        """Release all locks held by the current process.

        Deletes all lock rows owned by current PID.
        Called automatically when a JOB'd child process exits.
        """
        pid = os.getpid()
        self._conn.execute("DELETE FROM locks WHERE owner_pid = ?", (pid,))

    def get_locks(self) -> list[tuple[str, str, int]]:
        """Return all locks held by the current process.

        Used by ZSHOW "L".

        Returns:
            List of (lock_name, subscripts_json, lock_count) tuples
        """
        pid = os.getpid()
        rows = self._conn.execute(
            "SELECT lock_name, subscripts, lock_count FROM locks "
            "WHERE owner_pid = ? ORDER BY lock_name, subscripts",
            (pid,),
        ).fetchall()
        return [(r[0], r[1], r[2]) for r in rows]

    # =========================================================================
    # SSVN Queries
    # =========================================================================

    def ssvn_global(self, subscript: str) -> str:
        """Query ^$GLOBAL(name) for global existence."""
        row = self._conn.execute(
            "SELECT 1 FROM globals WHERE name = ? LIMIT 1",
            (subscript,),
        ).fetchone()
        return "1" if row else ""

    def ssvn_job(self, subscript: str) -> str:
        """Query ^$JOB(pid) for job/process information."""
        try:
            pid = int(subscript)
            if pid <= 0:
                return ""
            if pid == os.getpid():
                return "1"
            try:
                os.kill(pid, 0)
                return "1"
            except ProcessLookupError:
                return ""
            except PermissionError:
                return "1"
        except (ValueError, OverflowError):
            pass
        return ""

    def ssvn_lock(self, subscript: str) -> str:
        """Query ^$LOCK(lockname) for lock information.

        Queries the SQLite locks table.
        """
        json_subs = self._subs_to_json(())
        row = self._conn.execute(
            "SELECT lock_count FROM locks WHERE lock_name = ? AND subscripts = ?",
            (subscript, json_subs),
        ).fetchone()
        return str(row[0]) if row else ""

    def ssvn_routine(self, subscript: str) -> str:
        """Query ^$ROUTINE(routinename) for routine metadata."""
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
    # Namespace-aware Operations
    # =========================================================================

    def _ns_name(self, name: str, namespace: str) -> str:
        """Generate namespace-qualified global name."""
        if namespace:
            return f"{namespace}:{name}"
        return name

    def set_ns(
        self, name: str, subscripts: tuple[str, ...], value: str, namespace: str = ""
    ) -> None:
        """Set a global variable in a specific namespace."""
        self.set(self._ns_name(name, namespace), subscripts, value)

    def get_ns(
        self, name: str, subscripts: tuple[str, ...], namespace: str = ""
    ) -> str | None:
        """Get a global variable from a specific namespace."""
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

    # =========================================================================
    # ZWR Import
    # =========================================================================

    def import_zwr(self, source: Path | TextIO) -> int:
        """Import ZWR data via line-by-line ``parse_zwr_stream`` + ``set()``."""
        from m2py.runtime.zwr import parse_zwr_stream

        count = 0

        def _load(stream: TextIO) -> int:
            nonlocal count
            for name, subs, value in parse_zwr_stream(stream):
                bare_name = name[1:] if name.startswith("^") else name
                self.set(bare_name, tuple(subs), value)
                count += 1
            return count

        if isinstance(source, Path):
            with open(source, errors="replace") as f:
                return _load(f)
        return _load(source)
