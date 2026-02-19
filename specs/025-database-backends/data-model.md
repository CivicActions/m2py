# Data Model: Backend Architecture & Exception Hierarchy

**Date**: 2025-02-19  
**Feature**: 025-database-backends  
**Phase**: 1 (Design & Contracts)

## Overview

This document defines the class architecture for YottaDBGlobalStorage and IRISGlobalStorage backend implementations, the exception hierarchy for backend error translation, and the connection lifecycle models. All backends implement the existing `GlobalStorageBackend` protocol defined in `src/m2py/runtime/globals.py`.

## Backend Class Architecture

### Class Hierarchy

```
GlobalStorageBackend (Protocol)           # Defined in globals.py
├── InMemoryGlobalStorage                 # Existing implementation
├── YottaDBGlobalStorage                  # NEW: YottaDB backend
└── IRISGlobalStorage                     # NEW: IRIS backend
```

### GlobalStorageBackend Protocol (Existing)

**Location**: `src/m2py/runtime/globals.py`

**Interface** (25+ methods):
```python
from typing import Protocol, Any

class GlobalStorageBackend(Protocol):
    """Protocol for MUMPS global storage backends."""
    
    # Basic operations
    def get(self, name: str, *subscripts: str) -> str | None: ...
    def set(self, name: str, *subscripts: str, value: str) -> None: ...
    def kill(self, name: str, *subscripts: str) -> None: ...
    def kill_all(self, name: str) -> None: ...
    def kill_node(self, name: str, *subscripts: str) -> None: ...
    
    # Metadata
    def data(self, name: str, *subscripts: str) -> int: ...
    
    # Traversal
    def order(self, name: str, *subscripts: str) -> str | None: ...
    def query(self, name: str, *subscripts: str) -> tuple[str, tuple[str, ...]] | None: ...
    
    # Bulk operations
    def get_tree(self, name: str, *subscripts: str) -> dict[tuple[str, ...], str]: ...
    def merge_tree(self, target_name: str, target_subscripts: tuple[str, ...], 
                   source_tree: dict[tuple[str, ...], str]) -> None: ...
    
    # Atomic operations
    def incr(self, name: str, *subscripts: str, delta: int | float = 1) -> int | float: ...
    
    # Lock operations
    def lock(self, name: str, *subscripts: str, timeout: float | None = None) -> bool: ...
    def unlock(self, name: str, *subscripts: str) -> None: ...
    def unlock_all(self) -> None: ...
    
    # Transaction operations
    def transaction_start(self) -> None: ...
    def transaction_commit(self) -> None: ...
    def transaction_rollback(self) -> None: ...
    
    # SSVN (Structured System Variable Node) operations
    def ssvn_get(self, name: str, *subscripts: str) -> str | None: ...
    def ssvn_set(self, name: str, *subscripts: str, value: str) -> None: ...
    def ssvn_data(self, name: str, *subscripts: str) -> int: ...
    def ssvn_order(self, name: str, *subscripts: str) -> str | None: ...
    def ssvn_query(self, name: str, *subscripts: str) -> tuple[str, tuple[str, ...]] | None: ...
```

**No changes required** - existing protocol is sufficient for both backends.

### YottaDBGlobalStorage Class

**Location**: `src/m2py/runtime/yottadb_backend.py`

**Class Definition**:
```python
import os
import threading
from typing import Any
from .globals import GlobalStorageBackend
from .backend_exceptions import BackendConnectionError, BackendTimeoutError
from .subscript_canonicalizer import SubscriptCanonicalizer

class YottaDBGlobalStorage(GlobalStorageBackend):
    """YottaDB backend implementation using yottadb Python wrapper."""
    
    def __init__(self):
        """Initialize YottaDB backend with lazy connection."""
        self._initialized = False
        self._lock = threading.Lock()  # Thread safety for YDB API
        self._canonicalizer = SubscriptCanonicalizer()
        self._locks_held: set[tuple[str, tuple[str, ...]]] = set()  # Track locks for unlock()
        self._transaction_depth = 0  # Track nested transactions
        self._transaction_callback = None  # TP callback context
    
    def _ensure_initialized(self) -> None:
        """Lazy initialization of YottaDB connection."""
        if not self._initialized:
            with self._lock:
                if not self._initialized:  # Double-check locking
                    try:
                        import yottadb
                        self._ydb = yottadb
                    except ImportError as e:
                        raise BackendConnectionError(
                            "YottaDB Python wrapper not installed. "
                            "Install with: uv add yottadb"
                        ) from e
                    
                    # Validate environment
                    if "ydb_dist" not in os.environ:
                        raise BackendConnectionError(
                            "YottaDB not configured: $ydb_dist environment variable not set. "
                            "Run: source /opt/yottadb/current/ydb_env_set"
                        )
                    
                    self._initialized = True
    
    def get(self, name: str, *subscripts: str) -> str | None:
        """Get value of global node."""
        self._ensure_initialized()
        canonical_subs = [self._canonicalizer.canonicalize(s) for s in subscripts]
        
        with self._lock:
            try:
                key = self._ydb.Key(name)
                for sub in canonical_subs:
                    key = key[sub.encode('utf-8')]
                value_bytes = key.get()
                return value_bytes.decode('utf-8')
            except self._ydb.YDBError as e:
                if e.code() == 150373850:  # YDB_ERR_GVUNDEF
                    return None
                raise BackendConnectionError(f"YottaDB get() error: {e}") from e
    
    def set(self, name: str, *subscripts: str, value: str) -> None:
        """Set value of global node."""
        self._ensure_initialized()
        canonical_subs = [self._canonicalizer.canonicalize(s) for s in subscripts]
        
        with self._lock:
            try:
                key = self._ydb.Key(name)
                for sub in canonical_subs:
                    key = key[sub.encode('utf-8')]
                key.value = value.encode('utf-8')
            except self._ydb.YDBError as e:
                raise BackendConnectionError(f"YottaDB set() error: {e}") from e
    
    # ... (other methods follow same pattern)
    
    def lock(self, name: str, *subscripts: str, timeout: float | None = None) -> bool:
        """Lock global node with optional timeout."""
        self._ensure_initialized()
        canonical_subs = tuple(self._canonicalizer.canonicalize(s) for s in subscripts)
        lock_key = (name, canonical_subs)
        
        with self._lock:
            try:
                key = self._ydb.Key(name)
                for sub in canonical_subs:
                    key = key[sub.encode('utf-8')]
                
                # YDB lock() replaces all locks, so pass existing + new
                all_locks = list(self._locks_held) + [lock_key]
                self._ydb.lock([(key, timeout)] + [(self._make_key(n, s), None) for n, s in self._locks_held])
                
                self._locks_held.add(lock_key)
                return True
            except self._ydb.YDBError as e:
                if e.code() == self._ydb.YDB_ERR_TIME:
                    return False  # Timeout
                raise BackendTimeoutError(f"YottaDB lock() error: {e}") from e
    
    def transaction_start(self) -> None:
        """Start transaction (YDB uses tp callback model)."""
        self._ensure_initialized()
        self._transaction_depth += 1
        # Actual YDB tp() call deferred until commit() to collect all operations
    
    def transaction_commit(self) -> None:
        """Commit transaction."""
        if self._transaction_depth == 0:
            raise RuntimeError("No transaction to commit")
        
        self._transaction_depth -= 1
        if self._transaction_depth == 0:
            # Execute collected operations in YDB tp() callback
            def callback():
                # Replay operations collected during transaction
                # (Implementation detail: requires operation buffering)
                return self._ydb.YDB_OK
            
            with self._lock:
                try:
                    self._ydb.tp(callback)
                except self._ydb.YDBError as e:
                    raise BackendConnectionError(f"YottaDB transaction commit error: {e}") from e
```

**Key Design Decisions**:
- **Thread Safety**: Use `threading.Lock` around all YDB API calls (YDB has limited thread safety)
- **Lazy Init**: Defer `import yottadb` until first use to avoid import-time errors
- **Lock Tracking**: Maintain `_locks_held` set to support selective unlock (YDB only supports unlock-all)
- **Transaction Adapter**: Buffer operations during transaction, execute in `tp(callback)` on commit
- **Subscript Canonicalization**: Use existing `SubscriptCanonicalizer` to maintain MUMPS collation

### IRISGlobalStorage Class

**Location**: `src/m2py/runtime/iris_backend.py`

**Class Definition**:
```python
import os
import threading
from typing import Any
from .globals import GlobalStorageBackend
from .backend_exceptions import BackendConnectionError, BackendPermissionError, BackendTimeoutError
from .subscript_canonicalizer import SubscriptCanonicalizer

class IRISGlobalStorage(GlobalStorageBackend):
    """IRIS backend implementation using intersystems-irispython SDK."""
    
    def __init__(self):
        """Initialize IRIS backend with lazy connection."""
        self._connection = None
        self._lock = threading.Lock()  # Thread safety for connection
        self._canonicalizer = SubscriptCanonicalizer()
        self._transaction_depth = 0  # Track nested transactions
    
    def _ensure_connected(self) -> None:
        """Lazy initialization of IRIS connection."""
        if self._connection is None:
            with self._lock:
                if self._connection is None:  # Double-check locking
                    try:
                        import iris
                        self._iris = iris
                    except ImportError as e:
                        raise BackendConnectionError(
                            "IRIS Python SDK not installed. "
                            "Install with: uv add intersystems-irispython --optional backend"
                        ) from e
                    
                    # Read connection parameters from environment
                    host = os.environ.get("M2PY_IRIS_HOST", "localhost")
                    port = int(os.environ.get("M2PY_IRIS_PORT", "1972"))
                    namespace = os.environ.get("M2PY_IRIS_NAMESPACE", "USER")
                    username = os.environ.get("M2PY_IRIS_USERNAME", "_SYSTEM")
                    password = os.environ.get("M2PY_IRIS_PASSWORD")
                    
                    if password is None:
                        raise BackendConnectionError(
                            "IRIS password not configured: M2PY_IRIS_PASSWORD environment variable required"
                        )
                    
                    try:
                        self._connection = self._iris.connect(
                            hostname=host,
                            port=port,
                            namespace=namespace,
                            username=username,
                            password=password
                        )
                    except self._iris.IRISException as e:
                        raise BackendConnectionError(f"IRIS connection failed: {e}") from e
    
    def get(self, name: str, *subscripts: str) -> str | None:
        """Get value of global node."""
        self._ensure_connected()
        canonical_subs = [self._canonicalizer.canonicalize(s) for s in subscripts]
        
        # Handle extended references: ^|"NAMESPACE"|Global
        actual_name, namespace = self._parse_extended_ref(name)
        
        with self._lock:
            try:
                if namespace:
                    # Switch namespace temporarily
                    old_ns = self._connection.namespace
                    self._connection.namespace = namespace
                    try:
                        gn = self._connection.get_global_node(actual_name, canonical_subs)
                        return gn.get()
                    finally:
                        self._connection.namespace = old_ns
                else:
                    gn = self._connection.get_global_node(actual_name, canonical_subs)
                    return gn.get()
            except self._iris.IRISException as e:
                raise BackendConnectionError(f"IRIS get() error: {e}") from e
    
    def set(self, name: str, *subscripts: str, value: str) -> None:
        """Set value of global node."""
        self._ensure_connected()
        canonical_subs = [self._canonicalizer.canonicalize(s) for s in subscripts]
        actual_name, namespace = self._parse_extended_ref(name)
        
        with self._lock:
            try:
                if namespace:
                    old_ns = self._connection.namespace
                    self._connection.namespace = namespace
                    try:
                        gn = self._connection.get_global_node(actual_name, canonical_subs)
                        gn.set(value)
                    finally:
                        self._connection.namespace = old_ns
                else:
                    gn = self._connection.get_global_node(actual_name, canonical_subs)
                    gn.set(value)
            except self._iris.IRISException as e:
                raise BackendConnectionError(f"IRIS set() error: {e}") from e
    
    # ... (other methods follow same pattern)
    
    def lock(self, name: str, *subscripts: str, timeout: float | None = None) -> bool:
        """Lock global node with optional timeout."""
        self._ensure_connected()
        canonical_subs = [self._canonicalizer.canonicalize(s) for s in subscripts]
        
        with self._lock:
            try:
                timeout_int = int(timeout) if timeout is not None else -1  # IRIS uses -1 for infinite
                self._connection.lock(name, canonical_subs, timeout_int)
                return True
            except self._iris.IRISException as e:
                if "LOCK timeout" in str(e):
                    return False
                raise BackendTimeoutError(f"IRIS lock() error: {e}") from e
    
    def transaction_start(self) -> None:
        """Start transaction."""
        self._ensure_connected()
        
        with self._lock:
            if self._transaction_depth == 0:
                try:
                    self._connection.begin()
                except self._iris.IRISException as e:
                    raise BackendConnectionError(f"IRIS transaction start error: {e}") from e
            self._transaction_depth += 1
    
    def transaction_commit(self) -> None:
        """Commit transaction."""
        if self._transaction_depth == 0:
            raise RuntimeError("No transaction to commit")
        
        self._transaction_depth -= 1
        if self._transaction_depth == 0:
            with self._lock:
                try:
                    self._connection.commit()
                except self._iris.IRISException as e:
                    raise BackendConnectionError(f"IRIS transaction commit error: {e}") from e
    
    def transaction_rollback(self) -> None:
        """Rollback transaction."""
        if self._transaction_depth == 0:
            raise RuntimeError("No transaction to rollback")
        
        self._transaction_depth -= 1
        if self._transaction_depth == 0:
            with self._lock:
                try:
                    self._connection.rollback()
                except self._iris.IRISException as e:
                    raise BackendConnectionError(f"IRIS transaction rollback error: {e}") from e
    
    def _parse_extended_ref(self, name: str) -> tuple[str, str | None]:
        """Parse extended reference syntax: ^|"NAMESPACE"|Global → (^Global, NAMESPACE)."""
        if name.startswith('^|"') and '"|' in name:
            # Extended reference: ^|"NAMESPACE"|Global
            parts = name.split('"|', 1)
            namespace = parts[0][3:]  # Remove ^|"
            global_name = '^' + parts[1]  # Add back ^
            return global_name, namespace
        return name, None
```

**Key Design Decisions**:
- **Connection Management**: Single persistent connection per backend instance
- **Thread Safety**: Use `threading.Lock` around connection operations
- **Extended References**: Parse `^|"NAMESPACE"|Global` syntax and switch namespaces dynamically
- **Transaction Nesting**: Track depth, only commit/rollback outermost transaction
- **Error Translation**: Map IRIS exceptions to m2py backend exceptions

## Exception Hierarchy

### New Exception Classes

**Location**: `src/m2py/runtime/backend_exceptions.py`

```python
"""Backend-specific exceptions for database storage backends."""

from .exceptions import MRuntimeError

class BackendError(MRuntimeError):
    """Base class for backend operation errors."""
    pass

class BackendConnectionError(BackendError):
    """Backend connection failure (network, authentication, missing SDK)."""
    pass

class BackendPermissionError(BackendError):
    """Backend permission denied (insufficient privileges)."""
    pass

class BackendTimeoutError(BackendError):
    """Backend operation timeout (lock acquisition, query execution)."""
    pass

class BackendConfigurationError(BackendError):
    """Backend configuration error (missing environment variables, invalid parameters)."""
    pass
```

### Exception Translation Matrix

| SDK Error | Translated Exception | Trigger Condition |
|-----------|---------------------|------------------|
| **YottaDB** |
| `yottadb.YDBError(YDB_ERR_GVUNDEF)` | `None` return (not exception) | Global undefined |
| `yottadb.YDBError(YDB_ERR_TIME)` | `BackendTimeoutError` | Lock timeout |
| `yottadb.YDBError(YDB_ERR_INVSTRLEN)` | `ValueError` | Invalid subscript length |
| `yottadb.YDBError(YDB_ERR_UNIMPLOP)` | `NotImplementedError` | Unsupported operation |
| `ImportError` (yottadb) | `BackendConnectionError` | SDK not installed |
| Missing `$ydb_dist` | `BackendConnectionError` | YDB not configured |
| **IRIS** |
| `iris.IRISException` (connection) | `BackendConnectionError` | Network/auth failure |
| `iris.IRISException` (permission) | `BackendPermissionError` | Insufficient privileges |
| `iris.IRISException` (timeout) | `BackendTimeoutError` | Lock timeout |
| `ImportError` (iris) | `BackendConnectionError` | SDK not installed |
| Missing `M2PY_IRIS_PASSWORD` | `BackendConfigurationError` | Required env var missing |

### Exception Chaining

All backend exceptions preserve original SDK exception via `from` clause:

```python
try:
    key = yottadb.Key("^Global")["sub1"]
    value = key.get()
except yottadb.YDBError as e:
    raise BackendConnectionError(f"YottaDB error: {e}") from e
    # Original exception accessible via __cause__
```

**Benefits**:
- Debugging: Full SDK error details available in traceback
- Monitoring: Distinguish m2py errors from SDK errors
- Testing: Assert on exception type without losing SDK context

## Connection Lifecycle Models

### Lifecycle States

```
[NOT_INITIALIZED] → [INITIALIZING] → [CONNECTED] → [ERROR]
                                  ↓
                            [DISCONNECTED]
```

**State Transitions**:
- `NOT_INITIALIZED`: Backend created but not yet used
- `INITIALIZING`: First operation triggered, importing SDK and establishing connection
- `CONNECTED`: Connection established, operations succeed
- `DISCONNECTED`: Connection closed explicitly (future feature, not in initial implementation)
- `ERROR`: Connection failed or lost, operations raise BackendConnectionError

### YottaDB Connection Lifecycle

**Process-Bound Model**:
```
Backend.__init__()  → NOT_INITIALIZED
   ↓
First get/set()     → INITIALIZING (import yottadb, validate $ydb_dist)
   ↓
YDB API success     → CONNECTED (implicit, process-bound)
   ↓
Process exit        → DISCONNECTED (automatic, YDB cleanup)
```

**Key Characteristics**:
- No explicit connect/disconnect API (process lifecycle manages connection)
- `_ensure_initialized()` called on every operation
- Thread-safe via `threading.Lock`
- Connection errors surface as `BackendConnectionError` on first use

### IRIS Connection Lifecycle

**Network Connection Model**:
```
Backend.__init__()  → NOT_INITIALIZED
   ↓
First get/set()     → INITIALIZING (import iris, read env vars)
   ↓
iris.connect()      → CONNECTED (network connection established)
   ↓
iris.disconnect()   → DISCONNECTED (explicit, future feature)
```

**Key Characteristics**:
- Network connection persists across operations
- `_ensure_connected()` called on every operation (lightweight check)
- Thread-safe via `threading.Lock`
- Connection parameters from environment variables

### Lock State Tracking

**YottaDB Lock Model**:
- `yottadb.lock([list])` replaces ALL locks with new list
- Backend maintains `_locks_held` set to support incremental lock/unlock
- `unlock(name, *subs)` reconstructs lock list without specified lock

**IRIS Lock Model**:
- `iris.IRIS.lock()` adds lock (incremental)
- `iris.IRIS.unlock()` removes specific lock
- No lock state tracking needed (IRIS handles it)

### Transaction State Tracking

**YottaDB Transaction Model (Callback-Based)**:
```
transaction_start()  → _transaction_depth += 1
   ↓
get/set operations   → Buffer in transaction context
   ↓
transaction_commit() → _transaction_depth -= 1
                       if depth == 0: yottadb.tp(replay_operations)
```

**IRIS Transaction Model (Explicit)**:
```
transaction_start()  → _transaction_depth += 1
                       if depth == 1: iris.IRIS.begin()
   ↓
get/set operations   → Executed immediately (IRIS buffers internally)
   ↓
transaction_commit() → _transaction_depth -= 1
                       if depth == 0: iris.IRIS.commit()
```

**Nested Transaction Handling**:
- Both backends track transaction depth
- Only outermost transaction commits/rollbacks to database
- Inner "transactions" are no-ops (MUMPS semantics: nested TSTART increments $TLEVEL)

## Backend Factory Integration

### Updated get_global_storage() Factory

**Location**: `src/m2py/runtime/__init__.py`

**Current Implementation**:
```python
def get_global_storage(backend: str | None = None) -> GlobalStorageBackend:
    """Get global storage backend instance."""
    if backend is None:
        backend = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")
    
    backend = backend.lower()
    
    if backend == "inmemory":
        from .globals import InMemoryGlobalStorage
        return InMemoryGlobalStorage()
    elif backend == "yottadb":
        try:
            from .yottadb_backend import YottaDBGlobalStorage
            return YottaDBGlobalStorage()
        except ImportError:
            raise ValueError("YottaDB backend not available (SDK not installed)")
    elif backend == "iris":
        try:
            from .iris_backend import IRISGlobalStorage
            return IRISGlobalStorage()
        except ImportError:
            raise ValueError("IRIS backend not available (SDK not installed)")
    else:
        raise ValueError(f"Unknown backend: {backend}")
```

**Required Changes**:
- Add `elif backend == "yottadb"` case
- Add `elif backend == "iris"` case
- Handle `ImportError` gracefully (SDKs may not be installed)

## Configuration Model

### Environment Variables

**Backend Selection**:
- `M2PY_GLOBAL_BACKEND`: Backend type (`inmemory` | `yottadb` | `iris`, default: `inmemory`)

**YottaDB Configuration** (required when using YottaDB backend):
- `$ydb_dist`: YottaDB installation directory (e.g., `/opt/yottadb/current`)
- `$ydb_gbldir`: Global directory path (e.g., `/data/mumps.gld`, default: `mumps.gld`)
- `$ydb_routines`: Routine search path (optional)

**IRIS Configuration** (required when using IRIS backend):
- `M2PY_IRIS_HOST`: IRIS server hostname (default: `localhost`)
- `M2PY_IRIS_PORT`: IRIS superserver port (default: `1972`)
- `M2PY_IRIS_NAMESPACE`: IRIS namespace (default: `USER`)
- `M2PY_IRIS_USERNAME`: Authentication username (default: `_SYSTEM`)
- `M2PY_IRIS_PASSWORD`: Authentication password (REQUIRED, no default)

### Configuration Validation

**Validation Rules**:
1. YottaDB backend requires `$ydb_dist` environment variable → `BackendConnectionError` if missing
2. IRIS backend requires `M2PY_IRIS_PASSWORD` environment variable → `BackendConfigurationError` if missing
3. IRIS port must be valid integer → `ValueError` if invalid
4. Unknown backend type → `ValueError` from factory

**Validation Timing**:
- Lazy validation on first backend operation (not at import time)
- Early failure preferred (fail fast on first `get()` rather than silently continuing)

## Testing Strategy

### Test Organization

**Directory Structure**:
```
tests/runtime/backend/
├── conftest.py                      # Backend fixtures
├── test_basic_operations.py         # get, set, kill, data
├── test_order_query.py              # order, query traversal
├── test_locks.py                    # lock, unlock, unlock_all
├── test_transactions.py             # transaction_start/commit/rollback
├── test_connection_lifecycle.py     # Lazy init, error handling
├── test_exception_translation.py    # SDK exception → m2py exception
└── test_cross_validation.py         # m2py ↔ native MUMPS equivalence
```

### Backend Parameterization (conftest.py)

```python
import pytest
import os

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "backend_inmemory: InMemory backend tests")
    config.addinivalue_line("markers", "backend_yottadb: YottaDB backend tests")
    config.addinivalue_line("markers", "backend_iris: IRIS backend tests")

@pytest.fixture(params=["inmemory", "yottadb", "iris"])
def backend(request):
    """Parameterized backend fixture."""
    backend_type = request.param
    
    # Skip if backend unavailable
    if backend_type == "yottadb" and not os.environ.get("ydb_dist"):
        pytest.skip("YottaDB not configured (requires $ydb_dist)")
    
    if backend_type == "iris" and not os.environ.get("M2PY_IRIS_PASSWORD"):
        pytest.skip("IRIS not configured (requires M2PY_IRIS_PASSWORD)")
    
    from m2py.runtime import get_global_storage
    
    backend_instance = get_global_storage(backend_type)
    
    yield backend_instance
    
    # Cleanup: clear all globals
    backend_instance.kill_all("^Test")

@pytest.fixture
def inmemory_backend():
    """InMemory backend fixture (no configuration needed)."""
    from m2py.runtime.globals import InMemoryGlobalStorage
    return InMemoryGlobalStorage()

@pytest.fixture
def yottadb_backend():
    """YottaDB backend fixture (requires Docker container)."""
    if not os.environ.get("ydb_dist"):
        pytest.skip("YottaDB not configured")
    
    from m2py.runtime.yottadb_backend import YottaDBGlobalStorage
    return YottaDBGlobalStorage()

@pytest.fixture
def iris_backend():
    """IRIS backend fixture (requires Docker container)."""
    if not os.environ.get("M2PY_IRIS_PASSWORD"):
        pytest.skip("IRIS not configured")
    
    from m2py.runtime.iris_backend import IRISGlobalStorage
    return IRISGlobalStorage()
```

### Test Execution

**Run all backends**:
```bash
uv run pytest tests/runtime/backend/
```

**Run specific backend**:
```bash
# InMemory only
uv run pytest tests/runtime/backend/ -m backend_inmemory

# YottaDB only (in Docker)
docker run --rm -v $(pwd):/workspace m2py-yottadb \
  uv run pytest tests/runtime/backend/ -m backend_yottadb

# IRIS only
M2PY_IRIS_PASSWORD=SYS uv run pytest tests/runtime/backend/ -m backend_iris
```

## Design Decisions

### Decision: Thread Safety via Locks

**Rationale**: YottaDB Python wrapper has limited thread safety guarantees; IRIS connection is not thread-safe by default.

**Implementation**: Use `threading.Lock` around all SDK API calls.

**Alternatives Considered**:
- Thread-local storage (TLS) for connections → Rejected: MUMPS semantics expect process-wide globals
- No thread safety → Rejected: m2py-generated code may spawn threads (e.g., background jobs)

### Decision: Lazy Connection Initialization

**Rationale**: Defer connection overhead until first global access. Matches InMemoryGlobalStorage behavior (no setup required).

**Implementation**: `_ensure_initialized()` / `_ensure_connected()` called on every operation.

**Alternatives Considered**:
- Eager connection on import → Rejected: Breaks non-database code (import-time errors)
- Explicit connect/disconnect API → Rejected: Adds complexity, no use case yet

### Decision: Environment-Based Configuration

**Rationale**: 12-factor app principle (configuration via environment), easy CI/CD integration.

**Implementation**: Read env vars in `_ensure_connected()`, fail if required vars missing.

**Alternatives Considered**:
- Configuration file (YAML/TOML) → Rejected: No config files in m2py currently
- Programmatic API (`backend.configure(...)`) → Rejected: Breaks factory pattern

### Decision: Exception Translation Layer

**Rationale**: Consistent error handling across backends, preserve SDK error details for debugging.

**Implementation**: Translate SDK exceptions to backend_exceptions types, use `from` clause for chaining.

**Alternatives Considered**:
- Expose SDK exceptions directly → Rejected: Leaks implementation details to m2py user code
- Generic `BackendError` for all errors → Rejected: Loses specificity (lock timeout vs connection failure)

---

**Design Status**: ✅ COMPLETE  
**Approval**: Ready for Phase 1 continuation (quickstart.md, contracts/)
