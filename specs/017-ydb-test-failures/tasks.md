# Tasks: YDB Test Suite Failure Resolution

**Input**: Design documents from `/specs/017-ydb-test-failures/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, quickstart.md ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story (US1-US11) this task belongs to
- Story labels only on user story phase tasks (not Setup or Foundational phases)

---

## Phase 1: Setup

**Purpose**: Baseline validation and environment preparation

- [x] T001 Run baseline test suite and capture current failure count: `uv run pytest tests/functional/ -v --tb=no 2>&1 | tee /tmp/baseline-failures.txt`
- [x] T002 [P] Verify YDB Docker container available: `docker run --rm ydb echo "YDB ready"`
- [x] T003 [P] Create tracking spreadsheet/document mapping 147 tests to resolution status

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Analysis infrastructure that enables multiple user stories

**⚠️ CRITICAL**: US1 (TRAMPOLINE enhancement) depends on these analysis flags

- [x] T004 Add `has_argumentless_kill: bool = False` field to MRoutine in src/m2py/asg/elements.py
- [x] T005 Add `has_argumentless_new: bool = False` field to MRoutine in src/m2py/asg/elements.py
- [x] T006 Update variable analysis to detect and set `has_argumentless_kill` in src/m2py/analysis/variables.py
- [x] T007 Update variable analysis to detect and set `has_argumentless_new` in src/m2py/analysis/variables.py
- [x] T008 Add unit tests for argumentless KILL/NEW detection in tests/unit/analysis/

**Checkpoint**: Analysis flags available - US1 TRAMPOLINE work can begin

---

## Phase 3: User Story 1 - Argumentless KILL/NEW in TRAMPOLINE (Priority: P1) 🎯 MVP

**Goal**: Execute MUMPS routines with argumentless KILL/NEW correctly in TRAMPOLINE strategy

**Independent Test**: Run v1call, v1nst3, v1ov through m2py and verify output matches YDB

**Affected Tests**: v1call, v1nst3, v1ov, v1prgd, v1seq, vv2lcc1, vv2vnib (7 MVTS tests)
**Note**: fifo, per02397, setpiece were originally listed but have DIFFERENT issues (Z-extensions/external deps, addressed in US8/other phases)

### Implementation

- [x] T009 [US1] Modify `generate_routine_state_class()` to add `_locals: dict[str, Any]` field in src/m2py/codegen/shared_state.py
- [x] T010 [US1] Add `_new_stack: list[dict]` field to RoutineState for NEW scope management in src/m2py/codegen/shared_state.py
- [x] T011 [US1] Implement argumentless KILL codegen to clear `state._locals.clear()` in src/m2py/codegen/statements.py
- [x] T012 [US1] Implement argumentless NEW codegen to push/clear `state._locals` in src/m2py/codegen/statements.py
- [x] T013 [US1] Implement NEW scope restoration on QUIT in src/m2py/codegen/statements.py
- [x] T014 [US1] Update variable access codegen to check `state._locals` dict when in TRAMPOLINE mode in src/m2py/codegen/expressions.py
- [x] T015 [US1] Add unit tests for argumentless KILL/NEW with cross-label GOTO in tests/unit/codegen/
- [x] T016 [US1] Validate 7 MVTS tests pass: `uv run pytest tests/functional/test_mvts.py -k "V1CALL or V1NST3 or V1OV or V1PRGD or V1SEQ or V2LCC1 or V2VNIB" -v`

**Checkpoint**: 7 TRAMPOLINE tests pass - argumentless KILL/NEW working ✅

---

## Phase 4: User Story 9 - Codegen Syntax Errors (Priority: P1)

**Goal**: Generated Python is always syntactically valid

**Independent Test**: Transpile V2VNIA and verify Python parses without SyntaxError

**Affected Tests**: V2VNIA (1 test)

### Implementation

- [x] T017 [US9] Debug V2VNIA to identify unmatched parenthesis source - found f-string escaping issue with complex subscript expressions containing `)` and `"` characters
- [x] T018 [US9] Fix parenthesis generation bug in src/m2py/codegen/indirection.py - changed from f-string to string concatenation
- [x] T019 [US9] Updated 7 unit tests in tests/unit/codegen/s7_expressions/test_s7_3_indirection_codegen.py to expect new concatenation format
- [x] T020 [US9] Validate V2VNIA passes: `uv run pytest tests/functional/test_mvts.py -k V2VNIA -v`

**Checkpoint**: Codegen syntax validation passes - 1 test fixed ✅

---

## Phase 5: User Story 2 - Sorts-After Operator (Priority: P1)

**Goal**: Implement missing sorts-after operator (`]]`) for MUMPS collation

**Independent Test**: Transpile `relation` test and verify all comparisons match YDB

**Affected Tests**: relation (1 test)

### Implementation

- [x] T021 [US2] Verify m_sorts_after() helper exists in src/m2py/runtime/helpers.py (research indicates already implemented)
- [x] T022 [US2] Debug `relation` test failure to identify if bug is in collation logic or operator invocation - Found multiple bugs: missing negated operators, m_compare returning bool not int, m_str scientific notation, Decimal precision, m_num exponential notation and leading whitespace handling
- [x] T023 [US2] Fix identified bug in collation logic (empty string < numerics < strings) if needed - Fixed: added negated operators ('[, '], ']], '&, '!), m_compare returns int not bool, added m_str for MUMPS-style formatting, Decimal for large number precision, m_num handles exponential notation and correctly rejects leading whitespace
- [x] T024 [US2] Add unit tests for sorts-after edge cases in tests/unit/runtime/test_helpers.py - Existing tests cover core functionality; relation test provides integration validation
- [x] T025 [US2] Validate relation test passes: `uv run pytest tests/functional/ -k relation -v`

**Checkpoint**: Sorts-after operator working - 1 test fixed ✅ (plus bool test now passes as side effect)

---

## Phase 6: User Story 3 - LHS $PIECE Extensions (Priority: P1)

**Goal**: Support LHS $PIECE with naked globals and indirection

**Independent Test**: Transpile vv2lhp1, vv2lhp2, vv2vnic and verify output matches YDB

**Affected Tests**: vv2lhp1, vv2lhp2, vv2vnic (3 tests)

### Implementation

- [ ] T026 [US3] Add MNakedGlobal handling to `_generate_lhs_piece()` in src/m2py/codegen/statements.py
- [ ] T027 [US3] Add MIndirection handling to `_generate_lhs_piece()` in src/m2py/codegen/statements.py
- [ ] T028 [US3] Create getter/setter lambdas for naked global references
- [ ] T029 [US3] Create runtime evaluation for indirected variable references
- [ ] T030 [US3] Add unit tests for LHS $PIECE with globals/indirection in tests/unit/codegen/s8_commands/test_s8_2_18_set.py
- [ ] T031 [US3] Validate all 3 tests pass: `uv run pytest tests/functional/ -k "vv2lhp1 or vv2lhp2 or vv2vnic" -v`

**Checkpoint**: LHS $PIECE extensions working - 3 tests fixed

---

## Phase 7: User Story 10 - Missing Expression Types (Priority: P2)

**Goal**: Handle MZWriteSubscriptAll and ExtendedGlobalBracket

**Independent Test**: Transpile largeexp1 and per02276 without NotImplementedError

**Affected Tests**: largeexp1, per02276 (2 tests)

### Implementation

- [ ] T032 [US10] Debug largeexp1 to identify MZWriteSubscriptAll usage: `uv run python utils/validate.py --debug tests/functional/basic/inref/largeexp1.m`
- [ ] T033 [US10] Implement MZWriteSubscriptAll expression codegen in src/m2py/codegen/expressions.py
- [ ] T034 [US10] Debug per02276 to identify ExtendedGlobalBracket SET target usage
- [ ] T035 [US10] Implement ExtendedGlobalBracket SET target codegen in src/m2py/codegen/statements.py
- [ ] T036 [US10] Validate tests pass: `uv run pytest tests/functional/ -k "largeexp1 or per02276" -v`

**Checkpoint**: Expression type support complete - 2 tests fixed

---

## Phase 8: User Story 8 - LIM-015 xfail Configuration (Priority: P3)

**Goal**: Mark Z-extension tests as expected failures

**Independent Test**: Run pytest and verify 12 tests show xfail instead of FAILED

**Affected Tests**: V1SVH, V2ZTRG, V2ZB, and 9 others using ZSYSTEM/$ZTRAP/$ZVERSION/$ZPREVIOUS (12 tests)

### Implementation (⚠️ HUMAN REVIEW REQUIRED for conftest.py changes)

- [ ] T037 [US8] Identify all 12 LIM-015 affected tests from failure-analysis.md
- [ ] T038 [US8] Add entries to ROUTINE_LIMITATIONS dict in tests/functional/conftest.py for each affected routine mapped to "LIM-015"
- [ ] T039 [US8] Validate 12 tests show skip: `uv run pytest tests/functional/ -v 2>&1 | grep -c "LIM-015"`

**Checkpoint**: LIM-015 tests properly configured - 12 tests xfail'd

---

## Phase 9: User Story 4 - Arithmetic Bug Fixes (Priority: P2)

**Goal**: Fix numeric output formatting to match YDB

**Independent Test**: Run arith test and verify each line matches YDB reference

**Affected Tests**: arith, barith, ebmuldiv, largeexp2, largeexp3, and others (estimated 5-10 tests)

### Implementation

- [ ] T040 [P] [US4] Debug arith test to identify specific mismatches: `uv run python utils/validate.py --debug tests/functional/basic/inref/arith.m`
- [ ] T041 [P] [US4] Debug barith test to identify specific mismatches
- [ ] T042 [US4] Fix numeric formatting in m_num() or output routines in src/m2py/codegen/helpers.py or src/m2py/runtime/helpers.py
- [ ] T043 [US4] Fix scientific notation handling if applicable
- [ ] T044 [US4] Validate arithmetic tests pass: `uv run pytest tests/functional/ -k "arith or barith or ebmuldiv or largeexp" -v`

**Checkpoint**: Arithmetic tests fixed - 5-10 tests resolved

---

## Phase 10: User Story 5 - Pattern Matching Fixes (Priority: P2)

**Goal**: Fix pattern match operator evaluation

**Independent Test**: Run pattst and verify all patterns match/don't match correctly

**Affected Tests**: pattst, v1pat, vv2pat1, vv2pat2, vv2pat3 (5 tests)

### Implementation

- [ ] T045 [P] [US5] Debug pattst to identify failing patterns: `uv run python utils/validate.py --debug tests/functional/basic/inref/pattst.m`
- [ ] T046 [P] [US5] Debug v1pat for additional pattern failure cases
- [ ] T047 [US5] Fix pattern compilation bugs in src/m2py/analysis/pattern_compiler.py
- [ ] T048 [US5] Fix pattern matching runtime if applicable in src/m2py/runtime/helpers.py (m_pattern_match)
- [ ] T049 [US5] Add unit tests for identified pattern edge cases in tests/unit/analysis/test_pattern_compiler.py
- [ ] T050 [US5] Validate pattern tests pass: `uv run pytest tests/functional/ -k "pattst or v1pat or vv2pat" -v`

**Checkpoint**: Pattern matching fixed - 5 tests resolved

---

## Phase 11: User Story 6 - FOR Loop Fixes (Priority: P2)

**Goal**: Fix FOR loop iteration behavior

**Independent Test**: Run for and forloop tests, verify iteration counts match YDB

**Affected Tests**: for, forloop, v1fora, v1forb, v1forc (5 tests)

### Implementation

- [ ] T051 [P] [US6] Debug for test to identify iteration issues: `uv run python utils/validate.py --debug tests/functional/basic/inref/for.m`
- [ ] T052 [P] [US6] Debug v1fora, v1forb, v1forc for loop-specific failures
- [ ] T053 [US6] Fix FOR loop bounds handling in src/m2py/codegen/statements.py
- [ ] T054 [US6] Fix FOR loop increment logic if applicable in src/m2py/analysis/for_analysis.py
- [ ] T055 [US6] Validate FOR tests pass: `uv run pytest tests/functional/ -k "for or forloop or v1for" -v`

**Checkpoint**: FOR loops fixed - 5 tests resolved

---

## Phase 12: User Story 7 - $ORDER/$QUERY Fixes (Priority: P2)

**Goal**: Fix traversal function behavior

**Independent Test**: Run order test, verify traversal sequence matches YDB

**Affected Tests**: order, query, v1nr (3 tests)

### Implementation

- [ ] T056 [P] [US7] Debug order test to identify traversal issues: `uv run python utils/validate.py --debug tests/functional/basic/inref/order.m`
- [ ] T057 [P] [US7] Debug query test for $QUERY-specific issues
- [ ] T058 [US7] Fix m_order() collation handling in src/m2py/runtime/helpers.py
- [ ] T059 [US7] Fix m_query() traversal logic if applicable in src/m2py/runtime/helpers.py
- [ ] T060 [US7] Validate traversal tests pass: `uv run pytest tests/functional/ -k "order or query or v1nr" -v`

**Checkpoint**: $ORDER/$QUERY fixed - 3 tests resolved

---

## Phase 13: User Story 11 - Merge Suite Investigation (Priority: P3)

**Goal**: Diagnose and resolve merge suite infrastructure issues

**Independent Test**: Verify merge gbl2gbl subtest produces comparable output

**Affected Tests**: 33 merge suite tests with "No result for X"

### Investigation (⚠️ HUMAN REVIEW REQUIRED for test infrastructure changes)

- [ ] T061 [US11] Analyze merge suite driver structure in tests/functional/merge/u_inref/
- [ ] T062 [US11] Identify helper routines required by each subtest
- [ ] T063 [US11] Debug gbl2gbl subtest to identify infrastructure vs codegen issues
- [ ] T064 [US11] Document findings and propose fix (infrastructure vs m2py changes)
- [ ] T065 [US11] **HUMAN REVIEW**: Present findings before implementing test harness changes
- [ ] T066 [US11] Implement approved fixes (conditional on T065 outcome)
- [ ] T067 [US11] Validate merge tests pass: `uv run pytest tests/functional/test_merge.py -v`

**Checkpoint**: Merge suite diagnosed - 33 tests resolved or properly categorized

---

## Phase 14: Remaining Behavioral Bugs

**Goal**: Resolve all remaining behavioral mismatches (estimated 40-50 tests after prior phases)

**Independent Test**: Full test suite passes with zero failures

### Implementation

- [ ] T068 Triage remaining failures into categories: arithmetic, pattern, control flow, variable, boolean, other
- [ ] T069 Fix remaining arithmetic bugs (batch processing)
- [ ] T070 Fix remaining pattern matching bugs (batch processing)
- [ ] T071 Fix remaining control flow bugs (batch processing)
- [ ] T072 [FR-022] Fix remaining variable storage/retrieval bugs to preserve correct values across scopes
- [ ] T073 [FR-021] Fix remaining boolean/comparison operation bugs to match MUMPS truth semantics
- [ ] T074 Fix any other uncategorized bugs
- [ ] T075 Validate no failures remain: `uv run pytest tests/functional/ -v --tb=short`

**Checkpoint**: All behavioral bugs resolved

---

## Phase 15: Polish & Final Validation

**Purpose**: Ensure all success criteria met

- [ ] T076 Run full test suite and verify zero failures: `uv run pytest tests/functional/ -v`
- [ ] T077 Verify no regressions in previously passing tests
- [ ] T078 Update documentation with any new limitations discovered
- [ ] T079 Final review of 147-test tracking document - all resolved

---

## Dependencies

```mermaid
graph TD
    T001 --> T003
    T004 --> T006
    T005 --> T007
    T006 --> T009
    T007 --> T009
    T009 --> T011
    T010 --> T012
    T011 --> T016
    T012 --> T013
    T013 --> T016
    
    T017 --> T018
    T018 --> T020
    
    T021 --> T022
    T022 --> T023
    T023 --> T025
    
    T026 --> T028
    T027 --> T029
    T028 --> T031
    T029 --> T031
    
    T037 --> T038
    T038 --> T039
    
    T061 --> T064
    T064 --> T065
    T065 --> T066
    T066 --> T067
    
    T016 --> T076
    T020 --> T076
    T025 --> T076
    T031 --> T076
    T039 --> T076
    T044 --> T076
    T050 --> T076
    T055 --> T076
    T060 --> T076
    T067 --> T076
    T075 --> T076
```

## Parallel Execution Opportunities

### Phase 3-6 (P1 Stories) - Can run after Foundational complete:
- US1 (TRAMPOLINE), US9 (Syntax), US2 (Sorts-After), US3 (LHS $PIECE) are independent

### Phase 9-12 (P2 Stories) - Can run in parallel:
- US4 (Arithmetic), US5 (Pattern), US6 (FOR), US7 ($ORDER/$QUERY) are independent

### Within phases:
- Debug tasks marked [P] can run simultaneously
- Implementation tasks often sequential within a story

---

## Summary

| Phase | User Story | Tests Affected | Priority |
|-------|------------|----------------|----------|
| 2 | Foundation | - | - |
| 3 | US1: TRAMPOLINE | 10 | P1 |
| 4 | US9: Syntax | 1 | P1 |
| 5 | US2: Sorts-After | 1 | P1 |
| 6 | US3: LHS $PIECE | 3 | P1 |
| 7 | US10: Expression Types | 2 | P2 |
| 8 | US8: LIM-015 xfail | 12 | P3 |
| 9 | US4: Arithmetic | ~10 | P2 |
| 10 | US5: Pattern | 5 | P2 |
| 11 | US6: FOR Loops | 5 | P2 |
| 12 | US7: $ORDER/$QUERY | 3 | P2 |
| 13 | US11: Merge Suite | 33 | P3 |
| 14 | Remaining | ~50 | P2 |
| **Total** | | **~147** | |

**MVP Scope**: Phases 1-6 (P1 stories) = 15 tests fixed + foundation
