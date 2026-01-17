# Research: Indirection & XECUTE Runtime

**Date**: 2026-01-16  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

This document resolves all technical unknowns identified in the Technical Context section of the implementation plan.

---

## 1. Runtime XECUTE Implementation Strategy

### Decision: Reuse Existing m2py Pipeline

**Rationale**: The m2py transpiler already provides a complete MUMPS parser, ASG builder, and Python code generator. Reusing this pipeline for XECUTE ensures:
1. **Semantic consistency**: Dynamic code follows same rules as static code
2. **No duplication**: Single source of truth for MUMPS semantics
3. **Testability**: Same validation against YDB for both static and dynamic code

### Implementation Pattern

```python
# In runtime/__init__.py
def execute(self, mumps_code: str, _scope: dict) -> Any:
    """Execute MUMPS code string at runtime.
    
    Uses the same m2py pipeline as static transpilation:
    1. Parse MUMPS code string
    2. Build ASG
    3. Generate Python code
    4. Execute with exec() in context of _scope
    """
    from m2py.parser import parse_routine
    from m2py.codegen import generate_routine
    
    # Wrap code in synthetic routine for parsing
    synthetic = f"_XECUTE\n {mumps_code}\n Q\n"
    routine = parse_routine(synthetic)
    python_code = generate_routine(routine)
    
    # Execute in caller's scope context
    exec_globals = {'_rt': self, '_scope': _scope, **self._get_helpers()}
    exec(python_code, exec_globals)
```

### Alternatives Considered

| Approach | Why Rejected |
|----------|--------------|
| Build separate MUMPS interpreter | Duplicates semantics, maintenance burden |
| Use eval() directly on expressions | Doesn't handle statements, control flow |
| Precompile and cache | Optimization deferred; correctness first |

---

## 2. Name Indirection Variable Access

### Decision: Direct `_scope` Dict Access

**Rationale**: MUMPS variables are already stored in `_scope` dict (from Spec 008). Name indirection simply requires dynamic key access.

### Implementation Pattern

```python
# Read: @X (where X contains variable name)
def get_var(self, name: str) -> Any:
    """Get variable by name (name indirection read)."""
    if name.startswith("^"):
        return self.get_global(name)  # Global indirection
    return self._scope.get(name, "")  # Local, empty string if undefined

# Write: @X=value
def set_var(self, name: str, value: Any) -> None:
    """Set variable by name (name indirection write)."""
    if name.startswith("^"):
        self.set_global(name, value)  # Global indirection
    else:
        self._scope[name] = value
```

### Multi-Level Indirection

For `@@X` (multi-level), resolve iteratively:

```python
def resolve_indirection(self, expr: str, levels: int = 1) -> str:
    """Resolve N levels of name indirection."""
    result = expr
    for _ in range(levels):
        result = str(self.get_var(result))
    return result
```

### Subscripted Indirection

For `@NAME@(1,2)` syntax (name indirection with subscripts):

```python
# S NAME="ARRAY" S @NAME@(1,2)=5 → ARRAY(1,2)=5
name = _scope.get("NAME", "")  # "ARRAY"
_scope[f"{name}(1,2)"] = 5  # Or use MArray: _scope[name][1,2] = 5
```

---

## 3. Pattern Indirection

### Decision: Reuse Pattern Compiler at Runtime

**Rationale**: Pattern compiler already exists in `analysis/pattern_compiler.py`. For pattern indirection, invoke it at runtime.

### Implementation Pattern

```python
# X?@PAT where PAT="1N.N"
from m2py.analysis.pattern_compiler import compile_pattern

def match_pattern_indirect(self, subject: str, pattern_var: str) -> bool:
    """Match subject against pattern from variable (pattern indirection)."""
    pattern_str = str(self.get_var(pattern_var))
    regex = compile_pattern(pattern_str)
    return bool(re.match(regex, subject))
```

---

## 4. Indirect DO/GOTO Target Resolution

### Decision: Parse Target String, Use Existing Dispatch

**Rationale**: Indirect DO/GOTO target strings follow a simple format: `[LABEL][^ROUTINE][+OFFSET]`. Parse and dispatch using existing mechanisms.

### Implementation Pattern

```python
def resolve_call_target(self, target_str: str) -> tuple:
    """Parse indirect DO/GOTO target string.
    
    Returns: (label, routine, offset) tuple
    
    Examples:
        "LABEL" → ("LABEL", None, None)
        "^ROUTINE" → (None, "ROUTINE", None)
        "LABEL^ROUTINE" → ("LABEL", "ROUTINE", None)
        "LABEL+5" → ("LABEL", None, 5)
    """
    # Pattern: [LABEL][^ROUTINE][+OFFSET]
    match = re.match(r'^([^+^]*)?(?:\^([^+]*))?(?:\+(.*))?$', target_str)
    if not match:
        raise IndirectionError(f"Invalid call target: {target_str}")
    
    label = match.group(1) or None
    routine = match.group(2) or None
    offset_str = match.group(3)
    offset = int(offset_str) if offset_str else None
    
    return (label, routine, offset)
```

---

## 5. $TEST Semantics for XECUTE

### Decision: Do NOT Stack $TEST

**Rationale**: Per MUMPS specification, XECUTE does NOT stack $TEST (unlike argumentless DO). The `_rt._test` value is directly accessible to XECUTEd code and mutations persist.

### Implementation

XECUTE-generated code simply accesses `_rt._test` directly with no save/restore wrapper:

```python
# DO (argumentless) - stacks $TEST:
_saved_test = _rt._test
try:
    # ... block code ...
finally:
    _rt._test = _saved_test

# XECUTE - does NOT stack:
# ... executed code directly modifies _rt._test ...
# (no wrapper)
```

### Validation Reference

From MUGJ V1XECA tests and clarification session:
- `I 1=1 X "I 0=1" E W "ELSE"` outputs `ELSE` (inner IF sets $TEST=0, ELSE sees it)

---

## 6. FOR Loop Variable Indirection

### Decision: Supported per MUGJ V1IDNM1 Test I-489

**Rationale**: MUGJ test I-489 explicitly tests `F @A=1:1:3` where A contains the loop variable name. This is a real VistA pattern.

### Implementation Pattern

```python
# S A="B" F @A=1:1:3 S VCOMP=VCOMP_B
# Resolves to: F B=1:1:3

loop_var_name = _rt.get_var("A")  # "B"
for _i in range(1, 4):  # 1:1:3
    _rt.set_var(loop_var_name, _i)
    # ... body ...
```

---

## 7. Error Handling Strategy

### Decision: Raise Python Exceptions Immediately

**Rationale**: MUMPS default behavior (without `$ETRAP`/`$ECODE`) is to halt on errors. Python exceptions provide:
1. Clear error messages
2. Stack traces for debugging
3. Match MUMPS default semantics

### Implementation

```python
class IndirectionError(Exception):
    """Raised for invalid indirection operations.
    
    Attributes:
        expression: The indirection expression that failed
        reason: Human-readable error reason
    """
    def __init__(self, expression: str, reason: str):
        self.expression = expression
        self.reason = reason
        super().__init__(f"Indirection error: @{expression} - {reason}")

# Usage
def get_var(self, name: str) -> Any:
    if not self._is_valid_varname(name):
        raise IndirectionError(name, "invalid variable name")
    if name not in self._scope and not name.startswith("^"):
        raise IndirectionError(name, "undefined variable")
    return self._scope.get(name, "")
```

---

## 8. Static Optimization (Deferred)

### Decision: Always Use Runtime for This Spec

**Rationale**: Static indirection optimization (constant propagation to inline resolvable indirection) is an optimization concern, not correctness. Deferred per constitution "correctness first" principle.

### Future Optimization Opportunity

If `MIndirection.can_resolve_statically=True` and `resolved_value` is set, codegen could inline:

```python
# S X="VAR" W @X  with constant X
# Could inline to: W VAR
# But for now, always: _rt.get_var(_scope.get("X", ""))
```

---

## 9. Global Variable Indirection

### Decision: Supported via Runtime Dispatch

**Rationale**: Indirection can reference globals (`S X="^GLO",@X=1`). Detect `^` prefix and dispatch to global handlers.

### Implementation

```python
def get_var(self, name: str) -> Any:
    if name.startswith("^"):
        # Parse ^NAME or ^NAME(subs)
        return self._get_global_by_name(name)
    return self._scope.get(name, "")

def set_var(self, name: str, value: Any) -> None:
    if name.startswith("^"):
        self._set_global_by_name(name, value)
    else:
        self._scope[name] = value
```

---

## Summary of Decisions

| Unknown | Decision | Rationale |
|---------|----------|-----------|
| XECUTE implementation | Reuse m2py pipeline | Semantic consistency, no duplication |
| Name indirection access | Direct `_scope` dict | Variables already in `_scope` from Spec 008 |
| Pattern indirection | Runtime pattern compiler | Existing infrastructure, same semantics |
| Indirect DO/GOTO | Parse target, use existing dispatch | Builds on Spec 007/008 infrastructure |
| $TEST in XECUTE | Do NOT stack | Per MUMPS specification |
| FOR loop indirection | Supported | Per MUGJ V1IDNM1 test I-489 |
| Error handling | Raise Python exceptions | Matches MUMPS default, clear diagnostics |
| Static optimization | Deferred | Correctness first per constitution |
| Global indirection | Runtime dispatch | Detect `^` prefix, use global handlers |

---

## References

- [MUGJ V1IDNM1.m](../../tests/functional/mugj/inref/V1IDNM1.m) - FOR loop indirection tests
- [MUGJ V1XECA.m](../../tests/functional/mugj/inref/V1XECA.m) - XECUTE command tests
- [docs/examples/indirection.md](../../docs/examples/indirection.md) - Indirection ASG documentation
- [codegen-plan.md](../codegen-plan.md#spec-012) - Spec 012 requirements
