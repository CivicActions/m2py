# Quickstart: Computed Offsets & Line Dispatch

**Created**: 2026-01-12

## Overview

This feature implements computed offsets for GOTO/DO commands (`G LABEL+N`, `D SUB+expr`), enabling line-indexed execution in generated Python code.

## Prerequisites

- Spec 006 (Cross-Label Control Flow) implemented
- uv installed for package management
- Docker available for YDB validation

## Development Setup

```bash
# Clone and enter branch
git checkout 007-computed-offsets

# Sync environment
uv sync

# Run existing tests to verify baseline
uv run pytest tests/unit/codegen/s8_commands/test_s8_2_06_goto.py -v
```

## Key Files to Modify

| File | Purpose | Changes |
|------|---------|---------|
| `src/m2py/codegen/routine.py` | Routine generation | Add `_line_map` generation, update trampoline |
| `src/m2py/codegen/statements.py` | GOTO codegen | Detect offset, emit line-based dispatch |
| `src/m2py/codegen/line_dispatch.py` | NEW | Line map generation, offset evaluation helpers |

## Implementation Sequence

### Step 1: Line Map Generator (US4)

Create `line_dispatch.py` with:

```python
def generate_line_map(routine: MRoutine) -> Dict[int, Tuple[str, int]]:
    """Build source line → (label, offset) mapping."""
    ...

def generate_line_map_code(line_map: Dict[int, Tuple[str, int]], emitter: CodeEmitter) -> None:
    """Emit _line_map dict definition."""
    ...
```

Test: `TestLineMapGenerationCodegen` in test_s8_2_06_goto.py

### Step 2: Literal Offset GOTO (US1)

Modify `_generate_single_target_goto()` in statements.py:

```python
# Detect offset presence
if target.offset is not None:
    # Emit line-based dispatch
    label_line = target.target.line_number
    offset_expr = generate_expr(target.offset, ctx)
    ctx.emitter.line(f"return ({label_line} + int({offset_expr}), state)")
else:
    # Existing label-based dispatch
    ctx.emitter.line(f'return ("{target.name}", state)')
```

Test: `TestLiteralOffsetGoto` in test_s8_2_06_goto.py

### Step 3: Extended Trampoline (US4 cont.)

Modify `_generate_trampoline_code()` in routine.py:

```python
# Update dispatcher to handle int targets
ctx.emitter.line("while target is not None:")
with ctx.emitter.indented():
    ctx.emitter.line("if isinstance(target, int):")
    with ctx.emitter.indented():
        ctx.emitter.line("label, offset = _line_map[target]")
        ctx.emitter.line("func = _labels[label]")
        ctx.emitter.line("target, state = func(state, _start_offset=offset)")
    ctx.emitter.line("else:")
    with ctx.emitter.indented():
        ctx.emitter.line("func = _labels[target]")
        ctx.emitter.line("target, state = func(state)")
```

### Step 4: Label Functions with Offset Entry (US1/US2)

Modify `_generate_trampoline_label()` in routine.py:

```python
# Add _start_offset parameter
params_str = "state, _start_offset=0"

# Generate offset guards for statements
for i, stmt in enumerate(statements):
    ctx.emitter.line(f"if _start_offset <= {i}:")
    with ctx.emitter.indented():
        generate_statement(stmt, ctx)
```

### Step 5: Variable Offset (US2)

No additional changes - `generate_expr()` already handles variables.

Test: `TestVariableOffsetGoto` in test_s8_2_06_goto.py

### Step 6: Arithmetic Offset (US3)

No additional changes - `generate_expr()` already handles binary ops.

Test: `TestArithmeticOffsetGoto` in test_s8_2_06_goto.py

### Step 7: Error Handling (US5)

Add runtime check for invalid offsets:

```python
# In dispatcher
if target not in _line_map:
    next_line = _find_next_executable(target, _line_map)
    if next_line is None:
        raise ValueError(f"Entry point {label}+{offset} not valid")
    target = next_line
```

Test: `TestInvalidOffsetError` in test_s8_2_06_goto.py

## Validation

```bash
# Run unit tests
uv run pytest tests/unit/codegen/s8_commands/test_s8_2_06_goto.py -v

# Validate against YDB
uv run python utils/validate.py --code 'TEST S N=2 G STAR+N Q
STAR W "0"
 W "1"
 W "2"
 Q'

# Run V1GO2.m offset tests
uv run python utils/validate.py tests/functional/mugj/inref/V1GO2.m
```

## Success Criteria

- [ ] `G LABEL+N` (literal) produces correct output
- [ ] `G LABEL+VAR` (variable) evaluates at runtime
- [ ] `G LABEL+A-B` (arithmetic) evaluates correctly
- [ ] Invalid offset raises descriptive error
- [ ] Generated Python passes `ast.parse()`
- [ ] All V1GO2.m offset tests pass

## Out of Scope

- Cross-routine offsets (`G LABEL+N^ROUTINE`) → Spec 008
- Globals in offsets (`G LABEL+^VAR`) → Spec 009
- Functions in offsets (`G LABEL+$L(X)`) → Spec 010
- Postconditioned offsets (`G:cond LABEL+N`) → Spec 011
