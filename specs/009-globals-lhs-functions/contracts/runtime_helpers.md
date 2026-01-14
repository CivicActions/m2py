# Runtime Helper Functions Contract

**Module**: `m2py.runtime.helpers`

## m_set_piece

**Purpose**: Implement LHS $PIECE assignment.

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
    Set piece(s) of a string variable.
    
    Equivalent to: SET $PIECE(var, delimiter, piece_from, piece_to) = value
    
    Args:
        var_getter: Callable returning current variable value
        var_setter: Callable to set new variable value
        delimiter: Piece delimiter string
        piece_from: Starting piece number (1-indexed)
        piece_to: Ending piece number (1-indexed), or None for single piece
        value: Replacement value
        
    Behavior:
        - If piece_from > current piece count, pads with empty pieces
        - If piece_to specified, replaces range [piece_from, piece_to]
        - delimiter="" uses each character as delimiter (implementation-specific)
    """
```

### Examples

```python
# S X="A^B^C" S $P(X,"^",2)="NEW" → X="A^NEW^C"
m_set_piece(lambda: "A^B^C", setter, "^", 2, None, "NEW")
# Result: "A^NEW^C"

# S X="" S $P(X,"^",3)="X" → X="^^X"
m_set_piece(lambda: "", setter, "^", 3, None, "X")
# Result: "^^X"

# S $P(X,"^",2,4)="REPLACED" (range replacement)
m_set_piece(lambda: "A^B^C^D^E", setter, "^", 2, 4, "REPLACED")
# Result: "A^REPLACED^E"
```

---

## m_set_extract

**Purpose**: Implement LHS $EXTRACT assignment.

```python
def m_set_extract(
    var_getter: Callable[[], str],
    var_setter: Callable[[str], None],
    from_pos: int,
    to_pos: int | None,
    value: str
) -> None:
    """
    Set character(s) of a string variable by position.
    
    Equivalent to: SET $EXTRACT(var, from_pos, to_pos) = value
    
    Args:
        var_getter: Callable returning current variable value
        var_setter: Callable to set new variable value
        from_pos: Starting position (1-indexed)
        to_pos: Ending position (1-indexed), or None (defaults to from_pos)
        value: Replacement string
        
    Behavior:
        - Positions are 1-indexed and inclusive
        - If from_pos > string length, pads with spaces
        - Replacement can be shorter or longer than original range
    """
```

### Examples

```python
# S X="HELLO" S $E(X,2,3)="XX" → X="HXXLO"
m_set_extract(lambda: "HELLO", setter, 2, 3, "XX")
# Result: "HXXLO"

# S X="HELLO" S $E(X,2,3)="ABCD" → X="HABCDLO"
m_set_extract(lambda: "HELLO", setter, 2, 3, "ABCD")
# Result: "HABCDLO"

# S X="AB" S $E(X,5)="X" → X="AB  X"
m_set_extract(lambda: "AB", setter, 5, None, "X")
# Result: "AB  X"
```

---

## m_data

**Purpose**: Implement $DATA intrinsic function.

```python
def m_data(array: MArray | None, subscripts: tuple[str, ...] = ()) -> int:
    """
    Return $DATA value for array node.
    
    Args:
        array: MArray root, or None if variable undefined
        subscripts: Path to target node (empty for root)
        
    Returns:
        0 - Node undefined, no descendants
        1 - Node defined (has value), no descendants
        10 - Node undefined, has descendants
        11 - Node defined AND has descendants
    """
```

### Examples

```python
# Empty/undefined variable
m_data(None) → 0

# X=1 (value, no children)
arr = MArray(value="1")
m_data(arr) → 1

# X(1)=2 only (no root value, has children)
arr = MArray()
arr[1] = "2"
m_data(arr) → 10

# X=1, X(1)=2 (value AND children)
arr = MArray(value="1")
arr[1] = "2"
m_data(arr) → 11
```

---

## m_data_global

**Purpose**: Implement $DATA for global variables.

```python
def m_data_global(
    globals_backend: GlobalStorageBackend,
    name: str,
    subscripts: tuple[str, ...]
) -> int:
    """
    Return $DATA value for global variable.
    
    Delegates to globals_backend.data() with naked indicator update.
    """
```

---

## Codegen Integration

These helpers are imported in generated code preamble:

```python
from m2py.runtime.helpers import m_set_piece, m_set_extract, m_data, m_data_global
```

Codegen produces calls like:

```python
# For: S $P(X,"^",2)="NEW"
m_set_piece(
    lambda: _scope.get('X', MArray()).value or '',
    lambda v: _scope.setdefault('X', MArray()).__setattr__('value', v),
    '^', 2, None, 'NEW'
)
```
