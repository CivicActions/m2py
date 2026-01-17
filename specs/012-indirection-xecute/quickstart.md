# Quickstart: Indirection & XECUTE Runtime

**Date**: 2026-01-16  
**Spec**: [spec.md](spec.md)

## Overview

This guide explains how indirection (`@`) and XECUTE work in the m2py transpiler.

---

## Name Indirection

Name indirection allows dynamic variable access at runtime.

### Basic Read

```mumps
S X="VAR"
S VAR=100
W @X        ; Writes 100 (reads value of VAR via X)
```

Generated Python:
```python
_scope["X"] = "VAR"
_scope["VAR"] = 100
_rt.write(_rt.get_var(_scope.get("X", ""), _scope))  # Writes 100
```

### Basic Write

```mumps
S X="VAR"
S @X=100    ; Sets VAR=100
```

Generated Python:
```python
_scope["X"] = "VAR"
_rt.set_var(_scope.get("X", ""), 100, _scope)  # Sets _scope["VAR"]=100
```

### Multi-Level Indirection

```mumps
S A="B"
S B="C"
S C=100
W @@A       ; A→B→"C", so writes value of C (100)
```

Generated Python:
```python
_rt.write(_rt.resolve_indirection("A", 2, _scope))
```

### With Subscripts

```mumps
S NAME="ARRAY"
S @NAME@(1,2)=5   ; Sets ARRAY(1,2)=5
```

Generated Python:
```python
_name = _scope.get("NAME", "")
_rt.set_var(f"{_name}(1,2)", 5, _scope)
```

---

## XECUTE Command

XECUTE runs MUMPS code from a string at runtime.

### Constant String (Optimized)

```mumps
X "S X=1"
```

Generated Python (inlined for efficiency):
```python
_scope["X"] = 1
```

### Dynamic String

```mumps
S CODE="W 42,!"
X CODE
```

Generated Python:
```python
_scope["CODE"] = "W 42,!"
_rt.execute(_scope.get("CODE", ""), _scope)
```

### Multiple Arguments

```mumps
X "S A=1","S B=2"
```

Generated Python:
```python
_rt.execute("S A=1", _scope)
_rt.execute("S B=2", _scope)
```

### With Postcondition

```mumps
S P=1
X:P=1 "S X=5"   ; Executes only if P=1
```

Generated Python:
```python
_scope["P"] = 1
if m_truth(_scope.get("P", "")):
    _rt.execute("S X=5", _scope)
```

---

## $TEST Semantics

**Important**: XECUTE does NOT stack $TEST (unlike argumentless DO).

```mumps
I 1=1           ; $TEST=1
X "I 0=1"       ; Inner IF sets $TEST=0
E  W "ELSE"     ; ELSE sees $TEST=0, so executes
```

Output: `ELSE`

---

## Indirect DO

```mumps
S CMD="LABEL"
D @CMD          ; Calls LABEL
```

Generated Python:
```python
_target = _rt.parse_call_target(_scope.get("CMD", ""))
_rt.indirect_do(_target, _scope)
```

### With External Routine

```mumps
S RTN="ROUTINE"
D LABEL^@RTN    ; Calls LABEL in ROUTINE
```

### With Offset

```mumps
S CMD="LABEL"
D @CMD+5        ; Calls LABEL+5
```

---

## Indirect GOTO

```mumps
S TARGET="DONE"
G @TARGET       ; Jumps to DONE
```

Generated Python:
```python
_target = _rt.parse_call_target(_scope.get("TARGET", ""))
raise GotoIndirect(_target)  # Caught by trampoline
```

---

## Pattern Indirection

```mumps
S PAT="1N.N"
I "123"?@PAT W "MATCH"
```

Generated Python:
```python
import re
_pat = _rt.compile_pattern_indirect(_scope.get("PAT", ""))
if re.match(_pat, "123"):
    _rt._test = 1
    _rt.write("MATCH")
```

---

## FOR Loop Indirection

```mumps
S A="B"
F @A=1:1:3 W B   ; Loop variable is B
```

Generated Python:
```python
_loop_var = _scope.get("A", "")  # "B"
for _i in range(1, 4):
    _rt.set_var(_loop_var, _i, _scope)
    _rt.write(_scope.get("B", ""))
```

---

## Error Handling

### Invalid Variable Name

```mumps
S X="123INVALID"
S @X=1          ; Error: invalid variable name
```

Raises: `IndirectionError("123INVALID", "invalid variable name")`

### Undefined in Chain

```mumps
S A="B"
W @@A           ; Error: B is undefined
```

Raises: `IndirectionError("B", "undefined variable in indirection chain")`

### XECUTE Syntax Error

```mumps
X "S X="        ; Incomplete SET
```

Raises: `SyntaxError` with context showing XECUTE origin

---

## Common Patterns

### Dynamic Dispatch

```mumps
S ACTION=$P(INPUT,":",1)
D @ACTION       ; Dispatch to label based on input
```

### Configuration via XECUTE

```mumps
S ^CONFIG("SETUP")="S DEBUG=1,LOG=1"
X ^CONFIG("SETUP")
```

### Pattern Validation

```mumps
S PATTERNS("PHONE")="3N1""-""3N1""-""4N"
S PATTERNS("ZIP")="5N.1""-""4N"
I VALUE?@PATTERNS(TYPE) S VALID=1
```

---

## Testing

Run indirection tests:
```bash
uv run pytest tests/unit/codegen/s7_expressions/test_s7_3_indirection.py -v
uv run pytest tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py -v
uv run pytest tests/unit/cross_cutting/test_indirection.py -v
```

Validate against YDB:
```bash
uv run python utils/validate.py --code 'TEST S X="Y",Y=5 W @X Q'
```

---

## References

- [spec.md](spec.md) - Full specification
- [research.md](research.md) - Design decisions
- [contracts/runtime-api.md](contracts/runtime-api.md) - API contract
- [../../docs/examples/indirection.md](../../docs/examples/indirection.md) - ASG documentation
