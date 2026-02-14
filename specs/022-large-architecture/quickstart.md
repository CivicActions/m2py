# Quickstart: Phase 4 — Large Architecture

**Branch**: `022-large-architecture`

## Prerequisites

- Phases 1 (019), 2 (020), and 3 (021) complete
- `uv run pytest` passes with zero failures/xfails/skips
- Docker available (for YDB validation)

## Development Order

**Sequential**: Sub-Phase 1 → Sub-Phase 2 → Sub-Phase 3

### Sub-Phase 1: I/O Device Management

1. Create `src/m2py/runtime/devices.py` with `MUMPSDevice` abstract class
2. Implement `PrincipalDevice` wrapping current stdout/stdin behavior
3. Refactor `MUMPSRuntime.write()`/read helpers to dispatch through `current_device`
4. Add device table to `MUMPSRuntime` with `$PRINCIPAL` pre-registered
5. Update `open_device()` → create `FileDevice`, `use_device()` → switch current, `close_device()` → cleanup
6. Add per-device `$X`/`$Y`/`$KEY`/`$ZEOF` tracking
7. Implement `FileDevice` (read/write/append/stream modes)
8. Implement `TCPDevice` (client connections)
9. Update codegen if needed (minimal — runtime API calls remain similar)
10. Run full test suite — must pass

### Sub-Phase 2: JOB as Real Processes

1. Create `SQLiteGlobalStorage` implementing `GlobalStorageBackend` protocol
2. Migrate test suite to use SQLite backend (verify all tests pass)
3. Update `start_job()` to use `subprocess.Popen` instead of `threading.Thread`
4. Create a JOB entry script that imports the transpiled module + sets up runtime
5. Ensure child process connects to the same SQLite database
6. Update `$JOB` to use real OS PID
7. Update transaction support for SQLite (BEGIN/COMMIT/ROLLBACK)
8. Run full test suite — must pass

### Sub-Phase 3: Inter-Process LOCK

1. Add `locks` table to SQLite database
2. Implement `lock()`/`unlock()`/`unlock_all()` using SQLite lock table
3. Add dead-process detection (PID liveness check during polling)
4. Add hierarchical lock blocking (parent/child subscript checks)
5. Update `ZSHOW "L"` to query SQLite lock table
6. Verify single-process backward compatibility
7. Run full test suite — must pass

## Key Commands

```bash
# Run tests
uv run pytest

# Run specific test file
uv run pytest tests/unit/runtime/test_devices.py -v

# Validate against YDB
uv run python utils/validate.py --code 'TEST OPEN "/tmp/t.txt":NEWVERSION USE "/tmp/t.txt" WRITE "hi",! CLOSE "/tmp/t.txt" QUIT'

# Debug ASG output
uv run python utils/validate.py --debug --code 'TEST OPEN "/tmp/t.txt":NEWVERSION QUIT'
```

## Files to Create

| File | Purpose |
|------|---------|
| `src/m2py/runtime/devices.py` | Device abstraction layer |
| `src/m2py/runtime/sqlite_storage.py` | SQLite global storage backend |
| `tests/unit/runtime/test_devices.py` | Device unit tests |
| `tests/unit/runtime/test_sqlite_storage.py` | SQLite storage unit tests |
| `tests/unit/runtime/test_cross_process_lock.py` | Cross-process lock tests |
| `tests/integration/test_file_io.py` | File I/O integration tests |
| `tests/integration/test_job_subprocess.py` | JOB subprocess integration tests |

## Files to Modify

| File | Changes |
|------|---------|
| `src/m2py/runtime/__init__.py` | Device table, current_device, I/O dispatch, JOB subprocess, $ZEOF |
| `src/m2py/runtime/helpers.py` | Read functions → device-aware |
| `src/m2py/runtime/globals.py` | SQLite backend, lock table |
| `src/m2py/codegen/statements.py` | Minor codegen updates if runtime API changes |
| `src/m2py/codegen/expressions.py` | $ZEOF codegen |

## Constitution Compliance

- **I. Semantic Correctness**: All behavior validated against YDB reference output
- **II. YDB Reference**: Use `utils/validate.py` for every new feature
- **III. Layer Separation**: Runtime changes only — no codegen/parser changes for I/O
- **VII. Minimize Runtime**: Device dispatch is inherently runtime (dynamic device state)
