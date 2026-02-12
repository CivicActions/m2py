# Data Model: Phase 3 — Correctness Fixes & New Features

**Branch**: `021-correctness-features` | **Date**: 2026-02-10

## Overview

Phase 3 introduces new runtime data structures for error handling, stack tracking,
transaction variable snapshots, and extended global namespaces. Unlike Phases 1–2
(which restructured existing code), Phase 3 adds new entities to the runtime and
modifies the existing scope behavior.

## New Entities

### StackFrame (Runtime Dataclass)

Stores per-level call stack information for `$STACK(n,"info")` introspection.

```python
from typing import Optional
from dataclasses import dataclass, field

@dataclass
class StackFrame:
    """A single entry in the MUMPS call stack."""
    frame_type: str          # "DO", "$$", "XECUTE", "ZINTR", "TRIGGER"
    routine: str = ""        # Routine name (e.g., "MYROUTINE")
    label: str = ""          # Label name (e.g., "MAIN")
    offset: int = 0          # Line offset from label
    mcode: str = ""          # Original MUMPS source line
    ecode: str = ""          # Error code(s) at this level (if any)
```

**Location**: `runtime/__init__.py` (inner class or module-level)

**Validation rules**:
- `frame_type` must be one of: `"DO"`, `"$$"`, `"XECUTE"`, `"ZINTR"`, `"TRIGGER"`
- `routine` and `label` may be empty for XECUTE frames
- `offset` is 0-based line offset from label

**Relationships**:
- `MUMPSRuntime._stack_frames: list[StackFrame]` — current call stack (mutable)
- `MUMPSRuntime._stack_snapshot: Optional[list[StackFrame]]` — frozen snapshot during error handling

### StackSnapshot (Runtime State)

When `$ECODE` becomes non-empty, the current stack frames are deep-copied into
a snapshot. `$STACK(n)` queries return snapshot data during error handling.
Snapshot resets only when `SET $ECODE=""` clears the error.

```python
# In MUMPSRuntime.__init__:
self._stack_frames: list[StackFrame] = []
self._stack_snapshot: Optional[list[StackFrame]] = None
self._stack_snapshot_depth: int = 0  # $STACK(-1) returns this
```

### TransactionLocalSnapshot (Runtime Dict)

Stores deep copies of specified local variables at TSTART time for TRESTART.

```python
@dataclass
class TransactionLocalSnapshot:
    """Snapshot of local variables at TSTART time."""
    restart_vars: Optional[list[str]] = None  # Named vars, or None for "not restartable"
    restart_all: bool = False                  # True for TSTART *
    snapshot: dict[str, Any] = field(default_factory=dict)  # var_name → deepcopy(MArray)
    saved_test: Optional[bool] = None         # $TEST value at TSTART
```

**Location**: `runtime/__init__.py`

**Validation rules**:
- If `restart_all` is True, `restart_vars` is ignored (all locals saved)
- `snapshot` keys are MUMPS variable names, values are deep-copied MArray objects
- If variable was undefined at TSTART time, it's recorded as `_UNDEFINED` sentinel

**Relationship**:
- `MUMPSRuntime._transaction_snapshots: list[TransactionLocalSnapshot]` — one per $TLEVEL

### ZSearchState (Runtime State)

Iterator state for successive `$ZSEARCH` calls.

```python
# In MUMPSRuntime.__init__:
self._zsearch_results: list[str] = []
self._zsearch_index: int = 0
```

## Modified Entities

### MUMPSRuntime — New ISV Fields

```python
# Error handling ISVs (additions to existing __init__)
self._ztrap: str = ""           # $ZTRAP value
self._zstatus: str = ""         # $ZSTATUS value  
self._zposition: str = ""       # $ZPOSITION value
self._in_error_handler: bool = False  # Detect nested errors

# $STACK enhancements (replace simple _stack_level counter)
self._stack_frames: list[StackFrame] = []
self._stack_snapshot: Optional[list[StackFrame]] = None

# $ETRAP level tracking
self._etrap_set_level: int = 0  # Stack level where $ETRAP was SET

# ZSYSTEM ISV
self._zsystem_exit: int = 0     # Exit code from last ZSYSTEM

# Transaction restart variable snapshots
self._transaction_snapshots: list[TransactionLocalSnapshot] = []

# $ZSEARCH state
self._zsearch_results: list[str] = []
self._zsearch_index: int = 0
```

### CurrentScope — Remove strict_mode

```python
# BEFORE
class CurrentScope:
    def __init__(self, strict_mode: bool = False):
        self._strict_mode = strict_mode
    
    def get(self, name: str, default=None) -> Any:
        result = self._vars.get(name, default)
        if result is None and self._strict_mode:
            raise LVUNDEFError(name)
        return result if result is not None else ""

# AFTER
class CurrentScope:
    def __init__(self):
        pass  # No strict_mode parameter
    
    def get(self, name: str, default=None) -> Any:
        result = self._vars.get(name, default)
        if result is None:
            raise LVUNDEFError(name)
        return result
```

**Impact**: All callers that construct `CurrentScope(strict_mode=...)` must be updated.
All tests that expect undefined locals to return empty string must be fixed.

### _handle_etrap — Enhanced Error Handler

```python
# BEFORE: Simple $ETRAP execution
def _handle_etrap(self, exception, scope):
    ecode = self._exception_to_ecode(exception)
    self.set_ecode(ecode)
    if self._etrap:
        self.execute_mumps(self._etrap)
        if not self._ecode:  # $ECODE was cleared
            return  # Implicit QUIT

# AFTER: Level-aware with $ZTRAP fallback, nested error detection
def _handle_etrap(self, exception, scope, *, 
                   routine: str = "", label: str = "", offset: int = 0):
    # 1. Populate $ZSTATUS, $ZPOSITION
    self._zstatus = self._format_zstatus(exception, routine, label, offset)
    self._zposition = f"{label}+{offset}^{routine}" if routine else ""
    
    # 2. Detect nested error
    if self._in_error_handler:
        if self._tlevel > 0:
            self.globals.transaction_rollback()  # TROLLBACK:$TLEVEL
        raise  # QUIT:$QUIT "" QUIT (unwind)
    
    # 3. Set $ECODE, freeze $STACK snapshot
    ecode = self._exception_to_ecode(exception)
    self._append_ecode(ecode)
    self._freeze_stack_snapshot()
    
    # 4. Dispatch to $ETRAP or $ZTRAP
    self._in_error_handler = True
    try:
        if self._etrap:
            self.execute_mumps(self._etrap)
        elif self._ztrap:
            self._dispatch_ztrap()
        else:
            raise  # No trap → propagate
    finally:
        self._in_error_handler = False
```

## Entity Relationship Summary

```
MUMPSRuntime
├── _stack_frames: list[StackFrame]           ← push_frame() / pop_frame()
├── _stack_snapshot: list[StackFrame]          ← frozen on error
├── _transaction_snapshots: list[TransactionLocalSnapshot]  ← one per $TLEVEL
├── _ecode / _etrap / _ztrap / _zstatus / _zposition  ← ISV storage
├── _zsearch_results / _zsearch_index         ← $ZSEARCH iterator
├── _zsystem_exit                             ← ZSYSTEM exit code
└── CurrentScope (via _scope)
    └── LVUNDEF always raised (no strict_mode)
```

## State Transitions

### Error Handling State Machine

```
NORMAL → ERROR_OCCURRED → TRAP_EXECUTING → [ECODE_CLEARED → NORMAL | UNWIND → CALLER_FRAME]
                                         → NESTED_ERROR → TROLLBACK + UNWIND
```

1. **NORMAL**: `_ecode == ""`, `_in_error_handler == False`
2. **ERROR_OCCURRED**: Exception caught → `_append_ecode()`, `_freeze_stack_snapshot()`
3. **TRAP_EXECUTING**: `_in_error_handler = True`, execute $ETRAP or $ZTRAP code
4. **ECODE_CLEARED**: Trap code did `SET $ECODE=""` → implicit QUIT, return to NORMAL
5. **UNWIND**: Trap code did QUIT without clearing $ECODE → exception propagates to caller
6. **NESTED_ERROR**: Error during step 3 → `TROLLBACK:$TLEVEL`, QUIT (unwind)

### Transaction Snapshot Lifecycle

```
TSTART (vars) → snapshot created → [TCOMMIT → snapshot discarded]
                                 → [TRESTART → locals restored from snapshot, re-execute]
                                 → [TROLLBACK → globals restored, locals NOT restored, snapshot discarded]
```
