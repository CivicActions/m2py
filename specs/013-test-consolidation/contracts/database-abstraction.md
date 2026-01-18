# Database Abstraction Contract

**Spec**: 013-test-consolidation  
**Scope**: LOCK, transactions, SSVNs (FR-015, FR-019, FR-029)

## Protocol Extension

The existing `GlobalStorageBackend` protocol is extended with the following methods.

---

## Lock Operations (FR-019)

### `lock(name, subscripts, timeout, lock_type) → bool`

**Parameters**:
- `name: str` - Global/lock name without caret
- `subscripts: tuple[str, ...]` - Subscript path
- `timeout: float | None` - Timeout in seconds, None for indefinite
- `lock_type: str` - "+" for increment, "-" for decrement

**Returns**: `bool` - True if lock acquired, False if timeout

**Side Effects**: Sets `$TEST` to 1 (success) or 0 (timeout)

**MUMPS Examples**:
```mumps
L +^PATIENT(ID):5     ; Lock with 5-second timeout
L +^PATIENT(ID)       ; Lock indefinitely
L -^PATIENT(ID)       ; Unlock
```

**Backend Implementations**:

| Backend | Implementation |
|---------|----------------|
| Memory | In-process lock table with counts |
| YottaDB | `yottadb.lock_incr()` / `yottadb.lock_decr()` |
| IRIS | `irispy.lock()` / `irispy.unlock()` |

---

### `unlock(name, subscripts) → None`

**Parameters**:
- `name: str` - Global/lock name
- `subscripts: tuple[str, ...]` - Subscript path

**Behavior**: Decrements lock count, releases when count reaches 0.

---

### `unlock_all() → None`

**Behavior**: Releases all locks held by current process.

**MUMPS**: `L` (argumentless LOCK releases all locks)

---

## Transaction Operations (FR-015)

### `transaction_start() → None`

**MUMPS**: `TSTART`

**Behavior**:
- Increments transaction level
- Takes snapshot for rollback (Memory backend)
- Begins native transaction (YDB/IRIS)

**Nested Transactions**:
- MUMPS supports nested TSTART
- Each TSTART increments `$TLEVEL`
- TROLLBACK can rollback specific levels

---

### `transaction_commit() → None`

**MUMPS**: `TCOMMIT`

**Behavior**:
- Decrements transaction level
- When level reaches 0, persists changes
- Nested commit only decrements level

---

### `transaction_rollback() → None`

**MUMPS**: `TROLLBACK`

**Behavior**:
- Reverts changes since matching TSTART
- Resets `$TLEVEL` to previous value

---

### `get_tlevel() → int`

**MUMPS**: `$TLEVEL`

**Returns**: Current transaction nesting level (0 = no transaction)

---

## Backend Implementation Notes

### Memory Backend

```python
class InMemoryGlobalStorage:
    def __init__(self):
        self._lock_table: dict[tuple[str, tuple], int] = {}
        self._transaction_snapshots: list[dict] = []
        self._tlevel: int = 0
    
    def lock(self, name, subscripts, timeout=None, lock_type="+"):
        key = (name, subscripts)
        if lock_type == "+":
            # Memory backend: always succeeds immediately
            self._lock_table[key] = self._lock_table.get(key, 0) + 1
            return True
        else:  # "-"
            if key in self._lock_table:
                self._lock_table[key] -= 1
                if self._lock_table[key] <= 0:
                    del self._lock_table[key]
            return True
    
    def transaction_start(self):
        # Save snapshot of current state
        import copy
        self._transaction_snapshots.append(copy.deepcopy(self._globals))
        self._tlevel += 1
    
    def transaction_rollback(self):
        if self._tlevel > 0:
            self._globals = self._transaction_snapshots.pop()
            self._tlevel -= 1
```

### YottaDB Backend

```python
class YottaDBBackend:
    def lock(self, name, subscripts, timeout=None, lock_type="+"):
        import yottadb
        key = yottadb.Key(name)[subscripts] if subscripts else yottadb.Key(name)
        if lock_type == "+":
            try:
                if timeout is not None:
                    # lock_incr with timeout
                    yottadb.lock_incr(key, timeout_nsec=int(timeout * 1e9))
                else:
                    yottadb.lock_incr(key)
                return True
            except yottadb.YDBTimeoutError:
                return False
        else:
            yottadb.lock_decr(key)
            return True
    
    def transaction_start(self):
        # YDB uses callback-based transactions via yottadb.tp()
        # Implementation requires restructuring to batch operations
        ...
```

---

## SSVN Queries (FR-029)

### `ssvn_global(subscript) → str`

**MUMPS**: `^$GLOBAL(name)`

**Returns**: Information about global existence
- Returns non-empty if global exists

---

### `ssvn_job(subscript) → str`

**MUMPS**: `^$JOB(pid)`

**Returns**: Job/process information
- Requires backend support for process queries

---

### `ssvn_lock(subscript) → str`

**MUMPS**: `^$LOCK(lockname)`

**Returns**: Lock owner/status information

---

### `ssvn_routine(subscript) → str`

**MUMPS**: `^$ROUTINE(routinename)`

**Returns**: Routine metadata
- Source path, compile date, etc.

---

## Timeout Behavior (FR-028)

All timeout operations MUST set `$TEST`:
- `$TEST = 1` on success
- `$TEST = 0` on timeout

Affected commands:
- `LOCK name:timeout`
- `READ var:timeout`
- `OPEN device:timeout`
- `JOB routine:timeout`

**Implementation**: Runtime maintains `_test` variable, operations update it.
