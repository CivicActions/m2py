# Data Model: Phase 4 — Large Architecture

**Date**: 2026-02-12  
**Spec**: [spec.md](spec.md)

## Entity Diagram

```
MUMPSRuntime
├── device_table: Dict[str, MUMPSDevice]     # name → device instance
├── current_device: MUMPSDevice              # active I/O target
├── principal_device: PrincipalDevice        # $PRINCIPAL, always present
└── global_storage: GlobalStorageBackend     # SQLite or InMemory
    ├── globals: SQLite table                # ^NAME → value tree
    ├── lock_table: SQLite table             # lock entries with PID ownership
    └── transaction_state: per-connection    # TSTART/TCOMMIT/TROLLBACK

MUMPSDevice (abstract)
├── name: str                                # device identifier
├── x_pos: int                               # $X for this device
├── y_pos: int                               # $Y for this device
├── key: str                                 # $KEY for this device
├── zeof: bool                               # $ZEOF for this device
├── read(maxlen, timeout) → str
├── write(data: str)
├── open(params: dict)
└── close()

PrincipalDevice(MUMPSDevice)                 # stdin/stdout wrapper
├── _stdin: IO                               # sys.stdin or mock
├── _stdout: IO                              # output buffer or sys.stdout
└── _output: list[str]                       # captured output (for testing)

FileDevice(MUMPSDevice)                      # sequential file I/O
├── _file: IO                                # Python file object
├── _mode: str                               # "r", "w", "a", "r+"
├── _stream: bool                            # STREAM mode flag
└── _record_size: int | None                 # RECORDSIZE parameter

TCPDevice(MUMPSDevice)                       # TCP client socket I/O
├── _socket: socket.socket                   # TCP connection
├── _delimiter: str                          # READ terminator
└── _connected: bool                         # connection state
```

## SQLite Schema

### Global Storage Table

```sql
CREATE TABLE globals (
    name       TEXT NOT NULL,      -- global name (without ^)
    subscripts TEXT NOT NULL,      -- JSON array of subscript keys, e.g., '["1","A"]'
    value      TEXT,               -- node value (NULL = no value, children only)
    PRIMARY KEY (name, subscripts)
);

-- For $ORDER queries (sorted enumeration)
CREATE INDEX idx_globals_order ON globals (name, subscripts);
```

### Lock Table

```sql
CREATE TABLE locks (
    lock_name   TEXT NOT NULL,     -- e.g., "A" or "B"
    subscripts  TEXT NOT NULL,     -- JSON array, e.g., '["1","2"]'
    owner_pid   INTEGER NOT NULL,  -- OS PID of the owning process
    lock_count  INTEGER NOT NULL DEFAULT 1,  -- incremental lock count
    acquired_at REAL NOT NULL,     -- time.time() when acquired
    PRIMARY KEY (lock_name, subscripts)
);

-- For hierarchical blocking queries
CREATE INDEX idx_locks_hierarchy ON locks (lock_name);
```

### Hierarchical Lock Blocking Rules

Lock `^A(1)` blocks `^A(1,x)` for all x (parent blocks children).
Lock `^A(1)` is blocked by `^A` (child is blocked by parent).

SQL query to check if a lock can be acquired:

```sql
-- Check if any parent lock is held by another process
SELECT 1 FROM locks
WHERE lock_name = ? AND owner_pid != ?
  AND (subscripts = '[]'  -- bare lock ^A blocks all children
       OR ? LIKE subscripts || '%')  -- subscripts is a prefix of requested
LIMIT 1;

-- Check if any child lock is held by another process  
SELECT 1 FROM locks
WHERE lock_name = ? AND owner_pid != ?
  AND subscripts LIKE ? || '%'  -- requested subscripts is a prefix of held
LIMIT 1;
```

## State Transitions

### Device Lifecycle

```
[Not Opened] --OPEN--> [Opened, not current]
[Opened, not current] --USE--> [Current device]
[Current device] --USE other--> [Opened, not current]
[Opened, not current] --CLOSE--> [Not Opened]
[Current device] --CLOSE--> [Not Opened] + $IO reverts to $PRINCIPAL
```

### $ZEOF State Machine

```
OPEN file:READONLY  → $ZEOF = 0
READ (data available) → $ZEOF = 0
READ (past last data) → $ZEOF = 1
CLOSE file → $ZEOF state saved with device
OPEN new file → $ZEOF = 0 for new device
```

### Lock Acquisition Flow

```
LOCK +^name[:timeout]
  1. Check SQLite lock table for conflicts:
     a. Same (name, subscripts) held by other PID? → conflict
     b. Parent subscripts held by other PID? → conflict (hierarchical)
     c. Child subscripts held by other PID? → conflict (hierarchical)
  2. If no conflict:
     a. If already held by self: increment lock_count
     b. If not held: INSERT into lock table
     c. Return True ($TEST=1 if timeout specified)
  3. If conflict:
     a. If timeout=0: Return False ($TEST=0)
     b. If timeout>0: poll with backoff until timeout
     c. If no timeout: poll indefinitely (with dead-process detection)

Dead-process detection (during poll):
  Check if owner_pid is alive via os.kill(pid, 0)
  If dead: DELETE orphaned lock, retry acquisition
```

## Validation Rules

- Device names are case-sensitive strings (file paths, "0" for $PRINCIPAL)
- `$PRINCIPAL` cannot be CLOSEd (no-op)
- READ on a write-only device raises an error
- WRITE on a read-only device raises an error
- USE on an unopened device raises an error
- Lock names match global name syntax (name + subscripts)
- Lock counts are always ≥ 1 for held locks (releasing below 0 is a no-op)
- Transaction snapshots in SQLite use savepoints for nesting
