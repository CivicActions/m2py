# Tasks: Codegen Refactoring (Phase 2)

**Input**: Design documents from `/specs/020-codegen-refactoring/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/internal-apis.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/m2py/` source, `tests/` at repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish baselines and verify Phase 1 deliverables are available

- [x] T001 Verify Phase 1 deliverables exist and are importable: `src/m2py/core/values.py`, `src/m2py/core/parsing.py`, `src/m2py/core/tokenizer.py`, `src/m2py/asg/elements.py` (`MScope.walk_statements`), `src/m2py/codegen/exceptions.py`
- [x] T002 Record baseline metrics: line counts for `src/m2py/codegen/statements.py` (expect ~6,775), `src/m2py/codegen/indirection.py` (expect ~2,092), xfail/skip counts in test suite
- [x] T003 Run full test suite (`uv run pytest`) to establish green baseline (5,883+ tests passing)
- [x] T004 [P] Create snapshot of generated Python output for representative MUMPS routines (regression baseline for US1). Transpile all `.m` files in `YDBTest/` and `tests/functional/` via `uv run python main.py`, capture generated Python to `tmp/baseline-snapshots/` (one `.py` per routine). Include routines exercising subscripts, indirection, LOCK, ZWRITE, by-ref, scope sync, XECUTE, and SET $PIECE/$EXTRACT.

**Checkpoint**: Baselines recorded, Phase 1 confirmed available, all tests green

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No blocking shared infrastructure needed beyond Phase 1 deliverables (already merged)

**⚠️ NOTE**: Phase 1 deliverables (`core/values.py`, `core/parsing.py`, `core/tokenizer.py`, `asg/elements.py`, `codegen/exceptions.py`) are already merged to `main`. No new foundational work is needed before user stories can begin.

**Checkpoint**: Foundation ready — user story implementation can begin

---

## Phase 3: User Story 2 — Subscript Tuple Extraction (Priority: P2) — Track A Step 1

**Goal**: Replace all ~99 inline subscript-tuple generation patterns with calls to a single `gen_subscripts_tuple()` helper ([spec.md US2](spec.md), [plan.md A1](plan.md))

**Independent Test**: Search for the inline pattern (list comprehension + trailing-comma check). Zero matches remain. All 5,883+ tests pass.

### Implementation for User Story 2

- [x] T005 [US2] Create `gen_subscripts_tuple(subscripts, ctx) -> str` helper function near top of `src/m2py/codegen/statements.py` per contract in `contracts/internal-apis.md`. Handle 4 variations: standard subscript list, naked global with prefix, empty subscripts → `"()"`, pre-evaluated expr list. Include docstring.
- [x] T006 [US2] Write unit tests for `gen_subscripts_tuple()` in `tests/unit/codegen/test_gen_subscripts.py` covering 0, 1, 2, N subscripts and edge cases (empty list, single-element trailing comma)
- [x] T007 [US2] Replace all ~36 inline subscript-tuple patterns in `src/m2py/codegen/statements.py` with calls to `gen_subscripts_tuple()`. Run `uv run pytest` after each batch of replacements.
- [x] T008 [US2] Replace all ~57 inline subscript-tuple patterns in `src/m2py/codegen/expressions.py` with calls to `gen_subscripts_tuple()`. Import the function from `codegen/statements.py`. Run `uv run pytest`.
- [x] T009 [US2] Replace all ~6 inline subscript-tuple patterns in `src/m2py/codegen/indirection.py` with calls to `gen_subscripts_tuple()`. Import the function from `codegen/statements.py`. Run `uv run pytest`.
- [x] T010 [US2] Verify zero remaining inline pattern copies via `rg` search for `sub_exprs.*=.*\[generate_expr` and the trailing-comma check pattern. Remove any dead code. Run full test suite.

**Checkpoint**: US2 complete. gen_subscripts_tuple() is the single source of truth for subscript tuples. All tests pass.

---

## Phase 4: User Story 3 — LHS Piece/Extract Deduplication (Priority: P2) — Track A Step 2

**Goal**: Extract shared `_build_lhs_getter_setter()` helper from `_generate_lhs_piece` and `_generate_lhs_extract` ([spec.md US3](spec.md), [plan.md A2](plan.md))

**Independent Test**: Transpile MUMPS using `SET $P(X,"^",2)=Y` and `SET $E(X,1,3)=Y` for all variable types. Output matches pre-refactoring.

### Implementation for User Story 3

- [x] T011 [US3] Create `_build_lhs_getter_setter(target, ctx) -> tuple[str, str]` in `src/m2py/codegen/statements.py` handling all 4 variable types (GlobalVariable, NakedGlobal, MIndirection, MVariable) per contract in `contracts/internal-apis.md`. Include docstring.
- [x] T012 [US3] Write unit tests for `_build_lhs_getter_setter()` in `tests/unit/codegen/test_lhs_helpers.py` covering each variable type and strategy combination
- [x] T013 [US3] Refactor `_generate_lhs_piece` in `src/m2py/codegen/statements.py` (~L1200) to use `_build_lhs_getter_setter()`, keeping only position-arg logic and `m_set_piece` call. Run `uv run pytest`.
- [x] T014 [US3] Refactor `_generate_lhs_extract` in `src/m2py/codegen/statements.py` (~L1392) to use `_build_lhs_getter_setter()`, keeping only position-arg logic and `m_set_extract` call. Run `uv run pytest`.
- [x] T015 [US3] Verify MIndirection handling block exists in exactly one location. Remove dead code. Run full test suite.

**Checkpoint**: US3 complete. ~300 lines of duplication reduced to ~100 lines. All tests pass.

---

## Phase 5: User Story 4 — Scope-State Sync Consolidation (Priority: P2) — Track A Step 3

**Goal**: Replace all 22 inline scope↔state sync blocks with calls to `emit_state_to_scope_sync()` and `emit_scope_to_state_sync()` ([spec.md US4](spec.md), [plan.md A3](plan.md))

**Independent Test**: Transpile routines using TRAMPOLINE strategy with dynamic locals. Verify state↔scope sync works at subroutine boundaries, after GOTO, and during error handling.

### Implementation for User Story 4

- [x] T016 [US4] Create `emit_state_to_scope_sync(ctx)` and `emit_scope_to_state_sync(ctx)` helpers in `src/m2py/codegen/statements.py` per contract. Both must check `ctx.uses_dynamic_locals` internally (no-op if False). Include docstrings.
- [x] T017 [US4] Write unit tests for both sync helpers in `tests/unit/codegen/test_sync_helpers.py` covering dynamic_locals=True and False. Include test case where both sync directions apply within the same block (a variable appears in both scope→state and state→scope sync).

- [x] T018 [US4] Replace all ~9 state→scope sync blocks in `src/m2py/codegen/statements.py` with calls to `emit_state_to_scope_sync()`. Run `uv run pytest`.
- [x] T019 [US4] Replace all ~7 scope→state sync blocks in `src/m2py/codegen/statements.py` with calls to `emit_scope_to_state_sync()`. Run `uv run pytest`.
- [x] T020 [US4] Replace all ~6 sync blocks in `src/m2py/codegen/routine.py` with calls to the shared helpers. Import from `codegen/statements.py`. Run `uv run pytest`.
- [x] T021 [US4] Verify zero remaining inline sync patterns via `rg` search. Remove dead code. Run full test suite.

**Checkpoint**: US4 complete. 22 inline sync blocks consolidated to 2 helpers. All tests pass.

---

## Phase 6: User Story 5 — GotoExternal Handler Extraction (Priority: P2) — Track A Step 4

**Goal**: Replace all 6 inline `except GotoExternal` handler blocks with calls to `_emit_goto_external_handler()` ([spec.md US5](spec.md), [plan.md A4](plan.md))

**Independent Test**: Transpile routines with external GOTO. Verify handler propagates scope sync and re-raises correctly.

### Implementation for User Story 5

- [x] T022 [US5] Create `_emit_goto_external_handler(ctx)` in `src/m2py/codegen/statements.py` per contract. Include docstring.
- [x] T023 [US5] Replace all 4 inline `except GotoExternal` handler blocks in `src/m2py/codegen/statements.py` with calls to `_emit_goto_external_handler()`. Run `uv run pytest`.
- [x] T024 [US5] Replace all 2 inline `except GotoExternal` handler blocks in `src/m2py/codegen/routine.py` with calls to `_emit_goto_external_handler()`. Import from `codegen/statements.py`. Run `uv run pytest`.
- [x] T025 [US5] Verify zero remaining inline `except GotoExternal` blocks with scope sync code via `rg` search. Run full test suite. (Note: 4 handlers in indirection.py use a different sync pattern—_scope.update()—and are not candidates for this helper.)

**Checkpoint**: US5 complete. 6 identical handler blocks consolidated to 1 function. All tests pass.

---

## Phase 7: User Story 6 — ZWRITE Range Correctness (Priority: P2) — Track A Step 5

**Goal**: Fix ZWRITE subscript ranges to filter correctly using MUMPS collation instead of treating ranges as wildcards ([spec.md US6](spec.md), [plan.md A5](plan.md))

**Independent Test**: `ZW ^A(2:4)` on a global with subscripts 0–5 displays only 2, 3, 4. Compare output vs YDB.

### Implementation for User Story 6

- [x] T026 [US6] Extend `zwrite_local()` and `zwrite_global()` in `src/m2py/runtime/__init__.py` to accept optional `range_start` / `range_end` params per contract. Implement filtering using `_mumps_collation_key` from `runtime/helpers.py`.
- [x] T027 [US6] Write regression tests for ZWRITE range filtering in `tests/integration/test_zwrite_ranges.py` covering: numeric ranges `A(2:4)`, string ranges `A("A":"B")`, open-end `A(2:)`, open-start `A(:2)`, mixed type subscripts
- [x] T028 [US6] Fix `_generate_zwrite()` in `src/m2py/codegen/statements.py` (~L6580): replace `break` in `MZWriteSubscriptRange` branch with evaluation of start/end expressions via `generate_expr()`, pass as keyword args to runtime. Apply to both globals and locals paths.
- [x] T029 [US6] Unify the globals and locals ZWRITE codegen paths in `src/m2py/codegen/statements.py` to eliminate code duplication. Run `uv run pytest`.
- [x] T030 [US6] Validate ZWRITE range output against YDB using `uv run python utils/validate.py` for each edge case scenario. Run full test suite.

**Checkpoint**: US6 complete. ZWRITE ranges filter correctly using MUMPS collation. All tests pass.

---

## Phase 8: User Story 7 — Strategy Dispatch Consolidation (Priority: P2) — Track A Step 6

**Goal**: Replace all ~69 inline 3-way variable-access dispatch patterns with helpers in `codegen/var_access.py` ([spec.md US7](spec.md), [plan.md A6](plan.md))

**Independent Test**: Transpile routines under all three strategies. Generated Python is identical. Zero inline dispatch patterns remain.

### Implementation for User Story 7

- [x] T031 [US7] Create `src/m2py/codegen/var_access.py` with `var_read_expr()`, `var_write_stmt()`, and `var_base_expr()` per contract in `contracts/internal-apis.md`. Handle all 3 strategies and all variations (setdefault vs get, MArray default, array_vars vs state_vars). Include docstrings.
- [x] T032 [US7] Write unit tests for all 3 functions in `tests/unit/codegen/test_var_access.py` covering each strategy (SIMPLE_FUNCTIONS, TRAMPOLINE+static, TRAMPOLINE+dynamic) and each access mode (read, write, base)
- [x] T033 [US7] Replace all ~42 inline dispatch patterns in `src/m2py/codegen/statements.py` with calls to var_access helpers. Run `uv run pytest` after every ~10 replacements.
- [x] T034 [US7] Replace all ~20 inline dispatch patterns in `src/m2py/codegen/expressions.py` with calls to var_access helpers. Run `uv run pytest`.
- [x] T035 [US7] Replace all ~7 inline dispatch patterns in `src/m2py/codegen/indirection.py` with calls to var_access helpers. Run `uv run pytest`.
- [x] T036 [US7] Verify zero remaining inline 3-way dispatch patterns via `rg` search. Remove dead code. Run full test suite.

**Checkpoint**: US7 complete. 69 inline dispatch patterns consolidated to 3 helpers. All tests pass.

---

## Phase 9: User Story 8 — XECUTE Pipeline Extraction (Priority: P2) — Track A Step 7

**Goal**: Extract `compile_mumps_line()` to `parser/` and remove backward codegen→parser dependency ([spec.md US8](spec.md), [plan.md A7](plan.md))

**Independent Test**: Transpile routines with XECUTE. `statements.py` has zero imports from `parser/` (except textx_classes types).

### Implementation for User Story 8

- [x] T037 [US8] Create `compile_mumps_line(code_str, context)` in `src/m2py/parser/compiler.py` per contract. The function runs full parse→analyze→structure pipeline. Include docstring.
- [x] T038 [US8] Write unit tests for `compile_mumps_line()` in `tests/unit/parser/test_compile_mumps_line.py` covering representative XECUTE strings: `"WRITE 1,! QUIT"`, multi-command lines, edge cases
- [x] T039 [US8] Refactor `_generate_xecute()` in `src/m2py/codegen/statements.py` to call `compile_mumps_line()` instead of directly importing `parse_commands_from_line`, `_structure_commands_with_bodies`, and `analyze_command`. Run `uv run pytest`.
- [x] T040 [US8] Verify `src/m2py/codegen/statements.py` has zero imports from `m2py.parser.line_parser`, `m2py.parser.parser`, or `m2py.analysis.semantic_analyzer` inside `_generate_xecute`. Run full test suite.

**Checkpoint**: US8 complete. XECUTE uses shared pipeline. Backward imports eliminated. All tests pass.

---

## Phase 10: User Story 11 — Indirection Template Extraction (Priority: P2) — Track B

**Goal**: Collapse 14 near-identical indirection functions into thin wrappers over a shared `_build_indirection_call()` template ([spec.md US11](spec.md), [plan.md B1](plan.md))

**Independent Test**: All indirection forms (SET @X, WRITE @Y, KILL @Z, etc.) transpile and run correctly. `indirection.py` reduced by ≥40%.

**⚠️ NOTE**: This phase is on Track B and can be done IN PARALLEL with Track A phases (3–9) since it only modifies `src/m2py/codegen/indirection.py`.

### Implementation for User Story 11

- [X] T041 [P] [US11] Analyze all 16 indirection functions in `src/m2py/codegen/indirection.py` and categorize: 14 templatizable vs 2 complex (indirect_do, indirect_goto). Document per-function parameter differences.
- [X] T042 [P] [US11] Create `_build_indirection_call(ind, ctx, runtime_method, **kwargs)` shared template in `src/m2py/codegen/indirection.py`. Implement the 5-step template: count levels, build scope expr, type-switch inner expr, build per_level_subscripts, format runtime call.
- [X] T043 [US11] Refactor the first batch of templatizable functions (e.g., set_indirected, write_indirected, kill_indirected, merge_indirected) to thin wrappers calling `_build_indirection_call()`. Run `uv run pytest` after each function.
- [X] T044 [US11] Refactor remaining templatizable functions (e.g., order_indirected, data_indirected, get_indirected, query_indirected, increment_indirected, piece_indirected, and others) to thin wrappers. Run `uv run pytest` after each function.
- [X] T045 [US11] Simplify `generate_indirect_do` and `generate_indirect_goto` (non-templatizable) by extracting any shared sub-patterns without forcing them into the template. Run `uv run pytest`.
- [X] T046 [US11] Verify line count of `src/m2py/codegen/indirection.py` is ≤1,255 (40% reduction from ~2,092). Diff generated Python for indirection-heavy routines (SET @X, WRITE @Y, KILL @Z, IF @X, MERGE @X, $ORDER/@, $DATA/@, $GET/@, $QUERY/@, $INCREMENT/@, $PIECE/@) against T004 baseline to confirm byte-identical output per FR-021. Remove dead code. Run full test suite.

**Checkpoint**: US11 complete. 14 indirection functions are thin wrappers. ≥40% line reduction achieved. All tests pass.

---

## Phase 11: User Story 12 — offset_wrapper Consolidation (Priority: P3) — Track C Step 1

**Goal**: Consolidate two ~100-line `offset_wrapper` closures into a single factory function ([spec.md US12](spec.md), [plan.md C1](plan.md))

**Independent Test**: Routines with label+offset entry points execute correctly.

**⚠️ NOTE**: This phase is on Track C and can be done IN PARALLEL with Track A and Track B since it only modifies `src/m2py/runtime/__init__.py`.

### Implementation for User Story 12

- [x] T047 [P] [US12] Create `_create_offset_entry_wrapper(base_fn, offset, strategy, ...)` factory function in `src/m2py/runtime/__init__.py` parameterizing the differences: GotoExternal handling and state sync mechanism (`__dataclass_fields__` vs `dir(state)`). Include docstring.
- [x] T048 [P] [US12] Write unit tests for the factory function in `tests/unit/runtime/test_offset_wrapper.py` covering both closure variants and error handling
- [x] T049 [US12] Replace closure at ~L1056-1167 in `src/m2py/runtime/__init__.py` with call to `_create_offset_entry_wrapper()`. Run `uv run pytest`.
- [x] T050 [US12] Replace closure at ~L1413-1499 in `src/m2py/runtime/__init__.py` with call to `_create_offset_entry_wrapper()`. Run `uv run pytest`.
- [x] T051 [US12] Remove dead closure code. Verify scope init, state creation, trampoline loop, and state sync logic exist in exactly one location. Run full test suite.

**Checkpoint**: US12 complete. Two closures consolidated to one factory. All tests pass.

---

## Phase 12: User Story 13 — ASG Field Cleanup (Priority: P3) — Track C Step 2

**Goal**: Remove deprecated ASG fields, add `MLockTarget` dataclass, delegate ZWithdraw to ZKill ([spec.md US13](spec.md), [plan.md C2](plan.md))

**Independent Test**: Transpile routines exercising IF, HANG, LOCK, XECUTE, ZWithdraw. All produce correct output.

**⚠️ NOTE**: Track C Step 2. Can be done in parallel with Track A, Track B, AND Track C Step 1 (S-12), since C2 modifies `asg/statements.py` and `analysis/semantic_analyzer.py` while C1 modifies `runtime/__init__.py` — no file overlap.

### Implementation for User Story 13

- [x] T052 [P] [US13] Remove `MIfStatement.condition` field from `src/m2py/asg/statements.py`. Update all consumers (search with `rg '\.condition[^s]'` in codegen/ and analysis/) to use `conditions` list. Run `uv run pytest`.
- [x] T053 [P] [US13] Remove `MHangStatement.duration` field from `src/m2py/asg/statements.py`. Update all consumers (search with `rg '\.duration[^s]'`) to use `durations` list. Run `uv run pytest`.
- [x] T054 [P] [US13] Remove `MXecuteStatement.code_expressions` field from `src/m2py/asg/statements.py`. Update all consumers (search with `rg 'code_expressions'`) to use `arguments`. Run `uv run pytest`.
- [x] T055 [US13] Create `MLockTarget` dataclass in `src/m2py/asg/statements.py` per `data-model.md` (9 fields: name, subscripts, is_global, lockop, timeout, postcondition, is_indirect, indirection, indirection_levels). Write unit tests in `tests/unit/asg/test_lock_target.py`.
- [x] T056 [US13] Update `_analyze_LockCommand` in `src/m2py/analysis/semantic_analyzer.py` to build `MLockTarget` instances instead of dicts. Update `MLockStatement.targets` type annotation from `List[Any]` to `List[MLockTarget]`. Run `uv run pytest`.
- [x] T057 [US13] Update lock target consumers in `src/m2py/codegen/statements.py` to use `MLockTarget` attribute access instead of dict key access. Run `uv run pytest`.
- [x] T058 [US13] Make `_analyze_ZWithdrawCommand` in `src/m2py/analysis/semantic_analyzer.py` delegate to `_analyze_ZKillCommand`. Run `uv run pytest`.
- [x] T059 [US13] Verify all deprecated fields are removed, no stale attribute access remains. Run full test suite.

**Checkpoint**: US13 complete. ASG is clean — typed fields, no duplicates, alias delegation. All tests pass.

---

## Phase 13: User Story 9 — Comment Extraction via ASG (Priority: P3) — Track A Step 8

**Goal**: Add `MStatement.comment` field, populate during parsing, simplify codegen comment emission ([spec.md US9](spec.md), [plan.md A8](plan.md))

**Independent Test**: Transpile routines with inline comments (`;`). Comments appear in generated Python identically.

### Implementation for User Story 9

- [ ] T060 [US9] Add `comment: Optional[str] = None` field to `MStatement` in `src/m2py/asg/statements.py` per `data-model.md`
- [ ] T061 [US9] Implement comment extraction in `src/m2py/parser/textx_classes.py` (or `src/m2py/parser/line_parser.py`): after converting a textX command to an MStatement, scan for unquoted `;` in the source line and populate `stmt.comment`. Handle edge case: semicolons inside quoted strings must NOT be treated as comments.
- [ ] T062 [US9] Write tests for comment extraction covering: `SET X=1 ; comment` → comment="comment", `WRITE "hello;world"` → comment=None, line with no comment → comment=None
- [ ] T063 [US9] Simplify `_emit_source_comment` in `src/m2py/codegen/statements.py` to read from `stmt.comment` instead of re-scanning source lines. Run `uv run pytest`.
- [ ] T064 [US9] Verify identical comment output for a representative set of MUMPS routines. Run full test suite.

**Checkpoint**: US9 complete. Comments flow through ASG, codegen reads them. All tests pass.

---

## Phase 14: User Story 10 — By-Reference Call Unification (Priority: P3) — Track A Step 9

**Goal**: Unify TRAMPOLINE and SIMPLE_FUNCTIONS by-ref handling to use MArray aliasing (DATA-CELL semantics) ([spec.md US10](spec.md), [plan.md A9](plan.md))

**Independent Test**: By-ref parameter mutations visible to callers under both strategies, including error scenarios and descendant modifications. Compare against YDB.

### Implementation for User Story 10

- [ ] T065 [US10] Modify `src/m2py/analysis/semantic_analyzer.py`: when a routine declares by-reference formal parameters, force `uses_dynamic_locals=True`. This ensures dict-based access for MArray aliasing.
- [ ] T066 [US10] Write regression tests in `tests/integration/test_byref_unification.py` covering: basic by-ref modification, multiple by-ref params, by-ref with descendants (SET/KILL visibility), $DATA reflection, error-case mutation preservation, unmodified by-ref parameter (callee receives `.X` but never modifies it — verify no behavioral change or overhead)
- [ ] T067 [US10] Rewrite TRAMPOLINE by-ref code path in `src/m2py/codegen/statements.py` (~L4490-4530) to use MArray aliasing: pass `state._locals.setdefault(var, MArray())` directly instead of destructuring return tuples. Run `uv run pytest`.
- [ ] T068 [US10] Validate by-ref scenarios against YDB using `uv run python utils/validate.py` for: basic mutation, descendant visibility, $DATA, error-case preservation. Run full test suite.
- [ ] T069 [US10] Verify both strategies produce identical by-ref semantics. Clean up any dead value-result code. Run full test suite.

**Checkpoint**: US10 complete. Both strategies use MArray aliasing. DATA-CELL semantics match YDB. All tests pass.

---

## Phase 15: User Story 1 — Final Regression Validation (Priority: P1)

**Goal**: Verify the entire refactoring preserves behavioral correctness across ALL items ([spec.md US1](spec.md))

**Independent Test**: Full test suite passes. Generated output matches pre-refactoring baselines.

### Validation for User Story 1

- [ ] T070 [US1] Run full test suite (`uv run pytest -n auto`). Verify 5,883+ tests pass with zero failures, zero errors, zero new xfails, zero new skips.
- [ ] T071 [US1] Compare generated Python output for representative MUMPS routines against the snapshot taken in T004. Verify runtime behavior is identical (byte-identical output where expected, corrected output for C-09 and C-07).
- [ ] T072 [US1] Run YDBTest validation suite via `uv run python utils/validate.py` for routines exercising all touched features: subscripts, indirection, LOCK, KILL, NEW, DO, GOTO, JOB, SET $PIECE, SET $EXTRACT, XECUTE, ZWRITE, IF, HANG, FOR, by-ref calls, scope sync.
- [ ] T073 [US1] Verify quantitative targets: `codegen/statements.py` ≤5,759 lines (≥15% reduction from 6,775), `codegen/indirection.py` ≤1,255 lines (≥40% reduction from 2,092).

**Checkpoint**: US1 complete. All behavioral invariants confirmed. Quantitative targets met.

---

## Phase 16: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup affecting multiple stories

- [ ] T074 [P] Remove any unused imports across all modified files using `rg` or Pylance. Run `uv run pytest`.
- [ ] T075 [P] Verify all new helper functions and modules have docstrings per FR-051. Add any missing ones.
- [ ] T076 [P] Verify no dead code (commented-out functions, unreachable branches) remains per FR-052. Run `uv run pytest`.
- [ ] T077 [P] Verify no new backward imports introduced per FR-050: `runtime/` must not import from `codegen/`, `core/` must not import from `codegen/`/`runtime/`, `asg/` must not import from `codegen/`/`runtime/`.
- [ ] T078 Run quickstart.md validation checklist to confirm development workflow still works
- [ ] T079 Update `docs/coverage-matrix.md` and `docs/architecture.md` to reflect refactored structure

**Checkpoint**: All polish complete. Codebase is clean, documented, and properly layered.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Already satisfied (Phase 1 merged to main)
- **Track A (Phases 3–9, 13–14)**: MUST be sequential: US2→US3→US4→US5→US6→US7→US8→US9→US10
- **Track B (Phase 10)**: Independent of Track A — can run in parallel
- **Track C (Phases 11–12)**: Independent of Track A/B — can run in parallel; C1 and C2 are also independent of each other (different files)
- **US1 Validation (Phase 15)**: Depends on ALL user stories being complete
- **Polish (Phase 16)**: Depends on US1 validation

### User Story Dependencies

```text
Setup ──┬── Track A: US2→US3→US4→US5→US6→US7→US8→US9→US10
        ├── Track B: US11 (parallel with Track A)
        ├── Track C: US12 (parallel with Track A/B)
        └── Track C: US13 (parallel with Track A/B and US12)
                            
All stories ──→ US1 (final validation) ──→ Polish
```

### Within Each User Story

- Helper function / new code created FIRST
- Unit tests for new helper written and verified
- Inline patterns replaced incrementally (run tests after each batch)
- Dead code removed
- Full test suite run at checkpoint

### Track A Ordering Rationale

1. **US2 (S-02)** first: highest count (99 sites), lowest risk, reduces noise for everything after
2. **US3 (S-05)** next: self-contained ~300L cleanup, no cross-file impact
3. **US4 (S-04)** next: 22 sync blocks consolidated, affects `routine.py` too
4. **US5 (S-14)** next: small mechanical change, natural after sync consolidation
5. **US6 (C-09)** next: correctness fix, builds on reduced code volume
6. **US7 (S-01)** next: largest volume change (69 sites), easier after S-02/S-04 reduce surrounding code
7. **US8 (S-13)** next: layer separation fix, benefits from cleaner `statements.py`
8. **US9 (S-19)** next: structural improvement, light touch
9. **US10 (C-07)** last: highest-risk correctness change, benefits from all prior cleanup (especially S-01)

### Parallel Opportunities

**Cross-Track parallelism** (different files, fully independent):
```text
Track A (statements.py, expressions.py)  ║  Track B (indirection.py)  ║  Track C (runtime/__init__.py, asg/statements.py)
                                         ║                            ║
US2→US3→US4→US5→US6→US7→US8→US9→US10     ║  US11                     ║  US12→US13
```

**Within-phase parallelism** (marked [P]):
- Phase 10 (US11): T041 and T042 can run in parallel (analysis vs template creation)
- Phase 11 (US12): T047 and T048 can run in parallel (factory vs tests)  
- Phase 12 (US13): T052, T053, T054 can all run in parallel (independent field removals)
- Phase 16 (Polish): T074, T075, T076, T077 can all run in parallel

---

## Implementation Strategy

### MVP First (Track A through US6)

1. Complete Phase 1: Setup + baselines
2. Complete Phases 3–7: US2→US3→US4→US5→US6
3. **STOP and VALIDATE**: Bulk mechanical extractions done + ZWRITE correctness fixed
4. This is a natural **mid-point milestone** — the codebase is significantly simpler

### Incremental Delivery

1. **Milestone 1** (Phases 3–6): Bulk extractions — S-02, S-05, S-04, S-14 → ~400+ lines saved
2. **Milestone 2** (Phase 7): ZWRITE correctness — C-09 → behavioral fix
3. **Milestone 3** (Phases 8–9): Strategy consolidation — S-01, S-13 → largest structural improvements
4. **Milestone 4** (Phases 10–12): Track B/C — S-03, S-12, S-16 → indirection/runtime/ASG cleanup
5. **Milestone 5** (Phases 13–14): Final Track A — S-19, C-07 → comment extraction + by-ref fix
6. **Milestone 6** (Phases 15–16): Validation + polish

### Single Developer Strategy

Execute Track A sequentially (critical path), interleave Track B and Track C during natural break points:
- After US5 (A4 done, small item): Start Track B (US11) or Track C (US12)
- After US10 (A9 done, everything passes): Complete any remaining Track B/C items
- All items converge at US1 validation

---

## Notes

- [P] tasks = different files, no dependencies on in-progress tasks
- [Story] label maps task to specific user story for traceability
- Each user story is independently testable at its checkpoint
- Run `uv run pytest` (not bare `pytest`) per project conventions
- Commit after each task completes with tests green
- Track A items are sequential within `statements.py` — never work on two simultaneously
- Track B and C can be interleaved freely with Track A
