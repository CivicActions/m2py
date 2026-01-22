# Tasks: Functional Test Suite

**Input**: Design documents from `/specs/016-functional-test-suite/`
**Prerequisites**: plan.md, spec.md, research.md, quickstart.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create functional test infrastructure and fixtures

- [ ] T001 Create functional test conftest with core fixtures in tests/functional/conftest.py
- [ ] T002 [P] Implement outref normalization function (strip YDB markers, preamble, suspend blocks) in tests/functional/conftest.py
- [ ] T003 [P] Implement test driver parser (extract routine sequence from u_inref/*.csh) in tests/functional/conftest.py
- [ ] T004 [P] Implement MUMPS execution helper using generate_python() and MUMPSRuntime.execute() in tests/functional/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core test runner infrastructure that all suites depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T005 Create base test class/fixtures for parametrized suite execution in tests/functional/conftest.py
- [ ] T006 Implement output comparison with clear diff reporting in tests/functional/conftest.py
- [ ] T007 Add timeout handling for runaway tests (default 30s) in tests/functional/conftest.py
- [ ] T008 Create xfail helper that references limitations.py IDs in tests/functional/conftest.py

**Checkpoint**: Foundation ready - test suite implementation can begin

---

## Phase 3: User Story 1 - Run Complete Test Suite (Priority: P1) 🎯 MVP

**Goal**: Execute full mugj test suite via m2py and compare against outref

**Independent Test**: Run `uv run pytest tests/functional/test_mugj.py -v` and verify tests execute with pass/fail/xfail results

### Implementation for User Story 1

- [ ] T009 [US1] Create mugj test runner in tests/functional/test_mugj.py
- [ ] T010 [US1] Parse mugj.csh driver to extract routine execution order
- [ ] T011 [US1] Implement parametrized tests for each mugj routine
- [ ] T012 [US1] Load and normalize mugj outref content
- [ ] T013 [US1] Execute routines in driver order, concatenating output
- [ ] T014 [US1] Compare m2py output against normalized outref with diff on failure
- [ ] T015 [US1] Verify end-to-end execution: `uv run pytest tests/functional/test_mugj.py -v`

**Checkpoint**: mugj suite runs with clear pass/fail/xfail results

---

## Phase 4: User Story 2 - Run Individual Test Suites (Priority: P2)

**Goal**: Enable running specific suites independently (basic, mvts, etc.)

**Independent Test**: Run `uv run pytest tests/functional/test_basic.py -v` and see only basic tests

### Implementation for User Story 2

- [ ] T016 [P] [US2] Create basic suite test runner in tests/functional/test_basic.py
- [ ] T017 [P] [US2] Create mvts suite test runner in tests/functional/test_mvts.py (if outref exists)
- [ ] T018 [P] [US2] Create merge suite test runner in tests/functional/test_merge.py (if outref exists)
- [ ] T019 [US2] Add pytest markers for suite selection (e.g., @pytest.mark.mugj, @pytest.mark.basic)
- [ ] T020 [US2] Update tests/functional/conftest.py with suite-specific fixture variants
- [ ] T021 [US2] Verify suite isolation: `uv run pytest tests/functional/ -k basic -v`

**Checkpoint**: Individual suites can run independently via pytest selection

---

## Phase 5: User Story 4 - Handle Known Limitations Gracefully (Priority: P2)

**Goal**: Mark tests for known m2py limitations as xfail with limitation IDs

**Independent Test**: Run a test for VIEW command and verify xfail with LIM-005 reference

### Implementation for User Story 4

- [ ] T022 [US4] Create limitation mapping dict in tests/functional/conftest.py (routine → limitation ID)
- [ ] T023 [US4] Implement xfail decorator factory using limitations.py data
- [ ] T024 [US4] Apply xfail markers to routines using VIEW keywords (LIM-005)
- [ ] T025 [US4] Apply xfail markers to routines using MWAPI SSVNs (LIM-003)
- [ ] T026 [US4] Apply xfail markers to routines using unknown Z-extensions (LIM-012)
- [ ] T027 [US4] Apply xfail markers to routines using YDB-specific Z-commands (LIM-015)
- [ ] T028 [US4] Verify xfail reporting: `uv run pytest tests/functional/ --runxfail -v`

**Checkpoint**: Known limitations show as xfail with clear reason referencing limitation ID

---

## Phase 6: User Story 3 - Clean Legacy Integration Tests (Priority: P3)

**Goal**: Remove obsolete parsing-focused tests from tests/integration/

**Independent Test**: Verify tests/integration/ no longer contains test_ydb_suites.py or test_mugj.py

### Implementation for User Story 3

- [ ] T029 [US3] Review tests/integration/test_external_calls.py for useful patterns to preserve
- [ ] T030 [US3] Review tests/integration/test_indirection_edge_cases.py for useful patterns to preserve
- [ ] T031 [US3] Delete tests/integration/test_ydb_suites.py (obsolete parsing tests)
- [ ] T032 [US3] Delete tests/integration/test_mugj.py (obsolete ASG structure tests)
- [ ] T033 [US3] Verify remaining tests still pass: `uv run pytest tests/integration/ -v`

**Checkpoint**: Legacy parsing tests removed, useful integration tests preserved

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final touches

- [ ] T034 [P] Update quickstart.md with actual command outputs
- [ ] T035 [P] Add docstrings to all fixtures in tests/functional/conftest.py
- [ ] T036 Run full test suite and document pass/fail/xfail counts
- [ ] T037 Verify performance: full suite under 5 minutes
- [ ] T038 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - US1 (P1) → US2 (P2) → US4 (P2) → US3 (P3) is recommended sequential order
  - US2 and US4 can run in parallel after US1
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - Core mugj implementation
- **User Story 2 (P2)**: Depends on US1 patterns - Extends to other suites
- **User Story 4 (P2)**: Can start after US1 - Adds xfail markers to existing tests
- **User Story 3 (P3)**: Independent cleanup - Can start after US1 validates new approach works

### Within Each Phase

- Tasks marked [P] can run in parallel
- Core implementation before integration
- Verify checkpoint before moving to next phase

### Parallel Opportunities

**Phase 1 (Setup):**
```
T001 (conftest) → T002, T003, T004 can run in parallel
```

**Phase 4 (US2):**
```
T016, T017, T018 can run in parallel (different test files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T008)
3. Complete Phase 3: User Story 1 (T009-T015)
4. **STOP and VALIDATE**: Run `uv run pytest tests/functional/test_mugj.py -v`
5. Assess pass/fail/xfail ratio before expanding

### Incremental Delivery

1. Setup + Foundational → Test infrastructure ready
2. User Story 1 → mugj suite working → Validate MVP
3. User Story 2 → Multiple suites → Broader coverage
4. User Story 4 → xfail markers → Cleaner results
5. User Story 3 → Cleanup → Technical debt removed

---

## Notes

- All file paths are relative to repository root
- Use `uv run pytest` exclusively (per constitution)
- outref normalization is critical - test thoroughly with edge cases
- Driver parsing must handle commented-out tests (already excluded in mugj.csh)
- xfail markers should use `strict=False` to surface unexpected passes
