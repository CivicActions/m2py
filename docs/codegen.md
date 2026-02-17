# Code Generation

The codegen module (`src/m2py/codegen/`) translates an enriched ASG into executable Python. Strategy selection and all analysis are complete before code generation begins.

## Public API

```python
from m2py.codegen import generate_python

python_code = generate_python(source, routine_name="MYROUTINE")
```

`generate_python()` handles the full pipeline: parse → six analysis passes → strategy selection → code generation → `ast.parse()` validation. It is the primary entry point for transpilation.

## Strategy Selection

Two code generation strategies are automatically selected based on ASG analysis flags:

| Strategy | When Selected | Pattern |
|----------|---------------|---------|
| **SIMPLE_FUNCTIONS** | No cross-label GOTOs, no computed offsets | Labels as plain Python functions; variables in `_scope` dict |
| **TRAMPOLINE** | `needs_trampoline` or `has_offset_calls` | Labels return `(next_label, state)` tuples; `while` loop dispatches; `RoutineState` carries variables |

The trampoline pattern was selected over a state machine design because each label remains an independent, testable function. The dispatch loop is a simple `while target is not None:` with dictionary lookup.

## Generated Code Structure

A generated Python module contains (in order):

1. **Imports** — runtime helpers (`m_str`, `m_num`, `m_truth`, `m_compare`), `MUMPSRuntime`, `MArray`, plus strategy-specific imports (`dataclass`, `GotoExternal` for trampoline)
2. **Module-level state** — `_test = False` ($TEST), `_source_lines` (for $TEXT), `_routine_name`, `_label_lines`
3. **RoutineState dataclass** (trampoline only) — carries variables across label boundaries
4. **`_LoopExit` exception** (only if multi-loop exit GOTOs exist) — for cross-FOR-loop GOTO exits
5. **`_XecuteExit` exception** — for XECUTE scope exit
6. **`_call_extrinsic()` helper** — saves/restores `$TEST`, manages by-ref parameter unpacking, pushes/pops stack frames for `$$FUNC` calls
7. **Label functions** — one per label, with signatures derived from variable analysis
8. **`_line_map`** (if offset calls exist) — maps source line numbers to `(label_name, offset)` tuples
9. **Trampoline dispatcher** (trampoline only) — `while` loop calling label functions and handling `GotoExternal`
10. **Entry point** — `_entry_function` variable and `if __name__ == "__main__":` block

## Variable Access Modes

Three variable access patterns are used depending on strategy and routine complexity:

| Mode | When | Read | Write |
|------|------|------|-------|
| **`_scope` dict** | SIMPLE_FUNCTIONS | `_scope.get('X')` | `_scope['X'] = val` |
| **Static state fields** | TRAMPOLINE, no dynamic features | `state.X` | `state.X = val` |
| **Dynamic `_locals` dict** | TRAMPOLINE + argumentless KILL/NEW, exclusive KILL/NEW, name indirection, by-ref params, external GOTOs | `state._locals.get('X')` | `state._locals['X'] = val` |

The `routine_uses_dynamic_locals()` function in `shared_state.py` checks eight flags on `MRoutine` to determine whether static fields or a dynamic dict is needed. Dynamic mode is required when the set of live variables can change at runtime (e.g., argumentless KILL erases all locals).

For subscripted variables (MUMPS arrays), codegen uses `MArray` instances: `_scope.setdefault('X', MArray())` for writes, `_scope.get('X', MArray())` for reads.

## Key Patterns

### Value Coercion

MUMPS has no type system — all values are strings with implicit numeric coercion. Generated code uses helper functions from `core/values.py` (re-exported via `codegen/helpers.py`):

- `m_num(x)` — MUMPS numeric interpretation (left-to-right parse, sign composition)
- `m_str(x)` — canonical string form (no scientific notation, no leading zero for |x|<1)
- `m_truth(x)` — truth evaluation (0 = false, nonzero = true)
- `m_compare(left, op, right)` — comparison with appropriate coercion per operator

### $TEST Stacking

`$TEST` is a process-level flag set by IF and timeout operations. Argumentless DO blocks save and restore `$TEST` on entry/exit (stack semantics). XECUTE does NOT stack `$TEST`. Extrinsic function calls (`$$FUNC`) save/restore via `_call_extrinsic()`.

### By-Reference Parameters

MUMPS pass-by-reference uses a return-tuple pattern: the callee function returns modified variables alongside any return value, and the caller unpacks them back into scope.

### FOR Loop Translation

FOR loops map to Python `for` or `while` depending on classification:
- BOUNDED → `for` with computed range
- OPEN_ENDED → `while` loop
- STRING_LIST → `for` over a tuple of values
- ARGUMENTLESS → `while True`
- Loop variable modification in body triggers OPEN_ENDED → `while` conversion

### GOTO Restructuring

Forward intra-label GOTOs are restructured into `if/else` chains during code generation. Cross-label GOTOs use the trampoline. Multi-loop-exit GOTOs use `_LoopExit` exceptions caught at the outermost loop boundary.

### Cross-Routine GOTOs

External GOTOs (`G LABEL^ROUTINE`) raise `GotoExternal` exceptions. The trampoline dispatcher catches these, syncs state back to `_scope`, imports the target module, and continues execution via `run_with_goto_support()`.

## Indirection and XECUTE

Indirection (`@` expressions) and XECUTE require runtime support because their targets are determined dynamically.

- **Name indirection** (`@VAR`): generates calls to `_rt.set_indirected()`, `_rt.get_indirected()`, etc.
- **Argument indirection** (`D @CMD`): evaluates the expression and dispatches dynamically
- **XECUTE** (`X "SET X=1"`): calls `_rt.execute_mumps(code, scope)` which uses `compile_mumps_line()` from `parser/compiler.py` to transpile MUMPS to Python at runtime

The `IndirectionContext` enum (NAME vs ARGUMENT) in `core/indirection.py` is critical: `I @A` where `A="1=0"` must evaluate the string as a MUMPS expression (ARGUMENT context), not treat it as a variable name (NAME context).

## Computed Offsets

`DO LABEL+N` and `GOTO LABEL+N` use the `_line_map` dictionary to resolve line offsets. The `_start_offset` parameter on label functions guards which statements to execute, implementing "start at line N" semantics via `if _start_offset <= offset:` guards.

## File Map

| File | Lines | Responsibility |
|------|-------|----------------|
| `__init__.py` | ~200 | Public API, strategy selection, analysis orchestration |
| `routine.py` | ~1200 | Module structure, imports, trampoline dispatcher |
| `statements.py` | ~6800 | All statement type handlers |
| `expressions.py` | ~2600 | All expression type handlers |
| `var_access.py` | ~120 | 3-way variable read/write dispatch |
| `shared_state.py` | ~200 | RoutineState dataclass generation |
| `indirection.py` | ~1170 | @ expressions and XECUTE codegen |
| `line_dispatch.py` | ~100 | Line map for computed offsets |
| `emitter.py` | ~100 | Indent-aware code builder |
| `helpers.py` | ~80 | Re-exports value helpers for generated code imports |
| `names.py` | ~10 | Re-exports NameTranslator from core |
| `enums.py` | ~20 | GotoStrategy enum |
| `exceptions.py` | ~20 | CodegenError, UnsupportedFeatureError |
