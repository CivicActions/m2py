# Indirection: @ Operator

Examples of MUMPS indirection and their ASG representation.

## Overview

Indirection (`@`) allows runtime evaluation of names, subscripts, and arguments. It's one of MUMPS's most powerful (and challenging) features.

## Implementation Status

| Type | Status | Notes |
|------|--------|-------|
| Name Indirection (`@X`) | ✅ Implemented | Read and write supported |
| Multi-level (`@@X`) | ✅ Implemented | Arbitrary nesting depth |
| Name + Subscripts (`@NAME@(1,2)`) | ✅ Implemented | Uses `name_indirection_subscripts` |
| Indirect DO (`D @TARGET`) | ✅ Implemented | Spec 012 Phase 7 |
| Indirect GOTO (`G @TARGET`) | ✅ Implemented | Spec 012 Phase 8 |
| SET Argument Indirection (`S @A`) | ✅ Implemented | Spec 012 Phase 9 |
| Pattern Indirection (`X?@PAT`) | ✅ Implemented | Spec 012 Phase 10 |
| FOR Loop Variable (`F @A=1:1:3`) | ✅ Implemented | Spec 012 Phase 11 |
| KILL Indirection (`K @X`) | ✅ Implemented | Spec 012 Phase 11 |
| NEW Indirection (`N @X`) | ✅ Implemented | Spec 012 Phase 11 |
| Subscript Indirection (`A(@I)`) | ❌ Not yet | Future phase |
| XECUTE Constant (`X "S X=1"`) | ✅ Implemented | Inlined at transpile time |
| XECUTE Dynamic (`X CODE`) | ✅ Implemented | Via runtime execute_mumps() |

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

### SET Argument Indirection

SET command argument indirection allows dynamic assignment strings:

```mumps
S A="X=1" S @A     ; Sets X to 1
S B="Y=2,Z=3" S @B ; Sets Y to 2 and Z to 3
```

**ASG Structure:**
```
MSetStatement(
    assignments=[],  ; Empty - no static assignments
    argument_indirections=[
        MIndirection(
            expression=MVariable(name="A"),
            indirection_type=IndirectionType.ARGUMENT
        )
    ]
)
```

**Generated Python:**
```python
_rt.execute_mumps("S " + str(_scope.get('A', '')), _scope)
```

The runtime parses and executes the SET argument string dynamically.

### Nested SET Argument Indirection

Indirection chains work with argument indirection:

```mumps
S A="@B",B="X=5"
S @A              ; First resolves A to "@B", then resolves to "X=5"
```

### Pattern Indirection

Pattern indirection allows dynamic pattern matching at runtime:

```mumps
S PAT="1N.N"
I "123"?@PAT W "MATCH"    ; Pattern compiled at runtime
```

**ASG Structure:**
```
MPatternMatch(
    subject=MLiteral(value="123"),
    pattern="",              ; Empty for indirect
    pattern_indirect=MVariable(name="PAT"),
    operator="?"
)
```

**Generated Python:**
```python
_scope['PAT'] = "1N.N"
_test = m_truth(m_pattern_match("123", _scope.get('PAT', '')))
if _test:
    _rt.write("MATCH")
```

The runtime `m_pattern_match()` helper uses the pattern compiler to convert MUMPS patterns to Python regex at runtime. Note: Direct (non-indirect) pattern matches use pre-compiled regex for better performance.

### Negated Pattern Indirection

The negated pattern match operator (`'?`) also supports indirection:

```mumps
S PAT="1N"
I "A"'?@PAT W "NOT NUMERIC"   ; "A" does not match "1N"
```

**Generated Python:**
```python
_test = m_truth(int(not m_pattern_match("A", _scope.get('PAT', ''))))
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

## XECUTE Command

The XECUTE command executes MUMPS code from a string at runtime.

### Constant String XECUTE

```mumps
X "S X=1"      ; Execute SET command
X "W 42"       ; Execute WRITE command
```

**Optimization:** Constant strings are parsed at transpile time and inlined.

**ASG Structure:**
```
MXecuteStatement(
    code_expressions=[MLiteral(value="S X=1")],
    is_constant=True,
    constant_values=["S X=1"]
)
```

**Generated Python:**
```python
_scope["X"] = 1  # Inlined from "S X=1"
```

### Multiple Arguments

```mumps
X "S A=1","S B=2"
```

Each argument is processed in order:

**Generated Python:**
```python
_scope["A"] = 1
_scope["B"] = 2
```

### XECUTE with Postcondition

```mumps
X:cond "S X=1"  ; Execute only if cond is true
```

**Generated Python:**
```python
if m_truth(cond_expr):
    _scope["X"] = 1
```

### Dynamic XECUTE

```mumps
S CODE="W 42"
X CODE           ; Execute code from variable
```

Dynamic XECUTE uses runtime `execute_mumps()` to parse and execute code at runtime.

**ASG Structure:**
```
MXecuteStatement(
    code_expressions=[MVariable(name="CODE")],
    is_constant=False,
    constant_values=[]
)
```

**Generated Python:**
```python
_rt.execute_mumps(_scope.get("CODE", ""), _scope)
```

### Scope Sharing in XECUTE

XECUTEd code shares the caller's variable scope:

```mumps
S OUTER=10
X "S INNER=OUTER+1"   ; INNER=11 (reads OUTER from caller)
W INNER               ; Outputs 11
```

**Generated Python:**
```python
_scope["OUTER"] = 10
_rt.execute_mumps("S INNER=OUTER+1", _scope)  # _scope passed
_rt.write(_scope.get("INNER", ""))
```

The `_scope` dictionary is passed to `execute_mumps()`, allowing the executed
code to read and modify caller's variables.

### Global Access in XECUTE

XECUTEd code has full access to global variables through the runtime:

```mumps
S ^DATA=42
X "W ^DATA"            ; Outputs: 42
X "S ^OUT=99"          ; Sets global
```

**Generated Python:**
```python
_rt.globals.set('DATA', (), str(42))
_rt.execute_mumps("W ^DATA", _scope)  # Reads global via _rt
```

This is particularly useful for VistA patterns like `X ^%ZOSF("key")` which
execute platform-specific code stored in the `^%ZOSF` global:

```mumps
S ^ZOSF("CODE")="W 123,!"
X ^ZOSF("CODE")        ; Outputs: 123
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

## FOR Loop Variable Indirection

FOR loops support indirect loop variables:

```mumps
S A="I"
F @A=1:1:3 W I    ; Loop variable is I, outputs 123
```

**ASG Structure:**
```
MForStatement(
    loop_var=MIndirection(
        expression=MVariable(name="A"),
        indirection_type=IndirectionType.NAME
    ),
    parameters=[MForParameter(param_type=RANGE, start=1, step=1, end=3)],
    body=[...]
)
```

**Generated Python:**
```python
_for_indirect_var = _rt.get_indirection_source("A", _scope)
_scope.setdefault(_for_indirect_var, MArray()).value = m_num(1)
_for_step = m_num(1)
_for_end = m_num(3)
while (_for_step > 0 and _scope.setdefault(_for_indirect_var, MArray()).value <= _for_end) or (_for_step < 0 and _scope.setdefault(_for_indirect_var, MArray()).value >= _for_end):
    _rt.write(_scope.get('I', MArray()).value)
    if not ((_for_step > 0 and _scope.setdefault(_for_indirect_var, MArray()).value + _for_step <= _for_end) or (_for_step < 0 and _scope.setdefault(_for_indirect_var, MArray()).value + _for_step >= _for_end)):
        break
    _scope.setdefault(_for_indirect_var, MArray()).value = _scope.setdefault(_for_indirect_var, MArray()).value + _for_step
```

The loop variable name is resolved once via `get_indirection_source()` and used throughout the loop.

### String List with Indirect Variable

```mumps
S A="V"
F @A="X","Y","Z" W V    ; Outputs XYZ
```

**Generated Python:**
```python
_for_indirect_var = _rt.get_indirection_source("A", _scope)
_for_values = ["X", "Y", "Z"]
_for_idx = 0
while _for_idx < len(_for_values):
    _scope.setdefault(_for_indirect_var, MArray()).value = _for_values[_for_idx]
    _rt.write(_scope.get('V', MArray()).value)
    _for_idx += 1
```

---

## KILL Indirection

KILL supports indirect variable targets:

```mumps
S A="TARGET"
S TARGET=1
K @A          ; Kills TARGET (A contains "TARGET")
```

**Generated Python:**
```python
_scope['A'] = "TARGET"
_scope['TARGET'] = 1
_target = _rt.get_indirection_source("A", _scope)
_scope.pop(_target, None)
```

The source variable (A) remains unchanged; only the target (TARGET) is killed.

---

## NEW Indirection

NEW supports indirect variable targets:

```mumps
S A="X"
S X=1
N @A          ; NEWs X (A contains "X")
S X=2
; When scope exits, X is restored to 1
```

**Generated Python:**
```python
_target = _rt.get_indirection_source("A", _scope)
with NewScopeManager(_scope, [_target]):
    # body that may modify X
    pass
# X restored when exiting scope
```

---

## Error Handling

### Undefined Indirection Source

Accessing an undefined variable via indirection raises a clear error:

```mumps
W @UNDEF      ; Error: Undefined local variable: UNDEF
```

The `get_indirection_source()` runtime method validates that the source variable exists before resolving.

### Invalid Variable Names

Indirection targets must be valid MUMPS variable names:

```mumps
S A="123INVALID"
W @A          ; Error: invalid variable name - must start with letter or %
```

```mumps
S A=""
W @A          ; Error: empty variable name
```

---

## IndirectionType Enum

| Type | Example | Status |
|------|---------|--------|
| `NAME` | `@X` | ✅ Implemented |
| `SUBSCRIPT` | `A(@I)` | ❌ Not yet |
| `ARGUMENT` | `S @A` | ✅ Implemented |
| `PATTERN` | `X?@PAT` | ✅ Implemented |
| `UNKNOWN` | | Analysis fallback |

---

## Testing

```bash
# Unit tests for indirection codegen
uv run pytest tests/unit/codegen/s7_expressions/test_s7_3_indirection.py -v

# Unit tests for XECUTE codegen
uv run pytest tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py -v

# Integration tests  
uv run pytest tests/unit/cross_cutting/test_indirection.py -v

# Validate against YDB
uv run python utils/validate.py --code 'TEST S X="VAR",@X=1 W VAR Q'
uv run python utils/validate.py --code 'TEST X "S X=1" W X Q'
```
