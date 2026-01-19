# Tasks: xfail Test Elimination (Spec 014)

**Input**: Design documents from `/specs/014-xfail-elimination/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- All file paths are relative to repository root

## User Story Mapping

| Story | Spec Priority | Description | Tests |
|-------|---------------|-------------|-------|
| US1 | P1 | Zero xfail Tests in CI | 163 → 0 |
| US2 | P1 | Limitation Errors Are Explicit | 99 tests |
| US3 | P2 | Test Organization Matches Spec | Structure |
| US4 | P3 | Control Flow Advanced (was blocked) | 17 tests |

**Note**: All specs 001-013 are 100% COMPLETE. Nothing is blocked.

---

## Phase 1: Setup

**Purpose**: Validate baseline and prepare branch

- [x] T001 Verify baseline xfail count: `uv run pytest --collect-only -m xfail -q`
- [x] T002 [P] Create backup of current test state for rollback reference
- [x] T003 [P] Verify branch is `014-xfail-elimination` and up to date with main

**Checkpoint**: Baseline confirmed at 163 xfail tests ✅ COMPLETE

---

## Phase 2: Foundational (Error Infrastructure)

**Purpose**: Establish error handling patterns before test conversions

**⚠️ CRITICAL**: Complete before any US2 test conversions

- [ ] T004 Define `ANSI_LIBRARY_ROUTINES` constant in src/m2py/codegen/expressions.py
- [ ] T005 [P] Define `Z_COMMANDS` constant set in src/m2py/codegen/statements.py
- [ ] T006 [P] Define `Z_FUNCTIONS` constant set in src/m2py/codegen/expressions.py
- [ ] T007 Validate limitation IDs exist in src/m2py/limitations.py (LIM-003, LIM-011, LIM-014, LIM-015, LIM-016)

**Checkpoint**: Error infrastructure ready - test conversions can begin

---

## Phase 3: User Story 2 - Limitation Errors Are Explicit (Priority: P1) 🎯 MVP

**Goal**: 99 xfail tests → passing tests that verify `NotImplementedError` with LIM-XXX

**Independent Test**: 
```bash
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py \
    tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_*.py \
    tests/unit/codegen/extensions/ydb/ -v
```

### Task A1: SSVN Error Handling (4 tests)

- [ ] T008 [US2] Fix ^$EVENT/^$WINDOW/^$DISPLAY: raise NotImplementedError("LIM-003") in src/m2py/codegen/expressions.py:320
- [ ] T009 [US2] Fix ^$LIBRARY: raise NotImplementedError("LIM-011") in src/m2py/codegen/expressions.py:324
- [ ] T010 [US2] Convert test_mwapi_ssvns_codegen xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py
- [ ] T011 [US2] Convert test_library_ssvn_codegen xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py

### Task A2: ANSI Library Function Errors (68 tests)

- [ ] T012 [US2] Add ANSI library detection in `_generate_extrinsic()` in src/m2py/codegen/expressions.py
- [ ] T013 [P] [US2] Convert 12 trigonometric function tests (sin, cos, tan, etc.) from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py
- [ ] T014 [P] [US2] Convert 10 inverse trig function tests (asin, acos, atan, etc.) from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py
- [ ] T015 [P] [US2] Convert 8 exponential function tests (exp, log, sqrt, etc.) from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py
- [ ] T016 [P] [US2] Convert 4 angle conversion function tests (deg, rad, etc.) from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py
- [ ] T017 [P] [US2] Convert 13 complex number function tests from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py
- [ ] T018 [P] [US2] Convert 10 matrix function tests from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py
- [ ] T019 [P] [US2] Convert 6 string library function tests (crc16, crc32, etc.) from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py
- [ ] T020 [P] [US2] Convert 5 character library function tests (collate, upper, etc.) from xfail to pytest.raises in tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py

### Task A3: Z-Command/Function Errors (18 tests)

- [ ] T021 [US2] Add Z-command detection and NotImplementedError in src/m2py/codegen/statements.py
- [ ] T022 [P] [US2] Add Z-function detection ($ZDATE, $ZMESSAGE, $ZWIDTH) NotImplementedError in src/m2py/codegen/expressions.py
- [ ] T023 [P] [US2] Convert ZALLOCATE/ZDEALLOCATE tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zallocate.py
- [ ] T024 [P] [US2] Convert ZBREAK tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zbreak.py
- [ ] T025 [P] [US2] Convert ZCOMPILE tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zcompile.py
- [ ] T026 [P] [US2] Convert ZCONTINUE tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zcontinue.py
- [ ] T027 [P] [US2] Convert ZEDIT tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zedit.py
- [ ] T028 [P] [US2] Convert ZHELP tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zhelp.py
- [ ] T029 [P] [US2] Convert ZMESSAGE tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zmessage.py
- [ ] T030 [P] [US2] Convert ZPRINT tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zprint.py
- [ ] T031 [P] [US2] Convert ZSTEP tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zstep.py
- [ ] T032 [P] [US2] Convert ZSYSTEM tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_zsystem.py
- [ ] T033 [P] [US2] Convert ZTRIGGER tests from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/test_ztrigger.py
- [ ] T034 [P] [US2] Convert Z-function tests ($ZDATE, etc.) from xfail to pytest.raises in tests/unit/codegen/extensions/ydb/

### Task A4: Zero-VistA Feature Errors (9 tests)

- [ ] T035 [US2] Add TROLLBACK:n (level arg) detection and NotImplementedError in src/m2py/codegen/statements.py
- [ ] T036 [P] [US2] Add device parameter NotImplementedError in src/m2py/codegen/statements.py
- [ ] T037 [P] [US2] Convert TROLLBACK:n test from xfail to pytest.raises in tests/unit/codegen/s8_commands/test_s8_2_21_trollback.py
- [ ] T038 [P] [US2] Convert $TRESTART test from xfail to pytest.raises in tests/unit/codegen/s7_expressions/
- [ ] T039 [P] [US2] Convert legacy pre-1984 variable scope tests (2) from xfail to pytest.raises in tests/unit/codegen/legacy/test_pre1995_behavior.py
- [ ] T040 [P] [US2] Convert $NEXT tests (3) from xfail to pytest.raises in tests/unit/codegen/legacy/
- [ ] T041 [P] [US2] Convert device parameter tests (2) from xfail to pytest.raises in tests/unit/codegen/

### Phase 3 Validation

- [ ] T042 [US2] Run Phase A validation: `uv run pytest --collect-only -m xfail -q` (expect ~64 remaining)
- [ ] T043 [US2] Run full test suite: `uv run pytest` (expect 0 failures)

**Checkpoint**: 99 limitation error tests pass - US2 complete. xfail count reduced by 99.

---

## Phase 4: User Story 1 - Zero xfail Tests in CI (Priority: P1)

**Goal**: Implement remaining 64 features after error handling (163 - 99 = 64 tests)

**Independent Test**: `uv run pytest --collect-only -m xfail -q`

### Task B: Core Language Semantics (12 tests)

#### Task B1: Special Variables (4 tests)

- [ ] T044 [US1] Implement $TLEVEL special variable in src/m2py/codegen/expressions.py
- [ ] T045 [P] [US1] Implement $QUIT context awareness (1 in extrinsic, 0 in DO) in src/m2py/codegen/expressions.py
- [ ] T046 [US1] Implement $TEXT external routine lookup in src/m2py/codegen/expressions.py
- [ ] T047 [US1] Convert 4 special variable tests from xfail in tests/unit/codegen/s7_expressions/

#### Task B2: Indirection Completion (3 tests)

- [ ] T048 [US1] Implement subscript indirection (@var in subscript) in src/m2py/codegen/expressions.py
- [ ] T049 [US1] Implement argument indirection (@var as argument) in src/m2py/codegen/expressions.py
- [ ] T050 [US1] Convert 3 indirection tests from xfail in tests/unit/codegen/s7_expressions/

#### Task B3: Transaction Commands (4 tests)

- [ ] T051 [US1] Implement TSTART basic in src/m2py/codegen/statements.py
- [ ] T052 [P] [US1] Implement TCOMMIT basic in src/m2py/codegen/statements.py
- [ ] T053 [P] [US1] Implement TROLLBACK basic (no level arg) in src/m2py/codegen/statements.py
- [ ] T054 [US1] Convert 4 transaction tests from xfail in tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py

#### Task B4: Error Processing (1 test)

- [ ] T055 [US1] Implement error propagation across label calls in src/m2py/codegen/
- [ ] T056 [US1] Convert error processing test from xfail in tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py

### Task C: Data Operations (8 tests)

#### Task C1: MERGE Globals (2 tests)

- [ ] T057 [US1] Implement MERGE local→global (M ^GLO=LOCAL) in src/m2py/codegen/statements.py
- [ ] T058 [US1] Implement MERGE global→global (M ^GLO1=^GLO2) in src/m2py/codegen/statements.py
- [ ] T059 [US1] Convert 2 MERGE global tests from xfail in tests/unit/codegen/s8_commands/

#### Task C2: Naked Reference Edge Cases (5 tests)

- [ ] T060 [US1] Implement naked reference error without prior global in src/m2py/codegen/
- [ ] T061 [US1] Implement naked references in $DATA, $ORDER, MERGE, LOCK in src/m2py/codegen/
- [ ] T062 [US1] Convert 5 naked reference tests from xfail in tests/unit/codegen/

#### Task C3: KILL Global (1 test)

- [ ] T063 [US1] Implement KILL global (K ^GLO) in src/m2py/codegen/statements.py
- [ ] T064 [US1] Convert KILL global test from xfail in tests/unit/codegen/s8_commands/

### Task D: Routine Structure (6 tests)

#### Task D1: Routine Metadata (3 tests)

- [ ] T065 [US1] Implement routine docstring from MUMPS header in src/m2py/codegen/
- [ ] T066 [P] [US1] Implement empty label translation (_preamble) in src/m2py/codegen/
- [ ] T067 [US1] Convert 3 routine metadata tests from xfail in tests/unit/codegen/s6_routine/

#### Task D2: Extrinsic Advanced (3 tests)

- [ ] T068 [US1] Implement module caching for external imports in src/m2py/codegen/
- [ ] T069 [P] [US1] Implement cross-routine variable passing in src/m2py/codegen/
- [ ] T070 [US1] Convert 3 extrinsic advanced tests from xfail in tests/unit/codegen/

### Task E: Advanced Features (14 tests)

#### Task E1: Language Semantics (5 tests)

- [ ] T071 [US1] Implement $TEST NOT stacked for label call in src/m2py/codegen/
- [ ] T072 [P] [US1] Implement $TEST NOT stacked for DO with arguments in src/m2py/codegen/
- [ ] T073 [P] [US1] Implement $TEST NOT stacked for XECUTE in src/m2py/codegen/
- [ ] T074 [US1] Implement DO block execution level tracking in src/m2py/codegen/
- [ ] T075 [US1] Convert 5 language semantics tests from xfail in tests/unit/codegen/

#### Task E2: Postconditions Advanced (3 tests)

- [ ] T076 [US1] Implement argument postconditions as independent in src/m2py/codegen/
- [ ] T077 [P] [US1] Implement postcondition evaluation order in src/m2py/codegen/
- [ ] T078 [US1] Convert 3 postcondition tests from xfail in tests/unit/codegen/

#### Task E3: XECUTE Runtime (3 tests)

- [ ] T079 [US1] Implement runtime global access in XECUTE in src/m2py/codegen/
- [ ] T080 [P] [US1] Implement ZOSF lookup table optimization in src/m2py/codegen/
- [ ] T081 [US1] Convert 3 XECUTE runtime tests from xfail in tests/unit/codegen/

#### Task E4: Character Set (3 tests)

- [ ] T082 [US1] Implement M character encoding in src/m2py/codegen/
- [ ] T083 [P] [US1] Implement graphic/control character handling in src/m2py/codegen/
- [ ] T084 [US1] Convert 3 character set tests from xfail in tests/unit/codegen/s9_charset/

### Phase 4 Validation

- [ ] T085 [US1] Run validation: `uv run pytest --collect-only -m xfail -q` (expect ~24 remaining)
- [ ] T086 [US1] Run full test suite: `uv run pytest` (expect 0 failures)

**Checkpoint**: Core feature tests pass - Phase 5 (Control Flow Advanced) can begin

---

## Phase 5: User Story 4 - Control Flow Advanced (Priority: P3) 🎯 NOW IMPLEMENTABLE

**Goal**: Implement 17 tests using existing Spec 006/007/008 infrastructure

**Independent Test**: `uv run pytest tests/unit/codegen/s8_commands/test_s8_2_03_do.py tests/unit/codegen/s8_commands/test_s8_2_06_goto.py -v`

**Note**: Specs 006, 007, 008 are ✅ COMPLETE. These features are now implementable!

### Task F1: DO External (6 tests) - Spec 008 Ready

- [ ] T087 [US4] Implement DO external routine (D LABEL^ROUTINE) in src/m2py/codegen/
- [ ] T088 [P] [US4] Implement scope strategy PURE_FUNCTION codegen in src/m2py/codegen/
- [ ] T089 [P] [US4] Implement scope strategy SUBROUTINE codegen in src/m2py/codegen/
- [ ] T090 [P] [US4] Implement scope strategy FUNCTION_WITH_OUTPUTS codegen in src/m2py/codegen/
- [ ] T091 [P] [US4] Implement scope strategy REQUIRES_RUNTIME codegen in src/m2py/codegen/
- [ ] T092 [US4] Implement partial indirection (D @var^ROUTINE) in src/m2py/codegen/
- [ ] T093 [US4] Convert 6 DO external tests from xfail in tests/unit/codegen/s8_commands/test_s8_2_03_do.py

### Task F2: GOTO Advanced (5 tests) - Spec 006 Ready

- [ ] T094 [US4] Implement computed GOTO (G LABEL+offset) in src/m2py/codegen/
- [ ] T095 [P] [US4] Implement state machine fallback in src/m2py/codegen/
- [ ] T096 [P] [US4] Implement state machine variable scope in src/m2py/codegen/
- [ ] T097 [US4] Implement same-level enforcement in src/m2py/codegen/
- [ ] T098 [US4] Implement partial indirection (G @var) in src/m2py/codegen/
- [ ] T099 [US4] Convert 5 GOTO advanced tests from xfail in tests/unit/codegen/s8_commands/test_s8_2_06_goto.py

### Task F3: Computed Offsets (6 tests) - Spec 007 Ready

- [ ] T100 [US4] Implement DO/GOTO with literal offset in src/m2py/codegen/
- [ ] T101 [P] [US4] Implement offset with variable in src/m2py/codegen/
- [ ] T102 [P] [US4] Implement offset with global in src/m2py/codegen/
- [ ] T103 [P] [US4] Implement offset with function in src/m2py/codegen/
- [ ] T104 [P] [US4] Implement offset arithmetic in src/m2py/codegen/
- [ ] T105 [US4] Convert 6 computed offset tests from xfail in tests/unit/codegen/s8_commands/test_s8_2_18_set.py

### Task F4: Cross-Cutting & Misc (7 tests)

- [ ] T106 [US4] Implement/fix test_timeout_codegen in tests/unit/codegen/s8_commands/test_s8_1_general_rules.py
- [ ] T107 [P] [US4] Implement/fix test_command_sequence in tests/unit/codegen/s8_commands/test_s8_1_general_rules.py
- [ ] T108 [P] [US4] Implement/fix test_newed_variable_isolation in tests/unit/codegen/test_cross_label_goto.py
- [ ] T109 [P] [US4] Implement/fix test_formal_param_isolation in tests/unit/codegen/test_cross_label_goto.py
- [ ] T110 [US4] Convert remaining misc xfail tests (check with pytest --collect-only)

### Phase 5 Validation

- [ ] T111 [US4] Run validation: `uv run pytest --collect-only -m xfail -q` (expect 0)
- [ ] T112 [US4] Run full test suite: `uv run pytest` (expect 0 failures)

**Checkpoint**: All 17 control flow tests pass - ZERO xfail remaining!

---

## Phase 6: User Story 3 - Test Organization Matches Spec (Priority: P2)

**Goal**: Verify test file organization aligns with MUMPS ANSI Standard sections

**Independent Test**: `ls tests/unit/codegen/` shows s6_routine/, s7_expressions/, s8_commands/, s9_charset/

### Organization Verification

- [ ] T113 [US3] Verify test directory structure matches spec sections in tests/unit/codegen/
- [ ] T114 [P] [US3] Verify all modified test files have spec section docstrings
- [ ] T115 [P] [US3] Verify limitation reference tests are in correct directories
- [ ] T116 [US3] Update any misplaced tests to correct locations

**Checkpoint**: Test organization verified - US3 complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation updates

- [ ] T117 Final xfail count validation: `uv run pytest --collect-only -m xfail -q` (must be exactly 0)
- [ ] T118 [P] Run full test suite: `uv run pytest` (0 failures, 0 xpass)
- [ ] T119 [P] Update docs/limitations.md with any new limitation details
- [ ] T120 [P] Update specs/codegen-plan.md to mark Spec 014 tasks complete
- [ ] T121 Run quickstart.md validation steps
- [ ] T122 Create PR with comprehensive description of changes

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1: Setup ─────────────────────────────────────────────┐
                                                            ▼
Phase 2: Foundational (Error Infrastructure) ──────────────┐│
         T004-T007: Define constants & validate LIMs       ▼▼
                                                            │
Phase 3: US2 Limitation Errors (99 tests) ─────────────────┤
         T008-T043: Error handlers + test conversions      │
                                                            │
Phase 4: US1 Core Features (47 tests) ─────────────────────┤
         T044-T086: Feature implementations                 │
                                                            │
Phase 5: US4 Control Flow Advanced (17 tests) ────────────┤
         T087-T112: DO/GOTO/Offset implementations          │
         (Uses Spec 006/007/008 infrastructure)             │
                                                            │
Phase 6: US3 Test Organization ────────────────────────────┤
         T113-T116: Verify structure                        │
                                                            ▼
Phase 7: Polish ───────────────────────────────────────────┘
         T117-T122: Final validation & PR
```

**Note**: All specs 001-013 are ✅ COMPLETE. Phase 5 is now implementation, not blocked.

### User Story Independence

- **US2 (Limitation Errors)**: Can complete fully after Phase 2 - no feature implementation needed
- **US1 (Zero xfail)**: Depends on US2 for xfail count tracking, but implementation is independent
- **US4 (Control Flow)**: Uses Spec 006/007/008 infrastructure - fully implementable now
- **US3 (Organization)**: Verification only - independent of implementations

### Parallel Opportunities by Phase

**Phase 3 (US2 Limitation Errors)**:
```bash
# After T008-T009 (SSVN errors implemented), all test conversions can run in parallel:
T010, T011  # SSVN tests
T013-T020   # Library function tests (all [P])
T023-T034   # Z-command tests (all [P])
T037-T041   # Zero-VistA tests (all [P])
```

**Phase 4 (US1 Feature Implementation)**:
```bash
# These can run in parallel (different files):
T045, T052, T053  # $QUIT, TCOMMIT, TROLLBACK basic
T065, T066        # Docstring, empty label
T072, T073, T077  # $TEST variants, postcondition order
T080, T083        # ZOSF, graphic chars
```

---

## Implementation Strategy

### MVP First: US2 Only (Phase 1-3)

1. Complete Phase 1: Setup (T001-T003)
2. Complete Phase 2: Foundational (T004-T007)
3. Complete Phase 3: US2 Limitation Errors (T008-T043)
4. **STOP and VALIDATE**: 99 tests converted from xfail to passing
5. Result: xfail count drops from 163 → 64

### Full Scope (All Phases)

| Phase | Tests Converted | Cumulative xfail |
|-------|-----------------|------------------|
| Start | 0 | 163 |
| Phase 3 (US2) | 99 | 64 |
| Phase 4 (US1) | 40 | 24 |
| Phase 5 (US4) | 24 | 0 |
| Phase 6 (US3) | 0 (verification) | 0 |
| Final | — | **0 xfail** |

### Critical Path

1. **T004-T007**: Constants must be defined before any error handlers
2. **T008, T009**: SSVN errors must be fixed before T010-T011 tests
3. **T012**: Library detection must be added before T013-T020 tests
4. **T021**: Z-command detection must be added before T023-T034 tests
5. **T042**: Phase validation must pass before Phase 4 begins

---

## Task Count Summary

| Phase | Tasks | Tests Affected | Parallelizable |
|-------|-------|----------------|----------------|
| Phase 1: Setup | 3 | 0 | 2 |
| Phase 2: Foundational | 4 | 0 | 2 |
| Phase 3: US2 Errors | 36 | 99 | 29 |
| Phase 4: US1 Features | 43 | 40 | 15 |
| Phase 5: US4 Control Flow | 26 | 24 | 12 |
| Phase 6: US3 Org | 4 | 0 | 2 |
| Phase 7: Polish | 6 | 0 | 3 |
| **Total** | **122** | **163** | **65** |

**Target**: ZERO xfail tests remaining.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks in same phase
- [Story] label maps task to specific user story (US1, US2, US3, US4)
- After each test conversion, verify with `uv run pytest path/to/test.py -v`
- Commit after logical task groups (e.g., all SSVN changes together)
- If a test unexpectedly passes (xpass), remove xfail immediately per spec constraints
