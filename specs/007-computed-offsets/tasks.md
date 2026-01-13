# Tasks: Computed Offsets & Line Dispatch

**Input**: Design documents from `/specs/007-computed-offsets/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, quickstart.md ✓

**Tests**: Tests are included as this is a transpiler with correctness requirements. Each user story has unit tests for verification.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/m2py/`, `tests/` at repository root
- Based on plan.md structure for this transpiler project

---

## Phase 1: Setup ✅ COMPLETE

**Purpose**: Environment verification and baseline checks

- [X] T001 Verify branch is `007-computed-offsets` and sync environment with `uv sync`
- [X] T002 Run existing GOTO tests to verify baseline: `uv run pytest tests/unit/codegen/s8_commands/test_s8_2_06_goto.py -v` (32 passed, 7 xfailed)
- [X] T003 [P] Verify parser captures offsets: test `MCall.offset` population with ASG dump (NumericLiteral for literals, LocalVariable for variables)

---

## Phase 2: Foundational Infrastructure (US4 Prerequisites) ✅ COMPLETE

**Purpose**: Core line_dispatch.py module that User Story 4 integrates into routine generation

**⚠️ CRITICAL**: This phase builds the line map infrastructure that US4 then integrates into codegen

- [X] T004 [P] Create new module `src/m2py/codegen/line_dispatch.py` with module docstring and imports
- [X] T005 [P] Add `has_offset_calls` detection helper in line_dispatch.py
- [X] T006 Implement `generate_line_map(routine: MRoutine) -> Dict[int, Tuple[str, int]]` in line_dispatch.py
- [X] T007 Implement `generate_line_map_code(line_map, emitter)` to emit `_line_map` dict definition
- [X] T008 Implement `find_next_executable(target_line, line_map)` helper for non-executable line handling
- [X] T009 Add unit tests for line map generation: `TestLineMapGeneration` in tests/unit/codegen/test_line_dispatch.py (19 tests passing)

**Checkpoint**: Foundation ready - line map generation working and tested ✅

---

## Phase 3: User Story 4 - Line-to-Entry Mapping Generation (Priority: P1) 🎯 MVP Core

**Goal**: Code generator builds `_line_map` that enables dispatch by source line number

**Independent Test**: Generate code with offset calls, verify `_line_map` dict present with correct entries

### Implementation for User Story 4

- [X] T010 [US4] Modify `RoutineGenerator._generate_preamble()` in routine.py to call line map generator when routine has offset calls
- [X] T011 [US4] Add logic to detect if routine contains offset calls (check all MCall.offset fields)
- [X] T012 [US4] Generate `_line_map` dict in routine preamble using `generate_line_map_code()`
- [X] T013 [US4] Add unit test: verify generated code contains `_line_map` with correct line→(label, offset) entries
- [X] T014 [US4] Add unit test: verify comment-only and blank lines are excluded from `_line_map`

**Checkpoint**: Line map generation complete - `_line_map` appears in generated Python for routines with offsets ✅

---

## Phase 4: User Story 1 - Literal Offset GOTO (Priority: P1) 🎯 MVP

**Goal**: GOTO statements with literal integer offsets (`G LABEL+3`) produce correct control transfer

**Independent Test**: `G STAR+2` skips to 2nd line after STAR and outputs correct value

### Implementation for User Story 1

- [X] T015 [US1] Modify `_generate_single_target_goto()` in statements.py to detect `target.offset is not None`
- [X] T016 [US1] For TRAMPOLINE strategy with offset: emit `return (label_line + int(offset_expr), state)` instead of label name
- [X] T017 [US1] Use `generate_expr(target.offset, ctx)` for offset expression code generation
- [X] T018 [US1] Modify `_generate_trampoline_code()` in routine.py to handle `int` targets in dispatcher
- [X] T019 [US1] Update dispatcher: `if isinstance(target, int): label, offset = _line_map[target]; func(state, _start_offset=offset)`
- [X] T020 [US1] Modify `_generate_trampoline_label()` to accept `_start_offset=0` parameter
- [X] T021 [US1] Generate offset guards: `if _start_offset <= N:` for each statement in label body
- [X] T022 [US1] Add unit test: `G STAR+2` outputs "2" (skips first 2 lines after label)
- [X] T023 [US1] Add unit test: `G STAR+0` executes label line itself
- [X] T024 [US1] Add YDB validation: `uv run python utils/validate.py --code 'TEST G STAR+2 Q\nSTAR W "0"\n W "1"\n W "2"\n Q'`

**Checkpoint**: Literal offset GOTO working - can dispatch to specific line by integer offset ✅

---

## Phase 5: User Story 2 - Variable Offset GOTO (Priority: P1)

**Goal**: GOTO statements with variable offsets (`G LABEL+N`) evaluate variable at runtime

**Independent Test**: Set N=2, execute `G STAR+N`, verify correct line reached

### Implementation for User Story 2

- [X] T025 [US2] Verify existing implementation handles variables (T016-T017 should already support via `generate_expr`)
- [X] T026 [US2] Add unit test: `S N=2 G STAR+N` outputs "2"
- [X] T027 [US2] Add unit test: `S N=0 G STAR+N` executes label line
- [X] T028 [US2] Add unit test: `F N=0:1:2 D LINE+N` (DO with variable offset in loop)
- [X] T028b [US2] Add unit test: `D SUB+2` returns to caller after QUIT (FR-011 verification)
- [X] T028c [US2] Add unit test: DO+offset executes from offset line through QUIT, then continues caller
- [X] T029 [US2] Add YDB validation for variable offset patterns

**Checkpoint**: Variable offset GOTO and DO working - runtime variable evaluation dispatches correctly ✅

---

## Phase 6: User Story 3 - Arithmetic Offset Expressions (Priority: P2) ✅ COMPLETE

**Goal**: Arithmetic expressions in offsets (`G LABEL+A-B`, `G LABEL+1+1`) evaluate correctly

**Independent Test**: `S A=3,B=1 G STAR+A-B` outputs "2" (3-1=2)

### Implementation for User Story 3

- [X] T030 [US3] Verify existing implementation handles binary ops (T017 should already support via `generate_expr`)
- [X] T031 [US3] Add unit test: `G STAR+1+1` outputs "2" (chained addition)
- [X] T032 [US3] Add unit test: `G STAR+A-B` with A=3, B=1 outputs "2"
- [X] T033 [US3] Add unit test: `G STAR+6/3` outputs "2" (division)
- [X] T034 [US3] Add YDB validation for arithmetic offset expressions

**Checkpoint**: Arithmetic offset expressions working - all basic operators supported ✅

---

## Phase 7: User Story 5 - Invalid Offset Error Handling (Priority: P2) ✅ COMPLETE

**Goal**: Invalid offsets (past end of routine) raise descriptive runtime error

**Independent Test**: `G STAR+100` raises "Entry point STAR+100 not valid" error

### Implementation for User Story 5

- [X] T035 [US5] Add error handling in dispatcher: check if target line exists in `_line_map`
- [X] T036 [US5] If target not in `_line_map` and no next executable, raise ValueError with descriptive message
- [X] T037 [US5] Error message format: "Entry point LABEL+OFFSET not valid" (matches YDB format)
- [X] T038 [US5] Add unit test: `G STAR+100` raises error (literal offset past end)
- [X] T039 [US5] Add unit test: `S N=99 G STAR+N` raises error at runtime (variable offset past end)
- [X] T040 [US5] Add YDB validation to verify error message matches YDB semantics

**Checkpoint**: Invalid offset errors handled - matches YDB error behavior ✅

---

## Phase 8: User Story 6 - Non-Integer Offset Coercion (Priority: P3)

**Goal**: Non-integer offsets truncated to integer using MUMPS numeric coercion

**Independent Test**: `G STAR+2.7` outputs "2" (2.7 truncated to 2)

### Implementation for User Story 6

- [ ] T041 [US6] Verify `int()` wrapper in offset evaluation handles truncation (T016 should include this)
- [ ] T042 [US6] Add unit test: `G STAR+2.7` outputs "2" (float truncated)
- [ ] T043 [US6] Add unit test: `G STAR+2.999` outputs "2" (floor toward zero)
- [ ] T044 [US6] Add YDB validation for non-integer offset coercion

**Checkpoint**: Non-integer offset coercion working - matches MUMPS truncation semantics

---

## Phase 9: User Story 7 - Comment/Blank Line Handling (Priority: P3)

**Goal**: Offset landing on comment/blank line continues to next executable

**Independent Test**: Offset targeting comment line skips to next executable and outputs correct value

### Implementation for User Story 7

- [ ] T045 [US7] Integrate `find_next_executable()` (from T008) into dispatcher for non-executable line handling
- [ ] T046 [US7] In dispatcher, if target not in `_line_map`, call `find_next_executable()` before error
- [ ] T047 [US7] Add unit test: offset landing on comment line continues to next executable
- [ ] T048 [US7] Add unit test: offset landing on blank line continues to next executable
- [ ] T049 [US7] Add YDB validation for comment/blank line handling

**Checkpoint**: Comment/blank line handling working - matches YDB skip behavior

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation

- [ ] T050 [P] Run full test suite: `uv run pytest tests/unit/codegen/ -v`
- [ ] T051 [P] Run V1GO2.m offset tests: `uv run python utils/validate.py tests/functional/mugj/inref/V1GO2.m`
- [ ] T052 Verify generated Python passes `ast.parse()` for all test cases
- [ ] T053 [P] Update `docs/codegen/goto_handling.md` with computed offset architecture
- [ ] T054 [P] Update `specs/codegen-plan.md` to mark Spec 007 deliverables complete
- [ ] T055 Run quickstart.md validation scenarios

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - creates line_dispatch.py module
- **User Story 4 (Phase 3)**: Depends on Foundational - integrates line map into routine generation
- **User Story 1 (Phase 4)**: Depends on US4 - uses line map for dispatch
- **User Story 2 (Phase 5)**: Depends on US1 - same infrastructure, different input type
- **User Story 3 (Phase 6)**: Depends on US1 - same infrastructure, expression evaluation
- **User Story 5 (Phase 7)**: Depends on US1 - adds error handling to dispatcher
- **User Story 6 (Phase 8)**: Depends on US1 - verifies coercion in offset evaluation
- **User Story 7 (Phase 9)**: Depends on US5 - uses find_next_executable from error handling
- **Polish (Phase 10)**: Depends on all user stories complete

### User Story Dependencies

- **User Story 4 (P1)**: FOUNDATIONAL - all other stories depend on line map
- **User Story 1 (P1)**: Depends on US4 - establishes offset dispatch pattern
- **User Story 2 (P1)**: Depends on US1 - same pattern, variable input; includes DO+offset tests (FR-010, FR-011)
- **User Story 3 (P2)**: Depends on US1 - same pattern, expression input
- **User Story 5 (P2)**: Depends on US1 - adds error handling
- **User Story 6 (P3)**: Depends on US1 - verifies coercion
- **User Story 7 (P3)**: Depends on US5 - extends error handling logic

### Within Each User Story

- Core implementation before tests
- Unit tests verify implementation
- YDB validation confirms correctness

### Parallel Opportunities

- T003 (verify parser) can run in parallel with T001-T002
- T004, T005 (new module setup) can run in parallel
- T050-T054 (polish phase) can all run in parallel

---

## Parallel Example: Phase 2 (Foundational)

```bash
# These can run in parallel (different parts of new module):
Task T004: Create module with docstring
Task T005: Add has_offset_calls detection

# Then sequentially:
Task T006: Implement generate_line_map
Task T007: Implement generate_line_map_code
Task T008: Implement find_next_executable
Task T009: Add unit tests
```

---

## Implementation Strategy

### MVP First (User Stories 4 + 1)

1. Complete Phase 1: Setup ✓
2. Complete Phase 2: Foundational (line_dispatch.py module)
3. Complete Phase 3: User Story 4 (line map generation)
4. Complete Phase 4: User Story 1 (literal offset GOTO)
5. **STOP and VALIDATE**: Test with `G STAR+2` pattern
6. Run YDB validation to confirm correct behavior

### Incremental Delivery

1. US4 + US1 → MVP: Literal offset GOTO works
2. Add US2 → Variable offset GOTO works
3. Add US3 → Arithmetic expressions work
4. Add US5 → Error handling for invalid offsets
5. Add US6 + US7 → Edge cases (coercion, comments)
6. Polish → Documentation and final validation

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- US4 is foundational despite being "User Story 4" in spec - must complete first
- US1, US2, US3 share same dispatch infrastructure - incremental additions
- US5, US6, US7 are edge case handling built on US1 foundation
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
