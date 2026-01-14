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

- [X] T034 [US3] Update _generate_goto() for G ^ROUTINE pattern in src/m2py/codegen/statements.py (L1064)
- [X] T035 [US3] Update _generate_goto() for G LABEL^ROUTINE pattern in src/m2py/codegen/statements.py
- [X] T036 [US3] Generate raise GotoExternal(module, label) pattern in src/m2py/codegen/statements.py
- [X] T037 [US3] Handle G LABEL+N^ROUTINE with offset parameter in src/m2py/codegen/statements.py
- [X] T038 [US3] Handle G +N^ROUTINE with offset parameter in src/m2py/codegen/statements.py
- [X] T039 [US3] Implement run_with_goto_support() runtime helper for GotoExternal dispatch in src/m2py/runtime/__init__.py
- [X] T040 [US3] Generate trampoline call (run_with_goto_support) at entry points in src/m2py/codegen/routine.py - **Note**: Entry points raise GotoExternal; caller uses run_with_goto_support() for chain handling
- [X] T041 [US3] Add integration test for G ^ROUTINE in tests/integration/test_external_calls.py
- [X] T042 [US3] Add integration test for G LABEL^ROUTINE in tests/integration/test_external_calls.py

**Checkpoint**: External GOTO works with proper stack unwinding

---

## Phase 7: User Story 5 - External Extrinsic Function (Priority: P2)

**Goal**: Enable `$$FUNC^ROUTINE(args)` to call and return value from external routine

**Independent Test**: `EXT1 S X=$$ADD^ext2(3,5) W X Q` outputs 8

### Implementation for User Story 5

- [X] T043 [US5] Update _generate_extrinsic() for $$FUNC^ROUTINE pattern in src/m2py/codegen/expressions.py (L252)
- [X] T044 [US5] Generate import statement for external extrinsic in src/m2py/codegen/expressions.py
- [X] T045 [US5] Generate ext2.ADD(_rt, _scope, args) call pattern in src/m2py/codegen/expressions.py
- [X] T046 [US5] Generate $TEST save/restore around external extrinsic in src/m2py/codegen/expressions.py
- [X] T047 [US5] Add integration test for $$FUNC^ROUTINE in tests/integration/test_external_calls.py

**Checkpoint**: External extrinsics work with proper $TEST isolation

---

## Phase 8: User Story 6 - $TEXT with Current Routine (Priority: P2)

**Goal**: Enable `$TEXT(+N)` and `$TEXT(LABEL+N)` for current routine source access

**Independent Test**: `EXT1 W $T(+1) Q` outputs first source line

### Implementation for User Story 6

- [X] T048 [US6] Implement $TEXT(+N) using _current_source_lines in src/m2py/codegen/expressions.py
- [X] T049 [US6] Implement $TEXT(+0) returning _current_routine in src/m2py/codegen/expressions.py
- [X] T050 [US6] Implement $TEXT(LABEL) using _current_label_lines in src/m2py/codegen/expressions.py
- [X] T051 [US6] Implement $TEXT(LABEL+N) with label lookup and offset in src/m2py/codegen/expressions.py
- [X] T052 [US6] Handle negative offset edge case (return empty string) in src/m2py/codegen/expressions.py
- [X] T053 [US6] Add integration test for $TEXT(+N) current routine in tests/integration/test_external_calls.py
- [X] T054 [US6] Add integration test for $TEXT(-1) negative offset in tests/integration/test_external_calls.py

**Checkpoint**: $TEXT works for current routine with all offset patterns

---

## Phase 9: User Story 7 - $TEXT with External Routine (Priority: P3)

**Goal**: Enable `$TEXT(+N^ROUTINE)` and `$TEXT(LABEL^ROUTINE)` for external source access

**Independent Test**: `EXT1 W $T(+1^ext2) Q` outputs first source line of ext2

### Implementation for User Story 7

- [X] T055 [US7] Implement $TEXT(+N^ROUTINE) with module import in src/m2py/codegen/expressions.py
- [X] T056 [US7] Implement $TEXT(LABEL^ROUTINE) with external label lookup in src/m2py/codegen/expressions.py
- [X] T057 [US7] Implement $TEXT(LABEL+N^ROUTINE) with offset in src/m2py/codegen/expressions.py
- [X] T058 [US7] Add integration test for $TEXT external routine in tests/integration/test_external_calls.py

**Checkpoint**: $TEXT works for external routines with all patterns

---

## Phase 10: User Story 8 - Module Caching (Priority: P2)

**Goal**: Verify Python's sys.modules caching prevents redundant imports

**Independent Test**: Multiple calls to same routine don't re-import module

### Implementation for User Story 8

- [X] T059 [US8] Verify import statements are generated (no importlib) in src/m2py/codegen/statements.py
- [X] T060 [US8] Verify no custom module cache exists in runtime in src/m2py/runtime/__init__.py
- [X] T061 [US8] Add integration test verifying sys.modules caching behavior in tests/integration/test_external_calls.py

**Checkpoint**: Module caching works via standard Python import mechanism

---

## Phase 11: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and cleanup

- [X] T062 [P] Update docs/codegen/statements.md with external call patterns
- [X] T063 [P] Update docs/codegen/expressions.md with extrinsic and $TEXT patterns
- [X] T064 [P] Update docs/architecture.md with cross-routine infrastructure
- [X] T065 Run quickstart.md validation scenarios using utils/validate.py
- [X] T066 Run full test suite and verify YDB output matching
- [X] T067 Update docs/limitations.md if any edge cases deferred

---

## Phase 12: Gap Resolution & Test Coverage Improvements

**Purpose**: Address identified gaps from spec review (see tmp/spec_008_gap_analysis.md)

**Goal**: Complete missing test coverage for edge cases and error handling

### Immediate Fixes

- [X] T068 Update tasks.md Phase 7 checkboxes T043-T047 to reflect completed implementation in specs/008-external-calls/tasks.md

### Test Coverage Enhancements

- [X] T069 [P] Add integration test for circular routine calls (A→B→A pattern) in tests/integration/test_external_calls.py
- [X] T070 [P] Add integration test for external routine parse errors (FR-020) in tests/integration/test_external_calls.py
- [X] T071 [P] Add integration test for missing routine ImportError (US1 AC#3) in tests/integration/test_external_calls.py
- [X] T072 [P] Enhance module caching test to explicitly verify single import operation in tests/integration/test_external_calls.py

### Deferred Items (Dependencies)

- [ ] T073 Implement T031: Verify NEW semantics work across routine boundaries - **BLOCKED: Requires Spec 011 NEW command (not yet implemented - all tests are stubs/xfail)**
- [ ] T074 Implement T033: Add integration test for NEW hiding caller variables - **BLOCKED: Requires Spec 011 NEW command (not yet implemented - all tests are stubs/xfail)**

### Known Limitations

- [ ] T075 Document $TEXT runtime validation limitation (MFormatControl dependency) in docs/limitations.md - **DEFERRED: Format controls are part of Spec 011 (not a blocker for Spec 008)**

**Checkpoint**: All edge cases tested, error handling verified, spec gaps resolved

---

## Phase 13: Execution Model & Cross-Routine Variable Visibility

**Purpose**: Fix critical execution model issues identified in gap analysis

**Goal**: Correct the runtime/scope passing pattern and enable true cross-routine variable visibility

### Background

Gap analysis revealed critical issues with the current implementation:
1. Variables stored as Python locals, not in `_scope` dictionary - breaks cross-routine visibility
2. `_rt` not passed to external calls - each module creates its own runtime instance
3. Missing tests for external DO/GOTO with offset patterns
4. $TEXT(-1) test marked complete but not present
5. FR-020 parse error test too weak
6. Documentation patterns don't match implementation

### Execution Model Changes

- [ ] T076 Update function signatures to accept `_rt` as first parameter: `def LABEL(_rt, _scope=None)` in src/m2py/codegen/routine.py
- [ ] T077 Generate `if __name__ == "__main__"` block that creates `_rt = MUMPSRuntime()` and `_scope = {}` in src/m2py/codegen/routine.py
- [ ] T078 Remove module-level `_rt = MUMPSRuntime()` from generated code (entry point creates it) in src/m2py/codegen/routine.py
- [ ] T079 Update external DO calls to pass `_rt`: `ext2.LABEL(_rt, _scope)` in src/m2py/codegen/statements.py
- [ ] T080 Update external GOTO to pass `_rt` in GotoExternal exception handling in src/m2py/codegen/statements.py
- [ ] T081 Update external extrinsic calls to pass `_rt`: `ext2.FUNC(_rt, _scope, args)` in src/m2py/codegen/expressions.py
- [ ] T082 Update run_with_goto_support() to accept and pass `_rt` in src/m2py/runtime/__init__.py
- [ ] T083 Update _call_extrinsic() helper to accept and pass `_rt` in src/m2py/codegen/routine.py

### Variable Storage in _scope

- [ ] T084 Update SET command to store variables in `_scope['varname']` instead of Python locals in src/m2py/codegen/statements.py
- [ ] T085 Update variable reads to access `_scope.get('varname', '')` in src/m2py/codegen/expressions.py
- [ ] T086 Add integration test: variable set in caller visible to callee in tests/integration/test_external_calls.py
- [ ] T087 Add integration test: variable set in callee visible to caller after return in tests/integration/test_external_calls.py

### Missing Test Coverage

- [X] T088 Add integration test for $TEXT(-1) negative offset (was T054, marked done but missing) in tests/integration/test_external_calls.py
- [X] T089 [P] Add integration test for D LABEL+N^ROUTINE (external DO with label+offset) in tests/integration/test_external_calls.py
- [X] T090 [P] Add integration test for D +N^ROUTINE (external DO with absolute offset) in tests/integration/test_external_calls.py
- [X] T091 [P] Add integration test for G LABEL+N^ROUTINE (external GOTO with label+offset) in tests/integration/test_external_calls.py
- [X] T092 [P] Add integration test for G +N^ROUTINE (external GOTO with absolute offset) in tests/integration/test_external_calls.py
- [X] T093 Fix FR-020 test to actually test parse error handling with invalid MUMPS in tests/integration/test_external_calls.py

### Documentation Updates

- [ ] T094 [P] Update data-model.md to document `_rt, _scope` passing pattern in specs/008-external-calls/data-model.md
- [ ] T095 [P] Update research.md to reflect execution model decisions in specs/008-external-calls/research.md
- [ ] T096 [P] Update docs/codegen/functions.md with `def LABEL(_rt, _scope)` signature in docs/codegen/functions.md
- [ ] T097 [P] Update docs/architecture.md with entry point `if __name__ == "__main__"` pattern in docs/architecture.md
- [ ] T098 Update quickstart.md with correct invocation pattern in specs/008-external-calls/quickstart.md

### Validation

- [ ] T099 Run full test suite and fix any regressions from execution model changes
- [ ] T100 Validate with YDB using utils/validate.py for cross-routine variable visibility scenarios

**Checkpoint**: Execution model is clean with explicit `_rt, _scope` passing; variables stored in `_scope` for true cross-routine visibility

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
- **Gap Resolution (Phase 12)**: Can start after Phase 11 - improves test coverage and resolves tracking issues
- **Execution Model (Phase 13)**: Can start after Phase 12 - fixes critical execution model issues; may require updates to earlier phases' generated code

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
| src/m2py/runtime/__init__.py | T007-T012, T039, T082 |
| src/m2py/codegen/routine.py | T013-T016, T030, T040, T076-T078, T083 |
| src/m2py/codegen/statements.py | T017-T028, T029, T034-T038, T059, T079-T080, T084 |
| src/m2py/codegen/expressions.py | T043-T058, T081, T085 |
| tests/fixtures/external/ | T001-T005 |
| tests/integration/test_external_calls.py | T021, T027-T028, T032-T033, T041-T042, T047, T053-T054, T058, T061, T069-T072, T086-T093 |
| tests/conftest.py | T006 |
| specs/008-external-calls/tasks.md | T068 |
| specs/008-external-calls/data-model.md | T094 |
| specs/008-external-calls/research.md | T095 |
| specs/008-external-calls/quickstart.md | T098 |
| docs/codegen/functions.md | T096 |
| docs/architecture.md | T097 |
| docs/limitations.md | T075 |

---

## Notes

- [P] tasks = different files, no dependencies on each other
- [US?] label maps task to specific user story for traceability
- Existing placeholders: statements.py L1333 (DO), L1064 (GOTO), expressions.py L252 (extrinsic)
- Standard Python import used throughout - no importlib complexity
- $TEST save/restore per Spec 005 semantics
- Line dispatch (_line_map) from Spec 007 used for offset patterns
- Total tasks: **100** (67 original + 8 Phase 12 + 25 Phase 13)
- **Phase 12 added**: Addresses gaps identified in tmp/spec_008_gap_analysis.md
- **Phase 13 added**: Fixes critical execution model issues - `_rt, _scope` explicit passing, variables in `_scope` dictionary
