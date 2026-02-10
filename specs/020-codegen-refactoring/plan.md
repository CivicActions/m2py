# Implementation Plan: Codegen Refactoring (Phase 2)

**Branch**: `020-codegen-refactoring` | **Date**: 2026-02-10 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/020-codegen-refactoring/spec.md`

## Summary

Phase 2 restructures the three largest codegen files (`statements.py` 6,775L, `indirection.py` 2,092L, `expressions.py` 2,586L) and the runtime (`__init__.py` 6,168L) by extracting duplicated patterns into shared helpers, fixing two correctness bugs (ZWRITE range filtering C-09, by-ref call semantics C-07), and cleaning up deprecated ASG fields.

The work is organized into 3 parallel tracks:
- **Track A** (critical path, 14-20d): 9 sequential items all modifying `codegen/statements.py`
- **Track B** (parallel, 2-3d): Indirection template extraction in `codegen/indirection.py`
- **Track C** (parallel, 2-3d): Runtime offset_wrapper consolidation + ASG field cleanup

All Phase 1 deliverables (`core/values.py`, `core/parsing.py`, `core/tokenizer.py`, `MScope.walk_statements()`) are merged and available.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: textX ≥4.0 (parser), pytest ≥7.0 (testing)
**Storage**: N/A (transpiler — no persistent storage)
**Testing**: pytest with `uv run pytest` (5,883 tests, `-n auto` parallel execution)
**Target Platform**: Linux (dev container, Ubuntu 24.04)
**Project Type**: Single project — MUMPS-to-Python transpiler
**Performance Goals**: All 5,883 tests pass in <60s; no transpilation performance regression
**Constraints**: Zero test failures at every commit; no new xfail/skip markers; 15% code reduction in statements.py; 40% code reduction in indirection.py
**Scale/Scope**: 12 refactoring items across 6 primary source files (~22K lines total)

### Key Files and Baseline Metrics

| File | Lines | Phase 2 Role |
|---|---|---|
| `codegen/statements.py` | 6,775 | Track A: 9 sequential extractions (target ≤5,759) |
| `codegen/expressions.py` | 2,586 | Consumer updates for S-02, S-01 |
| `codegen/indirection.py` | 2,092 | Track B: template extraction (target ≤1,255) |
| `codegen/routine.py` | 1,310 | Consumer updates for S-04, S-14 |
| `runtime/__init__.py` | 6,168 | Track C: offset_wrapper, ZWRITE range extension |
| `asg/statements.py` | 1,354 | Track C: field cleanup, MLockTarget |

### Phase 1 Deliverables Available

| Module | Key Exports | Used By |
|---|---|---|
| `core/values.py` | `m_str`, `m_num`, `m_truth`, `m_compare`, `m_add/sub/mul` | C-07 (by-ref uses MArray from runtime) |
| `core/parsing.py` | `parse_subscripted_name`, `canonicalize_subscript` | S-13 (XECUTE pipeline) |
| `core/tokenizer.py` | `split_at_toplevel` | S-13 (XECUTE pipeline) |
| `asg/elements.py` | `MScope.walk_statements()` | S-16 (consumer migration) |
| `codegen/exceptions.py` | `CodegenError`, `UnsupportedFeatureError` | Already unified |

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Semantic Correctness First ✅

- C-09 (ZWRITE range): Fixes silent incorrect behavior using YDB-verified collation rules
- C-07 (by-ref calls): Fixes MUMPS standard 8.1.7 violation (value-result → DATA-CELL aliasing)
- All structural refactoring preserves byte-identical runtime output

### II. YDB as Reference Implementation ✅

- ZWRITE range behavior verified against YDB with mixed subscript types
- By-ref DATA-CELL aliasing verified against YDB (descendants, $DATA)
- Existing 5,883 YDB-validated tests serve as regression gate

### III. Strict Layer Separation ✅

- S-13: Removes codegen→parser backward dependency (XECUTE imports)
- FR-050: No new backward imports allowed
- `compile_mumps_line()` placed in `parser/` (correct layer)
- S-19: Moves comment extraction from codegen to parser (correct layer)
- C-08 (Phase 1): Already moved `contains_naked_global` to analysis

### IV. Explicit Over Implicit ✅

- No changes to the MUMPS value model
- Helper functions make variable access strategy explicit

### V. Foundational Correctness ✅

- C-07 fixes foundational by-ref semantics across strategies
- Phase 1 already solved foundational value model issues (C-01, C-02)

### VI. Cross-Cutting Semantics ✅

- S-01: Centralizes variable access dispatch (cross-cutting pattern)
- S-02: Centralizes subscript tuple generation (cross-cutting pattern)
- S-04: Centralizes scope↔state sync (cross-cutting pattern)

### VII. Minimize Runtime Surface ✅

- C-09 ZWRITE fix: Minimal runtime extension (adding range params to existing functions)
- S-12: Consolidates runtime closures (reduces, doesn't add)
- No new runtime classes introduced

### VIII. Research Before Implementation ✅

- Research phase completed: all 12 items analyzed with exact line numbers, pattern counts, and variations documented in [research.md](research.md)
- Key discovery: 16 indirection functions (not 11 originally estimated), but 14 are templatizable

### Post-Design Re-Check

- **III. Layer Separation**: `compile_mumps_line()` in `parser/` ✅ (clarified in spec Q1)
- **I. Semantic Correctness**: C-07 uses MUMPS standard 8.1.7 DATA-CELL aliasing ✅ (verified via YDB)
- **VII. Runtime Surface**: C-09 extends existing runtime functions with optional params ✅ (not new entry points)

**Gate result: PASS** — No violations found.

## Project Structure

### Documentation (this feature)

```text
specs/020-codegen-refactoring/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0: Research findings
├── data-model.md        # Phase 1: ASG changes (MLockTarget, MStatement.comment)
├── quickstart.md        # Phase 1: Development setup guide
├── contracts/
│   └── internal-apis.md # Phase 1: Internal function contracts
├── checklists/
│   └── requirements.md  # Quality validation checklist
└── tasks.md             # Phase 2 output (NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/m2py/
├── asg/
│   ├── statements.py        # S-16: Remove deprecated fields, add MLockTarget, add MStatement.comment
│   └── elements.py          # Phase 1: MScope.walk_statements() (already done)
├── codegen/
│   ├── statements.py        # Track A: S-02, S-05, S-04, S-14, C-09, S-01, S-13, S-19, C-07
│   ├── expressions.py       # Consumer updates for S-02 (57 sites), S-01 (20 sites)
│   ├── indirection.py       # Track B: S-03 template extraction (14+ functions)
│   ├── var_access.py        # NEW: S-01 strategy dispatch helpers
│   ├── routine.py           # Consumer updates for S-04 (6 sites), S-14 (2 sites)
│   └── exceptions.py        # Phase 1: Already unified
├── parser/
│   ├── compiler.py           # S-13: compile_mumps_line() (NEW)
│   ├── textx_classes.py      # S-19: Extract inline comments during parsing
│   └── line_parser.py        # S-19: Comment extraction support
├── analysis/
│   └── semantic_analyzer.py  # C-07: Force uses_dynamic_locals for by-ref; S-16: MLockTarget builder
├── runtime/
│   ├── __init__.py           # S-12: offset_wrapper consolidation; C-09: ZWRITE range params
│   └── helpers.py            # C-09: _mumps_collation_key already exists (read-only)
└── core/                     # Phase 1: All modules already done (read-only for Phase 2)

tests/
├── unit/
│   ├── codegen/
│   │   ├── test_var_access.py        # NEW: S-01 unit tests
│   │   ├── test_gen_subscripts.py    # NEW: S-02 unit tests
│   │   ├── test_lhs_helpers.py       # NEW: S-05 unit tests
│   │   ├── test_sync_helpers.py      # NEW: S-04 unit tests
│   │   └── extensions/ydb/
│   │       └── test_zwrite.py        # EXTEND: C-09 range filtering tests
│   ├── runtime/
│   │   └── test_offset_wrapper.py    # NEW: S-12 unit tests
│   └── asg/
│       └── test_lock_target.py       # NEW: S-16 MLockTarget tests
├── integration/
│   ├── test_byref_unification.py     # NEW: C-07 regression tests
│   └── test_zwrite_ranges.py         # NEW: C-09 regression tests
└── functional/                       # Existing: 5,883 tests unchanged
```

**Structure Decision**: Single project structure. New files limited to `codegen/var_access.py` and test files. All other changes are modifications to existing files.

## Implementation Tracks

### Track A — `codegen/statements.py` Sequential (Critical Path)

All items modify `codegen/statements.py` and MUST be sequential. Order is deliberate:
bulk mechanical extractions first (S-02, S-05, S-04, S-14) reduce file size,
making later extractions (S-01, S-13) safer. Correctness fixes (C-09, C-07)
come after structural cleanup.

| Step | Item | Description | Est. | Key Changes |
|---|---|---|---|---|
| A1 | S-02 | Extract `gen_subscripts_tuple()` | 1-2d | 99 inline sites → 1 helper across 3 files |
| A2 | S-05 | Extract `_build_lhs_getter_setter()` | 1d | ~300L of duplication → ~100L shared helper |
| A3 | S-04 | Extract `emit_state_to_scope_sync()` / `emit_scope_to_state_sync()` | 1-2d | 22 inline sync blocks → 2 helpers |
| A4 | S-14 | Extract `_emit_goto_external_handler()` | 0.5d | 6 inline blocks → 1 helper |
| A5 | C-09 | Fix ZWRITE subscript range filtering | 1-2d | Codegen emits range bounds + runtime filters using collation |
| A6 | S-01 | Extract to `codegen/var_access.py` | 3-5d | 69 inline dispatch sites → 3 helpers in new module |
| A7 | S-13 | Extract `compile_mumps_line()` to parser/ | 1-2d | Remove codegen→parser imports, single pipeline function |
| A8 | S-19 | Add `MStatement.comment`, move extraction to parser | 1d | ASG field + parser change + codegen simplification |
| A9 | C-07 | Unify by-ref call handling | 3-5d | Force dynamic_locals for by-ref, MArray aliasing unification |

### Track B — `codegen/indirection.py` (Parallel)

| Step | Item | Description | Est. | Key Changes |
|---|---|---|---|---|
| B1 | S-03 | Extract `_build_indirection_call()` template | 2-3d | 14 templatizable functions → thin wrappers + shared template |

### Track C — Runtime + ASG (Parallel)

| Step | Item | Description | Est. | Key Changes |
|---|---|---|---|---|
| C1 | S-12 | Consolidate offset_wrapper closures | 1d | 2 closures (~197L) → 1 factory function |
| C2 | S-16 | ASG field cleanup | 1-2d | Remove 3 deprecated fields, add MLockTarget, ZWithdraw delegation |

### Dependency Graph

```text
Phase 1 (merged) ──┬── Track A: A1→A2→A3→A4→A5→A6→A7→A8→A9
                   ├── Track B: B1
                   ├── Track C: C1 (runtime/__init__.py)
                   └── Track C: C2 (asg/statements.py, analysis/)

Track A and B/C are fully independent (different files).
Track B, C1, and C2 are all independent of each other (different files).
A9 (C-07) depends on A6 (S-01) because S-01 centralizes var access,
  making the by-ref changes simpler and more localized.
```

### Per-Item Implementation Details

#### A1: S-02 — Subscript Tuple Extraction

**What**: Create `gen_subscripts_tuple(subscripts, ctx) -> str` that outputs `"(expr1, expr2,)"`.

**Where to extract**: Define in `codegen/statements.py` (top-level, near other helpers). Called from `statements.py` (36 sites), `expressions.py` (57 sites), `indirection.py` (6 sites).

**Pattern to match** (grep for replacement targets):
```python
sub_exprs = [generate_expr(sub, ctx) for sub in *.subscripts]
if len(sub_exprs) == 1:
    subscripts_tuple = f"({sub_exprs[0]},)"
```

**Variations to handle**: (1) Standard subscript list, (2) naked global with prefix, (3) empty subscripts → `"()"`, (4) pre-evaluated expr list.

**Tests**: Unit test `gen_subscripts_tuple` with 0, 1, 2, N subscripts. Grep for zero remaining inline pattern copies.

---

#### A2: S-05 — LHS Piece/Extract Getter/Setter

**What**: Create `_build_lhs_getter_setter(target, ctx) -> tuple[str, str]` that returns `(getter_lambda, setter_lambda)` for any variable type.

**Where**: Define in `codegen/statements.py`. Called from `_generate_lhs_piece` (~L1200) and `_generate_lhs_extract` (~L1392).

**Structure**: Extract the 4-way type dispatch (GlobalVariable → NakedGlobal → MIndirection → MVariable) that is identical in both functions. Each caller keeps only: (1) target extraction from `assignment.target`, (2) position args, (3) runtime call (`m_set_piece` or `m_set_extract`).

**Tests**: Unit test the getter/setter builder with each variable type. Verify generated output matches baseline.

---

#### A3: S-04 — Scope↔State Sync Consolidation

**What**: Create `emit_state_to_scope_sync(ctx)` and `emit_scope_to_state_sync(ctx)`.

**Where**: Define in `codegen/statements.py`. Called from `statements.py` (16 sites) and `routine.py` (6 sites).

**Key behavior**: Both helpers check `ctx.uses_dynamic_locals` internally. If False, they emit nothing (no-op). If True, they emit the standard sync pattern.

**Variations**: State→scope uses `_scope.update(...)`. Scope→state iterates `_scope.items()` with MArray wrapping. Both patterns are confirmed identical across all sites.

**Tests**: Unit test both helpers with dynamic_locals=True and False. Verify emitted code matches baseline.

---

#### A4: S-14 — GotoExternal Handler Extraction

**What**: Create `_emit_goto_external_handler(ctx)`.

**Where**: Define in `codegen/statements.py`. Called from 4 sites in `statements.py` and 2 in `routine.py`.

**Structure**: Emits `except GotoExternal:` block with scope sync + re-raise. All 6 sites confirmed identical.

**Tests**: Unit test the handler emission. Verify the emitted pattern matches baseline.

---

#### A5: C-09 — ZWRITE Range Correctness

**What**: Fix `_generate_zwrite()` to emit range bounds. Extend `zwrite_local()` and `zwrite_global()` in runtime to accept and filter by range bounds.

**Codegen change**: Replace `break` in `MZWriteSubscriptRange` branch with: evaluate `start`/`end` expressions via `generate_expr()`, pass as keyword args to runtime.

**Runtime change**: Add `range_start` / `range_end` optional params. In `_zwrite_marray()`, filter children via `_mumps_collation_key` comparison before recursing.

**Edge cases** (YDB-verified):
- `A(1:10)` includes 1, 1.5, 2, 10 (all canonical numerics in range)
- `A("A":"B")` includes "A", "AA", "B" (strings in collation range)
- `A(2:)` includes all numerics ≥2 PLUS all strings
- `A(:2)` includes all values up to 2, NOT strings

**Tests**: New regression tests for each edge case. Integration test comparing m2py output vs YDB for ZWRITE with ranges.

---

#### A6: S-01 — Strategy Dispatch Consolidation

**What**: Create `codegen/var_access.py` with `var_read_expr()`, `var_write_stmt()`, `var_base_expr()`.

**Where**: New file `codegen/var_access.py`. Replace 69 inline dispatch patterns across 3 files.

**Approach**: Start with `var_base_expr()` (most common). Replace `statements.py` (42 sites) first, then `expressions.py` (20), then `indirection.py` (7). Run tests after each file.

**Variations to parameterize**:
- `setdefault` vs `get` (write vs read)
- `MArray()` default vs no default
- `array_vars` vs `state_vars` check (some sites check both)

**Risk**: Highest-volume change (69 sites). Each site has slight contextual differences. Must be done after S-02 and S-04 to reduce surrounding noise.

**Tests**: Unit tests for each helper with each strategy. Grep confirms zero remaining inline patterns.

---

#### A7: S-13 — XECUTE Pipeline Extraction

**What**: Create `compile_mumps_line(code_str, context)` in `parser/`.

**Where**: New file `parser/compiler.py`. Called from `_generate_xecute()` in `statements.py`.

**Eliminates**: 3 backward imports in `_generate_xecute()`:
- `from m2py.parser.line_parser import parse_commands_from_line`
- `from m2py.parser.parser import _structure_commands_with_bodies`
- `from m2py.analysis.semantic_analyzer import analyze_command`

**Tests**: Unit test `compile_mumps_line` with representative XECUTE strings. Verify `statements.py` has zero imports from `parser/` (except textx_classes types used for isinstance checks).

---

#### A8: S-19 — Comment Extraction via ASG

**What**: Add `comment: Optional[str]` field to `MStatement`. Populate during parsing. Codegen reads from ASG instead of re-scanning source.

**Parser change**: In `parser/textx_classes.py`, after converting a textX command to an MStatement ASG node, extract the inline comment (scan for unquoted `;` in the source line). Store in `stmt.comment`.

**Codegen change**: `_emit_source_comment` becomes trivial: `if stmt.comment: ctx.emitter.line(f"# {stmt.comment}")`.

**Tests**: Verify comment preservation for: (1) `SET X=1 ; comment`, (2) `WRITE "hello;world"` (no spurious comment), (3) line with no comment (comment=None).

---

#### A9: C-07 — By-Reference Call Unification

**What**: Unify TRAMPOLINE by-ref handling to use MArray aliasing instead of value-result.

**Semantic analyzer change**: In `analysis/semantic_analyzer.py`, when a routine has by-reference formal parameters, force `uses_dynamic_locals=True`. This ensures the TRAMPOLINE strategy uses `state._locals` dict, which naturally supports MArray aliasing.

**Codegen change**: The TRAMPOLINE by-ref path (~L4490-4530) is rewritten to match the SIMPLE_FUNCTIONS approach: pass `state._locals.setdefault(var, MArray())` directly instead of destructuring return tuples.

**What changes in generated code**: For routines with by-ref formals that previously used static state vars, the generated code will switch from `state.{name}` to `state._locals[{name!r}]`. This changes code structure but makes behavior correct (DATA-CELL pointer aliasing per MUMPS 8.1.7).

**Risk mitigation**: This is the last Track A item. All prior cleanup (S-01 centralizing var access) means the change is more localized. Extensive testing required:
- All existing by-ref tests pass
- New tests: descendant modification visibility, $DATA reflection, error-case mutation preservation

**Tests**: Dedicated regression suite comparing m2py vs YDB for by-ref scenarios.

---

#### B1: S-03 — Indirection Template Extraction

**What**: Create `_build_indirection_call(ind, ctx, runtime_method, **kwargs)` shared template.

**Where**: `codegen/indirection.py`. 14 functions become thin wrappers.

**Not templatizable**: `generate_indirect_do` (374 lines) and `generate_indirect_goto` (186 lines) have complex control flow specific to DO/GOTO. These should be simplified but retain their own implementations.

**Template structure** (shared ~70 lines):
1. Count indirection levels
2. Build scope expression
3. Type-switch on inner expression (MVariable, GlobalVariable, NakedGlobal)
4. Build `per_level_subscripts`
5. Format final `_rt.{runtime_method}(...)` call

**Tests**: All existing indirection tests pass. Line count check: ≤1,255 lines (40% reduction).

---

#### C1: S-12 — offset_wrapper Consolidation

**What**: Create `_create_offset_entry_wrapper(base_fn, offset, strategy, ...)` factory.

**Where**: `runtime/__init__.py`. Replaces closures at L1056-1167 and L1413-1499.

**Parameterized differences**: (1) GotoExternal handling (present in closure 1, absent in closure 2), (2) state sync mechanism (`__dataclass_fields__` vs `dir(state)`).

**Tests**: Existing tests covering label+offset entry points. New unit test for the factory function.

---

#### C2: S-16 — ASG Field Cleanup

**What**: Remove deprecated fields, add `MLockTarget`, delegate ZWithdraw.

**Sub-items** (each independently committable):

1. Remove `MIfStatement.condition` → update consumers to use `conditions` list
2. Remove `MHangStatement.duration` → update consumers to use `durations` list
3. Remove `MXecuteStatement.code_expressions` → update consumers to use `arguments`
4. Create `MLockTarget` dataclass → update `semantic_analyzer.py` builder and `statements.py` consumer
5. `_analyze_ZWithdrawCommand` → delegate to `_analyze_ZKillCommand`

**Consumer identification**: Use `grep` for each field name across all `.py` files. Update all attribute accesses.

**Tests**: All existing tests pass. New unit test for `MLockTarget` construction.

## Complexity Tracking

No constitution violations to justify. All changes align with existing architecture.
