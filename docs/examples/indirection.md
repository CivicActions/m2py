# Indirection: @ Operator

Examples of MUMPS indirection and their ASG representation.

## Overview

Indirection (`@`) allows runtime evaluation of names, subscripts, and arguments. It's one of MUMPS's most powerful (and challenging) features.

## Types of Indirection

### Name Indirection

```mumps
S X="VAR"
S @X=1      ; Sets VAR=1
W @X        ; Writes value of VAR
```

**ASG Structure:**
```
MIndirection(
    expression=MVariable(name="X"),
    indirection_type=IndirectionType.NAME
)
```

**Python Equivalent:**
```python
x = "var"
locals()[x] = 1  # or use dict-based variable storage
```

### Subscript Indirection

```mumps
S I=2
S A(@I)=5   ; Sets A(2)=5
```

**ASG Structure:**
```
MVariable(
    name="A",
    subscripts=[
        MIndirection(
            expression=MVariable(name="I"),
            indirection_type=IndirectionType.SUBSCRIPT
        )
    ]
)
```

This is simpler - just evaluate I at runtime.

### Full Name Indirection

```mumps
S REF="A(1,2)"
S @REF=5    ; Sets A(1,2)=5
```

**ASG Structure:**
```
MIndirection(
    expression=MVariable(name="REF"),
    indirection_type=IndirectionType.NAME
)
```

The string must be parsed at runtime.

### Argument Indirection

```mumps
S ARGS="A,B,C"
D PROC(@ARGS)    ; Calls PROC(A,B,C)
```

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(
            name="PROC",
            arguments=[
                MIndirection(
                    expression=MVariable(name="ARGS"),
                    indirection_type=IndirectionType.ARGUMENT
                )
            ]
        )
    ]
)
```

### Pattern Indirection

```mumps
S PAT="1N.A"
I X?@PAT    ; Pattern from variable
```

**ASG Structure:**
```
MPatternMatch(
    subject=MVariable(name="X"),
    pattern=None,
    pattern_indirect=MVariable(name="PAT")
)
```

---

## Combined Indirection

### Name + Subscripts

```mumps
S NAME="ARRAY"
S @NAME(1,2)=5   ; Sets ARRAY(1,2)=5
```

**ASG Structure:**
```
MIndirection(
    expression=MVariable(name="NAME"),
    indirection_type=IndirectionType.NAME,
    subscripts=[
        MLiteral(value=1),
        MLiteral(value=2)
    ]
)
```

### Multi-Level Indirection

```mumps
S A="B"
S B="C"
S C=100
W @@A       ; Writes 100 (A→B→C→100)
```

**ASG Structure:**
```
MIndirection(
    expression=MIndirection(
        expression=MVariable(name="A"),
        indirection_type=IndirectionType.NAME
    ),
    indirection_type=IndirectionType.NAME
)
```

---

## Command Indirection

### Indirect DO

```mumps
S CMD="LABEL"
D @CMD          ; Calls LABEL
D @CMD^@ROUT    ; Both parts indirect
```

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(
            name=None,
            name_indirect=MVariable(name="CMD"),
            call_type=CallType.INDIRECT_CALL
        )
    ]
)
```

### Indirect GOTO

```mumps
S TARGET="DONE"
G @TARGET
```

**ASG Structure:**
```
MGotoStatement(
    targets=[
        MCall(
            name=None,
            name_indirect=MVariable(name="TARGET"),
            call_type=CallType.INDIRECT_CALL
        )
    ]
)
```

---

## Static Resolution

Some indirection can be resolved at analysis time:

```mumps
S X="CONST"
W @X         ; If X is never modified, can resolve statically
```

**ASG Fields:**
```
MIndirection(
    expression=MVariable(name="X"),
    can_resolve_statically=True,
    resolved_value="CONST"
)
```

---

## Code Generation Implications

### Analysis Flags

```python
MRoutine.requires_runtime_eval  # True if any unresolvable indirection
MCall.call_type  # INDIRECT_CALL for indirect DO/GOTO
```

### Generation Strategies

| Scenario | Strategy |
|----------|----------|
| Static resolvable | Substitute resolved value |
| Name indirection | Dict-based variable storage |
| Subscript indirection | Normal expression evaluation |
| Argument indirection | Runtime argument unpacking |
| Pattern indirection | Runtime regex compilation |
| Multi-level | Recursive resolution |

### Runtime Requirements

When `requires_runtime_eval=True`:

```python
# Runtime variable access
def get_var(name):
    return runtime.variables[name]

def set_var(name, value):
    runtime.variables[name] = value

# Indirect call
def indirect_do(target_str):
    label, routine = parse_target(target_str)
    call_label(label, routine)
```

---

## Examples from MUGJ

### V1IDNM.m - Name Indirection

```mumps
S X="A"
S @X=1        ; Sets A=1
S A(1)=2
S Y="A(1)"
S @Y=3        ; Sets A(1)=3
```

### V1IDDO.m - DO Indirection

```mumps
S CMD="LABEL"
D @CMD        ; Indirect call
```

### V1IDARG.m - Argument Indirection

```mumps
S ARGS="1,2,3"
D PROC(@ARGS) ; Expands to PROC(1,2,3)
```

---

## IndirectionType Enum

| Type | Example | Meaning |
|------|---------|---------|
| `NAME` | `@X` | Variable name in X |
| `SUBSCRIPT` | `A(@I)` | Subscript value |
| `ARGUMENT` | `D F(@ARGS)` | Argument list |
| `PATTERN` | `X?@PAT` | Pattern string |
| `UNKNOWN` | | Cannot determine statically |

---

## Best Practices for Code Generation

1. **Detect static cases**: If the indirected expression is a constant or known value, resolve it.

2. **Use dict-based storage**: For name indirection, use:
   ```python
   variables = {}
   variables[name] = value
   ```

3. **Defer to runtime**: For complex cases, generate runtime calls:
   ```python
   runtime.eval_indirection(expr)
   ```

4. **Track requirements**: Set `requires_runtime_eval=True` on the routine if any indirection cannot be resolved.
