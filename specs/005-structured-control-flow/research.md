# Research: Spec 005 - Structured Control Flow Codegen

**Date**: 2025-01-21  
**Spec**: [spec.md](spec.md)

## Executive Summary

This document consolidates research findings for implementing structured control flow code generation in Spec 005. All NEEDS CLARIFICATION items from the Technical Context have been resolved.

---

## 1. $TEST Stack Semantics

### Decision: Save/Restore Pattern via Local Variable

**Rationale**: After analyzing the options from the spec's research phase, the save/restore pattern is the cleanest approach that:
- Maintains semantic correctness (block's $TEST doesn't leak to caller)
- Requires no runtime infrastructure (avoids principle VII violations)
- Is explicit and traceable

### $TEST Stacking Semantics (verified against YottaDB)

| Pattern | $TEST Stacked? | Behavior |
|---------|---------------|----------|
| `D SUB` (label call) | **NO** | Callee's $TEST visible to caller |
| `D SUB()` (empty args) | **NO** | Callee's $TEST visible to caller |
| `D SUB(X)` (with args) | **NO** | Callee's $TEST visible to caller |
| `D` (DO block with dots) | **YES** | Caller's $TEST restored after block |
| `$$FUNC` (extrinsic) | **YES** | Caller's $TEST restored after call |

**Key Terminology**: The term "argumentless DO" can be ambiguous:
- A **label call** without args (`D SUB`) does NOT stack $TEST
- A **DO block** (`D` followed by dot-indented lines) DOES stack $TEST

Only **DO blocks** and **extrinsic functions** stack $TEST.
All label calls (D SUB, D SUB(), D SUB(X)) share $TEST with the caller.

**Implementation Approach**:
```python
# Label calls (D SUB, D SUB(), D SUB(X)) - NO save/restore:
def caller():
    global _test
    SUB()  # Callee's $TEST changes ARE visible
    # No restoration - callee's _test value persists

# DO block (D followed by dot-indented lines) - save/restore:
def caller():
    global _test
    _saved_test = _test
    # ... block body (dot-indented statements) ...
    _test = _saved_test  # Restore after block

# Extrinsic function call - save/restore:
_saved_test = _test
result = extrinsic_func()
_test = _saved_test
```

**Alternatives Rejected**:
1. **Thread-local stack**: Adds runtime infrastructure, violates VII
2. **Context manager**: Syntactic overhead, harder to trace
3. **Pass as hidden parameter**: Changes all function signatures, complex

### YottaDB Validation Evidence

```mumps
; Test 1: D SUB (label call) - $TEST NOT stacked
TEST S X=1 I X W "After I X: $T=",$T,!
 D SUB
 W "After D SUB: $T=",$T,!   ; Shows $T=0 (callee's value)
 E  W "ELSE executed",!       ; ELSE DOES execute
 Q
SUB I 0 Q

; Output: After I X: $T=1, After D SUB: $T=0, ELSE executed

; Test 2: D block - $TEST IS stacked
TEST S Y=1 I Y W "After I Y: $T=",$T,!
 D
 . I 0 W "Inside block: $T=",$T,!
 W "After block: $T=",$T,!    ; Shows $T=1 (restored)
 E  W "ELSE2 executed",!      ; ELSE does NOT execute
 Q

; Output: After I Y: $T=1, After block: $T=1
```

---

## 2. By-Reference Parameter Handling

### Decision: Return Tuple Destructuring

**Rationale**: Clean, explicit, Pythonic pattern that:
- Makes data flow visible
- Requires no mutation tracking infrastructure
- Works with existing `FunctionSignature.byref_outputs` analysis

**Implementation Pattern**:
```python
# MUMPS: D SWAP(.A,.B)
# Where SWAP(X,Y) modifies both X and Y

def SWAP(x, y):
    return y, x  # Returns modified values

# Call site with by-ref args:
A, B = SWAP(A, B)  # Destructure results back

# Mixed by-ref and return value:
# MUMPS: S R=$$FUNC(.X,Y)
def FUNC(x, y):
    x = x + 1  # Modifies by-ref param
    return x * y, x  # (return_value, modified_x)

result, X = FUNC(X, Y)
```

**Call Site Generation Rules**:
1. Check callee's `FunctionSignature.byref_outputs`
2. For each actual param passed by-ref (`.VAR`), include its name in destructuring
3. Order: return value first (if any), then by-ref outputs in formal param order

**Dependency**: Requires `compute_all_signatures()` to be run before codegen.

---

## 3. FOR Loop Variable Visibility After Exit

### Decision: Loop variable survives with final value

**Rationale**: This is MUMPS semantics per MDC 7.1.10. After a FOR loop completes:
- Loop variable holds the value that caused loop termination
- For bounded loops: one step past the end
- For QUIT exit: value at QUIT execution

**Implementation Impact**:
```python
# MUMPS: F I=1:1:10 D WORK
# After loop: I=11 (one past end)

for i in range(1, 11):
    work()
# Python: i=10 after loop (last iteration value)
# MUMPS: I=11

# Need explicit final assignment for bounded loops:
for i in range(1, 11):
    work()
i = 11  # Set to termination value
```

**Decision**: For Spec 005, accept Python's behavior (final iteration value) since difference is rare to observe. Document as known divergence. Full fix deferred to Spec 006+ if needed.

---

## 4. Existing Infrastructure Analysis

### Analysis Modules - COMPLETE

| Module | Status | Key Exports Used in Spec 005 |
|--------|--------|------------------------------|
| `for_analysis.py` | ✅ Complete | `ForLoopType`, `loop_var_modified_in_body`, `has_internal_quit`, `has_internal_goto` |
| `goto_analysis.py` | ✅ Complete | `GotoType`, `is_cross_label`, `is_loop_continue`, `exits_loops` |
| `variables.py` | ✅ Complete | `FunctionSignature`, `ScopeStrategy`, `byref_outputs`, `compute_all_signatures()` |

### Codegen Modules - PARTIAL

| Module | Status | Changes Needed for Spec 005 |
|--------|--------|----------------------------|
| `routine.py` | ✅ Basic | Add formal parameters to function signatures, scope strategy dispatch |
| `statements.py` | ⚠️ Basic | Extend FOR (while loops, open-ended), GOTO (break/continue), QUIT (context-aware) |
| `emitter.py` | ✅ Complete | No changes needed |
| `names.py` | ✅ Complete | No changes needed |
| `helpers.py` | ✅ Complete | May need `m_for_range()` helper |

### ASG Fields Used

All required fields are already populated by analysis passes:

```python
# MForStatement (from for_analysis.py)
loop_type: ForLoopType           # ✅ Populated
loop_var_modified_in_body: bool  # ✅ Populated
has_internal_quit: bool          # ✅ Populated
has_internal_goto: bool          # ✅ Populated
exit_points: List[MGotoStatement]# ✅ Populated

# MGotoStatement (from goto_analysis.py)
goto_type: GotoType              # ✅ Populated
is_cross_label: bool             # ✅ Populated
is_loop_continue: bool           # ✅ Populated
exits_loops: List[MForStatement] # ✅ Populated

# MQuitStatement (from parser)
exits_for: bool                  # ✅ Populated
exits_do_block: bool             # ✅ Populated
return_value: Optional[MExpr]    # ✅ Populated

# FunctionSignature (from variables.py)
scope_strategy: ScopeStrategy    # ✅ Populated
byref_outputs: Set[str]          # ✅ Populated
formal_params: List[str]         # ✅ Populated
```

---

## 5. FOR Loop Code Generation Patterns

### Decision Matrix

| loop_var_modified | has_internal_quit | has_internal_goto | Pattern |
|-------------------|-------------------|-------------------|---------|
| False | False | False | `for i in range(...)` |
| False | True | False | `for i in range(...): ... break` |
| False | False | True | `for i in range(...): ... break` (GOTO becomes break) |
| False | True | True | `for i in range(...): ... break` |
| True | * | * | `while` loop with manual stepping |

### Open-Ended FOR (F I=1:1)

```python
# Option 1: itertools.count (preferred)
from itertools import count
for i in count(start, step):
    if condition:
        break

# Option 2: while loop
i = start
while True:
    # body
    i += step
```

**Decision**: Use `itertools.count` for cleaner code when loop var not modified.

### Argumentless FOR (F)

```python
while True:
    # body
    if condition:
        break
```

---

## 6. GOTO Patterns for Spec 005

### In-Scope Patterns (is_cross_label=False, forward direction only)

| Pattern | GOTO Type | Generated Code |
|---------|-----------|----------------|
| Loop continue | `LOOP_EXIT` + `is_loop_continue=True` | `continue` |
| Single loop exit | `LOOP_EXIT` | `break` |
| Multi-loop exit | `MULTI_LOOP_EXIT` | Exception pattern |
| Forward in label | `FORWARD_JUMP` + `is_cross_label=False` | If/else restructuring |

### Out-of-Scope Patterns (raise UnsupportedFeatureError)

| Pattern | GOTO Type | Deferred To |
|---------|-----------|-------------|
| Cross-label forward | `FORWARD_JUMP` + `is_cross_label=True` | Spec 006 |
| Cross-label backward | `BACKWARD_JUMP` + `is_cross_label=True` | Spec 006 |
| Backward intra-label | `BACKWARD_JUMP` + `is_cross_label=False` | Spec 006 (creates implicit loops) |
| External routine | `EXTERNAL` | Spec 009 |
| Unresolved/dynamic | `UNRESOLVED` | Spec 007 |

### Exception Pattern for Multi-Loop Exit

```python
class _LoopExit(Exception):
    """Exception for multi-loop exit pattern."""
    pass

try:
    for i in range(1, 11):
        for j in range(1, 11):
            if condition:
                raise _LoopExit()
        # more code
except _LoopExit:
    pass
# code after GOTO target
```

**Decision**: Define `_LoopExit` in generated module, not in helpers.

### Forward Jump Restructuring

```mumps
       I X=1 G SKIP
       W "Not skipped"
SKIP   W "After"
```

Becomes:
```python
if not m_truth(X == 1):
    print("Not skipped")
print("After")
```

**Limitation**: Only handles single-level forward jumps in Spec 005. Complex patterns deferred to Spec 006.

---

## 7. Scope Strategy Code Generation

### PURE_FUNCTION
```python
def label(formal1, formal2):
    # computation
    return result
```

### FUNCTION_WITH_OUTPUTS
```python
def label(formal1, formal2):
    # computation
    formal2 = modified_value  # by-ref output
    return result, formal2
```

### SUBROUTINE
```python
def label(formal1, formal2):
    # side effects
    # implicit return None
```

### REQUIRES_RUNTIME (Out of Scope for 005)
Raise `UnsupportedFeatureError` with message indicating Spec 006/007.

---

## 8. $TEST Elimination Spike Results

**Hypothesis from Spec**: Many IF/ELSE chains can be restructured to eliminate explicit `_test` tracking.

**Analysis**: After reviewing codegen/statements.py and MUMPS patterns:

1. **Argumentless IF** (`I  D action`) - Must use `_test`, cannot eliminate
2. **IF/ELSE pairs** - Can often restructure to Python `if/else` without `_test`
3. **Postconditioned commands** - Spec 005 doesn't implement, deferred

**Decision**: Keep current `_test` tracking approach. Restructuring adds complexity for marginal benefit. May revisit in future optimization pass.

---

## 9. Testing Strategy

### YDB Reference Testing
- Use `execute_mumps` fixture for authoritative MUMPS behavior
- Compare Python output to YDB output for each control flow pattern

### Test Categories
1. **$TEST semantics**: Extrinsic calls, argumentless IF, condition chains
2. **FOR variations**: Bounded, open-ended, argumentless, value-list, mixed
3. **GOTO patterns**: Loop continue, loop exit, multi-loop exit, intra-label forward
4. **QUIT context**: In FOR (break), in DO (return), with value (return val)
5. **By-ref parameters**: Single output, multiple outputs, mixed with return

### Coverage Target
- 85%+ code coverage on new codegen additions
- 100% of spec test cases passing against YDB

---

## 10. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Analysis fields not populated correctly | Low | High | Add assertions, fail fast |
| Edge cases in GOTO restructuring | Medium | Medium | Conservative patterns, defer complex to 006 |
| By-ref tuple ordering confusion | Medium | Low | Clear documentation, consistent ordering |
| Python FOR semantics divergence | Low | Low | Document, accept for 005 |

---

## Appendix: Key Source References

- `src/m2py/analysis/for_analysis.py` - FOR loop classification
- `src/m2py/analysis/goto_analysis.py` - GOTO classification  
- `src/m2py/analysis/variables.py` - Scope and signature analysis
- `src/m2py/codegen/statements.py` - Statement code generation
- `src/m2py/codegen/routine.py` - Module-level generation
- `src/m2py/asg/enums.py` - ForLoopType, GotoType, ScopeStrategy
- `docs/codegen/for_loops.md` - FOR translation patterns
- `docs/codegen/goto_handling.md` - GOTO translation patterns
