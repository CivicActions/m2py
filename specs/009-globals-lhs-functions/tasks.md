# Tasks: LHS Functions & Global Variables

**Input**: Design documents from `/specs/009-globals-lhs-functions/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Tests are included as this spec involves complex runtime behavior requiring validation.

**Organization**: Tasks grouped by user story. Stories 1-3 (P1) are MVP. Stories 4-8 can be delivered incrementally.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create new runtime modules and prepare codegen extension points

- [X] T001 Create `src/m2py/runtime/globals.py` with GlobalStorageBackend protocol stub
- [X] T002 [P] Create `src/m2py/runtime/helpers.py` with function stubs (m_set_piece, m_set_extract, m_data)
- [X] T003 [P] Add `data()` method to MArray class in `src/m2py/runtime/__init__.py`
- [X] T004 Update `src/m2py/runtime/__init__.py` exports to include new modules

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Complete GlobalStorageBackend and MArray.data() - required by ALL user stories

**⚠️ CRITICAL**: User stories 4-8 depend on globals infrastructure. Stories 1-3 can proceed with just MArray.

- [X] T005 Implement `MArray.data()` returning 0, 1, 10, or 11 in `src/m2py/runtime/__init__.py`
- [X] T006 Implement `InMemoryGlobalStorage` class in `src/m2py/runtime/globals.py`
- [X] T007 Add naked indicator tracking to InMemoryGlobalStorage (get/set/resolve methods)
- [X] T008 Add `globals` property to MUMPSRuntime in `src/m2py/runtime/__init__.py`
- [X] T009 Add environment variable config (`M2PY_GLOBAL_BACKEND`) for backend selection

**Checkpoint**: Foundation ready - GlobalStorageBackend works, MArray.data() returns correct codes

---

## Phase 3: User Story 1 - LHS $PIECE Assignment (Priority: P1) 🎯 MVP

**Goal**: `S $P(X,"^",2)="NEW"` modifies piece 2 of X in-place

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X="A^B^C" S $P(X,"^",2)="NEW" W X,! Q'` → `A^NEW^C`

### Tests for User Story 1

- [X] T010 [P] [US1] Create `tests/test_spec_009_lhs_piece.py` with 4 local-variable scenarios; scenario 5 (globals) tested after Phase 6

### Implementation for User Story 1

- [X] T011 [US1] Implement `m_set_piece()` helper in `src/m2py/runtime/helpers.py`
- [X] T012 [US1] Extend `_generate_set()` in `src/m2py/codegen/statements.py` to detect IntrinsicFunction target with name 'P'/'PIECE'
- [X] T013 [US1] Generate `m_set_piece()` call with getter/setter lambdas for local variables
- [X] T014 [US1] Add `m_set_piece` to generated code imports in `src/m2py/codegen/routine.py`

**Checkpoint**: `S $P(X,"^",2)="NEW"` works for local variables

---

## Phase 4: User Story 2 - LHS $EXTRACT Assignment (Priority: P1)

**Goal**: `S $E(X,2,3)="XX"` replaces characters 2-3 of X

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X="HELLO" S $E(X,2,3)="XX" W X,! Q'` → `HXXLO`

### Tests for User Story 2

- [X] T015 [P] [US2] Create `tests/test_spec_009_lhs_extract.py` with 5 acceptance scenarios from spec

### Implementation for User Story 2

- [X] T016 [US2] Implement `m_set_extract()` helper in `src/m2py/runtime/helpers.py`
- [X] T017 [US2] Extend `_generate_set()` in `src/m2py/codegen/statements.py` to detect IntrinsicFunction target with name 'E'/'EXTRACT'
- [X] T018 [US2] Generate `m_set_extract()` call with getter/setter lambdas
- [X] T019 [US2] Add `m_set_extract` to generated code imports

**Checkpoint**: `S $E(X,2,3)="XX"` works for local variables

---

## Phase 5: User Story 3 - Subscripted Local Variables (Priority: P1)

**Goal**: `S X(1,2)=5` and `W X(1,2)` work with MArray semantics

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X(1)=1 S X(1,2)=2 W X(1),"-",X(1,2),! Q'` → `1-2`

### Tests for User Story 3

- [X] T020 [P] [US3] Create `tests/test_spec_009_subscripted.py` with 5 acceptance scenarios from spec

### Implementation for User Story 3

- [X] T021 [US3] Modify `_generate_set()` to auto-vivify MArray for subscripted LocalVariable targets in `src/m2py/codegen/statements.py`
- [X] T022 [US3] Modify `generate_expr()` to handle subscripted LocalVariable reads in `src/m2py/codegen/expressions.py`
- [X] T023 [US3] Ensure undefined subscripted variables return empty string
- [X] T024 [US3] Add MArray import to generated code preamble

**Checkpoint**: Subscripted locals work with value+children semantics (MVP complete for local arrays!)

---

## Phase 6: User Story 4 - Global Variable SET/READ (Priority: P1)

**Goal**: `S ^G("a")=1 W ^G("a")` persists/reads via GlobalStorageBackend

**Independent Test**: `uv run python utils/validate.py --code 'TEST S ^G("a")=1 W ^G("a"),! Q'` → `1`

### Tests for User Story 4

- [X] T025 [P] [US4] Create `tests/test_spec_009_globals.py` with 5 acceptance scenarios from spec

### Implementation for User Story 4

- [X] T026 [US4] Extend `_generate_set()` to handle GlobalVariable targets → `_rt.globals.set()` in `src/m2py/codegen/statements.py`
- [X] T027 [US4] Extend `generate_expr()` to handle GlobalVariable reads → `_rt.globals.get()` in `src/m2py/codegen/expressions.py`
- [X] T028 [US4] Ensure undefined globals return empty string (not None)
- [X] T029 [US4] Support string subscripts in globals codegen

**Checkpoint**: Basic global SET/READ works with InMemoryGlobalStorage

---

## Phase 7: User Story 5 - Naked Global References (Priority: P2)

**Goal**: `S ^G(1)=1,^(2)=2` uses naked indicator to resolve `^(2)` to `^G(2)`

**Independent Test**: `uv run python utils/validate.py --code 'TEST S ^G(1)=1,^(2)=2 W ^G(2),! Q'` → `2`

### Tests for User Story 5

- [X] T030 [P] [US5] Create `tests/unit/codegen/test_spec_009_naked.py` with 10 tests (5 acceptance scenarios + 5 edge cases)

### Implementation for User Story 5

- [X] T031 [US5] Extend `_generate_set()` to handle NakedGlobal targets → `resolve_naked` + `set` in `src/m2py/codegen/statements.py`
- [X] T032 [US5] Extend `generate_expr()` to handle NakedGlobal reads → `resolve_naked` + `get` in `src/m2py/codegen/expressions.py`
- [X] T033 [US5] Backend already has `resolve_naked()` in InMemoryGlobalStorage (codegen uses `_rt.globals.resolve_naked()`)
- [X] T034 [US5] NAKEDERR already implemented in InMemoryGlobalStorage.resolve_naked()

**Checkpoint**: Naked references work, tracking last global access

---

## Phase 8: User Story 6 - $DATA Function (Priority: P2) ✅ COMPLETE

**Goal**: `W $D(X)` returns 0, 1, 10, or 11 based on value/children state

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X(1)=1 W $D(X),"-",$D(X(1)),! Q'` → `10-1`

### Tests for User Story 6

- [X] T035 [P] [US6] Create `tests/test_spec_009_data.py` with 5 acceptance scenarios from spec

### Implementation for User Story 6

- [X] T036 [US6] Implement `m_data()` for local arrays in `src/m2py/runtime/helpers.py`
- [X] T037 [US6] Implement `m_data_global()` for globals in `src/m2py/runtime/helpers.py`
- [X] T038 [US6] Extend `generate_expr()` to handle IntrinsicFunction 'D'/'DATA' → `m_data()` or `m_data_global()` in `src/m2py/codegen/expressions.py`
- [X] T039 [US6] Add `m_data`, `m_data_global` to generated code imports

**Checkpoint**: $DATA returns correct existence codes for all variable types

---

## Phase 9: User Story 7 - Backend Configuration (Priority: P2) ✅ COMPLETE

**Goal**: `M2PY_GLOBAL_BACKEND=inmemory` selects storage backend

**Independent Test**: Set env var, verify correct backend instantiated

### Tests for User Story 7

- [X] T040 [P] [US7] Create `tests/test_spec_009_backend.py` with 4 acceptance scenarios from spec

### Implementation for User Story 7

- [X] T041 [US7] Add `get_global_storage()` factory function in `src/m2py/runtime/globals.py` (already existed)
- [X] T042 [US7] Read `M2PY_GLOBAL_BACKEND` env var with 'inmemory' default (already existed)
- [X] T043 [US7] Add stub `YottaDBGlobalStorage` class (ImportError raised by factory function)
- [X] T044 [US7] Add stub `IRISGlobalStorage` class (ImportError raised by factory function)

**Additional**: Added `global_storage` parameter to `MUMPSRuntime.__init__()` for programmatic API

**Checkpoint**: Backend selection works via environment or programmatic API

---

## Phase 10: User Story 8 - KILL Command (Priority: P3) ✅

**Goal**: `K X(1)` deletes node and all descendants

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X=1 S X(1)=2 K X(1) W $D(X),"-",$D(X(1)) Q'` → `1-0`

### Tests for User Story 8

- [X] T045 [P] [US8] Create `tests/test_spec_009_kill.py` with 10 test cases (4 acceptance scenarios + edge cases)

### Implementation for User Story 8

- [X] T046 [US8] Add `_generate_kill()` handler in `src/m2py/codegen/statements.py`
- [X] T047 [US8] Handle MKillStatement with LocalVariable target → `MArray.kill()` / `_scope.pop()`
- [X] T048 [US8] Handle MKillStatement with GlobalVariable target → `_rt.globals.kill()`
- [X] T049 [US8] MArray.kill() already present in runtime/__init__.py (line 231)

**Checkpoint**: KILL works for locals and globals, removing node + descendants ✅

---

## Phase 11: Polish & Cross-Cutting Concerns ✅

**Purpose**: Integration, documentation, final validation

- [X] T050 [P] Update `docs/coverage-matrix.md` with spec 009 features (auto-generated by rebuild_docs.py)
- [X] T051 [P] Run all acceptance scenarios from quickstart.md via validate.py (7/7 pass)
- [X] T052 Run full test suite: `uv run pytest tests/test_spec_009*.py -v` (83 tests pass)
- [X] T053 Verify generated Python passes `ast.parse()` for all scenarios (7/7 pass)
- [X] T054 Performance check: tests complete in 1.1s (well under 5s limit)

---

## Phase 12: Gap Remediation

**Purpose**: Address gaps identified in spec review - missing tests, incomplete protocol, edge case validation

### Missing Test Coverage

- [X] T055 [P] [US1] Add test for LHS $PIECE on global variables in `tests/unit/codegen/test_spec_009_lhs_piece.py`: `S $P(^G,"^",2)="B" W ^G` → `^B`
- [X] T056 [P] [US2] Add test for LHS $EXTRACT on global variables in `tests/unit/codegen/test_spec_009_lhs_extract.py`: `S $E(^G,1,3)="ABC" W ^G` → `ABC`
- [X] T057 [P] [US8] Add test for KILL with naked reference in `tests/unit/codegen/test_spec_009_kill.py`: `S ^G(1)=1,^(2)=2 K ^(1) W $D(^G(1)),$D(^G(2))` → `01`

### Edge Case Validation

- [X] T058 [P] [US1] Add input validation in `src/m2py/runtime/helpers.py` `m_set_piece()`: raise error for piece_from <= 0
- [X] T059 [P] [US1] Add tests for invalid piece numbers (0, negative) in `tests/unit/codegen/test_spec_009_lhs_piece.py`
- [X] T060 [P] [US2] Add behavior for start > end in `src/m2py/runtime/helpers.py` `m_set_extract()`: no modification per YDB
- [X] T061 [P] [US2] Add tests for $EXTRACT start > end edge case in `tests/unit/codegen/test_spec_009_lhs_extract.py`

### Protocol Completion

- [X] T062 Add `order()` method stub to `GlobalStorageBackend` protocol in `src/m2py/runtime/globals.py`
- [X] T063 Add `query()` method stub to `GlobalStorageBackend` protocol in `src/m2py/runtime/globals.py`
- [X] T064 Add `incr()` method stub to `GlobalStorageBackend` protocol in `src/m2py/runtime/globals.py`
- [X] T065 Add `kill_node()` method stub to `GlobalStorageBackend` protocol in `src/m2py/runtime/globals.py`
- [X] T066 Implement `order()`, `query()`, `incr()`, `kill_node()` stubs in `InMemoryGlobalStorage` class

### Backend Stub Classes

- [X] T067 [P] Create `YottaDBGlobalStorage` stub class (not just factory ImportError) in `src/m2py/runtime/globals.py` per spec
- [X] T068 [P] Create `IRISGlobalStorage` stub class with connection params in `src/m2py/runtime/globals.py` per spec

### Quality

- [X] T069 Increase test coverage to ≥85% (currently 88%) - added tests for new protocol methods

**Checkpoint**: All spec requirements addressed, protocol complete, edge cases validated

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories needing globals
- **Phases 3-5 (US1-3)**: Depend on Phase 1 only (MArray) - can start in parallel
- **Phases 6-10 (US4-8)**: Depend on Phase 2 (globals infrastructure)
- **Phase 11 (Polish)**: Depends on all desired user stories being complete
- **Phase 12 (Gap Remediation)**: Depends on Phase 11 - addresses gaps found in spec review

### User Story Dependencies

| Story | Priority | Depends On | Independent Test |
|-------|----------|------------|------------------|
| US1 - LHS $PIECE | P1 | Phase 1 | ✅ Local vars only |
| US2 - LHS $EXTRACT | P1 | Phase 1 | ✅ Local vars only |
| US3 - Subscripted Locals | P1 | Phase 1 | ✅ Local vars only |
| US4 - Globals SET/READ | P1 | Phase 2 | ✅ InMemory backend |
| US5 - Naked References | P2 | US4 | ✅ After global access |
| US6 - $DATA | P2 | US3, US4 | ✅ Any variable type |
| US7 - Backend Config | P2 | Phase 2 | ✅ Env var check |
| US8 - KILL | P3 | US3, US4 | ✅ After SET |

### Parallel Opportunities

**Within Phase 1** (all can run in parallel):
- T001, T002, T003 create independent files

**User Stories 1-3** (P1 stories can run in parallel after Phase 1):
- US1 (LHS $PIECE), US2 (LHS $EXTRACT), US3 (Subscripted) are independent

**User Stories 4-8** (after Phase 2, can run in parallel):
- US4 must complete before US5 (naked needs globals)
- US6, US7, US8 can run in parallel with each other

---

## MVP Scope

**Minimum Viable Product**: Complete Phases 1-5 (User Stories 1-3)

This delivers:
- ✅ LHS $PIECE assignment
- ✅ LHS $EXTRACT assignment  
- ✅ Subscripted local variables with MArray

**Test MVP**: 
```bash
uv run pytest tests/test_spec_009_lhs_piece.py tests/test_spec_009_lhs_extract.py tests/test_spec_009_subscripted.py -v
```

---

## Task Count Summary

| Phase | Tasks | Parallel |
|-------|-------|----------|
| Setup | 4 | 3 |
| Foundational | 5 | 0 |
| US1 - LHS $PIECE | 5 | 1 |
| US2 - LHS $EXTRACT | 5 | 1 |
| US3 - Subscripted | 5 | 1 |
| US4 - Globals | 5 | 1 |
| US5 - Naked | 5 | 1 |
| US6 - $DATA | 5 | 1 |
| US7 - Backend | 5 | 1 |
| US8 - KILL | 5 | 1 |
| Polish | 5 | 2 |
| Gap Remediation | 15 | 9 |
| **Total** | **69** | **22** |
