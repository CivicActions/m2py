# Tasks: Extended Operators, Commands & Completion

**Input**: Design documents from `/specs/011-operators-commands-completion/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Included inline (TDD approach - tests validate YDB behavior).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)

> **Note on Numbering**: User story IDs (US1-US18) match spec.md numbering. Phase ordering prioritizes by priority level (P1→P2→P3), so US7 (Multiple SET, P1) appears before US4 (Contains/Follows, P2).

## Path Conventions

- **Source**: `src/m2py/codegen/` (expressions.py, statements.py)
- **Runtime**: `src/m2py/runtime/` (__init__.py, helpers.py)
- **Tests**: `tests/unit/codegen/`

---

## Phase 1: Setup ✅

**Purpose**: Verify baseline and prepare for implementation

- [x] T001 Verify existing test suite passes with `uv run pytest tests/unit/codegen/ -v`
- [x] T002 [P] Create test file `tests/unit/codegen/s7_expressions/test_s7_2_logical_operators.py` with failing tests for AND, OR, NOT
- [x] T003 [P] Create test file `tests/unit/codegen/s8_commands/test_s8_2_format_controls.py` with failing tests for `!`, `#`, `?n`, `*n`

---

## Phase 2: Foundational (Blocking Prerequisites) ✅

**Purpose**: Core infrastructure needed by multiple user stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Add `m_truth()` helper import to `src/m2py/codegen/expressions.py` if not present
- [x] T005 [P] Add `m_contains()`, `m_follows()`, `m_sorts_after()` helpers in `src/m2py/runtime/helpers.py`
- [x] T006 [P] Add `m_pattern_match()` helper in `src/m2py/runtime/helpers.py` using `compile_pattern_to_regex()` from `analysis/pattern_compiler.py`
- [x] T007 [P] Add runtime fields `_x`, `_y`, `_stack_level` to `MUMPSRuntime` in `src/m2py/runtime/__init__.py`
- [x] T008 Add `write_tab()` method to `MUMPSRuntime` for column positioning in `src/m2py/runtime/__init__.py`
- [x] T009 [P] Add `horolog()`, `job()`, `io()`, `x()`, `y()`, `stack_level()`, `quit_flag()` methods to `MUMPSRuntime` in `src/m2py/runtime/__init__.py`

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Logical Operators (Priority: P1) ✅

**Goal**: Generate Python for `&`, `!`, `'` with correct boolean logic (0/1, not True/False)

**Independent Test**: `uv run python utils/validate.py --code 'TEST W 1&1,! Q'` outputs "1\n"

### Implementation for User Story 1

- [x] T010 [US1] Fix `_generate_unary_op()` NOT operator to return `int(not m_truth(x))` instead of `not m_truth(x)` in `src/m2py/codegen/expressions.py`
- [x] T011 [US1] Add AND (`&`) operator case to `_generate_binary_op()` returning `int(m_truth(x) and m_truth(y))` in `src/m2py/codegen/expressions.py`
- [x] T012 [US1] Add OR (`!`) operator case to `_generate_binary_op()` returning `int(m_truth(x) or m_truth(y))` in `src/m2py/codegen/expressions.py`
- [x] T013 [US1] Add unit tests for logical operators in `tests/unit/codegen/s7_expressions/test_s7_2_logical_operators.py`
- [x] T014 [US1] Validate all 7 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Logical operators fully functional - `1&1→1`, `1!0→1`, `'1→0`

---

## Phase 4: User Story 2 - String Concatenation (Priority: P1) ✅

**Goal**: Verify/ensure concatenation (`_`) generates working Python

**Independent Test**: `uv run python utils/validate.py --code 'TEST W "A"_"B"_"C",! Q'` outputs "ABC\n"

### Implementation for User Story 2

- [x] T015 [US2] Verify concatenation operator `_` in `_generate_binary_op()` works correctly in `src/m2py/codegen/expressions.py`
- [x] T016 [US2] Add concatenation tests including number coercion (`"X"_1_"Y"`) in `tests/unit/codegen/s7_expressions/test_s7_2_operators.py`
- [x] T017 [US2] Validate all 3 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Concatenation functional - `"A"_"B"→"AB"`, `"X"_1_"Y"→"X1Y"`

---

## Phase 5: User Story 3 - Negated Comparison Operators (Priority: P1) ✅

**Goal**: Generate Python for `'=`, `'<`, `'>` with correct comparison logic

**Independent Test**: `uv run python utils/validate.py --code 'TEST W 5'\''=6,! Q'` outputs "1\n"

### Implementation for User Story 3

- [x] T018 [US3] Add negated equals (`'=`) operator case to `_generate_binary_op()` in `src/m2py/codegen/expressions.py`
- [x] T019 [P] [US3] Add negated less-than (`'<`) and negated greater-than (`'>`) operator cases in `src/m2py/codegen/expressions.py`
- [x] T020 [US3] Add unit tests for negated comparisons in `tests/unit/codegen/s7_expressions/test_s7_2_operators.py`
- [x] T021 [US3] Validate all 4 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Negated comparisons functional - `5'=6→1`, `10'<5→1`

---

## Phase 6: User Story 7 - Multiple SET Assignments (Priority: P1) ✅

**Goal**: Verify SET with multiple assignments generates correct Python

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X=1,Y=2,Z=3 W X,Y,Z,! Q'` outputs "123\n"

### Implementation for User Story 7

- [x] T022 [US7] Verify `_generate_set()` handles list of assignments in `src/m2py/codegen/statements.py`
- [x] T023 [US7] Add multiple assignment tests in `tests/unit/codegen/s8_commands/test_s8_2_18_set.py`
- [x] T024 [US7] Validate all 2 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Multiple SET functional - `S X=1,Y=2,Z=3` generates correct assignments

---

## Phase 7: User Story 8 - WRITE Format Controls (Priority: P1) ✅

**Goal**: Handle `MFormatControl` nodes in `_generate_write()` for `!`, `#`, `?n`, `*n`

**Independent Test**: `uv run python utils/validate.py --code 'TEST W "A",!,"B",! Q'` outputs "A\nB\n"

### Implementation for User Story 8

- [x] T025 [US8] Update `_generate_write()` to detect and dispatch `MFormatControl` nodes in `src/m2py/codegen/statements.py`
- [x] T026 [US8] Implement NEWLINE format control (`!`) in `_generate_write()` in `src/m2py/codegen/statements.py`
- [x] T027 [US8] Implement FORMFEED format control (`#`) in `_generate_write()` in `src/m2py/codegen/statements.py`
- [x] T028 [US8] Implement CHARCODE format control (`*n`) in `_generate_write()` in `src/m2py/codegen/statements.py`
- [x] T029 [US8] Implement TAB format control (`?n`) with `_rt.write_tab()` in `src/m2py/codegen/statements.py`
- [x] T030 [US8] Add format control tests in `tests/unit/codegen/s8_commands/test_s8_2_format_controls.py`
- [x] T031 [US8] Validate all 4 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Format controls functional - `!→\n`, `#→\f`, `*65→A`, `?10→tab to col 10`

---

## Phase 8: User Story 9 - Postconditions (Priority: P1) ✅

**Goal**: Check `stmt.postcondition` and wrap statement in conditional when present

**Independent Test**: `uv run python utils/validate.py --code 'TEST S:1 X=1 W X,! Q'` outputs "1\n"

### Implementation for User Story 9

- [x] T032 [US9] Modify `generate_statement()` to check `postcondition` field in `src/m2py/codegen/statements.py`
- [x] T033 [US9] Wrap statement body in `if m_truth(cond):` when postcondition present in `src/m2py/codegen/statements.py`
- [x] T034 [US9] Add postcondition tests in `tests/unit/codegen/s8_commands/test_s8_1_general_rules.py` and `tests/unit/cross_cutting/test_postconditions.py`
- [x] T035 [US9] Validate all 4 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Postconditions functional - `S:1 X=1` sets X, `S:0 X=1` skips

---

## Phase 9: User Story 17 - Decimal Numeric Literals (Priority: P1) ✅

**Goal**: Verify decimal literals in codegen produce correct Python floats

**Independent Test**: `uv run python utils/validate.py --code 'TEST W 1.5+2.7,! Q'` outputs "4.2\n"

### Implementation for User Story 17

- [x] T036 [US17] Verify `_generate_literal()` handles decimal numbers in `src/m2py/codegen/expressions.py`
- [x] T037 [US17] Add decimal literal tests in `tests/unit/codegen/s7_expressions/test_s7_1_literals.py`
- [x] T038 [US17] Validate all 3 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Decimals functional - `1.5+2.7→4.2`, `.5→0.5`

---

## Phase 10: User Story 4 - Contains and Follows Operators (Priority: P2)

**Goal**: Generate Python for `[` (contains), `]` (follows), `]]` (sorts after)

**Independent Test**: `uv run python utils/validate.py --code 'TEST W "ABC"["B",! Q'` outputs "1\n"

### Implementation for User Story 4

- [x] T039 [US4] Add contains (`[`) operator case to `_generate_binary_op()` in `src/m2py/codegen/expressions.py`
- [x] T040 [P] [US4] Add follows (`]`) operator case to `_generate_binary_op()` in `src/m2py/codegen/expressions.py`
- [x] T041 [P] [US4] Add sorts-after (`]]`) operator case to `_generate_binary_op()` in `src/m2py/codegen/expressions.py`
- [x] T042 [US4] Add contains/follows tests in `tests/unit/codegen/s7_expressions/test_s7_2_string_operators.py`
- [x] T043 [US4] Validate all 7 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: String operators functional - `"ABC"["B"→1`, `"B"]"A"→1`

---

## Phase 11: User Story 5 - Modulo and Integer Division (Priority: P2)

**Goal**: Verify `#` (modulo) and `\` (integer division) work correctly

**Independent Test**: `uv run python utils/validate.py --code 'TEST W 7#3,! Q'` outputs "1\n"

### Implementation for User Story 5

- [x] T044 [US5] Verify modulo (`#`) operator in `_generate_binary_op()` including edge cases (negative numbers: `-7#3`, zero dividend: `0#5`) in `src/m2py/codegen/expressions.py`
- [x] T045 [US5] Verify integer division (`\`) operator in `_generate_binary_op()` including edge cases (negative numbers: `-7\3`, large numbers) in `src/m2py/codegen/expressions.py`
- [x] T046 [US5] Add modulo/intdiv tests in `tests/unit/codegen/s7_expressions/test_s7_2_operators.py`
- [x] T047 [US5] Validate all 4 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Arithmetic operators functional - `7#3→1`, `7\3→2`

---

## Phase 12: User Story 6 - Pattern Match Operator (Priority: P2)

**Goal**: Generate Python for `?` (pattern match) using existing pattern_compiler

**Independent Test**: `uv run python utils/validate.py --code 'TEST W "ABC"?1A.A,! Q'` outputs "1\n"

### Implementation for User Story 6

- [x] T048 [US6] Add pattern match (`?`) operator case to `_generate_binary_op()` using `m_pattern_match()` in `src/m2py/codegen/expressions.py`
- [x] T049 [US6] Add pattern match tests including negated pattern (`X'?1N` = NOT pattern match) in `tests/unit/codegen/s7_expressions/test_s7_2_pattern_match.py`
- [x] T050 [US6] Validate all 4 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Pattern match functional - `"ABC"?1A.A→1`

---

## Phase 13: User Story 16 - Special Variables (Priority: P2)

**Goal**: Generate Python for $HOROLOG, $JOB, $IO, $X, $Y, $STORAGE, $STACK, $QUIT

**Independent Test**: `uv run python utils/validate.py --code 'TEST W $H,! Q'` outputs comma-separated format

### Implementation for User Story 16

- [X] T051 [US16] Add $HOROLOG case to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T052 [P] [US16] Add $JOB case to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T053 [P] [US16] Add $IO case to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T054 [P] [US16] Add $X and $Y cases to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T055 [P] [US16] Add $STORAGE case to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T056 [P] [US16] Add $STACK case to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T057 [P] [US16] Add $QUIT case to `_generate_special_variable()` in `src/m2py/codegen/expressions.py`
- [X] T058 [US16] Add special variable tests in `tests/unit/codegen/s7_expressions/test_s7_3_special_variables.py`
- [X] T059 [US16] Validate all 8 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Special variables functional - `$H→"days,seconds"`, `$J→pid`

---

## Phase 14: User Story 10 - NEW Command (Selective) (Priority: P2)

**Goal**: Generate Python for `N X,Y` that creates proper variable scope boundaries

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X=5 N X W $G(X,"empty"),! Q'` outputs "empty\n"

### Implementation for User Story 10

- [X] T060 [US10] Implement `_generate_new()` for selective NEW in `src/m2py/codegen/statements.py`
- [X] T061 [US10] Handle scope save/restore with try/finally pattern in `src/m2py/codegen/statements.py`
- [X] T062 [US10] Add NEW command tests in `tests/unit/codegen/s8_commands/test_s8_2_12_new.py`
- [X] T063 [US10] Validate all 2 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Selective NEW functional - `N X` makes X undefined locally

---

## Phase 15: User Story 11 - KILL Command (Selective) (Priority: P2)

**Goal**: Ensure KILL command properly deletes variables and descendants

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X=5 K X W $G(X,"gone"),! Q'` outputs "gone\n"

### Implementation for User Story 11

- [x] T064 [US11] Verify `_generate_kill()` handles basic local KILL in `src/m2py/codegen/statements.py`
- [x] T065 [US11] Verify `_generate_kill()` handles subscripted KILL in `src/m2py/codegen/statements.py`
- [x] T066 [US11] Add KILL command tests including edge case (KILL of undefined variable should no-op) in `tests/unit/codegen/s8_commands/test_s8_2_10_kill.py`
- [x] T067 [US11] Validate all 3 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Selective KILL functional - `K X` removes X, `K A(1)` removes subtree

---

## Phase 16: User Story 13 - MERGE Command (Priority: P2)

**Goal**: Generate Python for `M dest=src` that copies variable subtrees

**Independent Test**: `uv run python utils/validate.py --code 'TEST S A(1)=1,A(2)=2,A(3)=3 M B=A W B(1),B(2),B(3),! Q'` outputs "123\n"

### Implementation for User Story 13

- [x] T068 [US13] Implement `_generate_merge()` for local-to-local MERGE in `src/m2py/codegen/statements.py`
- [x] T069 [US13] Implement global-to-local MERGE variant in `src/m2py/codegen/statements.py`
- [x] T070 [US13] Add MERGE command tests in `tests/unit/codegen/s8_commands/test_s8_2_13_merge.py`
- [x] T071 [US13] Validate all 2 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: MERGE functional - `M B=A` copies A tree to B

---

## Phase 17: User Story 12 - Exclusive NEW and KILL (Priority: P3) ✅

**Prerequisites**: Phase 14 (US10 - Selective NEW) and Phase 15 (US11 - Selective KILL) must be complete.

**Goal**: Generate Python for `N (X,Y)` and `K (X,Y)` (operate on all except listed)

**Independent Test**: `uv run python utils/validate.py --code 'TEST S X=1,Y=2 N (X) S Z=3 W $G(X,"n"),$G(Y,"n"),$G(Z,"n"),! Q'` outputs "1none3\n"

### Implementation for User Story 12

- [x] T072 [US12] Implement exclusive NEW `N (X,Y)` in `_generate_new()` in `src/m2py/codegen/statements.py`
- [x] T073 [US12] Implement exclusive KILL `K (X,Y)` in `_generate_kill()` in `src/m2py/codegen/statements.py`
- [x] T074 [US12] Add exclusive NEW/KILL tests in `tests/unit/codegen/s8_commands/test_s8_2_14_new.py` and `test_s8_2_11_kill.py`
- [x] T075 [US12] Validate all 2 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: Exclusive forms functional - `N (X)` keeps X, NEWs everything else

---

## Phase 18: User Story 14 - HANG Command (Priority: P3)

**Goal**: Generate Python for `H seconds` using time.sleep()

**Independent Test**: `uv run python utils/validate.py --code 'TEST H 0.1 W "done",! Q'` outputs "done\n" after brief pause

### Implementation for User Story 14

- [ ] T076 [US14] Implement `_generate_hang()` using `time.sleep()` in `src/m2py/codegen/statements.py`
- [ ] T077 [US14] Add HANG command tests in `tests/unit/codegen/s8_commands/test_s8_2_07_hang.py`
- [ ] T078 [US14] Validate all 2 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: HANG functional - `H 0.5` pauses for 0.5 seconds

---

## Phase 19: User Story 15 - HALT Command (Priority: P3)

**Goal**: Generate Python for argumentless `H` that terminates execution

**Independent Test**: `uv run python utils/validate.py --code 'TEST W "before",! H W "after",! Q'` outputs "before\n" only

### Implementation for User Story 15

- [ ] T079 [US15] Distinguish argumentless HALT from HANG in statement dispatch in `src/m2py/codegen/statements.py`
- [ ] T080 [US15] Implement `_generate_halt()` using `raise SystemExit(0)` in `src/m2py/codegen/statements.py`
- [ ] T081 [US15] Add HALT command tests in `tests/unit/codegen/s8_commands/test_s8_halt.py`
- [ ] T082 [US15] Validate acceptance scenario from spec.md using `utils/validate.py`

**Checkpoint**: HALT functional - `H` (no args) terminates program

---

## Phase 20: User Story 18 - READ Command (Priority: P3)

**Goal**: Generate Python for `R X` and `R X:timeout` that reads user input

**Independent Test**: `echo "hello" | uv run python utils/validate.py --code 'TEST R X W X,! Q'` outputs "hello\n"

### Implementation for User Story 18

- [ ] T083 [US18] Implement `_generate_read()` for basic READ using input() in `src/m2py/codegen/statements.py`
- [ ] T084 [US18] Implement timeout variant `R X:n` with select-based timeout in `src/m2py/codegen/statements.py`
- [ ] T085 [US18] Add READ command tests in `tests/unit/codegen/s8_commands/test_s8_2_20_read.py`
- [ ] T086 [US18] Validate all 2 acceptance scenarios from spec.md using `utils/validate.py`

**Checkpoint**: READ functional - `R X` reads input, `R X:1` has timeout

---

## Phase 21: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T087 [P] Update `docs/coverage-matrix.md` with newly implemented operators and commands
- [ ] T088 [P] Update `docs/limitations.md` if any features remain partial
- [ ] T089 Run full test suite `uv run pytest tests/unit/codegen/ -v` to verify no regressions
- [ ] T090 Run quickstart.md validation scenarios
- [ ] T091 Code cleanup and remove any TODO comments in modified files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **P1 Stories (Phases 3-9)**: All depend on Foundational (Phase 2) completion
- **P2 Stories (Phases 10-16)**: Depend on Foundational (Phase 2) completion
- **P3 Stories (Phases 17-20)**: Depend on Foundational (Phase 2) completion
- **Polish (Phase 21)**: Depends on all user stories being complete

### User Story Dependencies

| Story | Priority | Depends On | Can Parallel With |
|-------|----------|------------|-------------------|
| US1 (Logical Ops) | P1 | Phase 2 | US2, US3, US7, US17 |
| US2 (Concat) | P1 | Phase 2 | US1, US3, US7, US17 |
| US3 (Negated Cmp) | P1 | Phase 2 | US1, US2, US7, US17 |
| US7 (Multiple SET) | P1 | Phase 2 | US1, US2, US3, US17 |
| US8 (Format Ctrl) | P1 | Phase 2, T009 | US9, US17 |
| US9 (Postconditions) | P1 | Phase 2 | US8, US17 |
| US17 (Decimals) | P1 | Phase 2 | US1-US3, US7-US9 |
| US4 (Contains/Follows) | P2 | Phase 2, T005 | US5, US6, US16 |
| US5 (Mod/IntDiv) | P2 | Phase 2 | US4, US6, US16 |
| US6 (Pattern Match) | P2 | Phase 2, T006 | US4, US5, US16 |
| US16 (Special Vars) | P2 | Phase 2, T007/T009 | US10, US11, US13 |
| US10 (NEW) | P2 | Phase 2 | US11, US13 |
| US11 (KILL) | P2 | Phase 2 | US10, US13 |
| US13 (MERGE) | P2 | Phase 2 | US10, US11 |
| US12 (Excl NEW/KILL) | P3 | US10, US11 | US14, US15, US18 |
| US14 (HANG) | P3 | Phase 2 | US15, US18 |
| US15 (HALT) | P3 | Phase 2 | US14, US18 |
| US18 (READ) | P3 | Phase 2 | US14, US15 |

### Parallel Opportunities per Phase

**Phase 2 (Foundational)**:
```bash
# These can run in parallel:
T005, T006, T007, T009  # All [P] marked
```

**Phase 3-9 (P1 Stories)**: Once Phase 2 complete, all P1 stories can start in parallel

**Phase 10-16 (P2 Stories)**: Once Phase 2 complete, all P2 stories can start in parallel

**Phase 13 (US16 - Special Variables)**:
```bash
# These can run in parallel:
T052, T053, T054, T055, T056, T057  # All [P] marked
```

---

## Implementation Strategy

### MVP Scope (Recommended)

**MVP = Phases 1-9 (P1 Stories Only)**

This delivers:
- ✅ Logical operators (`&`, `!`, `'` fixed)
- ✅ String concatenation verification
- ✅ Negated comparisons (`'=`, `'<`, `'>`)
- ✅ Multiple SET assignments
- ✅ WRITE format controls (`!`, `#`, `?n`, `*n`)
- ✅ Postconditions on all commands
- ✅ Decimal numeric literals

**Post-MVP = Phases 10-20 (P2 + P3 Stories)**

### Incremental Delivery

1. **Increment 1**: Phases 1-9 (Core operators + format controls + postconditions)
2. **Increment 2**: Phases 10-12 (String/pattern operators)  
3. **Increment 3**: Phases 13-16 (Special variables + NEW/KILL/MERGE)
4. **Increment 4**: Phases 17-20 (Exclusive forms + HANG/HALT/READ)
5. **Increment 5**: Phase 21 (Polish)

---

## Summary

| Metric | Value |
|--------|-------|
| **Total Tasks** | 91 |
| **Setup Phase** | 3 tasks |
| **Foundational Phase** | 6 tasks |
| **P1 User Stories** | 7 stories, 35 tasks |
| **P2 User Stories** | 7 stories, 32 tasks |
| **P3 User Stories** | 4 stories, 14 tasks |
| **Polish Phase** | 5 tasks |
| **Parallelizable Tasks** | 24 (marked [P]) |
| **MVP Scope** | 44 tasks (Phases 1-9) |
