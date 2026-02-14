# Research: Phase 4 — Large Architecture

**Date**: 2026-02-12  
**Spec**: [spec.md](spec.md)

## Decisions

### D1: Shared Global Storage Backend

- **Decision**: SQLite file-backed database with WAL mode
- **Rationale**: ACID guarantees, crash safety, no separate server process. Each subprocess opens its own connection. Well-tested concurrent access patterns.
- **Alternatives considered**:
  - `multiprocessing.Manager` shared dict — requires a Manager server process, no automatic crash recovery
  - Lightweight IPC server — highest implementation complexity, custom protocol needed

### D2: Lock Manager Implementation

- **Decision**: Shared lock table in SQLite, co-located with global storage database
- **Rationale**: Single backend for all shared state. PID-based ownership enables stale lock detection. Hierarchical lock name queries supported via SQL LIKE patterns.
- **Alternatives considered**:
  - Separate SQLite DB for locks — adds a second coordination point without clear benefit
  - OS-level advisory file locks (`fcntl.flock`) — can't represent hierarchical subscript locking

### D3: JOB Process Creation

- **Decision**: `subprocess.Popen` spawning a new Python interpreter
- **Rationale**: Clean process isolation matching MUMPS independent-process semantics. Child imports transpiled module and connects to SQLite independently. No fork/pickle complexities.
- **Alternatives considered**:
  - `multiprocessing.Process` — tighter coupling via fork, pickle requirements for passing state, shared memory complications

### D4: Deadlock Policy

- **Decision**: No automatic deadlock detection. LOCK without timeout blocks indefinitely.
- **Rationale**: Matches both the MUMPS standard (§8.1.5 — "execution suspends indefinitely") and YottaDB behavior. Dead-process detection auto-clears orphaned locks via PID liveness checks.
- **Alternatives considered**: None — both the standard and YDB are unambiguous on this.

## YDB Reference Behavior

### I/O Device Semantics (validated via YDB Docker)

```
# File I/O
OPEN F:NEWVERSION  → creates/truncates file
OPEN F:READONLY    → read-only access
OPEN F:APPEND      → append mode
OPEN F:(NEWVERSION:STREAM) → stream mode (no record-length limits)

# $IO tracking
$IO during USE of file  → full file path (e.g., "/tmp/m2py_io_test.txt")
$IO after CLOSE          → "0" ($PRINCIPAL identifier)
$IO at startup           → "0"

# $ZEOF behavior
Before any READ           → 0
After reading last line   → 0  (data was still available)
After READ past end       → 1  (no more data)
On new OPEN               → reset to 0

# $KEY for file reads
End-of-line termination → $C(10) (newline, ASCII 10)
End-of-file termination → "" (empty string)

# $X/$Y tracking
WRITE "AB"   → $X=2
WRITE "CDE"  → $X=5
WRITE !      → $X=0, $Y increments by 1
$Y is cumulative across entire process session

# CLOSE behavior
CLOSE current device → $IO reverts to "0" ($PRINCIPAL)

# OPEN timeout for non-existent files
OPEN "/nonexistent":(READONLY):0 → raises DEVOPENFAIL error (NOT $TEST=0)
OPEN existing_file:(NEWVERSION):0 → $TEST=1 (success)
```

**Critical finding**: OPEN with timeout on a non-existent file raises an error, not `$TEST=0`. The timeout only applies to waiting for a device that exists but is currently unavailable (e.g., locked by another process). Spec FR-022 needs correction — file-not-found is an error, not a timeout failure.

### LOCK Semantics (validated via YDB Docker)

```
# Basic acquire/release
LOCK +^A             → acquires
LOCK -^A             → releases

# Incremental locks
LOCK +^B(1); LOCK +^B(2)  → holds both
LOCK -^B(1)               → releases only ^B(1), ^B(2) still held

# Bare LOCK releases all then acquires
LOCK +^C(1); LOCK +^C(2)
LOCK ^D              → releases ^C(1) and ^C(2), acquires ^D

# Lock with timeout
LOCK +^E:0           → $TEST=1 (immediately available)

# Re-entrant locks (same process)
LOCK +^F; LOCK +^F   → count=2
LOCK -^F              → count=1 (still held)
LOCK -^F              → count=0 (fully released)

# Argumentless LOCK
LOCK                  → releases ALL held locks

# ZSHOW "L" output format
ZSHOW "L" → "MLG:2,MLT:0\nLOCK ^B(1) LEVEL=1\nLOCK ^A LEVEL=1"
```

### ^$LOCK SSVN

**Critical finding**: YDB does NOT support `^$LOCK(name)` syntax — it raises GBLNAME error. YDB uses `ZSHOW "L"` for lock introspection and the `LKE` utility for administrative lock management. The spec's FR-097 (`^$LOCK` SSVN) is a MUMPS standard feature NOT implemented by YDB.

**Decision**: Implement `^$LOCK` as m2py-specific runtime introspection (backed by SQLite lock table queries), noting it's not YDB-compatible. Alternatively, defer `^$LOCK` and implement `ZSHOW "L"` lock display instead (which m2py already partially supports).

### JOB Semantics (validated via YDB Docker)

```
# Basic JOB
JOB LABEL^ROUTINE  → spawns independent process
JOB LABEL          → spawns process in current routine (requires routine to be compiled)

# JOB within Docker container
JOB'd processes need the routine to be available as a compiled .o file
JOB CHILD^TESTJOB fails in single-file test setup (JOBFAIL error)
JOB CHILD (label-only, same routine) also requires compiled routine

# $JOB
Parent $JOB = OS PID (e.g., 1 in Docker)
Child $JOB = child's OS PID (distinct from parent)

# Independent local variables
Child process has NO access to parent's local variables
Child process starts with empty local symbol table (unless JOB actuallist provides values)

# Shared globals
Globals are database-backed in YDB — shared across all processes
```

## Current Implementation State

### What Exists (functional)

| Component | State | Notes |
|-----------|-------|-------|
| OPEN/USE/CLOSE grammar | Complete | Handles standard + GT.M syntax |
| OPEN/USE/CLOSE ASG nodes | Complete | `MOpenStatement`, `MUseStatement`, `MCloseStatement` |
| OPEN/USE/CLOSE codegen | Complete | Emits `_rt.open_device()`, `_rt.use_device()`, `_rt.close_device()` |
| `open_device()` runtime | Partial | Opens real files, maps keywords to modes, stores in `_devices` |
| `close_device()` runtime | Partial | Closes file handle, removes from `_devices`, resets `_io` |
| `use_device()` runtime | Stub | Sets `_io` string only — does NOT redirect I/O |
| `write()` | Working | Appends to `_output` list, updates `_x` — but NOT per-device |
| `read()` helpers | Working | Free functions using `sys.stdin` — NOT device-aware |
| `$IO` | Stub | Returns string `"0"` or device name, no actual device dispatch |
| `$X`/`$Y` | Partial | Updated on WRITE, not on READ, not per-device |
| `$KEY` | Partial | Set only for maxlen reads, not for basic R X |
| `$PRINCIPAL` | Stub | Returns `"0"` string, no device object |
| JOB | Thread-based | `threading.Thread`, virtual PIDs, shared `_globals` object |
| LOCK | Thread-based | `threading.Lock`/`threading.Condition`, per-thread ownership |
| Global storage | In-memory dict | `dict[str, MArray]`, thread-safe via `threading.RLock` |
| Transaction support | In-memory | Deep-copies `_globals` dict for snapshots |

### What's Missing

| Component | Needed For | Priority |
|-----------|------------|----------|
| `MUMPSDevice` abstraction | Sub-Phase 1 | P1 |
| `PrincipalDevice` | Sub-Phase 1 | P1 |
| `FileDevice` | Sub-Phase 1 | P1 |
| `TCPDevice` | Sub-Phase 1 | P3 |
| Device table with device objects | Sub-Phase 1 | P1 |
| I/O dispatch (write/read → current device) | Sub-Phase 1 | P1 |
| Per-device `$X`/`$Y`/`$KEY`/`$ZEOF` | Sub-Phase 1 | P1 |
| `$ZEOF` ISV | Sub-Phase 1 | P2 |
| SQLite global storage backend | Sub-Phase 2 | P1 |
| `subprocess.Popen`-based JOB | Sub-Phase 2 | P1 |
| SQLite lock table | Sub-Phase 3 | P2 |
| Cross-process lock manager | Sub-Phase 3 | P2 |
| Dead-process lock cleanup | Sub-Phase 3 | P2 |

### DeviceParam Keyword Analysis

The grammar already supports `DeviceParam` with keywords. Current `DEVICE_KEYWORDS` set in codegen:

```python
DEVICE_KEYWORDS = {
    "NEWVERSION", "READONLY", "APPEND", "VARIABLE", "FIXED",
    "STREAM", "NOWRAP", "WRAP", ...
}
```

OpenArg uses `Expr` instead of `DeviceParam` (unlike USE/CLOSE). Codegen compensates with hardcoded keyword detection. The analyzer loses keyword=value key names (only value survives).

### Spec Corrections Needed

1. **FR-022**: File-not-found with timeout raises an error (DEVOPENFAIL), NOT `$TEST=0`. Timeout applies to waiting for a device that exists but is unavailable. Correct the requirement.
2. **FR-097**: `^$LOCK` SSVN is NOT supported by YDB. Either implement as m2py-specific feature or replace with `ZSHOW "L"` lock display.
3. **Edge case**: "OPEN on non-existent file in read mode → error is raised" is correct, but "with timeout → $TEST=0" is incorrect. The error occurs regardless of timeout.
