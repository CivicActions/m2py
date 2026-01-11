# Quickstart: Spec 005 - Structured Control Flow Codegen

**Date**: 2025-01-21  
**Spec**: [spec.md](spec.md)

## Overview

This guide covers implementing structured control flow code generation for the MUMPS-to-Python transpiler. By the end of Spec 005, the system will generate Python code for:

- FOR loop variations (bounded, open-ended, argumentless, value-list)
- Intra-label GOTO **forward jumps only** (break, multi-loop exit, if/else restructuring)
- Context-aware QUIT (in FOR vs. in DO)
- By-reference parameter return tuples
- $TEST stack semantics for argumentless DO and extrinsic functions

**Out of scope** (deferred to later specs):
- Cross-label GOTO → Spec 006
- Backward intra-label GOTO → Spec 006
- REQUIRES_RUNTIME scope strategy → Spec 006/007
- Postcondition codegen → Spec 008

---

## Prerequisites

Before starting Spec 005:

1. **Spec 004 Complete**: Labels as functions, basic $TEST, `_rt` runtime
2. **Analysis Passes Run**: `analyze_for_loops()`, `classify_gotos()`, `analyze_variables()`
3. **Environment**: `uv` installed, `uv sync` completed

Verify prerequisites:
```bash
uv run pytest tests/unit/analysis/ -v
uv run pytest tests/unit/codegen/ -v
```

---

## Quick Test: Existing Infrastructure

### 1. Check FOR Analysis

```python
from m2py import MUMPSParser

source = """
LOOP F I=1:1:10 D
     . I I=5 Q
     . W I
     Q
"""

parser = MUMPSParser()
routine = parser.parse_string(source, "TEST")
parser.analyze_for_loops(routine)

for label in routine.labels:
    for stmt in label.body.walk_statements():
        if hasattr(stmt, 'loop_type'):
            print(f"Loop type: {stmt.loop_type}")
            print(f"Has internal QUIT: {stmt.has_internal_quit}")
```

### 2. Check GOTO Analysis

```python
source = """
LOOP F I=1:1:10 D
     . I ERR G DONE
     . D WORK
DONE W "Done"
     Q
"""

parser = MUMPSParser()
routine = parser.parse_string(source, "TEST")
parser.resolve_references(routine)
parser.classify_gotos(routine)

for label in routine.labels:
    for stmt in label.body.walk_statements():
        if hasattr(stmt, 'goto_type'):
            print(f"GOTO type: {stmt.goto_type}")
            print(f"Is cross-label: {stmt.is_cross_label}")
            print(f"Exits loops: {len(stmt.exits_loops)}")
```

---

## Implementation Roadmap

### Phase 1: FOR Loop Codegen Extensions

**Goal**: Handle all FOR loop types with proper break support.

**Files to modify**:
- `src/m2py/codegen/statements.py` - `_generate_for()`

**Key changes**:
1. Add `while` loop generation when `loop_var_modified_in_body=True`
2. Add `itertools.count` for `ForLoopType.OPEN_ENDED`
3. Add `while True` for `ForLoopType.ARGUMENTLESS`
4. Handle `has_internal_quit` with break-capable structure

**Test with**:
```bash
uv run pytest tests/unit/codegen/test_for_loops.py -v
```

### Phase 2: GOTO Patterns

**Goal**: Generate break, multi-loop exit, and forward restructuring patterns.

**MUMPS Semantic Note (MDC 3.6.5)**: GOTO terminates all FOR loops on the line containing the GOTO.
GOTO cannot create Python `continue` semantics. For skip-iteration patterns, use conditional execution
(`I cond <commands>`) or QUIT from DO blocks.

**Files to modify**:
- `src/m2py/codegen/statements.py` - `_generate_goto()` and new helper functions

**Key changes**:
1. Check `goto_type == LOOP_EXIT` → generate `break`
2. Check `goto_type == MULTI_LOOP_EXIT` → generate exception pattern
3. Handle `is_cross_label=False` forward jumps via `generate_scope_statements()`:
   - `_find_forward_goto_in_if()` detects restructurable GOTOs
   - `_restructure_forward_goto()` generates inverted if/else using `target_stmt_index`
   - `generate_scope_statements()` replaces direct statement loop in label generation

**MUMPS Offset Semantics**: `LABEL+n` targets line n from LABEL (e.g., TEST+4 from TEST at line 1 targets line 5).
The `classify_gotos()` analysis pass computes `target_stmt_index` by mapping line numbers to statement indices.

**Test with**:
```bash
uv run pytest tests/unit/codegen/s8_commands/test_s8_2_06_goto.py -v
```

### Phase 3: QUIT Context

**Goal**: Generate break vs. return based on context.

**Files to modify**:
- `src/m2py/codegen/statements.py` - `_generate_quit()`

**Key changes**:
1. Check `exits_for` → generate `break`
2. Check `exits_do_block` → generate `return`
3. Check `return_value` → generate `return expr`
4. Handle postconditioned QUIT

**Test with**:
```bash
uv run pytest tests/unit/codegen/test_quit_context.py -v
```

### Phase 4: Function Signatures

**Goal**: Generate proper function signatures based on ScopeStrategy.

**Files to modify**:
- `src/m2py/codegen/routine.py` - `_generate_label()`

**Key changes**:
1. Add formal parameters to function def
2. Generate return tuples for `FUNCTION_WITH_OUTPUTS`
3. Raise error for `REQUIRES_RUNTIME`

**Test with**:
```bash
uv run pytest tests/unit/codegen/test_signatures.py -v
```

### Phase 5: By-Reference Returns

**Goal**: Generate return tuples and call-site destructuring.

**Files to modify**:
- `src/m2py/codegen/statements.py` - `_generate_do()`
- `src/m2py/codegen/expressions.py` - extrinsic calls

**Key changes**:
1. Check callee's `byref_outputs`
2. Generate destructuring at call site
3. Include all modified by-ref params in return

**Test with**:
```bash
uv run pytest tests/unit/codegen/test_byref.py -v
```

### Phase 6: $TEST Stack

**Goal**: Save/restore $TEST around extrinsic function calls.

**Files to modify**:
- `src/m2py/codegen/expressions.py` - extrinsic function generation

**Key changes**:
1. Generate `_saved_test = _test` before call
2. Generate call
3. Generate `_test = _saved_test` after call

**Test with**:
```bash
uv run pytest tests/unit/codegen/test_test_stack.py -v
```

---

## Running Full Test Suite

```bash
# Unit tests
uv run pytest tests/unit/ -v

# Functional tests (compare to YDB)
uv run pytest tests/functional/ -v

# Coverage report
uv run pytest --cov=src/m2py/codegen --cov-report=html
```

---

## Common Patterns Reference

### FOR Loop Decision Tree

```python
def decide_for_pattern(stmt: MForStatement) -> str:
    if stmt.loop_type == ForLoopType.ARGUMENTLESS:
        return "while_true"
    elif stmt.loop_var_modified_in_body:
        return "while_bounded"
    elif stmt.loop_type == ForLoopType.OPEN_ENDED:
        return "itertools_count"
    elif stmt.loop_type == ForLoopType.STRING_LIST:
        return "for_in_list"
    else:
        return "for_range"
```

### GOTO Decision Tree

```python
def decide_goto_pattern(stmt: MGotoStatement) -> str:
    # First check for backward jumps - always unsupported in Spec 005
    if stmt.goto_type == GotoType.BACKWARD_JUMP:
        # Both intra-label (G LABEL without offset) and cross-label backward
        # Intra-label backward creates implicit loops, cross-label needs state machine
        return "unsupported"  # Spec 006
    
    if stmt.is_cross_label:
        if stmt.goto_type == GotoType.LOOP_EXIT:
            return "break_and_call"  # break + function call
        return "unsupported"  # Spec 006 (cross-label forward)
    
    # Intra-label patterns (is_cross_label=False)
    # Note: GOTO cannot create 'continue' - use conditional execution instead (MDC 3.6.5)
    if stmt.goto_type == GotoType.LOOP_EXIT:
        return "break"
    elif stmt.goto_type == GotoType.MULTI_LOOP_EXIT:
        return "exception"
    elif stmt.goto_type == GotoType.FORWARD_JUMP:
        return "restructure"  # if/else
    else:
        return "unsupported"
```

---

## Debugging Tips

### 1. Dump ASG with Analysis

```bash
uv run python utils/validate_asg.py --compact path/to/file.m
```

### 2. Check Generated Code

```python
from m2py.codegen.routine import RoutineGenerator

gen = RoutineGenerator(routine)
code = gen.generate()
print(code)

# Validate syntax
import ast
ast.parse(code)  # Should not raise
```

### 3. Compare to YDB

```python
from tests.conftest import execute_mumps

result = execute_mumps(source)
print(f"Expected: {result}")
```

---

## Success Checklist

- [ ] FOR bounded loops generate `for i in range(...)`
- [ ] FOR open-ended loops generate `while` or `itertools.count`
- [ ] FOR argumentless loops generate `while True`
- [ ] FOR loops with QUIT generate `break`
- [ ] GOTO loop-exit generates `break`
- [ ] GOTO multi-loop-exit generates exception pattern
- [ ] GOTO forward jump (intra-label) generates if/else restructuring
- [ ] QUIT in FOR generates `break`
- [ ] QUIT in DO generates `return`
- [ ] QUIT with value generates `return expr`
- [ ] Function signatures include formal parameters
- [ ] By-ref outputs return as tuple
- [ ] Call sites destructure by-ref returns
- [ ] Extrinsic calls save/restore $TEST
- [ ] All generated code passes `ast.parse()`
- [ ] 85%+ code coverage on codegen additions
