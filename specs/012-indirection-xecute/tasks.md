# Tasks: Indirection & XECUTE Runtime

**Input**: Design documents from `/specs/012-indirection-xecute/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/runtime-api.md ✅

**Tests**: Unit tests included per codegen-plan.md test strategy (embedded pytest tests).

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1-US8)
- Setup/Foundational phases: NO story label
- File paths are absolute from repository root

---

## Phase 1: Setup (Runtime Infrastructure)

**Purpose**: Create runtime foundation for indirection and XECUTE support

- [ ] T001 [P] Add `IndirectionError` exception class in src/m2py/runtime/__init__.py
- [ ] T002 [P] Add `CallTarget` named tuple in src/m2py/runtime/__init__.py  
- [ ] T003 [P] Create src/m2py/codegen/indirection.py module with empty placeholder functions
- [ ] T004 [P] Create tests/unit/codegen/s7_expressions/test_s7_3_indirection.py with test class stubs
- [ ] T005 [P] Create tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py with test class stubs
- [ ] T006 [P] Create tests/unit/cross_cutting/test_indirection.py with test class stubs

---

## Phase 2: Foundational (Core Runtime Methods)

**Purpose**: Implement core runtime methods that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Implement `MUMPSRuntime.get_var(name, _scope)` in src/m2py/runtime/__init__.py
- [ ] T008 Implement `MUMPSRuntime.set_var(name, value, _scope)` in src/m2py/runtime/__init__.py
- [ ] T009 Implement `MUMPSRuntime.resolve_indirection(expr, levels, _scope)` in src/m2py/runtime/__init__.py
- [ ] T010 Implement `MUMPSRuntime.parse_call_target(target_str)` in src/m2py/runtime/__init__.py
- [ ] T011 Implement `MUMPSRuntime.execute(mumps_code, _scope)` in src/m2py/runtime/__init__.py
- [ ] T012 Add `_is_valid_varname(name)` helper in src/m2py/runtime/__init__.py
- [ ] T013 Unit tests for foundational runtime methods in tests/unit/runtime/test_indirection_runtime.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Name Indirection (Priority: P1) 🎯 MVP

**Goal**: Support `@VAR` for dynamic variable read/write

**Independent Test**: `S X="VAR",@X=1` sets VAR=1; `S X="VAR",VAR=5,Y=@X` sets Y=5

### Implementation for User Story 1

- [ ] T014 [P] [US1] Implement `generate_name_indirection()` in src/m2py/codegen/indirection.py
- [ ] T015 [P] [US1] Implement `generate_name_indirection_write()` in src/m2py/codegen/indirection.py
- [ ] T016 [US1] Extend `generate_expr()` in src/m2py/codegen/expressions.py to handle MIndirection with NAME type
- [ ] T017 [US1] Extend SET codegen in src/m2py/codegen/statements.py for indirection targets
- [ ] T018 [US1] Implement multi-level indirection (`@@VAR`, `@@@VAR`) in generate_name_indirection()
- [ ] T019 [US1] Implement name+subscript syntax (`@NAME@(1,2)`) in generate_name_indirection()
- [ ] T020 [US1] Unit tests for name indirection read in tests/unit/codegen/s7_expressions/test_s7_3_indirection.py
- [ ] T021 [US1] Unit tests for name indirection write in tests/unit/codegen/s7_expressions/test_s7_3_indirection.py
- [ ] T022 [US1] Unit tests for multi-level indirection in tests/unit/codegen/s7_expressions/test_s7_3_indirection.py
- [ ] T023 [US1] Integration test: `S X="VAR",@X=1 W VAR` equals 1 in tests/unit/cross_cutting/test_indirection.py

**Checkpoint**: Name indirection fully functional - `@X` works for read and write

---

## Phase 4: User Story 2 - XECUTE with Constant Strings (Priority: P1) 🎯 MVP

**Goal**: Support `X "S X=1"` with constant string optimization (inline generated Python)

**Independent Test**: `X "S X=1"` sets X=1; `X "W 42,!"` outputs 42

### Implementation for User Story 2

- [ ] T024 [P] [US2] Implement `generate_xecute_constant()` in src/m2py/codegen/statements.py
- [ ] T025 [US2] Extend statement dispatch in src/m2py/codegen/statements.py for MXecuteStatement
- [ ] T026 [US2] Handle multiple XECUTE arguments (`X "S A=1","S B=2"`)
- [ ] T027 [US2] Handle postconditions (`X:cond code`)
- [ ] T028 [US2] Unit tests for constant XECUTE in tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py
- [ ] T029 [US2] Unit tests for multiple XECUTE args in tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py
- [ ] T030 [US2] Unit tests for XECUTE postconditions in tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py
- [ ] T031 [US2] Integration test: constant XECUTE produces readable inlined Python

**Checkpoint**: XECUTE with constant strings works with inline optimization

---

## Phase 5: User Story 3 - XECUTE with Dynamic Code (Priority: P2)

**Goal**: Support `S CODE="W 42" X CODE` via runtime.execute()

**Independent Test**: `S CODE="W 42,!" X CODE` outputs 42

### Implementation for User Story 3

- [ ] T032 [P] [US3] Implement `generate_xecute_dynamic()` in src/m2py/codegen/statements.py
- [ ] T033 [US3] Integrate constant vs dynamic XECUTE detection in statement generator
- [ ] T034 [US3] Implement scope sharing between caller and XECUTEd code
- [ ] T035 [US3] Unit tests for dynamic XECUTE in tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py
- [ ] T036 [US3] Unit tests for scope access from XECUTEd code in tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py
- [ ] T037 [US3] Integration test: `S OUTER=10 X "S INNER=OUTER+1"` sets INNER=11

**Checkpoint**: Dynamic XECUTE works with full scope access

---

## Phase 6: User Story 4 - XECUTE $TEST Semantics (Priority: P2)

**Goal**: XECUTE does NOT stack $TEST (mutations visible to caller)

**Independent Test**: `I 1=1 X "I 0=1" E W "ELSE"` outputs ELSE

### Implementation for User Story 4

- [ ] T038 [US4] Verify XECUTE codegen does NOT wrap with $TEST save/restore
- [ ] T039 [US4] Unit test: $TEST mutation in XECUTE visible to caller in tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py
- [ ] T040 [US4] Unit test: ELSE after XECUTE sees modified $TEST
- [ ] T041 [US4] Integration test: `I 1=1 X "I 0=1" E W "ELSE"` outputs ELSE

**Checkpoint**: $TEST semantics correct for XECUTE

---

## Phase 7: User Story 5 - Indirect DO (Priority: P2)

**Goal**: Support `D @CMD` for dynamic subroutine dispatch

**Independent Test**: `S CMD="LABEL" D @CMD` calls LABEL

### Implementation for User Story 5

- [ ] T042 [P] [US5] Implement `generate_indirect_do()` in src/m2py/codegen/indirection.py
- [ ] T043 [US5] Extend DO codegen in src/m2py/codegen/statements.py for indirect targets
- [ ] T044 [US5] Handle partial indirection (`D LABEL^@RTN`, `D @LBL^@RTN`)
- [ ] T045 [US5] Handle indirect DO with offset (`D @CMD+5`)
- [ ] T046 [US5] Unit tests for indirect DO in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [ ] T047 [US5] Unit tests for partial indirection in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [ ] T048 [US5] Integration test: `S CMD="LABEL" D @CMD` calls LABEL

**Checkpoint**: Indirect DO works for all patterns

---

## Phase 8: User Story 6 - Indirect GOTO (Priority: P2)

**Goal**: Support `G @TARGET` for dynamic control flow transfer

**Independent Test**: `S TARGET="DONE" G @TARGET` transfers to DONE

### Implementation for User Story 6

- [ ] T049 [P] [US6] Implement `generate_indirect_goto()` in src/m2py/codegen/indirection.py
- [ ] T050 [US6] Extend GOTO codegen in src/m2py/codegen/statements.py for indirect targets
- [ ] T051 [US6] Handle partial indirection (`G LABEL^@RTN`)
- [ ] T052 [US6] Handle indirect GOTO with offset (`G @TARGET+5`)
- [ ] T053 [US6] Unit tests for indirect GOTO in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py
- [ ] T054 [US6] Integration test: `S TARGET="DONE" G @TARGET` skips intervening code

**Checkpoint**: Indirect GOTO works for all patterns

---

## Phase 9: User Story 7 - Argument Indirection (Priority: P3)

**Goal**: Support `S @"X=1"` for SET argument indirection

**Independent Test**: `S A="X=1" S @A` sets X=1

### Implementation for User Story 7

- [ ] T055 [P] [US7] Implement `generate_argument_indirection()` in src/m2py/codegen/indirection.py
- [ ] T056 [US7] Extend SET codegen for argument indirection patterns
- [ ] T057 [US7] Handle nested argument indirection (`S @A` where A contains `"@B"`)
- [ ] T058 [US7] Unit tests for SET argument indirection in tests/unit/codegen/s8_commands/test_s8_2_18_set.py
- [ ] T059 [US7] Integration test: `S A="X=1",B="Y=2" S @A,@B` sets X=1 and Y=2

**Checkpoint**: SET argument indirection works

---

## Phase 10: User Story 8 - Pattern Indirection (Priority: P3)

**Goal**: Support `X?@PAT` for dynamic pattern matching

**Independent Test**: `S PAT="1N.N" I "123"?@PAT W "MATCH"` outputs MATCH

### Implementation for User Story 8

- [ ] T060 [P] [US8] Implement `generate_pattern_indirection()` in src/m2py/codegen/indirection.py
- [ ] T061 [US8] Add `compile_pattern_indirect()` to src/m2py/runtime/__init__.py
- [ ] T062 [US8] Extend pattern match codegen for indirect patterns
- [ ] T063 [US8] Unit tests for pattern indirection in tests/unit/codegen/s7_expressions/test_s7_3_indirection.py
- [ ] T064 [US8] Integration test: `S PAT="1N.N" I "123"?@PAT W "MATCH"` outputs MATCH

**Checkpoint**: Pattern indirection works

---

## Phase 11: Edge Cases & Error Handling

**Purpose**: Handle error conditions and edge cases from spec

- [ ] T065 [P] Implement error handling for undefined indirection source (`@UNDEF`)
- [ ] T066 [P] Implement error handling for invalid variable names (`@"123INVALID"`)
- [ ] T067 [P] Implement error handling for XECUTE syntax errors with context
- [ ] T068 [P] Implement FOR loop variable indirection (`F @A=1:1:10`)
- [ ] T069 [P] Implement indirection in KILL (`K @X`)
- [ ] T070 [P] Implement indirection in NEW (`N @X`)
- [ ] T071 Unit tests for edge cases in tests/unit/cross_cutting/test_indirection.py
- [ ] T072 Unit tests for error messages include variable name/value

**Checkpoint**: All edge cases handled with clear error messages

---

## Phase 12: Polish & Integration Tests

**Purpose**: MUGJ validation and documentation

- [ ] T073 [P] Run MUGJ V1IDNM* tests and fix failures
- [ ] T074 [P] Run MUGJ V1IDDO* tests and fix failures
- [ ] T075 [P] Run MUGJ V1IDGO* tests and fix failures
- [ ] T076 [P] Run MUGJ V1XECA*, V1XECB* tests and fix failures
- [ ] T077 Update docs/examples/indirection.md with codegen examples
- [ ] T078 Validate quickstart.md examples all work
- [ ] T079 Run full test suite and ensure ≥85% coverage

**Checkpoint**: MUGJ suites pass, documentation complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phases 3-10 (User Stories)**: All depend on Phase 2 completion
  - P1 stories (US1, US2) should complete first
  - P2 stories (US3-US6) can start after P1 complete
  - P3 stories (US7-US8) can start after P2 complete
- **Phase 11 (Edge Cases)**: Can start after Phase 3 (US1) complete
- **Phase 12 (Polish)**: Depends on all user stories complete

### User Story Dependencies

| Story | Priority | Depends On |
|-------|----------|------------|
| US1 - Name Indirection | P1 | Foundational only |
| US2 - XECUTE Constant | P1 | Foundational only |
| US3 - XECUTE Dynamic | P2 | US2 (constant XECUTE) |
| US4 - XECUTE $TEST | P2 | US2 or US3 |
| US5 - Indirect DO | P2 | US1 (name indirection) |
| US6 - Indirect GOTO | P2 | US1 (name indirection) |
| US7 - Argument Indirection | P3 | US1 (name indirection) |
| US8 - Pattern Indirection | P3 | US1 (name indirection) |

### Parallel Opportunities

**Within Phase 1** (all [P]):
- T001-T006 can all run in parallel (different files)

**Within Phase 2**:
- T007-T012 are sequential (same file, dependent methods)
- T013 (tests) after T007-T012

**Within User Stories**:
- T014, T015 can run in parallel (different functions)
- T020-T022 tests can run in parallel
- T024 can run in parallel with US1 implementation

**Across User Stories**:
- US1 and US2 can run in parallel (both P1, independent)
- US5 and US6 can run in parallel (both P2, similar patterns)
- US7 and US8 can run in parallel (both P3, independent)

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational  
3. Complete Phase 3: US1 - Name Indirection
4. Complete Phase 4: US2 - XECUTE Constant
5. **STOP and VALIDATE**: Test basic indirection and XECUTE work
6. Deploy/demo if ready

### Full Feature Delivery

1. MVP (US1 + US2) → Basic indirection and XECUTE
2. Add US3 + US4 → Full XECUTE support
3. Add US5 + US6 → Indirect control flow
4. Add US7 + US8 → Advanced indirection patterns
5. Edge cases + MUGJ validation → Production ready

---

## Summary

| Metric | Value |
|--------|-------|
| Total Tasks | 79 |
| Phase 1 (Setup) | 6 tasks |
| Phase 2 (Foundational) | 7 tasks |
| User Story Tasks | 51 tasks |
| Edge Cases | 8 tasks |
| Polish | 7 tasks |
| Parallel Opportunities | ~40% of tasks |

### Tasks by User Story

| Story | Priority | Tasks |
|-------|----------|-------|
| US1 - Name Indirection | P1 | 10 |
| US2 - XECUTE Constant | P1 | 8 |
| US3 - XECUTE Dynamic | P2 | 6 |
| US4 - XECUTE $TEST | P2 | 4 |
| US5 - Indirect DO | P2 | 7 |
| US6 - Indirect GOTO | P2 | 6 |
| US7 - Argument Indirection | P3 | 5 |
| US8 - Pattern Indirection | P3 | 5 |

### Suggested MVP Scope

**US1 + US2** (18 tasks) delivers:
- Name indirection read/write (`@X`)
- Multi-level indirection (`@@X`)
- XECUTE with constant strings (inlined)
- Basic XECUTE postconditions

This covers the most common VistA indirection patterns.
