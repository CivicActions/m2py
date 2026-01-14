# Code Generation Guide

This section documents strategies for generating Python code from ASG structures.

## Overview

### Philosophy

M2PY aims for **semantic-preserving translation**, not line-by-line conversion:

- Leverage ASG analysis to generate clean Python
- Use structured constructs where possible
- Fall back to runtime support only when necessary

### Public API

The `generate_python()` function is the primary entry point for code generation:

```python
from m2py.codegen import generate_python

# Generate Python from MUMPS source
python_code = generate_python(
    'TEST S X=1 W X Q',
    routine_name="example",
    validate=True  # Runs ast.parse() to verify output
)
print(python_code)
```

Output:
```python
from m2py.codegen.helpers import m_num, m_truth, m_compare
from m2py.runtime import MUMPSRuntime

_source_lines = ["TEST S X=1 W X Q"]
_routine_name = "example"
_label_lines = {"TEST": 0}

def TEST(_rt, _scope=None, **_kwargs):
    _scope = _scope if _scope is not None else {}
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    _scope['X'] = 1
    _rt.write(str(_scope.get('X', '')))

if __name__ == "__main__":
    _rt = MUMPSRuntime()
    _scope = {}
    TEST(_rt, _scope)
```

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
