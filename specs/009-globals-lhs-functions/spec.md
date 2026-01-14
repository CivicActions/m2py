# Feature Specification: LHS Functions & Global Variables

**Feature Branch**: `009-globals-lhs-functions`  
**Created**: 2026-01-13  
**Status**: Draft  
**Input**: Spec 009 from codegen-plan.md - LHS Functions & Global Variables

## Overview

This specification implements **left-hand-side function assignment** (SET $PIECE, SET $EXTRACT) and **global variable infrastructure** — foundational components for translating MUMPS systems that rely on in-place string modification and persistent data storage.

LHS function assignment allows modifying portions of variables in place:
```mumps
S $P(X,"^",2)="NEW"    ; Replace second ^-piece of X
S $E(X,1,3)="ABC"      ; Replace first 3 characters
```

Global variables provide persistent, tree-structured data storage:
```mumps
S ^PATIENT(123,"NAME")="DOE,JOHN"
W ^PATIENT(123,"NAME")
```

**Implementation approach**:
- LHS functions require special codegen (not standard function calls)
- Global variables use the existing `MArray` class for tree semantics
- Pluggable storage backends enable testing (InMemory) and production (YottaDB, IRIS)
- Subscripted local variables also use `MArray` for consistent array semantics

## Pre-requisites from Specs 007/008

The following infrastructure is available:

| Component | Status | Details |
|-----------|--------|---------|
| `MArray` class | ✅ Runtime | MUMPS sparse array with value+children at each node |
| Line dispatch (`_line_map`) | ✅ Spec 007 | For computed offset validation tests |
| Module loading | ✅ Spec 008 | For cross-routine global access tests |
| `_scope` dictionary | ✅ Spec 008 | For cross-routine variable visibility |
| `MGlobal` ASG node | ✅ Parser | Global variable references parsed |
| `MNakedGlobal` ASG node | ✅ Parser | Naked global references parsed |
| `MVariable.subscripts` | ✅ Parser | Subscripted variable references parsed |

## User Scenarios & Testing *(mandatory)*

### User Story 1 - LHS $PIECE Assignment (Priority: P1)

As a developer, when I generate Python from MUMPS code with `S $P(X,delim,pos)=value`, the code generator produces working Python that modifies the specified piece of the variable in-place, creating the variable if undefined and padding with delimiters if needed.

**Why this priority**: LHS $PIECE is the most common in-place modification pattern in MUMPS. VistA uses it extensively for parsing and modifying delimited data structures like HL7 messages and FileMan records.

**Independent Test**: Can be tested with simple variable manipulation without needing globals or external calls.

**YottaDB Verified Behavior**:
```
S X="A^B^C" S $P(X,"^",2)="NEW" W X → "A^NEW^C"
S $P(Y,"^",3)="C" W Y → "^^C" (pads with delimiters)
```

**Acceptance Scenarios**:

1. **Given** `S X="A^B^C" S $P(X,"^",2)="NEW" W X,! Q`, **When** generated and executed, **Then** output is "A^NEW^C\n"
2. **Given** `S $P(Y,"^",3)="C" W Y,! Q` (Y undefined), **When** generated and executed, **Then** output is "^^C\n" (created with padding)
3. **Given** `S X="A" S $P(X,"^",3)="C" W X,! Q`, **When** generated and executed, **Then** output is "A^^C\n" (pads to reach piece 3)
4. **Given** `S X="A^B^C^D^E" S $P(X,"^",2,4)="X" W X,! Q`, **When** generated and executed, **Then** output is "A^X^E\n" (range replacement collapses pieces 2-4)
5. **Given** `S $P(^G,"^",2)="B" W ^G,! Q`, **When** generated and executed, **Then** output is "^B\n" (works on globals) *(Note: Requires US4 globals infrastructure)*

---

### User Story 2 - LHS $EXTRACT Assignment (Priority: P1)

As a developer, when I generate Python from MUMPS code with `S $E(X,start,end)=value`, the code generator produces working Python that modifies the specified substring of the variable in-place, creating the variable if undefined and padding with spaces if needed.

**Why this priority**: LHS $EXTRACT is the second most common in-place modification pattern. Used for fixed-width field manipulation and character-level string editing.

**Independent Test**: Can be tested with simple variable manipulation.

**YottaDB Verified Behavior**:
```
S X="HELLO" S $E(X,1,2)="YO" W X → "YOLLO"
S $E(Z,1,3)="ABC" W Z → "ABC" (creates variable)
S W="AB" S $E(W,5,6)="XY" W W → "AB  XY" (pads with spaces)
```

**Acceptance Scenarios**:

1. **Given** `S X="HELLO" S $E(X,1,2)="YO" W X,! Q`, **When** generated and executed, **Then** output is "YOLLO\n"
2. **Given** `S $E(Z,1,3)="ABC" W Z,! Q` (Z undefined), **When** generated and executed, **Then** output is "ABC\n"
3. **Given** `S W="AB" S $E(W,5,6)="XY" W W,! Q`, **When** generated and executed, **Then** output is "AB  XY\n" (space padding)
4. **Given** `S X="ABCDE" S $E(X,2)="X" W X,! Q`, **When** generated and executed, **Then** output is "AXCDE\n" (single position)
5. **Given** `S X="ABC" S $E(X,1,5)="HELLO" W X,! Q`, **When** generated and executed, **Then** output is "HELLO\n" (replacement longer than original range)

---

### User Story 3 - Subscripted Local Variables (Priority: P1)

As a developer, when I generate Python from MUMPS code with subscripted local variables like `X(1,2)`, the code generator produces working Python using MArray that correctly handles the MUMPS array model where each node can have both a value AND children.

**Why this priority**: Subscripted locals are fundamental to MUMPS programming. Nearly every non-trivial MUMPS program uses arrays. The MArray class already exists; this enables codegen support.

**Independent Test**: Can be tested with local array manipulation only.

**YottaDB Verified Behavior**:
```
S X(1)=1 S X(1,2)=2 W X(1)," ",X(1,2) → "1 2"
S X=1 S X(1)=2 W X," ",X(1) → "1 2" (both value AND child)
```

**Acceptance Scenarios**:

1. **Given** `S X(1)=1 W X(1),! Q`, **When** generated and executed, **Then** output is "1\n"
2. **Given** `S X(1,2)=2 W X(1,2),! Q`, **When** generated and executed, **Then** output is "2\n"
3. **Given** `S X=1 S X(1)=2 W X," ",X(1),! Q`, **When** generated and executed, **Then** output is "1 2\n" (value AND children)
4. **Given** `S A("key")="value" W A("key"),! Q`, **When** generated and executed, **Then** output is "value\n" (string subscripts)
5. **Given** `W X(99),! Q` (X(99) undefined), **When** generated and executed, **Then** output is "\n" (empty string for undefined)

---

### User Story 4 - Global Variable SET/READ (Priority: P1)

As a developer, when I generate Python from MUMPS code with global variables like `^GLOBAL` and `^DATA(1,2)`, the code generator produces working Python that uses the configured global storage backend to persist and retrieve values.

**Why this priority**: Global variables are the MUMPS database. Without globals, no data persistence is possible. This is the foundation for all database operations.

**Independent Test**: Can be tested with InMemoryGlobalStorage backend.

**YottaDB Verified Behavior**:
```
S ^A(1,2)=1 W ^A(1,2) → "1"
S ^G=1 S ^G(1)=2 S ^G(1,2)=3 W $D(^G)," ",$D(^G(1))," ",$D(^G(1,2)) → "11 11 1"
```

**Acceptance Scenarios**:

1. **Given** `S ^A=1 W ^A,! Q`, **When** generated and executed (InMemory backend), **Then** output is "1\n"
2. **Given** `S ^A(1,2)=1 W ^A(1,2),! Q`, **When** generated and executed, **Then** output is "1\n"
3. **Given** `S ^G=1 S ^G(1)=2 W ^G," ",^G(1),! Q`, **When** generated and executed, **Then** output is "1 2\n" (value AND children)
4. **Given** `W ^UNDEFINED,! Q`, **When** generated and executed, **Then** output is "\n" (empty for undefined global)
5. **Given** `S ^DATA("NAME")="John" W ^DATA("NAME"),! Q`, **When** generated and executed, **Then** output is "John\n" (string subscripts)

---

### User Story 5 - Naked Global References (Priority: P2)

As a developer, when I generate Python from MUMPS code with naked global references like `^(subscripts)`, the code generator produces working Python that uses runtime tracking of the "naked indicator" (last global name and subscripts) to resolve the full reference.

**Why this priority**: Naked references are a MUMPS optimization pattern used extensively in VistA for efficient database traversal. Without this, many VistA routines won't work.

**Independent Test**: Requires globals from Story 4.

**YottaDB Verified Behavior**:
```
S ^A(1,2)=1 S ^(3)=2 W ^A(1,3) → "2" (naked replaces last subscript)
```

**Acceptance Scenarios**:

1. **Given** `S ^A(1,2)=1 S ^(3)=2 W ^A(1,3),! Q`, **When** generated and executed, **Then** output is "2\n"
2. **Given** `S ^B(1,2,3)=1 S ^(4)=2 W ^B(1,2,4),! Q`, **When** generated and executed, **Then** output is "2\n"
3. **Given** `S ^C(1,2)=1 S ^(3,4)=2 W ^C(1,3,4),! Q`, **When** generated and executed, **Then** output is "2\n" (multiple new subscripts)
4. **Given** `S ^D(1)=1 W ^(1),! Q`, **When** generated and executed, **Then** output is "1\n" (naked read)
5. **Given** `S ^E(1,2)=1 S ^F(3,4)=2 S ^(5)=3 W ^F(3,5),! Q`, **When** generated and executed, **Then** output is "3\n" (naked follows last global accessed)

---

### User Story 6 - $DATA Function for Globals/Arrays (Priority: P2)

As a developer, when I use `$DATA(var)` to check variable existence, the code generator produces working Python that returns the correct existence code (0, 1, 10, or 11) for both local arrays and global variables.

**Why this priority**: $DATA is essential for conditional logic that checks whether data exists before accessing it. Required for most non-trivial MUMPS programs.

**Independent Test**: Requires subscripted variables and globals.

**YottaDB Verified Behavior**:
```
S ^G=1 S ^G(1)=2 S ^G(1,2)=3
W $D(^G)," ",$D(^G(1))," ",$D(^G(1,2)) → "11 11 1"
```

**Acceptance Scenarios**:

1. **Given** `W $D(UNDEF),! Q`, **When** generated and executed, **Then** output is "0\n" (undefined)
2. **Given** `S X=1 W $D(X),! Q`, **When** generated and executed, **Then** output is "1\n" (value only)
3. **Given** `S X(1)=1 W $D(X),! Q`, **When** generated and executed, **Then** output is "10\n" (children only)
4. **Given** `S X=1 S X(1)=2 W $D(X),! Q`, **When** generated and executed, **Then** output is "11\n" (both)
5. **Given** `S ^G=1 S ^G(1)=2 W $D(^G),! Q`, **When** generated and executed, **Then** output is "11\n" (works on globals)

---

### User Story 7 - Global Storage Backend Configuration (Priority: P2)

As a developer, I can configure which global storage backend to use (InMemory for tests, YottaDB for YDB-backed systems, IRIS for InterSystems systems) via environment variable or programmatic API.

**Why this priority**: Backend pluggability enables fast testing with InMemory while supporting production databases. Without this, all tests would require a real database.

**Independent Test**: Can be tested by instantiating different backends.

**Acceptance Scenarios**:

1. **Given** `M2PY_GLOBAL_BACKEND=inmemory` environment variable, **When** runtime initialized, **Then** InMemoryGlobalStorage is used
2. **Given** `MUMPSRuntime(global_storage=YottaDBGlobalStorage())` programmatic API, **When** globals accessed, **Then** YottaDB database operations occur
3. **Given** no configuration, **When** runtime initialized, **Then** InMemoryGlobalStorage is used (default)
4. **Given** `M2PY_GLOBAL_BACKEND=yottadb` but yottadb package not installed, **When** runtime initialized, **Then** ImportError raised with helpful message

---

### User Story 8 - KILL for Globals/Arrays (Priority: P3)

As a developer, when I use `KILL variable` or `KILL ^global(subscripts)`, the code generator produces working Python that deletes the node and all its descendants.

**Why this priority**: KILL is needed for data cleanup and is fundamental to MUMPS, but less common than SET/READ operations.

**Independent Test**: Requires globals and subscripted variables.

**Acceptance Scenarios**:

1. **Given** `S X=1 K X W $D(X),! Q`, **When** generated and executed, **Then** output is "0\n" (simple variable, no children)
2. **Given** `S X(1)=1 S X(1,2)=2 K X(1) W $D(X(1))," ",$D(X(1,2)),! Q`, **When** generated and executed, **Then** output is "0 0\n" (kills descendants)
3. **Given** `S ^G(1)=1 S ^G(1,2)=2 K ^G(1) W $D(^G(1)),! Q`, **When** generated and executed, **Then** output is "0\n"
4. **Given** `S ^H=1 S ^H(1)=2 K ^H W $D(^H),! Q`, **When** generated and executed, **Then** output is "0\n" (kills entire tree)

---

### Edge Cases

- What happens when LHS $PIECE piece number is 0 or negative? → Error per MUMPS spec
- What happens when LHS $EXTRACT start > end? → No modification (per YDB behavior)
- What happens when naked reference used before any global access? → Error - naked indicator undefined
- What happens when global name contains special characters? → Only valid MUMPS names accepted
- What happens with very deep subscript nesting? → Works up to backend limits (YDB: 31 subscripts max, IRIS: 255, InMemory: unlimited)
- What happens when global storage backend connection fails? → Raise clear exception with backend name

## Requirements *(mandatory)*

### Functional Requirements

**LHS Functions:**
- **FR-001**: System MUST support `S $P(var,delim,pos)=value` for single piece replacement
- **FR-002**: System MUST support `S $P(var,delim,from,to)=value` for piece range replacement
- **FR-003**: System MUST create variable if undefined when LHS $PIECE assigns
- **FR-004**: System MUST pad with delimiter characters when LHS $PIECE position > current piece count
- **FR-005**: System MUST support `S $E(var,start,end)=value` for substring replacement
- **FR-006**: System MUST support `S $E(var,pos)=value` for single character replacement
- **FR-007**: System MUST create variable if undefined when LHS $EXTRACT assigns
- **FR-008**: System MUST pad with spaces when LHS $EXTRACT position > current string length
- **FR-009**: LHS functions MUST work on global variables as well as locals

**Subscripted Local Variables:**
- **FR-010**: System MUST support subscripted local variable SET: `S X(1,2)=value`
- **FR-011**: System MUST support subscripted local variable READ: `W X(1,2)`
- **FR-012**: System MUST support nodes having BOTH value AND children (MArray semantics)
- **FR-013**: System MUST return empty string for undefined subscripted variables
- **FR-014**: System MUST support string subscripts: `S X("key")=value`

**Global Variables:**
- **FR-015**: System MUST support global variable SET: `S ^NAME=value`, `S ^NAME(subs)=value`
- **FR-016**: System MUST support global variable READ: `W ^NAME`, `W ^NAME(subs)`
- **FR-017**: System MUST use MArray-like tree semantics for globals (value+children)
- **FR-018**: System MUST return empty string for undefined global nodes
- **FR-019**: System MUST support string subscripts in globals

**Naked Global References:**
- **FR-020**: System MUST track "naked indicator" (last global name + subscript path)
- **FR-021**: System MUST resolve `^(subscripts)` using naked indicator
- **FR-022**: System MUST update naked indicator on every global access (SET or READ)
- **FR-023**: System MUST raise error if naked reference used before any global access

**Storage Backend:**
- **FR-024**: System MUST provide `GlobalStorageBackend` protocol/interface
- **FR-025**: System MUST provide `InMemoryGlobalStorage` implementation (default)
- **FR-026**: System SHOULD provide `YottaDBGlobalStorage` stub (raises ImportError with helpful message if yottadb package not installed; functional implementation deferred to integration testing spec)
- **FR-027**: System SHOULD provide `IRISGlobalStorage` stub (raises ImportError with helpful message if iris package not installed; functional implementation deferred to integration testing spec)
- **FR-028**: System MUST support backend configuration via `M2PY_GLOBAL_BACKEND` environment variable
- **FR-029**: System MUST support programmatic backend configuration via `MUMPSRuntime(global_storage=...)`

### GlobalStorageBackend Protocol Specification

The `GlobalStorageBackend` protocol defines the interface for pluggable global storage. Each implementation maps MUMPS global semantics to the underlying storage system.

```python
from typing import Protocol, Optional, Tuple, Iterator, Any

class GlobalStorageBackend(Protocol):
    """Protocol for MUMPS global variable storage backends."""
    
    def get(self, name: str, subscripts: Tuple[str, ...] = ()) -> Optional[str]:
        """Get value at global node. Returns None if undefined."""
        ...
    
    def set(self, name: str, subscripts: Tuple[str, ...], value: str) -> None:
        """Set value at global node. Creates intermediate nodes as needed."""
        ...
    
    def kill(self, name: str, subscripts: Tuple[str, ...] = ()) -> None:
        """Delete node and all descendants."""
        ...
    
    def kill_node(self, name: str, subscripts: Tuple[str, ...] = ()) -> None:
        """Delete only the value at node, preserving descendants."""
        ...
    
    def data(self, name: str, subscripts: Tuple[str, ...] = ()) -> int:
        """Return existence code: 0=undefined, 1=value, 10=children, 11=both."""
        ...
    
    def order(self, name: str, subscripts: Tuple[str, ...], direction: int = 1) -> Optional[str]:
        """Return next/previous subscript at same level. None if end reached."""
        ...
    
    def query(self, name: str, subscripts: Tuple[str, ...] = ()) -> Optional[Tuple[str, ...]]:
        """Return full subscript path of next node in tree order. None if end."""
        ...
    
    def incr(self, name: str, subscripts: Tuple[str, ...], increment: str = "1") -> str:
        """Atomically increment value, return new value."""
        ...
```

### YottaDB Python API Reference

The `yottadb` Python package provides direct access to YottaDB globals. Installation requires a working YottaDB installation.

**Package**: `yottadb` (PyPI: yottadb)
**Docs**: https://docs.yottadb.com/MultiLangProgGuide/pythonprogram.html

| MUMPS Operation | YottaDB Python API | Notes |
|-----------------|-------------------|-------|
| `S ^G(a,b)=x` | `yottadb.set("^G", ("a", "b"), x)` | varname includes `^`, subscripts as tuple |
| `W ^G(a,b)` | `yottadb.get("^G", ("a", "b"))` | Returns `bytes` or `None` |
| `K ^G(a)` | `yottadb.delete_tree("^G", ("a",))` | Deletes node + all descendants |
| `K ^G(a)` (value only) | `yottadb.delete_node("^G", ("a",))` | Deletes value, keeps descendants |
| `$D(^G(a))` | `yottadb.data("^G", ("a",))` | Returns 0, 1, 10, or 11 |
| `$O(^G(a))` | `yottadb.subscript_next("^G", ("a",))` | Returns `bytes` or raises `YDBNodeEnd` |
| `$O(^G(a),-1)` | `yottadb.subscript_previous("^G", ("a",))` | Reverse order |
| `$Q(^G(a))` | `yottadb.node_next("^G", ("a",))` | Returns subscript tuple or raises `YDBNodeEnd` |
| `$I(^G)` | `yottadb.incr("^G", (), "1")` | Atomic increment, returns `bytes` |

**Key Implementation Notes:**
- All YottaDB values are returned as `bytes`, not `str` - decode with `.decode('utf-8')`
- Subscript arrays must be tuples: `("a", "b")` not `["a", "b"]`
- Global names include the `^` prefix
- `YDBNodeEnd` exception signals end of iteration (not an error)
- `None` return from `get()` indicates undefined node (no exception)

**Stub Implementation:**
```python
class YottaDBGlobalStorage:
    """YottaDB-backed global storage. Requires yottadb package."""
    
    def __init__(self):
        try:
            import yottadb
            self._ydb = yottadb
        except ImportError:
            raise ImportError(
                "YottaDB Python wrapper not installed. "
                "Install with: pip install yottadb "
                "(requires YottaDB database to be installed)"
            )
    
    def get(self, name: str, subscripts: Tuple[str, ...] = ()) -> Optional[str]:
        result = self._ydb.get(f"^{name}", subscripts)
        return result.decode('utf-8') if result is not None else None
    
    def set(self, name: str, subscripts: Tuple[str, ...], value: str) -> None:
        self._ydb.set(f"^{name}", subscripts, value)
    
    def kill(self, name: str, subscripts: Tuple[str, ...] = ()) -> None:
        self._ydb.delete_tree(f"^{name}", subscripts)
    
    def kill_node(self, name: str, subscripts: Tuple[str, ...] = ()) -> None:
        self._ydb.delete_node(f"^{name}", subscripts)
    
    def data(self, name: str, subscripts: Tuple[str, ...] = ()) -> int:
        return self._ydb.data(f"^{name}", subscripts)
    
    def order(self, name: str, subscripts: Tuple[str, ...], direction: int = 1) -> Optional[str]:
        try:
            if direction >= 0:
                result = self._ydb.subscript_next(f"^{name}", subscripts)
            else:
                result = self._ydb.subscript_previous(f"^{name}", subscripts)
            return result.decode('utf-8')
        except self._ydb.YDBNodeEnd:
            return None
    
    def query(self, name: str, subscripts: Tuple[str, ...] = ()) -> Optional[Tuple[str, ...]]:
        try:
            result = self._ydb.node_next(f"^{name}", subscripts)
            return tuple(s.decode('utf-8') for s in result)
        except self._ydb.YDBNodeEnd:
            return None
    
    def incr(self, name: str, subscripts: Tuple[str, ...], increment: str = "1") -> str:
        result = self._ydb.incr(f"^{name}", subscripts, increment)
        return result.decode('utf-8')
```

### InterSystems IRIS Python API Reference

The `iris` (intersystems-iris) package provides access to IRIS globals via Native SDK.

**Package**: `iris` (PyPI: intersystems-iris or intersystems-irispython)
**Docs**: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT

| MUMPS Operation | IRIS Python API | Notes |
|-----------------|-----------------|-------|
| `S ^G(a,b)=x` | `irispy.set(x, "G", "a", "b")` | value first, then name+subscripts (no `^`) |
| `W ^G(a,b)` | `irispy.get("G", "a", "b")` | Returns value or `None` |
| `K ^G(a)` | `irispy.kill("G", "a")` | Deletes node + all descendants |
| `$D(^G(a))` | `irispy.isDefined("G", "a")` | Returns 0, 1, 10, or 11 |
| `$O(^G(a))` | `irispy.nextSubscript(False, "G", "a")` | Returns subscript or `None` |
| `$O(^G(a),-1)` | `irispy.nextSubscript(True, "G", "a")` | True = reverse direction |
| `$I(^G)` | `irispy.increment(1, "G")` | Atomic increment, returns new value |

**Connection Setup:**
```python
import iris
conn = iris.connect("localhost", 1972, "USER", "_SYSTEM", "SYS")
irispy = iris.createIRIS(conn)
```

**Key Implementation Notes:**
- Global names do NOT include `^` prefix (unlike YottaDB)
- `set()` takes value as FIRST argument: `set(value, name, *subscripts)`
- Subscripts are passed as *args, not tuple: `get("G", "a", "b")` not `get("G", ("a", "b"))`
- `nextSubscript()` takes boolean reversed as first arg
- No separate "delete value only" - only full tree delete with `kill()`
- Connection must be established before any operations

**Stub Implementation:**
```python
class IRISGlobalStorage:
    """InterSystems IRIS-backed global storage. Requires iris package."""
    
    def __init__(self, hostname: str = "localhost", port: int = 1972,
                 namespace: str = "USER", username: str = "_SYSTEM", 
                 password: str = "SYS"):
        try:
            import iris
            self._iris_module = iris
            self._conn = iris.connect(hostname, port, namespace, username, password)
            self._irispy = iris.createIRIS(self._conn)
        except ImportError:
            raise ImportError(
                "InterSystems IRIS Python SDK not installed. "
                "Install with: pip install intersystems-irispython "
                "(requires IRIS database connection)"
            )
    
    def get(self, name: str, subscripts: Tuple[str, ...] = ()) -> Optional[str]:
        result = self._irispy.get(name, *subscripts)
        return str(result) if result is not None else None
    
    def set(self, name: str, subscripts: Tuple[str, ...], value: str) -> None:
        self._irispy.set(value, name, *subscripts)
    
    def kill(self, name: str, subscripts: Tuple[str, ...] = ()) -> None:
        self._irispy.kill(name, *subscripts)
    
    def kill_node(self, name: str, subscripts: Tuple[str, ...] = ()) -> None:
        # IRIS doesn't have delete_node equivalent - must implement manually
        # by reading children, deleting, and restoring children
        raise NotImplementedError("IRIS SDK doesn't support delete_node directly")
    
    def data(self, name: str, subscripts: Tuple[str, ...] = ()) -> int:
        return self._irispy.isDefined(name, *subscripts)
    
    def order(self, name: str, subscripts: Tuple[str, ...], direction: int = 1) -> Optional[str]:
        # nextSubscript(reversed, globalName, *subscripts)
        result = self._irispy.nextSubscript(direction < 0, name, *subscripts)
        return str(result) if result is not None else None
    
    def query(self, name: str, subscripts: Tuple[str, ...] = ()) -> Optional[Tuple[str, ...]]:
        # IRIS doesn't have direct $QUERY equivalent - must implement via iteration
        raise NotImplementedError("$QUERY not directly available in IRIS SDK")
    
    def incr(self, name: str, subscripts: Tuple[str, ...], increment: str = "1") -> str:
        result = self._irispy.increment(int(increment), name, *subscripts)
        return str(result)
    
    def close(self):
        """Close the IRIS connection."""
        if self._conn:
            self._conn.close()
```

### API Differences Summary

| Feature | YottaDB | IRIS |
|---------|---------|------|
| Package | `yottadb` | `iris` |
| Global name format | `"^NAME"` (with caret) | `"NAME"` (no caret) |
| Subscript format | Tuple: `("a", "b")` | *args: `"a", "b"` |
| set() signature | `set(name, subs, value)` | `set(value, name, *subs)` |
| Undefined read | Returns `None` | Returns `None` |
| End of iteration | Raises `YDBNodeEnd` | Returns `None` |
| Return types | `bytes` | Native Python types |
| Connection | Implicit (env vars) | Explicit `connect()` |
| delete_node | ✅ Supported | ❌ Not supported |
| $QUERY equivalent | `node_next()` | ❌ Not directly available |

**Data Functions (subset for this spec):**
- **FR-030**: System MUST support `$DATA(var)` returning 0, 1, 10, or 11 for local arrays
- **FR-031**: System MUST support `$DATA(^global)` returning 0, 1, 10, or 11 for globals
- **FR-032**: System MUST support `KILL var` and `KILL ^global` for deletion

### Key Entities

- **MArray**: MUMPS sparse array class where each node can have value AND children. Already exists in `src/m2py/runtime/__init__.py`.
- **GlobalStorageBackend**: Protocol defining `get()`, `set()`, `kill()`, `is_defined()`, `order()`, `query()` methods for global storage.
- **InMemoryGlobalStorage**: Default backend using MArray trees in memory. Fast, isolated, no persistence.
- **NakedIndicator**: Runtime state tracking last global name and subscript path (all but last subscript).

**Terminology**: "Naked indicator" refers to the runtime state (name + subscripts). "Naked reference" refers to the MUMPS syntax `^(subscripts)` that uses the naked indicator.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: LHS $PIECE scenarios produce correct output matching YottaDB
- **SC-002**: LHS $EXTRACT scenarios produce correct output matching YottaDB
- **SC-003**: Subscripted local variable scenarios produce correct output matching YottaDB
- **SC-004**: Global variable SET/READ scenarios produce correct output (InMemory backend)
- **SC-005**: Naked global reference scenarios produce correct output matching YottaDB
- **SC-006**: $DATA returns correct values (0, 1, 10, 11) for all node states
- **SC-007**: KILL removes nodes and all descendants correctly
- **SC-008**: Backend switching via environment variable works correctly
- **SC-009**: Generated Python remains syntactically valid (`ast.parse()` succeeds)
- **SC-010**: Unit tests complete in under 5 seconds (InMemory backend performance)

## Assumptions

1. Parser already captures `MGlobal`, `MNakedGlobal`, and `MVariable.subscripts` - no parser changes needed for basic globals/arrays
2. Parser already captures LHS function calls in SET command (need to verify ASG structure)
3. MArray class in runtime already provides correct value+children semantics
4. Global subscript ordering follows MUMPS collation rules (numeric before string, ascending)
5. InMemoryGlobalStorage is sufficient for spec validation; real database testing is optional
6. Extended global references (`^|"env"|NAME`, `^["gld"]NAME`) are deferred to a later spec
7. Transaction/lock semantics are out of scope (deferred to later spec)

## Integration Testing Requirements

The stub implementations above are sufficient for this spec's implementation. However, **production integration testing** requires:

### YottaDB Integration Testing
- **Environment**: Docker container with YottaDB installed (use existing `ydb` image)
- **Package**: `pip install yottadb` inside container
- **Test approach**: 
  1. Run generated Python code in YDB container
  2. Compare globals values via direct YDB access
  3. Verify round-trip: MUMPS→Python→YDB→MUMPS reads match

### IRIS Integration Testing  
- **Environment**: Docker container with IRIS Community Edition
- **Package**: `pip install intersystems-irispython`
- **Test approach**:
  1. Connect to IRIS via Native SDK
  2. Run generated Python code with IRIS backend
  3. Verify globals via ObjectScript or SQL access

### Testing Without Database (This Spec)
- **InMemoryGlobalStorage**: Default for all unit tests
- **Mock backends**: Can verify API calls without real database
- **Behavioral tests**: Validate correct method signatures called

**Recommendation**: Create Spec 015 (or similar) for "Production Database Integration Testing" that:
1. Sets up CI/CD pipeline with Docker-based YDB and IRIS containers
2. Runs integration test suite against real databases
3. Validates backend implementations work correctly in production
4. Tests edge cases like connection failures, timeouts, encoding issues

## Explicitly Out of Scope (Deferred to Later Specs)

**Spec 010** (Intrinsic Functions):
- $ORDER function (next subscript traversal)
- $QUERY function (tree walk)
- $GET function with default (safe read)
- $NAME function (variable name as string)
- Most other intrinsic functions

**Spec 011** (Extended Operators & Commands):
- Exclusive NEW/KILL: `N (A,B)`, `K (X,Y)`
- MERGE command: `M dest=src`
- Multiple targets in KILL: `K A,B,C`

**Spec 012** (Indirection & XECUTE):
- Indirect global references: `S @"^"_NAME=1`
- XECUTE with global access

**Future Specs**:
- Extended global references with environment: `^|"env"|NAME`
- Transaction support (TSTART, TCOMMIT, TROLLBACK)
- LOCK command for concurrency
- Global subscript ordering customization
