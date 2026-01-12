# Tasks: Cross-Label Control Flow (Spec 006)

**Input**: Design documents from `/specs/006-cross-label-control-flow/`  
**Prerequisites**: plan.md (complete), spec.md (complete), research.md, data-model.md, quickstart.md

**Organization**: Tasks are grouped by phase, following the spike-first approach from plan.md. User stories map to implementation tasks after spike decisions.

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Test Strategy

Tests are generated in each phase as implementation progresses. Per spec, use embedded pytest strings with `execute_mumps`/`generate_python` fixtures. Generate YDB reference outputs at phase start.

---

## Phase 1: Setup & Research ✅ COMPLETE

**Purpose**: Validate environment, review existing infrastructure, prepare spike

### 1.1 Environment Validation

- [X] T001 Verify YDB Docker image works: `echo -e 'TEST\n write "PASS",!' | docker run --rm -i ydb`
- [X] T002 Verify utils/validate.py works: `uv run python utils/validate.py --code 'TEST W "PASS" Q'` and make improvements to function if needed
- [X] T003 Review existing ASG fields in src/m2py/asg/elements.py (MRoutine, MLabel, MGotoStatement)

### 1.2 ASG Infrastructure Review

- [X] T004 [P] Document current `has_unstructured_goto` flag behavior in src/m2py/analysis/goto_analysis.py
- [X] T005 [P] Document `is_cross_label` flag computation in `_classify_single_goto()`
- [X] T006 [P] Document `goto_type` enum values and when each is set
- [X] T007 [P] Verify `input_variables`/`output_variables` populated on MLabel by variable analysis
- [X] T008 Update research.md section R1 with findings from T003-T007

### 1.3 V1GO1.m Pattern Analysis (Research Only)

- [X] T009 Analyze V1GO1.m patterns: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1GO1.m`
- [X] T010 Count cross-label forward/backward jumps in V1GO1.m
- [X] T011 Identify patterns that are truly irreducible (require state machine)
- [X] T012 Update research.md section R2 with pattern analysis

### 1.4 VistA Production Codebase Analysis (Extended Research)

- [X] T012.1 Create parser-based VistA analysis utility: `utils/analyze_vista_gotos.py`
- [X] T012.2 Run full VistA analysis (33,951 files) with per-module statistics
- [X] T012.3 Document findings in research.md section R2.5
- [X] T012.4 Save detailed JSON report: `specs/006-cross-label-control-flow/vista-analysis.json`

**Key Findings**: V1GO1.m (0% cycles) is NOT representative of VistA (47.5% files with cycles). Trampoline pattern is REQUIRED for correctness, not just an optimization.

**Checkpoint**: Phase 1 complete - all research documented, spike can proceed ✅

---

## Phase 2: Spikes (Decision Phase)

**Purpose**: Prototype strategies, make architecture decisions. This IS implementation - spike code may become production code.

### 2.1 V1GO1.m Strategy Bake-off (REQUIRED)

**Goal**: Determine primary strategy (trampoline vs state machine)

- [ ] T013 Create spike directory: `specs/006-cross-label-control-flow/spikes/`
- [ ] T014 Implement trampoline prototype in spikes/trampoline_v1go1.py
- [ ] T015 Implement state machine prototype in spikes/state_machine_v1go1.py
- [ ] T016 Run both against YDB reference for V1GO1.m patterns
- [ ] T017 Measure: correctness (% patterns passing), line count, complexity
- [ ] T018 Test Rope refactorability: can extract/rename functions in each?
- [ ] T019 Document decision in research.md section R3 with evaluation matrix

### 2.2 Shared State Pattern Evaluation

**Goal**: Choose variable visibility approach for labels-as-functions

- [ ] T020 [P] Test RoutineState class approach in spikes/shared_state_class.py
- [ ] T021 [P] Test outer-scope variables approach in spikes/shared_state_outer.py
- [ ] T022 [P] Test runtime dict approach in spikes/shared_state_runtime.py
- [ ] T023 Evaluate each for: Rope compatibility, clarity, name collision risk
- [ ] T024 Document decision in research.md section R4

### 2.3 Subscripted Locals Mini-Spike (REQUIRED)

**Goal**: Validate MArray approach for cross-label array visibility

- [ ] T025 Create MArray prototype in spikes/marray_spike.py
- [ ] T026 Test case: `S A(1)=10,A(2)=20 G SUM` / `SUM W A(1)+A(2)` → expect "30"
- [ ] T027 Test nested subscripts: `S A=1,A(1)=2,A(1,2)=3` (each node has value AND children)
- [ ] T028 Validate MArray integrates with chosen shared state pattern
- [ ] T029 Document decision in research.md section R5

---

## Next Steps After Phase 2

After completing Phase 2 spikes and updating spec/plan with final decisions:

1. **If architecture matches provisional tasks**: Merge relevant sections from [tasks-phase3-provisional.md](tasks-phase3-provisional.md)
2. **If architecture changes significantly**: Regenerate implementation tasks with `/speckit.tasks`

See [tasks-phase3-provisional.md](tasks-phase3-provisional.md) for detailed Phase 3-13 task breakdown (contingent on spike outcomes).

---

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks (Phases 1-2) | 36 |
| Phase 1 (Setup + Research) | 16 |
| Phase 2 (Spikes) | 20 |
| Parallel Opportunities | 7 tasks marked [P] |

### Decision Gate

After Phase 2, update:
- `research.md` - Document spike findings and decisions
- `plan.md` - Finalize architecture based on spike results
- `spec.md` - Amend if significant scope changes needed

Then proceed to implementation phases.
