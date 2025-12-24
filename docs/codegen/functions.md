# Intrinsic Function Translation

How to translate MUMPS intrinsic functions to Python.

## Overview

MUMPS intrinsic functions start with `$`. Most have both full and abbreviated names.

## String Functions

### $EXTRACT / $E

Extract substring by position (1-based).

```mumps
$E(X)       ; First character
$E(X,2)     ; Second character
$E(X,2,5)   ; Characters 2 through 5
```

```python
x[0]        # First character (0-indexed)
x[1]        # Second character
x[1:5]      # Characters 2-5 (adjust indices)
```

**Full translation:**
```python
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
x.split("^")[1]  # Second piece (0-indexed)
"^".join(x.split("^")[1:4])  # Pieces 2-4
```

**Full translation:**
```python
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
"one" if x == 1 else "two" if x == 2 else "other"
```

Or using match (Python 3.10+):
```python
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
var_dict.get("X", "")       # Default empty
var_dict.get("X", "default")  # Custom default
```

### $ORDER / $O

Next subscript in collation order.

```mumps
$O(^DATA(KEY))      ; Next key after KEY
$O(^DATA(KEY),-1)   ; Previous key
```

```python
def mumps_order(data_dict, prefix, current, direction=1):
    keys = sorted(k for k in data_dict if k.startswith(prefix))
    try:
        idx = keys.index(current)
        next_idx = idx + direction
        return keys[next_idx] if 0 <= next_idx < len(keys) else ""
    except ValueError:
        return keys[0] if direction == 1 and keys else ""
```

### $QUERY / $Q

Full reference of next node.

```mumps
$Q(^DATA(A,B))      ; Next subscripted reference
```

More complex than $ORDER - returns full variable reference.

## Date/Time Functions

### $HOROLOG / $H

Current date and time.

```mumps
$H              ; "days,seconds"
$P($H,",",1)    ; Days since Dec 31, 1840
$P($H,",",2)    ; Seconds since midnight
```

```python
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

```python
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
from mumps_runtime import piece, extract, order
```
