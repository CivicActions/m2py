# Tasks: Test Suite Consolidation & VistA Compatibility

**Input**: Design documents from `/specs/013-test-consolidation/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1=Stub Cleanup, US2=Fall-Through, US3=Test Conversion, US4=VistA Features)
- Exact file paths included in descriptions

---

## Phase 1: Setup

**Purpose**: Verify infrastructure and prepare for task execution

- [x] T001 Verify `execute_mumps` fixture works in tests/unit/codegen/conftest.py
- [x] T002 Verify `validate.py` can compare against YDB in utils/validate.py
- [x] T003 [P] Count current xfail tests and document baseline (`uv run pytest --collect-only | grep xfail`)

**Baseline documented**: 283 xfail tests collected (286 @pytest.mark.xfail markers across test files)

---

## Phase 2: Foundational - Database Abstraction Extensions

**Purpose**: Extend GlobalStorageBackend protocol for LOCK, transactions, SSVNs (blocks US4 features)

**⚠️ CRITICAL**: VistA feature implementation depends on this phase

- [ ] T004 Add lock methods to GlobalStorageBackend protocol in src/m2py/runtime/globals.py
- [ ] T005 [P] Implement lock() in InMemoryGlobalStorage (in-process lock table) in src/m2py/runtime/globals.py
- [ ] T006 [P] Add transaction methods to GlobalStorageBackend protocol in src/m2py/runtime/globals.py
- [ ] T007 Implement transaction_start/commit/rollback in InMemoryGlobalStorage in src/m2py/runtime/globals.py
- [ ] T008 [P] Add SSVN query methods to GlobalStorageBackend protocol in src/m2py/runtime/globals.py
- [ ] T009 Implement ssvn_global/job/lock/routine in InMemoryGlobalStorage in src/m2py/runtime/globals.py
- [ ] T010 Add $TLEVEL support to MUMPSRuntime in src/m2py/runtime/__init__.py

**Checkpoint**: Database abstraction ready - VistA features can now be implemented

---

## Phase 3: User Story 1 - Stub Cleanup (Priority: P1) 🎯 MVP

**Goal**: Delete ~44 redundant stubs, reduce xfail noise, establish trust in test suite

**Independent Test**: `uv run pytest --collect-only | grep xfail | wc -l` shows reduction of ~44

### DELETE: §7.2 Operators (4 stubs)

- [ ] T011 [P] [US1] Verify test_s7_2_logical_operators.py covers multiplication, then delete stub in tests/
- [ ] T012 [P] [US1] Verify test_s7_2_logical_operators.py covers logical_and, then delete stub in tests/
- [ ] T013 [P] [US1] Verify test_s7_2_logical_operators.py covers logical_or, then delete stub in tests/
- [ ] T014 [P] [US1] Verify test_s7_2_logical_operators.py covers left_to_right_evaluation, then delete stub in tests/

### DELETE: §8.2.18 SET (9 stubs)

- [ ] T015 [P] [US1] Verify test_spec_009_globals.py covers set_global, then delete stub in tests/
- [ ] T016 [P] [US1] Verify test_spec_009_lhs_piece.py covers set_piece stubs (3), then delete stubs in tests/
- [ ] T017 [P] [US1] Verify test_spec_009_lhs_extract.py covers set_extract stubs (3), then delete stubs in tests/
- [ ] T018 [P] [US1] Verify test_spec_009_lhs_piece.py covers lhs_piece stubs (3), then delete in tests/
- [ ] T019 [P] [US1] Verify test_spec_009_lhs_extract.py covers lhs_extract stubs (3), then delete in tests/

### DELETE: Control Flow Duplicates

- [ ] T020 [P] [US1] Verify spec-aligned coverage for IF stubs, delete duplicates in tests/
- [ ] T021 [P] [US1] Verify spec-aligned coverage for WRITE stubs, delete duplicates in tests/
- [ ] T022 [P] [US1] Verify spec-aligned coverage for FOR stubs, delete duplicates in tests/

### DELETE: Z-Command Duplicates (8 stubs)

- [ ] T023 [P] [US1] Identify and delete duplicate ZWRITE test stubs across test files
- [ ] T024 [P] [US1] Identify and delete duplicate ZLINK test stubs across test files
- [ ] T025 [P] [US1] Identify and delete other duplicate Z-command stubs

### DELETE: Remaining Redundant Stubs

- [ ] T026 [US1] Audit remaining DELETE candidates from gaps-stubs.md, verify coverage, delete
- [ ] T027 [US1] Run xfail count, verify ~44 reduction from baseline

**Checkpoint**: User Story 1 complete - xfail reduced by ~44, all deletions verified

---

## Phase 4: User Story 2 - Fall-Through Semantics (Priority: P2)

**Goal**: Implement implicit label fall-through for MUMPS semantic correctness

**Independent Test**: `execute_mumps("TEST\n W \"A\"\nFOR\n W \"B\"\nEND\n W \"C\"\n Q")` returns "ABC"

### Analysis Phase

- [ ] T028 [US2] Add fall-through detection to semantic analyzer in src/m2py/analysis/semantic_analyzer.py
- [ ] T029 [US2] Add `needs_fallthrough` flag to MLabel ASG node in src/m2py/asg/elements.py
- [ ] T030 [US2] Detect labels not ending with QUIT/GOTO/HALT in src/m2py/analysis/semantic_analyzer.py

### Codegen Phase

- [ ] T031 [US2] Generate explicit fall-through calls in label codegen in src/m2py/codegen/routine.py
- [ ] T032 [US2] Handle return value propagation through fall-through chain in src/m2py/codegen/routine.py
- [ ] T033 [US2] Support external entry fall-through (D LABEL^ROUTINE) in src/m2py/codegen/routine.py

### Tests

- [ ] T034 [US2] Create fall-through test: TEST→FOR→END outputs ABC in tests/unit/codegen/
- [ ] T035 [US2] Create fall-through test: middle QUIT stops chain in tests/unit/codegen/
- [ ] T036 [US2] Create fall-through test: external entry continues fall-through in tests/unit/codegen/
- [ ] T037 [US2] Validate fall-through against YDB using validate.py

**Checkpoint**: User Story 2 complete - fall-through works per SC-004

---

## Phase 5: User Story 3 - Test Conversion (Priority: P3)

**Goal**: Convert ~39 stubs from generate_python to execute_mumps with real assertions

**Independent Test**: Converted tests use execute_mumps fixture and assert actual output

### CONVERT: §7.2 Operators (7 stubs)

- [ ] T038 [P] [US3] Validate division works, convert test_division to execute_mumps in tests/
- [ ] T039 [P] [US3] Validate equals works, convert test_equals to execute_mumps in tests/
- [ ] T040 [P] [US3] Convert test_addition_then_multiplication to execute_mumps in tests/
- [ ] T041 [P] [US3] Convert test_subtraction_left_to_right to execute_mumps in tests/
- [ ] T042 [P] [US3] Convert test_division_left_to_right to execute_mumps in tests/
- [ ] T043 [P] [US3] Convert test_mixed_arithmetic_comparison to execute_mumps in tests/
- [ ] T044 [P] [US3] Convert test_parentheses_override_left_to_right to execute_mumps in tests/

### CONVERT: SET Command (1 stub)

- [ ] T045 [US3] Validate set_multiple_targets works, convert to execute_mumps in tests/

### CONVERT: IF Command Stubs

- [ ] T046 [P] [US3] Convert test_if_multiple_conditions to execute_mumps in tests/
- [ ] T047 [P] [US3] Convert other IF-related stubs to execute_mumps in tests/

### CONVERT: Remaining Stubs

- [ ] T048 [US3] Identify all remaining CONVERT candidates from gaps-stubs.md
- [ ] T049 [US3] Validate each feature works using validate.py before conversion
- [ ] T050 [US3] Convert remaining ~25 stubs to execute_mumps with real assertions
- [ ] T051 [US3] Run test suite, verify all converted tests pass

**Checkpoint**: User Story 3 complete - ~39 stubs converted to real tests (SC-003)

---

## Phase 6: User Story 4 - VistA Features Part A: String Intrinsics (Priority: P4)

**Goal**: Implement high-usage string functions ($ASCII, $CHAR, $TRANSLATE, $REVERSE, $JUSTIFY, $FNUMBER)

**Independent Test**: `$ASCII("A")` returns 65, `$CHAR(65)` returns "A"

### $ASCII/$CHAR (FR-013, FR-014) - 31.1% usage

- [ ] T052 [P] [US4] Implement _ascii() helper in src/m2py/codegen/helpers.py
- [ ] T053 [P] [US4] Implement _char() helper in src/m2py/codegen/helpers.py
- [ ] T054 [US4] Add $ASCII/$CHAR codegen in src/m2py/codegen/expressions.py
- [ ] T055 [US4] Create tests for $ASCII/$CHAR edge cases in tests/unit/codegen/

### $TRANSLATE (FR-020) - 8.7% usage

- [ ] T056 [US4] Implement _translate() helper in src/m2py/codegen/helpers.py
- [ ] T057 [US4] Add $TRANSLATE codegen in src/m2py/codegen/expressions.py
- [ ] T058 [US4] Create tests for $TRANSLATE in tests/unit/codegen/

### $JUSTIFY (FR-017) - 13.2% usage

- [ ] T059 [US4] Implement _justify() helper in src/m2py/codegen/helpers.py
- [ ] T060 [US4] Add $JUSTIFY codegen in src/m2py/codegen/expressions.py
- [ ] T061 [US4] Create tests for $JUSTIFY in tests/unit/codegen/

### $REVERSE (FR-027) - 0.11% usage

- [ ] T062 [US4] Implement _reverse() helper in src/m2py/codegen/helpers.py
- [ ] T063 [US4] Add $REVERSE codegen in src/m2py/codegen/expressions.py
- [ ] T064 [US4] Create tests for $REVERSE in tests/unit/codegen/

### $FNUMBER (FR-025) - 1.4% usage

- [ ] T065 [US4] Implement _fnumber() helper in src/m2py/codegen/helpers.py
- [ ] T066 [US4] Add $FNUMBER codegen in src/m2py/codegen/expressions.py
- [ ] T067 [US4] Create tests for $FNUMBER in tests/unit/codegen/

**Checkpoint**: String intrinsics complete (SC-009 verified)

---

## Phase 7: User Story 4 - VistA Features Part B: $TEXT and $NEXT (Priority: P4)

**Goal**: Implement $TEXT (26.7% usage) and $NEXT (deprecated, 0.12% usage)

### $TEXT (FR-021)

- [ ] T068 [US4] Implement _text() helper using _source_lines/_label_lines in src/m2py/codegen/helpers.py
- [ ] T069 [US4] Add $TEXT codegen in src/m2py/codegen/expressions.py
- [ ] T070 [US4] Create tests for $TEXT(LABEL) and $TEXT(LABEL+n) in tests/unit/codegen/
- [ ] T071 [US4] Validate $TEXT against YDB using validate.py

### $NEXT (FR-031) - Deprecated

- [ ] T072 [US4] Implement _next() helper (wraps _order, returns -1) in src/m2py/codegen/helpers.py
- [ ] T073 [US4] Add $NEXT codegen with deprecation warning in src/m2py/codegen/expressions.py
- [ ] T074 [US4] Create tests for $NEXT in tests/unit/codegen/

**Checkpoint**: $TEXT and $NEXT complete (SC-014, SC-018 verified)

---

## Phase 8: User Story 4 - VistA Features Part C: Transactions (Priority: P4)

**Goal**: Implement TSTART/TCOMMIT/TROLLBACK via database abstraction (29.4% usage)

### Transaction Commands (FR-015)

- [ ] T075 [US4] Add MTStartStatement codegen in src/m2py/codegen/statements.py
- [ ] T076 [US4] Add MTCommitStatement codegen in src/m2py/codegen/statements.py
- [ ] T077 [US4] Add MTRollbackStatement codegen in src/m2py/codegen/statements.py
- [ ] T078 [US4] Create transaction tests with Memory backend in tests/unit/codegen/
- [ ] T079 [US4] Test transaction rollback restores state in tests/unit/codegen/
- [ ] T080 [US4] Validate transactions against YDB using validate.py

**Checkpoint**: Transactions complete (SC-010 verified)

---

## Phase 9: User Story 4 - VistA Features Part D: LOCK Command (Priority: P4)

**Goal**: Implement LOCK command via database abstraction (10.2% usage)

### LOCK Command (FR-019)

- [ ] T081 [US4] Add MLockStatement codegen in src/m2py/codegen/statements.py
- [ ] T082 [US4] Implement LOCK +/- syntax handling in src/m2py/codegen/statements.py
- [ ] T083 [US4] Create LOCK tests with Memory backend in tests/unit/codegen/
- [ ] T084 [US4] Test LOCK timeout sets $TEST in tests/unit/codegen/
- [ ] T085 [US4] Validate LOCK against YDB using validate.py

**Checkpoint**: LOCK complete (SC-011 partial, SC-015 partial)

---

## Phase 10: User Story 4 - VistA Features Part E: I/O Commands (Priority: P4)

**Goal**: Implement READ, USE, OPEN, CLOSE commands

### READ Command (FR-016) - 13.4% usage

- [ ] T086 [US4] Add MReadStatement codegen in src/m2py/codegen/statements.py
- [ ] T087 [US4] Implement READ timeout syntax in src/m2py/codegen/statements.py
- [ ] T088 [US4] Create READ tests (mock input) in tests/unit/codegen/

### USE Command (FR-018) - 10.6% usage

- [ ] T089 [US4] Add MUseStatement codegen in src/m2py/codegen/statements.py
- [ ] T090 [US4] Create USE tests in tests/unit/codegen/

### OPEN/CLOSE Commands (FR-022) - 7.2% usage

- [ ] T091 [US4] Add MOpenStatement codegen in src/m2py/codegen/statements.py
- [ ] T092 [US4] Add MCloseStatement codegen in src/m2py/codegen/statements.py
- [ ] T093 [US4] Implement OPEN timeout syntax in src/m2py/codegen/statements.py
- [ ] T094 [US4] Create OPEN/CLOSE tests in tests/unit/codegen/

**Checkpoint**: I/O commands complete (SC-015 partial)

---

## Phase 11: User Story 4 - VistA Features Part F: JOB and Exclusive NEW (Priority: P4)

**Goal**: Implement JOB command and exclusive NEW syntax

### JOB Command (FR-024) - 1.5% usage

- [ ] T095 [US4] Add MJobStatement codegen using subprocess in src/m2py/codegen/statements.py
- [ ] T096 [US4] Implement JOB timeout syntax in src/m2py/codegen/statements.py
- [ ] T097 [US4] Create JOB tests (spawn process) in tests/unit/codegen/

### Exclusive NEW (FR-023) - 5.3% usage

- [ ] T098 [US4] Add exclusive NEW detection in analysis in src/m2py/analysis/variables.py
- [ ] T099 [US4] Add exclusive NEW codegen in src/m2py/codegen/statements.py
- [ ] T100 [US4] Create exclusive NEW tests in tests/unit/codegen/

**Checkpoint**: JOB and exclusive NEW complete (SC-011 verified)

---

## Phase 12: User Story 4 - VistA Features Part G: Error Processing (Priority: P4)

**Goal**: Implement $ECODE, $ETRAP, $ZERROR for error handling

### Error Processing (FR-026, FR-045)

- [ ] T101 [US4] Add $ECODE special variable to runtime in src/m2py/runtime/__init__.py
- [ ] T102 [US4] Add $ETRAP special variable to runtime in src/m2py/runtime/__init__.py
- [ ] T103 [US4] Add $ZERROR special variable to runtime in src/m2py/runtime/__init__.py
- [ ] T104 [US4] Implement error trap codegen in src/m2py/codegen/statements.py
- [ ] T105 [US4] Create error processing tests in tests/unit/codegen/

**Checkpoint**: Error processing complete

---

## Phase 13: User Story 4 - VistA Features Part H: Math Functions (Priority: P4)

**Goal**: Implement all math intrinsic functions (FR-034 through FR-038)

### Math Functions

- [ ] T106 [P] [US4] Implement _exp() using math.exp in src/m2py/codegen/helpers.py
- [ ] T107 [P] [US4] Implement _log() using math.log in src/m2py/codegen/helpers.py
- [ ] T108 [P] [US4] Implement _sqrt() using math.sqrt in src/m2py/codegen/helpers.py
- [ ] T109 [P] [US4] Implement trig functions (_sin, _cos, _tan) in src/m2py/codegen/helpers.py
- [ ] T110 [P] [US4] Implement inverse trig (_arcsin, _arccos, _arctan) in src/m2py/codegen/helpers.py
- [ ] T111 [US4] Add math function codegen in src/m2py/codegen/expressions.py
- [ ] T112 [US4] Create math function tests in tests/unit/codegen/
- [ ] T113 [US4] Validate math functions against YDB

**Checkpoint**: Math functions complete (SC-012 verified)

---

## Phase 14: User Story 4 - VistA Features Part I: Exponentiation (Priority: P4)

**Goal**: Implement exponentiation operator (FR-012) - 0.4% usage

### Exponentiation

- [ ] T114 [US4] Add exponentiation operator codegen in src/m2py/codegen/expressions.py
- [ ] T115 [US4] Create exponentiation tests (`W 2**3` → 8) in tests/unit/codegen/
- [ ] T116 [US4] Validate exponentiation against YDB

**Checkpoint**: Exponentiation complete (SC-005 verified)

---

## Phase 15: User Story 4 - VistA Features Part J: Pattern Alternation (Priority: P4)

**Goal**: Implement pattern match alternation syntax (FR-030) - 0.11% usage

### Pattern Alternation

- [ ] T117 [US4] Extend pattern compiler for alternation in src/m2py/analysis/pattern_compiler.py
- [ ] T118 [US4] Create pattern alternation tests in tests/unit/codegen/
- [ ] T119 [US4] Validate pattern alternation against YDB

**Checkpoint**: Pattern alternation complete (SC-017 verified)

---

## Phase 16: User Story 4 - VistA Features Part K: SSVNs (Priority: P4)

**Goal**: Implement ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE (FR-029) - 0.04% usage

### SSVNs

- [ ] T120 [US4] Add SSVN detection in parser/analysis in src/m2py/analysis/semantic_analyzer.py
- [ ] T121 [US4] Add SSVN codegen using database abstraction in src/m2py/codegen/expressions.py
- [ ] T122 [US4] Create SSVN tests in tests/unit/codegen/

**Checkpoint**: SSVNs complete (SC-016 verified)

---

## Phase 17: User Story 4 - VistA Features Part L: VIEW and BREAK (Priority: P4)

**Goal**: Implement VIEW (6 files) and BREAK (2 files) commands

### VIEW Command (FR-032)

- [ ] T123 [US4] Add MViewStatement codegen in src/m2py/codegen/statements.py
- [ ] T124 [US4] Create VIEW tests in tests/unit/codegen/

### BREAK Command (FR-033)

- [ ] T125 [US4] Add MBreakStatement codegen in src/m2py/codegen/statements.py
- [ ] T126 [US4] Create BREAK tests in tests/unit/codegen/

**Checkpoint**: VIEW and BREAK complete (SC-019, SC-020 verified)

---

## Phase 18: User Story 4 - VistA Features Part M: Timeout Infrastructure (Priority: P4)

**Goal**: Implement timeout infrastructure for LOCK, READ, OPEN, JOB (FR-028)

### Timeout Infrastructure

- [ ] T127 [US4] Add timeout parameter handling to LOCK codegen in src/m2py/codegen/statements.py
- [ ] T128 [US4] Add timeout parameter handling to READ codegen in src/m2py/codegen/statements.py
- [ ] T129 [US4] Add timeout parameter handling to OPEN codegen in src/m2py/codegen/statements.py
- [ ] T130 [US4] Add timeout parameter handling to JOB codegen in src/m2py/codegen/statements.py
- [ ] T131 [US4] Verify $TEST set correctly on timeout in tests/unit/codegen/

**Checkpoint**: Timeout infrastructure complete (SC-015 verified)

---

## Phase 19: User Story 4 - VistA Features Part N: Z-Commands (Priority: P4)

**Goal**: Implement Z-commands with VistA usage (FR-039 through FR-044)

### ZWRITE (FR-039) - 54 files

- [ ] T132 [US4] Implement _zwrite() helper in src/m2py/codegen/helpers.py
- [ ] T133 [US4] Add ZWRITE codegen in src/m2py/codegen/statements.py
- [ ] T134 [US4] Create ZWRITE tests in tests/unit/codegen/

### ZKILL (FR-042) - 5 files

- [ ] T135 [US4] Add ZKILL codegen using kill_node() in src/m2py/codegen/statements.py
- [ ] T136 [US4] Create ZKILL tests in tests/unit/codegen/

### ZLINK (FR-040) - 20 files

- [ ] T137 [US4] Implement _zlink() for dynamic routine loading in src/m2py/codegen/helpers.py
- [ ] T138 [US4] Add ZLINK codegen in src/m2py/codegen/statements.py
- [ ] T139 [US4] Create ZLINK tests in tests/unit/codegen/

### ZSHOW (FR-041) - 9 files

- [ ] T140 [US4] Implement _zshow() helper in src/m2py/codegen/helpers.py
- [ ] T141 [US4] Add ZSHOW codegen in src/m2py/codegen/statements.py
- [ ] T142 [US4] Create ZSHOW tests in tests/unit/codegen/

### ZGOTO (FR-043) - 2 files

- [ ] T143 [US4] Implement ZGotoException for stack unwinding in src/m2py/runtime/exceptions.py
- [ ] T144 [US4] Add ZGOTO codegen in src/m2py/codegen/statements.py
- [ ] T145 [US4] Create ZGOTO tests in tests/unit/codegen/

### ZHALT (FR-044) - 1 file

- [ ] T146 [US4] Add ZHALT codegen using sys.exit() in src/m2py/codegen/statements.py
- [ ] T147 [US4] Create ZHALT tests in tests/unit/codegen/

**Checkpoint**: Z-commands complete (SC-013 verified)

---

## Phase 20: Polish & Validation

**Purpose**: Final validation and cleanup

- [ ] T148 Run full test suite, verify zero xfail tests (SC-001)
- [ ] T149 Search for duplicate tests, verify none exist (SC-002)
- [ ] T150 Verify test suite time increase <20% (SC-006)
- [ ] T151 Run validate.py against sample VistA routines (SC-007)
- [ ] T152 Update docs/coverage-matrix.md with new features
- [ ] T153 Update docs/limitations.md if any features remain unimplemented
- [ ] T154 Run quickstart.md validation checklist

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup) → Phase 2 (Foundational/DB Abstraction)
                          ↓
         ┌────────────────┼────────────────┐
         ↓                ↓                ↓
   Phase 3 (US1)    Phase 4 (US2)    Phase 5 (US3)
   Stub Cleanup     Fall-Through     Test Convert
         ↓                ↓                ↓
         └────────────────┴────────────────┘
                          ↓
              Phases 6-19 (US4 Features)
                          ↓
                   Phase 20 (Polish)
```

### User Story Dependencies

- **US1 (Stub Cleanup)**: After Setup - independent of other stories
- **US2 (Fall-Through)**: After Setup - independent of other stories
- **US3 (Test Conversion)**: After Setup - independent of other stories
- **US4 (VistA Features)**: After Phase 2 (DB Abstraction) - has internal dependencies

### Within US4 (VistA Features)

- String intrinsics (Phase 6) - no dependencies, start first
- $TEXT (Phase 7) - depends on Spec 007 (already complete)
- Transactions (Phase 8) - depends on Phase 2 (DB abstraction)
- LOCK (Phase 9) - depends on Phase 2 (DB abstraction)
- I/O commands (Phase 10) - no dependencies within US4
- JOB/NEW (Phase 11) - depends on Phase 2 (DB abstraction)
- Error processing (Phase 12) - no dependencies within US4
- Math functions (Phase 13) - no dependencies within US4
- Exponentiation (Phase 14) - no dependencies within US4
- Pattern alternation (Phase 15) - no dependencies within US4
- SSVNs (Phase 16) - depends on Phase 2 (DB abstraction)
- VIEW/BREAK (Phase 17) - no dependencies within US4
- Timeouts (Phase 18) - depends on commands being implemented (Phases 9-11)
- Z-commands (Phase 19) - depends on Phase 2 for ZKILL

### Parallel Opportunities

**After Phase 2 completion:**
- US1, US2, US3 can run in parallel
- Within US4: Phases 6, 10, 12, 13, 14, 15, 17 can run in parallel

**Within phases:**
- All tasks marked [P] can run in parallel
- Math function implementations (T106-T110) can run in parallel
- String intrinsic implementations can run in parallel
- DELETE tasks within US1 can run in parallel

---

## Implementation Strategy

### MVP First (User Stories 1-3)

1. Complete Phase 1: Setup
2. Complete Phase 2: DB Abstraction
3. Complete Phase 3: US1 Stub Cleanup (~44 xfail reduction)
4. **STOP and VALIDATE**: xfail count reduced, deletions verified
5. Continue with US2 (Fall-Through) and US3 (Test Conversion)

### Incremental VistA Features

After MVP, implement US4 features by VistA usage:
1. String intrinsics ($ASCII/$CHAR) - 31.1%
2. Transactions - 29.4%
3. $TEXT - 26.7%
4. READ - 13.4%
5. Continue in priority order...

### Final Validation

After all phases:
1. Zero xfail tests
2. Zero duplicate tests
3. All VistA features validated against YDB

---

## Summary

| Category | Tasks | Notes |
|----------|-------|-------|
| Setup | 3 | Infrastructure verification |
| Foundational | 7 | DB abstraction extensions |
| US1: Stub Cleanup | 17 | DELETE ~44 stubs |
| US2: Fall-Through | 10 | Core MUMPS semantics |
| US3: Test Conversion | 14 | CONVERT ~39 stubs |
| US4: VistA Features | 96 | 33 FRs implementation |
| Polish | 7 | Final validation |
| **Total** | **154** | |

**Parallel Tasks**: 47 tasks marked [P]
**MVP Scope**: Phases 1-5 (51 tasks)
**Independent Test Points**: After each checkpoint
