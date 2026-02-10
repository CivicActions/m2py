# Research: Codegen Refactoring (Phase 2)

**Date**: 2026-02-10  
**Branch**: `020-codegen-refactoring`

## Phase 1 Deliverable Status

All Phase 1 deliverables are complete and merged to `main`:

| Deliverable | Location | Status |
|---|---|---|
| `core/values.py` | `src/m2py/core/values.py` | ✅ Merged. Exports: `mumps_canonical_str`, `m_str`, `m_num`, `m_truth`, `m_compare`, `m_add`, `m_sub`, `m_mul`, `_decimal_binop` |
| `core/parsing.py` | `src/m2py/core/parsing.py` | ✅ Merged. Exports: `parse_subscripted_name`, `canonicalize_subscript` |
| `core/tokenizer.py` | `src/m2py/core/tokenizer.py` | ✅ Merged. Exports: `split_at_toplevel` |
| `asg/traversal.py` | `src/m2py/asg/elements.py` (method) | ✅ Merged. Implemented as `MScope.walk_statements()` instead of standalone module |
| `codegen/exceptions.py` | `src/m2py/codegen/exceptions.py` | ✅ Merged. Exports: `CodegenError`, `UnsupportedFeatureError` |

**Key difference from plan**: The ASG traversal was implemented as a method on `MScope` rather than a standalone `asg/traversal.py` module. This is fine — the spec's FR-042 dependency is satisfied.

## Subscript Tuple Pattern (S-02) — 99 Sites

### Pattern Variations Found

The inline pattern has **4 variations**, not 1 uniform pattern:

1. **Standard form** (most common, ~70 sites):
   ```python
   sub_exprs = [generate_expr(sub, ctx) for sub in var.subscripts]
   if len(sub_exprs) == 1:
       subscripts_tuple = f"({sub_exprs[0]},)"
   else:
       subscripts_tuple = f"({', '.join(sub_exprs)},)"
   ```

2. **Pre-evaluated subscripts** (~15 sites): Same but uses pre-generated string list.

3. **Naked global subscripts** (~8 sites): Uses `_rt.get_last_global_ref()` prefix plus additional subscripts.

4. **Empty subscripts handling** (~6 sites): Generates `"()"` when no subscripts.

### Design Decision

- **Chosen**: `gen_subscripts_tuple(subscripts, ctx) -> str` — a single helper that handles all variations.
- **Rationale**: All 4 variations share the same core logic (join exprs with commas, add trailing comma). The naked-global case can pass its pre-built expr list.
- **Alternative rejected**: Making it part of the expression generator — too tightly coupled to expression context.

## LHS $PIECE/$EXTRACT Deduplication (S-05)

### Structure Analysis

Both functions (`_generate_lhs_piece` at L1200, `_generate_lhs_extract` at L1392) follow identical 4-step structure:

1. **Extract target** from `assignment.target` (assert MIntrinsicFunction)
2. **Build getter/setter** with 4-way type dispatch: GlobalVariable → NakedGlobal → MIndirection → MVariable
3. **3-way strategy dispatch** within MVariable branch
4. **Emit** `m_set_piece(getter, setter, ...)` or `m_set_extract(getter, setter, ...)`

The MIndirection block (~50 lines) is byte-identical between the two functions.

### Design Decision

- **Chosen**: `_build_lhs_getter_setter(target, ctx) -> tuple[str, str]` extracts steps 2-3.
- **Rationale**: Eliminates ~200 lines of duplication. Each caller retains only step 1 (assertion) and step 4 (specific runtime call).

## Scope↔State Sync (S-04) — 22 Sites

### Pattern Classification

Two distinct sync directions found:

1. **State→Scope** (9 in statements.py, 3 in routine.py = 12 sites):
   ```python
   _scope.update({k: v for k, v in state._locals.items()})
   ```

2. **Scope→State** (7 in statements.py, 3 in routine.py = 10 sites):
   ```python
   for _k, _v in _scope.items():
       if isinstance(_v, MArray):
           state._locals[_k] = _v
       else:
           _m = MArray(); _m._value = str(_v); state._locals[_k] = _m
   ```

### Variations Observed

- Some sites add a conditional guard (`if ctx.uses_dynamic_locals:`)
- Some sites use `state._locals` while others use `__dataclass_fields__` iteration
- The routine.py copies have slightly more context (error handling wrapping)

### Design Decision

- **Chosen**: Two helpers `emit_state_to_scope_sync(ctx)` and `emit_scope_to_state_sync(ctx)` that conditionally emit based on `ctx.uses_dynamic_locals`.
- **Rationale**: Both helpers check context flags internally, making call sites simple 1-liners.

## Strategy Dispatch (S-01) — 69 Sites

### Pattern Classification

Three dispatch modes found:

1. **Read expression** (var access for reading): Returns base expression string
2. **Write statement** (var access for writing): Emits assignment statement
3. **Base expression** (MArray/dict access): Returns the base object reference

All share the same 3-way condition:
```
TRAMPOLINE + dynamic_locals → state._locals.*
TRAMPOLINE + state_vars     → state.{name}
SIMPLE_FUNCTIONS            → _scope.*
```

### File Distribution

| File | Count | Note |
|---|---|---|
| `codegen/statements.py` | 42 | Highest concentration |
| `codegen/expressions.py` | 20 | Read-only patterns |
| `codegen/indirection.py` | 7 | Mixed read/write |

### Design Decision

- **Chosen**: New `codegen/var_access.py` with `var_read_expr()`, `var_write_stmt()`, `var_base_expr()`.
- **Rationale**: Centralizes the 3-way dispatch. Adding a 4th strategy in the future requires exactly 1 code change.
- **Risk**: Some call sites have slight variations (e.g., `setdefault` vs `get`, MArray() defaults). Need to parameterize these.

## ZWRITE Range Correctness (C-09)

### Current Bug

At `statements.py` L6540-6575 (`_generate_zwrite`), when encountering `MZWriteSubscriptRange`:
```python
elif isinstance(s, MZWriteSubscriptRange):
    # TODO: Range support would need runtime filtering
    # For now treat like * (show all)
    break
```

The range's `start` and `end` expressions are completely ignored.

### YDB-Verified Behavior

Testing confirmed MUMPS collation-based filtering:
- `A(1:10)` → includes 1, 1.5, 2, 10 (all numerics in collation range)
- `A("A":"B")` → includes "A", "AA", "B" (strings in collation range)
- `A(2:)` → includes 2, 10, "A", "AA", "B" (strings sort after all numerics)
- `A(:2)` → includes -1, 0, 1, 1.5, 2 (only numerics up to 2, NOT strings)

### Design Decision

- **Chosen**: Use existing `m_sorts_after` / `_mumps_collation_key` from `runtime/helpers.py`.
- **Rationale**: These functions already implement correct MUMPS collation. Simple Python comparison operators would fail for mixed-type subscripts.
- **Implementation approach**: 
  1. Codegen emits range bounds as arguments to `_rt.zwrite_local()` / `_rt.zwrite_global()`
  2. Runtime filters children using `_mumps_collation_key` comparisons
  3. Both local and global ZWRITE paths share a single implementation

## XECUTE Coupling (S-13)

### Current Problem

`_generate_xecute()` at L5814 makes 3 backward imports:
- `from m2py.parser.line_parser import parse_commands_from_line` (L5839)
- `from m2py.parser.parser import _structure_commands_with_bodies` (L5872)
- `from m2py.analysis.semantic_analyzer import analyze_command` (L5838)

Then inlines the full parse→analyze→structure pipeline (~30 lines).

### Design Decision

- **Chosen**: `compile_mumps_line(code_str, context)` in `parser/` package.
- **Location**: `parser/__init__.py` or `parser/compiler.py` (clarified: `parser/` package).
- **Rationale**: Keeps the full pipeline alongside its components. Codegen calls one function instead of 3 imports + inline pipeline.

## Comment Extraction (S-19)

### Current Implementation

`_emit_source_comment` at L117-147 re-scans `ctx.routine.source_lines[line_idx]` for unquoted semicolons. The `_extract_comment` helper at L150 does character-by-character scanning.

### Design Decision

- **Chosen**: Add `comment: Optional[str]` to `MStatement` base class, populated during parsing.
- **Parser change**: In `parser/textx_classes.py`, extract inline comments during line parsing (after the command, scan for unquoted `;`).
- **Codegen change**: `_emit_source_comment` reads `stmt.comment` instead of re-scanning source.
- **Risk**: Low — the comment extraction logic is well-tested and straightforward to move.

## By-Reference Call Unification (C-07)

### Current Divergence

| Strategy | Approach | Correctness |
|---|---|---|
| SIMPLE_FUNCTIONS | MArray aliasing via `_scope.setdefault(var, MArray())` | ✅ Correct — true pass-by-reference |
| TRAMPOLINE | Value-result via return tuple destructuring | ❌ Incorrect — loses mutations on error, no descendant aliasing |

### MUMPS Standard Requirement

Section 8.1.7: DATA-CELL pointer aliasing. Callee and caller share the same data cell. SET/KILL of descendants visible to both. `$DATA` reflects full variable tree.

### Design Decision

- **Chosen**: Force `uses_dynamic_locals=True` when by-ref formals are present (full unification).
- **Mechanism**: Semantic analyzer detects by-ref formal parameters → sets `uses_dynamic_locals=True` → TRAMPOLINE uses `state._locals` dict → MArray references naturally alias.
- **Impact**: Changes generated code structure for TRAMPOLINE routines with by-ref formals. Runtime behavior becomes correct.
- **Risk**: Highest-risk change. Must be last in Track A sequence. Comprehensive regression testing required.

## Indirection Template Extraction (S-03)

### Function Count Correction

Research found **16 public indirection functions** (not 11 as originally estimated):

| # | Function | Line | Pattern |
|---|---|---|---|
| 1 | `generate_argument_indirection` | L213 | Template |
| 2 | `generate_name_indirection` | L338 | Template |
| 3 | `generate_indirection_marray_expr` | L456 | Template |
| 4 | `generate_subscript_indirection` | L554 | Template |
| 5 | `generate_name_indirection_write` | L663 | Template |
| 6 | `generate_name_indirection_kill` | L794 | Template |
| 7 | `generate_name_indirection_for` | L867 | Template |
| 8 | `generate_merge_indirection_name` | L941 | Template |
| 9 | `generate_data_indirection_name` | L1014 | Template |
| 10 | `generate_get_indirection_name` | L1107 | Template |
| 11 | `generate_name_function_indirection` | L1228 | Template |
| 12 | `generate_query_indirection_name` | L1335 | Template |
| 13 | `generate_indirect_do` | L1402 | Complex (DO-specific) |
| 14 | `generate_indirect_goto` | L1776 | Complex (GOTO-specific) |
| 15 | `generate_set_argument_indirection` | L1962 | Template |
| 16 | `generate_increment_indirection` | L2006 | Template |

Plus 5 private helpers: `_get_scope_expr`, `_generate_do_goto_indirection_string`, `_count_indirection_levels`, `_count_indirection_levels_with_subscripts`, `_generate_inner_name_expr`.

### Design Decision

- **Templatizable**: 14 of 16 follow the standard pattern (count levels → build scope → type-switch → build call).
- **Non-templatizable**: `generate_indirect_do` (L1402, ~374 lines) and `generate_indirect_goto` (L1776, ~186 lines) have complex DO/GOTO-specific logic that doesn't fit the template pattern. These should be simplified but not templatized.
- **Updated spec impact**: The "11 functions" estimate in the spec should be treated as "~14 templatizable functions" — the 40% line reduction target is still achievable.

## offset_wrapper Consolidation (S-12)

### Two Closures Analyzed

| Closure | Location | Lines | Context |
|---|---|---|---|
| 1 | `runtime/__init__.py` L1056-1167 | ~111 | `resolve_goto_target()` — line offset handling |
| 2 | `runtime/__init__.py` L1413-1499 | ~86 | `resolve_entry_ref()` — entry reference handling |

### Shared Logic (~80%)

Both implement: scope init → state creation → trampoline loop → GotoExternal handling → state→scope sync.

### Differences (~20%)

- Closure 1 has a `handle_goto_external` nested helper
- Closure 1 uses `__dataclass_fields__` for state sync; Closure 2 uses `dir(state)`
- Error handling approach differs slightly

### Design Decision

- **Chosen**: `_create_offset_entry_wrapper(base_fn, offset, strategy, ...)` factory function.
- **Parameterize**: The goto_external handling and state sync mechanism differences.

## ASG Field Cleanup (S-16)

### Fields to Remove

| Class | Remove | Keep | Consumers to Update |
|---|---|---|---|
| `MIfStatement` | `condition: Optional[MExpr]` | `conditions: List[MExpr]` | Codegen IF handler, analysis |
| `MHangStatement` | `duration: Optional[MExpr]` | `durations: List[MExpr]` | Codegen HANG handler |
| `MXecuteStatement` | `code_expressions: List[MExpr]` | `arguments: List[MXecuteArg]` | Codegen XECUTE handler |

### New Dataclass

`MLockTarget` to replace `dict` in `MLockStatement.targets: List[Any]`:

Current dict keys found: `lockop`, `postcondition`, `indirection`, `indirection_levels`, `is_indirect`, `name`, `subscripts`, `is_global`, `timeout`.

### Design Decision

- **Chosen**: Create `MLockTarget` dataclass with typed fields matching the dict keys.
- **Consumer updates**: `semantic_analyzer.py` (builder), `codegen/statements.py` (reader), attribute access replaces dict `.get()`.
- **ZWithdraw**: `_analyze_ZWithdrawCommand` → delegates to `_analyze_ZKillCommand`.

## GeneratorContext Structure

`GeneratorContext` is defined in `codegen/routine.py` L32-91 as a `@dataclass`. Key fields relevant to Phase 2:

- `strategy: GotoStrategy` — used by S-01 dispatch
- `uses_dynamic_locals: bool` — used by S-01 and C-07
- `state_vars: set[str]` — used by S-01 dispatch
- `emitter: CodeEmitter` — used by S-04, S-14 helpers
- `routine: MRoutine` — used by S-19 comment extraction

All new helper functions will accept `ctx: GeneratorContext` as their primary parameter.
