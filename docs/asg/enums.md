# ASG Enumerations

This document describes all enumeration types used in the ASG, with guidance on how each value affects code generation.

**Source**: [`src/m2py/asg/enums.py`](../../src/m2py/asg/enums.py)

---

## ForLoopType

Classification of FOR loop control flow patterns. Used to determine transpilation strategy.

| Value | Description | Python Translation |
|-------|-------------|-------------------|
| `BOUNDED` | Fixed bounds: `F I=1:1:10` | `for i in range(1, 11, 1)` |
| `OPEN_ENDED` | No upper bound: `F I=1:1` | `while True:` with break |
| `STRING_LIST` | Explicit values: `F I="A","B"` | `for i in ["A", "B"]` |
| `MIXED` | Combination: `F I="A",1:1:3` | Multiple loops or combined |
| `ARGUMENTLESS` | Infinite: `F  ...` | `while True:` with break |

**Code Generation Notes**:
- `BOUNDED`: Check step sign for range direction; use `range(start, end+1, step)` for positive step
- `OPEN_ENDED`/`ARGUMENTLESS`: Must have exit mechanism (QUIT or GOTO)
- `MIXED`: May need to split into sequential loops or use generators

---

## ForParamType

Type of individual FOR parameter within a FOR command.

| Value | Description | Example |
|-------|-------------|---------|
| `VALUE` | Single expression | `F I=7` |
| `RANGE` | Bounded range | `F I=1:1:10` |
| `OPEN_RANGE` | Unbounded range | `F I=1:1` |

**Usage**: Each `MForParameter` has a `param_type` field classifying its form.

---

## GotoType

Classification of GOTO statement behavior. Determines control flow translation strategy.

| Value | Description | Code Gen Strategy |
|-------|-------------|-------------------|
| `FORWARD_JUMP` | Jump ahead (same or different label) | if/elif chain or labeled block |
| `BACKWARD_JUMP` | Jump back (same or different label) | while loop wrapper |
| `LOOP_EXIT` | Exit single FOR loop | `break` |
| `MULTI_LOOP_EXIT` | Exit nested FOR loops | Exception or state machine |
| `CROSS_LABEL` | **Deprecated** - use `is_cross_label` flag | - |
| `EXTERNAL` | Jump to external routine | Module import + call |
| `UNRESOLVED` | Cannot determine statically | Runtime dispatch |

**Note**: The `is_cross_label` field on `MGotoStatement` indicates whether the jump crosses label boundaries. This is orthogonal to direction (`FORWARD_JUMP`/`BACKWARD_JUMP`). For example:
- `FORWARD_JUMP` + `is_cross_label=False`: Jump ahead within same label → simple if/else
- `FORWARD_JUMP` + `is_cross_label=True`: Jump ahead to different label → function call
- `LOOP_EXIT` + `is_cross_label=True`: Exit FOR and jump to different label

**Code Generation Notes**:
- `LOOP_EXIT`: Simple `break` statement
- `MULTI_LOOP_EXIT`: Either:
  - Raise custom exception caught at outer loop
  - Use state variable checked after each loop
- `CROSS_LABEL`: Convert label to function, GOTO becomes function call
- `BACKWARD_JUMP`: Wrap code in while loop with break at end

---

## CallType

Type of subroutine call or reference. Classifies DO, GOTO, and extrinsic calls.

| Value | Description | Example | Code Gen |
|-------|-------------|---------|----------|
| `LABEL_CALL` | Simple label | `D LABEL` | Direct function call |
| `OFFSET_CALL` | Label + offset | `D LABEL+2` | Complex: source lookup |
| `ROUTINE_CALL` | External routine | `D LABEL^ROUTINE` | Import + call |
| `INDIRECT_CALL` | Indirected | `D @CMD` | Runtime dispatch |
| `UNRESOLVED` | Cannot determine | Dynamic | Runtime dispatch |

**Code Generation Notes**:
- `LABEL_CALL`: `label_name()` or `self.label_name()`
- `ROUTINE_CALL`: `from routine import label_name; label_name()`
- `OFFSET_CALL`: May need `$TEXT` support to find actual line
- `INDIRECT_CALL`: `eval()` equivalent or dispatch table

---

## LiteralType

Type of literal value. Classifies the syntactic form.

| Value | Description | Example | Python Type |
|-------|-------------|---------|-------------|
| `STRING` | Quoted string | `"hello"` | `str` |
| `INTEGER` | Integer | `42` | `int` |
| `DECIMAL` | Decimal | `3.14` | `float` or `Decimal` |

**Note**: MUMPS treats all values as strings that can be coerced to numbers. Python code generation may need explicit conversions.

---

## FormatControlType

Type of I/O format control in WRITE/READ commands.

| Value | Description | Syntax | Python |
|-------|-------------|--------|--------|
| `NEWLINE` | Line feed | `!` | `"\n"` or `print()` |
| `FORMFEED` | Page break | `#` | `"\f"` |
| `TAB` | Tab to column | `?n` | String padding |
| `CHARCODE` | Character by code | `*n` | `chr(n)` |

**Code Generation**:
```python
if control_type == FormatControlType.NEWLINE:
    print()
elif control_type == FormatControlType.TAB:
    # Pad to column n
    current_col = len(current_line)
    if n > current_col:
        print(" " * (n - current_col), end="")
elif control_type == FormatControlType.CHARCODE:
    print(chr(n), end="")
```

---

## IndirectionType

Classification of indirection (`@`) usage patterns.

| Value | Description | Example | Code Gen |
|-------|-------------|---------|----------|
| `NAME` | Name indirection | `@X` | `eval(x)` or lookup |
| `SUBSCRIPT` | Subscript indirection | `Y(@I)` | Dynamic subscript |
| `ARGUMENT` | Argument indirection | `D @X` | Runtime dispatch |
| `PATTERN` | Pattern indirection | `Y?@X` | Runtime pattern compile |
| `UNKNOWN` | Cannot determine | Mixed | Full runtime |

**Code Generation Notes**:
- Static resolution preferred when possible (`can_resolve_statically`)
- Otherwise requires runtime variable lookup mechanism
- May need sandboxed eval or restricted dispatch

---

## PassingMode

Classification of parameter passing mode for function arguments.

| Value | Description | Syntax | Code Gen |
|-------|-------------|--------|----------|
| `BY_VALUE` | Value passed | `D SUB(X+1)` | Normal parameter |
| `BY_REFERENCE` | Variable aliased | `D SUB(.X)` | Mutable container |
| `OMITTED` | Position empty | `D SUB(,Y)` | `None` or sentinel |

**Code Generation for BY_REFERENCE**:

Option 1: Mutable container
```python
def swap(a_ref, b_ref):
    a_ref[0], b_ref[0] = b_ref[0], a_ref[0]

x, y = [1], [2]
swap(x, y)
```

Option 2: Return modified values
```python
def swap(a, b):
    return b, a

x, y = swap(x, y)
```

---

## ScopeStrategy

Classification of label for code generation strategy. Determined by variable analysis.

| Value | Description | Code Gen Approach |
|-------|-------------|-------------------|
| `PURE_FUNCTION` | No side effects, clean inputs/outputs | Standard Python function |
| `FUNCTION_WITH_OUTPUTS` | Return value AND modifies by-ref params | Return tuple |
| `SUBROUTINE` | No return value, may have side effects | Function returning None |
| `REQUIRES_RUNTIME` | Static analysis insufficient | Runtime variable management |

**Code Generation Examples**:

**PURE_FUNCTION**:
```python
def calculate(a, b):
    return a + b
```

**FUNCTION_WITH_OUTPUTS**:
```python
def process(x, y_ref):
    result = x * 2
    y_ref[0] = x + 1  # Modify by-ref
    return result
```

**SUBROUTINE**:
```python
def log_message(msg):
    print(msg)
    # No return value
```

**REQUIRES_RUNTIME**:
```python
def dynamic_label():
    runtime.set_local("X", 1)
    if runtime.get_local("COND"):
        runtime.xecute("S Y=2")
```

---

## Using Enums in Analysis

```python
from m2py.asg.enums import ForLoopType, GotoType

# Check FOR loop type
for stmt in label.body.walk_statements():
    if isinstance(stmt, MForStatement):
        if stmt.loop_type == ForLoopType.BOUNDED:
            # Can use Python for loop
            pass
        elif stmt.loop_type in (ForLoopType.OPEN_ENDED, ForLoopType.ARGUMENTLESS):
            # Need while True with break
            pass

# Check GOTO type
for stmt in label.body.walk_statements():
    if isinstance(stmt, MGotoStatement):
        if stmt.goto_type == GotoType.LOOP_EXIT:
            # Simple break
            pass
        elif stmt.goto_type == GotoType.MULTI_LOOP_EXIT:
            # Need exception or state machine
            pass
```
