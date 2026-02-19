# Quickstart: Using Database Backends

**Date**: 2025-02-19  
**Feature**: 025-database-backends  
**Phase**: 1 (Design & Contracts)

## Overview

This guide shows how to use YottaDB and IRIS backends with m2py-generated Python code. By default, m2py uses an in-memory backend suitable for development and testing. For production use cases requiring data persistence, switch to YottaDB or IRIS backends via environment configuration.

**No code changes required** - backend selection is entirely configuration-driven.

## Quick Start (3 Steps)

### 1. Install Backend SDK

**YottaDB**:
```bash
# No local installation needed — runs inside Docker container
# Build the YDB container image (auto-built on first use)
bash utils/ydb.sh echo "ready"
```

**IRIS**:
```bash
# No database installation required (uses network connection)
uv add intersystems-irispython --optional backend
```

**InMemory** (default):
```bash
# No installation needed - included in m2py
```

### 2. Configure Backend via Environment

**YottaDB**:
```bash
# YDB env vars are set automatically inside the container by ydb_env_set
export M2PY_GLOBAL_BACKEND=yottadb
# Run inside YDB container:
bash utils/ydb.sh uv run python myprogram.py
```

**IRIS**:
```bash
export M2PY_GLOBAL_BACKEND=iris
# Connection env vars exported automatically by utils/iris.sh:
bash utils/iris.sh uv run python myprogram.py
```

**InMemory**:
```bash
export M2PY_GLOBAL_BACKEND=inmemory  # Or omit (default)
```

### 3. Run Your MUMPS Code

```bash
# Run m2py-generated code (backend selected automatically)
uv run python -c "from m2py.runtime import get_global_storage; \
    backend = get_global_storage(); \
    backend.set('^MyGlobal', 'key1', value='Hello World'); \
    print(backend.get('^MyGlobal', 'key1'))"
```

**Output**: `Hello World`

---

## Docker-Based Development

### YottaDB in Docker

**Why**: YottaDB Python SDK requires `libyottadb.so` which is only available inside the container. `utils/ydb.sh` handles building the image and mounting the workspace automatically.

**Setup**:
```bash
# Auto-builds image on first use, mounts workspace, runs command
bash utils/ydb.sh uv run python myprogram.py

# Interactive shell (YDB env pre-configured)
bash utils/ydb.sh bash
```

**How it works**:
- `Dockerfile.yottadb` builds an image with YottaDB + Python + uv + gcc
- `ydb_env_set` is sourced automatically on container start
- `uv sync --group yottadb` runs in the entrypoint
- Venv is at `/tmp/m2py-venv` (doesn't clobber host `.venv`)

### IRIS in Docker

**Why**: No local IRIS installation, easy cleanup, network SDK connects over TCP.

**Setup**:
```bash
# Auto-starts IRIS container, exports connection env vars, runs command locally
bash utils/iris.sh uv run python myprogram.py

# Container management
bash utils/iris.sh --start    # Start container only
bash utils/iris.sh --stop     # Stop and remove container
bash utils/iris.sh --status   # Show container status
```

**Exported env vars**: `IRIS_HOST`, `IRIS_PORT`, `IRIS_NAMESPACE`, `IRIS_USER`, `IRIS_PASSWORD`

**Web Management Portal**:
- URL: http://localhost:52773/csp/sys/UtilHome.csp
- Credentials: `_SYSTEM` / `SYS`
- Use to browse globals, run SQL queries, monitor system

---

## Testing Your Application

### Run Tests Against Specific Backend

**InMemory** (fast, no setup):
```bash
uv run pytest tests/
```

**YottaDB** (requires Docker):
```bash
bash utils/ydb.sh uv run pytest tests/ -x -n0
```

**IRIS** (requires Docker):
```bash
bash utils/iris.sh uv run pytest tests/ -x -n0
```

### Run Tests Against All Backends

Use the provided test suite to validate semantic equivalence:

```bash
# InMemory
uv run pytest tests/runtime/backend/

# YottaDB (in Docker)
bash utils/ydb.sh uv run pytest tests/runtime/backend/ -m backend_yottadb

# IRIS (Docker container auto-started)
bash utils/iris.sh uv run pytest tests/runtime/backend/ -m backend_iris
```

---

## Configuration Reference

### Environment Variables

#### Backend Selection

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `M2PY_GLOBAL_BACKEND` | `inmemory`, `yottadb`, `iris` | `inmemory` | Backend type |

#### YottaDB Configuration (required when using YottaDB)

| Variable | Example | Default | Description |
|----------|---------|---------|-------------|
| `ydb_dist` | `/opt/yottadb/current` | *(required)* | YottaDB installation directory |
| `ydb_gbldir` | `/data/mumps.gld` | `mumps.gld` | Global directory path |
| `ydb_routines` | `/data` | *empty* | Routine search path |
| `ydb_tmp` | `/tmp` | `/tmp` | Temporary file directory |

#### IRIS Configuration (required when using IRIS)

| Variable | Example | Default | Description |
|----------|---------|---------|-------------|
| `M2PY_IRIS_HOST` | `localhost` | `localhost` | IRIS server hostname |
| `M2PY_IRIS_PORT` | `1972` | `1972` | IRIS superserver port |
| `M2PY_IRIS_NAMESPACE` | `USER` | `USER` | IRIS namespace for globals |
| `M2PY_IRIS_USERNAME` | `_SYSTEM` | `_SYSTEM` | Authentication username |
| `M2PY_IRIS_PASSWORD` | `SYS` | *(required)* | Authentication password |

### Configuration Validation

**Common Errors**:

1. **YottaDB: `$ydb_dist not set`**
   ```
   BackendConnectionError: YottaDB not configured: $ydb_dist environment variable not set.
   Run: source /opt/yottadb/current/ydb_env_set
   ```
   **Fix**: `source /opt/yottadb/current/ydb_env_set` or set `export ydb_dist=/opt/yottadb/current`

2. **IRIS: Missing password**
   ```
   BackendConfigurationError: IRIS password not configured: M2PY_IRIS_PASSWORD environment variable required
   ```
   **Fix**: `export M2PY_IRIS_PASSWORD=SYS`

3. **IRIS: Connection refused**
   ```
   BackendConnectionError: IRIS connection failed: [Errno 111] Connection refused
   ```
   **Fix**: Ensure IRIS container is running: `docker ps | grep iris`

4. **Unknown backend**
   ```
   ValueError: Unknown backend: postgres
   ```
   **Fix**: Use `inmemory`, `yottadb`, or `iris`

---

## Usage Examples

### Example 1: Basic Global Operations

```python
from m2py.runtime import get_global_storage

# Backend selected via M2PY_GLOBAL_BACKEND environment variable
backend = get_global_storage()

# Set values
backend.set("^Patient", "123", "Name", value="John Doe")
backend.set("^Patient", "123", "Age", value="45")

# Get values
name = backend.get("^Patient", "123", "Name")
print(f"Patient: {name}")  # Output: Patient: John Doe

# Check existence
data_code = backend.data("^Patient", "123")
print(f"Data code: {data_code}")  # Output: Data code: 10 (has descendants)

# Traversal
subscript = backend.order("^Patient", "123", "")
print(f"First subscript: {subscript}")  # Output: First subscript: Age

# Delete
backend.kill("^Patient", "123")
```

### Example 2: Lock Synchronization

```python
from m2py.runtime import get_global_storage
import time

backend = get_global_storage()

# Acquire lock (blocks until available)
success = backend.lock("^JobQueue", "process1")
if success:
    print("Lock acquired")
    
    # Critical section
    backend.set("^JobQueue", "process1", "status", value="running")
    time.sleep(5)  # Simulate work
    
    # Release lock
    backend.unlock("^JobQueue", "process1")
    print("Lock released")

# Lock with timeout
success = backend.lock("^Resource", "shared", timeout=10.0)
if not success:
    print("Lock timeout after 10 seconds")
```

### Example 3: Transactions

```python
from m2py.runtime import get_global_storage

backend = get_global_storage()

# Start transaction
backend.transaction_start()

try:
    # Multiple operations (atomic)
    balance = float(backend.get("^Account", "12345", "Balance") or "0")
    backend.set("^Account", "12345", "Balance", value=str(balance - 100))
    backend.set("^Transaction", "txn001", "amount", value="-100")
    backend.set("^Transaction", "txn001", "status", value="completed")
    
    # Commit
    backend.transaction_commit()
    print("Transaction committed")
except Exception as e:
    # Rollback on error
    backend.transaction_rollback()
    print(f"Transaction rolled back: {e}")
```

### Example 4: Cross-Namespace Globals (IRIS only)

```python
from m2py.runtime import get_global_storage

backend = get_global_storage("iris")  # Explicit IRIS backend

# Write to USER namespace (default)
backend.set("^Data", "key1", value="value1")

# Write to SAMPLES namespace (extended reference syntax)
backend.set('^|"SAMPLES"|Data', "key1", value="value2")

# Read from SAMPLES namespace
value = backend.get('^|"SAMPLES"|Data', "key1")
print(f"SAMPLES Data: {value}")  # Output: SAMPLES Data: value2
```

### Example 5: Programmatic Backend Selection

```python
import os
from m2py.runtime import get_global_storage

# Development: use inmemory
if os.environ.get("ENV") == "development":
    backend = get_global_storage("inmemory")

# Staging: use YottaDB
elif os.environ.get("ENV") == "staging":
    os.environ["ydb_dist"] = "/opt/yottadb/current"
    backend = get_global_storage("yottadb")

# Production: use IRIS
else:
    os.environ.update({
        "M2PY_IRIS_HOST": "prod-iris.example.com",
        "M2PY_IRIS_PORT": "1972",
        "M2PY_IRIS_NAMESPACE": "PROD",
        "M2PY_IRIS_USERNAME": "AppUser",
        "M2PY_IRIS_PASSWORD": os.environ["IRIS_PASSWORD"],  # From secrets
    })
    backend = get_global_storage("iris")

# Use backend (code unchanged regardless of selection)
backend.set("^AppConfig", "version", value="1.0.0")
```

---

## Performance Considerations

### Latency Comparison

| Backend | First Operation | Subsequent Operations | Notes |
|---------|----------------|----------------------|-------|
| **InMemory** | <0.1ms | <0.01ms | Fastest, no persistence |
| **YottaDB** | ~5ms | ~0.5ms | Process-bound, low overhead |
| **IRIS** | ~50ms | ~3ms | Network connection, higher latency |

**Recommendations**:
- **Development/Testing**: Use InMemory (fastest, no setup)
- **Local Production**: Use YottaDB (best performance for single-node)
- **Distributed Production**: Use IRIS (supports clustering, network access)

### Optimization Tips

1. **Batch Operations**: Use `get_tree()` / `merge_tree()` instead of individual `get()` / `set()` calls
2. **Connection Pooling** (future): IRIS backend will support connection pooling for multi-threaded applications
3. **Transaction Batching**: Group related operations in transactions to reduce roundtrips
4. **Lock Granularity**: Lock at finest granularity needed (e.g., `^Global("ID")` not `^Global`)

---

## Troubleshooting

### Problem: YottaDB errors after installation

**Symptoms**:
```
ImportError: cannot import name 'yottadb' from 'yottadb'
```

**Solution**:
1. Verify YottaDB installed: `ls /opt/yottadb`
2. Source environment: `source /opt/yottadb/current/ydb_env_set`
3. Check `$ydb_dist`: `echo $ydb_dist` (should output `/opt/yottadb/current`)
4. Reinstall SDK: `uv sync && uv run python -c "import yottadb; print('OK')"`

### Problem: IRIS connection timeout

**Symptoms**:
```
BackendConnectionError: IRIS connection failed: Timeout connecting to localhost:1972
```

**Solution**:
1. Check container running: `docker ps | grep iris`
2. Check port exposed: `docker ps` should show `0.0.0.0:1972->1972/tcp`
3. Wait for startup: IRIS takes 10-15 seconds to initialize
4. Test connection: `telnet localhost 1972` (should connect)

### Problem: Tests fail with one backend but pass with another

**Symptoms**:
```
PASSED tests/test_globals.py::test_get_set (inmemory)
FAILED tests/test_globals.py::test_get_set (yottadb)
```

**Solution**:
1. **Semantic difference**: Check if test assumes specific backend behavior (e.g., numeric collation)
2. **Configuration issue**: Verify backend environment variables set correctly
3. **Bug in backend**: Report issue with test case and backend configuration

### Problem: Permission denied (IRIS)

**Symptoms**:
```
BackendPermissionError: IRIS error: User '_SYSTEM' does not have WRITE permission on namespace USER
```

**Solution**:
1. Use admin user: `export M2PY_IRIS_USERNAME=_SYSTEM`
2. Grant permissions in IRIS Management Portal (http://localhost:52773)
3. Switch to application namespace with write access

---

## Migration Guide

### Migrating from InMemory to YottaDB/IRIS

**No code changes required** - only configuration:

1. **Install backend SDK** (see Installation section above)
2. **Set environment variables** (see Configuration Reference above)
3. **Test application** with new backend:
   ```bash
   M2PY_GLOBAL_BACKEND=yottadb uv run pytest tests/
   ```
4. **Verify data persistence**:
   ```bash
   # Write data
   M2PY_GLOBAL_BACKEND=yottadb uv run python -c "from m2py.runtime import get_global_storage; \
       backend = get_global_storage(); backend.set('^Test', 'key', value='persistent')"
   
   # Restart process, read data (should succeed)
   M2PY_GLOBAL_BACKEND=yottadb uv run python -c "from m2py.runtime import get_global_storage; \
       backend = get_global_storage(); print(backend.get('^Test', 'key'))"
   ```
5. **Update deployment configuration** (Docker Compose, Kubernetes, etc.)

### Switching Between YottaDB and IRIS

**Use case**: Develop on YottaDB (faster), deploy to IRIS (production features)

**Strategy**:
1. **Unified test suite**: Run same tests against both backends to ensure equivalence
2. **Environment parity**: Use Docker for both to match production setup
3. **Feature detection**: Check for IRIS-specific features (e.g., `$LISTBUILD`) and provide fallbacks

**Example**:
```python
from m2py.runtime import get_global_storage
import os

backend = get_global_storage()

# Feature detection
is_iris = os.environ.get("M2PY_GLOBAL_BACKEND") == "iris"

if is_iris:
    # Use IRIS-specific features
    backend.set("^Data", "list", value="$LISTBUILD(1,2,3)")  # IRIS $LISTBUILD
else:
    # Fallback for YottaDB
    backend.set("^Data", "list", value="1^2^3")  # Delimited string
```

---

## Next Steps

1. **Read Architecture**: See [data-model.md](data-model.md) for backend internals
2. **Contribute**: Add backend support for PostgreSQL, Redis, etc.
3. **Production Deployment**: See deployment guides for YottaDB/IRIS clustering
4. **Performance Tuning**: Benchmark your workload, optimize hot paths

**Support**: For issues or questions, see [GitHub Discussions](https://github.com/your-org/m2py/discussions)
