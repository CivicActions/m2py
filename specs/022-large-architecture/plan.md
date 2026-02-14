# Implementation Plan: Phase 4 — Large Architecture

**Branch**: `022-large-architecture` | **Date**: 2026-02-12 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/022-large-architecture/spec.md`

## Summary

Phase 4 implements three interdependent subsystems — I/O device management, subprocess-based JOB, and cross-process LOCK — that together enable multi-process MUMPS operation. The technical approach uses a `MUMPSDevice` abstraction layer for I/O dispatch, SQLite with WAL mode for shared global storage and lock coordination, and `subprocess.Popen` for JOB process creation. All three sub-phases are sequential: I/O → JOB → LOCK.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX (parser), sqlite3 (stdlib — shared storage), subprocess (stdlib — JOB)
**Storage**: SQLite file-backed database (WAL mode) for cross-process globals and lock table
**Testing**: pytest via `uv run pytest`, YDB Docker validation via `utils/validate.py`
**Target Platform**: Linux (dev container), portable Python
**Project Type**: Single project — transpiler runtime extension
**Performance Goals**: Correctness first. SQLite WAL mode provides adequate concurrent read/write performance for VistA-scale workloads (~100 concurrent processes).
**Constraints**: No external dependencies beyond stdlib. No separate server process. Process crash must not corrupt shared state (SQLite ACID guarantees).
**Scale/Scope**: ~2,000 lines of new runtime code, ~1,500 lines of tests. 3 sub-phases over 20-28 days.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | PASS | All I/O, JOB, LOCK behavior validated against MUMPS standard and YDB |
| II. YDB as Reference | PASS | YDB Docker tests run for all features. Spec corrected where YDB behavior differs from initial assumptions (FR-022 OPEN timeout, FR-097 ^$LOCK) |
| III. Strict Layer Separation | PASS | Changes are runtime-only. Grammar/parser/ASG already handle OPEN/USE/CLOSE/JOB/LOCK. No codegen changes needed except $ZEOF expression and minor API adjustments |
| IV. Explicit Over Implicit | PASS | Device dispatch is explicit via `current_device`. Lock ownership is explicit via PID. Process isolation is explicit via subprocess |
| V. Foundational Correctness | PASS | I/O device layer is foundational — built first, then JOB, then LOCK. Each layer builds on the previous |
| VI. Cross-Cutting Semantics | PASS | $X/$Y/$KEY/$ZEOF are per-device (cross-cutting). Shared storage affects all global operations (cross-cutting). Both addressed at the architectural level |
| VII. Minimize Runtime Surface | PASS | Device dispatch, process management, and lock coordination are inherently dynamic runtime concerns. Cannot be statically resolved |
| VIII. Research Before Implementation | PASS | Extensive research completed: current runtime state, MUMPS standard, YDB behavior, SQLite patterns |

**Post-design re-check**: All gates still pass. The SQLite backend adds a runtime dependency but it's stdlib (`sqlite3`), not an external package. The `subprocess.Popen` approach for JOB avoids fork/pickle complexity.

## Project Structure

### Documentation (this feature)

```text
specs/022-large-architecture/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Entity model and SQLite schema
├── quickstart.md        # Development quickstart guide
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
src/m2py/runtime/
├── __init__.py          # MODIFY: Device table, current_device, I/O dispatch, JOB subprocess
├── devices.py           # NEW: MUMPSDevice, PrincipalDevice, FileDevice, TCPDevice
├── sqlite_storage.py    # NEW: SQLiteGlobalStorage implementing GlobalStorageBackend
├── job_runner.py        # NEW: Entry point for JOB'd subprocess
├── globals.py           # MODIFY: Add SQLite lock methods, update protocol
├── helpers.py           # MODIFY: Read functions → device-aware
└── exceptions.py        # MODIFY: Add device-related exceptions

src/m2py/codegen/
├── expressions.py       # MODIFY: $ZEOF codegen
└── statements.py        # MODIFY: Minor API adjustments if runtime signatures change

tests/
├── unit/runtime/
│   ├── test_devices.py              # NEW: Device abstraction tests
│   ├── test_principal_device.py     # NEW: PrincipalDevice tests
│   ├── test_file_device.py          # NEW: FileDevice tests
│   ├── test_tcp_device.py           # NEW: TCPDevice tests
│   ├── test_sqlite_storage.py       # NEW: SQLite global storage tests
│   ├── test_cross_process_lock.py   # NEW: Cross-process lock tests
│   └── test_job_threading.py        # MODIFY: Update for subprocess-based JOB
├── integration/
│   ├── test_file_io.py              # NEW: End-to-end file I/O tests
│   └── test_job_subprocess.py       # NEW: End-to-end JOB subprocess tests
└── functional/
    └── io/                          # MODIFY: Add file I/O functional tests
```

## Implementation Phases

### Sub-Phase 1: I/O Device Management (F-02, F-12 remainder) — 10-14 days

**Goal**: Replace single-target I/O with device-dispatched I/O. All existing tests pass. File I/O works end-to-end.

#### Step 1.1: MUMPSDevice Abstraction (2 days)

Create `src/m2py/runtime/devices.py`:

```python
class MUMPSDevice(ABC):
    """Abstract base class for all MUMPS I/O devices."""
    name: str
    x_pos: int = 0      # $X per-device
    y_pos: int = 0      # $Y per-device
    key: str = ""        # $KEY per-device
    zeof: bool = False   # $ZEOF per-device

    @abstractmethod
    def read(self, maxlen=None, timeout=None) -> tuple[str, str]:
        """Read from device. Returns (data, terminator_key)."""

    @abstractmethod
    def write(self, data: str) -> None:
        """Write data to device. Updates x_pos."""

    @abstractmethod
    def write_newline(self) -> None:
        """Write newline. Resets x_pos, increments y_pos."""

    @abstractmethod
    def close(self) -> None:
        """Close device and release resources."""
```

Implement `PrincipalDevice`:
- Wraps current `write()` → `_output` list behavior
- Wraps current `read()` → `sys.stdin` / `input()` behavior
- Preserves exact current $X/$Y tracking logic
- **Critical**: All existing write/read tests must pass through PrincipalDevice without any output changes

**Test gate**: Full test suite passes. No behavioral changes.

#### Step 1.2: Device Table & I/O Dispatch (2-3 days)

Modify `MUMPSRuntime.__init__()`:
- Add `self._principal_device = PrincipalDevice()`
- Add `self._device_table: dict[str, MUMPSDevice] = {"0": self._principal_device}`
- Add `self._current_device: MUMPSDevice = self._principal_device`

Refactor `MUMPSRuntime.write()`:
- Delegate to `self._current_device.write(data)`
- $X/$Y now tracked in device, not in runtime

Refactor read helpers:
- `m_read_timeout()`, `m_read_char()`, `m_read_maxlen()`, `m_read_maxlen_timeout()` → accept device parameter or use `_rt._current_device`
- Basic `R X` codegen: change from `input()` to `_rt.read_line()` which delegates to `_current_device.read()`

Refactor ISV accessors:
- `x()` → `self._current_device.x_pos`
- `y()` → `self._current_device.y_pos`
- `key()` → `self._current_device.key`
- `io()` → `self._current_device.name`

**Test gate**: Full test suite passes. All existing I/O behavior identical.

#### Step 1.3: FileDevice Implementation (2-3 days)

Implement `FileDevice(MUMPSDevice)`:
- `open(path, mode, params)`: Maps MUMPS keywords → Python file modes
  - NEWVERSION → `"w"`, READONLY → `"r"`, APPEND → `"a"`, read-write → `"r+"`
  - STREAM → disables record-size limits
  - RECORDSIZE=n → truncates/pads output lines
- `read()`: Reads line from file. Sets `$KEY` to `$C(10)` (newline) or `""` (EOF). Updates `$ZEOF`.
- `write()`: Writes to file. Updates `$X`.
- `close()`: Closes file handle.

Update `open_device()`:
- Create `FileDevice` for file paths
- Register in device table
- Handle timeout (for files, OPEN is immediate — timeout always succeeds)
- Handle errors (file not found → raise DEVOPENFAIL error, NOT $TEST=0)

Update `use_device()`:
- Save current device's $X/$Y to its device object
- Switch `_current_device` to target device
- $X/$Y/$KEY/$ZEOF now automatically reflect target device's state

Update `close_device()`:
- Close device, remove from table
- If closing current device → revert to $PRINCIPAL
- Set $IO to "0"

**YDB-validated behavior**:
```
$IO during USE of file = full file path (e.g., "/tmp/test.txt")
$IO after CLOSE = "0"
$KEY after file READ = $C(10) for line-terminated, "" for EOF
$ZEOF = 0 until READ past last data, then 1
$X tracks per-device (WRITE "AB" → $X=2 on that device)
$Y is cumulative per-device (WRITE ! → $Y+1 on that device)
```

**Test gate**: Full test suite passes. New file I/O tests pass. YDB validation matches.

#### Step 1.4: $ZEOF ISV (1 day)

Add `$ZEOF` to the runtime:
- Accessor: `zeof()` → `self._current_device.zeof`
- FileDevice: Set `zeof = True` when READ returns empty at EOF
- PrincipalDevice: `zeof = False` (interactive) or detect pipe EOF

Add codegen for `$ZEOF`:
- In `expressions.py`: `$ZEOF` → `_rt.zeof()` (follows $KEY/$IO pattern)

**YDB-validated reference**:
```
OPEN file:READONLY USE file
$ZEOF before READ = 0
READ line1 → $ZEOF = 0
READ line2 → $ZEOF = 0
READ past end → $ZEOF = 1, data = ""
```

**Test gate**: Full test suite passes. $ZEOF tests pass.

#### Step 1.5: TCPDevice Implementation (2-3 days)

Implement `TCPDevice(MUMPSDevice)`:
- `open(host, port, params)`: Connect via `socket.socket()`
- `read()`: Read until delimiter or timeout. Set `$KEY`.
- `write()`: Send over socket.
- `close()`: Close socket.

Device type detection in `open_device()`:
- If name matches `host:port` pattern → TCPDevice (CONNECT parameter required)
- If name starts with `/` or is a relative path → FileDevice
- If name is `"0"` or `$PRINCIPAL` → PrincipalDevice (already registered)

**Test gate**: Full test suite passes. TCP tests pass (against local echo server in tests).

#### Step 1.6: Codegen & Integration (1-2 days)

- Verify codegen for OPEN/USE/CLOSE still works (runtime API should be compatible)
- If runtime method signatures changed, update codegen call sites
- Write integration tests: transpile MUMPS file I/O routines, compare output against YDB
- Write functional tests using YDBTest infrastructure

**Test gate**: Full test suite passes. All Sub-Phase 1 tests pass. Zero failures/xfails/skips.

---

### Sub-Phase 2: JOB as Real Processes (F-04) — 5-8 days

**Goal**: Replace thread-based JOB with subprocess-based JOB. Shared globals via SQLite. All tests pass.

#### Step 2.1: SQLiteGlobalStorage Backend (3-4 days)

Create `src/m2py/runtime/sqlite_storage.py`:

```python
class SQLiteGlobalStorage:
    """SQLite-backed GlobalStorageBackend for cross-process global sharing."""

    def __init__(self, db_path: str | None = None):
        # If db_path is None, use tempfile for single-process mode
        self._db_path = db_path or tempfile.mktemp(suffix=".db")
        self._conn = sqlite3.connect(self._db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()
```

Implement `GlobalStorageBackend` protocol methods:
- `set_global(name, subscripts, value)` → INSERT OR REPLACE
- `get_global(name, subscripts)` → SELECT value
- `kill_global(name, subscripts)` → DELETE subtree
- `data_global(name, subscripts)` → check value + children existence
- `order_global(name, subscripts, direction)` → SELECT with ORDER BY
- `query_global(name, subscripts)` → next subscript via sorted query
- `merge_global()` → batch INSERT from source
- `increment_global()` → atomic UPDATE via SQL transaction
- Transaction support: `transaction_start()` → SAVEPOINT, `transaction_commit()` → RELEASE, `transaction_rollback()` → ROLLBACK TO

Key design considerations:
- **Subscript storage**: JSON arrays for correct structure, with a custom collation for MUMPS numeric-before-string sorting
- **$ORDER**: SQL query with `WHERE subscripts > ? ORDER BY subscripts LIMIT 1` using custom collation
- **Naked indicator**: Per-connection Python state, not stored in SQLite (correct MUMPS per-process behavior)
- **Connection per process**: Each process opens its own connection to the shared file

**Test gate**: Full test suite passes with SQLiteGlobalStorage as the backend. All existing global tests (SET, GET, KILL, MERGE, $DATA, $ORDER, $QUERY, $INCREMENT, TSTART/TCOMMIT/TROLLBACK) pass identically.

#### Step 2.2: Subprocess-Based JOB (2-3 days)

Create `src/m2py/runtime/job_runner.py`:

```python
"""Entry point for JOB'd subprocess."""
def main():
    args = parse_args()  # routine, label, db_path, actuallist values
    storage = SQLiteGlobalStorage(args.db_path)
    rt = MUMPSRuntime(global_storage=storage)
    module = importlib.import_module(args.routine)
    entry = getattr(module, args.label)
    try:
        run_with_goto_support(entry, rt, initial_locals_from_actuallist)
    except SystemExit:
        pass
    finally:
        rt.globals.unlock_all()  # Release all locks on exit
```

Update `start_job()`:
- Replace `threading.Thread` with `subprocess.Popen`
- Pass SQLite DB path to child
- Child imports transpiled module and runs entry function
- Child has independent local variables (fresh Python process)
- Child shares globals via same SQLite file

Update `$JOB`:
- Parent: `os.getpid()` (real PID)
- Child: `os.getpid()` (child's real PID, naturally distinct)
- No more virtual PID counter

Update `$ZJOB`:
- Set to child's PID from `Popen.pid`

Timeout handling:
- With timeout: `Popen` + poll for process start within timeout
- Without timeout: `Popen` (returns immediately)
- Failure: timeout → `$TEST=0`, success → `$TEST=1`

**Test gate**: Full test suite passes. JOB tests pass with real subprocesses.

#### Step 2.3: Migration & Cleanup (1 day)

- Refactor `test_job_threading.py` for subprocess model
- Verify JOB indirection still works
- Remove dead thread-based code: virtual PID counter, `_job_thread_wrapper`, `threading.Thread` usage in JOB
- Update `ZSHOW "J"` if format changed

**Test gate**: Full test suite passes. Zero failures/xfails/skips.

---

### Sub-Phase 3: Inter-Process LOCK (F-01) — 5-7 days

**Goal**: Replace threading.Lock with SQLite-backed cross-process lock manager. All tests pass.

#### Step 3.1: SQLite Lock Manager (3-4 days)

Add lock table and methods to `SQLiteGlobalStorage`:

```sql
CREATE TABLE locks (
    lock_name   TEXT NOT NULL,
    subscripts  TEXT NOT NULL,     -- JSON array
    owner_pid   INTEGER NOT NULL,
    lock_count  INTEGER NOT NULL DEFAULT 1,
    acquired_at REAL NOT NULL,
    PRIMARY KEY (lock_name, subscripts)
);
```

Implement lock methods:
- `lock(name, subscripts, lock_type, timeout)`:
  - Release (`-`): Decrement count, delete if 0
  - Acquire (`+`): Check conflicts → acquire or wait/fail
- `unlock_all()`: Delete all locks owned by current PID

Hierarchical blocking:
- Lock `^A` blocks `^A(1)`, `^A(1,2)`, etc. from other PIDs
- Lock `^A(1)` is blocked by `^A` held by another PID
- SQL: check if any held lock's subscripts is a prefix of requested (or vice versa)

Dead-process detection:
- During polling, check `os.kill(owner_pid, 0)` for each blocking lock
- If `ProcessLookupError`: delete orphaned lock, retry

Blocking without timeout:
- Poll with exponential backoff (1ms → 128ms, matching YDB behavior)
- Check dead processes on each iteration
- Block indefinitely (no automatic deadlock detection)

#### Step 3.2: ZSHOW "L" Integration (1 day)

Update `MUMPSRuntime.zshow()` "L" handler:
- Query SQLite lock table for current process's locks
- Format matching YDB output:
  ```
  MLG:2,MLT:0
  LOCK ^B(1) LEVEL=1
  LOCK ^A LEVEL=1
  ```
- MLG = total lock count, MLT = 0 (no missed lock tracking)

#### Step 3.3: Single-Process Backward Compatibility (1 day)

- Verify all existing LOCK tests pass with SQLite lock manager
- Verify in-process locking (between routines) works identically
- Verify lock indirection still works
- Verify argumentless LOCK releases all locks
- Verify re-entrant locks (same process increments count)

#### Step 3.4: Cross-Process Integration Testing (1 day)

Test scenarios:
- Parent acquires lock, JOB'd child attempts same lock with timeout=0 → $TEST=0
- Parent releases lock, child retries → $TEST=1
- Child crashes → parent detects stale lock, acquires it
- Bare LOCK in child releases only child's locks
- Hierarchical blocking: parent holds `^A`, child can't acquire `^A(1)`

**Test gate**: Full test suite passes. All Sub-Phase 3 tests pass. Zero failures/xfails/skips.

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| SQLite performance for high-frequency global access | Medium | WAL mode, connection pooling, batch writes. Profile early in Step 2.1. |
| MUMPS sorting semantics in SQLite | High | Custom collation function or application-level sort. Test with $ORDER edge cases early. |
| Subprocess startup latency for JOB | Low | Acceptable for VistA TaskMan. Not a tight loop. |
| PrincipalDevice refactoring breaks existing tests | High | Step 1.1 designed to be output-identical. Run full test suite after every change. |
| Dead-process detection reliability | Medium | `os.kill(pid, 0)` works on Linux. Add retry logic and PID reuse awareness. |
| Naked indicator across processes | Medium | Per-process Python state. Correct MUMPS behavior — each process has independent naked indicator. |
| READ codegen changes (input() → _rt.read_line()) | High | May require updating many codegen tests. Batch the change and verify all at once. |

## Dependencies

- **External**: None beyond Python stdlib (`sqlite3`, `subprocess`, `socket`, `os`)
- **Internal**: Phases 1-3 complete. `GlobalStorageBackend` protocol in `globals.py`. Codegen infrastructure for OPEN/USE/CLOSE/JOB/LOCK.
- **Testing**: Docker for YDB validation. `uv` for Python execution.
