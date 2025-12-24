# Expressions: Variables, Operators, Functions

Examples of MUMPS expressions and their ASG representation.

## Variables

### Local Variable

```mumps
X
```

**ASG Structure:**
```
MVariable(name="X", subscripts=[])
```

### Subscripted Variable

```mumps
A(1,2,3)
```

**ASG Structure:**
```
MVariable(
    name="A",
    subscripts=[
        MLiteral(value=1),
        MLiteral(value=2),
        MLiteral(value=3)
    ]
)
```

### Global Variable

```mumps
^PATIENT(ID)
```

**ASG Structure:**
```
MGlobal(
    name="PATIENT",
    subscripts=[MVariable(name="ID")]
)
```

### Naked Global Reference

```mumps
^(2)
```

Uses last global reference's name.

**ASG Structure:**
```
MNakedGlobal(
    subscripts=[MLiteral(value=2)],
    requires_runtime_tracking=True
)
```

---

## Operators

### Arithmetic

| MUMPS | Meaning | Python |
|-------|---------|--------|
| `+` | Add | `+` |
| `-` | Subtract | `-` |
| `*` | Multiply | `*` |
| `/` | Divide | `/` |
| `\` | Integer divide | `//` |
| `#` | Modulo | `%` |
| `**` | Power | `**` |

```mumps
A+B*C
```

**CRITICAL:** MUMPS has strict left-to-right evaluation, no precedence!

**ASG Structure:**
```
MBinaryOp(
    operator="*",
    left=MBinaryOp(
        operator="+",
        left=MVariable(name="A"),
        right=MVariable(name="B")
    ),
    right=MVariable(name="C")
)
```

This equals `(A+B)*C`, not `A+(B*C)`!

**Python Equivalent:**
```python
(a + b) * c  # Must add parentheses!
```

### String Concatenation

```mumps
A_B_C
```

**ASG Structure:**
```
MBinaryOp(
    operator="_",
    left=MBinaryOp(operator="_", left=MVariable(name="A"), right=MVariable(name="B")),
    right=MVariable(name="C")
)
```

**Python Equivalent:**
```python
str(a) + str(b) + str(c)
```

### Comparison Operators

| MUMPS | Meaning | Python |
|-------|---------|--------|
| `=` | Equals | `==` |
| `<` | Less than | `<` |
| `>` | Greater than | `>` |
| `'=` | Not equals | `!=` |
| `'<` | Not less (>=) | `>=` |
| `'>` | Not greater (<=) | `<=` |

### String Operators

| MUMPS | Meaning | Python Equivalent |
|-------|---------|-------------------|
| `]` | Sorts after | `a > b` (collation) |
| `]]` | Strictly follows | Special comparison |
| `[` | Contains | `b in a` |

```mumps
A[B
```

True if A contains B as substring.

**ASG Structure:**
```
MBinaryOp(operator="[", left=MVariable(name="A"), right=MVariable(name="B"))
```

**Python Equivalent:**
```python
b in a  # Note operand order reversal!
```

### Logical Operators

| MUMPS | Meaning | Python |
|-------|---------|--------|
| `&` | AND | `and` |
| `!` | OR | `or` |
| `'` | NOT (unary) | `not` |

```mumps
'(A&B)
```

**ASG Structure:**
```
MUnaryOp(
    operator="'",
    operand=MBinaryOp(operator="&", left=MVariable(name="A"), right=MVariable(name="B"))
)
```

---

## Pattern Match

```mumps
X?1A.N
```

**ASG Structure:**
```
MPatternMatch(
    subject=MVariable(name="X"),
    pattern=MLiteral(value="1A.N"),
    operator="?",
    compiled_regex="[A-Za-z][0-9]*"
)
```

**Python Equivalent:**
```python
import re
bool(re.fullmatch(r"[A-Za-z][0-9]*", x))
```

### Negated Pattern

```mumps
X'?1N
```

**ASG Structure:**
```
MPatternMatch(
    subject=MVariable(name="X"),
    pattern=MLiteral(value="1N"),
    operator="'?"
)
```

---

## Intrinsic Functions

### $PIECE

```mumps
$P(X,"^",2)
```

**ASG Structure:**
```
MIntrinsicFunction(
    name="P",
    arguments=[
        MVariable(name="X"),
        MLiteral(value="^"),
        MLiteral(value=2)
    ]
)
```

**Python Equivalent:**
```python
x.split("^")[1]  # 0-indexed in Python!
```

### $EXTRACT

```mumps
$E(X,2,5)
```

**ASG Structure:**
```
MIntrinsicFunction(
    name="E",
    arguments=[
        MVariable(name="X"),
        MLiteral(value=2),
        MLiteral(value=5)
    ]
)
```

**Python Equivalent:**
```python
x[1:5]  # Adjust indices (MUMPS is 1-based)
```

### $LENGTH

```mumps
$L(X)
$L(X,"^")
```

**ASG Structure (1-arg):**
```
MIntrinsicFunction(name="L", arguments=[MVariable(name="X")])
```

**ASG Structure (2-arg):**
```
MIntrinsicFunction(name="L", arguments=[MVariable(name="X"), MLiteral(value="^")])
```

**Python Equivalent:**
```python
len(x)  # 1-arg
x.count("^") + 1  # 2-arg (count pieces)
```

### $ORDER

```mumps
$O(^DATA(KEY))
```

Returns next subscript.

**ASG Structure:**
```
MIntrinsicFunction(
    name="O",
    arguments=[MGlobal(name="DATA", subscripts=[MVariable(name="KEY")])]
)
```

### Common Functions

| MUMPS | Full Name | Purpose |
|-------|-----------|---------|
| `$E` | $EXTRACT | Substring |
| `$P` | $PIECE | Split by delimiter |
| `$L` | $LENGTH | String/piece count |
| `$F` | $FIND | Find substring |
| `$O` | $ORDER | Next subscript |
| `$D` | $DATA | Variable existence |
| `$G` | $GET | Get with default |
| `$S` | $SELECT | Conditional value |
| `$TR` | $TRANSLATE | Character mapping |
| `$R` | $RANDOM | Random number |

---

## Extrinsic Functions

```mumps
$$CALC^MATH(X,Y)
```

**ASG Structure:**
```
MExtrinsicFunction(
    target=MCall(
        name="CALC",
        routine="MATH",
        arguments=[...]
    ),
    arguments=[MVariable(name="X"), MVariable(name="Y")]
)
```

---

## Special Variables

```mumps
$H      ; $HOROLOG - date/time
$T      ; $TEST - last test result
$J      ; $JOB - process ID
$IO     ; $IO - current device
$X      ; $X - cursor column
$Y      ; $Y - cursor row
```

**ASG Structure:**
```
MSpecialVariable(name="H")  # $HOROLOG
MSpecialVariable(name="T")  # $TEST
```

---

## Literals

### String

```mumps
"Hello"
```

**ASG Structure:**
```
MLiteral(value="Hello", literal_type=LiteralType.STRING)
```

### Integer

```mumps
42
```

**ASG Structure:**
```
MLiteral(value=42, literal_type=LiteralType.INTEGER)
```

### Decimal

```mumps
3.14
```

**ASG Structure:**
```
MLiteral(value=3.14, literal_type=LiteralType.DECIMAL)
```

---

## Code Generation Notes

### Operator Precedence

MUMPS has **no precedence** - strict left-to-right. Always generate parentheses:

```mumps
2+3*4   ; = 20 in MUMPS
```
```python
(2 + 3) * 4  # = 20
```

### String/Number Coercion

MUMPS automatically coerces:
- `"123"+1` = 124
- `"abc"+1` = 1 (non-numeric string = 0)

### Function Mapping

Most intrinsic functions need Python runtime equivalents or library calls.
