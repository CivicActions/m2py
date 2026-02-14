# Feature Specification: Phase 4 — Large Architecture

**Feature Branch**: `022-large-architecture`  
**Created**: 2026-02-12  
**Status**: Draft  
**Input**: User description: "Phase 4 Large Architecture — Implement I/O device management, JOB as real processes, and inter-process LOCK coordination"  
**Source**: [refactoring-plan.md](../refactoring-plan.md) — Phase 4 section

## Overview

Phase 4 is the final and most architecturally significant phase of M2PY's refactoring plan. It implements three deeply interdependent subsystems that together enable multi-process MUMPS operation and full I/O device support — capabilities essential for running VistA's Kernel infrastructure (TaskMan, file I/O, HL7 communication, device management).

Unlike Phases 1–3 (which focused on internal refactoring, consolidation, and adding features to an existing single-process runtime), Phase 4 introduces **new architectural layers**:

- **I/O Device Management (F-02):** A device abstraction layer replacing the current `$PRINCIPAL`-only I/O with support for file devices, TCP sockets, and device parameter processing — unlocking 1,062 VistA files that use OPEN/USE/CLOSE.
- **JOB as Real Processes (F-04):** Replacing thread-based JOB with true subprocess-based process creation, giving each JOB'd routine its own local variable space while sharing global storage — unlocking VistA's TaskMan (`^%ZTMS`, 343 VistA files).
- **Inter-Process LOCK (F-01):** Replacing in-process `threading.Lock` with a cross-process lock coordination mechanism, enabling the MUMPS LOCK command to work correctly across JOB'd processes — affecting 2,977 VistA files.
- **`$ZEOF` (F-12 remainder):** End-of-file flag for sequential file I/O, blocked on I/O device management — used by 13 VistA files.

These items are **sequential** — each unblocks the next. F-02 (I/O) must come first because F-04 (JOB) and F-01 (LOCK) depend on the device layer for process I/O, and `$ZEOF` is a device-layer feature. F-04 (JOB) must precede F-01 (inter-process LOCK) because inter-process locking only matters when separate processes exist.

The deliverables are:
- A new `runtime/devices.py` module with a `MUMPSDevice` abstraction and concrete implementations (`PrincipalDevice`, `FileDevice`, `TCPDevice`)
- A device table in `MUMPSRuntime` managing OPEN/USE/CLOSE lifecycle and device parameter processing
- Process-based JOB implementation using `subprocess` or `multiprocessing`, with shared global storage and independent local variable spaces
- A cross-process lock manager replacing `threading.Lock`, supporting lock timeout with `$TEST`, incremental lock/unlock, and lock escalation/de-escalation
- `$ZEOF` ISV support for sequential file I/O
- Updated codegen for OPEN, USE, CLOSE, READ, WRITE, and JOB commands to use the new device and process infrastructure
- Full device parameter parsing for MUMPS OPEN/USE commands

## Clarifications

### Session 2026-02-12

- Q: Which shared global storage backend should be used for cross-process globals (FR-071)? → A: SQLite file-backed database
- Q: Which lock manager implementation should be used for cross-process LOCK (FR-092)? → A: Shared lock table in SQLite, co-located with global storage
- Q: Which process creation mechanism should be used for JOB (FR-060)? → A: `subprocess.Popen` — child runs as separate Python interpreter
- Q: How should deadlock between LOCK'd processes be handled? → A: No automatic deadlock detection; LOCK without timeout blocks indefinitely (matches MUMPS standard and YottaDB behavior). Dead-process detection auto-clears orphaned locks.
- Q: Does OPEN with timeout on a non-existent file set $TEST=0? → A: No. YDB raises DEVOPENFAIL error regardless of timeout. Timeout only applies to waiting for a device that exists but is currently unavailable. FR-022 corrected.
- Q: Does YDB support ^$LOCK SSVN? → A: No. YDB uses ZSHOW "L" for lock introspection and LKE utility for admin. FR-097 updated to target ZSHOW "L" compatibility.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Transpiled MUMPS programs continue producing identical output for existing functionality (Priority: P1)

A developer transpiles any MUMPS routine through m2py. All previously working functionality — including console I/O, single-process LOCK, and existing JOB behavior — produces identical output. The full test suite passes.

**Why this priority**: Architectural changes to I/O, process management, and locking touch the most fundamental runtime operations. Breaking existing behavior would undermine all prior phases.

**Independent Test**: Run the full test suite (`uv run pytest`). Every test passes. YDB validation suite produces matching output.

**Acceptance Scenarios**:

1. **Given** the complete m2py test suite, **When** all Phase 4 changes are applied and `uv run pytest` is executed, **Then** 100% of tests pass with zero failures, zero xfails, and zero skips.
2. **Given** a MUMPS routine that uses only `$PRINCIPAL` I/O (WRITE, READ from stdin/stdout), **When** transpiled and run after Phase 4, **Then** behavior is identical to pre-Phase 4.
3. **Given** a MUMPS routine that uses single-process LOCK, **When** transpiled and run after Phase 4, **Then** in-process locking still works correctly.
4. **Given** a MUMPS routine using JOB with threads, **When** transpiled and run after Phase 4, **Then** JOB'd routines execute (now as subprocesses) with correct behavior.

---

### User Story 2 — File I/O with OPEN, USE, CLOSE, READ, and WRITE works for sequential files (Priority: P1)

A developer transpiles a VistA routine that opens a file, writes data to it, closes it, reopens it for reading, reads the data back, and closes it again. The file operations produce correct results matching YottaDB behavior.

**Why this priority**: 1,062 VistA files use OPEN (3.1% of the codebase). File I/O is the most common device type after `$PRINCIPAL`. VistA uses it for configuration files, HL7 message queues, report generation, and data import/export. This is the core deliverable of Phase 4.

**Independent Test**: Transpile a MUMPS routine that creates a temp file, writes lines, reads them back, and verifies content. Compare output against YottaDB.

**Acceptance Scenarios**:

1. **Given** `OPEN "test.txt":("WN") USE "test.txt" WRITE "Hello",! CLOSE "test.txt"`, **When** transpiled and run, **Then** the file `test.txt` is created containing `Hello` followed by a newline.
2. **Given** an existing file `test.txt`, **When** `OPEN "test.txt":("R") USE "test.txt" READ X CLOSE "test.txt"` is transpiled and run, **Then** X contains the first line of the file.
3. **Given** a file open for reading, **When** `READ X` is called repeatedly until end-of-file, **Then** `$ZEOF` is set to 1 when the file is exhausted.
4. **Given** `OPEN "test.txt":("AW")`, **When** data is written, **Then** it is appended to the existing file content.
5. **Given** `USE "test.txt"`, **When** the device is switched, **Then** subsequent READ and WRITE operations target the file, not `$PRINCIPAL`.
6. **Given** `CLOSE "test.txt"`, **When** the device is closed, **Then** the file handle is released and `USE` of that device raises an error.
7. **Given** `OPEN "test.txt":("RW")` in read-write mode, **When** data is read and written interchangeably, **Then** file position is maintained correctly.

---

### User Story 3 — Device parameter processing handles MUMPS OPEN/USE parameters (Priority: P2)

A developer transpiles VistA routines that use OPEN with device parameters (e.g., access mode, record size, newline handling). The device parameters are parsed and applied correctly.

**Why this priority**: VistA routines use a variety of device parameters for file access control, encoding, and format. Without parameter support, many VistA file I/O routines cannot function.

**Independent Test**: Transpile routines using common device parameter combinations. Verify the file is opened with correct access mode, encoding, and record-size constraints.

**Acceptance Scenarios**:

1. **Given** `OPEN file:(READONLY)`, **When** transpiled and run, **Then** the file is opened in read-only mode. Write attempts raise an error.
2. **Given** `OPEN file:(NEWVERSION)`, **When** transpiled and run, **Then** a new file is created (or existing file is truncated).
3. **Given** `OPEN file:(APPEND)`, **When** transpiled and run, **Then** writes append to the existing file.
4. **Given** `OPEN file:(RECORDSIZE=132)`, **When** transpiled and run, **Then** the record size limit is enforced.
5. **Given** `OPEN device:timeout` with timeout on a device that exists but is currently unavailable (e.g., locked by another process or a TCP connection in progress), **When** the device cannot be opened within the timeout, **Then** `$TEST` is set to 0 and execution continues. Note: file-not-found and permission errors raise DEVOPENFAIL regardless of timeout (see FR-022).

---

### User Story 4 — `$PRINCIPAL` I/O uses the device abstraction layer (Priority: P1)

A developer's existing console I/O (stdin/stdout) works through the new device abstraction layer. `$PRINCIPAL` is the default device. USE 0 and USE $P switch back to the principal device.

**Why this priority**: All existing MUMPS programs use `$PRINCIPAL` I/O. The new device layer must handle this transparently as a backward-compatible foundation.

**Independent Test**: Transpile routines using READ and WRITE with no explicit device management. Verify I/O still uses stdin/stdout. Verify USE 0 and USE $P work.

**Acceptance Scenarios**:

1. **Given** a routine with `WRITE "hello",!`, **When** transpiled and run, **Then** `hello` is printed to stdout followed by a newline — identical to pre-Phase 4 behavior.
2. **Given** a routine that opens a file, uses it, then does `USE 0`, **When** transpiled and run, **Then** subsequent WRITE goes to stdout.
3. **Given** `USE $P`, **When** transpiled and run, **Then** the principal device is restored as the current device.
4. **Given** `$IO` is read, **When** `$PRINCIPAL` is the current device, **Then** `$IO` returns the principal device identifier.
5. **Given** `$IO` is read after `USE "file.txt"`, **When** the file is the current device, **Then** `$IO` returns `"file.txt"`.

---

### User Story 5 — TCP socket I/O supports basic client connections (Priority: P3)

A developer transpiles VistA HL7 communication routines that open TCP socket connections to send and receive data. Basic client-mode TCP operations work.

**Why this priority**: VistA uses TCP sockets for HL7 messaging (inter-system clinical data exchange). While fewer VistA files use TCP directly (most go through Kernel abstractions), the device layer should support TCP to enable HL7 infrastructure. This is lower priority because VistA typically wraps TCP in Kernel routines.

**Independent Test**: Transpile a routine that opens a TCP connection to a local echo server, sends data, reads the response, and closes the connection.

**Acceptance Scenarios**:

1. **Given** `OPEN "host:port":(CONNECT)`, **When** transpiled and run with a listening server, **Then** a TCP connection is established.
2. **Given** an open TCP device, **When** `WRITE data` is called, **Then** the data is sent over the TCP connection.
3. **Given** an open TCP device, **When** `READ X` is called, **Then** X contains data received from the TCP connection.
4. **Given** `OPEN "host:port":(CONNECT):timeout`, **When** the connection cannot be established within the timeout, **Then** `$TEST` is set to 0.
5. **Given** `CLOSE "host:port"`, **When** the TCP connection is closed, **Then** the socket is released.

---

### User Story 6 — JOB creates a real subprocess with independent local variables (Priority: P1)

A developer transpiles a VistA routine that uses JOB to start a background task (e.g., TaskMan's `^%ZTMS`). The JOB'd routine runs as a real subprocess with its own local variable space, not sharing locals with the parent process.

**Why this priority**: 343 VistA files use JOB (1.0%). VistA's TaskMan (`^%ZTMS`) is built on JOB and is critical infrastructure. The current thread-based implementation shares memory, violating MUMPS semantics where JOB creates an independent process.

**Independent Test**: Transpile a routine that JOBs a subroutine which sets a local variable. Verify the parent process does not see the child's local variable. Verify the child process runs to completion and exits.

**Acceptance Scenarios**:

1. **Given** `JOB LABEL^ROUTINE`, **When** transpiled and run, **Then** a new subprocess is created running the specified routine, and `$JOB` in the parent process does not change.
2. **Given** a JOB'd subprocess, **When** it sets `SET X=1`, **Then** the parent process's local variable X is unaffected (independent local variable space).
3. **Given** a JOB'd subprocess, **When** it sets `SET ^GLOBAL(1)="data"`, **Then** the parent process can read `^GLOBAL(1)` and sees `"data"` (shared global storage).
4. **Given** `JOB LABEL^ROUTINE:(parameters):timeout`, **When** the JOB cannot start within the timeout, **Then** `$TEST` is set to 0 in the parent process.
5. **Given** a JOB'd process, **When** `$JOB` is read within the child, **Then** it returns the child's process ID (distinct from the parent's `$JOB`).
6. **Given** multiple JOB commands, **When** each completes, **Then** each runs as an independent subprocess with its own locals and shared globals.

---

### User Story 7 — JOB'd processes share global storage with the parent (Priority: P1)

A developer verifies that globals written by a JOB'd subprocess are visible to the parent process and vice versa. The global storage backend supports concurrent access from multiple processes.

**Why this priority**: MUMPS globals are shared across all processes by design. This is fundamental to JOB semantics and VistA operation — TaskMan communicates with its parent via globals (`^%ZTSK`).

**Independent Test**: Transpile a routine that JOBs a child which writes to a global, then the parent waits and reads the global. Verify the data is visible.

**Acceptance Scenarios**:

1. **Given** a parent sets `SET ^FLAG=0` and JOBs a child that does `SET ^FLAG=1`, **When** the parent polls `^FLAG` after the child completes, **Then** it reads `1`.
2. **Given** a parent sets `SET ^DATA(1)="parent"` and a child sets `SET ^DATA(2)="child"`, **When** both processes finish, **Then** `^DATA` contains both subscripts.
3. **Given** concurrent global writes from parent and child, **When** both complete, **Then** no data is lost or corrupted.
4. **Given** `$ORDER(^DATA(""))` is called after both processes write, **When** transpiled and run, **Then** all subscripts are correctly enumerated.

---

### User Story 8 — Inter-process LOCK coordinates across JOB'd processes (Priority: P2)

A developer transpiles a VistA routine where the parent process acquires a LOCK and a JOB'd child attempts to acquire the same lock. The lock correctly blocks the child until the parent releases it.

**Why this priority**: 2,977 VistA files use LOCK (8.8%). LOCK's purpose is inter-process coordination. The current `threading.Lock` only works within a single process. With real JOB subprocesses (Story 6), inter-process locking becomes essential.

**Independent Test**: Transpile a routine where the parent acquires `LOCK +^LCK`, JOBs a child that attempts `LOCK +^LCK:1`, verify the child's `$TEST` is 0 (lock not acquired within timeout), then the parent releases and the child retries and succeeds.

**Acceptance Scenarios**:

1. **Given** process A holds `LOCK +^GLO(1)` and process B attempts `LOCK +^GLO(1):0`, **When** transpiled and run, **Then** process B's `$TEST` is 0 (lock is held by A).
2. **Given** process A releases `LOCK -^GLO(1)` and process B retries `LOCK +^GLO(1):5`, **When** transpiled and run, **Then** process B's `$TEST` is 1 (lock acquired).
3. **Given** a bare `LOCK ^GLO(1)` (not incremental), **When** transpiled and run, **Then** all previously held locks by the current process are released before acquiring the new lock.
4. **Given** incremental locks `LOCK +^A LOCK +^B`, **When** `LOCK -^A` is called, **Then** only `^A` is released; `^B` remains held.
5. **Given** a process exits (normally or abnormally), **When** its locks are checked, **Then** all locks held by that process are automatically released.
6. **Given** `LOCK +^GLO(1):0` with a zero timeout, **When** the lock is immediately unavailable, **Then** `$TEST` is set to 0 without blocking.

---

### User Story 9 — `$ZEOF` indicates end-of-file during sequential file reads (Priority: P2)

A developer transpiles a VistA routine that reads a file line by line until `$ZEOF` indicates the file is exhausted. The ISV correctly reflects the file's read state.

**Why this priority**: 13 VistA files use `$ZEOF`. It is the standard way to detect end-of-file during file processing in MUMPS. Blocked on I/O device management (Story 2).

**Independent Test**: Create a file with 3 lines, open it for reading, read until `$ZEOF=1`, verify all lines were read and `$ZEOF` transitions correctly.

**Acceptance Scenarios**:

1. **Given** a file with 3 lines is opened for reading, **When** `$ZEOF` is read before any READ, **Then** it returns 0.
2. **Given** reading the third (last) line, **When** the next READ attempts to read past end-of-file, **Then** `$ZEOF` is set to 1.
3. **Given** `$ZEOF` is 1, **When** the file is closed and a new file is opened, **Then** `$ZEOF` resets to 0 for the new file.
4. **Given** `$PRINCIPAL` is the current device, **When** `$ZEOF` is read, **Then** it returns 0 (stdin is not exhaustible in interactive mode) or 1 when piped input is exhausted.

---

### User Story 10 — `$X` and `$Y` track cursor position across devices (Priority: P2)

A developer transpiles a VistA routine that uses `$X` and `$Y` to track output position. The position tracking works correctly for both `$PRINCIPAL` and file devices.

**Why this priority**: `$X` and `$Y` are standard MUMPS ISVs for cursor position. VistA uses `$X` for output formatting (checking line width before writing). Currently partially implemented; the device layer must maintain position per-device.

**Independent Test**: Transpile a routine that writes text, checks `$X`, writes a newline, checks `$Y`, then switches devices and verifies position tracking is per-device.

**Acceptance Scenarios**:

1. **Given** `WRITE "ABCDE"`, **When** `$X` is read, **Then** it returns 5 (5 characters written on current line).
2. **Given** `WRITE !`, **When** `$Y` and `$X` are read, **Then** `$Y` increments by 1 and `$X` resets to 0.
3. **Given** `USE "file.txt" WRITE "Hello"`, **When** `$X` is read, **Then** it returns 5 for the file device.
4. **Given** switching from file device back to `$PRINCIPAL`, **When** `$X` is read, **Then** it reflects the principal device's position (not the file device's).

---

### User Story 11 — `$KEY` reflects device-specific read termination (Priority: P2)

A developer transpiles a VistA routine that uses `$KEY` to determine how a READ was terminated on the current device. `$KEY` correctly reflects the termination character for both `$PRINCIPAL` and file devices.

**Why this priority**: `$KEY` is essential for VistA menu navigation and data entry routines. Phase 3 added `$KEY` for `$PRINCIPAL`; Phase 4 extends it to file and TCP devices.

**Independent Test**: Read from a file and verify `$KEY` reflects end-of-line characters. Read from TCP and verify `$KEY` reflects the terminator.

**Acceptance Scenarios**:

1. **Given** a file read that terminates at end-of-line, **When** `$KEY` is read, **Then** it contains the newline character.
2. **Given** a file read that terminates at end-of-file, **When** `$KEY` is read, **Then** it contains empty string.
3. **Given** a TCP read that terminates at a protocol delimiter, **When** `$KEY` is read, **Then** it contains the delimiter character.

---

### Edge Cases

- What happens when OPEN is called on a file that does not exist in read mode? An error is raised (DEVOPENFAIL), regardless of whether a timeout was specified. This matches YDB behavior.
- What happens when OPEN is called on a file path the process does not have permission to access? An error is raised (DEVOPENFAIL), regardless of whether a timeout was specified. This matches YDB behavior.
- What happens when a JOB'd subprocess crashes? Its locks are automatically released, its exit status is available, and the parent process is not affected.
- What happens when the global storage backend is accessed concurrently by parent and child processes? A process-safe storage mechanism (shared memory, file-backed, or IPC) must be used — no data loss or corruption.
- What happens when a LOCK timeout of 0 is specified? The lock is attempted without blocking; `$TEST` is set to 0 if unavailable, 1 if acquired.
- What happens when CLOSE is called on `$PRINCIPAL`? The close is a no-op; `$PRINCIPAL` cannot be closed.
- What happens when USE is called on a device that has not been OPENed? An error is raised.
- What happens when READ is called on a file open for write-only? An error is raised.
- What happens when multiple JOB'd processes attempt to OPEN the same file for writing? Each OPEN produces an independent file handle; file locking follows OS behavior.
- What happens when the lock manager storage fails? Pending LOCK operations fail with a timeout or error, ensuring the system does not deadlock.
- What happens when two processes deadlock with incremental LOCKs (e.g., A holds `^X` and waits for `^Y`, B holds `^Y` and waits for `^X`)? Both block indefinitely — no automatic deadlock detection. This matches MUMPS standard and YottaDB behavior. Resolution requires external intervention (e.g., killing one process).
- What happens when a process waiting for a LOCK discovers the blocking process has died? The orphaned lock is automatically cleared and the waiting process acquires it.
- What happens when `$ZEOF` is read when no file device is in USE? It returns 0.
- What happens when a TCP connection is lost mid-read? An appropriate error is raised; `$ZEOF` may be set to 1 on the TCP device.

## Requirements *(mandatory)*

### Functional Requirements

#### Test Suite Integrity — Per-Implementation-Phase Gates

- **FR-001**: The full test suite MUST pass with zero failures, zero xfails, and zero skips after each implementation sub-phase (I/O device layer, JOB processes, inter-process LOCK, `$ZEOF`) is completed. No sub-phase may leave the test suite in a failing state.
- **FR-002**: Each new feature MUST include new unit tests covering the implementation in isolation, including edge cases documented in this specification. Tests MUST cover both happy-path and error-path scenarios.
- **FR-003**: Each new feature MUST include integration tests that transpile representative MUMPS routines exercising the feature and compare output against YottaDB reference output where applicable.
- **FR-004**: New tests MUST cover edge cases explicitly: invalid file paths, permission errors, connection timeouts, concurrent access patterns, end-of-file conditions, and process lifecycle events.
- **FR-005**: At the completion of the entire Phase 4, the full test suite (including all new tests from Phases 1–4) MUST pass with zero failures, zero xfails, and zero skips. Any test updated to reflect new architecture MUST retain its original intent and coverage.

#### Sub-Phase 1 — I/O Device Management (F-02)

##### Device Abstraction Layer

- **FR-010**: A new `runtime/devices.py` module MUST define an abstract `MUMPSDevice` base class with the following interface: `read(maxlen=None, timeout=None) -> tuple[str, str]` (returns data and terminator key for `$KEY` tracking), `write(data: str)`, `write_newline()`, `close()`, and properties `zeof: bool`, `x_pos: int`, `y_pos: int`, `key: str`. Device construction and parameter application are handled by factory methods on `MUMPSRuntime` (`open_device()`), not by the device ABC.
- **FR-011**: A `PrincipalDevice` class MUST implement `MUMPSDevice` for stdin/stdout I/O. It MUST replicate the current `$PRINCIPAL` behavior exactly, including `$X`/`$Y` tracking and `$KEY` support from Phase 3. Existing console I/O behavior MUST NOT change.
- **FR-012**: A `FileDevice` class MUST implement `MUMPSDevice` for sequential file I/O. It MUST support read mode, write mode (new version), append mode, and read-write mode. It MUST track `$X`, `$Y`, `$KEY`, and `$ZEOF` per-device.
- **FR-013**: A `TCPDevice` class MUST implement `MUMPSDevice` for TCP socket client connections. It MUST support CONNECT mode and basic read/write operations. It MUST track `$KEY` and `$ZEOF`.

##### Device Table and Lifecycle

- **FR-020**: `MUMPSRuntime` MUST maintain a device table mapping device names (strings) to `MUMPSDevice` instances. `$PRINCIPAL` MUST be pre-registered as device `"0"` (or `"$PRINCIPAL"`) at runtime initialization.
- **FR-021**: `MUMPSRuntime` MUST maintain a `current_device` reference pointing to the active `MUMPSDevice`. It MUST default to `$PRINCIPAL` at startup.
- **FR-022**: The OPEN command MUST create a new `MUMPSDevice` instance of the appropriate type (file, TCP, etc.), register it in the device table, and apply device parameters. If a timeout is specified and the device is opened successfully, `$TEST` MUST be set to 1. If the device cannot be opened due to a fundamental error (file not found, permission denied), an error MUST be raised regardless of timeout — matching YDB's DEVOPENFAIL behavior. Timeout applies only to waiting for a device that exists but is currently unavailable (e.g., locked by another process or network connection in progress).
- **FR-023**: The USE command MUST switch `current_device` to the specified device. If the device is not in the device table (not previously OPENed and not `$PRINCIPAL`), an error MUST be raised. `USE 0` and `USE $P` MUST switch to `$PRINCIPAL`.
- **FR-024**: The CLOSE command MUST close the device, release resources, and remove it from the device table. CLOSEing `$PRINCIPAL` MUST be a no-op. After CLOSE, `current_device` MUST revert to `$PRINCIPAL`.
- **FR-025**: READ and WRITE operations MUST dispatch to `current_device.read()` and `current_device.write()` respectively. No changes to READ/WRITE MUMPS syntax are required — only the target device changes.

##### Device Parameters

- **FR-030**: The OPEN command MUST parse MUMPS device parameters from the `(params)` syntax. At minimum, the following parameters MUST be supported for file devices: `READONLY`/`R`, `NEWVERSION`/`N`/`WN`, `APPEND`/`A`, `RECORDSIZE=n`, and `STREAM`.
- **FR-031**: The OPEN command MUST parse timeout parameters from the `:timeout` syntax. When a timeout is specified, OPEN MUST be non-blocking: if the device cannot be opened within the timeout, `$TEST` is set to 0.
- **FR-032**: TCP device parameters MUST include at minimum: `CONNECT` (for client connections), and `DELIMITER=chars` (for read termination on TCP). Server-mode (`LISTEN`) MUST be designed-for in the interface but not implemented.

##### ISV Updates

- **FR-040**: `$IO` MUST return the name of the current device. After `USE "file.txt"`, `$IO` returns `"file.txt"`. After `USE 0`, `$IO` returns the principal device identifier.
- **FR-041**: `$X` and `$Y` MUST be tracked per-device. Switching devices via USE MUST switch to the target device's position counters. WRITE operations MUST update the current device's `$X` and `$Y`.
- **FR-042**: `$KEY` MUST reflect the termination character of the most recent READ on the current device.
- **FR-043**: `$ZEOF` MUST reflect the end-of-file state of the current device. For `$PRINCIPAL` in interactive mode, `$ZEOF` MUST be 0. For file devices, `$ZEOF` MUST be set to 1 when a READ operation reaches end-of-file. Opening a new file MUST reset `$ZEOF` to 0.

##### Codegen Changes

- **FR-050**: Codegen for the OPEN command MUST emit calls to `_rt.open_device(name, params, timeout)` instead of any current stub or no-op.
- **FR-051**: Codegen for the USE command MUST emit calls to `_rt.use_device(name)`.
- **FR-052**: Codegen for the CLOSE command MUST emit calls to `_rt.close_device(name)`.
- **FR-053**: Codegen for READ and WRITE MUST continue to call `_rt.read()` and `_rt.write()`, which now dispatch to `current_device`. No READ/WRITE codegen changes should be needed if the runtime methods are updated to use the device layer.

##### Test Gates

- **FR-058**: After Sub-Phase 1 is complete, the full test suite MUST pass with zero failures, zero xfails, and zero skips. All existing console I/O tests MUST pass without modification (unless updated to use the new device API while preserving intent).
- **FR-059**: New unit tests MUST cover: `PrincipalDevice` read/write, `FileDevice` read/write/append/close, `TCPDevice` connect/read/write/close, device table management, device parameter parsing, `$IO`/`$X`/`$Y`/`$KEY`/`$ZEOF` per-device tracking, and all edge cases (invalid paths, permission errors, timeouts).

#### Sub-Phase 2 — JOB as Real Processes (F-04)

##### Process Creation

- **FR-060**: The JOB command MUST create a new subprocess using `subprocess.Popen` to spawn a separate Python interpreter that runs the specified routine. The child process MUST import the transpiled module and connect to the shared SQLite database independently. The subprocess MUST have its own independent local variable space. This avoids `multiprocessing`'s fork/pickle complexities and provides clean process isolation matching MUMPS's independent-process semantics.
- **FR-061**: `$JOB` within the child process MUST return the child's OS process ID. `$JOB` in the parent process MUST remain the parent's OS process ID.
- **FR-062**: JOB with a timeout (`JOB routine:timeout`) MUST set `$TEST` to 0 if the subprocess cannot be started within the timeout, and 1 on success.
- **FR-062a**: After a successful JOB command, `$ZJOB` in the parent process MUST be set to the child process's OS PID, enabling the parent to identify the spawned process.
- **FR-063**: JOB parameters (process parameters like input/output device redirection) MUST be parsed and applied. At minimum, default I/O for the JOB'd process MUST be redirectable (e.g., `JOB routine:(output="file.txt")`).

##### Global Storage Sharing

- **FR-070**: JOB'd subprocesses MUST share global storage with the parent process. Writes to globals in the child MUST be visible to the parent and vice versa.
- **FR-071**: The in-memory global storage backend MUST be replaced with (or wrapped by) a SQLite file-backed database that supports concurrent access. Each process MUST open its own SQLite connection to the shared database file. The storage MUST use SQLite's WAL (Write-Ahead Logging) mode for concurrent read/write performance and MUST handle process crashes without data corruption (guaranteed by SQLite's ACID properties).
- **FR-072**: `$DATA`, `$ORDER`, `$GET`, `$QUERY`, KILL, SET, and MERGE on globals MUST all work correctly across process boundaries with the shared storage.
- **FR-073**: Transaction semantics (`TSTART`/`TCOMMIT`/`TROLLBACK`) MUST work correctly with shared global storage. Transactions MUST be isolated per-process.

##### Process Lifecycle

- **FR-080**: When a JOB'd subprocess exits (normally via HALT or QUIT), its resources MUST be cleaned up: file handles closed, locks released.
- **FR-081**: When a JOB'd subprocess crashes (unhandled exception), its locks MUST be automatically released and its exit status MUST be available to the parent (via `^$JOB` or similar mechanism).
- **FR-082**: The parent process MUST NOT block waiting for JOB'd subprocesses unless explicitly coordinated via LOCK or global polling.

##### Codegen Changes

- **FR-085**: Codegen for the JOB command MUST emit calls to `_rt.job(routine, label, params, timeout)` that create a real subprocess via `subprocess.Popen`, replacing the current thread-based implementation.

##### Test Gates

- **FR-088**: After Sub-Phase 2 is complete, the full test suite MUST pass with zero failures, zero xfails, and zero skips.
- **FR-089**: New unit tests MUST cover: subprocess creation and cleanup, independent local variable spaces, shared global access from parent and child, JOB with timeout, `$JOB` in parent and child, concurrent global writes, and process crash cleanup.

#### Sub-Phase 3 — Inter-Process LOCK (F-01)

##### Lock Manager

- **FR-090**: A cross-process lock manager MUST be implemented. LOCK operations (`LOCK +name`, `LOCK -name`, bare `LOCK name`) MUST coordinate across all processes (parent and JOB'd children).
- **FR-091**: The lock manager MUST support: incremental lock acquisition (`LOCK +`), incremental lock release (`LOCK -`), bare LOCK (release all, then acquire), lock timeout with `$TEST` update, and automatic lock release on process exit. LOCK without a timeout MUST block indefinitely until the lock becomes available (matching the MUMPS standard and YottaDB behavior). No automatic deadlock detection is implemented — it is the programmer's responsibility to use timeouts or consistent lock ordering to avoid deadlocks.
- **FR-091a**: When a process is waiting for a LOCK held by another process, the lock manager MUST periodically check whether the blocking process is still alive (PID liveness check). If the blocking process has died, the orphaned lock MUST be automatically cleared and the waiting process MUST acquire it. This matches YottaDB's dead-process detection behavior.
- **FR-092**: The lock manager MUST use a shared lock table in the same SQLite database as global storage. Lock entries MUST include the lock name, owning PID, and lock count (for incremental locks). Stale locks from crashed processes MUST be detectable by checking whether the owning PID is still alive. The lock table MUST support hierarchical lock name queries (parent-child blocking).
- **FR-093**: Lock granularity MUST match MUMPS semantics: `LOCK +^GLO(1,2)` acquires a lock on that specific node, and `LOCK +^GLO(1)` acquires a lock on the parent (which blocks children). Lock names follow the same namespace as globals (including subscripts).
- **FR-094**: Lock escalation and de-escalation MUST follow MUMPS rules: acquiring a parent lock implicitly blocks all child locks (e.g., `LOCK +^A` blocks `LOCK +^A(1)` from other processes). Releasing a parent lock releases the block.

##### Backward Compatibility

- **FR-095**: Single-process locking (no JOB'd children) MUST continue to work correctly with the new lock manager. The lock manager MUST NOT require a separate server process for single-process operation.
- **FR-096**: In-process locking within a single process (e.g., between routines) MUST work identically to pre-Phase 4 behavior.

##### Lock Introspection (ZSHOW "L")

- **FR-097**: Lock introspection MUST be available via `ZSHOW "L"`, matching YDB's format: `"LOCK ^name LEVEL=n"` per held lock, preceded by `"MLG:count,MLT:count"` summary. Note: YDB does not support the `^$LOCK` SSVN syntax from the MUMPS standard. m2py follows YDB here — `ZSHOW "L"` is the lock introspection mechanism.

##### Test Gates

- **FR-098**: After Sub-Phase 3 is complete, the full test suite MUST pass with zero failures, zero xfails, and zero skips.
- **FR-099**: New unit tests MUST cover: cross-process lock acquisition and release, lock timeout with `$TEST`, lock escalation/de-escalation, bare LOCK releasing all locks, automatic lock release on process exit/crash, ZSHOW "L" output format, and single-process backward compatibility.

#### Code Quality

- **FR-100**: No new backward imports (lower layer importing from higher layer) MUST be introduced. `runtime/` MUST NOT import from `codegen/`, `core/` MUST NOT import from `codegen/` or `runtime/`.
- **FR-101**: Each new module, class, and public method MUST include a docstring describing its purpose, parameters, return type, and behavioral notes.
- **FR-102**: Dead code resulting from replaced implementations (thread-based JOB, threading.Lock-based locking) MUST be removed.

### Key Entities

- **`MUMPSDevice` (abstract)**: Base class for all I/O devices. Defines the read/write/open/close interface and position tracking (`$X`, `$Y`, `$KEY`, `$ZEOF`).
- **`PrincipalDevice`**: Device implementation for stdin/stdout (`$PRINCIPAL`). Default device at runtime startup.
- **`FileDevice`**: Device implementation for sequential file I/O. Supports read, write, append, and read-write modes with device parameters.
- **`TCPDevice`**: Device implementation for TCP socket client connections. Supports CONNECT mode, read/write with delimiters.
- **Device Table**: Runtime-maintained mapping of device names to `MUMPSDevice` instances. Manages device lifecycle (OPEN/USE/CLOSE).
- **`current_device`**: Reference to the active `MUMPSDevice` in the runtime. Switched by the USE command. Defaults to `$PRINCIPAL`.
- **Lock Manager**: Cross-process lock coordination mechanism. Manages the lock table, timeout-based acquisition, incremental lock/unlock, and automatic release on process exit.
- **Shared Global Storage**: Process-safe global storage backend replacing the current in-memory dict. Supports concurrent access from parent and JOB'd child processes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of existing tests pass with zero failures, zero xfails, and zero skips after each sub-phase and at the completion of Phase 4.
- **SC-002**: New unit tests are added for every new feature. Each test module covers at least the acceptance scenarios and edge cases listed in this specification.
- **SC-003**: MUMPS routines using OPEN/USE/CLOSE for file I/O produce output matching YottaDB when transpiled and run.
- **SC-004**: `$PRINCIPAL` I/O behavior is identical to pre-Phase 4 for all existing tests and routines.
- **SC-005**: JOB'd subprocesses have independent local variable spaces — a local variable set in a child is not visible in the parent.
- **SC-006**: Globals written by a JOB'd subprocess are visible to the parent process and vice versa.
- **SC-007**: LOCK operations coordinate correctly across processes — a lock held by process A blocks process B's attempt to acquire the same lock.
- **SC-008**: Lock timeout with `$TEST` works correctly: `LOCK +name:0` on a held lock sets `$TEST=0` without blocking.
- **SC-009**: `$ZEOF` correctly reflects end-of-file state for file devices, transitioning from 0 to 1 when a READ reaches the end of the file.
- **SC-010**: `$IO`, `$X`, `$Y`, `$KEY` are tracked per-device and reflect the current device's state after USE commands.
- **SC-011**: Process crash cleanup works: locks held by a crashed process are released, file handles are closed.
- **SC-012**: Single-process locking (no JOB) continues to work identically to pre-Phase 4 behavior.

## Assumptions

- Phases 1 (019-foundation-cleanup), 2 (020-codegen-refactoring), and 3 (021-correctness-features) are complete before Phase 4 begins. Phase 4 uses infrastructure from all prior phases: `core/values.py`, `codegen/var_access.py`, `_build_indirection_call()` template, error handling infrastructure (`$ETRAP`/`$ZTRAP`), LOCK indirection, etc.
- The I/O device abstraction follows standard MUMPS device semantics: each device is identified by a name string, managed through OPEN/USE/CLOSE commands, and has independent `$X`/`$Y`/`$KEY`/`$ZEOF` state.
- TCP device support in this phase covers client-mode connections. Server-mode (LISTEN/ACCEPT) is a future extension — the `MUMPSDevice` interface should be designed to accommodate it.
- The shared global storage mechanism for JOB'd processes uses SQLite as a file-backed database. Each process opens its own connection; SQLite's WAL mode provides concurrent read/write access. SQLite was chosen for its simplicity, ACID guarantees, and crash safety without requiring a separate server process.
- Lock management for inter-process LOCK follows MUMPS semantics: lock names are hierarchical (matching global subscript structure), parent locks block children, and locks are automatically released on process exit.
- "Automatic lock release on process exit" includes both normal exit (HALT/QUIT) and abnormal exit (crash/kill). The lock manager detects stale locks by checking PID liveness against the owning PID stored in the SQLite lock table.
- Device parameter syntax follows YDB conventions. The full set of YDB device parameters is large; this phase implements the most commonly used parameters (access mode, record size, stream, append). Exotic parameters (e.g., `ICHSET`, `OCHSET` for encoding) may be deferred to a future iteration.
- The `PrincipalDevice` wrapping of stdin/stdout must be transparent — existing tests that verify console I/O (WRITE output, READ input from pipes) must pass without modification.
- JOB'd subprocesses are Python processes running the transpiled routine. The child process requires the m2py runtime and the transpiled module to be importable (available on PYTHONPATH or in the working directory).
- Lock introspection is provided via `ZSHOW "L"` (matching YDB), not via `^$LOCK` SSVN (which YDB does not support). `ZSHOW "L"` output format matches YDB: `"MLG:count,MLT:count"` header followed by `"LOCK ^name LEVEL=n"` per held lock.

## Dependencies

- **Blocked by**: Phase 1 (019-foundation-cleanup), Phase 2 (020-codegen-refactoring), and Phase 3 (021-correctness-features) must all be complete.
- **Blocks**: No further phases are planned. Phase 4 is the final phase of the refactoring plan.
- **Internal dependencies (sequential)**: F-02 (I/O) → F-04 (JOB) → F-01 (inter-process LOCK). `$ZEOF` (F-12 remainder) depends on F-02.

## Scope Boundaries

### In Scope

- All items from the refactoring plan's Phase 4: F-01 (inter-process LOCK), F-02 (I/O device management), F-04 (JOB as real processes), F-12 remainder (`$ZEOF`)
- New `runtime/devices.py` module with `MUMPSDevice` hierarchy
- Device table management in `MUMPSRuntime`
- Device parameter parsing for OPEN/USE commands
- `PrincipalDevice`, `FileDevice`, `TCPDevice` implementations
- Process-based JOB using `subprocess` or `multiprocessing`
- Process-safe shared global storage backend
- Cross-process lock manager
- `$ZEOF`, `$IO`, `$X`/`$Y` per-device tracking, `$KEY` per-device
- Updated codegen for OPEN, USE, CLOSE, JOB commands
- Unit and integration tests for all new features
- YDB validation for features with well-defined reference behavior

### Out of Scope

- TCP server mode (LISTEN/ACCEPT) — design for future extension but not implemented
- Interactive terminal raw mode (character-at-a-time input with `termios`/`tty`) — deferred
- Full VistA Kernel module compatibility testing (TaskMan, HL7) — deferred to integration phase
- Changes to the parser/ASG for I/O commands (OPEN/USE/CLOSE are already parsed; only codegen and runtime changes are needed)
- Persistent global storage backend (disk-backed globals beyond shared-process scope) — the shared storage is for cross-process coordination within a single m2py session
- `^%G` (YDB global display utility) — requires interactive terminal infrastructure
- Deferred items from the refactoring plan: `TROLLBACK:n`, `$TRESTART`, VIEW behavioral keywords, user-defined pattern tables, ANSI library functions, zero-usage Z-commands
- Full device parameter coverage — only the most commonly used parameters are implemented; exotic parameters are deferred
- Named pipe devices, FIFO devices, or other non-standard device types
