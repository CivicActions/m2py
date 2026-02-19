# Backend Protocol Contract

**Date**: 2025-02-19  
**Feature**: 025-database-backends  
**Phase**: 1 (Design & Contracts)

## Overview

This document references the existing `GlobalStorageBackend` protocol that all backend implementations must adhere to. The protocol is defined in `src/m2py/runtime/globals.py` and has been stable since m2py's initial release.

**No protocol changes are required** for this feature - YottaDBGlobalStorage and IRISGlobalStorage are pure implementations of the existing interface.

## Protocol Definition

**Location**: [src/m2py/runtime/globals.py](../../../src/m2py/runtime/globals.py)

**Protocol Class**: `GlobalStorageBackend`

**Purpose**: Define a standard interface for MUMPS global storage backends, supporting:
- Basic CRUD operations (get, set, kill)
- Metadata queries (data)
- Tree traversal (order, query)
- Bulk operations (get_tree, merge_tree)
- Atomic operations (incr)
- Synchronization (lock, unlock)
- Transactions (start, commit, rollback)
- Structured System Variable Nodes (SSVN)

## Method Contracts

### Basic Operations

#### `get(name: str, *subscripts: str) -> str | None`

**Purpose**: Retrieve value of global node.

**Parameters**:
- `name`: Global name (e.g., `"^Patient"`)
- `subscripts`: Variable-length subscript tuple (e.g., `"123", "Name"`)

**Returns**: 
- Node value as string if defined
- `None` if node undefined

**Behavior**:
- Must canonicalize subscripts before lookup (numeric vs string collation)
- Must return `None` for undefined nodes (not raise exception)
- Must decode bytes to UTF-8 string (if backend uses bytes internally)

**Example**:
```python
backend.set("^Patient", "123", "Name", value="John")
assert backend.get("^Patient", "123", "Name") == "John"
assert backend.get("^Patient", "456", "Name") is None  # Undefined
```

#### `set(name: str, *subscripts: str, value: str) -> None`

**Purpose**: Set value of global node.

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple
- `value`: Node value (string)

**Returns**: None

**Behavior**:
- Must canonicalize subscripts before storage
- Must create intermediate nodes if necessary (implicit $DATA=10 for ancestors)
- Must update naked reference indicator
- Must encode string to bytes if backend requires

**Example**:
```python
backend.set("^Patient", "123", "Name", value="John")
assert backend.data("^Patient", "123") == 10  # Has descendants
```

#### `kill(name: str, *subscripts: str) -> None`

**Purpose**: Delete global node and all descendants.

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple

**Returns**: None

**Behavior**:
- Must delete specified node and entire subtree
- Must be idempotent (no error if node undefined)
- Must update naked reference indicator

**Example**:
```python
backend.set("^Patient", "123", "Name", value="John")
backend.set("^Patient", "123", "Age", value="45")
backend.kill("^Patient", "123")
assert backend.get("^Patient", "123", "Name") is None
assert backend.get("^Patient", "123", "Age") is None
```

#### `kill_all(name: str) -> None`

**Purpose**: Delete entire global and all nodes.

**Parameters**:
- `name`: Global name

**Returns**: None

**Behavior**:
- Must delete global root and entire tree
- Must be idempotent

**Example**:
```python
backend.kill_all("^Patient")
assert backend.data("^Patient") == 0
```

### Metadata Operations

#### `data(name: str, *subscripts: str) -> int`

**Purpose**: Return MUMPS $DATA value for node.

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple

**Returns**: Integer code:
- `0`: Node undefined, no descendants
- `1`: Node defined, no descendants
- `10`: Node undefined, has descendants
- `11`: Node defined, has descendants

**Behavior**:
- Must check both node existence and descendant existence
- Must return exact $DATA semantics per ANSI MUMPS standard

**Example**:
```python
backend.set("^Patient", "123", "Name", value="John")
assert backend.data("^Patient") == 10  # Undefined, has descendants
assert backend.data("^Patient", "123") == 10  # Undefined, has descendants
assert backend.data("^Patient", "123", "Name") == 1  # Defined, no descendants
assert backend.data("^Patient", "456") == 0  # Undefined, no descendants
```

### Traversal Operations

#### `order(name: str, *subscripts: str) -> str | None`

**Purpose**: Return next subscript at current level (MUMPS $ORDER).

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple (last element is starting point)

**Returns**:
- Next subscript as string
- `None` if no more subscripts

**Behavior**:
- Must follow MUMPS collation order (numeric < string)
- Must return empty string for first subscript if starting from `""`
- Must canonicalize input subscripts

**Example**:
```python
backend.set("^Patient", "1", value="Alice")
backend.set("^Patient", "2", value="Bob")
backend.set("^Patient", "10", value="Charlie")

assert backend.order("^Patient", "") == "1"
assert backend.order("^Patient", "1") == "2"
assert backend.order("^Patient", "2") == "10"
assert backend.order("^Patient", "10") is None
```

#### `query(name: str, *subscripts: str) -> tuple[str, tuple[str, ...]] | None`

**Purpose**: Return next node in tree traversal (MUMPS $QUERY).

**Parameters**:
- `name`: Global name
- `subscripts`: Starting subscript tuple

**Returns**:
- Tuple of `(global_name, subscripts)` for next node
- `None` if no more nodes

**Behavior**:
- Must traverse in MUMPS standard order (depth-first, pre-order)
- Must return next **defined** node (skip intermediates with $DATA=10)
- Must handle tree boundaries correctly

**Example**:
```python
backend.set("^Patient", "1", "Name", value="Alice")
backend.set("^Patient", "2", "Name", value="Bob")

result = backend.query("^Patient", "")
assert result == ("^Patient", ("1", "Name"))

result = backend.query("^Patient", "1", "Name")
assert result == ("^Patient", ("2", "Name"))
```

### Bulk Operations

#### `get_tree(name: str, *subscripts: str) -> dict[tuple[str, ...], str]`

**Purpose**: Get all nodes in subtree.

**Parameters**:
- `name`: Global name
- `subscripts`: Root subscript tuple

**Returns**: Dictionary mapping subscript tuples to values

**Behavior**:
- Must return only defined nodes ($DATA=1 or $DATA=11)
- Subscript tuples are relative to root (exclude root subscripts)

**Example**:
```python
backend.set("^Patient", "123", "Name", value="John")
backend.set("^Patient", "123", "Age", value="45")

tree = backend.get_tree("^Patient", "123")
assert tree == {
    ("Name",): "John",
    ("Age",): "45"
}
```

#### `merge_tree(target_name: str, target_subscripts: tuple[str, ...], source_tree: dict[tuple[str, ...], str]) -> None`

**Purpose**: Bulk set operation (MUMPS MERGE semantics).

**Parameters**:
- `target_name`: Target global name
- `target_subscripts`: Target root subscripts
- `source_tree`: Dictionary of relative subscripts to values

**Returns**: None

**Behavior**:
- Must set all nodes in source_tree under target root
- Must overwrite existing nodes at target
- Must preserve nodes not in source_tree

**Example**:
```python
source = {
    ("Name",): "John",
    ("Age",): "45"
}
backend.merge_tree("^Patient", ("123",), source)

assert backend.get("^Patient", "123", "Name") == "John"
assert backend.get("^Patient", "123", "Age") == "45"
```

### Atomic Operations

#### `incr(name: str, *subscripts: str, delta: int | float = 1) -> int | float`

**Purpose**: Atomic increment operation (MUMPS $INCREMENT).

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple
- `delta`: Increment value (default: 1)

**Returns**: New value after increment

**Behavior**:
- Must be atomic (thread-safe, transaction-safe)
- Must treat undefined node as 0
- Must return numeric value (int or float based on delta type)

**Example**:
```python
backend.set("^Counter", "requests", value="100")
new_value = backend.incr("^Counter", "requests", delta=5)
assert new_value == 105
assert backend.get("^Counter", "requests") == "105"

# Undefined node
new_value = backend.incr("^Counter", "new", delta=1)
assert new_value == 1
```

### Synchronization Operations

#### `lock(name: str, *subscripts: str, timeout: float | None = None) -> bool`

**Purpose**: Acquire lock on global node (MUMPS LOCK).

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple
- `timeout`: Timeout in seconds (`None` = wait indefinitely)

**Returns**:
- `True` if lock acquired
- `False` if timeout expired

**Behavior**:
- Must be process/thread-scoped (lock held until unlocked or process exit)
- Must block if lock held by another process (up to timeout)
- Must support nested locks (same process can re-lock same node)
- Must update lock state (for backends that need tracking)

**Example**:
```python
success = backend.lock("^JobQueue", "process1", timeout=10.0)
assert success is True

# Lock with timeout
success = backend.lock("^Resource", "contested", timeout=0.1)
# Returns False if another process holds lock
```

#### `unlock(name: str, *subscripts: str) -> None`

**Purpose**: Release lock on global node (MUMPS LOCK without +).

**Parameters**:
- `name`: Global name
- `subscripts`: Subscript tuple

**Returns**: None

**Behavior**:
- Must release lock held by current process
- Must be idempotent (no error if lock not held)
- Must maintain other locks (selective unlock)

**Example**:
```python
backend.lock("^Resource", "R1")
backend.lock("^Resource", "R2")
backend.unlock("^Resource", "R1")
# R2 still locked
```

#### `unlock_all() -> None`

**Purpose**: Release all locks held by current process.

**Parameters**: None

**Returns**: None

**Behavior**:
- Must release all locks acquired by current process
- Must be idempotent

**Example**:
```python
backend.lock("^R1")
backend.lock("^R2")
backend.unlock_all()
# All locks released
```

### Transaction Operations

#### `transaction_start() -> None`

**Purpose**: Start transaction (MUMPS TSTART).

**Parameters**: None

**Returns**: None

**Behavior**:
- Must support nested transactions (increment transaction level)
- Must buffer operations until commit (or execute immediately if backend supports)
- Must be thread-safe

**Example**:
```python
backend.transaction_start()
backend.set("^Account", "123", "Balance", value="100")
# Operations not visible outside transaction yet
```

#### `transaction_commit() -> None`

**Purpose**: Commit transaction (MUMPS TCOMMIT).

**Parameters**: None

**Returns**: None

**Behavior**:
- Must decrement transaction level
- Only commit to database when outermost transaction commits
- Must be atomic (all-or-nothing)
- Must raise exception if no transaction active

**Example**:
```python
backend.transaction_start()
backend.set("^Account", "123", "Balance", value="100")
backend.transaction_commit()
# Changes now visible
```

#### `transaction_rollback() -> None`

**Purpose**: Rollback transaction (MUMPS TROLLBACK).

**Parameters**: None

**Returns**: None

**Behavior**:
- Must discard all changes since transaction_start()
- Must decrement transaction level
- Must raise exception if no transaction active

**Example**:
```python
backend.transaction_start()
backend.set("^Account", "123", "Balance", value="100")
backend.transaction_rollback()
# Changes discarded, Balance unchanged
```

### SSVN Operations

Structured System Variable Node operations (same semantics as basic operations, but for system variables like `^$JOB`, `^$LOCK`, etc.).

**Methods**:
- `ssvn_get(name: str, *subscripts: str) -> str | None`
- `ssvn_set(name: str, *subscripts: str, value: str) -> None`
- `ssvn_data(name: str, *subscripts: str) -> int`
- `ssvn_order(name: str, *subscripts: str) -> str | None`
- `ssvn_query(name: str, *subscripts: str) -> tuple[str, tuple[str, ...]] | None`

**Behavior**: Same as corresponding non-SSVN methods, but operate on system-wide globals with special semantics (e.g., `^$JOB` for job information).

## Implementation Requirements

### Subscript Canonicalization

**Requirement**: All backends MUST use `SubscriptCanonicalizer` to normalize subscripts before storage/lookup.

**Rationale**: MUMPS distinguishes numeric vs string subscripts in collation order. Subscript `"1"` and `1` must be treated identically.

**Implementation**:
```python
from .subscript_canonicalizer import SubscriptCanonicalizer

class MyBackend(GlobalStorageBackend):
    def __init__(self):
        self._canonicalizer = SubscriptCanonicalizer()
    
    def get(self, name: str, *subscripts: str) -> str | None:
        canonical = [self._canonicalizer.canonicalize(s) for s in subscripts]
        # Use canonical subscripts for lookup
```

### Exception Handling

**Requirement**: Backends MUST translate SDK-specific exceptions to m2py exception types.

**Standard Exceptions**:
- `BackendConnectionError`: Connection failures, SDK not available
- `BackendPermissionError`: Permission denied
- `BackendTimeoutError`: Operation timeout
- `BackendConfigurationError`: Missing configuration

**Implementation**:
```python
from .backend_exceptions import BackendConnectionError

def get(self, name: str, *subscripts: str) -> str | None:
    try:
        return self._sdk.get(name, subscripts)
    except SDKException as e:
        raise BackendConnectionError(f"Get failed: {e}") from e
```

**Requirement**: Original exception MUST be chained via `from` clause for debugging.

### Thread Safety

**Requirement**: Backends MUST be thread-safe (multiple threads can call methods concurrently).

**Implementation**: Use `threading.Lock` around SDK operations if SDK is not thread-safe.

```python
import threading

class MyBackend(GlobalStorageBackend):
    def __init__(self):
        self._lock = threading.Lock()
    
    def get(self, name: str, *subscripts: str) -> str | None:
        with self._lock:
            return self._sdk.get(name, subscripts)
```

### Lazy Initialization

**Requirement**: Backends SHOULD defer connection/initialization until first operation.

**Rationale**: Avoid import-time errors, allow non-database code to run without backend configuration.

**Implementation**:
```python
def _ensure_initialized(self):
    if not self._initialized:
        with self._lock:
            if not self._initialized:  # Double-check locking
                self._initialize_backend()
                self._initialized = True

def get(self, name: str, *subscripts: str) -> str | None:
    self._ensure_initialized()
    # ... operation
```

## Semantic Guarantees

### Collation Order

**Guarantee**: Backends MUST implement MUMPS standard collation:
1. Numeric subscripts in ascending order
2. String subscripts in ASCII order
3. Numeric subscripts < string subscripts

**Test**:
```python
backend.set("^Test", "1", value="numeric one")
backend.set("^Test", "2", value="numeric two")
backend.set("^Test", "10", value="numeric ten")
backend.set("^Test", "A", value="string A")

assert backend.order("^Test", "") == "1"
assert backend.order("^Test", "1") == "2"
assert backend.order("^Test", "2") == "10"
assert backend.order("^Test", "10") == "A"
```

### Naked Reference Tracking

**Guarantee**: Backends MUST update naked reference indicator on global operations.

**Note**: For initial implementation, naked reference tracking is handled by m2py codegen, not backend. Future optimization may move tracking to backend.

### $DATA Semantics

**Guarantee**: Backends MUST return correct $DATA codes:
- `0`: Undefined, no descendants
- `1`: Defined, no descendants
- `10`: Undefined, has descendants  
- `11`: Defined, has descendants

**Test**:
```python
backend.set("^Test", "parent", "child", value="value")
assert backend.data("^Test") == 10
assert backend.data("^Test", "parent") == 10
assert backend.data("^Test", "parent", "child") == 1
```

### Transaction Isolation

**Guarantee**: Backends SHOULD provide READ COMMITTED isolation or stronger.

**Note**: MUMPS standard does not specify isolation level. READ COMMITTED is minimum for correctness.

## Backend Comparison

| Feature | InMemory | YottaDB | IRIS | Notes |
|---------|----------|---------|------|-------|
| Persistence | ❌ | ✅ | ✅ | InMemory data lost on exit |
| Transactions | ✅ | ✅ (tp callback) | ✅ (explicit) | YDB requires adapter |
| Locks | ✅ | ✅ (process-scoped) | ✅ (process-scoped) | All support LOCK semantics |
| Thread-Safe | ✅ | ⚠️ (with lock) | ⚠️ (with lock) | Backends add threading.Lock |
| Extended Refs | ❌ | ❌ | ✅ (`^|"NS"|Global`) | IRIS-specific feature |
| Performance | Fastest | Fast (local) | Slower (network) | See benchmarks |

---

## Validation

### Test Suite

All backends MUST pass the unified test suite in `tests/runtime/backend/`:
- `test_basic_operations.py`: get, set, kill, data
- `test_order_query.py`: order, query traversal
- `test_locks.py`: lock, unlock,unlock_all
- `test_transactions.py`: start, commit, rollback
- `test_subscript_canonicalization.py`: Numeric vs string collation
- `test_cross_validation.py`: m2py output matches native MUMPS

### Acceptance Criteria

Backend is considered **production-ready** if:
1. ✅ All protocol methods implemented
2. ✅ All test suite tests pass
3. ✅ Cross-validation with YottaDB succeeds
4. ✅ Thread-safety verified (concurrent test execution)
5. ✅ Performance meets goals (<10ms for typical operations)
6. ✅ Exception translation complete
7. ✅ Documentation complete (quickstart, troubleshooting)

---

**Protocol Status**: ✅ STABLE (no changes required)  
**Backend Status**: 
- InMemory: ✅ Complete
- YottaDB: 🚧 Pending implementation
- IRIS: 🚧 Pending implementation
