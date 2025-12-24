# Code Generation Guide

This section documents strategies for generating Python code from ASG structures.

## Overview

### Philosophy

M2PY aims for **semantic-preserving translation**, not line-by-line conversion:

- Leverage ASG analysis to generate clean Python
- Use structured constructs where possible
- Fall back to runtime support only when necessary

### Using Analysis Flags

The analysis pipeline populates fields that guide code generation:

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")
parser.resolve_references(routine)  # MCall.target, back-refs
parser.classify_gotos(routine)      # goto_type, exits_loops
parser.analyze_for_loops(routine)   # loop analysis flags
parser.analyze_variables(routine)   # input/output variables
```

### Decision Flow

```
Parse MUMPS → Build ASG → Run Analysis → Generate Python
                                ↓
                    Check analysis flags
                                ↓
            ┌───────────────────┼───────────────────┐
            ↓                   ↓                   ↓
    Simple patterns    Structured GOTO    Unstructured patterns
            ↓                   ↓                   ↓
    Direct Python       break/continue      State machine or
    translation         with flags          runtime dispatch
```

## Guide Topics

- [FOR Loops](for_loops.md) - Iteration translation strategies
- [GOTO Handling](goto_handling.md) - Control flow restructuring
- [Variable Scoping](variable_scoping.md) - Function signatures and scope
- [Operators](operators.md) - MUMPS operators to Python
- [Functions](functions.md) - Intrinsic function translation
- [Runtime Requirements](runtime_requirements.md) - When runtime support is needed
- [MUMPS Gotchas](mumps_gotchas.md) - Edge cases and semantic quirks

## Quick Reference

### FOR Loop Strategy

| ForLoopType | has_internal_quit | loop_var_modified | Strategy |
|-------------|-------------------|-------------------|----------|
| BOUNDED | No | No | `for i in range()` |
| BOUNDED | Yes | No | `for` with `break` |
| BOUNDED | * | Yes | `while` loop |
| OPEN_ENDED | * | * | `while True:` |
| ARGUMENTLESS | * | * | `while True:` |

### GOTO Strategy

| GotoType | Strategy |
|----------|----------|
| FORWARD_JUMP | If/elif restructuring |
| BACKWARD_JUMP | Loop construct |
| LOOP_EXIT | `break` |
| MULTI_LOOP_EXIT | Exception pattern |
| EXTERNAL | Cross-module call |

### Function Signature

| ScopeStrategy | Python Pattern |
|---------------|----------------|
| PURE_FUNCTION | `def f(args) -> result` |
| FUNCTION_WITH_OUTPUTS | `def f(args) -> Tuple[result, ...]` |
| SUBROUTINE | `def f(args) -> None` |
| REQUIRES_RUNTIME | Runtime scope access |

## Existing Notes

For additional detail, see:
- [`specs/001-textx-semantic-graph/asg-codegen-notes.md`](../../specs/001-textx-semantic-graph/asg-codegen-notes.md)
