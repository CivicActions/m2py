# GOTO Handling Strategies

Python code generation for MUMPS GOTO statements.

## Overview

GOTO is MUMPS's primary control flow mechanism. The code generator translates it to Python's structured constructs.

## GOTO Classifications

After `classify_gotos()`, each MGotoStatement has a `goto_type`:

| GotoType | Meaning | Python Strategy |
|----------|---------|-----------------|
| `FORWARD_JUMP` | To later code (same label) | Inverted if/else |
| `LOOP_EXIT` | Out of one FOR | `break` |
| `MULTI_LOOP_EXIT` | Out of nested FORs | `raise _LoopExit()` |
| `FORWARD_JUMP` (cross-label) | To later label | Trampoline: `return (label, state)` |
| `BACKWARD_JUMP` (intra-label) | To earlier code in same label | `while True:` + `continue` |
| `BACKWARD_JUMP` (cross-label) | To earlier label | Trampoline: `return (label, state)` |
| `EXTERNAL` | To other routine | Not yet supported (Spec 008) |
| `UNRESOLVED` | Dynamic target | Not yet supported (Spec 012) |

## Intra-Label Forward Jump

When a GOTO targets a line within the same label, `generate_scope_statements()` restructures it to an inverted if/else block.

**MUMPS Offset Semantics**: `LABEL+n` targets line n from LABEL (0-indexed). For example, `G TEST+4` from TEST at line 1 targets line 5.

```mumps
TEST   I 1 G TEST+4    ; Line 1 - if true, skip to line 5
       W "A",!         ; Line 2 - skipped when GOTO fires
       W "B",!         ; Line 3 - skipped when GOTO fires
       W "C",!         ; Line 4 - skipped when GOTO fires
       W "D",!         ; Line 5 - target (TEST+4)
       Q
```

```python
def TEST():
    global _test
    _test = m_truth(1)
    if not _test:
        _rt.write(str("A"))
        _rt.write(str("\n"))
        _rt.write(str("B"))
        _rt.write(str("\n"))
        _rt.write(str("C"))
        _rt.write(str("\n"))
    _rt.write(str("D"))
    _rt.write(str("\n"))
```

**Implementation Details**:
- `is_restructurable` field (set by `classify_gotos()`) identifies intra-label forward GOTOs
- `MIfStatement.restructurable_goto` field (set by `classify_gotos()`) provides direct back-reference
- `_find_forward_goto_in_if()` returns the pre-computed back-reference (no scanning needed)
- `_restructure_forward_goto()` generates the inverted if/else structure
- `target_stmt_index` (computed in `classify_gotos()`) identifies which statements to wrap

## Cross-Label Jump

Cross-label GOTOs transfer control to a different label function:

```mumps
START  I X=1 G DONE
       W "Not 1"
       Q
DONE   W "Done"
```

```python
def START():
    global _test
    _test = m_truth(m_compare(X, "=", 1))
    if _test:
        DONE()
        return
    _rt.write(str("Not 1"))

def DONE():
    _rt.write(str("Done"))
```

The `return` after the call ensures control doesn't continue past the GOTO.

## Single Loop Exit

When a GOTO exits exactly one FOR loop, it generates `break`:

```mumps
F I=1:1:100 D
. I ERR G DONE
. D WORK
DONE W "Exited"
```

```python
for I in range(1, 101):
    _test = m_truth(ERR)
    if _test:
        break
    WORK()
# Label DONE continues here
_rt.write(str("Exited"))
```

The `exits_loops` attribute (computed by analysis) contains exactly one loop.

## Multi-Loop Exit

When a GOTO exits multiple nested FOR loops, it generates `raise _LoopExit()`:

```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=Y G ALLDONE
ALLDONE W "Done"
```

```python
class _LoopExit(Exception):
    pass

try:
    for I in range(1, 11):
        for J in range(1, 11):
            _test = m_truth(m_compare(X, "=", Y))
            if _test:
                raise _LoopExit()
except _LoopExit:
    pass  # Multi-loop exit completed
# Label ALLDONE continues here
_rt.write(str("Done"))
```

**Implementation Details**:
- `MRoutine.needs_loop_exit_exception` field (set by analysis) indicates if any GOTO has `GotoType.MULTI_LOOP_EXIT`
- The `_LoopExit` class is generated in the module preamble only when needed
- `_for_needs_loop_exit_wrapper()` determines which FOR loop gets the try/except wrapper

## No Continue Semantics

**Important**: GOTO cannot create Python `continue` semantics. Per MDC 3.6.5:

> "Execution of GOTO effects the immediate termination of all FORs in the line containing the GOTO."

A GOTO to the same label creates recursion, not skip-iteration:

```mumps
LOOP F I=1:1:10 I I=5 G LOOP
     W I
     Q
```

This creates an **infinite loop** in YDB - when I=5, `G LOOP` transfers to LOOP label and restarts the entire FOR from I=1.

### Skip-Iteration Alternatives

Use conditional execution:

```mumps
F I=1:1:10 I I'=5 W I
```

```python
for I in range(1, 11):
    _test = m_truth(m_compare(I, "'=", 5))
    if _test:
        _rt.write(str(I))
```

Or QUIT from DO block:

```mumps
F I=1:1:10 D
. I I=5 Q
. W I
```

```python
for I in range(1, 11):
    _test = m_truth(m_compare(I, "=", 5))
    if _test:
        pass  # QUIT exits DO block, not FOR
    else:
        _rt.write(str(I))
```

## Conditional GOTO

Postcondition syntax `G:cond target` generates conditional code:

```mumps
G:X=1 DONE
```

```python
_test = m_truth(m_compare(X, "=", 1))
if _test:
    DONE()
    return
```

## Multiple GOTO Targets

MUMPS supports multiple GOTO targets: `G A,B,C`. The semantics depend on postconditions:

### Without Postconditions

`G A,B,C` simply goes to the first target (A). The subsequent targets only matter if all preceding targets have false postconditions.

```mumps
TEST G A,B,C  ; Same as G A - just goes to A
```

### With Postconditions

Each target can have a postcondition. Targets are evaluated left-to-right, and the first target with a true (or missing) postcondition is taken:

```mumps
TEST G A:X,B:Y,C  ; If X true -> A; else if Y true -> B; else -> C
```

If all postconditions are false, no GOTO is performed and execution continues to the next command:

```mumps
TEST G A:0,B:0 W "no goto"  ; Outputs "no goto"
```

### Generated Code Pattern

For multiple targets with postconditions, an if/elif chain is generated:

```python
if X:
    return ("A", state)  # Cross-label jump
elif Y:
    return ("B", state)
else:
    return ("C", state)
```

For targets without postconditions (unconditional), processing stops at that target since subsequent targets can never be reached.

## Not Yet Supported

The following GOTO patterns raise `NotImplementedError` or `UnsupportedFeatureError`:

| Pattern | Example | Reason | Spec |
|---------|---------|--------|------|
| External routine | `G LABEL^OTHER` | Requires module import handling | 008 |
| Indirect | `G @VAR` | Runtime dispatch needed | 012 |
| Argumentless | `G` | Returns to caller | 006 |

## Backward Intra-Label GOTO (Self-Loop Pattern)

When a label GOTOs to itself (intra-label backward GOTO), it creates an implicit loop. The code generator wraps the label body in `while True:`:

```mumps
TEST S X=0
     S X=X+1 W X I X<3 G TEST
     Q
```

```python
def TEST():
    global _test
    while True:
        X = 0
        X = (m_num(X) + m_num(1))
        _rt.write(str(X))
        _test = m_truth(m_compare(X, "<", 3))
        if _test:
            continue  # G TEST
        break  # Q
```

**Implementation Details**:
- `MLabel.has_self_loop` field is set by `classify_gotos()` when a backward intra-label GOTO is detected
- In `_generate_trampoline_label()` and `_generate_label()`, labels with `has_self_loop=True` wrap body in `while True:`
- Backward GOTO to self becomes `continue`
- QUIT becomes `break`
- Implicit `break` at end of body prevents infinite loop if no explicit exit

## Backward Cross-Label GOTO

When a GOTO targets an earlier label (cross-label backward), the trampoline pattern handles it naturally by returning the target label name. The dispatcher loop iterates back to the earlier label.

```mumps
TEST S X=0 G LOOP
INC S X=X+1 W X
LOOP I X<3 G INC
     Q
```

The trampoline dispatcher handles the cycle:
1. `_TEST` sets X=0, returns `("LOOP", state)`
2. `_LOOP` checks condition, if true returns `("INC", state)` (backward)
3. `_INC` increments X, falls through to `_LOOP`
4. Loop continues until condition is false

This pattern prevents stack overflow - no recursion occurs.

## Strategy Selection (Spec 006)

The code generator selects a strategy based on ASG analysis:

```python
from m2py.codegen.enums import GotoStrategy

def _select_goto_strategy(routine: MRoutine) -> GotoStrategy:
    """Select GOTO code generation strategy based on routine analysis."""
    if routine.needs_trampoline:
        return GotoStrategy.TRAMPOLINE
    return GotoStrategy.SIMPLE_FUNCTIONS
```

| Strategy | When Used | Description |
|----------|-----------|-------------|
| `SIMPLE_FUNCTIONS` | No cross-label GOTOs | Labels become simple functions (current behavior) |
| `TRAMPOLINE` | Any cross-label GOTOs | Labels return target, dispatcher loop handles control |

Unsupported patterns raise `UnsupportedFeatureError` referencing future specs:
- `UNRESOLVED` GOTOs → "See Spec 012"
- `EXTERNAL` GOTOs → "See Spec 008"

## Trampoline Pattern (Spec 006 Phase 5+)

When `needs_trampoline=True`, the code generator produces:

1. **RoutineState dataclass** - Carries variables across label boundaries
2. **Label functions** - Prefixed with `_`, accept state parameter, return `(next_target, state)` tuple
3. **Entry point function** - Named after first label, creates state and runs trampoline dispatcher
4. **Labels dictionary** - Maps label names to their functions
5. **Line map** (Spec 007) - Maps source line numbers to (label, offset) tuples for offset dispatch

```python
from dataclasses import dataclass, field
from typing import Any, Optional, Tuple

@dataclass
class RoutineState:
    """Shared state for cross-label variable visibility."""
    X: Any = None

def _TEST(state, _start_offset=0) -> Tuple[Optional[str | int], RoutineState]:
    """Label function receives/returns state."""
    global _test
    if _start_offset <= 0:
        state.X = m_num(1)
        return ("NEXT", state)  # Cross-label GOTO
    return (None, state)

def _NEXT(state, _start_offset=0) -> Tuple[Optional[str | int], RoutineState]:
    global _test
    if _start_offset <= 0:
        _rt.write(str(state.X))
    return (None, state)  # End execution

_labels = {
    "TEST": _TEST,
    "NEXT": _NEXT,
}

# Spec 007: Line map for offset dispatch
_line_map: dict[int, tuple[str, int]] = {
    1: ("TEST", 0),
    2: ("NEXT", 0),
}

def TEST():
    """Trampoline dispatcher for routine execution."""
    state = RoutineState()
    target: str | int | None = "TEST"

    while target is not None:
        if isinstance(target, int):
            label_name, offset = _line_map[target]
            func = _labels[label_name]
            target, state = func(state, _start_offset=offset)
        else:
            func = _labels[target]
            target, state = func(state)

    return state
```

**Key Implementation Details:**

- Label functions are prefixed with `_` (e.g., `_TEST`) to distinguish from entry point
- The entry point (`TEST()`) has the original label name for external callers
- Cross-label GOTOs return the target label as a string: `return ("NEXT", state)`
- **Spec 007**: Offset GOTOs return line number: `return (label_line + offset, state)`
- **Spec 007**: Dispatcher handles `int` targets via `_line_map` lookup
- **Spec 007**: Label functions accept `_start_offset=0` parameter for entry at offset
- QUIT returns `(None, state)` to exit the trampoline loop
- Fall-through to next label returns that label's name instead of `None`
- FOR loop variables in state use `state.VAR` for loop counter when cross-label visible

## Computed Offsets (Spec 007)

GOTO/DO with computed offsets (`G LABEL+N`, `D SUB+expr`) dispatches by source line number:

```mumps
TEST G STAR+2 Q    ; Line 1 - jump to STAR+2 = line 4
STAR W "0"         ; Line 2 - offset 0 (label line)
 W "1"             ; Line 3 - offset 1
 W "2"             ; Line 4 - offset 2 (target)
 Q                 ; Line 5 - offset 3
```

**Generated Code Pattern:**

1. **GOTO with offset**: emits `return (label_line + int(offset_expr), state)`
2. **DO with offset**: emits `_LABEL(state, _start_offset=int(offset_expr))`
3. Dispatcher resolves line number via `_line_map[target]` → `(label_name, offset)`
4. Label function is called with `_start_offset=offset`
5. Each statement has offset guard: `if _start_offset <= N:` to skip earlier statements

**DO+Offset Example:**

```mumps
TEST F N=0:1:2 D LINE+N
 Q
LINE W "A"
 W "B"
 W "C"
 Q
```

Output: `ABCBCC` (N=0→ABC, N=1→BC, N=2→C)

```python
# Generated DO+offset call:
_LINE(state, _start_offset=int(N))
```

**Offset Semantics:**

- Offset 0 = label line itself
- Offset 1 = first statement after label line
- Offsets are based on source line number difference: `stmt.line_number - label.line_number`
- DO with offset returns to caller after QUIT (unlike GOTO which transfers control)
- Non-integer offsets are truncated toward zero (e.g., 2.7 → 2, 2.999 → 2)
- Invalid offsets (past end of routine) raise "Entry point LABEL+N not valid" error
- **String coercion**: String offsets are coerced using MUMPS numeric rules via `m_num()` (e.g., `"ABC"` → 0, `"2A"` → 2)
- **Negative offsets**: Negative values raise `ValueError("Entry point LABEL+-N not valid")` at runtime

**Non-Executable Line Handling:**

When an offset lands on a non-executable line (comment or blank), execution continues to the next executable line:

```mumps
TEST G STAR+1 Q    ; Target line 3 (comment)
STAR W "0"         ; Line 2 - offset 0
;comment line      ; Line 3 - offset 1 (non-executable)
 W "2"             ; Line 4 - offset 2 (next executable)
 Q
```

Output: `2` (skips comment, continues to next executable)

**Generated Code Pattern:**

```python
_target = label_line + int(offset_expr)
if _target not in _line_map:
    _next = min((ln for ln in _line_map if ln > _target), default=None)
    if _next is None:
        raise ValueError("Entry point LABEL+offset not valid")
    _target = _next
return (_target, state)
```

**Strategy Selection:**

- Routines with offset calls use TRAMPOLINE strategy (even without cross-label GOTOs)
- This ensures label functions have `_start_offset` parameter and offset guards

## MArray Runtime Support

For subscripted local variables that flow across labels, the `MArray` class provides MUMPS array semantics:

```python
from m2py.runtime import MArray

# MUMPS: S A=1,A(1)=2,A(1,2)=3
arr = MArray()
arr.value = 1        # Root has value
arr[1] = 2           # And children
arr[1, 2] = 3        # Nested subscripts

# Access
arr.get()           # → 1 (root value)
arr.get(1)          # → 2
arr.get(1, 2)       # → 3

# $DATA semantics
arr.defined()       # → 11 (has value AND children)
arr.defined(1)      # → 11 (has value AND children)
arr.defined(1, 2)   # → 1  (has value only)
arr.defined(9)      # → 0  (undefined)
```

The `MArray` class supports:
- `__getitem__`, `__setitem__` for subscripted access
- `value` property for root/node value
- `defined(*subscripts)` for $DATA semantics (0, 1, 10, 11)
- `kill(*subscripts)` for KILL command
- `order(*subscripts)` for $ORDER traversal

## Analysis Fields

| Field | Purpose |
|-------|---------|
| `goto_stmt.goto_type` | Classification (GotoType enum) |
| `goto_stmt.postcondition` | Conditional GOTO expression |
| `goto_stmt.exits_loops` | List of FOR loops exited |
| `goto_stmt.is_cross_label` | True if target is different label |
| `goto_stmt.target_stmt_index` | Statement index for intra-label forward |
| `goto_stmt.is_restructurable` | True if GOTO can be restructured to if/else |
| `if_stmt.restructurable_goto` | Back-reference to restructurable GOTO inside IF |
| `for_stmt.has_internal_goto` | Has GOTO in body |
| `for_stmt.exit_points` | List of exiting GOTOs |
| `label.has_self_loop` | True if label has backward GOTO to itself |
| `routine.needs_trampoline` | True if any cross-label GOTOs exist |
| `routine.routine_state_vars` | Variables that need RoutineState fields |
| `routine.array_vars` | Variables accessed with subscripts (need MArray) |

## Code Generator Functions

| Function | Purpose |
|----------|---------|
| `_generate_goto()` | Main GOTO dispatch in statements.py |
| `_select_goto_strategy()` | Select strategy based on ASG flags |
| `_check_unsupported_gotos()` | Raise errors for UNRESOLVED/EXTERNAL |
| `_find_forward_goto_in_if()` | Return pre-computed restructurable GOTO from IF |
| `_restructure_forward_goto()` | Generate inverted if/else structure |
| `generate_scope_statements()` | Statement generation with GOTO restructuring |

## RoutineState Generator Functions (src/m2py/codegen/shared_state.py)

| Function | Purpose |
|----------|---------|
| `generate_routine_state_class()` | Build RoutineState dataclass from routine analysis |
| `generate_state_initialization()` | Create `state = RoutineState()` call |
| `generate_state_imports()` | Required imports for RoutineState |

## ASG Fields for Codegen

| Field | Purpose |
|-------|---------|
| `MRoutine.needs_loop_exit_exception` | True if routine needs `_LoopExit` class (set by `classify_gotos()`) |
| `MRoutine.needs_trampoline` | True if routine has cross-label GOTOs (set by `classify_gotos()`) |
