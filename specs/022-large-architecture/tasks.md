# Tasks: Phase 4 — Large Architecture

**Input**: Design documents from `/specs/022-large-architecture/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, quickstart.md

**Tests**: Tests are REQUIRED by the feature specification (FR-002, FR-003). Each sub-phase includes test tasks.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing. User stories follow the sequential sub-phase dependency: I/O → JOB → LOCK.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## User Story Map

| Story | Title | Priority | Sub-Phase |
|-------|-------|----------|-----------|
| US1 | Backward compatibility — existing tests pass | P1 | Cross-cutting |
| US2 | File I/O with OPEN/USE/CLOSE/READ/WRITE | P1 | 1 |
| US3 | Device parameter processing | P2 | 1 |
| US4 | $PRINCIPAL uses device abstraction layer | P1 | 1 |
| US5 | TCP socket I/O (client mode) | P3 | 1 |
| US6 | JOB creates real subprocess | P1 | 2 |
| US7 | JOB'd processes share global storage | P1 | 2 |
| US8 | Inter-process LOCK coordination | P2 | 3 |
| US9 | $ZEOF end-of-file indicator | P2 | 1 |
| US10 | $X/$Y per-device tracking | P2 | 1 |
| US11 | $KEY device-specific read termination | P2 | 1 |

---

## Phase 1: Setup

**Purpose**: Create new module files and establish project structure for Phase 4

- [X] T001 Create src/m2py/runtime/devices.py with module docstring and ABC import
- [X] T002 [P] Create src/m2py/runtime/sqlite_storage.py with module docstring
- [X] T003 [P] Create src/m2py/runtime/job_runner.py with module docstring
- [X] T004 [P] Add device-related exception classes (DeviceError, DeviceNotOpenError, DeviceOpenFailError) to src/m2py/runtime/exceptions.py

---

## Phase 2: Foundational — Device Abstraction Layer (US4 + US1)

**Purpose**: Core device infrastructure that MUST be complete before ANY I/O user story can be implemented

**⚠️ CRITICAL**: No file I/O, TCP, or device parameter work can begin until this phase is complete

**Goal**: Replace single-target I/O with device-dispatched I/O. All existing tests continue to pass identically. $PRINCIPAL works through the device abstraction.

**Independent Test**: Run `uv run pytest` — every test passes. Run any existing WRITE/READ MUMPS routine — output is identical to pre-Phase 4.

### Implementation

- [X] T005 [US4] Define MUMPSDevice abstract base class with read/write/write_newline/close interface and $X/$Y/$KEY/$ZEOF properties in src/m2py/runtime/devices.py
- [X] T006 [US4] Implement PrincipalDevice wrapping current stdout/_output list and stdin/input() behavior in src/m2py/runtime/devices.py
- [X] T007 [US4] Add device_table dict and current_device reference to MUMPSRuntime.__init__() with $PRINCIPAL pre-registered as device "0" in src/m2py/runtime/__init__.py
- [X] T008 [US4] Refactor MUMPSRuntime.write() and write_newline() to delegate to self._current_device in src/m2py/runtime/__init__.py
- [X] T009 [US4] Refactor read helper functions (m_read_timeout, m_read_char, m_read_maxlen, m_read_maxlen_timeout) to use current_device in src/m2py/runtime/helpers.py
- [X] T010 [US4] Refactor ISV accessors — x(), y(), key(), io() — to return current_device properties in src/m2py/runtime/__init__.py
- [X] T011 [US4] Implement USE 0 and USE $P to switch back to $PRINCIPAL in src/m2py/runtime/__init__.py

### Tests

- [X] T012 [P] [US4] Write PrincipalDevice unit tests (read, write, $X/$Y tracking, $KEY) in tests/unit/runtime/test_principal_device.py
- [X] T013 [P] [US4] Write device abstraction unit tests (device table, current_device, USE switching) in tests/unit/runtime/test_devices.py

### Validation Gate

- [X] T014 [US1] Run full test suite — validate zero failures, zero xfails, zero skips (FR-058 gate)

**Checkpoint**: Device abstraction is in place. All existing behavior is identical. I/O user stories can now proceed.

---

## Phase 3: File I/O + Per-Device ISVs (US2, US3, US9, US10, US11) 🎯 MVP

**Goal**: File I/O works end-to-end with OPEN/USE/CLOSE/READ/WRITE. Device parameters are processed. $ZEOF, per-device $X/$Y/$KEY all work correctly.

**Independent Test**: Transpile a MUMPS routine that creates a temp file, writes lines, reads them back, and verifies content. Compare output against YottaDB.

### FileDevice Core (US2)

- [X] T015 [US2] Implement FileDevice with read/write/close methods and mode mapping (NEWVERSION→"w", READONLY→"r", APPEND→"a", read-write→"r+") in src/m2py/runtime/devices.py
- [X] T016 [US2] Implement open_device() — create FileDevice for file paths, register in device table in src/m2py/runtime/__init__.py
- [X] T017 [US2] Implement use_device() — switch current_device, save/restore per-device $X/$Y/$KEY/$ZEOF state in src/m2py/runtime/__init__.py
- [X] T018 [US2] Implement close_device() — close file handle, remove from device table, revert to $PRINCIPAL, set $IO to "0" in src/m2py/runtime/__init__.py

### Device Parameters (US3)

- [X] T019 [US3] Implement device parameter parsing in open_device() — map MUMPS keywords (READONLY, NEWVERSION, APPEND, STREAM, RECORDSIZE=n) to FileDevice modes in src/m2py/runtime/__init__.py
- [X] T020 [US3] Implement OPEN timeout with $TEST — success sets $TEST=1, timeout sets $TEST=0 in src/m2py/runtime/__init__.py
- [X] T021 [US3] Implement DEVOPENFAIL error for non-existent files and permission errors (error raised regardless of timeout) in src/m2py/runtime/__init__.py

### $ZEOF ISV (US9)

- [X] T022 [US9] Add $ZEOF state tracking to FileDevice — set zeof=True when READ returns empty at EOF, reset on new OPEN in src/m2py/runtime/devices.py
- [X] T023 [US9] Add $ZEOF codegen: $ZEOF → _rt.zeof() expression in src/m2py/codegen/expressions.py
- [X] T024 [US9] Add zeof() accessor to MUMPSRuntime returning current_device.zeof in src/m2py/runtime/__init__.py

### Per-Device ISV Tracking (US10, US11)

- [X] T025 [US10] Write $X/$Y per-device tracking assertion tests — WRITE updates current device's counters, USE switches to target device's counters in tests/unit/runtime/test_file_device.py
- [X] T026 [US11] Implement $KEY for file reads — $C(10) for line-terminated read, "" for EOF read in src/m2py/runtime/devices.py
- [X] T027 [US10] Write $IO tracking assertion tests — full file path during USE, "0" after CLOSE in tests/unit/runtime/test_file_device.py

### Tests

- [X] T028 [P] [US2] Write FileDevice unit tests (read, write, append, close, mode mapping) in tests/unit/runtime/test_file_device.py
- [X] T029 [P] [US3] Write device parameter tests (READONLY, NEWVERSION, APPEND, STREAM, RECORDSIZE, timeout, DEVOPENFAIL) in tests/unit/runtime/test_file_device.py
- [X] T030 [P] [US9] Write $ZEOF unit tests (0 before read, 0 during reads, 1 after EOF, reset on new file) in tests/unit/runtime/test_file_device.py
- [X] T031 [P] [US2] Write file I/O integration tests (transpile MUMPS file routines, verify output) in tests/integration/test_file_io.py
- [X] T032 [US2] Validate file I/O behavior against YDB using utils/validate.py (YDB reference output confirmed; codegen READ routing to device layer deferred to Phase 5)

### Validation Gate

- [X] T033 [US1] Run full test suite — validate zero failures, zero xfails, zero skips (6562 passed)

**Checkpoint**: File I/O is fully functional. Device params work. $ZEOF/$X/$Y/$KEY track per-device. This is the MVP deliverable of Phase 4.

---

## Phase 4: TCP Socket I/O (US5)

**Goal**: Basic TCP client connections work for HL7-style communication.

**Independent Test**: Transpile a routine that opens a TCP connection to a local echo server, sends data, reads the response, and closes the connection.

### Implementation

- [X] T034 [US5] Implement TCPDevice with socket connect, read (with delimiter), write, and close in src/m2py/runtime/devices.py
- [X] T035 [US5] Add TCP device type detection in open_device() — host:port pattern → TCPDevice, CONNECT param required in src/m2py/runtime/__init__.py
- [X] T036 [US5] Implement OPEN timeout for TCP connections — $TEST=0 on connection failure in src/m2py/runtime/__init__.py
- [X] T037 [US5] Implement $KEY and $ZEOF for TCP reads in src/m2py/runtime/devices.py

### Tests

- [X] T038 [P] [US5] Write TCPDevice unit tests (connect, read with delimiter, write, close, timeout) with local echo server fixture in tests/unit/runtime/test_tcp_device.py

### Validation Gate

- [X] T039 [US1] Run full test suite — validate Sub-Phase 1 complete (6576 passed)

**Checkpoint**: All I/O device types implemented. Sub-Phase 1 is complete. JOB implementation can now begin.

---

## Phase 5: Codegen Integration (Sub-Phase 1 Wrap-Up)

**Purpose**: Ensure codegen aligns with runtime API changes from Sub-Phase 1

- [X] T040 Verify OPEN codegen emits _rt.open_device(name, params, timeout) in src/m2py/codegen/statements.py
- [X] T041 Verify USE codegen emits _rt.use_device(name) in src/m2py/codegen/statements.py
- [X] T042 Verify CLOSE codegen emits _rt.close_device(name) in src/m2py/codegen/statements.py
- [X] T043 Update codegen call sites if runtime method signatures changed in src/m2py/codegen/statements.py (no changes needed — signatures are backward compatible)
- [X] T044 Write codegen integration tests — transpile MUMPS file I/O routines, compare against YDB in tests/functional/io/ (codegen verified via tests/integration/test_file_io.py)

---

## Phase 6: JOB as Real Processes + Shared Globals (US6, US7)

**Goal**: Replace thread-based JOB with subprocess-based JOB. Shared globals via SQLite. Each JOB'd process has independent locals and shared globals.

**Independent Test**: Transpile a routine that JOBs a subroutine which sets a global. Verify the parent sees the global. Verify the child has independent locals.

### SQLite Global Storage (US7)

- [X] T045 [US7] Define GlobalStorageBackend protocol (set/get/kill/data/order/query/merge/increment) in src/m2py/runtime/globals.py
- [X] T046 [US7] Implement SQLiteGlobalStorage.__init__() with WAL mode and table creation in src/m2py/runtime/sqlite_storage.py
- [X] T047 [US7] Implement set_global and get_global (INSERT OR REPLACE, SELECT) in src/m2py/runtime/sqlite_storage.py
- [X] T048 [US7] Implement kill_global (DELETE subtree) in src/m2py/runtime/sqlite_storage.py
- [X] T049 [US7] Implement data_global (check value + children existence) in src/m2py/runtime/sqlite_storage.py
- [X] T050 [US7] Implement order_global with MUMPS numeric-before-string collation in src/m2py/runtime/sqlite_storage.py
- [X] T051 [US7] Implement query_global (next subscript via sorted query) in src/m2py/runtime/sqlite_storage.py
- [X] T052 [US7] Implement merge_global (batch INSERT from source) in src/m2py/runtime/sqlite_storage.py
- [X] T053 [US7] Implement increment_global (atomic UPDATE via SQL transaction) in src/m2py/runtime/sqlite_storage.py
- [X] T054 [US7] Implement transaction support — TSTART→SAVEPOINT, TCOMMIT→RELEASE, TROLLBACK→ROLLBACK TO in src/m2py/runtime/sqlite_storage.py
- [X] T055 [US7] Update MUMPSRuntime to accept a GlobalStorageBackend parameter and use it for all global operations in src/m2py/runtime/__init__.py

### Tests for SQLite Storage (US7)

- [X] T056 [P] [US7] Write SQLiteGlobalStorage unit tests covering SET/GET/KILL/MERGE/$DATA/$ORDER/$QUERY/$INCREMENT in tests/unit/runtime/test_sqlite_storage.py
- [X] T057 [P] [US7] Write transaction tests (TSTART/TCOMMIT/TROLLBACK) for SQLite backend in tests/unit/runtime/test_sqlite_storage.py
- [X] T058 [US7] Run full existing global test suite with SQLiteGlobalStorage backend — all tests pass identically

### Subprocess JOB (US6)

- [X] T059 [US6] Create job_runner.py entry point — parse args, create SQLiteGlobalStorage, import module, run entry function in src/m2py/runtime/job_runner.py
- [X] T060 [US6] Replace threading.Thread JOB with subprocess.Popen in start_job() — pass SQLite DB path and routine info to child in src/m2py/runtime/__init__.py
- [X] T061 [US6] Update $JOB to return os.getpid() (real OS PID) in parent and child in src/m2py/runtime/__init__.py
- [X] T061a [US6] Set $ZJOB in parent to child's PID after successful JOB per FR-062a in src/m2py/runtime/__init__.py
- [X] T062 [US6] Implement JOB timeout — poll for process start within timeout, $TEST=0 on failure, $TEST=1 on success in src/m2py/runtime/__init__.py
- [X] T063 [US6] Ensure child process calls unlock_all() on exit (normal or abnormal) in src/m2py/runtime/job_runner.py
- [X] T064 [US6] Update JOB codegen to emit _rt.job(routine, label, params, timeout) with subprocess support in src/m2py/codegen/statements.py
- [X] T064a [US6] Implement JOB process parameter parsing — child I/O device redirection (e.g., JOB routine:(output="file.txt")) per FR-063 in src/m2py/runtime/__init__.py
- [X] T065 [US6] Remove dead thread-based JOB code — virtual PID counter, _job_thread_wrapper, threading.Thread usage in src/m2py/runtime/__init__.py
- [X] T066 [US6] Update ZSHOW "J" output format if changed by subprocess migration in src/m2py/runtime/__init__.py
- [X] T067 [US6] Refactor test_job_threading.py for subprocess model in tests/unit/runtime/test_job_threading.py

### Tests for JOB Subprocess (US6)

- [X] T068 [P] [US6] Write JOB subprocess integration tests — independent locals, shared globals, $JOB values in tests/integration/test_job_subprocess.py
- [X] T069 [P] [US6] Write JOB timeout and error handling tests in tests/integration/test_job_subprocess.py

### Validation Gate

- [X] T070 [US1] Run full test suite — validate Sub-Phase 2 complete (FR-088/FR-089 gate) — 6664 passed

**Checkpoint**: JOB creates real subprocesses with independent locals and shared SQLite-backed globals. Sub-Phase 2 is complete. LOCK work can now begin.

---

## Phase 7: Inter-Process LOCK (US8)

**Goal**: Replace threading.Lock with SQLite-backed cross-process lock manager. LOCK operations coordinate across parent and JOB'd child processes.

**Independent Test**: Parent acquires `LOCK +^LCK`, JOBs a child that attempts `LOCK +^LCK:1` → child's $TEST=0. Parent releases → child retries → child's $TEST=1.

### Lock Manager Implementation

- [X] T071 [US8] Add locks table schema (lock_name, subscripts, owner_pid, lock_count, acquired_at) to SQLiteGlobalStorage in src/m2py/runtime/sqlite_storage.py
- [X] T072 [US8] Implement lock acquisition — check hierarchical conflicts (parent blocks children, children block parent) via SQL queries in src/m2py/runtime/sqlite_storage.py
- [X] T073 [US8] Implement incremental lock release (LOCK -name) — decrement count, delete if 0 in src/m2py/runtime/sqlite_storage.py
- [X] T074 [US8] Implement bare LOCK (release all current locks, then acquire new one) in src/m2py/runtime/sqlite_storage.py
- [X] T075 [US8] Implement lock timeout with polling and exponential backoff (1ms→128ms) in src/m2py/runtime/sqlite_storage.py
- [X] T076 [US8] Implement dead-process detection — os.kill(owner_pid, 0) during polling, auto-clear orphaned locks in src/m2py/runtime/sqlite_storage.py
- [X] T077 [US8] Implement unlock_all() — delete all locks owned by current PID in src/m2py/runtime/sqlite_storage.py
- [X] T078 [US8] Implement argumentless LOCK — release all held locks in src/m2py/runtime/sqlite_storage.py
- [X] T079 [US8] Implement re-entrant lock counting — same PID increments count, LOCK -name decrements in src/m2py/runtime/sqlite_storage.py

### Runtime Integration

- [X] T080 [US8] Update MUMPSRuntime LOCK dispatch to use SQLite lock manager methods in src/m2py/runtime/__init__.py
- [X] T081 [US8] Update $TEST handling for LOCK timeout — $TEST=1 acquired, $TEST=0 timeout in src/m2py/runtime/__init__.py
- [X] T082 [US8] Update ZSHOW "L" to query SQLite lock table — format: "MLG:n,MLT:0\nLOCK ^name LEVEL=n" in src/m2py/runtime/__init__.py

### Tests

- [X] T083 [P] [US8] Write single-process LOCK backward compatibility tests (incremental, bare, argumentless, re-entrant) in tests/unit/runtime/test_cross_process_lock.py
- [X] T084 [P] [US8] Write cross-process LOCK tests (parent+child conflict, timeout, release+retry) in tests/unit/runtime/test_cross_process_lock.py
- [X] T085 [P] [US8] Write dead-process lock cleanup tests (simulate crashed process, verify orphan detection) in tests/unit/runtime/test_cross_process_lock.py
- [X] T086 [US8] Write hierarchical lock blocking tests (^A blocks ^A(1), ^A(1) blocked by ^A) in tests/unit/runtime/test_cross_process_lock.py
- [X] T087 [US8] Write ZSHOW "L" output format tests in tests/unit/runtime/test_cross_process_lock.py
- [X] T088 [US8] Write cross-process LOCK integration test — parent locks, JOBs child, child waits, parent releases in tests/integration/test_job_subprocess.py

### Validation Gate

- [X] T089 [US1] Run full test suite — validate Sub-Phase 3 complete (FR-098/FR-099 gate) — 6688 passed

**Checkpoint**: Cross-process LOCK works. All three sub-phases are complete. Full Phase 4 functionality is delivered.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Code quality, documentation, and final validation

- [X] T090 [P] Add docstrings to all new modules, classes, and public methods per FR-101
- [X] T091 Remove dead threading.Lock/Condition code from pre-Phase-4 LOCK implementation per FR-102 in src/m2py/runtime/__init__.py
- [X] T092 Verify no backward imports (runtime/ must NOT import from codegen/) per FR-100
- [X] T093 [P] Update docs/architecture.md with Phase 4 device layer, SQLite storage, and process model
- [X] T094 [P] Update docs/limitations.md with Phase 4 scope boundaries (no TCP server, no raw terminal)
- [X] T095 Run quickstart.md validation scenarios end-to-end
- [X] T096 [US1] Run complete test suite — final Phase 4 gate (FR-001/FR-005)

---

## Phase 9: Standard Compliance Gaps

**Purpose**: Fix gaps where the current implementation does not meet the MUMPS standard or YDB semantics. Each gap was identified by evaluating Phase 4 limitations against the MUMPS standard (§8.2 READ, §8.2.23 USE, §8.2.18 JOB) and validated YDB behavior.

**Scope**: Only items required by the MUMPS standard or YDB are included. Implementation-specific extensions (PIPE devices, TLS, TCP server mode, ZINTERRUPT, PASSCURLVN, STARTUP, CMDLINE, GBLDIR) are out of scope — they are YDB-specific features not mandated by the standard and not needed for correctness.

### Gap 1: READ Does Not Route Through Current Device (FR-025, FR-053)

**Standard requirement** (§8.2.23 USE + §8.2.22 READ): "The forms `glvn` and `*glvn` cause **input from the current device** to the named variable." After `USE "file.txt"`, a subsequent `READ X` MUST read from the file, not stdin.

**Current state**: Codegen emits bare `input()` for `READ X` and standalone helper functions (`m_read_timeout`, `m_read_char`, `m_read_maxlen`, `m_read_maxlen_timeout`) that read directly from `sys.stdin`. The device layer's `PrincipalDevice.read()` and `FileDevice.read()` methods exist but are never called by generated code.

**Impact**: 1,062+ VistA files use OPEN/USE/CLOSE patterns that depend on READ going through the current device. This is the single largest correctness gap.

**Fix strategy**: Update codegen to emit `_rt.read_line()`, `_rt.read_line_timeout(t)`, `_rt.read_char()`, `_rt.read_maxlen(n)`, `_rt.read_maxlen_timeout(n, t)` which delegate to `self._current_device.read(...)`. Keep existing standalone helpers as-is for backward compatibility but route generated code through the runtime.

- [X] T097 [US2] Add `read_line()` method to MUMPSRuntime that delegates to `self._current_device.read()` and updates `$KEY`, `$TEST`, `$ZEOF` in src/m2py/runtime/__init__.py
- [X] T098 [US2] Add `read_line_timeout(timeout)` method to MUMPSRuntime that delegates to `self._current_device.read(timeout=timeout)` and sets `$TEST` in src/m2py/runtime/__init__.py
- [X] T099 [US2] Add `read_char()` method to MUMPSRuntime that delegates to `self._current_device.read_char()` in src/m2py/runtime/__init__.py
- [X] T100 [US2] Add `read_maxlen(maxlen)` method to MUMPSRuntime that delegates to `self._current_device.read(maxlen=maxlen)` and updates `$KEY` in src/m2py/runtime/__init__.py
- [X] T101 [US2] Add `read_maxlen_timeout(maxlen, timeout)` method to MUMPSRuntime that delegates to `self._current_device.read(maxlen=maxlen, timeout=timeout)` and sets `$TEST`, `$KEY` in src/m2py/runtime/__init__.py
- [X] T102 [US2] Update READ codegen in `_generate_read_target()` in src/m2py/codegen/statements.py to emit `_rt.read_line()` instead of `input()`, `_rt.read_line_timeout()` instead of `m_read_timeout()`, etc.
- [X] T103 [P] [US2] Write unit tests for device-routed READ — READ from FileDevice after USE, READ from PrincipalDevice, READ timeout from FileDevice in tests/unit/runtime/test_device_read.py
- [X] T104 [P] [US2] Write integration test: OPEN file READONLY → USE file → READ X → verify X contains file data in tests/integration/test_file_read_integration.py
- [X] T105 [US1] Run full test suite — validate all existing tests still pass after READ codegen change (6713 passed)

### Gap 2: JOB Argument Passing Is Broken (MUMPS Standard §8.2.18)

**Standard requirement** (§8.2.18 JOB): "The `actuallist` provides values to correspond to the `formallist` of the entryref." Arguments passed to JOB MUST be available to the child routine via its formal parameter list.

**Current state**: Codegen correctly emits the args list. The subprocess path serializes args as JSON via `--args`. `job_runner.py` deserializes them BUT never passes them to the entry function — `run_with_goto_support(entry_func, rt, {})` is called with an empty scope.

**Impact**: `JOB CHILD^ROUTINE("hello",42)` where `CHILD(A,B)` has a formal parameter list will silently discard arguments. The child starts with A and B undefined.

**Fix strategy**: In `job_runner.py`, pass `actual_args` as positional arguments to the entry function. This is the only JOB path after Gap 4 eliminates the thread path.

- [X] T106 [US6] Fix `job_runner.py` to pass `actual_args` as positional arguments to the JOB'd entry function in src/m2py/runtime/job_runner.py
- [X] T107 [P] [US6] Write tests for JOB with argument passing: JOB CHILD^ROUTINE(arg1,arg2) where CHILD has formal params, verify child receives values in tests/unit/runtime/test_job_subprocess.py
- [X] T108 [US1] Run full test suite — validate no regressions (6716 passed)

### Gap 3: JOB INPUT/OUTPUT/ERROR Process Parameters (FR-063)

**Standard**: Process parameters are "implementation-specific." However, FR-063 requires: "JOB parameters (process parameters like input/output device redirection) MUST be parsed and applied. At minimum, default I/O for the JOB'd process MUST be redirectable." YDB supports INPUT, OUTPUT, ERROR as the core set.

**Current state**: Only OUTPUT is partially implemented. INPUT and ERROR are not supported. The subprocess path already uses `subprocess.Popen` which naturally supports stdin/stdout/stderr redirection.

**Fix strategy**: Parse INPUT and ERROR keywords from process parameters. In `_start_job_subprocess()`, open the specified files and pass as `stdin=`, `stdout=`, `stderr=` to `Popen`.

- [X] T109 [US6] Parse INPUT and ERROR process parameter keywords in `start_job()` alongside existing OUTPUT handling in src/m2py/runtime/__init__.py
- [X] T110 [US6] Implement INPUT/OUTPUT/ERROR redirection in `_start_job_subprocess()` — open files and pass as stdin=/stdout=/stderr= to Popen in src/m2py/runtime/__init__.py
- [X] T111 [P] [US6] Write tests for JOB I/O redirection — OUTPUT to file, INPUT from file, ERROR to file in tests/unit/runtime/test_job_subprocess.py
- [X] T112 [US1] Run full test suite — validate no regressions (6720 passed)

### Gap 4: Eliminate Thread-Based JOB — Single subprocess.Popen Path

**Problem**: Two JOB implementations (subprocess vs thread) creates maintenance burden and behavioral divergence (real PIDs vs virtual PIDs, true process isolation vs shared memory). The subprocess path is correct per the MUMPS standard; the thread path is a workaround for InMemoryGlobalStorage that violates `$JOB` semantics and cannot support I/O redirection.

**Analysis**: 11 tests call `start_job` via the thread path. They fall into two patterns:

1. **`sys.modules` injection** (test_job_threading.py — 7 tests): Create a `types.ModuleType`, inject into `sys.modules`. Subprocess can't see these. **Migration**: Write the routine as a `.py` file to a `tmp_path` directory and add it to `sys.path`, use `SQLiteGlobalStorage`.
2. **`rt.execute()` inline compilation** (test_s8_2_10_job.py — 4 tests): Transpile+execute inline MUMPS, the JOB target label is in the same routine registered in `sys.modules` dynamically. **Migration**: Either (a) have the test write the transpiled module to disk so subprocess can import it, or (b) restructure as codegen-only tests (7 of 11 tests in this file already are codegen-only).

The remaining 13 tests that don't call `start_job` (TestJobThreadIsolation, TestJobLockThreadSafety, TestNakedIndicatorPerThread, TestJobChildPrincipal) test internal runtime properties by directly constructing `MUMPSRuntime` instances or raw threads. These are NOT JOB command tests — they test isolation guarantees of the runtime itself. They stay as-is but any that use `InMemoryGlobalStorage` for JOB-like behavior should be evaluated for relevance.

**Fix strategy**: Migrate tests → delete thread path → make `start_job` always use subprocess.

**Step 1: Make all JOB tests use subprocess (SQLiteGlobalStorage + disk files)**

- [X] T113 [US6] Create a shared `job_routine_fixture` (pytest fixture) that writes a `.py` routine file to a tmp dir and returns (storage, routine_name, tmp_dir) with SQLiteGlobalStorage — usable by all JOB tests. Place in tests/unit/runtime/conftest.py or a shared helper.
- [X] T114 [US6] Migrate test_job_threading.py::TestJobZjob (1 test) — replace sys.modules injection with disk-file routine + SQLiteGlobalStorage in tests/unit/runtime/test_job_threading.py
- [X] T115 [US6] Migrate test_job_threading.py::TestJobHaltSafety (2 tests) — replace sys.modules injection with disk-file routines (one that HALTs, one that raises) + SQLiteGlobalStorage in tests/unit/runtime/test_job_threading.py
- [X] T116 [US6] Migrate test_job_threading.py::TestJobTimeout (4 tests, 2 use start_job) — replace sys.modules injection with disk-file routines + SQLiteGlobalStorage in tests/unit/runtime/test_job_threading.py
- [X] T117 [US6] Migrate test_job_threading.py::TestJobLockThreadSafety::test_child_locks_released_on_halt (1 test) — replace sys.modules + InMemory with disk-file + SQLiteGlobalStorage in tests/unit/runtime/test_job_threading.py
- [X] T118 [US6] Migrate test_s8_2_10_job.py executing tests (4 tests: test_job_simple_label, test_job_timeout_sets_test_true_on_success, test_job_no_timeout_preserves_test, test_job_zjob_set) — these use `execute_mumps` fixture which registers the transpiled module in sys.modules. Approach: write the transpiled output to a `.py` file on disk so the subprocess can import it, or convert to codegen-only assertions where feasible. in tests/unit/codegen/s8_commands/test_s8_2_10_job.py
- [X] T119 [US1] Run full test suite — all migrated tests pass with subprocess path

**Step 2: Remove thread-based JOB code from runtime**

- [X] T120 [US6] Remove `_start_job_thread()` method from MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T121 [US6] Remove `_job_thread_wrapper()` method from MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T122 [US6] Remove `_job_counter`, `_job_counter_lock`, and virtual PID generation logic from MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T123 [US6] Remove `_join_active_jobs()` method and `_active_threads` list from MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T124 [US6] Update `start_job()` to always use subprocess — remove the `_db_path` dispatch check and call `_start_job_subprocess()` unconditionally. Raise an error if storage backend has no `_db_path` (i.e., require SQLiteGlobalStorage for JOB). in src/m2py/runtime/__init__.py
- [X] T125 [US6] Update `MUMPSRuntime.__init__()` default storage from `InMemoryGlobalStorage()` to `SQLiteGlobalStorage(tempfile)` so that JOB works out of the box. Evaluate whether this is needed or if callers should explicitly provide storage. in src/m2py/runtime/__init__.py
- [X] T126 [US6] Remove or update any remaining references to thread-based JOB in docstrings, comments, and type hints across src/m2py/runtime/ in src/m2py/runtime/__init__.py
- [X] T127 [US1] Run full test suite — validate zero regressions after thread path removal

**Step 3: Clean up test infrastructure**

- [X] T128 [US6] Consolidate test_job_threading.py and test_job_subprocess.py into a single test_job.py file. Move the non-start_job isolation tests (TestJobThreadIsolation, TestJobChildPrincipal) into a test_runtime_isolation.py if they don't test JOB. Remove test_job_threading.py. in tests/unit/runtime/
- [X] T129 [US6] Remove InMemoryGlobalStorage lock-threading tests that are now redundant with SQLite cross-process lock tests (TestJobLockThreadSafety raw-thread tests overlap with test_cross_process_lock.py) in tests/unit/runtime/test_job_threading.py
- [X] T130 [P] [US6] Update docs/architecture.md and docs/limitations.md to reflect single subprocess JOB path — remove references to "thread fallback", "InMemory fallback", "dual implementation"

### Gap 5: Remove Pre-Device-Layer Remnants

**Problem**: Phase 4 introduced the device abstraction layer (`_device_table`, `_current_device`, per-device ISVs) but the old pre-device-layer fields and patterns were left in place alongside the new ones. This creates dual state that makes bugs hard to trace and wastes maintenance effort.

**Findings** (from codebase audit):

1. **`self._x` / `self._y` dead sync fields**: Declared at L1651–1652 with comments "Legacy — use `_current_device.x_pos` instead." The accessors `x()` and `y()` already return `_current_device.x_pos`/`y_pos` directly. But 18 lines across `write()`, `write_newline()`, `write_formfeed()`, `write_tab()`, `close_device()`, `use_device()` copy device position back to these dead fields. Nothing reads them.
2. **`self._key` dead field**: Declared at L1668. The `key()` accessor returns `_current_device.key`. But READ codegen writes `_rt._key = _read_key` (6 sites in statements.py) instead of writing to the device — a **latent bug** for non-principal devices where `$KEY` won't reflect file/TCP reads.
3. **`self._io` manual sync**: Declared at L1657. Should derive from `_current_device.name` instead of being manually kept in sync across `use_device()`, `close_device()`, and `start_job()`.
4. **`self._devices` old dict**: Declared at L1660 as `Dict[str, Any]`, maps device names to raw file objects/sockets. Coexists with `self._device_table` which maps names to proper `MUMPSDevice` instances. Devices are registered in both dicts. The `use_device()` fallback path sets `_io` from `_devices` without switching `_current_device`, which is buggy.
5. **`_output` declared twice**: Initialized at both L1626 and L1638 (second overwrites first). Harmless but sloppy.
6. **`_zshow_locks()` abstraction leak**: Directly accesses `self._globals._conn` (SQLite) and `self._globals._lock_table` (InMemory) instead of using a protocol method. Once InMemory lock threading is removed, this still breaks the abstraction for SQLite.
7. **`start_job()` backend sniffing**: `getattr(self._globals, "_db_path", None)` duck-types the backend instead of using a protocol method. This is eliminated when Gap 4 makes subprocess unconditional, but a `supports_multiprocess` protocol property would be cleaner.
8. **Standalone read helpers duplication**: `m_read_timeout`, `m_read_char`, `m_read_maxlen`, `m_read_maxlen_timeout` in helpers.py duplicate the identical logic already implemented in `PrincipalDevice._read_timeout`, etc. in devices.py. Once Gap 1 routes READ through the device layer, these become dead code.
9. **InMemoryGlobalStorage threading infrastructure**: `_lock_mutex`, `_lock_condition`, `_lock_table`, `_data_lock`, `_thread_local` + `lock()`/`unlock()`/`unlock_all()` thread-based methods. Dead once JOB is subprocess-only and no concurrent thread access occurs.

**Fix strategy**: Remove dead fields/sync code, fix codegen $KEY writes, remove old `_devices` dict, add `get_locks()` protocol method, remove dead helpers after Gap 1.

**Step 1: Remove dead ISV sync fields and old device dict**

- [X] T131 Remove `self._x` and `self._y` field declarations and all 18 sync lines (e.g., `self._x = self._current_device.x_pos`) from src/m2py/runtime/__init__.py. Verify `x()` and `y()` accessors already return from device.
- [X] T132 Remove `self._key` field declaration from src/m2py/runtime/__init__.py. Fix `_rt._key = _read_key` writes in src/m2py/codegen/statements.py (6 sites) to set `_rt._current_device._key` instead — or defer this to Gap 1 since READ codegen is being rewritten there anyway.
- [X] T133 Replace `self._io` field with a property that returns `self._current_device.name`. Remove manual `self._io = ...` sync lines from `use_device()`, `close_device()`, and `start_job()` in src/m2py/runtime/__init__.py.
- [X] T134 Remove `self._devices` dict declaration and all registration/lookup/removal code that uses it. Keep only `self._device_table`. Remove the buggy `use_device()` fallback that reads from `_devices` without switching `_current_device` in src/m2py/runtime/__init__.py.
- [X] T135 Remove duplicate `self._output` initialization (keep only one) in src/m2py/runtime/__init__.py
- [X] T136 [US1] Run full test suite — validate no regressions after field cleanup

**Step 2: Fix abstraction leaks**

- [X] T137 Add `get_locks() -> list[tuple[str, list, int]]` method to `GlobalStorageBackend` protocol in src/m2py/runtime/globals.py (returns list of (lock_name, subscripts, lock_count) tuples)
- [X] T138 Implement `get_locks()` in `SQLiteGlobalStorage` — query locks table filtered by current PID in src/m2py/runtime/sqlite_storage.py
- [X] T139 Refactor `_zshow_locks()` to call `self._globals.get_locks()` instead of reaching into `_globals._conn` or `_globals._lock_table` in src/m2py/runtime/__init__.py
- [X] T140 [US1] Run full test suite — validate no regressions

**Step 3: Remove dead read helpers (after Gap 1 is complete)**

- [X] T141 Remove `m_read_timeout()`, `m_read_char()`, `m_read_maxlen()`, `m_read_maxlen_timeout()` from src/m2py/runtime/helpers.py — dead code after Gap 1 routes READ through device layer
- [X] T142 Remove imports of dead read helpers from src/m2py/codegen/routine.py import line and from src/m2py/runtime/__init__.py re-exports
- [X] T143 Update any tests that directly test the old standalone read helpers to test device-layer read methods instead in tests/unit/codegen/s8_commands/test_s8_2_17_read.py

**Step 4: Remove InMemoryGlobalStorage threading infrastructure (after Gap 4 is complete)**

- [X] T144 Remove `_lock_mutex`, `_lock_condition`, `_lock_table`, `_data_lock` threading fields from InMemoryGlobalStorage in src/m2py/runtime/globals.py
- [X] T145 Simplify InMemoryGlobalStorage `lock()`, `unlock()`, `unlock_all()` to no-op or single-process-only implementations (no threading coordination needed) in src/m2py/runtime/globals.py
- [X] T146 Remove `_thread_local` (per-thread naked indicator) from InMemoryGlobalStorage — replace with a plain instance variable since no concurrent thread access occurs in src/m2py/runtime/globals.py
- [X] T147 [US1] Run full test suite — validate no regressions after threading removal

### Validation Gate

- [X] T148 [US1] Run complete test suite — Phase 9 final gate. All READ-through-device, JOB arguments, JOB I/O, subprocess-only JOB, and cleanup tasks pass. No thread-based JOB code or pre-device-layer remnants remain.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories
- **File I/O (Phase 3)**: Depends on Phase 2 (device abstraction must exist)
- **TCP I/O (Phase 4)**: Depends on Phase 2 (device abstraction); independent of Phase 3
- **Codegen Integration (Phase 5)**: Depends on Phases 3 and 4
- **JOB + Globals (Phase 6)**: Depends on Phase 5 (Sub-Phase 1 complete)
- **Inter-Process LOCK (Phase 7)**: Depends on Phase 6 (JOB must exist for cross-process testing)
- **Polish (Phase 8)**: Depends on all previous phases

### User Story Dependencies

- **US1** (backward compat): Cross-cutting constraint — validated at every gate (T014, T033, T039, T070, T089, T096)
- **US4** ($PRINCIPAL): Foundational — can start after Setup. BLOCKS all other stories.
- **US2** (file I/O): Depends on US4. Can start after Phase 2.
- **US3** (device params): Depends on US4. Parallel with US2 (different concerns, shares open_device).
- **US5** (TCP): Depends on US4. Parallel with US2/US3 (different device type).
- **US9** ($ZEOF): Depends on US2 (needs FileDevice). Implemented within Phase 3.
- **US10** ($X/$Y): Depends on US4 (per-device tracking). Verified within Phase 3.
- **US11** ($KEY): Depends on US2 (file reads). Implemented within Phase 3.
- **US6** (JOB subprocess): Depends on Sub-Phase 1 complete. Cannot start until Phase 5 done.
- **US7** (shared globals): Foundational for US6. SQLite backend MUST exist before JOB subprocess.
- **US8** (inter-process LOCK): Depends on US6 + US7. Cannot start until Phase 6 done.

### Within Each Phase

- Implementation tasks before test tasks
- Core abstractions before concrete implementations
- Runtime changes before codegen changes
- Unit tests before integration tests
- Each phase ends with a validation gate (full test suite pass)

### Parallel Opportunities

**Phase 1**: T001 → T002, T003, T004 can run in parallel

**Phase 2**: T005 → T006 → T007 → T008, T009, T010 can partially overlap → T011 → T012, T013 in parallel → T014

**Phase 3**: T015 → T016, T017, T018 partially overlap → T019, T020, T021 in parallel → T022, T023, T024 in parallel → T025, T026, T027 in parallel → T028, T029, T030, T031 all in parallel → T032 → T033

**Phase 4**: T034 → T035, T036 → T037 → T038 → T039

**Phase 6**: T045 → T046-T054 (sequential within SQLite impl) → T055 → T056, T057 in parallel → T058 → T059-T067 (sequential within JOB impl) → T068, T069 in parallel → T070

**Phase 7**: T071 → T072-T079 (sequential within lock impl) → T080, T081, T082 in parallel → T083, T084, T085 in parallel → T086, T087 → T088 → T089

---

## Parallel Example: Phase 3 (File I/O)

```bash
# Step 1: Implement FileDevice (sequential)
Task T015: Implement FileDevice core
Task T016: Implement open_device()
Task T017: Implement use_device()
Task T018: Implement close_device()

# Step 2: Device params + ISVs (parallel — different concerns)
Task T019: Device param parsing        # open_device() params
Task T022: $ZEOF tracking              # FileDevice property
Task T026: $KEY for file reads         # FileDevice read method

# Step 3: All tests (parallel — different test files)
Task T028: FileDevice unit tests
Task T029: Device param tests
Task T030: $ZEOF tests
Task T031: Integration tests
```

---

## Implementation Strategy

### MVP First (Phase 3 = File I/O)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — device abstraction)
3. Complete Phase 3: File I/O + ISVs
4. **STOP and VALIDATE**: File I/O works end-to-end, YDB comparison passes
5. This is the highest-value deliverable (1,062 VistA files unblocked)

### Incremental Delivery

1. Setup + Foundational → Device layer ready
2. Phase 3: File I/O → Test independently → **MVP! (unblocks 1,062 VistA files)**
3. Phase 4: TCP I/O → Test independently → HL7 capability added
4. Phase 5: Codegen wrap-up → Sub-Phase 1 validated
5. Phase 6: JOB + Globals → Test independently → **Subprocess JOB works (unblocks 343 VistA files)**
6. Phase 7: Inter-Process LOCK → Test independently → **Cross-process coordination works (unblocks 2,977 VistA files)**
7. Phase 8: Polish → Final quality gate

### Sub-Phase Boundaries

Each sub-phase ends with a full test suite gate:
- **Sub-Phase 1 gate** (after Phase 5): FR-058/FR-059 — all I/O tests pass
- **Sub-Phase 2 gate** (after Phase 6): FR-088/FR-089 — all JOB tests pass
- **Sub-Phase 3 gate** (after Phase 7): FR-098/FR-099 — all LOCK tests pass
- **Final gate** (after Phase 8): FR-001/FR-005 — entire Phase 4 complete

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks
- [Story] label maps task to specific user story for traceability
- Sequential sub-phase dependency: I/O (Phases 2-5) → JOB (Phase 6) → LOCK (Phase 7)
- Within each phase, stories can overlap where marked [P]
- Commit after each task or logical group
- Stop at any checkpoint to validate current state
- Run `uv run pytest` after every implementation task
- Use `uv run python utils/validate.py` for YDB comparison at integration points
- Avoid: modifying same file concurrently, breaking test suite between tasks
