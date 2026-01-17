# Indirection: @ Operator

Examples of MUMPS indirection and their ASG representation.

## Overview

Indirection (`@`) allows runtime evaluation of names, subscripts, and arguments. It's one of MUMPS's most powerful (and challenging) features.

## Implementation Status

| Type | Status | Notes |
|------|--------|-------|
| Name Indirection (`@X`) | ✅ Implemented | Read and write supported |
| Multi-level (`@@X`) | ✅ Implemented | Arbitrary nesting depth |
| Name + Subscripts (`@NAME@(1,2)`) | ⚠️ Codegen ready | Blocked by subscripted SET bug |
| Subscript Indirection (`A(@I)`) | ❌ Not yet | Future phase |
| Argument Indirection (`D F(@ARGS)`) | ❌ Not yet | Future phase |
| Pattern Indirection (`X?@PAT`) | ❌ Not yet | Future phase |

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

**Generated Python:**
```python
_scope["X"] = "VAR"
_rt.set_var(_scope.get("X", ""), 1, _scope)  # S @X=1
_rt.write(_rt.get_var(_scope.get("X", ""), _scope))  # W @X
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

**Generated Python:**
```python
_rt.write(_rt.resolve_indirection("A", 2, _scope))
```

The `resolve_indirection` method:
1. Gets value of A → "B"
2. Gets value of B → "C"  
3. Gets value of C → 100
4. Returns 100
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

## Code Generation

### Runtime Methods

The `MUMPSRuntime` class provides these methods for indirection:

| Method | Purpose |
|--------|---------|
| `get_var(name, _scope)` | Read variable by dynamic name |
| `set_var(name, value, _scope)` | Write variable by dynamic name |
| `resolve_indirection(name, levels, _scope)` | Multi-level indirection |

### Generation Strategies

| Scenario | Generated Code |
|----------|----------------|
| `@X` read | `_rt.get_var(_scope.get("X", ""), _scope)` |
| `S @X=1` | `_rt.set_var(_scope.get("X", ""), 1, _scope)` |
| `@@X` | `_rt.resolve_indirection("X", 2, _scope)` |
| `@@@X` | `_rt.resolve_indirection("X", 3, _scope)` |

### Scope Strategy

Labels using indirection have `ScopeStrategy.REQUIRES_RUNTIME`, which generates
functions with `_scope` parameter for runtime variable access:

```python
def TEST(_rt, _scope=None, **_kwargs):
    if _scope is None:
        _scope = {}
    # ... code using _rt.get_var()/_rt.set_var() ...
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
D @CMD        ; Indirect call (not yet implemented)
```

### V1IDARG.m - Argument Indirection

```mumps
S ARGS="1,2,3"
D PROC(@ARGS) ; Expands to PROC(1,2,3) (not yet implemented)
```

---

## IndirectionType Enum

| Type | Example | Status |
|------|---------|--------|
| `NAME` | `@X` | ✅ Implemented |
| `SUBSCRIPT` | `A(@I)` | ❌ Not yet |
| `ARGUMENT` | `D F(@ARGS)` | ❌ Not yet |
| `PATTERN` | `X?@PAT` | ❌ Not yet |
| `UNKNOWN` | | Analysis fallback |

---

## Testing

```bash
# Unit tests
uv run pytest tests/unit/codegen/s7_expressions/test_s7_3_indirection.py -v

# Integration tests  
uv run pytest tests/unit/cross_cutting/test_indirection.py -v

# Validate against YDB
uv run python utils/validate.py --code 'TEST S X="VAR",@X=1 W VAR Q'
```
