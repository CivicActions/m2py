# Data Model: Intrinsic Functions

**Spec**: 010-intrinsic-functions | **Date**: 2026-01-14

## Core Entities

### MIntrinsicFunction (existing ASG node)

MUMPS intrinsic function call representation.

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Function name without `$` prefix (e.g., "LENGTH", "L") |
| `arguments` | `List[MExpr]` | Function arguments as ASG expressions |

**Relationships**:
- Extends `MExpr` (base expression class)
- Arguments are `MExpr` instances (may be any expression type)

### MSelectArg (existing ASG node)

$SELECT function condition:value pair.

| Field | Type | Description |
|-------|------|-------------|
| `condition` | `MExpr` | Boolean expression (tvexpr) |
| `value` | `MExpr` | Value returned if condition is true |

**Relationships**:
- Used only as argument elements in $SELECT MIntrinsicFunction
- Both fields are `MExpr` instances

### MRuntimeError (new exception class)

MUMPS runtime error with error code.

| Field | Type | Description |
|-------|------|-------------|
| `code` | `str` | Error code (e.g., "SELECTFALSE", "RANDARGNEG") |
| `message` | `str` | Optional detailed message |

**Location**: `src/m2py/runtime/exceptions.py` (new file)

## Function Dispatch Table

Map from function name (uppercase) to generator function.

```python
INTRINSIC_GENERATORS = {
    # String functions
    "L": _gen_length,
    "LENGTH": _gen_length,
    "P": _gen_piece,
    "PIECE": _gen_piece,
    "E": _gen_extract,
    "EXTRACT": _gen_extract,
    "F": _gen_find,
    "FIND": _gen_find,
    "TR": _gen_translate,
    "TRANSLATE": _gen_translate,
    "J": _gen_justify,
    "JUSTIFY": _gen_justify,
    "A": _gen_ascii,
    "ASCII": _gen_ascii,
    "C": _gen_char,
    "CHAR": _gen_char,
    "RE": _gen_reverse,
    "REVERSE": _gen_reverse,
    "FN": _gen_fnumber,
    "FNUMBER": _gen_fnumber,
    
    # Numeric functions
    "R": _gen_random,
    "RANDOM": _gen_random,
    
    # Data functions
    "D": _gen_data,
    "DATA": _gen_data,
    "G": _gen_get,
    "GET": _gen_get,
    "O": _gen_order,
    "ORDER": _gen_order,
    "Q": _gen_query,
    "QUERY": _gen_query,
    
    # Array utilities
    "NA": _gen_name,
    "NAME": _gen_name,
    "QL": _gen_qlength,
    "QLENGTH": _gen_qlength,
    "QS": _gen_qsubscript,
    "QSUBSCRIPT": _gen_qsubscript,
    
    # Conditional
    "S": _gen_select,
    "SELECT": _gen_select,
    
    # Already implemented (Spec 008)
    "T": _gen_text,
    "TEXT": _gen_text,
}
```

## Runtime Helper Functions

### New helpers for `runtime/helpers.py`

| Function | Signature | Description |
|----------|-----------|-------------|
| `m_piece` | `(string, delim, start, end=None) -> str` | Extract piece(s) from delimited string |
| `m_extract` | `(string, start, end=None) -> str` | Extract substring (1-based) |
| `m_find` | `(string, target, start=1) -> int` | Find substring, return position after match |
| `m_get` | `(array, *subscripts, default="") -> str` | Safe get with default |
| `m_order` | `(array, subscripts, direction=1) -> str` | Next subscript in collation |
| `m_query` | `(array, subscripts) -> str` | Full reference of next node |
| `m_name` | `(var_name, subscripts, depth=None) -> str` | Variable reference as string |
| `m_qlength` | `(name) -> int` | Count subscripts in name string |
| `m_qsubscript` | `(name, position) -> str` | Extract subscript from name |
| `m_fnumber` | `(number, codes, decimals=None) -> str` | Formatted numeric output |

### Existing helpers (no changes needed)

| Function | Description |
|----------|-------------|
| `m_set_piece` | LHS $PIECE assignment |
| `m_set_extract` | LHS $EXTRACT assignment |
| `m_data` | $DATA for local arrays |
| `m_data_global` | $DATA for global variables |

## State Transitions

### $SELECT Evaluation

```
For each (condition, value) pair left-to-right:
  1. Evaluate condition as tvexpr
  2. If true → evaluate and return value
  3. If false → continue to next pair
  4. If no pairs remain → raise SELECTFALSE
```

### $ORDER Traversal

```
Given array(subscripts):
  direction = 1 (forward) or -1 (reverse)
  
  Forward (direction=1):
    Return first subscript > current in collation order
    If none exists → return ""
    
  Reverse (direction=-1):
    Return first subscript < current in collation order
    If none exists → return ""
```

### $QUERY Traversal

```
Given array(subscripts):
  1. Find current node in tree
  2. Find next node in depth-first order
  3. Return full reference (e.g., "A(1,2)")
  4. If no more nodes → return ""
```

## Validation Rules

### $RANDOM Validation

```
If limit <= 0:
  Raise MRuntimeError("RANDARGNEG")
Return random.randint(0, limit - 1)
```

### $SELECT Validation

```
If no condition evaluates to true:
  Raise MRuntimeError("SELECTFALSE")
```

### $CHAR Validation

```
For each code in arguments:
  If code < 0 → return ""
  Else → return chr(code)
```

### $ASCII Validation

```
If position < 1 or position > len(string) or string == "":
  Return -1
Return ord(string[position - 1])
```
