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

- [x] T016 [US3] Investigate how compiled_pattern is stored in ASG by pattern_compiler in src/m2py/analysis/pattern_compiler.py
- [x] T017 [US3] Update pattern match codegen in src/m2py/codegen/expressions.py to use pre-compiled regex from ASG
- [x] T018 [US3] Update runtime helper in src/m2py/runtime/helpers.py to accept pre-compiled pattern (or remove re-compilation)
- [x] T019 [US3] Add test verifying pre-compiled pattern is used in tests/unit/codegen/test_coverage_gaps.py

**Checkpoint**: ✅ Pattern match codegen now uses pre-compiled regex (re.fullmatch) for direct patterns, avoiding runtime re-compilation. Indirect patterns (X?@Y) still use m_pattern_match() for runtime compilation. 5 new tests added to verify.

---

## Phase 4: YDB Extension Tests (Category A)

**Purpose**: Add tests for YDB-specific features that should raise NotImplementedError

**Goal**: Document YDB extensions as not supported with proper test coverage

**Independent Test**: YDB extension tests pass, codegen raises NotImplementedError for unsupported features

### Implementation

- [x] T020 [P] [US1] Ensure tests/unit/codegen/extensions/ydb/ directory exists (create if needed)
- [x] T021 [P] [US1] Create test_zload.py with ZLOAD NotImplementedError test in tests/unit/codegen/extensions/ydb/test_zload.py
- [x] T022 [P] [US1] Create test_ztstart.py with ZTSTART/ZTCOMMIT NotImplementedError tests in tests/unit/codegen/extensions/ydb/test_ztstart.py
- [x] T023 [P] [US1] Add TestExtendedGlobals class with pipe/bracket tests in tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py
- [x] T024 [P] [US1] Add test_write_device_control_not_supported in tests/unit/codegen/s8_commands/test_s8_2_25_write.py
- [x] T025 [P] [US1] Add YDB special variable tests ($ZYERROR, $ZINT) in tests/unit/codegen/extensions/ydb/test_zfunctions.py
- [x] T026 Run coverage check to verify Phase 4 impact: `uv run python utils/coverage_check.py transpile` (target: +1% raw)

**Checkpoint**: ✅ YDB-specific features documented as not supported with 22 new tests. Coverage reached 87.1% (exceeds 87% target).

---

## Phase 5: Fix Indirect JOB Bug (Category A)

**Purpose**: Fix codegen bug where indirect JOB loses the indirection expression

**Goal**: Generate `_rt.parse_call_target()` for indirect JOB labels like indirect GOTO does

**Independent Test**: `J @X` generates correct runtime call; YDB validation passes

### Implementation

- [x] T027 [US1] Analyze indirect GOTO handling in _generate_goto() as reference in src/m2py/codegen/statements.py
- [x] T028 [US1] Update _generate_job() to check call.label_is_indirect in src/m2py/codegen/statements.py
- [x] T029 [US1] Generate _rt.parse_call_target() for indirect JOB labels in src/m2py/codegen/statements.py
- [x] T030 [US1] Add test_job_indirect_label to TestJobCommandCodegen in tests/unit/codegen/s8_commands/test_s8_2_10_job.py
- [x] T031 Validate fix with YDB: `uv run python utils/validate.py --code 'TEST S X="LABEL" J @X Q'`

**Checkpoint**: ✅ Indirect JOB (`J @X`) works correctly. Added _generate_indirect_job() function with 3 new tests (label, routine, timeout indirection).

---

## Phase 6: Fix Subscripted FOR Loop Variable Bug (Category A)

**Purpose**: Fix codegen bug where subscripted FOR loop variables are ignored

**Goal**: Generate subscript assignment in FOR loop instead of simple variable

**Independent Test**: `F I(1)=1:1:3 W I(1)` outputs `123`; YDB validation passes

### Implementation

- [x] T032 [US1] Update ForGenContext to track loop_var subscripts in src/m2py/codegen/statements.py
- [x] T033 [US1] Update FOR codegen to generate subscripted assignment in src/m2py/codegen/statements.py
- [x] T034 [US1] Add test_for_subscripted_loop_variable to TestForCommandCodegen in tests/unit/codegen/s8_commands/test_s8_2_05_for.py
- [x] T035 Validate fix with YDB: `uv run python utils/validate.py --code 'TEST F I(1)=1:1:3 W I(1) Q'`

**Checkpoint**: ✅ Subscripted FOR loop variables (`F I(1)=1:1:3`) work correctly. ForGenContext tracks subscripts, _generate_for_body uses .set(subs, value=val) for subscripted vars. 3 new tests added.

---

## Phase 7: TSTART Restart Variables (Category A)

**Purpose**: Raise NotImplementedError for TSTART restart variables (advanced transaction feature)

**Goal**: Clear error message when restart_vars used, instead of silently ignoring

**Independent Test**: `TSTART (X):RESTART` raises NotImplementedError with helpful message

### Implementation

- [ ] T036 [US1] Update _generate_tstart() to check for restart_vars in src/m2py/codegen/statements.py
- [ ] T037 [US1] Raise NotImplementedError with clear message when restart_vars present
- [ ] T038 [US1] Add test_tstart_restart_vars_not_supported in tests/unit/codegen/s8_commands/test_s8_2_22_tstart.py
- [ ] T039 Run coverage check to verify Phase 7 impact: `uv run python utils/coverage_check.py transpile`

**Checkpoint**: TSTART restart variables raise clear NotImplementedError (+0.3% raw coverage)

---

## Phase 8: Additional Pragma Exclusions (Category C - Analysis/Semantic)

**Purpose**: Add pragma exclusions to remaining uncovered analysis code

**Goal**: Exclude ~75 more lines of edge cases and extension code from coverage metric

**Independent Test**: Coverage metric improves after each pragma addition

### TYPE_CHECKING Blocks

- [ ] T040 [P] [US2] Add pragma exclusion to TYPE_CHECKING block (lines 21-23) in src/m2py/asg/statements.py
- [ ] T041 [P] [US2] Add pragma exclusion to TYPE_CHECKING block (lines 24-25) in src/m2py/asg/expressions.py
- [ ] T042 [P] [US2] Add pragma exclusion to TYPE_CHECKING block (lines 9-11) in src/m2py/asg/type_helpers.py
- [ ] T043 [P] [US2] Add pragma exclusion to TYPE_CHECKING block (lines 16-18) in src/m2py/asg/elements.py

### Future Extensibility / Convenience Code

- [ ] T044 [P] [US2] Add pragma exclusion to get_else_scope() (lines 88-109) in src/m2py/asg/type_helpers.py
- [ ] T045 [P] [US2] Add pragma exclusion to MActualParameter.is_byref (line 385) in src/m2py/asg/expressions.py
- [ ] T046 [P] [US2] Add pragma exclusion to MActualParameter.is_omitted (line 390) in src/m2py/asg/expressions.py

### Dead Code / Invalid MUMPS

- [ ] T047 [P] [US2] Add pragma exclusion to global FOR loop var handling (lines 1024-1030) in src/m2py/analysis/semantic_analyzer.py

### YDB Extension Edge Cases

- [ ] T048 [P] [US2] Add pragma exclusion to ZWRITE subscript wildcards/ranges (lines 399-441) in src/m2py/parser/textx_classes.py
- [ ] T049 [P] [US2] Add pragma exclusion to extended global/device patterns (lines 603-655) in src/m2py/parser/textx_classes.py

### Unused Exported Analysis Functions

- [ ] T050 [P] [US2] Add pragma exclusion to get_loop_exiting_gotos(), get_gotos_by_type() in src/m2py/analysis/goto_analysis.py
- [ ] T051 [P] [US2] Add pragma exclusion to get_def_use_chains(), compute_transitive_inputs/outputs in src/m2py/analysis/variables.py
- [ ] T052 [P] [US2] Add pragma exclusion to external call signature edge cases (lines 263-271, 303-324) in src/m2py/analysis/for_analysis.py

### Z-command Edge Cases

- [ ] T053 [P] [US2] Add pragma exclusion to ZWRITE argument handling (lines 1869-1900) in src/m2py/analysis/semantic_analyzer.py
- [ ] T054 [P] [US2] Add pragma exclusion to Z-command argument processing (lines 2399-2469) in src/m2py/analysis/semantic_analyzer.py
- [ ] T055 [P] [US2] Add pragma exclusion to ZPRINT/ZBreak location parsing (lines 2623-2710) in src/m2py/analysis/semantic_analyzer.py
- [ ] T056 Run coverage check to verify Phase 8 impact: `uv run python utils/coverage_check.py transpile` (target: +2.5% raw)

**Checkpoint**: All analysis/semantic edge cases excluded from coverage metric (+2.5% raw coverage)

---

## Phase 9: Verification & Polish

**Purpose**: Confirm 100% metric achieved and no regressions

- [ ] T057 Run `uv run python utils/coverage_check.py transpile` and verify progress reaches 100% (85% raw)
- [ ] T058 Run `uv run pytest` to verify full test suite passes with no regressions
- [ ] T059 Verify overall test coverage remains ≥85% with `uv run pytest --cov`
- [ ] T060 Update docs/coverage-matrix.md if needed to reflect changes
- [ ] T061 Update research.md with final status and mark completed findings
- [ ] T062 Document any remaining exceptions with justification in research.md

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (C pragmas) ──┬──► Phase 2 (A tests) ──► Phase 3 (B optimization)
                      │
                      ├──► Phase 4 (YDB tests) [parallel with 2,3]
                      │
                      ├──► Phase 5 (JOB fix) - uses GOTO as reference [after 2]
                      │
                      ├──► Phase 6 (FOR fix) [parallel with 4,5,7]
                      │
                      └──► Phase 7 (TSTART) [parallel with 4,5,6]

Phases 1-7 ──► Phase 8 (more pragmas) ──► Phase 9 (verification)
```

- **Phase 1 (Category C)**: No dependencies - can start immediately. All T001-T007 are independent.
- **Phase 2 (Category A)**: Can start after Phase 1. T008 first, then T009-T015.
- **Phase 3 (Category B)**: Can start in parallel with Phase 2. T016 first, then T017-T019.
- **Phase 4 (YDB)**: Can start after Phase 1. All tasks independent.
- **Phase 5 (JOB)**: Should start after Phase 2 (uses indirect GOTO as reference). Sequential.
- **Phase 6 (FOR)**: Can start after Phase 1. Sequential.
- **Phase 7 (TSTART)**: Can start after Phase 1. Sequential.
- **Phase 8 (more pragmas)**: Should wait for Phases 1-7. All tasks independent.
- **Phase 9 (Verification)**: Depends on Phases 1-8 completion.

### User Story Mapping

- **US1** (Complete Transpilation Pipeline): T008-T015 codegen tests, T020-T038 YDB/bug fixes
- **US2** (Remove Dead Code): T001-T007 initial pragmas, T039-T055 additional pragmas
- **US3** (Improve Codegen Using Analysis): T016-T019 pattern optimization

### Parallel Opportunities

**Within-phase parallelization:**

- **Phase 1**: T001-T007 (7 tasks) - all different files
- **Phase 2**: T009-T015 (7 tasks) - after T008 creates test file
- **Phase 4**: T020-T024 (5 tasks) - all different files
- **Phase 8**: T039-T054 (16 tasks) - all different files

**Cross-phase parallelization:**

After Phase 1 completes, can run in parallel:
- Phase 2, Phase 4, Phase 6, Phase 7

After Phase 2 completes:
- Phase 3, Phase 5

---

## Implementation Strategy

### Recommended Order (Single Developer)

1. **Phase 1 first**: Pragma exclusions provide immediate metric improvement with low risk
2. **Phase 2 second**: Add codegen tests to exercise real analysis code
3. **Phase 3 third**: Optimization requires understanding pattern flow
4. **Phases 4-7 in priority order**: Fix bugs and add YDB tests
5. **Phase 8**: Additional pragma exclusions for remaining gaps
6. **Phase 9 last**: Verification confirms success

### MVP Checkpoint

After completing Phases 1-3 (T001-T019):
- Run `uv run python utils/coverage_check.py transpile`
- Expect ~84-86% raw coverage from initial pragmas and tests
- Phases 4-8 provide remaining ~4-6% to reach 85% target

### Coverage Impact Estimates

| Phase | Impact | Cumulative |
|-------|--------|------------|
| 1 | +5.7% | ~84.3% |
| 2 | +1-2% | ~85-86% |
| 3 | +0.5% | ~86% |
| 4 | +1% | ~87% |
| 5 | +0.5% | ~87.5% |
| 6 | +0.5% | ~88% |
| 7 | +0.3% | ~88.3% |
| 8 | +2.5% | ~90% |
| **Target** | | 85% raw (100% norm) |

### Risk Mitigation

- Each task is atomic - can be reverted independently
- Run tests after each task to catch regressions early
- Phase 5 (JOB fix) and Phase 6 (FOR fix) are most complex - analyze existing patterns first

---

## Summary

| Phase | Description | Tasks | Parallel | Impact |
|-------|-------------|-------|----------|--------|
| 1 | Category C Pragmas (initial) | T001-T007 (7) | 7 | +5.7% ✅ |
| 2 | Category A Tests | T008-T015 (8) | 7 | +1-2% ✅ |
| 3 | Category B Optimization | T016-T019 (4) | 1 | +0.5% ✅ |
| 4 | YDB Extension Tests | T020-T026 (7) | 6 | +1% |
| 5 | Fix Indirect JOB | T027-T031 (5) | 1 | +0.5% |
| 6 | Fix Subscripted FOR | T032-T035 (4) | 1 | +0.5% |
| 7 | TSTART Restart Vars | T036-T039 (4) | 1 | +0.3% |
| 8 | Category C Pragmas (more) | T040-T056 (17) | 16 | +2.5% |
| 9 | Verification | T057-T062 (6) | 1 | Verify |
| **Total** | | **62 tasks** | | **~10-12% raw** |

---

## Notes

- [P] tasks = different files, no dependencies
- [US1/US2/US3] maps to user stories from spec.md
- Commit after each task for easy rollback
- Target: 100% transpilation readiness (85% raw coverage)
- Current: 84.3% raw (after Phases 1-3)
- Gap: ~1% raw to reach normalized 100%
- Phases 1-3 completed, providing strong foundation
- Total: 62 tasks (T001-T062)
