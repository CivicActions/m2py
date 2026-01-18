# Data Model: Test Suite Consolidation & VistA Compatibility

**Spec**: 013-test-consolidation  
**Phase**: 1 - Design  
**Date**: 2026-01-17

## Overview

This spec primarily focuses on test consolidation (DELETE/CONVERT/IMPLEMENT) and feature implementation. The key data model additions are extensions to the database abstraction layer.

## Entity Definitions

### 1. GlobalStorageBackend Protocol Extensions

**Purpose**: Extend existing protocol for LOCK, transactions, and SSVNs.

**Existing Protocol** (from `src/m2py/runtime/globals.py`):
- `get`, `set`, `kill`, `kill_all`, `data`
- `order`, `query`, `incr`, `kill_node`
- Naked indicator methods

**New Methods Required**:

```python
# Lock Operations (FR-019)
def lock(
    name: str,
    subscripts: tuple[str, ...],
    timeout: float | None = None,
    lock_type: str = "+"  # "+" increment, "-" decrement
) -> bool:
    """Acquire/release lock on ^NAME(subscripts).
    
    Returns True if lock acquired, False if timeout expired.
    Updates $TEST accordingly.
    """
    ...

def unlock(self, name: str, subscripts: tuple[str, ...]) -> None:
    """Release lock on ^NAME(subscripts)."""
    ...

def unlock_all(self) -> None:
    """Release all locks held by this process."""
    ...

# Transaction Operations (FR-015)
def transaction_start(self) -> None:
    """Begin a transaction (TSTART)."""
    ...

def transaction_commit(self) -> None:
    """Commit current transaction (TCOMMIT)."""
    ...

def transaction_rollback(self) -> None:
    """Rollback current transaction (TROLLBACK)."""
    ...

def get_tlevel(self) -> int:
    """Return current transaction nesting level ($TLEVEL)."""
    ...

# SSVN Queries (FR-029)
def ssvn_global(self, subscript: str) -> str:
    """Query ^$GLOBAL(subscript) for global existence."""
    ...

def ssvn_job(self, subscript: str) -> str:
    """Query ^$JOB(subscript) for job information."""
    ...

def ssvn_lock(self, subscript: str) -> str:
    """Query ^$LOCK(subscript) for lock information."""
    ...

def ssvn_routine(self, subscript: str) -> str:
    """Query ^$ROUTINE(subscript) for routine information."""
    ...
```

### 2. Test Stub States

**Entity**: Test stub audit state (from gaps-stubs.md)

| Field | Type | Values |
|-------|------|--------|
| stub_name | str | Test function name |
| file_path | str | Test file location |
| spec_section | str | MUMPS spec reference |
| disposition | enum | DELETE, CONVERT, IMPLEMENT |
| evidence | str | Verification results |
| existing_coverage | str | Spec-aligned test location |

### 3. Intrinsic Function Registry

**New Intrinsic Functions** (FR-013, FR-014, FR-017, FR-020-021, FR-025, FR-027, FR-031):

| Function | Signature | Return Type |
|----------|-----------|-------------|
| $ASCII | `$ASCII(string, position?)` | int |
| $CHAR | `$CHAR(code, ...)` | str |
| $JUSTIFY | `$JUSTIFY(string, width, decimals?)` | str |
| $TRANSLATE | `$TRANSLATE(string, from, to?)` | str |
| $TEXT | `$TEXT(label+offset)` | str |
| $FNUMBER | `$FNUMBER(number, format, decimals?)` | str |
| $REVERSE | `$REVERSE(string)` | str |
| $NEXT | `$NEXT(subscript)` | str (deprecated) |

### 4. Math Function Registry

**New Math Functions** (FR-034 through FR-038):

| Function | Python Equivalent |
|----------|------------------|
| $EXP(x) | `math.exp(x)` |
| $LOG(x) | `math.log(x)` |
| $SQRT(x) | `math.sqrt(x)` |
| $SIN(x) | `math.sin(x)` |
| $COS(x) | `math.cos(x)` |
| $TAN(x) | `math.tan(x)` |
| $ARCSIN(x) | `math.asin(x)` |
| $ARCCOS(x) | `math.acos(x)` |
| $ARCTAN(x) | `math.atan(x)` |

## State Transitions

### Test Stub Lifecycle

```
┌─────────────┐
│   XFAIL     │ (initial state: 286 stubs)
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│              AUDIT                        │
│  Verify feature status + existing tests  │
└──────────────────────────────────────────┘
       │
       ├──────────────────┬──────────────────┐
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   DELETE    │    │   CONVERT   │    │  IMPLEMENT  │
│  ~44 stubs  │    │  ~39 stubs  │    │ ~200 stubs  │
└──────┬──────┘    └──────┬──────┘    └──────┬──────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   REMOVED   │    │  PASSING    │    │  PASSING    │
│  (verified) │    │ (runtime)   │    │  (runtime)  │
└─────────────┘    └─────────────┘    └─────────────┘
```

### Transaction State Machine

```
┌─────────────┐
│   NONE      │  ($TLEVEL = 0)
└──────┬──────┘
       │ TSTART
       ▼
┌─────────────┐
│   ACTIVE    │  ($TLEVEL = 1+)
└──────┬──────┘
       │
       ├─────────────────┐
       │ TCOMMIT         │ TROLLBACK
       ▼                 ▼
┌─────────────┐    ┌─────────────┐
│  COMMITTED  │    │ ROLLED BACK │
│  (persisted)│    │  (reverted) │
└─────────────┘    └─────────────┘
```

## Validation Rules

### Stub Deletion Rules

1. A stub can only be DELETED if spec-aligned coverage exists
2. Spec-aligned coverage must include `execute_mumps` assertions
3. DELETE requires verification via `validate.py`

### Stub Conversion Rules

1. CONVERT only applies when feature is working (validated)
2. Converted test must use `execute_mumps` fixture
3. Converted test must assert actual output, not code structure

### Implementation Rules

1. All IMPLEMENT features must pass YDB validation
2. Database operations must use abstraction layer
3. Z-commands must be fully functional (no stubs)

## Relationships

```
GlobalStorageBackend
    │
    ├── InMemoryGlobalStorage (testing)
    │       ├── lock_table: dict
    │       ├── transaction_stack: list
    │       └── ssvn_handlers: dict
    │
    ├── YottaDBBackend (production)
    │       └── uses: yottadb native API
    │
    └── IRISBackend (future)
            └── uses: intersystems-iris API

MRuntime
    │
    ├── _global_backend: GlobalStorageBackend
    ├── _test: int (0 or 1)
    ├── _source_lines: list[str]
    └── _label_lines: dict[str, int]
```

## Memory Backend Lock Table Design

For unit testing (InMemoryGlobalStorage):

```python
class InMemoryGlobalStorage:
    def __init__(self):
        self._globals: dict[str, MArray] = {}
        self._naked_indicator: tuple | None = None
        # New for FR-019
        self._lock_table: dict[tuple[str, tuple], int] = {}  # count per lock
        # New for FR-015
        self._transaction_stack: list[dict] = []  # snapshots for rollback
        self._tlevel: int = 0
```

This design allows:
- Multiple incremental locks on same resource (lock count)
- Nested transactions with independent rollback
- Thread-safe testing (single-process only)
