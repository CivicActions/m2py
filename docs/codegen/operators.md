# Operator Translation

How to translate MUMPS operators to Python.

## Critical: No Operator Precedence

**MUMPS evaluates strictly left-to-right with no precedence rules.**

```mumps
S X=2+3*4
```

In MUMPS: `(2+3)*4 = 20`
In Python: `2+3*4 = 14` (multiplication first)

**Always generate parentheses in Python:**

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
x = ((2 + 3) * 4)  # Force left-to-right
```

## Arithmetic Operators

| MUMPS | Python | Notes |
|-------|--------|-------|
| `+` | `+` | Addition |
| `-` | `-` | Subtraction |
| `*` | `*` | Multiplication |
| `/` | `/` | Division (Python 3 returns float) |
| `\` | `//` | Integer division |
| `#` | `%` | Modulo |
| `**` | `**` | Exponentiation |

### Integer Division

```mumps
S X=7\2     ; X=3
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
x = 7 // 2  # x=3
```

### Modulo

```mumps
S X=7#3     ; X=1
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
x = 7 % 3   # x=1
```

### Unary Operators

```mumps
S X=-Y
S Z=+A      ; Numeric coercion
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
x = -y
z = float(a) if isinstance(a, str) else a  # Coerce to number
```

## String Operators

### Concatenation

```mumps
S X=A_B_C
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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

### Negated Comparisons

```mumps
I X'<10     ; If X is not less than 10 (i.e., >= 10)
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
if x >= 10:
```

## String Comparison Operators

### Contains `[`

```mumps
I A[B       ; True if A contains B
```

**Note operand order reversal in Python:**

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
if b in a:  # B in A
```

### Sorts After `]`

```mumps
I A]B       ; True if A collates after B
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
if a and b:
```

### OR

```mumps
I A!B
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
if a or b:
```

### NOT

```mumps
I 'X
I '(A&B)
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
if not x:
if not (a and b):
```

## Pattern Match

```mumps
I X?1A.N
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
import re
if re.fullmatch(r"[A-Za-z][0-9]*", x):
```

See [pattern_compiler.md](../analysis/pattern_compiler.md) for pattern translation.

### Negated Pattern

```mumps
I X'?1N
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
if not re.fullmatch(r"[0-9]", x):
```

## Complex Expressions

### Left-to-Right Evaluation

```mumps
S X=A+B*C-D/E
```

Evaluates as: `((((A+B)*C)-D)/E)`

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
x = ((((a + b) * c) - d) / e)
```

### Parentheses in MUMPS

```mumps
S X=A+(B*C)
```

This changes order: `A+(B*C)`

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
