# Tasks: Foundation & Cleanup

## Phase 1: Setup
- [x] T001 Create feature directory structure in /specs/019-foundation-cleanup
- [x] T002 [P] Create src/m2py/core/values.py (done; parsing.py + tokenizer.py tracked by US3 T031/T032)
- [x] T003 [P] Create tests/unit/core/test_values.py (done; test_parsing.py + test_tokenizer.py tracked by US3 T035)

## Phase 2: Foundational
- [x] T004 Update pyproject.toml and uv dependencies if needed for Decimal, textX (no changes needed — Decimal is stdlib, textX already a dep)
- [x] T005 [P] Add initial contracts to contracts/module-contracts.md for new modules
- [x] T006 [P] Add initial data model to data-model.md for new entities

## Phase 3: User Story 1 — Transpiler Produces Identical Output After Refactoring (P1) 🎯 MVP
- [x] T007 [US1] Move mumps_canonical_str, m_num, m_str, m_truth, m_compare, m_add, m_sub, m_mul to src/m2py/core/values.py
- [x] T008 [P] [US1] Update codegen/helpers.py to re-export from core/values.py
- [x] T009 [US1] Update runtime/helpers.py to delegate m_format_output to core/values.py
- [x] T010 [US1] Update SubscriptCanonicalizer in core/subscripts.py to delegate to core/values.py
- [x] T011 [US1] Update all deferred imports in runtime/__init__.py, runtime/helpers.py, runtime/globals.py, core/indirection.py to use core/values.py (17 value-model imports done; 1 generate_python remains — that's US2/T016)
- [x] T012 [US1] Remove duplicate _is_canonical_numeric from runtime/helpers.py
- [x] T013 [US1] Add/Update tests for value-model functions in tests/unit/core/test_values.py
- [x] T014 [US1] Run uv run pytest and verify zero failures, xfails, skips (5776 passed, 0 failed)

---

## Phase 4: US2 — Runtime Can Be Used Without Codegen Layer (P2)  ⇄ PARALLEL with Phase 5

**Goal**: Eliminate the last deferred codegen import in runtime, making `m2py.runtime` independently importable.

**Independent Test**: `from m2py.runtime import MUMPSRuntime` and `from m2py.core.values import m_num, m_str` succeed without any codegen import.

**Files touched**: runtime/__init__.py, runtime/helpers.py, core/values.py, core/names.py — NO overlap with Phase 5.

- [ ] T015 [US2] Verify all runtime imports of NameTranslator/translate_name use m2py.core.names (not m2py.codegen.names); update any remaining backward import paths in src/m2py/runtime/ (R-02 confirmed definitions are in core/names.py)
- [ ] T016 [US2] Replace generate_python deferred import with callback injection in src/m2py/runtime/__init__.py — add codegen_callback parameter to MUMPSRuntime.__init__, update execute_mumps() at L5794
- [ ] T017 [P] [US2] Verify m_format_output docstring accuracy in src/m2py/runtime/helpers.py (S-17 — fix if last example line is incorrect per research.md)
- [ ] T018 [P] [US2] Add integration test: import MUMPSRuntime and core/values without codegen in tests/integration/test_runtime_independence.py
- [ ] T019 [US2] Run uv run pytest and verify zero failures

**Checkpoint**: `rg "from m2py\.codegen" src/m2py/runtime/ src/m2py/core/` returns zero results (except callback usage comments)

---

## Phase 5: US4 — Analysis Cleanup & Detection (P3)  ⇄ PARALLEL with Phase 4

> **Note**: US4 (P3) appears before US3 (P2) because parallel file-ownership analysis groups it with Phase 4 in Wave 1. Priority ordering is preserved within each lane.

**Goal**: Fix exclusive KILL/NEW detection gap (C-06), deduplicate analysis-layer code, remove dead codegen stubs, and move misplaced analysis functions.

**Independent Test**: Existing KILL/ZKILL/NEW tests pass. A MUMPS routine with `K (X)` under TRAMPOLINE compiles without `NotImplementedError`.

**Files touched**: asg/elements.py, analysis/variables.py, analysis/semantic_analyzer.py, analysis/for_analysis.py, codegen/shared_state.py, codegen/expressions.py, codegen/indirection.py — NO overlap with Phase 4.

### C-06: Exclusive KILL/NEW Detection
- [ ] T020 [US4] Add has_exclusive_kill and has_exclusive_new fields (default False) to MRoutine in src/m2py/asg/elements.py
- [ ] T021 [US4] Add _routine_has_exclusive_kill and _routine_has_exclusive_new detection functions in src/m2py/analysis/variables.py; set flags alongside existing flag-setting code (~L188)
- [ ] T022 [US4] Update routine_uses_dynamic_locals predicate in src/m2py/codegen/shared_state.py to include has_exclusive_kill and has_exclusive_new

### Quick Wins
- [ ] T023 [P] [US4] Remove dead generate_xecute_constant (L1403) and generate_xecute_dynamic (L1426) stubs from src/m2py/codegen/indirection.py (S-18)

### Analysis Deduplication
- [ ] T024 [US4] Deduplicate _analyze_KillCommand, _analyze_KSubscriptsCommand, _analyze_KValueCommand, _analyze_ZKillCommand, _analyze_ZWithdrawCommand via shared _analyze_kill_like helper in src/m2py/analysis/semantic_analyzer.py (S-08)
- [ ] T025 [US4] Deduplicate DO/GOTO/JOB argument iteration via shared _analyze_call_arguments helper in src/m2py/analysis/semantic_analyzer.py (S-09)
- [ ] T026 [US4] Add assertion to unwrap_expression for non-empty operator tails in src/m2py/analysis/semantic_analyzer.py (S-15)

### Analysis Infrastructure
- [ ] T027 [US4] Delegate _check_var_modified_in_scope to variables.py write-detection infrastructure in src/m2py/analysis/for_analysis.py (S-20)
- [ ] T028 [US4] Move contains_naked_global from src/m2py/codegen/expressions.py to src/m2py/analysis/variables.py; compute during semantic analysis and store as _has_naked_global ASG annotation; update codegen to read annotation (C-08)
- [ ] T029 [P] [US4] Add/Update tests for exclusive KILL/NEW detection and analysis helpers in tests/unit/analysis/
- [ ] T030 [US4] Run uv run pytest and verify zero failures

**Checkpoint**: Exclusive KILL/NEW routines compile under TRAMPOLINE. `contains_naked_global` no longer in codegen/expressions.py.

---

## Phase 6: US3 — Subscript Parsing Consolidation (P2)  ⇄ PARALLEL with Phase 7

**Goal**: Unify 3 independent `_parse_subscripted_name` implementations and 13+ parenthesis-depth state machines into shared `core/parsing.py` and `core/tokenizer.py`.

**Independent Test**: `core/parsing.parse_subscripted_name('ARR(1,"A,B",3)')` returns `('ARR', ['1', '"A,B"', '3'])`. All 3 former call sites delegate to it. `split_at_toplevel` handles nested parens and quoted strings correctly.

**Files touched**: core/parsing.py (new), core/tokenizer.py (new), runtime/__init__.py, core/scope.py, core/indirection.py — NO overlap with Phase 7.

**Requires**: Phase 4 (US2) complete — both phases modify runtime/__init__.py.

- [ ] T031 [US3] Create src/m2py/core/parsing.py with parse_subscripted_name and canonicalize_subscript per contracts/module-contracts.md (C-03)
- [ ] T032 [P] [US3] Create src/m2py/core/tokenizer.py with split_at_toplevel per contracts/module-contracts.md (S-07)
- [ ] T033 [US3] Update src/m2py/runtime/__init__.py: replace _parse_subscripted_name (L106) with delegation to core/parsing.py; apply canonicalize_subscript where numeric conversion is needed (~20 call sites)
- [ ] T034 [US3] Update src/m2py/core/scope.py (_parse_subscripted_name at L429) and src/m2py/core/indirection.py (_parse_subscripted_name at L1352, _split_argument_list at L600) to delegate to core/parsing.py and core/tokenizer.py
- [ ] T035 [P] [US3] Add/Update tests in tests/unit/core/test_parsing.py and tests/unit/core/test_tokenizer.py
- [ ] T036 [US3] Run uv run pytest and verify zero failures

**Checkpoint**: `rg "_parse_subscripted_name" src/m2py/` shows only core/parsing.py definition and thin delegation wrappers (if any).

---

## Phase 7: US5 — ASG Statement Walker (P3)  ⇄ PARALLEL with Phase 6

**Goal**: Extend `MScope.walk_statements()` to handle else-scopes and migrate direct-iteration sites to use the shared walker.

**Independent Test**: `walk_statements()` on a routine with nested IF/ELSE/FOR/DO blocks visits every statement exactly once, including else-body statements.

**Files touched**: asg/elements.py, analysis/ consumers — NO overlap with Phase 6.

**Requires**: Phase 5 (US4) complete — both phases modify asg/elements.py and analysis/ files.

- [ ] T037 [US5] Audit and extend MScope.walk_statements (L74) in src/m2py/asg/elements.py to recurse into get_else_scope in addition to get_body_scope and get_then_scope (S-10)
- [ ] T038 [US5] Migrate direct scope.statements iteration sites (8 remaining per R-05) to walk_statements in analysis/ files where appropriate (S-10)
- [ ] T039 [P] [US5] Add/Update tests for walk_statements in tests/unit/asg/test_walker.py
- [ ] T040 [US5] Run uv run pytest and verify zero failures

**Checkpoint**: `walk_statements()` covers then/else/body scopes. Direct `scope.statements` iteration is reduced.

---

## Phase 8: Polish & Cross-Cutting

**Requires**: All desired user story phases complete.

- [ ] T041 [P] Update documentation in quickstart.md, data-model.md, contracts/module-contracts.md to reflect final module structure
- [ ] T042 [P] Final constitution check: verify all 8 principles in plan.md
- [ ] T043 Run uv run pytest — final verification of zero failures/xfails/skips

---

## Phase Parallelism Guide

```
                    ┌─── Phase 4: US2 (runtime) ──→ Phase 6: US3 (parsing) ──┐
After Phase 3 ─────┤                                                         ├──→ Phase 8: Polish
(US1 complete)      └─── Phase 5: US4 (analysis) ──→ Phase 7: US5 (walker) ──┘
```

### Parallel Pairs

| Wave | Lane A (core/runtime) | Lane B (analysis/ASG) | Shared Files |
|------|----------------------|----------------------|--------------|
| **Wave 1** | Phase 4: US2 | Phase 5: US4 | None — fully parallel ✅ |
| **Wave 2** | Phase 6: US3 | Phase 7: US5 | None — fully parallel ✅ |

### Why These Pairings

- **Phase 4 ∥ Phase 5**: US2 touches `runtime/`, `core/values.py`, `core/names.py`. US4 touches `analysis/`, `asg/`, `codegen/`. Zero file overlap.
- **Phase 6 ∥ Phase 7**: US3 touches `core/parsing.py`, `core/tokenizer.py`, `runtime/__init__.py`, `core/scope.py`, `core/indirection.py`. US5 touches `asg/elements.py`, `analysis/` consumers. Zero file overlap.
- **Phase 6 after Phase 4**: Both modify `runtime/__init__.py` — US2's callback injection (T016) must land before US3's parse delegation (T033).
- **Phase 7 after Phase 5**: Both modify `asg/elements.py` and `analysis/` files — US4's flag additions (T020) and analysis changes (T024–T028) must land before US5's walker extension (T037) and migration (T038).

### Solo Developer Strategy

1. Complete Phase 4 (US2), then Phase 5 (US4) — or interleave since no file conflicts
2. Complete Phase 6 (US3), then Phase 7 (US5) — or interleave
3. Phase 8 (Polish)

### Two-Developer Strategy

- **Developer A** (core/runtime lane): Phase 4 → Phase 6
- **Developer B** (analysis/ASG lane): Phase 5 → Phase 7
- **Joint**: Phase 8

### Task-Level Parallel Opportunities

Within each phase, tasks marked [P] can run in parallel:
- Phase 4: T017, T018 can run in parallel (different files)
- Phase 5: T023 can run in parallel with T020–T022 (different files); T029 can run in parallel with other tasks
- Phase 6: T031, T032 can run in parallel (new files, no deps); T035 can run in parallel with T034
- Phase 7: T039 can run in parallel with T038
- Phase 8: T041, T042 can run in parallel

## Implementation Strategy
- MVP: User Story 1 (T007–T014) — ✅ COMPLETE
- Wave 1: US2 (P2) ∥ US4 (P3) — fix runtime independence + analysis cleanup
- Wave 2: US3 (P2) ∥ US5 (P3) — consolidate parsing + extend walker
- Final: Polish & verification
- Each user story is independently testable with its own checkpoint

---

**Total tasks**: 43
**Tasks per user story**:
- US1: 8 (complete)
- US2: 5
- US4: 11
- US3: 6
- US5: 4
- Setup/Foundational/Polish: 9

**Phase-level parallel opportunities**: 2 waves of 2 parallel phases each
**Task-level parallel opportunities**: 10+
**Independent test criteria**: Each phase has a checkpoint with specific verification commands
**MVP scope**: User Story 1 (T007–T014) — complete
**Format validation**: All tasks follow strict checklist format (checkbox, ID, labels, file paths)
