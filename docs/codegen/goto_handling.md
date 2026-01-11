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
| `CROSS_LABEL` | To different label | Function call + return |
| `BACKWARD_JUMP` | To earlier code | Not yet supported |
| `EXTERNAL` | To other routine | Not yet supported |
| `UNRESOLVED` | Dynamic target | Not yet supported |

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
- `_is_restructurable_goto()` checks if GOTO is intra-label forward
- `_find_forward_goto_in_if()` detects restructurable GOTOs inside IF statements
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

## Not Yet Supported

The following GOTO patterns raise `NotImplementedError` or `UnsupportedFeatureError`:

| Pattern | Example | Reason | Spec |
|---------|---------|--------|------|
| Backward intra-label | `G LOOP` (where LOOP is earlier) | Creates implicit loops | 006 |
| External routine | `G LABEL^OTHER` | Requires module import handling | 009 |
| Multiple targets | `G A,B` | Sequential label execution | 006 |
| Indirect | `G @VAR` | Runtime dispatch needed | 007 |
| Argumentless | `G` | Returns to caller | 006 |

## Analysis Fields

| Field | Purpose |
|-------|---------|
| `goto_stmt.goto_type` | Classification (GotoType enum) |
| `goto_stmt.postcondition` | Conditional GOTO expression |
| `goto_stmt.exits_loops` | List of FOR loops exited |
| `goto_stmt.is_cross_label` | True if target is different label |
| `goto_stmt.target_stmt_index` | Statement index for intra-label forward |
| `for_stmt.has_internal_goto` | Has GOTO in body |
| `for_stmt.exit_points` | List of exiting GOTOs |

## Code Generator Functions

| Function | Purpose |
|----------|---------|
| `_generate_goto()` | Main GOTO dispatch in statements.py |
| `_is_restructurable_goto()` | Check if GOTO can become if/else |
| `_find_forward_goto_in_if()` | Find restructurable GOTO in IF |
| `_restructure_forward_goto()` | Generate inverted if/else structure |
| `generate_scope_statements()` | Statement generation with GOTO restructuring |
| `_for_needs_loop_exit_wrapper()` | Check if FOR needs try/except |

## ASG Fields for Codegen

| Field | Purpose |
|-------|---------|
| `MRoutine.needs_loop_exit_exception` | True if routine needs `_LoopExit` class (set by `classify_gotos()`) |
