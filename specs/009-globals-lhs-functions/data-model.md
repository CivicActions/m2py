# Data Model: LHS Functions & Global Variables (Spec 009)

**Date**: 2025-01-20  
**Status**: Complete

## Entity Overview

This spec introduces storage abstractions and extends codegen to handle new SET targets.

---

## Entities

### 1. GlobalStorageBackend (Protocol)

**Purpose**: Abstract interface for global variable storage (in-memory, YottaDB, IRIS).

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class GlobalStorageBackend(Protocol):
    """Protocol for MUMPS global variable storage."""
    
    def get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """Get value at global^NAME(subscripts). Returns None if undefined."""
        ...
    
    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """Set value at global^NAME(subscripts)."""
        ...
    
    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Kill node and all descendants."""
        ...
    
    def kill_all(self) -> None:
        """Kill all globals (for testing/reset)."""
        ...
    
    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """Return $DATA value: 0, 1, 10, or 11."""
        ...
    
    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """Return (name, subscripts) of last global access, or None."""
        ...
    
    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """Update naked indicator after global access."""
        ...
```

**Relationships**: 
- Used by MUMPSRuntime (composition)
- Implemented by InMemoryGlobalStorage

---

### 2. InMemoryGlobalStorage

**Purpose**: Default in-memory implementation using nested MArray structures.

```python
class InMemoryGlobalStorage:
    """In-memory global storage for testing and standalone execution."""
    
    _globals: dict[str, MArray]  # name -> MArray tree
    _naked_indicator: tuple[str, tuple[str, ...]] | None
    
    def __init__(self) -> None:
        self._globals = {}
        self._naked_indicator = None
```

**Validation Rules**:
- Global names must start with letter
- Subscripts coerced to canonical string form
- Naked indicator cleared on error/routine switch (implementation-dependent)

**State Transitions**:
```
Initial: _globals = {}, _naked_indicator = None

After S ^G(1)=5:
  _globals = {"G": MArray with [1]=5}
  _naked_indicator = ("G", ("1",))

After S ^(2)=10:
  _globals = {"G": MArray with [1]=5, [2]=10}
  _naked_indicator = ("G", ("2",))

After K ^G(1):
  _globals = {"G": MArray with [2]=10}
  _naked_indicator = ("G", ("1",))
```

---

### 3. MArray (Existing - Extended Usage)

**Purpose**: Sparse array supporting MUMPS semantics where nodes can have both value AND children.

**Current Location**: `src/m2py/runtime/__init__.py`

**Key Properties**:
```python
@dataclass
class MArray:
    value: str | None = None        # Value at this node
    _children: dict[str, MArray]    # Child nodes by subscript key
```

**Methods Used by Spec 009**:
- `__getitem__(key)` → Get child MArray (auto-vivify if needed)
- `__setitem__(key, value)` → Set child value
- `defined()` → Returns True if value is not None
- `kill()` → Clear value and all children
- `data()` → Returns $DATA code (0, 1, 10, 11)

**$DATA Logic**:
```python
def data(self) -> int:
    has_value = self.value is not None
    has_children = len(self._children) > 0
    if has_value and has_children:
        return 11
    elif has_value:
        return 1
    elif has_children:
        return 10
    else:
        return 0
```

---

### 4. LHS Function Target (Conceptual)

**Purpose**: Represent $PIECE or $EXTRACT appearing on left side of SET.

**Not a separate class** - detected by IntrinsicFunction in assignment target position.

**Detection Logic** (in codegen):
```python
if isinstance(target, IntrinsicFunction):
    if target.name in ('P', 'PIECE'):
        # LHS $PIECE
    elif target.name in ('E', 'EXTRACT'):
        # LHS $EXTRACT
    else:
        raise NotImplementedError(f"LHS function {target.name} not supported")
```

**Argument Structure**:
| Function | Arg 0 | Arg 1 | Arg 2 | Arg 3 |
|----------|-------|-------|-------|-------|
| $PIECE | variable | delimiter | piece# | (optional end) |
| $EXTRACT | variable | from | to (optional) | - |

---

## Runtime Helpers

### m_set_piece

```python
def m_set_piece(
    var_getter: Callable[[], str],
    var_setter: Callable[[str], None],
    delimiter: str,
    piece_from: int,
    piece_to: int | None,
    value: str
) -> None:
    """
    Implement $PIECE on LHS of SET.
    
    var_getter: Function to get current variable value
    var_setter: Function to set new variable value
    delimiter: Piece delimiter string
    piece_from: Starting piece (1-indexed)
    piece_to: Ending piece (1-indexed, or None for single piece)
    value: New value for the piece(s)
    """
```

### m_set_extract

```python
def m_set_extract(
    var_getter: Callable[[], str],
    var_setter: Callable[[str], None],
    from_pos: int,
    to_pos: int | None,
    value: str
) -> None:
    """
    Implement $EXTRACT on LHS of SET.
    
    var_getter: Function to get current variable value
    var_setter: Function to set new variable value
    from_pos: Starting position (1-indexed)
    to_pos: Ending position (1-indexed, or None = from_pos)
    value: Replacement string
    """
```

### m_data

```python
def m_data(array: MArray | None, subscripts: tuple[str, ...] = ()) -> int:
    """
    Implement $DATA function.
    
    Returns: 0, 1, 10, or 11
    """
```

---

## Storage Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Generated Python                          │
├─────────────────────────────────────────────────────────────────┤
│  _scope: dict[str, MArray]     │  _rt.globals: GlobalStorage    │
│  (local variables)             │  (global variables)            │
├────────────────────────────────┴────────────────────────────────┤
│                         MUMPSRuntime                            │
│  - _output: StringIO                                            │
│  - globals: GlobalStorageBackend                                │
│  - _naked_indicator: handled by globals                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Codegen Patterns

### Subscripted Local SET

```mumps
S X(1,2)=5
```

Generates:
```python
_scope.setdefault('X', MArray())[1, 2] = 5
```

### Global SET

```mumps
S ^G("a")=5
```

Generates:
```python
_rt.globals.set("G", ("a",), "5")
```

### Naked Reference SET

```mumps
S ^(2)=10
```

Generates:
```python
_rt.globals.set_naked(("2",), "10")  # Uses stored indicator
```

### LHS $PIECE

```mumps
S $P(X,"^",2)="NEW"
```

Generates:
```python
m_set_piece(
    lambda: _scope.get('X', MArray()).value or '',
    lambda v: _scope.setdefault('X', MArray()).__setattr__('value', v),
    '^', 2, None, 'NEW'
)
```

### $DATA

```mumps
W $D(X(1))
```

Generates:
```python
_rt.write(str(m_data(_scope.get('X'), ('1',))))
```

### KILL

```mumps
K X(1)
```

Generates:
```python
if 'X' in _scope:
    _scope['X'].kill_child('1')
```
