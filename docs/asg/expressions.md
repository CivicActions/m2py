# ASG Expression Types

This document describes all expression types in the ASG. Expressions are the fundamental building blocks that produce values.

## Base Expression

All expressions inherit from `MExpr`:

```python
@dataclass
class MExpr(ASGElement):
    result_type: Optional[str] = None  # "string", "number", "unknown"
```

**Source**: [`src/m2py/asg/expressions.py`](../../src/m2py/asg/expressions.py)

---

## Literals

### MLiteral

Constant values in source code:

```mumps
"Hello"      ; String literal
42           ; Integer literal
3.14         ; Decimal literal
```

| Field | Type | Description |
|-------|------|-------------|
| `value` | `Any` | The literal value |
| `literal_type` | `LiteralType` | STRING, INTEGER, or DECIMAL |
| `raw_value` | `Optional[str]` | Original text representation |

**Code Generation**:
- `STRING`: Python string literal
- `INTEGER`: Python int
- `DECIMAL`: Python float or Decimal

---

## Variable References

### MVariable

Local variable reference:

```mumps
X            ; Simple variable
DATA(1,2,3)  ; Subscripted variable
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Variable name |
| `subscripts` | `List[MExpr]` | Array subscripts (may be empty) |

**Code Generation**:
- Simple: Direct Python variable
- Subscripted: Dict access `data[(1, 2, 3)]` or custom array class

### MGlobal

Global (persistent) variable reference:

```mumps
^GLOBAL
^DATA(1,2,3)
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Global name (without ^) |
| `subscripts` | `List[MExpr]` | Array subscripts |

**Code Generation**: Requires runtime global storage (database, file, etc.)

### MNakedGlobal

Naked global reference using last global context:

```mumps
^(2)         ; Uses last ^GLOBAL reference, replaces last subscript
```

| Field | Type | Description |
|-------|------|-------------|
| `subscripts` | `List[MExpr]` | New subscripts |
| `requires_runtime_tracking` | `bool` | Always True |

**Code Generation**: Requires runtime tracking of last global reference.

---

## Operations

### MBinaryOp

Binary operation with two operands:

```mumps
A+B*C        ; Left-to-right: (A+B)*C
X=Y          ; Comparison (not assignment!)
A_B          ; String concatenation
X?1N.A       ; Pattern match
```

| Field | Type | Description |
|-------|------|-------------|
| `operator` | `str` | Operator symbol |
| `left` | `MExpr` | Left operand |
| `right` | `MExpr` | Right operand |

**MUMPS Operators**:

| Operator | Meaning | Python Equivalent |
|----------|---------|-------------------|
| `+` `-` `*` `/` | Arithmetic | Same |
| `\` | Integer division | `//` |
| `#` | Modulo | `%` |
| `**` | Exponentiation | `**` |
| `=` | Equals | `==` |
| `<` `>` | Less/greater than | Same |
| `'=` `'<` `'>` | Negated comparison | `!=`, `>=`, `<=` |
| `[` | Contains | `in` (string) |
| `]` | Follows (collation) | Custom |
| `]]` | Sorts after | Custom |
| `&` | Logical AND | `and` |
| `!` | Logical OR | `or` |
| `_` | Concatenation | `+` (strings) |
| `?` | Pattern match | Regex |

**Critical Note**: MUMPS uses strict **left-to-right** evaluation with **no operator precedence**:
```mumps
2+3*4 = 20   ; (2+3)*4, NOT 2+(3*4)
```

**Code Generation**: Must add explicit parentheses to preserve L-to-R semantics.

### MUnaryOp

Unary operation with single operand:

```mumps
-X           ; Negative
+X           ; Positive (numeric conversion)
'X           ; NOT (logical negation)
```

| Field | Type | Description |
|-------|------|-------------|
| `operator` | `str` | `+`, `-`, or `'` |
| `operand` | `MExpr` | The operand |

**Code Generation**:
- `-`: Python `-`
- `+`: Python `+` or explicit numeric conversion
- `'`: Python `not` (with truthiness conversion)

---

## Functions

### MIntrinsicFunction

Built-in MUMPS functions:

```mumps
$LENGTH(STR)
$PIECE(STR,"^",2)
$ORDER(ARR(I))
$GET(X,DEFAULT)
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Function name (without `$`) |
| `arguments` | `List[MExpr]` | Function arguments |

**Common Functions**:

| MUMPS | Description | Python Equivalent |
|-------|-------------|-------------------|
| `$EXTRACT(s,f,t)` | Substring | `s[f-1:t]` |
| `$PIECE(s,d,p)` | Split and get | `s.split(d)[p-1]` |
| `$LENGTH(s)` | Length | `len(s)` |
| `$LENGTH(s,d)` | Count pieces | `s.count(d) + 1` |
| `$ORDER(arr(i))` | Next subscript | Dict iteration |
| `$DATA(var)` | Variable exists | Existence check |
| `$GET(var,def)` | Get with default | `dict.get()` |
| `$FIND(s,sub)` | Find substring | `s.find(sub)` |
| `$TRANSLATE(s,f,t)` | Translate chars | `str.translate()` |
| `$SELECT(c1:v1,...)` | Conditional | `v1 if c1 else ...` |
| `$HOROLOG` | Date/time | `datetime` |
| `$RANDOM(n)` | Random 0..n-1 | `random.randint(0,n-1)` |

See: [codegen/functions.md](../codegen/functions.md)

### MExtrinsicFunction

User-defined function call:

```mumps
$$MYFUNC
$$CALC^MATH
$$ADD(A,B)
$$CALC(.X,Y)   ; With by-reference
```

| Field | Type | Description |
|-------|------|-------------|
| `target` | `MCall` | Target label/routine |
| `arguments` | `List[MActualParameter]` | Function arguments with passing mode |

**Code Generation**: Function call with return value capture. By-reference parameters (`.VAR` syntax) require special handling - see `PassingMode` in [enums.md](enums.md).

---

## Special Expressions

### MPatternMatch

Pattern matching using `?` operator:

```mumps
X?1N.A       ; One digit, zero or more letters
X?."AB"      ; Zero or more "AB"
X?@PAT       ; Indirect pattern
X'?1N        ; NOT match (negated)
```

| Field | Type | Description |
|-------|------|-------------|
| `subject` | `MExpr` | Value being matched |
| `pattern` | `str` | Raw pattern string |
| `pattern_indirect` | `Optional[MExpr]` | For `?@X` |
| `operator` | `str` | `?` or `'?` |
| `compiled_regex` | `Optional[str]` | Pre-compiled regex |

**Pattern Codes**:

| Code | Meaning | Regex Equivalent |
|------|---------|------------------|
| `A` | Alphabetic | `[A-Za-z]` |
| `C` | Control | `[\x00-\x1F\x7F]` |
| `E` | Everything | `.` |
| `L` | Lowercase | `[a-z]` |
| `N` | Numeric | `[0-9]` |
| `P` | Punctuation | Specific set |
| `U` | Uppercase | `[A-Z]` |

**Pattern Counts**:
- `1N` - Exactly one
- `.N` - Zero or more
- `1.N` - One or more
- `1.3N` - One to three

See: [analysis/pattern_compiler.md](../analysis/pattern_compiler.md)

### MIndirection

Indirect reference using `@`:

```mumps
@X           ; Name indirection (X contains var name)
Y(@I)        ; Subscript indirection
D @CMD       ; Argument indirection
X?@PAT       ; Pattern indirection
@X@(1,2)     ; Name indirection + subscripts
@@X          ; Multi-level (double) indirection
```

| Field | Type | Description |
|-------|------|-------------|
| `expression` | `MExpr` | Expression to evaluate |
| `indirection_type` | `IndirectionType` | Classification |
| `subscripts` | `Optional[List]` | For `@X(1,2)` |
| `name_indirection_subscripts` | `Optional[List]` | For `@X@(1,2)` |
| `can_resolve_statically` | `bool` | True if determinable at compile time |
| `resolved_value` | `Optional[str]` | If statically resolved |
| `indirection_levels` | `int` | Count of `@` signs (@@=2, @@@=3) |

**IndirectionType values**:

| Type | Example | Description |
|------|---------|-------------|
| `NAME` | `@X` | X contains variable name |
| `SUBSCRIPT` | `Y(@I)` | I provides subscript |
| `ARGUMENT` | `D @X` | X contains call target |
| `PATTERN` | `Y?@X` | X contains pattern |
| `NAME_SUBSCRIPT` | `@X@(1,2)` | Name + subscripts |
| `UNKNOWN` | Various | Cannot determine |

**Name Indirection with Subscripts** (`@X@(subs)`):

A critical pattern where subscripts are applied to the resolved name:
```mumps
S X="ARRAY"
S @X@(1,2)=5    ; Same as: S ARRAY(1,2)=5
```

The `@X@(1,2)` syntax differs from `@X(1,2)`:
- `@X(1,2)` - X contains "ARRAY(1,2)" as full reference
- `@X@(1,2)` - X contains "ARRAY", subscripts applied after

**Multi-Level Indirection** (`@@`, `@@@`):

Nested indirection requires multiple evaluations:
```mumps
S A="B", B="C", C=100
W @A        ; First eval A→"B", second lookup B: outputs "C"
W @@A       ; Eval A→"B", eval B→"C", lookup C: outputs 100
```

The `indirection_levels` field tracks the nesting depth for runtime dispatch.

**Code Generation**: Requires runtime support (dynamic variable access).

### MFormatControl

I/O format controls for WRITE/READ:

```mumps
W !          ; Newline
W #          ; Form feed
W ?10        ; Tab to column 10
W *65        ; Output char 'A' (ASCII 65)
```

| Field | Type | Description |
|-------|------|-------------|
| `control_type` | `FormatControlType` | NEWLINE, FORMFEED, TAB, CHARCODE |
| `expression` | `Optional[MExpr]` | Column/code for ?n/*n |

**Code Generation**:
- `NEWLINE`: `print()` or `"\n"`
- `FORMFEED`: `"\f"` or custom
- `TAB`: Pad to column
- `CHARCODE`: `chr(n)`

### MSpecialVariable

Intrinsic special variables (ISVs):

```mumps
$TEST        ; Result of last IF
$HOROLOG     ; Date/time
$IO          ; Current device
$JOB         ; Process ID
$X, $Y       ; Cursor position
$STORAGE     ; Available storage
```

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Variable name (without `$`) |

**Common ISVs**:

| ISV | Description | Python |
|-----|-------------|--------|
| `$TEST` | Last IF result | State variable |
| `$HOROLOG` | Days,seconds | `datetime` |
| `$JOB` | Process ID | `os.getpid()` |
| `$IO` | Current device | File handle |
| `$X`, `$Y` | Cursor position | State variables |
| `$PIECE` | Last $PIECE | Not commonly used |

---

## Parameter Passing

### MActualParameter

Actual parameter in a call:

```mumps
D SUB(A+1)    ; BY_VALUE
D SUB(.X)     ; BY_REFERENCE
D SUB(,Y)     ; First is OMITTED
```

| Field | Type | Description |
|-------|------|-------------|
| `passing_mode` | `PassingMode` | BY_VALUE, BY_REFERENCE, OMITTED |
| `expression` | `Optional[MExpr]` | The expression/variable |
| `variable_name` | `Optional[str]` | For BY_REFERENCE |

**PassingMode values**:

| Mode | Syntax | Meaning |
|------|--------|---------|
| `BY_VALUE` | `D SUB(X+1)` | Expression evaluated, value passed |
| `BY_REFERENCE` | `D SUB(.X)` | Variable aliased to formal |
| `OMITTED` | `D SUB(,Y)` | Empty position |

**Code Generation**:
- `BY_VALUE`: Normal parameter passing
- `BY_REFERENCE`: Use mutable container or return modified value
- `OMITTED`: Pass None or sentinel value

---

## Expression Type Summary

| Category | Types |
|----------|-------|
| Literals | `MLiteral` |
| Variables | `MVariable`, `MGlobal`, `MNakedGlobal` |
| Operations | `MBinaryOp`, `MUnaryOp` |
| Functions | `MIntrinsicFunction`, `MExtrinsicFunction` |
| Special | `MPatternMatch`, `MIndirection`, `MFormatControl`, `MSpecialVariable` |
| Parameters | `MActualParameter` |
