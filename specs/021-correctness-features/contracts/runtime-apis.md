# Runtime API Contracts: Phase 3 — Correctness Fixes & New Features

These contracts define the interfaces of new and enhanced runtime methods and
codegen helpers for Phase 3 features. All are internal APIs — no external/public
API surface changes.

## Track A: Error Handling

### runtime/__init__.py — ISV Accessors

```python
def ztrap(self) -> str:
    """Return current $ZTRAP value.
    
    Returns:
        The MUMPS code or label reference set as the $ZTRAP error handler,
        or "" if not set.
    """

def set_ztrap(self, value: str) -> None:
    """Set $ZTRAP. Implicitly NEWs $ETRAP (mutual exclusion).
    
    When $ZTRAP is SET, the current $ETRAP value is saved (as if NEWed)
    and $ETRAP is cleared at this stack level. On scope exit (QUIT),
    $ETRAP is restored.
    
    Args:
        value: MUMPS code to XECUTE on error, or label reference (e.g., "ERR^ROUTINE")
    """

def zstatus(self) -> str:
    """Return $ZSTATUS — the full error message from the last error.
    
    Format: "errorcode,location^routine,%YDB-E-ERRNAME, Human readable message"
    Returns "" if no error has occurred.
    """

def zposition(self) -> str:
    """Return $ZPOSITION — the current position after error handler transfer.
    
    Format: "LABEL+offset^ROUTINE"
    Returns "" if no error has occurred.
    """

def set_zstatus(self, value: str) -> None:
    """Set $ZSTATUS (writable in YDB)."""

def set_zposition(self, value: str) -> None:
    """Set $ZPOSITION (writable in YDB)."""
```

### runtime/__init__.py — Enhanced Error Handler

```python
def _handle_etrap(self, exception: Exception, scope: "CurrentScope", *,
                   routine: str = "", label: str = "", offset: int = 0) -> None:
    """Handle a MUMPS error using $ETRAP or $ZTRAP.
    
    Enhanced from the existing implementation to add:
    1. $ZSTATUS / $ZPOSITION population
    2. Nested error detection (error during error processing)
    3. $ZTRAP fallback when $ETRAP is empty
    4. Stack snapshot freezing
    5. Level-aware stack unwinding
    
    Args:
        exception: The Python exception that occurred
        scope: Current variable scope
        routine: Routine name where error occurred
        label: Label name where error occurred
        offset: Line offset from label where error occurred
    
    Raises:
        The original exception if no trap is set, or if nested error processing
        requires stack unwinding.
    """

def _append_ecode(self, code: str) -> None:
    """Append an error code to $ECODE in the standard format.
    
    $ECODE accumulates codes: setting ",M6," when $ECODE is already ",M9,"
    produces ",M9,M6,".
    
    Args:
        code: Error code without commas (e.g., "M6", "Z150373850")
    """

def _freeze_stack_snapshot(self) -> None:
    """Deep-copy current _stack_frames to _stack_snapshot.
    
    Called when $ECODE transitions from empty to non-empty.
    The snapshot is used by $STACK(n) queries during error handling.
    Snapshot is cleared when SET $ECODE="" resets the error state.
    """

def _dispatch_ztrap(self) -> None:
    """Execute $ZTRAP code.
    
    If $ZTRAP value matches a label reference pattern (e.g., "ERR^ROUTINE"),
    transfer control via GOTO semantics. Otherwise, XECUTE the code.
    """
```

### runtime/__init__.py — $STACK Introspection

```python
def push_stack_frame(self, frame_type: str, routine: str = "",
                      label: str = "", offset: int = 0, mcode: str = "") -> None:
    """Push a new frame onto the call stack.
    
    Called at DO, XECUTE, and extrinsic function ($$) entry points.
    Replaces the simple _stack_level increment.
    
    Args:
        frame_type: One of "DO", "$$", "XECUTE", "ZINTR", "TRIGGER"
        routine: Routine name
        label: Entry label
        offset: Line offset
        mcode: Original MUMPS source line
    """

def pop_stack_frame(self) -> None:
    """Pop the top frame from the call stack.
    
    Called at QUIT/return from DO, XECUTE, or extrinsic function.
    Replaces the simple _stack_level decrement.
    """

def stack_function(self, level: int, info: str = "") -> str:
    """Implement $STACK(level[,info]) intrinsic function.
    
    During error handling ($ECODE non-empty), returns data from the frozen
    snapshot. Otherwise returns data from the live stack.
    
    Args:
        level: Stack level to query. -1 for error snapshot depth.
        info: Optional info code: "PLACE", "MCODE", "ECODE", or ""
    
    Returns:
        For level=-1: highest error frame level as string
        For level=0 with no info: implementation start info
        For level=n with no info: frame type string ("DO", "$$", etc.)
        For level=n with "PLACE": "LABEL+offset^ROUTINE"
        For level=n with "MCODE": MUMPS source line
        For level=n with "ECODE": error codes at that level
        For level > stack depth: ""
    """
```

## Track B: LOCK Indirection + TSTART Variables

### codegen/indirection.py

```python
def generate_lock_indirection(
    lock_expr: str, lockop: str, timeout_expr: Optional[str],
    ctx: "GeneratorContext"
) -> str:
    """Generate Python code for an indirected LOCK target.
    
    Follows the same pattern as other indirection generators (SET, KILL, etc.)
    or uses the Phase 2 shared _build_indirection_call() template.
    
    Args:
        lock_expr: Python expression for the indirected lock name
        lockop: Lock operation: "", "+", "-"
        timeout_expr: Optional Python expression for timeout value
        ctx: Generator context
    
    Returns:
        Python code string that calls _rt.lock_indirected()
    """
```

### runtime/__init__.py

```python
def lock_indirected(self, name_expr: str, lockop: str = "",
                     timeout: Optional[float] = None) -> None:
    """Resolve an indirected lock name and acquire/release the lock.
    
    Parses the name expression (may contain subscripts), resolves
    through multiple indirection levels if needed, and delegates to
    the existing lock()/unlock() methods.
    
    Args:
        name_expr: MUMPS name expression (e.g., "^GLO(1)")
        lockop: Lock operation - "" (exclusive), "+" (incremental), "-" (release)
        timeout: Optional timeout in seconds. Sets $TEST on timeout.
    
    Raises:
        IndirectionError: If the name cannot be parsed as a valid lock target
    """

def snapshot_locals(self, var_names: Optional[list[str]] = None,
                     all_vars: bool = False) -> None:
    """Snapshot specified local variables at TSTART time.
    
    Creates a TransactionLocalSnapshot and pushes it onto
    _transaction_snapshots. Used for TRESTART variable restoration.
    
    Args:
        var_names: List of variable names to snapshot, or None
        all_vars: If True, snapshot ALL current local variables (TSTART *)
    """

def restore_locals_from_snapshot(self) -> None:
    """Restore local variables from the most recent transaction snapshot.
    
    Called on TRESTART. Pops the snapshot and restores each
    variable to its saved value (or KILLs it if it was undefined).
    """

def discard_local_snapshot(self) -> None:
    """Discard the most recent transaction snapshot without restoring.
    
    Called on TCOMMIT or TROLLBACK (which restores globals only,
    not locals per YDB semantics).
    """
```

## Track C: $ZDATE, ZSYSTEM

### runtime/helpers.py

```python
def m_zdate(horolog: str, fmt: str = "MM/DD/YY",
            months: str = "", days: str = "") -> str:
    """Format a $HOROLOG value into a human-readable date/time string.
    
    Implements YDB's $ZDATE format codes (not IRIS numeric codes).
    
    Args:
        horolog: $HOROLOG string — either "days" or "days,seconds"
        fmt: Format string using YDB codes (MM, DD, YY, YYYY, MON, DAY,
             24, 12, 60, SS, AM). Max 64 characters.
        months: Optional comma-separated list of 12 month names
        days: Optional comma-separated list of 7 day-of-week names
    
    Returns:
        Formatted date/time string
    
    Raises:
        ValueError: If horolog is not a valid $HOROLOG value
    
    Examples:
        m_zdate("66337") → "08/16/22"
        m_zdate("66337", "YYYY-MM-DD") → "2022-08-16"
        m_zdate("66337", "DD MON YEAR") → "16 AUG 2022"
        m_zdate("66337,45296", "YYYY-MM-DD 24:60:SS") → "2022-08-16 12:34:56"
    """
```

### runtime/__init__.py

```python
def zsystem(self, command: str) -> None:
    """Execute a shell command via ZSYSTEM.
    
    Runs the command string in the default shell via subprocess.run().
    Stores the exit code in _zsystem_exit for $ZSYSTEM access.
    
    Args:
        command: Shell command string. Empty string is a no-op.
    """

def zsystem_exit(self) -> int:
    """Return exit code from last ZSYSTEM command ($ZSYSTEM ISV)."""
```

## Track D: SVNs, SSVNs, Extended Globals

### runtime/__init__.py

```python
def zsearch(self, pattern: str) -> str:
    """Implement $ZSEARCH — file system search with iterator state.
    
    First call with a non-empty pattern: performs glob.glob(pattern),
    stores results, returns first match.
    Subsequent calls with empty string: returns next match.
    Returns empty string when exhausted.
    
    Args:
        pattern: File glob pattern, or "" for next match
    
    Returns:
        Full path of matching file, or "" if no more matches
    """

def zro(self) -> str:
    """Return $ZRO — routine search path (configurable)."""

def zmessage_text(self, code: int) -> str:
    """Return error message text for a YDB error code ($ZMESSAGE function).
    
    Args:
        code: YDB error code (e.g., 150373850 for LVUNDEF)
    
    Returns:
        Human-readable error message string
    """
```

### runtime/globals.py (or runtime/__init__.py)

```python
def set_ns(self, name: str, subscripts: tuple, value: str,
            namespace: str = "") -> None:
    """Set a global variable in a specific namespace.
    
    For extended global references like ^|"MYNS"|GLO(1).
    
    Args:
        name: Global name (without ^)
        subscripts: Subscript tuple
        value: Value to set
        namespace: Namespace identifier. Empty string = default namespace.
    """

def get_ns(self, name: str, subscripts: tuple,
            namespace: str = "") -> str:
    """Get a global variable from a specific namespace.
    
    For extended global references.
    """
```

## Track E: READ #maxlen

### runtime/helpers.py

```python
def m_read_maxlen(maxlen: int) -> str:
    """Read at most maxlen characters from stdin.
    
    For piped/non-interactive input, reads up to maxlen characters.
    Returns the characters read (may be fewer if EOF or terminator).
    
    Args:
        maxlen: Maximum number of characters to read. Must be > 0.
    
    Returns:
        String of at most maxlen characters
    
    Raises:
        MUMPSError: If maxlen <= 0 (M18 error)
    """

def m_read_maxlen_timeout(maxlen: int, timeout: float) -> tuple[str, bool]:
    """Read at most maxlen characters with timeout.
    
    Combines character limit with time limit. Returns whichever
    condition is met first.
    
    Args:
        maxlen: Maximum characters to read
        timeout: Timeout in seconds
    
    Returns:
        Tuple of (characters_read, timed_out). timed_out is True if
        the timeout expired before maxlen characters were received.
    """
```
