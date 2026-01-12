# Quickstart: Cross-Label Control Flow

**Spec**: 006-cross-label-control-flow  
**Date**: 2026-01-11

## Overview

This guide helps developers work with cross-label GOTO code generation in m2py. After Spec 006, the transpiler handles GOTOs that cross label boundaries correctly.

## Prerequisites

- Spec 005 complete (labels-as-functions, intra-label GOTO, loop exits)
- Python 3.10+ with uv package manager
- Docker with YDB image for validation

## Quick Validation

```bash
# Test simple cross-label GOTO
uv run python utils/validate.py --code 'TEST S X=1 G NEXT Q
NEXT W X Q'

# Test backward cross-label GOTO (implicit loop)
uv run python utils/validate.py --code 'TEST S X=0
LOOP S X=X+1 W X I X<5 G LOOP Q'

# Test variable visibility across labels
uv run python utils/validate.py --code 'TEST S A=10,B=20 G SUM Q
SUM W A+B Q'
```

## Generated Patterns

### 1. Simple Forward Cross-Label GOTO

MUMPS:
```mumps
TEST S X=1 G NEXT S X=99 Q
NEXT W X Q
```

Generated Python (labels-as-functions):
```python
def TEST():
    global _test
    X = 1
    return ("NEXT", {"X": X})  # Return next label + state
    X = 99  # Unreachable
    return (None, {})

def NEXT(state):
    global _test
    X = state.get("X")
    _rt.write(str(X))
    return (None, {})

# Trampoline dispatcher
def _run():
    state = {}
    label = "TEST"
    while label is not None:
        label, state = _labels[label](state)
```

### 2. Backward Cross-Label GOTO (Loop)

MUMPS:
```mumps
TEST S X=0
LOOP S X=X+1 W X I X<5 G LOOP Q
```

Generated Python:
```python
def TEST():
    X = 0
    return ("LOOP", {"X": X})

def LOOP(state):
    X = state.get("X", 0)
    X = X + 1
    _rt.write(str(X))
    if m_truth(m_compare(X, "<", 5)):
        return ("LOOP", {"X": X})  # Back to LOOP
    return (None, {})
```

### 3. State Machine (DEFERRED)

> **Note**: State machine pattern was evaluated in research (R3) but found unnecessary. Trampoline handles all known patterns including cycles (47.5% of VistA routines). State machine is deferred to future specs if truly irreducible patterns are discovered.

## Strategy Selection

The transpiler automatically selects the appropriate pattern:

| Condition | Strategy |
|-----------|----------|
| `needs_trampoline=True` | Trampoline pattern with RoutineState |
| `needs_trampoline=False` | Simple labels-as-functions |

> **Note**: `has_unstructured_goto` is reserved for future state machine support if truly irreducible patterns are discovered.

Check which strategy a routine uses:
```bash
uv run python utils/validate.py --debug --code 'YOUR_CODE_HERE'
# Look for "has_unstructured_goto" and "needs_trampoline" in AST output
```

## Common Patterns

### Error Handling with Cross-Label GOTO

```mumps
TEST S ERR=0 D PROCESS I ERR G ERROR W "OK" Q
PROCESS ; do work
 I X<0 S ERR=1
 Q
ERROR W "Error!" Q
```

### Loop with Break to Label

```mumps
TEST F I=1:1:100 D CHECK I ERR G DONE W I
DONE W "End" Q
CHECK S ERR=0 I I>10 S ERR=1 Q
```

## Debugging

### Inspect Generated Code

```bash
# Show full generated Python
uv run python utils/validate.py --debug --code 'TEST G A Q
A W "A" Q'
```

### Check ASG Fields

```python
# In Python
from m2py import parse, analyze

routine = parse(source)
analyze(routine)

# Check cross-label flags
for label in routine.labels:
    for stmt in label.body.walk_statements():
        if isinstance(stmt, MGotoStatement):
            print(f"GOTO to {stmt.targets[0].name}")
            print(f"  is_cross_label: {stmt.is_cross_label}")
            print(f"  goto_type: {stmt.goto_type}")

# Check strategy selection
print(f"has_unstructured_goto: {routine.has_unstructured_goto}")
print(f"needs_trampoline: {routine.needs_trampoline}")
```

## Limitations (Spec 006)

The following are NOT supported in Spec 006:

- Computed offsets: `G LABEL+expr` → Spec 008
- External GOTO: `G LABEL^ROUTINE` → Spec 009
- Indirect GOTO: `G @VAR` → Spec 007
- Argumentless GOTO: `G` alone → Invalid in YDB

## Testing Your Changes

```bash
# Run unit tests
uv run pytest tests/unit/codegen/test_cross_label.py -v

# Run integration tests
uv run pytest tests/integration/test_v1go1.py -v

# Run all tests with coverage
uv run pytest --cov=src/m2py/codegen --cov-report=term-missing
```

## Further Reading

- [spec.md](spec.md) - Full specification
- [plan.md](plan.md) - Implementation plan
- [research.md](research.md) - Spike results and decisions
- [data-model.md](data-model.md) - ASG additions
