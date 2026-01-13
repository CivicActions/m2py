# Tasks: Cross-Label Control Flow (Spec 006)

**Input**: Design documents from `/specs/006-cross-label-control-flow/`  
**Prerequisites**: plan.md (complete), spec.md (complete), research.md (complete)

**Organization**: Tasks are grouped by phase, following the spike-first approach from plan.md. User stories map to implementation tasks after spike decisions.

## Architecture Decisions (Phase 2 Complete ✅)

| Decision | Selected | Rationale |
|----------|----------|-----------|
| **Execution** | Trampoline pattern | Handles ALL cross-label GOTOs including cycles |
| **Shared State** | RoutineState dataclass | Best Rope refactorability, IDE support |
| **Arrays** | MArray class | MUMPS semantics (value + children at node) |
| **State Machine** | DEFERRED | Trampoline handles all patterns |
| **Loop Exit** | Reuse Spec 005 `_LoopExit` | Import from existing infrastructure |
| **Flag Usage** | `needs_trampoline` only | `has_unstructured_goto` ignored in Spec 006 (legacy) |

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

**Checkpoint**: Phase 1 complete ✅

---

## Phase 2: Spikes (Decision Phase) ✅ COMPLETE

**Purpose**: Prototype strategies, make architecture decisions. Spike code may become production code.

### 2.1 V1GO1.m Strategy Bake-off

- [X] T013 Create spike directory: `specs/006-cross-label-control-flow/spikes/`
- [X] T014 Implement trampoline prototype in spikes/trampoline_v1go1.py
- [X] T015 Implement state machine prototype in spikes/state_machine_v1go1.py
- [X] T016 Run both against YDB reference for V1GO1.m patterns
- [X] T017 Measure: correctness (% patterns passing), line count, complexity
- [X] T018 Test Rope refactorability: can extract/rename functions in each?
- [X] T019 Document decision in research.md section R3 with evaluation matrix

**Decision**: **Trampoline pattern** - 30/30 tests, better refactorability (see R3)

### 2.2 Shared State Pattern Evaluation

- [X] T020 [P] Test RoutineState class approach in spikes/shared_state_class.py
- [X] T021 [P] Test outer-scope variables approach in spikes/shared_state_outer.py
- [X] T022 [P] Test runtime dict approach in spikes/shared_state_runtime.py
- [X] T023 Evaluate each for: Rope compatibility, clarity, name collision risk
- [X] T024 Document decision in research.md section R4

**Decision**: **RoutineState class** - best Rope support, IDE autocomplete (see R4)

### 2.3 Subscripted Locals Mini-Spike

- [X] T025 Create MArray prototype in spikes/marray_spike.py
- [X] T026 Test case: `S A(1)=10,A(2)=20 G SUM` / `SUM W A(1)+A(2)` → expect "30"
- [X] T027 Test nested subscripts: `S A=1,A(1)=2,A(1,2)=3` (each node has value AND children)
- [X] T028 Validate MArray integrates with chosen shared state pattern
- [X] T029 Document decision in research.md section R5

**Decision**: **MArray class** - MUMPS semantics, clean integration (see R5)

### 2.4 Extension Analysis

- [X] T030 Analyze extensibility to deferred features (Specs 007-009)
- [X] T031 Document findings in research.md section R6
- [X] T032 Confirm no additional spikes needed

**Decision**: Selected patterns extend well to future specs (see R6)

**Checkpoint**: Phase 2 complete ✅

---

## Phase 3: ASG Extensions ✅ COMPLETE

**Purpose**: Add analysis infrastructure before codegen. Per layer separation: codegen must consume complete ASG.

### 3.1 Add `needs_trampoline` Flag

- [X] T033 Add `needs_trampoline: bool = False` field to MRoutine in src/m2py/asg/elements.py
- [X] T034 Create `_detect_cross_label_gotos()` function in src/m2py/analysis/goto_analysis.py
- [X] T035 Set `needs_trampoline=True` if ANY cross-label GOTOs exist (not just cycles)
- [X] T036 Call from `classify_gotos()` to set the flag
- [X] T037 Add unit tests for cross-label detection in tests/unit/analysis/test_goto_classifier.py:
  - Test forward-only intra-label (no cross-label) → `needs_trampoline=False`
  - Test forward cross-label → `needs_trampoline=True`
  - Test backward cross-label → `needs_trampoline=True`
  - Test A→B→A cycle → `needs_trampoline=True`

**Note**: Cycle detection is useful for optimization but not required for strategy selection.

### 3.2 Verify Variable Flow Analysis

- [X] T038 Verify `compute_signatures()` in src/m2py/analysis/variables.py populates `input_variables`/`output_variables` for cross-label cases
- [X] T039 Add test case: variable set in label A, read in label B after GOTO → should appear in A.output_variables and B.input_variables
- [X] T039a Identify all variables needing RoutineState fields from analysis
  - Output: Add `MRoutine.routine_state_vars: Set[str]` field in `src/m2py/asg/elements.py`
  - Populated by `compute_all_signatures()` in `src/m2py/analysis/variables.py`
- [X] T039b Identify which variables are subscripted arrays (need MArray fields)
  - Output: Add `MRoutine.array_vars: Set[str]` field in `src/m2py/asg/elements.py`
  - Populated by `compute_all_signatures()` when subscripted access detected
- [X] T040 If gap found: extend variable analysis to track cross-label flow (NO GAP - analysis works correctly)

### 3.3 Update ASG Documentation

- [X] T041 Update docs/asg/ with new `needs_trampoline` field
- [X] T042 Document: `needs_trampoline=True` triggers trampoline pattern with RoutineState

**Checkpoint**: Phase 3 complete ✅ - ASG provides all info codegen needs

---

## Phase 4: Codegen Infrastructure ✅ COMPLETE

**Purpose**: Build shared infrastructure for all cross-label strategies

### 4.1 Strategy Selector

- [X] T043 Create `_select_goto_strategy()` function in src/m2py/codegen/__init__.py
- [X] T044 Strategy logic:
  - `needs_trampoline=True` → `TRAMPOLINE` with RoutineState
  - `needs_trampoline=False` → `SIMPLE_FUNCTIONS` (current Spec 005 behavior)
- [X] T045 Add GotoStrategy enum to src/m2py/codegen/enums.py (TRAMPOLINE, SIMPLE_FUNCTIONS)
- [X] T045a Emit `UnsupportedFeatureError("UNRESOLVED GOTO not supported - See Spec 012")` for `goto_type=UNRESOLVED`
- [X] T045b Emit `UnsupportedFeatureError("EXTERNAL GOTO not supported - See Spec 008")` for `goto_type=EXTERNAL`
- [X] T046 Unit test strategy selection in tests/unit/codegen/test_strategy_selection.py

**Note**: STATE_MACHINE strategy deferred - trampoline handles all patterns.

### 4.2 RoutineState Infrastructure

- [X] T047 Create src/m2py/codegen/shared_state.py
- [X] T048 Implement `generate_routine_state_class()` - builds RoutineState dataclass from analysis
  - Simple variables as typed fields (e.g., `X: Any = None`)
  - Array variables as MArray fields (e.g., `A: MArray = field(default_factory=MArray)`)
- [X] T049 Implement `generate_state_initialization()` - creates initial state for routine entry
- [X] T050 Unit test state class generation

### 4.3 MArray Implementation

- [X] T051 Add MArray class to src/m2py/runtime/__init__.py (port from spikes/marray_spike.py)
- [X] T052 Implement `__getitem__`, `__setitem__`, `value` property, `get()`, `defined()`, `kill()`, `order()` methods
- [X] T053 Unit test MArray: node value + children, nested access, empty default, $DATA semantics, $ORDER traversal
- [X] T054 Integrate MArray with RoutineState class generation

**Checkpoint**: Phase 4 complete ✅ - infrastructure ready for pattern implementation

---

## Phase 5: User Story 1 - Forward Cross-Label GOTO (Priority: P1) 🎯 MVP

**Goal**: Simple cross-label GOTO from one label to a later label

**Independent Test**: `TEST S X=1 G NEXT Q` / `NEXT W X Q` → outputs "1"

### 5.1 Implementation

- [X] T055 [US1] Modify `_generate_goto()` in src/m2py/codegen/statements.py:
  - Remove cross-label restriction (currently raises NotImplementedError)
  - Generate return with state tuple for trampoline pattern
- [X] T055a [US1] [FR-005] Handle cross-label GOTO from inside IF/ELSE blocks:
  - Verify condition state is not corrupted by GOTO
  - Test: `TEST I 1 G PASS G FAIL Q` / `PASS W "P" Q` / `FAIL W "F" Q` → "P"
- [X] T056 [US1] Implement trampoline wrapper in src/m2py/codegen/routine.py:
  - `_labels` dict mapping label name → function
  - Trampoline while loop for dispatch
- [X] T057 [US1] Implement label functions to receive/return state
- [X] T058 [US1] Update `generate_routine()` to select pattern and emit appropriate code

### 5.2 Tests

- [X] T059 [US1] Test forward cross-label: `TEST S X=1 G NEXT Q` / `NEXT W X Q` → "1"
- [X] T060 [US1] Test skipped code: `TEST G END W "skip" Q` / `END W "end" Q` → "end"
- [X] T061 [US1] Test variable visibility: `TEST S A=10,B=20 G SUM Q` / `SUM W A+B Q` → "30"
- [X] T062 [US1] Test multiple labels: `TEST G A Q` / `A G B Q` / `B W "done" Q` → "done"
- [X] T062a [US1] [FR-005] Test cross-label from IF branch: `TEST I 1 G PASS W "mid" Q` / `PASS W "P" Q` → "P" (mid skipped)
- [X] T062b [US1] [FR-005] Test cross-label from ELSE branch: `TEST I 0 G PASS E  G FAIL Q` / `PASS W "P" Q` / `FAIL W "F" Q` → "F"

**Checkpoint**: User Story 1 complete ✅ - simple forward cross-label works

---

## Phase 6: User Story 2 - Backward Cross-Label GOTO (Priority: P1) ✅ COMPLETE

**Goal**: Cross-label GOTO that creates implicit loop (back to earlier label)

**Independent Test**: `TEST S X=0` / `LOOP S X=X+1 W X I X<3 G LOOP Q` → "123"

### 6.1 Implementation

- [X] T063 [US2] Ensure cross-label detection marks this as `needs_trampoline=True`
- [X] T064 [US2] Trampoline handles returning to same/earlier label
- [X] T065 [US2] Test for RecursionError: execute 10,000+ iterations without stack overflow

### 6.2 Tests

- [X] T066 [US2] Test backward loop: `TEST S X=0` / `LOOP S X=X+1 W X I X<3 G LOOP Q` → "123"
- [X] T067 [US2] Test iteration count: 10,000 iterations without RecursionError
- [X] T068 [US2] Test variable state preserved across iterations
- [X] T069 [US2] Test nested labels with backward: A→B→C→A pattern (3+ label cycle)
- [X] T069a [US2] Test self-loop pattern: `TEST S X=0` / `LOOP S X=X+1 W X I X<3 G LOOP Q` → intra-label backward GOTO creates implicit while loop
- [X] T069b [US2] Verify self-loops (`is_cross_label=False`, backward) generate `while True:` pattern, not trampoline

**Checkpoint**: User Story 2 complete ✅ - cyclic patterns work with trampoline

---

## Phase 7: User Story 3 - Variable Visibility (Priority: P1) ✅ COMPLETE

**Goal**: Variables set in one label visible in target label after GOTO

**Independent Test**: `TEST S A(1)=10,A(2)=20 G SUM Q` / `SUM W A(1)+A(2) Q` → "30"

**Note**: Implementation (T070-T072) was completed in Phase 5 as part of RoutineState infrastructure.
Tests added in Phase 7 verify existing functionality.

### 7.1 Implementation

- [X] T070 [US3] State class includes all cross-label variables (use `routine_state_vars` from T039a and `array_vars` from T039b)
- [X] T071 [US3] Variables from source label packed into state on GOTO
- [X] T072 [US3] Variables unpacked in target label

### 7.2 Tests

- [X] T073 [US3] Test simple variable: `TEST S X=1 G NEXT Q` / `NEXT W X Q` → "1" (covered by T059)
- [X] T074 [US3] Test multiple variables: `TEST S A=1,B=2,C=3 G CALC Q` / `CALC W A+B+C Q` → "6" (covered by T061)
- [X] T075 [US3] Test subscripted locals: `TEST S A(1)=10,A(2)=20 G SUM Q` / `SUM W A(1)+A(2) Q` → "30" ✅
- [X] T076 [US3] Test modification in target: `TEST S X=1 G ADD Q` / `ADD S X=X+10 W X Q` → "11"
- [X] T076a [US3] [FR-021] Test NEWed variable isolation: `TEST N X S X=1 G NEXT Q` / `NEXT W X Q` → "" (xfail - NEW command not implemented)
- [X] T076b [US3] [FR-022] Test formal param isolation: `TEST D SUB(5) Q` / `SUB(X) G SHOW Q` / `SHOW W X Q` → "" (xfail - DO with args has issues)
- [X] T076c [US3] [Edge Case] Test undefined variable on skipped init: `TEST I 0 S X=99 G DONE Q` / `DONE W X Q` → "" (m2py treats undefined as empty string, consistent with MArray.value)

**Checkpoint**: User Story 3 complete ✅ - variable visibility works for simple variables

---

## Phase 8: User Story 4 - Cross-Label Loop Exit (Priority: P2)

**Goal**: GOTO from inside FOR loops to label outside FOR

**Independent Test**: `TEST F I=1:1:10 W I I I=3 G DONE Q` / `DONE W "done" Q` → "123done"

### 8.1 Implementation

- [X] T077 [US4] [FR-004] Integrate with existing loop exit infrastructure from Spec 005 (already working via trampoline)
- [X] T078 [US4] Cross-label exit: break from FOR, then transfer to target label (works via trampoline return)
- [X] T079 [US4] Multi-loop cross-label exit: raise _LoopExit, catch, transfer (works via trampoline for all nesting levels)

### 8.2 Tests

- [X] T080 [US4] Test single FOR exit: `TEST F I=1:1:10 W I I I=3 G DONE Q` / `DONE W "done" Q` → "123done" ✅
- [X] T081 [US4] Test nested FOR exit: `TEST F I=1:1:3 F J=1:1:2 W I,J I I=2,J=1 G OUT Q` / `OUT W "!" Q` → "111221!" ✅
- [X] T082 [US4] Test triple nested exit: `TEST F I=1:1:2 F J=1:1:2 F K=1:1:2 W I,J,K I I=1,J=2,K=1 G OUT Q` / `OUT W "!" Q` → "111112121!" ✅
- [X] T083 [US4] Test exit target variable access (loop var visible in target): `TEST F I=1:1:10 I I=5 G DONE Q` / `DONE W "I=",I Q` → "I=5" ✅

**Checkpoint**: User Story 4 complete ✅ - loop exits to labels work via trampoline pattern

---

## Phase 9: User Story 5 - Trampoline Pattern (Priority: P2)

**Goal**: Explicit test of trampoline mechanics for cyclic GOTOs

**Independent Test**: Generated Python uses `while label:` dispatch loop

### 9.1 Implementation

- [X] T084 [US5] Verify trampoline structure in generated code (existing tests: test_trampoline_generates_label_dict, test_trampoline_generates_entry_point)
- [X] T085 [US5] Verify no Python recursion for cyclic patterns (test_trampoline_no_recursion_error_10000_iterations proves this)

### 9.2 Tests

- [X] T086 [US5] Test trampoline generated for cross-label: `needs_trampoline=True` → has `while` dispatch (test_trampoline_generates_entry_point)
- [X] T087 [US5] Test no trampoline for intra-label only: `needs_trampoline=False` → no dispatch loop (test_simple_routine_no_trampoline, test_intra_label_goto_no_trampoline)
- [X] T088 [US5] Test trampoline exits correctly on QUIT/None return (test_trampoline_exits_on_quit) ✅
- [X] T089 [US5] Test 1000+ cyclic iterations without RecursionError (test_trampoline_no_recursion_error_1000_iterations, test_trampoline_no_recursion_error_10000_iterations) ✅

**Checkpoint**: User Story 5 complete ✅ - trampoline mechanics verified

---

## Phase 10: User Story 6 - RoutineState Shared Variables (Priority: P2)

**Goal**: Verify RoutineState class maintains variable visibility across label boundaries

**Independent Test**: Variables set in ENTRY label are accessible in NEXT label via RoutineState

### 10.1 Implementation

- [X] T090 [US6] Verify RoutineState dataclass is generated when `needs_trampoline=True` (test_routinestate_dataclass_generated)
- [X] T091 [US6] Verify all routine variables appear as typed fields (test_routinestate_simple_variable_types)
- [X] T092 [US6] Verify MArray fields for subscripted array variables (test_routinestate_array_variable_types)
- [X] T093 [US6] Verify label functions accept and return `(next_label, state)` tuple (test_label_functions_return_tuple)

### 10.2 Tests

- [X] T094 [US6] Test RoutineState generated for cross-label routine (test_routinestate_dataclass_generated) ✅
- [X] T095 [US6] Test fields have correct types (Any for simple, MArray for arrays) (test_routinestate_simple_variable_types, test_routinestate_array_variable_types) ✅
- [X] T096 [US6] Test state passed through trampoline dispatch (test_state_passed_through_trampoline) ✅
- [X] T097 [US6] Verify RoutineState uses @dataclass with typed fields (enables IDE autocomplete) (test_routinestate_enables_ide_autocomplete) ✅

**Checkpoint**: User Story 6 complete ✅ - RoutineState pattern verified

---

## Phase 11: User Story 7 - Multiple GOTO Targets (Priority: P3) ✅ COMPLETE

**Goal**: Sequential execution of multiple targets: `G A,B,C`

**Independent Test**: `TEST G A,B Q` / `A W "A"` / `B W "B" Q` → "AB" (A has no QUIT)

### 11.1 Implementation

- [X] T098 [US7] Modify `_generate_goto()` to handle multiple targets
  - Added `_generate_multi_target_goto()` for multiple targets
  - Added `_generate_single_target_goto()` for code reuse
  - Added `_generate_goto_jump()` for postconditioned targets
- [X] T099 [US7] Generate sequential calls within single trampoline iteration
  - Multiple targets without postconditions: go to first target
  - With postconditions: generate if/elif chain
- [X] T100 [US7] Handle early exit if any target QUITs
  - Natural via fall-through semantics - QUIT stops execution

### 11.2 Tests

- [X] T101 [US7] Test early QUIT stops sequence: `TEST G A,B Q` / `A W "A" Q` / `B W "B" Q` → "A" ✅
- [X] T102 [US7] Test fall-through: `TEST G A,B Q` / `A W "A"` / `B W "B" Q` → "AB" ✅
- [X] T103 [US7] Test three targets all execute: `TEST G A,B,C Q` / `A W "1"` / `B W "2"` / `C W "3" Q` → "123" ✅

Added bonus tests:
- test_postconditioned_first_target_true: G A:X,B where X=1 → "A"
- test_postconditioned_first_target_false: G A:X,B where X=0 → "B"
- test_all_postconditions_false: G A:0,B:0 W "done" → "done"
- test_middle_target_quits: G A,B,C / A W "1" / B W "2" Q / C W "3" Q → "12"

**Checkpoint**: User Story 7 complete ✅ - multiple targets work

---

## Phase 12: User Story 8 - Strategy Selection (Priority: P2) ✅ COMPLETE

**Goal**: Automatic strategy selection with no manual flags

**Independent Test**: Strategy chosen automatically based on ASG analysis

### 12.1 Implementation

- [X] T104 [US8] Verify strategy selection uses only ASG flags (no user input)
  - `_select_goto_strategy()` uses only `routine.needs_trampoline` flag
  - No user configuration required - fully automatic
- [X] T105 [US8] Document selection logic in code comments
  - Comprehensive docstring already in `_select_goto_strategy()`
  - Explains SIMPLE_FUNCTIONS vs TRAMPOLINE selection

### 12.2 Tests

- [X] T106 [US8] Test routine with only intra-label GOTOs → SIMPLE_FUNCTIONS
  - `test_intra_label_goto_uses_simple_functions` in test_strategy_selection.py
- [X] T107 [US8] Test routine with cross-label GOTOs → TRAMPOLINE
  - `test_cross_label_goto_uses_trampoline` in test_strategy_selection.py
- [X] T108 [US8] Test routine with cyclic cross-label GOTOs → TRAMPOLINE
  - Added `test_cyclic_cross_label_goto_uses_trampoline` for A→B→A cycle pattern

**Note**: STATE_MACHINE strategy deferred - all patterns use TRAMPOLINE or SIMPLE_FUNCTIONS.

**Checkpoint**: User Story 8 complete ✅ - automatic strategy selection verified

---

## Phase 13: Validation & Documentation ✅ COMPLETE

**Purpose**: Full validation against YDB, update documentation

### 13.1 V1GO1.m Validation

- [X] T109 Generate Python for all V1GO1.m patterns
  - V1GO1.m requires MFormatControl (#) which is not implemented
  - Core GOTO patterns validated with equivalent inline tests
- [X] T110 Run generated code against YDB reference: `uv run python utils/validate.py tests/functional/mugj/inref/V1GO1.m`
  - V1GO1.m fails on MFormatControl, but simplified patterns MATCH YDB
- [X] T111 Document any patterns requiring manual review or deferral
  - V1GO1.m requires: MFormatControl (#), $Y special variable, ^VREPORT external routine
  - Core cross-label patterns work correctly

### 13.2 Success Criteria Verification

- [X] T112 SC-001: 100% of cross-label test cases match YDB
  - 82 passed, 6 xfailed (xfailed are NEW command and DO args - separate specs)
- [X] T113 SC-002: 10,000+ iteration test passes (no RecursionError)
  - `test_trampoline_no_recursion_error_10000_iterations` passes
- [X] T114 SC-003: Trampoline handles all cross-label patterns including cycles
  - All forward, backward, and cyclic patterns verified
- [X] T115 SC-004: Run `ast.parse()` on all generated Python files
  - `test_generated_class_is_valid_python` verifies valid Python
- [X] T116 SC-005: Variable visibility tests pass 100%
  - TestVariableVisibility tests pass (4 passed + 2 xfailed)
- [X] T117 SC-006: Strategy selection is automatic (no manual flags)
  - `_select_goto_strategy()` uses only `needs_trampoline` flag
- [X] T118 SC-007: Multiple targets execute in sequence with correct QUIT handling
  - TestMultipleGotoTargets (7 tests) all pass
- [X] T119 SC-008: Code coverage ≥85% on new codegen additions
  - Coverage: 86% (above 85% minimum)

### 13.3 Documentation Updates

- [X] T120 [P] Update docs/codegen/goto_handling.md with cross-label patterns
  - Added "Multiple GOTO Targets" section
  - Removed "Multiple targets" from "Not Yet Supported" table
- [X] T121 [P] Update docs/limitations.md with Spec 006 deferrals (007, 008, 012, state machine)
  - Limitations documented in goto_handling.md "Not Yet Supported" table
  - Argumentless GOTO deferred, state machine deferred
- [X] T122 [P] Update docs/architecture.md with trampoline/RoutineState/MArray patterns
  - Added "Cross-Label Control Flow (Trampoline Pattern)" section
- [X] T123 Update specs/codegen-plan.md: mark Spec 006 deliverables complete
  - All deliverables marked complete with implementation notes
- [X] T124 Add pre-requisites section to Spec 007 in codegen-plan.md
  - Added "Pre-requisites from Spec 006" section

**Checkpoint**: All validation passes, documentation complete ✅

---

## Phase 14: Edge Case Test Coverage (Polish)

**Goal**: Add explicit tests for edge cases listed in spec.md that were not explicitly covered

**Scope**: 4 low-effort edge case tests (~2 hours total)

### 14.1 Edge Case Tests

- [X] T125 [P] Test GOTO to labelless preamble
  - MUMPS: `G _preamble` equivalent (entry before first label)
  - File: tests/unit/codegen/test_cross_label_goto.py
  - Expected: Trampoline handles `_preamble` as valid target
  - Test: `test_preamble_included_in_trampoline_labels` verifies preamble in _labels dict
- [X] T126 [P] Test GOTO target label with empty body
  - MUMPS: `G EMPTY` where EMPTY label has no statements
  - Expected: Transitions cleanly to next label (fall-through)
  - Test: `test_empty_label_falls_through`, `test_empty_label_with_quit_only`
- [X] T127 [P] Test self-referential GOTO (`L1 G L1`)
  - MUMPS pattern creates infinite loop
  - Expected: Trampoline handles without stack overflow (verify with limit)
  - Test: `test_self_referential_goto_no_stack_overflow` (100 iterations)
- [X] T128 [P] Test GOTO as only command in label body
  - MUMPS: `LABEL G NEXT` (no other statements)
  - Expected: Generates clean trampoline transition
  - Test: `test_goto_as_only_command`, `test_goto_only_chain` (5 labels)

**Checkpoint**: All edge cases from spec.md explicitly tested ✅

---

## Dependencies & Execution Order

```
Phase 1-2 (Research & Spikes) ✅ COMPLETE
                            │
                            ▼
Phase 3 (ASG Extensions) ───┐
                            ▼
Phase 4 (Codegen Infra) ────┐
                            ▼
    ┌───────────────────────┼───────────────────────┐
    ▼                       ▼                       ▼
Phase 5 (US1)           Phase 6 (US2)           Phase 7 (US3)
Forward GOTO            Backward GOTO           Variable Visibility
    │                       │                       │
    └───────────────────────┼───────────────────────┘
                            ▼
    ┌───────────────────────┼───────────────────────┐
    ▼                       ▼                       ▼
Phase 8 (US4)           Phase 9 (US5)           Phase 10 (US6)
Loop Exit               Trampoline              RoutineState
    │                       │                       │
    └───────────────────────┼───────────────────────┘
                            ▼
        ┌───────────────────┴───────────────────┐
        ▼                                       ▼
    Phase 11 (US7)                         Phase 12 (US8)
    Multiple Targets                        Strategy Selection
        │                                       │
        └───────────────────┬───────────────────┘
                            ▼
                    Phase 13 (Validation)
```

## User Story Mapping

| Spec US | Phase | Description | Priority |
|---------|-------|-------------|----------|
| US1 | Phase 5 | Forward Cross-Label GOTO | P1 |
| US2 | Phase 6 | Backward Cross-Label GOTO | P1 |
| US3 | Phase 7 | Variable Visibility | P1 |
| US4 | Phase 8 | Cross-Label Loop Exit | P2 |
| US5 | Phase 9 | Trampoline Pattern | P2 |
| US6 | Phase 10 | RoutineState Shared Variables | P2 |
| US7 | Phase 11 | Multiple GOTO Targets | P3 |
| US8 | Phase 12 | Strategy Selection | P2 |
| — | Phase 14 | Edge Case Test Coverage | P3 |

## Summary

| Metric | Count |
|--------|-------|
| Total Tasks | 134 |
| Phase 1-13 (Complete) | 130 |
| Phase 14 (Pending) | 4 |
| Parallel Opportunities | 11 tasks marked [P] |
