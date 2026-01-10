# Tasks: Spec 005 - Structured Control Flow Codegen

**Input**: Design documents from `/specs/005-structured-control-flow/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Extend codegen module structure for Spec 005

- [X] T001 Create test file structure for Spec 005 in tests/unit/codegen/s8_commands/
- [X] T002 [P] Add UnsupportedFeatureError exception class in src/m2py/codegen/exceptions.py
- [X] T003 [P] Add itertools import infrastructure in src/m2py/codegen/routine.py preamble generation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Extend GeneratorContext with signatures dict and loop_stack in src/m2py/codegen/routine.py
- [X] T005 Add validation that required analysis passes have run before codegen in src/m2py/codegen/routine.py
- [X] T006 Add scope strategy dispatcher function in src/m2py/codegen/routine.py
- [X] T007 [P] Add ForGenContext helper dataclass in src/m2py/codegen/statements.py
- [X] T008 [P] Add GotoGenContext helper dataclass in src/m2py/codegen/statements.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - $TEST Stack for DO Blocks (Priority: P1) 🎯 MVP

**$TEST Stacking Rules** (verified against YottaDB):
- Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack $TEST - callee's $TEST IS visible
- Only DO blocks (D + dot-indented lines) stack $TEST
- Extrinsic functions ($$func) stack $TEST

**Goal**: Save/restore $TEST around DO blocks (D with dot lines) so ELSE sees correct value

**Independent Test**: Execute DO blocks that modify $TEST, verify restoration

### Implementation for User Story 1

- [X] T009 [US1] Add _is_do_block() helper to detect DO blocks in src/m2py/codegen/statements.py (renamed from _is_argumentless_do)
- [X] T010 [US1] Modify _generate_do() to emit _saved_test save before DO blocks in src/m2py/codegen/statements.py
- [X] T011 [US1] Modify _generate_do() to emit _test restore after DO blocks in src/m2py/codegen/statements.py
- [X] T012 [US1] Add test: label calls do NOT save/restore $TEST in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [X] T013 [US1] Add test: label call $TEST visible to caller in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [X] T014 [US1] Add test: _is_do_block helper in tests/unit/codegen/s8_commands/test_s8_2_03_do.py

**Checkpoint**: $TEST semantics correct - label calls share $TEST, DO blocks stack it

---

## Phase 4: User Story 2 - Label Calls Share $TEST (Priority: P1)

**Note**: All label calls (D SUB, D SUB(), D SUB(X)) have identical $TEST behavior - none stack it.
This phase verifies the implementation and adds argument passing support.

**Goal**: Verify all label call forms share $TEST with caller and implement argument codegen

**Independent Test**: Execute D SUB(args) where callee sets $TEST, verify caller sees it

### Implementation for User Story 2

- [X] T015 [US2] Ensure _generate_do() does NOT emit save/restore for DO with arguments in src/m2py/codegen/statements.py
- [X] T016 [US2] Add test: DO with args does NOT restore $TEST in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [X] T017 [US2] Add test: ELSE after DO(args) sees callee's $TEST in tests/unit/codegen/s8_commands/test_s8_2_03_do.py

**Note**: T015-T017 completed 2026-01-10. Added _generate_call_arguments() helper and tests.
Full formal parameter support requires Phase 9 (US7) - deferred test marked xfail.

**Checkpoint**: $TEST behavior differs correctly between argumentless DO and DO with arguments

---

## Phase 5: User Story 3 - FOR Loop Variations (Priority: P1)

**Goal**: Handle all FOR loop types based on analysis flags

**Independent Test**: Execute each loop type and verify correct iteration count

### Implementation for User Story 3

- [ ] T018 [US3] Refactor _generate_for() to dispatch based on loop_type in src/m2py/codegen/statements.py
- [ ] T019 [US3] Implement _generate_for_open_ended() using itertools.count in src/m2py/codegen/statements.py
- [ ] T020 [US3] Implement _generate_for_argumentless() using while True in src/m2py/codegen/statements.py
- [ ] T021 [US3] Implement _generate_for_mixed() using itertools.chain in src/m2py/codegen/statements.py
- [ ] T022 [US3] Implement _generate_for_while() for loop_var_modified_in_body=True in src/m2py/codegen/statements.py
- [ ] T023 [US3] Add test: open-ended FOR with QUIT in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [ ] T024 [US3] Add test: argumentless FOR with DO block in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [ ] T025 [US3] Add test: mixed parameter FOR in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [ ] T026 [US3] Add test: FOR with loop var modification in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [ ] T027 [US3] Add test: negative step FOR bounds in tests/unit/codegen/s8_commands/test_s8_2_05_for.py

**Checkpoint**: All FOR loop types generate correct Python patterns

---

## Phase 6: User Story 4 - Intra-Label GOTO Restructuring (Priority: P2)

**Goal**: Restructure forward same-label GOTOs to if/else chains

**Independent Test**: Verify generated Python uses if/else not function calls

### Implementation for User Story 4

- [ ] T028 [US4] Add _is_restructurable_goto() to check is_cross_label=False and FORWARD_JUMP in src/m2py/codegen/statements.py
- [ ] T029 [US4] Implement _restructure_forward_goto() to generate if/else structure in src/m2py/codegen/statements.py
- [ ] T030 [US4] Modify _generate_goto() to dispatch to restructure for intra-label forward jumps in src/m2py/codegen/statements.py
- [ ] T031 [US4] Add UnsupportedFeatureError for backward intra-label GOTO in src/m2py/codegen/statements.py
- [ ] T032 [US4] Add test: forward jump restructures to if/else in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py
- [ ] T033 [US4] Add test: backward intra-label GOTO raises error in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py

**Checkpoint**: Intra-label forward GOTO restructures to Python control flow

---

## Phase 7: User Story 5 - Loop Exit Translation (Priority: P2)

**Goal**: Translate LOOP_EXIT to break, MULTI_LOOP_EXIT to exception

**Independent Test**: Execute loop-exiting GOTOs and verify correct exit behavior

### Implementation for User Story 5

- [ ] T034 [US5] Implement is_loop_continue=True GOTO as continue in src/m2py/codegen/statements.py
- [ ] T035 [US5] Implement LOOP_EXIT GOTO as break in src/m2py/codegen/statements.py
- [ ] T036 [US5] Add _LoopExit exception class generation in module preamble in src/m2py/codegen/routine.py
- [ ] T037 [US5] Implement MULTI_LOOP_EXIT GOTO as raise _LoopExit() in src/m2py/codegen/statements.py
- [ ] T038 [US5] Generate try/except wrapper for FOR loops with exit_points in src/m2py/codegen/statements.py
- [ ] T039 [US5] Add test: GOTO continue pattern in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py
- [ ] T040 [US5] Add test: single loop exit becomes break in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py
- [ ] T041 [US5] Add test: multi-loop exit uses exception in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py

**Checkpoint**: Loop exits translate to idiomatic Python patterns

---

## Phase 8: User Story 6 - QUIT Context Awareness (Priority: P2)

**Goal**: QUIT generates break vs return based on ASG context flags

**Independent Test**: Verify QUIT in FOR generates break, in DO generates return

### Implementation for User Story 6

- [ ] T042 [US6] Modify _generate_quit() to check exits_for flag in src/m2py/codegen/statements.py
- [ ] T043 [US6] Generate break when exits_for=True in src/m2py/codegen/statements.py
- [ ] T044 [US6] Generate return when exits_do_block=True in src/m2py/codegen/statements.py
- [ ] T045 [US6] Generate return <expr> when return_value present in src/m2py/codegen/statements.py
- [ ] T046 [US6] Add test: QUIT in FOR generates break in tests/unit/codegen/s8_commands/test_s8_2_16_quit.py
- [ ] T047 [US6] Add test: QUIT in DO block generates return in tests/unit/codegen/s8_commands/test_s8_2_16_quit.py
- [ ] T048 [US6] Add test: QUIT with value generates return expr in tests/unit/codegen/s8_commands/test_s8_2_16_quit.py

**Checkpoint**: QUIT context-aware code generation working

---

## Phase 9: User Story 7 - Scope Strategy Code Generation (Priority: P2)

**Goal**: Generate function signatures based on ScopeStrategy classification

**Independent Test**: Examine generated function signatures and return statements

### Implementation for User Story 7

- [ ] T049 [US7] Modify _generate_label() to accept FunctionSignature in src/m2py/codegen/routine.py
- [ ] T050 [US7] Generate formal parameters in function definition from signature.formal_params in src/m2py/codegen/routine.py
- [ ] T051 [US7] Implement PURE_FUNCTION return pattern in src/m2py/codegen/routine.py
- [ ] T052 [US7] Implement SUBROUTINE pattern (implicit return None) in src/m2py/codegen/routine.py
- [ ] T053 [US7] Implement FUNCTION_WITH_OUTPUTS return tuple pattern in src/m2py/codegen/routine.py
- [ ] T054 [US7] Add UnsupportedFeatureError for REQUIRES_RUNTIME strategy in src/m2py/codegen/routine.py
- [ ] T055 [US7] Add test: PURE_FUNCTION generates simple return in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T056 [US7] Add test: SUBROUTINE generates no explicit return in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T057 [US7] Add test: FUNCTION_WITH_OUTPUTS generates tuple return in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py
- [ ] T058 [US7] Add test: REQUIRES_RUNTIME raises error in tests/unit/codegen/s6_routine/test_s6_1_routine_head.py

**Checkpoint**: Scope strategies generate appropriate function patterns

---

## Phase 10: User Story 8 - By-Reference Parameter Handling (Priority: P3)

**Goal**: Generate return tuples for by-ref params, destructure at call sites

**Independent Test**: Pass variables by reference and verify caller sees modifications

### Implementation for User Story 8

- [ ] T059 [US8] Add byref_outputs to return tuple in _generate_label() in src/m2py/codegen/routine.py
- [ ] T060 [US8] Modify _generate_do() to check callee signature for byref_outputs in src/m2py/codegen/statements.py
- [ ] T061 [US8] Generate tuple destructuring at DO call site when byref_outputs non-empty in src/m2py/codegen/statements.py
- [ ] T062 [US8] Handle mixed by-ref and by-value parameters in argument mapping in src/m2py/codegen/statements.py
- [ ] T063 [US8] Add test: SWAP pattern with two by-ref params in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [ ] T064 [US8] Add test: INCR pattern with single by-ref param in tests/unit/codegen/s8_commands/test_s8_2_03_do.py
- [ ] T065 [US8] Add test: multiple by-ref calls accumulate in tests/unit/codegen/s8_commands/test_s8_2_03_do.py

**Checkpoint**: By-reference parameters work via return tuple pattern

---

## Phase 11: $TEST for Extrinsic Functions (Completing $TEST Stack)

**Goal**: Save/restore $TEST around extrinsic function calls ($$label)

**Independent Test**: Execute extrinsic calls and verify $TEST isolation

### Implementation

- [ ] T066 [US1] Implement $TEST save/restore for extrinsic function calls in src/m2py/codegen/expressions.py
- [ ] T067 [US1] Add test: extrinsic function isolates $TEST in tests/unit/codegen/s7_expressions/test_s7_1_1_values.py
- [ ] T068 [US1] Add test: postconditions do NOT update $TEST in tests/unit/cross_cutting/test_language_semantics.py

**Checkpoint**: Full $TEST stack semantics implemented (argumentless DO + extrinsics)

---

## Phase 12: Polish & Cross-Cutting Concerns

**Purpose**: Validation, documentation, and cleanup

- [ ] T069 [P] Add ast.parse() validation to routine generation in src/m2py/codegen/routine.py
- [ ] T070 [P] Update docs/codegen/for_loops.md with actual generated patterns
- [ ] T071 [P] Update docs/codegen/goto_handling.md with actual generated patterns
- [ ] T072 Run pytest coverage and verify 85%+ on codegen additions
- [ ] T073 Run quickstart.md validation - all success checklist items pass
- [ ] T074 Update codegen-plan.md: mark Spec 005 deliverables complete

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies - can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 - BLOCKS all user stories
- **Phases 3-4 (US1-US2)**: Depend on Phase 2, both P1 priority - do sequentially (related $TEST logic)
- **Phase 5 (US3)**: Depends on Phase 2 - can run parallel with US1/US2
- **Phases 6-9 (US4-US7)**: Depend on Phase 2 - can run in parallel
- **Phase 10 (US8)**: Depends on Phase 9 (scope strategy) - needs signature infrastructure
- **Phase 11**: Depends on Phase 3 (US1 $TEST pattern)
- **Phase 12 (Polish)**: Depends on all user stories

### User Story Dependencies

- **US1 ($TEST argumentless DO)**: Foundation only - can start first
- **US2 ($TEST DO with args)**: Same code area as US1 - do after US1
- **US3 (FOR loops)**: Independent - can run parallel with US1/US2
- **US4 (Intra-label GOTO)**: Independent - can run parallel
- **US5 (Loop exits)**: Depends on US3 FOR infrastructure
- **US6 (QUIT context)**: Independent - can run parallel
- **US7 (Scope strategy)**: Independent - can run parallel
- **US8 (By-ref)**: Depends on US7 scope infrastructure

### Parallel Opportunities

Within Phase 2:
- T007 and T008 can run in parallel (different helper classes)

Within Phase 5 (US3):
- T023, T024, T025, T026, T027 tests can run in parallel once implementation complete

Within Phase 9 (US7):
- T055, T056, T057, T058 tests can run in parallel

Within Phase 12:
- T069, T070, T071 can run in parallel (different files)

---

## Implementation Strategy

### MVP First (User Stories 1-3)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: US1 ($TEST argumentless DO) - **Critical for correctness**
4. Complete Phase 4: US2 ($TEST with args) - **Completes $TEST behavior**
5. Complete Phase 5: US3 (FOR loops) - **Core functionality**
6. **STOP and VALIDATE**: Test $TEST + FOR loops against YDB
7. Deploy/demo MVP

### Incremental Delivery

After MVP:
1. Add US4 (GOTO restructuring) → More idiomatic Python
2. Add US5 (Loop exits) → break/exception patterns
3. Add US6 (QUIT context) → Context-aware returns
4. Add US7 (Scope strategy) → Proper function signatures
5. Add US8 (By-ref) → Full parameter handling
6. Complete Phase 11 → Full $TEST stack
7. Polish phase → Documentation and validation

---

## Notes

- All tests use embedded MUMPS strings, NOT .m files (per codegen-plan.md)
- Use `execute_mumps` fixture for full routine execution tests
- Verify generated code passes `ast.parse()` before execution
- Cross-label GOTO patterns → raise UnsupportedFeatureError (Spec 006)
- REQUIRES_RUNTIME scope → raise UnsupportedFeatureError (Spec 006/007)
- Postcondition codegen → out of scope (Spec 008), but test $TEST behavior
