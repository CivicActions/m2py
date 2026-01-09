# Tasks: Minimal Control Flow Foundation

**Input**: Design documents from `/specs/004-codegen-foundation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: TDD approach - tests written first and must FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup

**Purpose**: Create module structure and project scaffolding

- [ ] T001 Create codegen module structure in src/m2py/codegen/__init__.py
- [ ] T002 [P] Create runtime module structure in src/m2py/runtime/__init__.py
- [ ] T003 [P] Create helpers module skeleton in src/m2py/codegen/helpers.py
- [ ] T004 [P] Create names module skeleton in src/m2py/codegen/names.py
- [ ] T005 [P] Create runtime class skeleton in src/m2py/runtime/runtime.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Implement MUMPSRuntime.get() returning "" for undefined in src/m2py/runtime/runtime.py
- [ ] T007 Implement MUMPSRuntime.set() with string coercion in src/m2py/runtime/runtime.py
- [ ] T008 Implement MUMPSRuntime.write() appending to output buffer in src/m2py/runtime/runtime.py
- [ ] T009 Implement ExecutionResult dataclass in src/m2py/runtime/runtime.py
- [ ] T010 Implement MUMPSRuntime.execute() running code and capturing output in src/m2py/runtime/runtime.py
- [ ] T011 [P] Export generate_python() stub in src/m2py/codegen/__init__.py

**Checkpoint**: Runtime foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Generate Valid Python from Basic MUMPS (Priority: P1) 🎯 MVP

**Goal**: Generated Python executes and produces correct output for basic MUMPS constructs (literals, variables, SET, WRITE, QUIT)

**Independent Test**: Execute `S X=5 W X Q` and verify output is "5"

### Tests for User Story 1

- [ ] T012 [P] [US1] Test m_num() numeric prefix extraction in tests/unit/codegen/s7_expressions/test_s7_1_1_values.py
- [ ] T013 [P] [US1] Test numeric literal codegen in tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py
- [ ] T014 [P] [US1] Test string literal codegen in tests/unit/codegen/s7_expressions/test_s7_1_4_literals.py
- [ ] T015 [P] [US1] Test local variable codegen in tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py
- [ ] T016 [P] [US1] Test SET command codegen in tests/unit/codegen/s8_commands/test_s8_2_18_set.py
- [ ] T017 [P] [US1] Test WRITE command codegen in tests/unit/codegen/s8_commands/test_s8_2_25_write.py
- [ ] T018 [P] [US1] Test QUIT command codegen in tests/unit/codegen/s8_commands/test_s8_2_16_quit.py
- [ ] T019 [P] [US1] Test arithmetic operators (+, -, *) codegen in tests/unit/codegen/s7_expressions/test_s7_2_operators.py
- [ ] T020 [P] [US1] Test left-to-right evaluation (2+3*4=20) in tests/unit/codegen/s7_expressions/test_s7_2_operators.py

### Implementation for User Story 1

- [ ] T021 [US1] Implement m_num() in src/m2py/codegen/helpers.py (FR-002)
- [ ] T022 [US1] Implement expression codegen for literals in src/m2py/codegen/expressions.py
- [ ] T023 [US1] Implement expression codegen for local variables in src/m2py/codegen/expressions.py
- [ ] T024 [US1] Implement expression codegen for arithmetic ops (+, -, *) in src/m2py/codegen/expressions.py
- [ ] T025 [US1] Implement SET statement codegen in src/m2py/codegen/statements.py (FR-006)
- [ ] T026 [US1] Implement WRITE statement codegen in src/m2py/codegen/statements.py (FR-007)
- [ ] T027 [US1] Implement QUIT statement codegen in src/m2py/codegen/statements.py (FR-008)
- [ ] T028 [US1] Implement routine-to-module codegen in src/m2py/codegen/routine.py (FR-001)
- [ ] T029 [US1] Wire generate_python() to parse, analyze, and generate in src/m2py/codegen/__init__.py (FR-005)

**Checkpoint**: `S X=5 W X Q` should produce output "5"

---

## Phase 4: User Story 2 - M Value Coercion Helpers (Priority: P1) 🎯 MVP

**Goal**: `m_num()`, `m_truth()`, `m_compare()` implement MUMPS coercion semantics

**Independent Test**: Verify `m_num("3A")` returns `3` and `m_truth("A3")` returns `False`

### Tests for User Story 2

- [ ] T030 [P] [US2] Test m_truth() boolean coercion in tests/unit/codegen/s7_expressions/test_s7_1_1_values.py
- [ ] T031 [P] [US2] Test m_compare() for =, <, > operators in tests/unit/codegen/s7_expressions/test_s7_1_1_values.py
- [ ] T032 [P] [US2] Test comparison operators codegen in tests/unit/codegen/s7_expressions/test_s7_2_operators.py

### Implementation for User Story 2

- [ ] T033 [US2] Implement m_truth() in src/m2py/codegen/helpers.py (FR-003)
- [ ] T034 [US2] Implement m_compare() in src/m2py/codegen/helpers.py (FR-004)
- [ ] T035 [US2] Implement comparison operator codegen (=, <, >) in src/m2py/codegen/expressions.py

**Checkpoint**: `W "3A"+0` outputs "3", `W 5<10` outputs "1"

---

## Phase 5: User Story 3 - IF/ELSE Control Flow (Priority: P2)

**Goal**: IF and ELSE statements generate correct Python conditionals using M truth evaluation

**Independent Test**: Execute `S X=5 I X>3 W "GT" Q` and verify output is "GT"

### Tests for User Story 3

- [ ] T036 [P] [US3] Test IF command codegen with comparison in tests/unit/codegen/s8_commands/test_s8_2_09_if.py
- [ ] T037 [P] [US3] Test ELSE command codegen in tests/unit/codegen/s8_commands/test_s8_2_04_else.py
- [ ] T038 [P] [US3] Test IF with string truth evaluation in tests/unit/codegen/s8_commands/test_s8_2_09_if.py

### Implementation for User Story 3

- [ ] T039 [US3] Implement IF statement codegen with m_truth() in src/m2py/codegen/statements.py (FR-009)
- [ ] T040 [US3] Implement ELSE statement codegen in src/m2py/codegen/statements.py (FR-010)

**Checkpoint**: `I "3A" W "T"` outputs "T", `I "A3" W "T" E W "F"` outputs "F"

---

## Phase 6: User Story 4 - FOR Loops with Literal Parameters (Priority: P2)

**Goal**: FOR loops with literal start:increment:stop generate correct Python loops

**Independent Test**: Execute `F I=1:1:3 W I` and verify output is "123"

### Tests for User Story 4

- [ ] T041 [P] [US4] Test bounded FOR codegen (F I=1:1:3) in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [ ] T042 [P] [US4] Test string-list FOR codegen (F I="A","B") in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [ ] T043 [P] [US4] Test negative increment FOR (F I=3:-1:1) in tests/unit/codegen/s8_commands/test_s8_2_05_for.py

### Implementation for User Story 4

- [ ] T044 [US4] Implement bounded FOR codegen in src/m2py/codegen/statements.py (FR-011)
- [ ] T045 [US4] Implement string-list FOR codegen in src/m2py/codegen/statements.py (FR-012)

**Checkpoint**: `F I=1:1:3 W I` outputs "123", `F I=3:-1:1 W I` outputs "321"

**Note**: Open-ended FOR (`F I=1:1`), argumentless FOR, and Q:cond move to Spec 005.

---

## Phase 7: User Story 5 - DO Subroutine Calls (Priority: P2)

**Goal**: DO calls labels as subroutines and returns correctly

**Independent Test**: Execute `D SUB W "After"` with `SUB W "Sub " Q` → output "Sub After"

### Tests for User Story 5

- [ ] T046 [P] [US5] Test DO label call codegen in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [ ] T047 [P] [US5] Test nested DO calls in tests/unit/codegen/s8_commands/test_s8_2_03_do.py

### Implementation for User Story 5

- [ ] T048 [US5] Implement DO label codegen as function call in src/m2py/codegen/statements.py (FR-013)
- [ ] T049 [US5] Ensure routine codegen generates callable label functions in src/m2py/codegen/routine.py

**Checkpoint**: Nested DO calls work correctly with proper return

---

## Phase 8: User Story 6 - Simple GOTO (Priority: P3)

**Goal**: GOTO to label targets transfers control within a routine

**Independent Test**: Execute `S X=1 G DONE S X=2` with `DONE W X Q` → output "1"

### Tests for User Story 6

- [ ] T050 [P] [US6] Test forward GOTO codegen in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py
- [ ] T051 [P] [US6] Test GOTO skips intermediate code in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py

### Implementation for User Story 6

- [ ] T052 [US6] Implement GOTO label codegen in src/m2py/codegen/statements.py (FR-014)
- [ ] T053 [US6] Integrate GOTO with routine structure in src/m2py/codegen/routine.py

**Checkpoint**: Forward GOTO skips intermediate code correctly

---

## Phase 9: User Story 7 - Name Translation (Priority: P3)

**Goal**: Labels and variables translated to valid Python identifiers preserving M semantics

**Independent Test**: Verify `%UTIL` → `_pct_UTIL`, `01` → `_n_01`, `for` → `_m_for`

### Tests for User Story 7

- [ ] T054 [P] [US7] Test %-prefix translation in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T055 [P] [US7] Test numeric label translation in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T056 [P] [US7] Test Python keyword translation in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T057 [P] [US7] Test case preservation (FOO ≠ foo) in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T058 [P] [US7] Test reverse translation in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T059 [P] [US7] Test injectivity (no collisions) in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py

### Implementation for User Story 7

- [ ] T060 [US7] Implement NameTranslator.translate() in src/m2py/codegen/names.py (FR-015, FR-016, FR-017)
- [ ] T061 [US7] Implement NameTranslator.reverse() in src/m2py/codegen/names.py
- [ ] T062 [US7] Add Python reserved words detection in src/m2py/codegen/names.py (FR-017a)
- [ ] T063 [US7] Integrate NameTranslator into codegen pipeline in src/m2py/codegen/routine.py

**Checkpoint**: Name translation is injective (SC-004)

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Improvements affecting multiple user stories

- [ ] T064 [P] Add docstrings and type hints to all public APIs
- [ ] T065 [P] Run quickstart.md validation - verify all examples work
- [ ] T066 Validate all 22 YDB reference outputs from spec.md pass
- [ ] T067 Run full test suite: `uv run pytest tests/unit/codegen/ -v`
- [ ] T068 [P] Update docs/codegen/index.md with Spec 004 implementation notes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1+2 (Phase 3+4)**: Core MVP - can be done sequentially
- **User Stories 3-7 (Phase 5-9)**: All depend on Phase 2; can proceed in priority order
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Foundation only - no story dependencies
- **US2 (P1)**: Foundation only - provides helpers used by US3+
- **US3 (P2)**: Depends on US2 (uses m_truth)
- **US4 (P2)**: Depends on US1 (basic codegen) - bounded/string-list FOR only
- **US5 (P2)**: Depends on US1 (basic codegen)
- **US6 (P3)**: Depends on US1 (basic codegen)
- **US7 (P3)**: Foundation only - integrates into all codegen

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Models/helpers before statements
- Statements before routine integration
- Story complete before moving to next priority

---

## Parallel Opportunities

### Phase 1: All tasks can run in parallel
```
T001 + T002 + T003 + T004 + T005
```

### Phase 3 (US1): Tests can run in parallel, then implementation
```
T012 + T013 + T014 + T015 + T016 + T017 + T018 + T019 + T020  # All tests
T021 → T022 → T023 → T024 → T025 → T026 → T027 → T028 → T029  # Sequential impl
```

### Different user stories can be worked on by different developers after Phase 2

---

## Implementation Strategy

### MVP First (User Stories 1 + 2)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 - Basic codegen
4. Complete Phase 4: US2 - Coercion helpers
5. **VALIDATE**: `S X=5 W X Q` outputs "5", coercion works
6. Deploy/demo if ready

### Incremental Delivery

1. Setup + Foundational → Runtime ready
2. Add US1 + US2 → Basic transpilation works (MVP!)
3. Add US3 → IF/ELSE works
4. Add US4 → FOR loops work
5. Add US5 + US6 → DO/GOTO work
6. Add US7 → Name translation complete

---

## Notes

- All tests use TDD: write test, verify it fails, implement, verify it passes
- Use `uv run pytest` for all test execution
- YDB Docker (`ydb:latest`) for reference output validation
- Commit after each completed task or logical group
- Stop at any checkpoint to validate story independently
