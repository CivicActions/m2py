# Intrinsic Functions API Contract

**Spec**: 010-intrinsic-functions | **Date**: 2026-01-14

## Code Generation Contract

### Expression Generator Extension

The `generate_expr()` function in `src/m2py/codegen/expressions.py` MUST dispatch to `generate_intrinsic_function()` when the expression type is `MIntrinsicFunction`.

```python
def generate_expr(expr: MExpr, ctx: "GeneratorContext") -> str:
    # ... existing handlers ...
    elif isinstance(expr, MIntrinsicFunction):
        return generate_intrinsic_function(expr, ctx)
    # ...
```

### Intrinsic Function Generator

```python
def generate_intrinsic_function(
    expr: MIntrinsicFunction,
    ctx: "GeneratorContext"
) -> str:
    """Generate Python code for MUMPS intrinsic function.
    
    Args:
        expr: MIntrinsicFunction ASG node
        ctx: Generator context
        
    Returns:
        Python expression string
        
    Raises:
        NotImplementedError: For unsupported function names
    """
```

**Behavior**:
1. Normalize function name to uppercase
2. Look up generator in `INTRINSIC_GENERATORS` dispatch table
3. Call generator with (expr, ctx)
4. Return Python expression string

## Runtime Helper Contracts

### m_piece

```python
def m_piece(
    string: str,
    delimiter: str,
    piece_from: int,
    piece_to: int | None = None
) -> str:
    """Extract piece(s) from delimited string.
    
    Args:
        string: Source string
        delimiter: Piece delimiter
        piece_from: Starting piece (1-indexed)
        piece_to: Ending piece (1-indexed), None for single piece
        
    Returns:
        Extracted piece(s), empty string if out of range
        
    Examples:
        m_piece("A^B^C", "^", 2) → "B"
        m_piece("A^B^C", "^", 2, 3) → "B^C"
        m_piece("A", "^", 3) → ""
    """
```

### m_extract

```python
def m_extract(
    string: str,
    start: int = 1,
    end: int | None = None
) -> str:
    """Extract substring (1-indexed positions).
    
    Args:
        string: Source string
        start: Starting position (1-indexed)
        end: Ending position (1-indexed), None defaults to start
        
    Returns:
        Extracted substring, empty string if out of range
        
    Examples:
        m_extract("HELLO") → "H"
        m_extract("HELLO", 2, 4) → "ELL"
        m_extract("HELLO", 100) → ""
    """
```

### m_find

```python
def m_find(
    string: str,
    target: str,
    start: int = 1
) -> int:
    """Find substring, return position AFTER match.
    
    Args:
        string: String to search
        target: Substring to find
        start: Starting position (1-indexed)
        
    Returns:
        Position after match (1-indexed), 0 if not found
        
    Examples:
        m_find("HELLO", "LL") → 5  # Position after "LL"
        m_find("HELLO", "X") → 0
        m_find("HELLO", "") → 1  # Empty string found at start
    """
```

### m_get

```python
def m_get(
    array: MArray | None,
    subscripts: tuple[str, ...] = (),
    default: str = ""
) -> str:
    """Safe variable retrieval with default.
    
    Args:
        array: MArray instance or None
        subscripts: Tuple of subscript values
        default: Default value if undefined
        
    Returns:
        Variable value or default
        
    Examples:
        m_get(None, (), "DEF") → "DEF"  # Undefined
        m_get(arr, (), "DEF") → arr.value or ""  # Defined but empty
    """
```

### m_order

```python
def m_order(
    array: MArray | None,
    subscripts: tuple[str, ...],
    direction: int = 1
) -> str:
    """Get next subscript in collation order.
    
    Args:
        array: MArray instance or None
        subscripts: Current subscript path (last is search key)
        direction: 1 for forward, -1 for reverse
        
    Returns:
        Next subscript value, empty string if none
        
    Examples:
        # arr has children at 1, 2, 3
        m_order(arr, ("",), 1) → "1"  # First key
        m_order(arr, ("1",), 1) → "2"  # Next after 1
        m_order(arr, ("3",), 1) → ""  # No more keys
        m_order(arr, ("",), -1) → "3"  # Last key (reverse)
    """
```

### m_query

```python
def m_query(
    array: MArray | None,
    var_name: str,
    subscripts: tuple[str, ...]
) -> str:
    """Get full reference of next node in depth-first traversal.
    
    Args:
        array: MArray instance or None
        var_name: Variable name for reference
        subscripts: Current position
        
    Returns:
        Full variable reference string, empty if no more nodes
        
    Examples:
        # arr(1,1)=1, arr(1,2)=2, arr(2,1)=3
        m_query(arr, "A", ("",)) → "A(1,1)"
        m_query(arr, "A", ("1", "1")) → "A(1,2)"
        m_query(arr, "A", ("2", "1")) → ""
    """
```

### m_name

```python
def m_name(
    var_name: str,
    subscripts: tuple[str, ...],
    depth: int | None = None
) -> str:
    """Convert variable reference to name string.
    
    Args:
        var_name: Variable name
        subscripts: Subscript values
        depth: Max subscript depth (None = all)
        
    Returns:
        Name string
        
    Examples:
        m_name("A", ()) → "A"
        m_name("A", ("1", "2", "3")) → "A(1,2,3)"
        m_name("A", ("1", "2", "3"), 2) → "A(1,2)"
    """
```

### m_qlength

```python
def m_qlength(name: str) -> int:
    """Count subscripts in name string.
    
    Args:
        name: Variable name string (e.g., "A(1,2,3)")
        
    Returns:
        Number of subscripts
        
    Examples:
        m_qlength("A") → 0
        m_qlength("A(1,2,3)") → 3
    """
```

### m_qsubscript

```python
def m_qsubscript(name: str, position: int) -> str:
    """Extract subscript from name string.
    
    Args:
        name: Variable name string (e.g., "A(1,2,3)")
        position: Subscript position (0 = variable name, 1+ = subscripts)
        
    Returns:
        Subscript value or variable name
        
    Examples:
        m_qsubscript("A(1,2,3)", 0) → "A"
        m_qsubscript("A(1,2,3)", 2) → "2"
        m_qsubscript("A(1,2,3)", 5) → ""
    """
```

### m_fnumber

```python
def m_fnumber(
    number: float,
    codes: str,
    decimals: int | None = None
) -> str:
    """Format number with codes.
    
    Args:
        number: Numeric value
        codes: Format codes (combination of):
            - "+" → Always show sign
            - "-" → Suppress minus sign (returns absolute value)
            - "," → Comma grouping
            - "P" → Parentheses for negatives
            - "T" → Trailing sign
        decimals: Fixed decimal places (None = natural)
        
    Returns:
        Formatted string
        
    Examples:
        m_fnumber(12345.67, ",") → "12,345.67"
        m_fnumber(-12345.67, "-") → "12345.67"
        m_fnumber(-12345.67, "P") → "(12345.67)"
    """
```

## Exception Contract

### MRuntimeError

```python
class MRuntimeError(Exception):
    """MUMPS runtime error with error code.
    
    Attributes:
        code: Error code (e.g., "SELECTFALSE")
    """
    
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(f"M-{code}: {message}" if message else f"M-{code}")
```

**Error codes**:
- `SELECTFALSE` - $SELECT with no true condition
- `RANDARGNEG` - $RANDOM with argument ≤ 0

## Generated Code Patterns

### Simple Function (inline)

```python
# $L("HELLO") →
len("HELLO")

# $C(65) →
chr(65)

# $R(10) →
random.randint(0, 9)
```

### Complex Function (helper)

```python
# $P("A^B^C","^",2) →
m_piece("A^B^C", "^", 2)

# $O(A("")) →
m_order(_scope.get('A', MArray()), ("",))

# $G(X,"DEF") →
m_get(_scope.get('X', None), (), "DEF")
```

### $SELECT Pattern

```python
# $S(A=1:"X",B=2:"Y",1:"Z") →
("X" if m_truth(m_compare(A, "=", 1)) else
 "Y" if m_truth(m_compare(B, "=", 2)) else
 "Z" if m_truth(1) else
 _raise_select_false())

def _raise_select_false():
    raise MRuntimeError("SELECTFALSE")
```
