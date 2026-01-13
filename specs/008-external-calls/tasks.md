# Tasks: External Calls & Cross-Routine Infrastructure

**Spec**: 008-external-calls  
**Generated**: 2025-01-13

---

## Phase 1: Setup

**Purpose**: Create test fixtures and development infrastructure

- [X] T001 Create external call test fixtures directory at tests/fixtures/external/
- [X] T002 [P] Create ext1.m fixture with DO/GOTO calls in tests/fixtures/external/ext1.m
- [X] T003 [P] Create ext2.m fixture with helper labels in tests/fixtures/external/ext2.m
- [X] T004 [P] Create ext3.m fixture for $TEXT testing in tests/fixtures/external/ext3.m
- [X] T005 [P] Create circular.m fixture for circular call testing in tests/fixtures/external/circular.m
- [X] T006 Add pytest fixture for sys.path configuration (insert tests/fixtures/external/ into sys.path) in tests/conftest.py

**Checkpoint**: Test fixtures exist and can be used by subsequent phases

---

## Phase 2: Foundational (BLOCKS all user stories)

**Purpose**: Runtime infrastructure required by all user story implementations

### Runtime Additions

- [X] T007 Add GotoExternal exception class in src/m2py/runtime/__init__.py
- [X] T008 [P] Add LabelNotFoundError exception class in src/m2py/runtime/__init__.py
- [X] T009 Add _current_routine field to MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T010 Add _current_source_lines field to MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T011 Add _current_label_lines field to MUMPSRuntime in src/m2py/runtime/__init__.py
- [X] T012 Implement get_text() method in MUMPSRuntime in src/m2py/runtime/__init__.py

### Codegen Infrastructure

- [X] T013 Generate _source_lines module constant in src/m2py/codegen/routine.py
- [X] T014 [P] Generate _routine_name module constant in src/m2py/codegen/routine.py
- [X] T015 [P] Generate _label_lines mapping in src/m2py/codegen/routine.py
- [X] T016 Add context update prologue to generated label functions in src/m2py/codegen/routine.py

**Checkpoint**: Runtime exceptions, context fields, and module constants are generated for all routines

---

## Phase 3: User Story 1 - External DO Routine Call (Priority: P1)

**Goal**: Enable `D ^ROUTINE` to call entry label of pre-transpiled external routine

**Independent Test**: `EXT1 D ^ext2 Q` executes ext2's entry label and returns

### Implementation for User Story 1

- [X] T017 [US1] Verify parser already captures MCall.routine for external DO in src/m2py/asg/elements.py
- [X] T018 [US1] Update _generate_do() for D ^ROUTINE pattern in src/m2py/codegen/statements.py (L1333)
- [X] T019 [US1] Generate import statement for external routine in src/m2py/codegen/statements.py
- [X] T020 [US1] Generate ext2.ext2(_rt, _scope) call pattern in src/m2py/codegen/statements.py
- [X] T021 [US1] Add integration test for D ^ROUTINE in tests/integration/test_external_calls.py

**Checkpoint**: `D ^ROUTINE` works end-to-end with YDB-matching output

---

## Phase 4: User Story 2 - External DO Label Call (Priority: P1)

**Goal**: Enable `D LABEL^ROUTINE` to call specific label in external routine

**Independent Test**: `EXT1 D HELPER^ext2 Q` executes HELPER label and returns

### Implementation for User Story 2

- [X] T022 [US2] Update _generate_do() for D LABEL^ROUTINE pattern in src/m2py/codegen/statements.py
- [X] T023 [US2] Generate ext2.HELPER(_rt, _scope) call pattern in src/m2py/codegen/statements.py
- [X] T024 [US2] Handle D LABEL+N^ROUTINE using _label_lines and _line_map in src/m2py/codegen/statements.py
- [X] T025 [US2] Handle D +N^ROUTINE using _line_map in src/m2py/codegen/statements.py
- [X] T026 [US2] Generate LabelNotFoundError check for missing labels in src/m2py/codegen/statements.py
- [X] T027 [US2] Add integration test for D LABEL^ROUTINE in tests/integration/test_external_calls.py
- [X] T028 [US2] Add integration test for LabelNotFoundError in tests/integration/test_external_calls.py

**Checkpoint**: `D LABEL^ROUTINE` and offset variants work end-to-end

---

## Phase 5: User Story 4 - Cross-Routine Variable Visibility (Priority: P1)

**Goal**: Variables modified in external routine visible to caller (unless NEWed)

**Independent Test**: `EXT1 S X=1 D ^ext2 W X Q` shows ext2's modification to X

### Implementation for User Story 4

- [X] T029 [US4] Ensure _scope parameter is passed to all external DO calls in src/m2py/codegen/statements.py
- [X] T030 [US4] Ensure _scope initialization at entry points in src/m2py/codegen/routine.py
- [ ] T031 [US4] Verify NEW semantics work across routine boundaries (Spec 005 integration) - **DEFERRED: requires NEW command from Spec 005**
- [X] T032 [US4] Add integration test for cross-routine variable modification in tests/integration/test_external_calls.py
- [ ] T033 [US4] Add integration test for NEW hiding caller variables in tests/integration/test_external_calls.py - **DEFERRED: requires NEW command from Spec 005**

**Checkpoint**: Shared scope infrastructure works correctly across routine boundaries

---

## Phase 6: User Story 3 - External GOTO (Priority: P2)

**Goal**: Enable `G ^ROUTINE` and `G LABEL^ROUTINE` for permanent control transfer

**Independent Test**: `EXT1 G ^ext2 W "Never"` transfers to ext2, "Never" not printed

### Implementation for User Story 3

- [ ] T034 [US3] Update _generate_goto() for G ^ROUTINE pattern in src/m2py/codegen/statements.py (L1064)
- [ ] T035 [US3] Update _generate_goto() for G LABEL^ROUTINE pattern in src/m2py/codegen/statements.py
- [ ] T036 [US3] Generate raise GotoExternal(module, label) pattern in src/m2py/codegen/statements.py
- [ ] T037 [US3] Handle G LABEL+N^ROUTINE with offset parameter in src/m2py/codegen/statements.py
- [ ] T038 [US3] Handle G +N^ROUTINE with offset parameter in src/m2py/codegen/statements.py
- [ ] T039 [US3] Implement run_with_goto_support() runtime helper for GotoExternal dispatch in src/m2py/runtime/__init__.py
- [ ] T040 [US3] Generate trampoline call (run_with_goto_support) at entry points in src/m2py/codegen/routine.py
- [ ] T041 [US3] Add integration test for G ^ROUTINE in tests/integration/test_external_calls.py
- [ ] T042 [US3] Add integration test for G LABEL^ROUTINE in tests/integration/test_external_calls.py

**Checkpoint**: External GOTO works with proper stack unwinding

---

## Phase 7: User Story 5 - External Extrinsic Function (Priority: P2)

**Goal**: Enable `$$FUNC^ROUTINE(args)` to call and return value from external routine

**Independent Test**: `EXT1 S X=$$ADD^ext2(3,5) W X Q` outputs 8

### Implementation for User Story 5

- [ ] T043 [US5] Update _generate_extrinsic() for $$FUNC^ROUTINE pattern in src/m2py/codegen/expressions.py (L252)
- [ ] T044 [US5] Generate import statement for external extrinsic in src/m2py/codegen/expressions.py
- [ ] T045 [US5] Generate ext2.ADD(_rt, _scope, args) call pattern in src/m2py/codegen/expressions.py
- [ ] T046 [US5] Generate $TEST save/restore around external extrinsic in src/m2py/codegen/expressions.py
- [ ] T047 [US5] Add integration test for $$FUNC^ROUTINE in tests/integration/test_external_calls.py

**Checkpoint**: External extrinsics work with proper $TEST isolation

---

## Phase 8: User Story 6 - $TEXT with Current Routine (Priority: P2)

**Goal**: Enable `$TEXT(+N)` and `$TEXT(LABEL+N)` for current routine source access

**Independent Test**: `EXT1 W $T(+1) Q` outputs first source line

### Implementation for User Story 6

- [ ] T048 [US6] Implement $TEXT(+N) using _current_source_lines in src/m2py/codegen/expressions.py
- [ ] T049 [US6] Implement $TEXT(+0) returning _current_routine in src/m2py/codegen/expressions.py
- [ ] T050 [US6] Implement $TEXT(LABEL) using _current_label_lines in src/m2py/codegen/expressions.py
- [ ] T051 [US6] Implement $TEXT(LABEL+N) with label lookup and offset in src/m2py/codegen/expressions.py
- [ ] T052 [US6] Handle negative offset edge case (return empty string) in src/m2py/codegen/expressions.py
- [ ] T053 [US6] Add integration test for $TEXT(+N) current routine in tests/integration/test_external_calls.py
- [ ] T054 [US6] Add integration test for $TEXT(-1) negative offset in tests/integration/test_external_calls.py

**Checkpoint**: $TEXT works for current routine with all offset patterns

---

## Phase 9: User Story 7 - $TEXT with External Routine (Priority: P3)

**Goal**: Enable `$TEXT(+N^ROUTINE)` and `$TEXT(LABEL^ROUTINE)` for external source access

**Independent Test**: `EXT1 W $T(+1^ext2) Q` outputs first source line of ext2

### Implementation for User Story 7

- [ ] T055 [US7] Implement $TEXT(+N^ROUTINE) with module import in src/m2py/codegen/expressions.py
- [ ] T056 [US7] Implement $TEXT(LABEL^ROUTINE) with external label lookup in src/m2py/codegen/expressions.py
- [ ] T057 [US7] Implement $TEXT(LABEL+N^ROUTINE) with offset in src/m2py/codegen/expressions.py
- [ ] T058 [US7] Add integration test for $TEXT external routine in tests/integration/test_external_calls.py

**Checkpoint**: $TEXT works for external routines with all patterns

---

## Phase 10: User Story 8 - Module Caching (Priority: P2)

**Goal**: Verify Python's sys.modules caching prevents redundant imports

**Independent Test**: Multiple calls to same routine don't re-import module

### Implementation for User Story 8

- [ ] T059 [US8] Verify import statements are generated (no importlib) in src/m2py/codegen/statements.py
- [ ] T060 [US8] Verify no custom module cache exists in runtime in src/m2py/runtime/__init__.py
- [ ] T061 [US8] Add integration test verifying sys.modules caching behavior in tests/integration/test_external_calls.py

**Checkpoint**: Module caching works via standard Python import mechanism

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and cleanup

- [ ] T062 [P] Update docs/codegen/statements.md with external call patterns
- [ ] T063 [P] Update docs/codegen/expressions.md with extrinsic and $TEXT patterns
- [ ] T064 [P] Update docs/architecture.md with cross-routine infrastructure
- [ ] T065 Run quickstart.md validation scenarios using utils/validate.py
- [ ] T066 Run full test suite and verify YDB output matching
- [ ] T067 Update docs/limitations.md if any edge cases deferred

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - P1 stories (US1, US2, US4) can proceed first
  - P2 stories (US3, US5, US6, US8) follow
  - P3 stories (US7) complete last
- **Polish (Phase 11)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - Foundation for all external calls
- **User Story 2 (P1)**: Can start after US1 - Extends DO with label support
- **User Story 4 (P1)**: Can start after US1 - Shared scope verification
- **User Story 3 (P2)**: Can start after US1 - Different codegen path but shares import logic
- **User Story 5 (P2)**: Can start after US1 - Extends to expressions
- **User Story 6 (P2)**: Can start after Foundational - Depends on _source_lines generation
- **User Story 7 (P3)**: Can start after US6 - Extends $TEXT to external
- **User Story 8 (P2)**: Can start after US1 - Verification only (no new code)

### Within Each User Story

- Core codegen before edge cases
- Import generation before call generation  
- Integration tests validate each story independently

### Parallel Opportunities

- All Setup tasks T002-T005 can run in parallel
- T007-T012 runtime additions can run in parallel
- T013-T015 codegen module constants can run in parallel
- Different user stories can be worked on by different team members after Foundational

---

## Parallel Example: Foundational Phase

```bash
# Launch runtime additions in parallel:
Task T007: "Add GotoExternal exception class"
Task T008: "Add LabelNotFoundError exception class"
Task T009: "Add _current_routine field"
Task T010: "Add _current_source_lines field"
Task T011: "Add _current_label_lines field"

# Launch codegen module constants in parallel:
Task T013: "Generate _source_lines module constant"
Task T014: "Generate _routine_name module constant"
Task T015: "Generate _label_lines mapping"
```

---

## Implementation Strategy

### MVP First (User Stories 1, 2, 4 Only)

1. Complete Phase 1: Setup fixtures
2. Complete Phase 2: Foundational runtime + codegen
3. Complete Phase 3: US1 - External DO Routine
4. Complete Phase 4: US2 - External DO Label
5. Complete Phase 5: US4 - Variable Visibility
6. **STOP and VALIDATE**: Test basic cross-routine calls
7. Deploy/demo if ready - VistA basic routine calls work!

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 + US2 + US4 → Basic external calls (MVP!)
3. Add US3 → External GOTO support
4. Add US5 → Extrinsic functions
5. Add US6 + US7 → Full $TEXT support
6. Add US8 → Verify caching (mostly automatic)

### Key Files Summary

| File | Tasks |
|------|-------|
| src/m2py/runtime/__init__.py | T007-T012, T039 |
| src/m2py/codegen/routine.py | T013-T016, T030, T040 |
| src/m2py/codegen/statements.py | T017-T028, T029, T034-T038, T059 |
| src/m2py/codegen/expressions.py | T043-T058 |
| tests/fixtures/external/ | T001-T005 |
| tests/integration/test_external_calls.py | T021, T027-T028, T032-T033, T041-T042, T047, T053-T054, T058, T061 |
| tests/conftest.py | T006 |

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [US?] label maps task to specific user story for traceability
- Existing placeholders: statements.py L1333 (DO), L1064 (GOTO), expressions.py L252 (extrinsic)
- Standard Python import used throughout - no importlib complexity
- $TEST save/restore per Spec 005 semantics
- Line dispatch (_line_map) from Spec 007 used for offset patterns
- Total tasks: 67 (was 64, added T026-T028 for LabelNotFoundError, T054 for negative $TEXT)
