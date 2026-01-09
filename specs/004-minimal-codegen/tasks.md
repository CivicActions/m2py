# Tasks: Minimal Control Flow Foundation

**Input**: Design documents from `/specs/004-minimal-codegen/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure and stub files

- [X] T001 Create `src/m2py/codegen/__init__.py` with `generate_python()` stub
- [X] T002 [P] Create `src/m2py/runtime/__init__.py` with empty module structure

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story

**⚠️ CRITICAL**: All user stories depend on these components

### Value Model Helpers

- [X] T003 Implement `m_num()` in `src/m2py/codegen/helpers.py` (ANSI 7.1.4.5 numeric coercion)
- [X] T004 Implement `m_truth()` in `src/m2py/codegen/helpers.py` (truth evaluation: 0=false, else true)
- [X] T005 Implement `m_compare()` in `src/m2py/codegen/helpers.py` (comparison with coercion)

### Name Translation

- [X] T006 Implement `NameTranslator` class in `src/m2py/codegen/names.py`
  - `translate()`: Handle %, numeric, reserved words, case preservation
  - `reverse()`: Recover original MUMPS name from Python name

### Minimal Runtime

- [X] T007 Implement `MUMPSRuntime` class in `src/m2py/runtime/__init__.py`
  - `write(value)`: Capture output
  - `get_output()`: Return accumulated output
  - `execute()`: Run generated Python code
- [X] T008 Implement `ExecutionResult` dataclass in `src/m2py/runtime/__init__.py`

### Expression Generator

- [X] T009 Create `src/m2py/codegen/expressions.py` with `generate_expr()` function
- [X] T010 Handle `MLiteral` (INTEGER, STRING) in `generate_expr()`
- [X] T011 Handle `MVariable` with name translation in `generate_expr()`
- [X] T012 Handle `MBinaryOp` (+, -, =, <, >) in `generate_expr()`
- [X] T013 Handle `MUnaryOp` (-) in `generate_expr()`

### Statement Generator Base

- [X] T014 Create `src/m2py/codegen/statements.py` with `generate_statement()` function
- [X] T015 Handle `MSetStatement` (single assignment) in `generate_statement()`
- [X] T016 Handle `MWriteStatement` (single value) in `generate_statement()`
- [X] T017 Handle `MQuitStatement` (without value) in `generate_statement()`

### Routine Generator

- [X] T018 Create `src/m2py/codegen/routine.py` with `RoutineGenerator` class
- [X] T019 Implement label → Python function generation in `RoutineGenerator`
- [X] T020 Add module preamble generation (imports, _rt, _test) in `RoutineGenerator`
- [X] T021 Wire `generate_python()` in `__init__.py` to parser + RoutineGenerator

### Test Infrastructure

- [X] T022 Implement `generate_python` fixture in `tests/unit/codegen/conftest.py`
- [X] T023 Implement `execute_mumps` fixture in `tests/unit/codegen/conftest.py`

**Checkpoint**: Foundation ready - user story implementation can begin

---

## Phase 3: User Story 1 - Generate Python from Simple MUMPS Routine (Priority: P1) 🎯 MVP

**Goal**: Pass simple MUMPS routine through code generator, get valid executable Python

**Independent Test**: Generate Python from `TEST S X=1 W X Q`, verify output "1"

### Implementation for User Story 1

- [X] T024 [US1] Add `ast.parse()` validation in `generate_python()` to ensure valid Python
- [X] T025 [US1] Test: `TEST S X=1 W X Q` → generates Python → outputs "1"
- [X] T026 [US1] Test: `TEST W "PASS" Q` → outputs "PASS"
- [X] T027 [US1] Test: `TEST W 2+3 Q` → outputs "5"

**Checkpoint**: User Story 1 complete - can generate and execute simple routines

---

## Phase 4: User Story 2 - IF/ELSE Control Flow (Priority: P1)

**Goal**: Generate IF/ELSE with correct branch execution

**Independent Test**: `TEST S X=5 I X>3 W "GT" Q E W "LE" Q` → "GT"

### Implementation for User Story 2

- [X] T028 [US2] Handle `MIfStatement` in `generate_statement()` - emit `_test = m_truth(cond); if _test:`
- [X] T029 [US2] Handle `MElseStatement` in `generate_statement()` - emit `if not _test:`
- [X] T030 [US2] Test: `S X=5 I X>3 W "GT" E W "LE"` → outputs "GT"
- [X] T031 [US2] Test: `S X=1 I X>3 W "GT" E W "LE"` → outputs "LE"
- [X] T032 [US2] Test: `S X=0 I X W "TRUE" E W "FALSE"` → outputs "FALSE" (zero is false)

**Checkpoint**: User Story 2 complete - IF/ELSE control flow works

---

## Phase 5: User Story 3 - FOR Loop Iteration (Priority: P1)

**Goal**: Generate FOR loops with correct iteration count and values

**Independent Test**: `TEST F I=1:1:3 W I Q` → "123"

### Implementation for User Story 3

- [ ] T033 [US3] Handle `MForStatement` bounded range in `generate_statement()` - emit `for i in range(...)`
- [ ] T034 [US3] Handle end-inclusive semantics (MUMPS includes end, Python excludes)
- [ ] T035 [US3] Handle `MForStatement` string list in `generate_statement()` - emit `for i in [...]`
- [ ] T036 [US3] Test: `F I=1:1:3 W I` → outputs "123"
- [ ] T037 [US3] Test: `F I=5:-1:3 W I` → outputs "543" (negative step)
- [ ] T038 [US3] Test: `F I="A","B","C" W I` → outputs "ABC"

**Checkpoint**: User Story 3 complete - FOR loops iterate correctly

---

## Phase 6: User Story 4 - GOTO to Label (Priority: P2)

**Goal**: Generate GOTO as function call + return

**Independent Test**: `TEST G END Q END W "END" Q` → "END"

### Implementation for User Story 4

- [ ] T039 [US4] Handle `MGotoStatement` in `generate_statement()` - emit `label(); return`
- [ ] T040 [US4] Test: `G DONE` generates `DONE(); return`
- [ ] T041 [US4] Test: `TEST G END Q END W "END" Q` → outputs "END"

**Checkpoint**: User Story 4 complete - GOTO transfers control

---

## Phase 7: User Story 5 - DO Subroutine Call (Priority: P2)

**Goal**: Generate DO as function call that returns to caller

**Independent Test**: `TEST D SUB W "END" Q SUB W "SUB" Q` → "SUBEND"

### Implementation for User Story 5

- [ ] T042 [US5] Handle `MDoStatement` in `generate_statement()` - emit `label()`
- [ ] T043 [US5] Test: `TEST D SUB W "END" Q SUB W "SUB" Q` → outputs "SUBEND"
- [ ] T044 [US5] Test: `TEST D A Q A D B Q B W "B" Q` → outputs "B" (nested)

**Checkpoint**: User Story 5 complete - DO calls and returns work

---

## Phase 8: User Story 6 - MUMPS Value Coercion (Priority: P2)

**Goal**: Coercion edge cases match YDB behavior

**Independent Test**: `TEST I "1A" W "TRUE" E W "FALSE" Q` → "TRUE"

### Implementation for User Story 6

- [ ] T045 [US6] Test: `I "0" W "TRUE" E W "FALSE"` → "FALSE" (string "0" is falsy)
- [ ] T046 [US6] Test: `I "1A" W "TRUE" E W "FALSE"` → "TRUE" (numeric prefix 1 ≠ 0)
- [ ] T047 [US6] Test: `I "A" W "TRUE" E W "FALSE"` → "FALSE" (no prefix = 0)
- [ ] T048 [US6] Test: `I "3A"<5 W "YES" E W "NO"` → "YES" (coerces to 3)
- [ ] T049 [US6] Test: `m_num("")` returns `0`
- [ ] T050 [US6] Test: `m_num("007")` returns `7`

**Checkpoint**: User Story 6 complete - coercion matches MUMPS semantics

---

## Phase 9: User Story 7 - Name Translation (Priority: P3)

**Goal**: Invalid Python identifiers translated correctly

**Independent Test**: Label `%START` generates function `_pct_START`

### Implementation for User Story 7

- [ ] T051 [US7] Test: `%START` label → `_pct_START` function name
- [ ] T052 [US7] Test: variable `0` → `_n_0` Python name
- [ ] T053 [US7] Test: variable `IF` → `_m_IF` (reserved word escape)
- [ ] T054 [US7] Test: case preservation - `FOO`, `Foo`, `foo` all different
- [ ] T055 [US7] Test: reverse translation recovers original names

**Checkpoint**: User Story 7 complete - all MUMPS names translate safely

---

## Phase 10: Polish & Integration

**Purpose**: Final validation and cleanup

- [ ] T056 Run all 7 user story acceptance scenarios against YDB reference
- [ ] T057 Verify `ast.parse()` succeeds for all generated code
- [ ] T058 Run `uv run pytest tests/unit/codegen/` - all tests pass
- [ ] T059 Check coverage ≥85% on codegen module
- [ ] T060 Validate quickstart.md examples work

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    ↓
Phase 2 (Foundational) ← BLOCKS ALL USER STORIES
    ↓
┌───┴───┐
│       │
US1 ──→ US2 ──→ US3  (P1 stories - sequential recommended)
        │
        ↓
    US4, US5, US6    (P2 stories - can parallelize after US1-3)
        │
        ↓
       US7           (P3 story)
        │
        ↓
    Phase 10 (Polish)
```

### Within Each User Story

1. Implementation tasks first
2. Test tasks verify implementation
3. Complete story before moving to next priority

### Parallel Opportunities

**Phase 2 parallelizable tasks**:
- T003, T004, T005 (helpers) - same file, but independent functions
- T006 (names.py) can parallel with T007-T008 (runtime)
- T009-T013 (expressions) can parallel with T014-T017 (statements) after helpers done

**Cross-story parallelization**:
- After Phase 2, different developers can work on different P1 stories
- US4, US5, US6 can parallelize after foundational P1 stories

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| 1 | T001-T002 | Setup module structure |
| 2 | T003-T023 | Foundational (BLOCKING) |
| 3 | T024-T027 | US1: Basic generation (MVP) |
| 4 | T028-T032 | US2: IF/ELSE |
| 5 | T033-T038 | US3: FOR loops |
| 6 | T039-T041 | US4: GOTO |
| 7 | T042-T044 | US5: DO calls |
| 8 | T045-T050 | US6: Coercion |
| 9 | T051-T055 | US7: Name translation |
| 10 | T056-T060 | Polish & validation |

**Total**: 60 tasks
**MVP Scope**: Phases 1-3 (T001-T027) = 27 tasks
