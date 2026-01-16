# Operator Translation

How to translate MUMPS operators to Python.

## Helper Functions

The `m2py.codegen.helpers` module provides functions that implement MUMPS semantics:

| Helper | Purpose |
|--------|---------|
| `m_num(value)` | Numeric coercion (ANSI 7.1.4.5) |
| `m_truth(value)` | Truth evaluation (ANSI 1.2.4) |
| `m_compare(a, b, op)` | Comparison with appropriate coercion |

```python
from m2py.codegen.helpers import m_num, m_truth, m_compare

m_num("3.14ABC")   # 3.14 (extract numeric prefix)
m_num("+-5")       # -5 (sign chain processing)
m_truth("")        # False (empty string is falsy)
m_truth("0.0")     # False (numeric zero is falsy)
m_compare("7", 7, "=")  # True (numeric comparison)
```

## Critical: No Operator Precedence

**MUMPS evaluates strictly left-to-right with no precedence rules.**

```mumps
S X=2+3*4
```

In MUMPS: `(2+3)*4 = 20`
In Python: `2+3*4 = 14` (multiplication first)

**Always generate parentheses in Python:**

```python
# Conceptual Python equivalent

x = ((2 + 3) * 4)  # Force left-to-right
```

## Arithmetic Operators

| MUMPS | Python | Notes |
|-------|--------|-------|
| `+` | `+` | Addition |
| `-` | `-` | Subtraction |
| `*` | `*` | Multiplication |
| `/` | `/` | Division (Python 3 returns float) |
| `\` | `int(x / y)` | Integer division (truncation towards zero) |
| `#` | `%` | Modulo |
| `**` | `**` | Exponentiation |

### Integer Division

MUMPS integer division truncates towards zero, not towards negative infinity like Python's `//`.

```mumps
S X=7\2     ; X=3
S Y=-7\3    ; Y=-2 (not -3)
```

```python
# Conceptual Python equivalent

x = int(7 / 2)   # x=3
y = int(-7 / 3)  # y=-2 (truncation, not floor)
```

### Modulo

```mumps
S X=7#3     ; X=1
```

```python
# Conceptual Python equivalent

x = 7 % 3   # x=1
```

### Unary Operators

```mumps
S X=-Y
S Z=+A      ; Numeric coercion
```

```python
# Conceptual Python equivalent

x = -y
z = float(a) if isinstance(a, str) else a  # Coerce to number
```

## String Operators

### Concatenation

```mumps
S X=A_B_C
```

```python
# Conceptual Python equivalent

x = str(a) + str(b) + str(c)
```

Note: MUMPS implicitly converts to string. Python may need explicit `str()`.

## Comparison Operators

| MUMPS | Python | Notes |
|-------|--------|-------|
| `=` | `==` | Equality |
| `<` | `<` | Less than |
| `>` | `>` | Greater than |
| `'=` | `!=` | Not equal |
| `'<` | `>=` | Not less than |
| `'>` | `<=` | Not greater than |

**MUMPS comparison semantics** differ from Python. Use the `m_compare()` helper:

```python
from m2py.codegen.helpers import m_compare

# m_compare handles numeric vs string comparison
m_compare(a, b, "=")   # True if a equals b (type-aware)
m_compare(a, b, "<")   # True if a < b (numeric coercion)
m_compare(a, b, ">")   # True if a > b (numeric coercion)
```

For equality (`=`), `m_compare` checks if both operands look numeric. If so, 
it compares numerically (so `"007" = 7` is true). For `<` and `>`, it always 
coerces both sides to numbers via `m_num()`.

### Negated Comparisons

```mumps
I X'<10     ; If X is not less than 10 (i.e., >= 10)
```

```python
# Conceptual Python equivalent

if x >= 10:
```

## String Comparison Operators

### Contains `[`

```mumps
I A[B       ; True if A contains B
```

**Note operand order reversal in Python:**

```python
# Conceptual Python equivalent

if b in a:  # B in A
```

### Sorts After `]`

```mumps
I A]B       ; True if A collates after B
```

```python
# Conceptual Python equivalent

if a > b:   # String comparison
```

For numeric strings, MUMPS compares numerically:
```mumps
"10"]"9"    ; True (10 > 9 numerically)
```

This requires special handling in Python.

### Strictly Follows `]]`

Similar to `]` but for strict ordering (implementation-specific).

## Logical Operators

| MUMPS | Python | Notes |
|-------|--------|-------|
| `&` | `and` | Logical AND |
| `!` | `or` | Logical OR |
| `'` | `not` | Logical NOT (unary) |

### AND

```mumps
I A&B
```

```python
# Conceptual Python equivalent

if a and b:
```

### OR

```mumps
I A!B
```

```python
# Conceptual Python equivalent

if a or b:
```

### NOT

```mumps
I 'X
I '(A&B)
```

```python
# Conceptual Python equivalent

if not x:
if not (a and b):
```

## Pattern Match

The pattern match operator (`?`) checks if a string matches a MUMPS pattern.

```mumps
W "ABC"?1A.A    ; 1 (one letter, any letters)
W "123"?1N.N    ; 1 (one or more digits)
W "AB12"?2A2N   ; 1 (exactly 2 letters, 2 digits)
W "ABC"'?1N.N   ; 1 (negated - ABC doesn't match numeric)
```

The codegen generates `m_pattern_match()` calls:

```python
m_pattern_match("ABC", "1A.A")   # Returns 1 (match)
m_pattern_match("A1B", "1A.A")   # Returns 0 (no match)
```

Negated pattern match (`'?`) wraps the result:

```python
int(not m_pattern_match("ABC", "1N.N"))  # Returns 1 (doesn't match)
```

See [pattern_compiler.md](../analysis/pattern_compiler.md) for pattern translation.

### Negated Pattern

```mumps
I X'?1N
```

```python
# Conceptual Python equivalent

if not re.fullmatch(r"[0-9]", x):
```

## Complex Expressions

### Left-to-Right Evaluation

```mumps
S X=A+B*C-D/E
```

Evaluates as: `((((A+B)*C)-D)/E)`

```python
# Conceptual Python equivalent

x = ((((a + b) * c) - d) / e)
```

### Parentheses in MUMPS

```mumps
S X=A+(B*C)
```

This changes order: `A+(B*C)`

```python
# Conceptual Python equivalent

x = a + (b * c)  # Parentheses preserved
```

## Truthiness

MUMPS truthy values:
- Non-zero numbers are true
- Empty string is false
- Non-numeric strings coerce to 0 (false)

```mumps
I "ABC"     ; False (coerces to 0)
I "1ABC"    ; True (coerces to 1)
I 0.001     ; True (non-zero)
```

Python needs explicit coercion:
```python
# Conceptual Python equivalent

def mumps_bool(value):
    if isinstance(value, str):
        # Try to extract leading number
        import re
        match = re.match(r'^[+-]?(\d+\.?\d*|\.\d+)', value)
        return float(match.group()) != 0 if match else False
    return bool(value)
```

## Type Coercion

MUMPS automatically coerces between strings and numbers:

```mumps
S X="123"+1     ; X=124
S Y="ABC"+1     ; Y=1 (ABC coerces to 0)
```

Python helper:
```python
# Conceptual Python equivalent

def mumps_num(value):
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        import re
        match = re.match(r'^[+-]?(\d+\.?\d*|\.\d+)', value.lstrip())
        return float(match.group()) if match else 0
    return 0
```

## Code Generation Pattern

```python
# Conceptual Python equivalent

def generate_binary_op(op_node):
    left = generate_expr(op_node.left)
    right = generate_expr(op_node.right)
    op = op_node.operator
    
    op_map = {
        "+": "+", "-": "-", "*": "*",
        "/": "/", "\\": "//", "#": "%",
        "**": "**", "_": "+",  # concat
        "=": "==", "<": "<", ">": ">",
        "'=": "!=", "'<": ">=", "'>": "<=",
        "&": "and", "!": "or",
    }
    
    python_op = op_map.get(op, op)
    
    if op == "_":
        # String concatenation - ensure strings
        return f"str({left}) + str({right})"
    elif op == "[":
        # Contains - note operand swap
        return f"({right} in {left})"
    else:
        # Wrap in parens for left-to-right semantics
        return f"({left} {python_op} {right})"
```
