# Runtime Library

The runtime library (`src/m2py/runtime/`) provides execution support for generated Python code. It handles everything that can't be expressed as pure Python: global variables, I/O devices, indirection resolution, XECUTE compilation, error handling, and process management.

The shared value semantics layer (`src/m2py/core/`) provides canonical implementations used by both codegen and runtime.

## MArray — MUMPS Sparse Arrays

`MArray` implements MUMPS hierarchical arrays where each node has both a **value** and **children**. This is the fundamental difference from Python dicts — in MUMPS, `A` and `A(1)` coexist as value and child.

Key behaviors:
- **Auto-vivification**: accessing `arr[1,2,3]` creates intermediate nodes as needed
- **Subscript canonicalization**: `A(1)`, `A(1.0)`, and `A("1")` all refer to the same node; `A("01")` is distinct
- **$DATA semantics**: `defined()` returns 0 (undef), 1 (value only), 10 (children only), or 11 (both)
- **MUMPS collation**: numeric subscripts sort before strings, numerics by value
- **Recursive KILL**: `kill(subscripts)` removes a node and all its descendants
- **MERGE**: `merge_from(source)` performs deep recursive merge

Tuple key access is supported: `arr[1, 2, 3] = "value"` is equivalent to navigating three subscript levels.

## MUMPSRuntime

Central runtime class — one instance per process. Created as `_rt` in generated code.

### I/O

- `write()`, `write_newline()`, `write_formfeed()`, `write_tab()` — output operations
- `read_line()`, `read_char()`, `read_maxlen()` — input with optional timeout
- Output is captured in an internal list for test validation via `get_output()`

### Device Management

- `open_device()` / `close_device()` / `use_device()` — OPEN/CLOSE/USE commands
- Each device tracks per-device ISVs: `$X`, `$Y`, `$KEY`, `$ZEOF`
- Active device set via `use_device()`, defaulting to principal (stdin/stdout)

### Global Variables

- `get_var()`, `set_var()`, `kill_var()`, `merge_var()` — dispatches to `GlobalStorageBackend`
- `get_data()`, `get_order()`, `get_query()` — `$DATA`, `$ORDER`, `$QUERY` for globals
- Naked reference tracking maintained by the storage backend

### Indirection Resolution

- `set_indirected()`, `get_indirected()`, `kill_indirected()` — dynamic variable access via `@` expressions
- `resolve_for_target()` — resolve FOR loop variable indirection
- `evaluate_argument_indirection()` — evaluate expressions in ARGUMENT context
- Uses `IndirectionResolver` from `core/indirection.py` with `IndirectionContext` (NAME vs ARGUMENT)

### XECUTE

- `execute_mumps(code, scope)` — compiles MUMPS to Python at runtime via `compile_mumps_line()` from `parser/compiler.py`, then executes with `exec()` in the caller's scope
- `$TEST` is NOT stacked during XECUTE (mutations visible to caller, unlike DO)

### Error Handling

- `$ETRAP` / `$ECODE` — ANSI standard error trapping with stack unwinding
- `$ZTRAP` / `$ZSTATUS` / `$ZPOSITION` — YottaDB-specific error handling
- Nested error detection with configurable max depth
- `LVUNDEFError` (M6 error) raised for undefined local variable access

### Stack Introspection

- `push_stack_frame()` / `pop_stack_frame()` — rich metadata frames for `$STACK`
- `stack_function(level, info)` — implements `$STACK(level, "MCODE"|"ECODE"|"PLACE"|"TYPE")`

### Transactions

- `snapshot_locals()` / `restore_locals_from_snapshot()` — TSTART/TROLLBACK local variable management
- Transaction support in global storage delegated to the backend

### JOB Subprocess Management

- `start_job()` — launches child process via `subprocess.Popen`, passing `--routine`, `--label`, `--db-path`, `--args`
- `kill_job_processes()` — cleanup on exit
- Child processes use `job_runner.py` as entry point with independent local variables but shared global storage

### Special Variables

ISV accessors include `$HOROLOG`, `$JOB`, `$IO`, `$PRINCIPAL`, `$KEY`, `$SYSTEM`, `$TEST`, `$TLEVEL`, `$ECODE`, `$ETRAP`, `$ZSTATUS`, `$ZJOB`, `$ZRO`, `$ZSEARCH`, and others.

## Cross-Routine GOTO Support

`GotoExternal` is an exception raised by generated code for external GOTOs (`G LABEL^ROUTINE`). The `run_with_goto_support()` function wraps routine execution in a loop that catches `GotoExternal`, imports the target module, and transfers control — enabling GOTO chains across routines without stack overflow.

## Global Storage Backends

The `GlobalStorageBackend` protocol defines the interface for global variable persistence. Storage is selected via the `M2PY_GLOBAL_BACKEND` environment variable or `--backend` test option.

### InMemoryGlobalStorage (default)

In-process storage using `MArray` trees. Fast, suitable for testing and standalone execution. No cross-process visibility.

### SQLiteGlobalStorage

SQLite with WAL mode for concurrent multi-process access. Features:
- ACID-compliant operations
- Custom MUMPS collation function for correct `$ORDER` ordering
- Cross-process lock coordination via `locks` table
- Transaction support (SAVEPOINT/RELEASE/ROLLBACK)
- Subscripts stored as JSON arrays

Used automatically by JOB'd subprocesses — the parent creates a SQLite database and passes its path to child processes.

### Other Backends

`yottadb` and `iris` backends are defined as stubs for future implementation.

## Device Layer

Three device types implement the `MUMPSDevice` abstract base class:

| Device | Purpose | Key Features |
|--------|---------|--------------|
| `PrincipalDevice` | stdin/stdout | Output capture for testing, `select.select()` for timeout reads |
| `FileDevice` | Sequential file I/O | NEWVERSION/READONLY/APPEND modes, STREAM/RECORDSIZE parameters |
| `TCPDevice` | TCP socket client | Buffered line reads, delimiter-based or maxlen reads, timeout support |

Each device independently tracks `$X` (column position), `$Y` (line counter), `$KEY` (terminator), and `$ZEOF`.

## Core Value Semantics (`core/`)

Shared canonical implementations used by both codegen (at compile time) and runtime (at execution time):

| Function | Module | Purpose |
|----------|--------|---------|
| `m_num(x)` | `core/values.py` | MUMPS numeric coercion (ANSI §7.1.4.5) |
| `m_str(x)` | `core/values.py` | Canonical string form (no scientific notation) |
| `m_truth(x)` | `core/values.py` | Truth evaluation (0 = false, nonzero = true) |
| `m_compare(l, op, r)` | `core/values.py` | Comparison with operator-appropriate coercion |
| `mumps_canonical_str(n)` | `core/values.py` | Number → canonical string |
| `NameTranslator` | `core/names.py` | MUMPS↔Python name translation (`%FOO` → `_pct_FOO`) |
| `SubscriptCanonicalizer` | `core/subscripts.py` | Consistent subscript key forms |
| `CurrentScope` | `core/scope.py` | Unified variable access abstraction |
| `IndirectionResolver` | `core/indirection.py` | Runtime `@`-expression resolution |
| `LVUNDEFError` | `core/exceptions.py` | M6 error — undefined local variable |
| `VarExpectedError` | `core/exceptions.py` | NAME context received expression |

## Bundled Routines

Pre-transpiled MUMPS routines are available in `runtime/routines/`:
- `MATH.py` — mathematical library functions (`%SIN`, `%COS`, `%SQRT`, etc.)
