# Intrinsic Function Translation

How to translate MUMPS intrinsic functions to Python.

## Overview

MUMPS intrinsic functions start with `$`. Most have both full and abbreviated names.

## Implementation Architecture

Intrinsic functions are handled by the `generate_intrinsic_function()` dispatcher in `codegen/expressions.py`. The function uses a dispatch table (`INTRINSIC_GENERATORS`) that maps function names to generator functions:

```python
# Dispatch table pattern
INTRINSIC_GENERATORS = {
    "L": _gen_length, "LENGTH": _gen_length,
    "P": _gen_piece, "PIECE": _gen_piece,
    # ... etc
}

def generate_intrinsic_function(expr: MIntrinsicFunction, ctx: GeneratorContext) -> str:
    func_name = expr.name.upper()
    if func_name in INTRINSIC_GENERATORS:
        return INTRINSIC_GENERATORS[func_name](expr, ctx)
    raise NotImplementedError(f"Intrinsic function ${expr.name} not yet implemented")
```

### Runtime Helpers

Complex functions that require M-specific semantics use runtime helpers in `runtime/helpers.py`:
- `m_piece()` - $PIECE extraction with edge case handling
- `m_extract()` - $EXTRACT with 1-based indexing
- `m_order()` - $ORDER with MUMPS collation order
- `m_query()` - $QUERY depth-first tree traversal

Simple functions generate inline Python (e.g., `len()` for $LENGTH, `chr()` for $CHAR).

### Error Handling

Runtime errors specific to MUMPS semantics use `MRuntimeError` from `runtime/exceptions.py`:
- `SELECTFALSE` - $SELECT with no true condition
- `RANDARGNEG` - $RANDOM with argument ≤ 0

## String Functions

### $EXTRACT / $E

Extract substring by position (1-based).

```mumps
$E(X)       ; First character
$E(X,2)     ; Second character
$E(X,2,5)   ; Characters 2 through 5
```

```python
# Conceptual Python equivalent

x[0]        # First character (0-indexed)
x[1]        # Second character
x[1:5]      # Characters 2-5 (adjust indices)
```

**Full translation:**
```python
# Conceptual Python equivalent

def mumps_extract(string, start=1, end=None):
    if end is None:
        end = start
    return string[start-1:end]  # Adjust for 1-based indexing
```

### $PIECE / $P

Split by delimiter and get piece (1-based).

```mumps
$P(X,"^",2)     ; Second piece
$P(X,"^",2,4)   ; Pieces 2 through 4
```

```python
# Conceptual Python equivalent

x.split("^")[1]  # Second piece (0-indexed)
"^".join(x.split("^")[1:4])  # Pieces 2-4
```

**Full translation:**
```python
# Conceptual Python equivalent

def mumps_piece(string, delim, start=1, end=None):
    pieces = string.split(delim)
    if end is None:
        end = start
    return delim.join(pieces[start-1:end])
```

### $LENGTH / $L

String length or piece count.

```mumps
$L(X)           ; String length
$L(X,"^")       ; Number of pieces
```

```python
# Conceptual Python equivalent

len(x)          # String length
x.count("^") + 1  # Piece count
```

### $FIND / $F

Find substring, return position after match.

```mumps
$F(X,"AB")      ; Position after "AB"
$F(X,"AB",5)    ; Start searching at position 5
```

```python
# Conceptual Python equivalent

def mumps_find(string, target, start=1):
    pos = string.find(target, start-1)
    if pos == -1:
        return 0
    return pos + len(target) + 1  # Position after match, 1-based
```

### $TRANSLATE / $TR

Character-by-character translation.

```mumps
$TR(X,"abc","ABC")   ; Replace lowercase with uppercase
$TR(X,"aeiou")       ; Remove vowels (no replacement)
```

```python
# Conceptual Python equivalent

x.translate(str.maketrans("abc", "ABC"))  # With replacement
x.translate(str.maketrans("", "", "aeiou"))  # Deletion
```

### $JUSTIFY / $J

Right-justify in field.

```mumps
$J(X,10)        ; Right-justify in 10 chars
$J(X,10,2)      ; Format number with 2 decimals in 10 chars
```

```python
# Conceptual Python equivalent

f"{x:>10}"      # Right-justify
f"{x:>10.2f}"   # With decimals
```

## Numeric Functions

### $RANDOM / $R

Random integer.

```mumps
$R(100)         ; Random 0-99
```

```python
# Conceptual Python equivalent

import random
random.randint(0, 99)
```

### $ASCII / $A

ASCII value of character.

```mumps
$A(X)           ; ASCII of first char
$A(X,3)         ; ASCII of third char
```

```python
# Conceptual Python equivalent

ord(x[0])       # First char
ord(x[2])       # Third char (0-indexed)
```

### $CHAR / $C

Character from ASCII value.

```mumps
$C(65)          ; "A"
$C(65,66,67)    ; "ABC"
```

```python
# Conceptual Python equivalent

chr(65)         # "A"
"".join(chr(c) for c in [65, 66, 67])  # "ABC"
```

## Conditional Functions

### $SELECT / $S

Conditional value selection.

```mumps
$S(X=1:"one",X=2:"two",1:"other")
```

```python
# Conceptual Python equivalent

"one" if x == 1 else "two" if x == 2 else "other"
```

Or using match (Python 3.10+):
```python
# Conceptual Python equivalent

match x:
    case 1: result = "one"
    case 2: result = "two"
    case _: result = "other"
```

## Data Functions

### $DATA / $D

Check variable existence.

```mumps
$D(X)           ; 0=undefined, 1=value, 10=descendants, 11=both
```

```python
# Conceptual Python equivalent

def mumps_data(var_dict, name):
    has_value = name in var_dict
    has_descendants = any(k.startswith(name + "(") for k in var_dict)
    return (1 if has_value else 0) + (10 if has_descendants else 0)
```

### $GET / $G

Get value with default.

```mumps
$G(X)           ; X or empty string if undefined
$G(X,"default") ; X or "default" if undefined
```

```python
# Conceptual Python equivalent

var_dict.get("X", "")       # Default empty
var_dict.get("X", "default")  # Custom default
```

### $ORDER / $O

Next subscript in collation order.

```mumps
$O(A(""))       ; First subscript (forward)
$O(A(KEY))      ; Next key after KEY
$O(A(""),-1)    ; Last subscript (reverse)
$O(A(KEY),-1)   ; Previous key before KEY
```

**MUMPS Collation Order:**
1. Negative numbers (most negative first)
2. Zero
3. Positive numbers (ascending)
4. Strings (ASCII/UTF-8 order)

**Translation:**
```python
# Local array
m_order(_scope.get('A', MArray()), ("",), 1)      # Forward from start
m_order(_scope.get('A', MArray()), ("KEY",), -1)  # Reverse from KEY

# Global array
m_order_global(_rt.globals, 'DATA', ("KEY",), 1)  # Forward from KEY
```

The `m_order()` and `m_order_global()` helpers in `runtime/helpers.py` implement MUMPS collation order sorting.

### $QUERY / $Q

Full reference of next node in depth-first traversal.

```mumps
$Q(A(""))       ; First valued node reference
$Q(A(1,2))      ; Next valued node after A(1,2)
```

**Translation:**
```python
# Local array
m_query(_scope.get('A', MArray()), 'A', ("",))      # Start traversal
m_query(_scope.get('A', MArray()), 'A', ("1", "2")) # Continue after A(1,2)

# Global array
m_query_global(_rt.globals, 'DATA', ("",))  # Start traversal
```

Returns full variable reference string (e.g., "A(1,2,3)") or empty string when traversal is complete. The `m_query()` helper performs depth-first tree traversal following MUMPS collation order.

## Source Access Functions

### $TEXT / $T

Access source code lines from current or external routines.

```mumps
$T(+0)           ; Current routine name
$T(+N)           ; Nth line of current routine (1-based)
$T(LABEL)        ; Line containing LABEL in current routine
$T(LABEL+N)      ; Nth line after LABEL
$T(+N^ROUTINE)   ; Nth line of external ROUTINE
$T(LABEL^ROUTINE) ; LABEL line in external ROUTINE
```

```python
# Translation uses runtime get_text() method
_rt.get_text(offset=0)              # +0 → routine name
_rt.get_text(offset=5)              # +5 → 5th line
_rt.get_text(label="HELPER")        # LABEL → label line
_rt.get_text(offset=2, label="HELPER")  # LABEL+2 → offset from label
_rt.get_text(offset=5, module=__import__('ext2'))  # +5^ext2 → external routine
_rt.get_text(label="HELPER", module=__import__('ext2'))  # LABEL^ext2 → external label
```

**Implementation Notes:**
- Runtime `get_text()` method uses `_source_lines` attribute storing original MUMPS source
- External routines require `__import__()` to load the target module
- Returns empty string for invalid references (negative offsets, nonexistent labels, past EOF)
- Line numbers are 1-based (MUMPS convention)
- External calls format: `module=__import__('routine_name')`

**Edge Cases:**
```python
_rt.get_text(offset=-1)  # Invalid: returns ""
_rt.get_text(offset=999) # Past end: returns ""
_rt.get_text(label="NOEXIST")  # Missing label: returns ""
```

## Date/Time Functions

### $HOROLOG / $H

Current date and time.

```mumps
$H              ; "days,seconds"
$P($H,",",1)    ; Days since Dec 31, 1840
$P($H,",",2)    ; Seconds since midnight
```

```python
# Conceptual Python equivalent

from datetime import datetime, date

def mumps_horolog():
    epoch = date(1840, 12, 31)
    today = date.today()
    days = (today - epoch).days
    now = datetime.now()
    seconds = now.hour * 3600 + now.minute * 60 + now.second
    return f"{days},{seconds}"
```

## Special Variables

| MUMPS | Meaning | Python |
|-------|---------|--------|
| `$T` / `$TEST` | Last test result | Global flag |
| `$H` / `$HOROLOG` | Date/time | See above |
| `$J` / `$JOB` | Process ID | `os.getpid()` |
| `$IO` | Current device | File handle |
| `$X` | Cursor column | Output tracking |
| `$Y` | Cursor row | Output tracking |
| `$P` / `$PRINCIPAL` | Principal device | `sys.stdout` |

## Code Generation Pattern

### Function Name Normalization

The ASG preserves function names exactly as written in the source (`$p`, `$PIECE`, etc.).
Code generators should normalize to uppercase when mapping to runtime functions:

```python
# Conceptual Python equivalent

def generate_intrinsic(node: MIntrinsicFunction) -> str:
    func_name = FUNCTION_MAP.get(node.name.upper())  # Normalize here
    # ...
```

This design allows case-sensitive source preservation for debugging and error messages
while ensuring correct function dispatch regardless of source casing.

```python
# Conceptual Python equivalent

FUNCTION_MAP = {
    "E": "mumps_extract",
    "EXTRACT": "mumps_extract",
    "P": "mumps_piece",
    "PIECE": "mumps_piece",
    "L": "mumps_length",
    "LENGTH": "mumps_length",
    "F": "mumps_find",
    "FIND": "mumps_find",
    "R": "random.randint",
    "RANDOM": "random.randint",
    "G": "mumps_get",
    "GET": "mumps_get",
    "D": "mumps_data",
    "DATA": "mumps_data",
    "O": "mumps_order",
    "ORDER": "mumps_order",
}

def generate_intrinsic(node):
    func_name = FUNCTION_MAP.get(node.name.upper())
    args = [generate_expr(arg) for arg in node.arguments]
    
    # Special cases
    if node.name.upper() in ("R", "RANDOM"):
        # $R(N) → randint(0, N-1)
        return f"random.randint(0, {args[0]} - 1)"
    
    return f"{func_name}({', '.join(args)})"
```

## Runtime Library

Many functions need runtime library implementations:

```python
# Conceptual Python equivalent

# mumps_runtime.py
def piece(string, delim, start, end=None):
    ...

def extract(string, start, end=None):
    ...

def order(collection, current, direction=1):
    ...
```

Then generate:
```python
# Conceptual Python equivalent

from mumps_runtime import piece, extract, order
```
