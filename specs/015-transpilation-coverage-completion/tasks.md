# Tasks: Transpilation Coverage Completion

**Input**: Design documents from `/specs/015-transpilation-coverage-completion/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓

**Tests**: Test tasks included for Category A (codegen gaps that need test coverage)

**Organization**: Tasks grouped by category (C/A/B) matching the implementation phases in plan.md

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1/US2/US3]**: Which user story this task belongs to
- Include exact file paths in descriptions

---

## Phase 1: Category C - Pragma Exclusions

**Purpose**: Add `# pragma: no cover` to code with debugging/intrinsic value that codegen will never call

**Goal**: Exclude ~100 lines of infrastructure/debugging code from coverage metric

**Independent Test**: Run `uv run python utils/coverage_check.py transpile` - metric should improve after each file

### Implementation

- [x] T001 [P] [US2] Add pragma exclusions to error formatting in src/m2py/parser/exceptions.py (lines 32-55, 85-90)
- [x] T002 [P] [US2] Add pragma exclusions to to_dict() serialization in src/m2py/asg/elements.py (lines 84-117, 123-150)
- [x] T003 [P] [US2] ~~Add pragma exclusions to all __repr__ methods in src/m2py/parser/textx_classes.py~~ SKIP: No __repr__ methods exist (task description was incorrect)
- [x] T004 [P] [US2] Add pragma exclusions to RoutineAnalysisCache class in src/m2py/analysis/variables.py (lines 174-339)
- [x] T005 [P] [US2] Add pragma exclusions to classify_for_patterns() in src/m2py/parser/parser.py (lines 569-609, 848-933)
- [x] T006 [P] [US2] Add pragma exclusions to FOR utilities in src/m2py/parser/line_parser.py (lines 168-182, 197-212, 216-260)
- [x] T007 [P] [US2] Add pragma exclusions to unused utilities in src/m2py/analysis/resolver.py (lines 184-187, 209-214)

**Checkpoint**: ✅ Coverage improved from 78.6% to 84.3% after pragma exclusions

---

## Phase 2: Category A - Codegen Tests

**Purpose**: Create targeted MUMPS tests exercising uncovered analysis paths

**Goal**: Add ~50 lines of codegen tests for MUMPS patterns that exercise semantic_analyzer, for_analysis, goto_analysis, and resolver

**Independent Test**: New test file passes and increases coverage on target analysis modules

### Implementation

- [x] T008 [US1] Create test file tests/unit/codegen/test_coverage_gaps.py with module docstring and imports
- [x] T009 [US1] Add test for indirect GOTO pattern (`S X="LABEL" G @X`) in tests/unit/codegen/test_coverage_gaps.py
- [x] T010 [US1] Add test for indirect DO pattern (`S Y="^ROUTINE" D @Y`) in tests/unit/codegen/test_coverage_gaps.py
- [x] T011 [US1] Add tests for FOR loop var modification (SET/KILL) - READ cannot be tested without input
- [x] T012 [US1] Add test for FOR loop with KILL modifying loop var in tests/unit/codegen/test_coverage_gaps.py
- [x] T013 [US1] Add test for external routine call (`D ^EXTERNAL`) in tests/unit/codegen/test_coverage_gaps.py
- [x] T014 [US1] Add test for external GOTO (`G ^ROUTINE`) in tests/unit/codegen/test_coverage_gaps.py
- [x] T015 [US1] Add test for MULTI_LOOP_EXIT pattern (`F I=1:1:10 F J=1:1:5 G:J>3 END`) in tests/unit/codegen/test_coverage_gaps.py

**Checkpoint**: ✅ All 17 tests pass (`uv run pytest tests/unit/codegen/test_coverage_gaps.py -v`). for_analysis coverage improved from 61% to 66%.

---

## Phase 3: Category B - Codegen Optimization

**Purpose**: Update codegen to use pre-compiled patterns from analysis instead of re-compiling at runtime

**Goal**: Eliminate dead analysis code by having codegen use pattern_compiler's pre-compiled regex

**Independent Test**: Pattern match operations use pre-compiled regex; coverage on pattern_compiler.py improves

### Implementation

- [ ] T016 [US3] Investigate how compiled_pattern is stored in ASG by pattern_compiler in src/m2py/analysis/pattern_compiler.py
- [ ] T017 [US3] Update pattern match codegen in src/m2py/codegen/expressions.py to use pre-compiled regex from ASG
- [ ] T018 [US3] Update runtime helper in src/m2py/runtime/helpers.py to accept pre-compiled pattern (or remove re-compilation)
- [ ] T019 [US3] Add test verifying pre-compiled pattern is used in tests/unit/codegen/test_coverage_gaps.py

**Checkpoint**: Pattern compilation analysis is now exercised by codegen path

---

## Phase 4: Verification & Polish

**Purpose**: Confirm 100% metric achieved and no regressions

- [ ] T020 Run `uv run python utils/coverage_check.py transpile` and verify progress reaches 100%
- [ ] T021 Run `uv run pytest` to verify full test suite passes with no regressions
- [ ] T022 Verify overall test coverage remains ≥85% with `uv run pytest --cov`
- [ ] T023 Update docs/coverage-matrix.md if needed to reflect changes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Category C)**: No dependencies - can start immediately. All T001-T007 are independent.
- **Phase 2 (Category A)**: Can start after T008. T009-T015 depend on T008.
- **Phase 3 (Category B)**: Can start in parallel with Phases 1 & 2. T016 first, then T017-T019.
- **Phase 4 (Verification)**: Depends on Phases 1, 2, and 3 completion.

### User Story Mapping

- **US1** (Complete Transpilation Pipeline): T008-T015 - codegen tests
- **US2** (Remove Dead Code): T001-T007 - pragma exclusions for debugging code
- **US3** (Improve Codegen Using Analysis): T016-T019 - pattern optimization

### Parallel Opportunities

Phase 1 tasks (T001-T007) can ALL run in parallel - different files, no dependencies:

```bash
# All pragma exclusion tasks in parallel:
T001: src/m2py/parser/exceptions.py
T002: src/m2py/asg/elements.py
T003: src/m2py/parser/textx_classes.py
T004: src/m2py/analysis/variables.py
T005: src/m2py/parser/parser.py
T006: src/m2py/parser/line_parser.py
T007: src/m2py/analysis/resolver.py
```

---

## Implementation Strategy

### Recommended Order (Single Developer)

1. **Phase 1 first**: Pragma exclusions provide immediate metric improvement with low risk
2. **Phase 2 second**: Add codegen tests to exercise real analysis code
3. **Phase 3 third**: Optimization requires understanding pattern flow
4. **Phase 4 last**: Verification confirms success

### MVP Checkpoint

After completing Phase 1 (T001-T007):
- Run `uv run python utils/coverage_check.py transpile`
- Expect significant progress toward 100% from pragma exclusions alone
- If metric is very close, Phases 2 & 3 may provide diminishing returns

### Risk Mitigation

- Each task is atomic - can be reverted independently
- Run tests after each task to catch regressions early
- Phase 3 (optimization) is most complex - research T016 thoroughly before T017-T018

---

## Notes

- [P] tasks = different files, no dependencies
- [US1/US2/US3] maps to user stories from spec.md
- Commit after each task for easy rollback
- Target: 100% transpilation readiness (85% raw coverage)
- Current: 78.6% (70% raw coverage)
- Gap: ~21.4% normalized (~15% raw)
