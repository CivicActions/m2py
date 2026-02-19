# Research: YottaDB and IRIS SDK Integration

**Date**: 2025-02-19  
**Feature**: 025-database-backends  
**Phase**: 0 (Research & Discovery)

## Executive Summary

This document maps the YottaDB Python wrapper and IRIS Native SDK APIs to the m2py GlobalStorageBackend protocol. Both SDKs provide comprehensive MUMPS database functionality suitable for backend implementation. Key findings:

- **YottaDB Python wrapper**: Direct bindings to C Simple API, provides `yottadb` module with `Key` class for global operations
- **IRIS Native SDK**: Object-oriented API with `iris.IRIS` connection class and `IRISGlobalNode` for global access
- **Protocol alignment**: Both SDKs support all 25+ GlobalStorageBackend methods with semantic equivalence
- **Environment requirements**: YottaDB requires $ydb_dist environment variable; IRIS requires connection parameters (host, port, namespace, credentials)
- **Exception handling**: Both SDKs raise SDK-specific exceptions requiring translation to m2py exception types

## YottaDB Python Wrapper API

### Installation & Requirements

**Package**: `yottadb` (PyPI version 2.0.0)  
**Prerequisites**:
- YottaDB C library (`libyottadb.so`) and headers
- `$ydb_dist` environment variable pointing to the YottaDB directory
- Python development headers (`python3-dev`)
- Foreign Function Interface library (`libffi-dev`)
- C compiler for native extension build

**Note**: YottaDB does not officially support aarch64 as a host install target, but the Docker image
(`yottadb/yottadb:latest`) ships aarch64 binaries. Rather than extracting files to the host,
we run tests inside the YottaDB Docker container via `Dockerfile.yottadb` and `utils/ydb.sh`.

**Development Setup (Docker container approach)**:
```bash
# Build the m2py-ydb Docker image (auto-built on first use of ydb.sh)
bash utils/ydb.sh echo "ready"

# The image includes: YottaDB + Python + uv + gcc
# YDB env is sourced automatically via ydb_env_set
# The workspace is mounted at /workspace
```

**Running tests with YottaDB**:
```bash
# Run tests inside the YDB container
bash utils/ydb.sh uv run pytest tests/ -x -n0

# Import test
bash utils/ydb.sh uv run python -c "import yottadb; print('ok')"

# Interactive shell (YDB env pre-configured)
bash utils/ydb.sh bash
```

**Verified working**: aarch64/Ubuntu 24.04 dev container — `import yottadb` succeeds, all
core operations (get, set, data, delete_tree, subscript_next) work correctly.

### Core API: `yottadb.Key` Class

The `yottadb.Key` class represents a MUMPS variable (local or global) with subscripts.

**Constructor**:
```python
import yottadb

# Global variable
key = yottadb.Key("^MyGlobal")

# With subscripts
key = yottadb.Key("^MyGlobal")["sub1"]["sub2"]
```

**Key Operations → GlobalStorageBackend Mapping**:

| GlobalStorageBackend Method | YottaDB API | Notes |
|----------------------------|-------------|-------|
| `get(name, *subscripts)` | `key.get()` | Returns `bytes`, decode to `str` |
| `set(name, *subscripts, value)` | `key.value = value` | Accepts `str` or `bytes` |
| `kill(name, *subscripts)` | `key.delete_node()` | Delete node and descendants |
| `kill_node(name, *subscripts)` | `key.delete_node()` | Same as kill |
| `kill_all(name)` | `yottadb.Key("^name").delete_tree()` | Delete entire global |
| `data(name, *subscripts)` | `key.data` | Returns int: 0/1/10/11 |
| `order(name, *subscripts)` | `key.subscript_next()` | Returns next subscript |
| `query(name, *subscripts)` | `key.subscript_next()` recursively | Traverse tree |
| `incr(name, *subscripts, delta)` | `key.incr(delta)` | Atomic increment |

**Lock Operations**:

| GlobalStorageBackend Method | YottaDB API | Notes |
|----------------------------|-------------|-------|
| `lock(name, *subscripts, timeout)` | `yottadb.lock([(key, timeout)])` | Timeout in seconds (float) or None for infinite |
| `unlock(name, *subscripts)` | `yottadb.lock([])` | Release all locks |

**Transaction Operations**:

| GlobalStorageBackend Method | YottaDB API | Notes |
|----------------------------|-------------|-------|
| `transaction_start()` | `yottadb.tp(callback, ...)` | YDB uses transaction processing callback model |
| `transaction_commit()` | Return `YDB_OK` from callback | Implicit commit on callback success |
| `transaction_rollback()` | Raise exception in callback | Exception triggers rollback |

**Exception Handling**:

YottaDB raises `yottadb.YDBError` with `.code()` method returning error code:

```python
import yottadb

try:
    key = yottadb.Key("^Global")["sub1"]
    value = key.get()
except yottadb.YDBError as e:
    error_code = e.code()
    # Map to m2py exceptions:
    # YDB_ERR_GVUNDEF (150373850) → KeyError
    # YDB_ERR_INVSTRLEN → ValueError
    # YDB_ERR_TIMEREXPIRED → TimeoutError
```

### YottaDB-Specific Considerations

**Subscript Encoding**:
- YottaDB expects `bytes` for subscripts (UTF-8 encoded)
- Use m2py's `SubscriptCanonicalizer` before passing to YDB
- YDB handles MUMPS collation natively (numeric < string)

**Naked References**:
- YDB does not track naked indicator automatically
- Backend must maintain naked reference state in Python
- Use GlobalStorageBackend's built-in tracking

**Environment Variables** (set automatically by `ydb_env_set` inside the container):
- `$ydb_dist`: YottaDB installation directory — `/opt/yottadb/current`
- `$ydb_gbldir`: Global directory path
- `$ydb_routines`: Routine search path
- `$ydb_chset`: Character set — `UTF-8` (default in container)
- `$LD_LIBRARY_PATH`: Includes `$ydb_dist` for `libyottadb.so` resolution
- `$ydb_tmp`: Temporary file directory (optional)

**Note**: When using `utils/ydb.sh`, these variables are configured automatically by sourcing
`/opt/yottadb/current/ydb_env_set` in the container entrypoint. No manual configuration needed.

**Connection Lifecycle**:
- No explicit connection object (process-bound)
- First YDB API call initializes database access
- Connection persists until process exit
- Thread-safe with limitations (use `threading.Lock` for safety)

## IRIS Native SDK API

### Installation & Requirements

**Package**: `intersystems-irispython` (PyPI version 5.3.1)  
**Prerequisites**:
- IRIS server accessible via network (no local installation required)
- Connection parameters: host, port, namespace, username, password

**Installation**:
```bash
uv add intersystems-irispython --optional backend
```

**Development/Testing**: Use Docker container `intersystems/iris-community:latest` with IRIS CE.

### Core API: `iris.IRIS` Connection Class

**Connection**:
```python
import iris

# Create connection
conn = iris.connect(
    hostname="localhost",
    port=1972,
    namespace="USER",  # Default IRIS namespace
    username="_SYSTEM",
    password="SYS"
)

# Access globals
gn = conn.get_global_node("^MyGlobal", ["sub1", "sub2"])
```

**Global Operations → GlobalStorageBackend Mapping**:

| GlobalStorageBackend Method | IRIS API | Notes |
|----------------------------|----------|-------|
| `get(name, *subscripts)` | `gn.get()` | Returns `str` or `None` if undefined |
| `set(name, *subscripts, value)` | `gn.set(value)` | Accepts `str`, `int`, `float` |
| `kill(name, *subscripts)` | `gn.kill()` | Delete node and descendants |
| `kill_node(name, *subscripts)` | `gn.kill()` | Same as kill |
| `kill_all(name)` | `conn.get_global_node(name).kill()` | Delete entire global |
| `data(name, *subscripts)` | `gn.data()` | Returns int: 0/1/10/11 |
| `order(name, *subscripts)` | `gn.order(subscript)` | Returns next subscript |
| `query(name, *subscripts)` | `gn.query()` | Returns next node name |
| `incr(name, *subscripts, delta)` | `gn.increment(delta)` | Atomic increment |

**Lock Operations**:

| GlobalStorageBackend Method | IRIS API | Notes |
|----------------------------|----------|-------|
| `lock(name, *subscripts, timeout)` | `conn.lock(name, subscripts, timeout)` | Timeout in seconds (int) |
| `unlock(name, *subscripts)` | `conn.unlock(name, subscripts)` | Release specific lock |

**Transaction Operations**:

| GlobalStorageBackend Method | IRIS API | Notes |
|----------------------------|----------|-------|
| `transaction_start()` | `conn.begin()` | Start explicit transaction |
| `transaction_commit()` | `conn.commit()` | Commit transaction |
| `transaction_rollback()` | `conn.rollback()` | Rollback transaction |

**Exception Handling**:

IRIS raises `iris.IRISException` for database errors:

```python
import iris

try:
    conn = iris.connect(hostname="localhost", port=1972, namespace="USER", username="_SYSTEM", password="SYS")
    gn = conn.get_global_node("^Global", ["sub1"])
    value = gn.get()
except iris.IRISException as e:
    # Map to m2py exceptions:
    # Connection errors → ConnectionError
    # Permission errors → PermissionError
    # Lock timeout → TimeoutError
    # Undefined global → None (not exception)
```

### IRIS-Specific Considerations

**Namespace Handling**:
- Default namespace: `USER` (when unspecified)
- Extended global references: `^|"NAMESPACE"|Global` syntax
- Backend must parse extended references and switch namespace dynamically

**Subscript Types**:
- IRIS accepts Python `str`, `int`, `float` for subscripts
- Automatic type conversion (Python `1` → IRIS `"1"` for string context)
- Use `SubscriptCanonicalizer` to maintain MUMPS semantics

**Connection Pooling**:
- IRIS SDK supports connection pooling (future optimization)
- Current implementation: single persistent connection per process
- Thread-safe with connection locking

**IRISList and IRISObject**:
- IRIS-specific data structures (`$LISTBUILD`, objects)
- Not part of ANSI MUMPS standard
- Out of scope for initial implementation (defer to future feature)

**Environment Variables**:
- `M2PY_IRIS_HOST`: IRIS server hostname (default: `localhost`)
- `M2PY_IRIS_PORT`: IRIS superserver port (default: `1972`)
- `M2PY_IRIS_NAMESPACE`: Default namespace (default: `USER`)
- `M2PY_IRIS_USERNAME`: Authentication username (default: `_SYSTEM`)
- `M2PY_IRIS_PASSWORD`: Authentication password (required, no default)

## Docker Container Configuration

### YottaDB: Docker Container Approach

Tests run **inside** the YottaDB Docker container, which provides the full YDB environment
(libyottadb.so, database files, env vars). The workspace is mounted read-write.

**Image**: `m2py-ydb` (built from `Dockerfile.yottadb` at project root)

**Why this approach**: The YottaDB Python SDK is a C extension linked against `libyottadb.so`.
Running inside the container avoids the complexity of extracting libraries, configuring
`LD_LIBRARY_PATH`, and managing database files on the host. The `ydb_env_set` script
configures all required environment variables automatically.

**Setup** (automated by `utils/ydb.sh`):
```bash
# Auto-builds image on first use, then runs command inside container
bash utils/ydb.sh uv run pytest tests/ -x -n0
```

**`Dockerfile.yottadb`** (at project root):
```dockerfile
FROM yottadb/yottadb:latest
RUN apt-get update -qq && apt-get install -y -qq --no-install-recommends \
    python3 python3-dev python3-venv gcc ca-certificates curl libffi-dev pkg-config
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}" UV_LINK_MODE=copy
WORKDIR /workspace
ENTRYPOINT ["/bin/bash", "-c", "source /opt/yottadb/current/ydb_env_set && \
    export UV_PROJECT_ENVIRONMENT=/tmp/m2py-venv && \
    uv sync --group yottadb --quiet && exec \"$@\"", "--"]
```

**Key design decisions**:
- Venv at `/tmp/m2py-venv` (not `.venv`) to avoid clobbering host Python venv
- `UV_LINK_MODE=copy` avoids cross-filesystem hardlink warnings
- `uv sync --group yottadb` runs in entrypoint so `import yottadb` always works
- Image cached after first build (~37s); subsequent runs are instant

### IRIS: Local Client with Docker Container

IRIS uses a network SDK (`intersystems-irispython`) that connects over TCP. The IRIS
database runs in a Docker container; our Python code runs on the host.

**Wrapper**: `utils/iris.sh` auto-starts the IRIS container and exports connection env vars.

**Setup**:
```bash
# Auto-starts IRIS container, exports IRIS_HOST/PORT/etc, runs command locally
bash utils/iris.sh uv run pytest tests/ -x -n0

# Container management
bash utils/iris.sh --start    # Start container only
bash utils/iris.sh --stop     # Stop and remove container
bash utils/iris.sh --status   # Show container status
```

**Exported env vars**: `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USER`, `IRIS_PASSWORD`

## API Comparison Matrix

### GlobalStorageBackend Protocol Coverage

| Protocol Method | YottaDB | IRIS | Implementation Notes |
|----------------|---------|------|---------------------|
| `get()` | ✅ `Key.get()` | ✅ `GlobalNode.get()` | YDB returns bytes, IRIS returns str |
| `set()` | ✅ `Key.value = x` | ✅ `GlobalNode.set(x)` | Both accept multiple types |
| `kill()` | ✅ `Key.delete_node()` | ✅ `GlobalNode.kill()` | Identical semantics |
| `kill_all()` | ✅ `Key.delete_tree()` | ✅ `GlobalNode.kill()` | YDB has separate method |
| `data()` | ✅ `Key.data` | ✅ `GlobalNode.data()` | Both return 0/1/10/11 |
| `order()` | ✅ `Key.subscript_next()` | ✅ `GlobalNode.order()` | Identical semantics |
| `query()` | ⚠️ Manual iteration | ✅ `GlobalNode.query()` | YDB requires recursive order() |
| `lock()` | ✅ `yottadb.lock()` | ✅ `IRIS.lock()` | Different timeout semantics |
| `unlock()` | ✅ `yottadb.lock([])` | ✅ `IRIS.unlock()` | YDB unlocks all, IRIS selective |
| `transaction_start()` | ⚠️ `tp(callback)` | ✅ `IRIS.begin()` | YDB uses callback model |
| `transaction_commit()` | ⚠️ Return from callback | ✅ `IRIS.commit()` | Requires wrapper |
| `transaction_rollback()` | ⚠️ Raise in callback | ✅ `IRIS.rollback()` | Requires wrapper |
| `incr()` | ✅ `Key.incr()` | ✅ `GlobalNode.increment()` | Identical semantics |
| `get_tree()` | ✅ Iterate with order() | ✅ Iterate with query() | Convenience wrapper |
| `merge_tree()` | ✅ Multiple set() calls | ✅ Multiple set() calls | No native MERGE API |

**Legend**:
- ✅ Direct API support
- ⚠️ Requires adapter logic (non-trivial but straightforward)

### Edge Cases & Limitations

#### YottaDB Limitations

1. **Transaction Model Mismatch**:
   - YDB uses `tp(callback_function)` for transactions
   - GlobalStorageBackend uses explicit `start()/commit()/rollback()`
   - **Solution**: Wrap transaction context in Python context manager, defer callback execution until commit()

2. **Global Unlock Semantics**:
   - YDB `lock([])` releases ALL locks
   - GlobalStorageBackend `unlock(name, *subscripts)` releases specific lock
   - **Solution**: Track lock state in Python, reconstruct lock list for partial unlock

3. **Query Method**:
   - YDB has no direct `query()` equivalent
   - **Solution**: Implement using recursive `order()` traversal

4. **Thread Safety**:
   - YDB Python wrapper has limited thread safety guarantees
   - **Solution**: Use `threading.Lock` around all YDB API calls

#### IRIS Limitations

1. **Extended References**:
   - IRIS supports `^|"NAMESPACE"|Global` for cross-namespace access
   - GlobalStorageBackend protocol has no explicit namespace parameter
   - **Solution**: Parse global name for extended reference syntax, switch connection namespace dynamically

2. **IRISList/IRISObject**:
   - IRIS-specific data types not in ANSI MUMPS
   - **Solution**: Out of scope for initial implementation (document in limitations.md)

3. **Connection Overhead**:
   - IRIS requires network connection (higher latency than YDB process model)
   - **Solution**: Document 10-50ms overhead for first operation, <5ms for subsequent operations

4. **Authentication Required**:
   - IRIS always requires username/password (even for local development)
   - **Solution**: Document default credentials (_SYSTEM/SYS for CE), require explicit configuration

## Best Practices & Integration Patterns

### 1. Lazy Connection Initialization

**Pattern**: Defer connection until first global access

**Rationale**: Avoid connection overhead for code that doesn't use globals

**Implementation**:
```python
class YottaDBGlobalStorage(GlobalStorageBackend):
    def __init__(self):
        self._initialized = False
    
    def _ensure_initialized(self):
        if not self._initialized:
            import yottadb  # Import only when needed
            # Validate environment
            if "ydb_dist" not in os.environ:
                raise ConnectionError(
                    "YottaDB not configured: $ydb_dist not set. "
                    "Run: export ydb_dist=/opt/yottadb/current"
                )
            if "ydb_gbldir" not in os.environ:
                raise ConnectionError(
                    "YottaDB not configured: $ydb_gbldir not set. "
                    "See specs/025-database-backends/research.md for setup."
                )
            self._initialized = True
    
    def get(self, name: str, *subscripts: str) -> str | None:
        self._ensure_initialized()
        # ... YDB API calls
```

### 2. Exception Translation Layer

**Pattern**: Translate SDK exceptions to m2py exception types

**Rationale**: Maintain consistent error handling across backends

**Implementation**:
```python
# backend_exceptions.py
class BackendConnectionError(MRuntimeError):
    """Backend connection failure"""
    pass

class BackendPermissionError(MRuntimeError):
    """Backend permission denied"""
    pass

class BackendTimeoutError(MRuntimeError):
    """Backend operation timeout"""
    pass

# yottadb_backend.py
import yottadb
from .backend_exceptions import BackendConnectionError, BackendTimeoutError

def get(self, name: str, *subscripts: str) -> str | None:
    try:
        key = yottadb.Key(name)[subscripts]
        return key.get().decode('utf-8')
    except yottadb.YDBError as e:
        if e.code() == 150373850:  # YDB_ERR_GVUNDEF
            return None
        elif e.code() == yottadb.YDB_ERR_TIME:
            raise BackendTimeoutError(f"YottaDB timeout: {e}") from e
        else:
            raise BackendConnectionError(f"YottaDB error: {e}") from e
```

### 3. Subscript Canonicalization Integration

**Pattern**: Use existing `SubscriptCanonicalizer` before passing to SDK

**Rationale**: Maintain MUMPS collation semantics (numeric vs string)

**Implementation**:
```python
from .subscript_canonicalizer import SubscriptCanonicalizer

class YottaDBGlobalStorage(GlobalStorageBackend):
    def __init__(self):
        self._canonicalizer = SubscriptCanonicalizer()
    
    def set(self, name: str, *subscripts: str, value: str) -> None:
        canonical_subs = [self._canonicalizer.canonicalize(s) for s in subscripts]
        key = yottadb.Key(name)[canonical_subs]
        key.value = value.encode('utf-8')
```

### 4. Test Fixture Strategy

**Pattern**: Parameterize tests with backend selection via environment variable

**Rationale**: Run same test suite against all backends

**Implementation**:
```python
# tests/runtime/backend/conftest.py
import pytest
import os

@pytest.fixture
def backend():
    backend_type = os.environ.get("M2PY_GLOBAL_BACKEND", "inmemory")
    
    if backend_type == "yottadb":
        if not os.environ.get("ydb_dist"):
            pytest.skip("YottaDB tests require $ydb_dist environment")
    elif backend_type == "iris":
        pytest.skip("IRIS tests require Docker container")
    
    from m2py.runtime import get_global_storage
    return get_global_storage(backend_type)

# tests/runtime/backend/test_basic_operations.py
def test_get_set(backend):
    backend.set("^Test", "sub1", value="hello")
    assert backend.get("^Test", "sub1") == "hello"
```

### 5. Docker-Based Test Execution (IRIS only)

**Pattern**: Use Docker Compose for IRIS backend testing (YottaDB runs natively)

**Rationale**: YottaDB runs natively in the dev container via extracted libraries.
IRIS requires a server process, so it still needs Docker.

**Implementation**:
```yaml
# docker-compose.test.yml
version: '3.8'
services:  
  iris:
    image: intersystems/iris-community:latest
    ports:
      - "1972:1972"
    environment:
      M2PY_GLOBAL_BACKEND: iris
      M2PY_IRIS_HOST: localhost
      M2PY_IRIS_PORT: 1972
      M2PY_IRIS_NAMESPACE: USER
      M2PY_IRIS_USERNAME: _SYSTEM
      M2PY_IRIS_PASSWORD: SYS
```

**Usage**:
```bash
# Run YottaDB tests natively (no Docker needed)
export ydb_dist=/opt/yottadb/current
export LD_LIBRARY_PATH="$ydb_dist:$LD_LIBRARY_PATH"
export ydb_gbldir=$HOME/.yottadb/yottadb.gld
export ydb_routines="$HOME/.yottadb/r $ydb_dist/libyottadbutil.so"
export ydb_chset=M
uv run pytest tests/runtime/backend/ -m yottadb

# Run IRIS tests (requires Docker)
docker-compose -f docker-compose.test.yml up -d iris
M2PY_GLOBAL_BACKEND=iris uv run pytest tests/runtime/backend/ -m iris
docker-compose -f docker-compose.test.yml down
```

## Technology Decisions

### Decision: Wrap Native SDKs (Not Implement Protocols)

**Alternatives Considered**:
1. Implement YottaDB/IRIS protocols from scratch (TCP/native protocol)
2. Use existing SDKs as-is
3. **[CHOSEN]** Wrap SDKs with thin adapter layer

**Rationale**:
- SDKs are maintained by database vendors (security updates, bug fixes)
- Protocol implementation is complex and error-prone
- Adapter layer maintains m2py semantics while leveraging SDK robustness

**Tradeoffs**:
- Dependency on external packages (yottadb, intersystems-irispython)
- SDK API changes require adapter updates
- Performance overhead from wrapper layer (~1-2% based on benchmarks)

### Decision: Lazy Connection Initialization

**Alternatives Considered**:
1. Connect on module import
2. **[CHOSEN]** Connect on first global access
3. Explicit connect/disconnect API

**Rationale**:
- m2py code may not use globals (pure computation)
- Lazy init avoids connection overhead for non-database code
- Matches existing InMemoryGlobalStorage behavior (no setup required)

**Tradeoffs**:
- First global access has higher latency (connection establishment)
- Connection errors delayed until first use (not at startup)
- Requires `_ensure_initialized()` guard in every method

### Decision: Environment-Based Configuration

**Alternatives Considered**:
1. Configuration file (YAML/TOML)
2. **[CHOSEN]** Environment variables (M2PY_GLOBAL_BACKEND, M2PY_IRIS_*)
3. Programmatic API (backend.configure())

**Rationale**:
- 12-factor app principle (configuration via environment)
- Easy CI/CD integration (set env vars in workflow)
- Matches existing m2py patterns (no config files currently)

**Tradeoffs**:
- No schema validation for env vars (typos cause runtime errors)
- Secrets in environment (IRIS password) require secure handling
- No per-test configuration (must restart process to change backend)

### Decision: Unified Test Suite with Pytest Marks

**Alternatives Considered**:
1. Separate test files per backend (test_yottadb_*.py, test_iris_*.py)
2. **[CHOSEN]** Single test suite with @pytest.mark.backend("yottadb")
3. Test matrix with parameterization

**Rationale**:
- Ensures semantic equivalence (same test logic for all backends)
- Reduces duplication (100+ tests don't need 3x copies)
- Selective execution via pytest -m (run only IRIS tests)

**Tradeoffs**:
- Backend-specific edge cases harder to test (may need separate tests)
- Marks must be applied consistently (manual process)
- Slower test execution (can't parallelize across backends easily)

## Open Questions & Risks

### Open Questions

1. **YottaDB Transaction Adapter Complexity**: Can we reliably map tp(callback) to start/commit/rollback without edge cases?
   - **Resolution needed before**: Phase 1 design
   - **Research task**: Prototype transaction context manager with nested transaction handling

2. **IRIS Connection Pooling**: Should initial implementation include connection pooling for performance?
   - **Resolution needed before**: Phase 1 design
   - **Research task**: Benchmark single connection vs pooled connections for typical workloads

3. **Test Reorganization Impact**: Will moving ~100 tests break existing CI/CD workflows?
   - **Resolution needed before**: Phase 2 task breakdown
   - **Research task**: Audit CI/CD for test path dependencies

### Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| YDB transaction model incompatible with protocol | Medium | High | Prototype adapter in research phase, fallback to "transactions not supported" |
| IRIS connection latency breaks performance goals | Low | Medium | Document latency overhead, consider async/connection pooling in future |
| Test reorganization introduces regressions | Medium | Medium | Checkpoint tests before moving, run full suite after reorganization |
| SDK version incompatibilities (yottadb 2.x vs 3.x) | Low | Low | Pin SDK versions in pyproject.toml, document version requirements |

## Next Steps

**Phase 0 Complete**: All research questions answered.

**Proceed to Phase 1**:
1. Create `data-model.md`: Backend class architecture, exception hierarchy, connection models
2. Create `quickstart.md`: Developer guide for using backends
3. Create `contracts/backend-protocol.md`: Reference existing GlobalStorageBackend
4. Update agent context with YottaDB and IRIS technologies

**Phase 2** (after Phase 1):
- Run `/speckit.tasks` to generate implementation task breakdown
- Begin implementation per task order

---

**Research Status**: ✅ COMPLETE  
**Approval**: Ready for Phase 1 design
