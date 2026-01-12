# Provisional Tasks: Phases 3-13 (Spec 006)

> **⚠️ PROVISIONAL**: These tasks are contingent on Phase 2 spike outcomes. After completing Phase 2 and updating spec/plan with final decisions:
> - If architecture matches these tasks: Merge relevant sections back into tasks.md
> - If architecture changes significantly: Regenerate with `/speckit.tasks`

---

## Phase 3: ASG Extensions

**Purpose**: Add analysis infrastructure before codegen. Per layer separation: codegen must consume complete ASG.

### 3.1 Add `needs_trampoline` Flag

- [ ] T033 Add `needs_trampoline: bool = False` field to MRoutine in src/m2py/asg/elements.py
- [ ] T034 Create `_detect_goto_cycles()` function in src/m2py/analysis/goto_analysis.py
- [ ] T035 Implement DFS cycle detection: build label→label edge graph, detect back edges
- [ ] T036 Call `_detect_goto_cycles()` from `classify_gotos()` to set `needs_trampoline`
- [ ] T037 Add unit tests for cycle detection in tests/unit/analysis/test_goto_analysis.py:
  - Test forward-only pattern (no cycles) → `needs_trampoline=False`
  - Test A→B→A cycle → `needs_trampoline=True`
  - Test A→B→C→B cycle → `needs_trampoline=True`
  - Test loop exit (FOR+GOTO) is not a cycle → `needs_trampoline=False`

### 3.2 Verify Variable Flow Analysis

- [ ] T038 Verify `compute_signatures()` in src/m2py/analysis/variables.py populates `input_variables`/`output_variables` for cross-label cases
- [ ] T039 Add test case: variable set in label A, read in label B after GOTO → should appear in A.output_variables and B.input_variables
- [ ] T040 If gap found: extend variable analysis to track cross-label flow

### 3.3 Update ASG Documentation

- [ ] T041 Update docs/asg/ with new `needs_trampoline` field
- [ ] T042 Document relationship: `has_unstructured_goto` (state machine) vs `needs_trampoline` (trampoline)

**Checkpoint**: Phase 3 complete - ASG provides all info codegen needs

---

## Phase 4: Codegen Infrastructure (User Stories 1-4 Foundation)

**Purpose**: Build shared infrastructure for all cross-label strategies

### 4.1 Strategy Selector

- [ ] T043 Create `_select_goto_strategy()` function in src/m2py/codegen/__init__.py
- [ ] T044 Strategy logic:
  - `has_unstructured_goto=True` → `STATE_MACHINE`
  - `needs_trampoline=True` → `TRAMPOLINE`
  - Neither → `SIMPLE_FUNCTIONS` (current Spec 005 behavior)
- [ ] T045 Add GotoStrategy enum to src/m2py/codegen/enums.py (if not exists)
- [ ] T046 Unit test strategy selection in tests/unit/codegen/test_strategy_selection.py

### 4.2 Shared State Infrastructure (Based on Spike Decision)

- [ ] T047 Create src/m2py/codegen/shared_state.py
- [ ] T048 Implement `generate_routine_state_class()` - builds state class from union of label variables
- [ ] T049 Implement `generate_state_initialization()` - creates initial state for routine entry
- [ ] T050 Unit test state class generation

### 4.3 MArray Implementation (If Spike Confirms)

- [ ] T051 Add MArray class to src/m2py/runtime/__init__.py
- [ ] T052 Implement `__getitem__`, `__setitem__`, `value` property per data-model.md spec
- [ ] T053 Unit test MArray: node value + children, nested access, empty default
- [ ] T054 Integrate MArray with state class generation

**Checkpoint**: Phase 4 complete - infrastructure ready for pattern implementation

---

## Phase 5: User Story 1 - Forward Cross-Label GOTO (Priority: P1) 🎯 MVP

**Goal**: Simple cross-label GOTO from one label to a later label

**Independent Test**: `TEST S X=1 G NEXT Q` / `NEXT W X Q` → outputs "1"

### 5.1 Implementation

- [ ] T055 [US1] Modify `_generate_goto()` in src/m2py/codegen/statements.py:
  - Remove cross-label restriction (currently raises NotImplementedError)
  - Generate return with state tuple for trampoline pattern
  - Generate state transfer for state machine pattern
- [ ] T055a [US1] [FR-005] Handle cross-label GOTO from inside IF/ELSE blocks:
  - Verify condition state is not corrupted by GOTO
  - Test: `TEST I 1 G PASS G FAIL Q` / `PASS W "P" Q` / `FAIL W "F" Q` → "P"
- [ ] T056 [US1] Implement trampoline wrapper in src/m2py/codegen/routine.py:
  - `_labels` dict mapping label name → function
  - Trampoline while loop for dispatch
- [ ] T057 [US1] Implement label functions to receive/return state
- [ ] T058 [US1] Update `generate_routine()` to select pattern and emit appropriate code

### 5.2 Tests

- [ ] T059 [US1] Test forward cross-label: `TEST S X=1 G NEXT Q` / `NEXT W X Q` → "1" (control transfer)
- [ ] T060 [US1] Test skipped code: `TEST G END W "skip" Q` / `END W "end" Q` → "end"
- [ ] T061 [US1] Test variable visibility (also validates US3): `TEST S A=10,B=20 G SUM Q` / `SUM W A+B Q` → "30"
- [ ] T062 [US1] Test multiple labels: `TEST G A Q` / `A G B Q` / `B W "done" Q` → "done"

**Checkpoint**: User Story 1 complete - simple forward cross-label works

---

## Phase 6: User Story 2 - Backward Cross-Label GOTO (Priority: P1)

**Goal**: Cross-label GOTO that creates implicit loop (back to earlier label)

**Independent Test**: `TEST S X=0` / `LOOP S X=X+1 W X I X<3 G LOOP Q` → "123"

### 6.1 Implementation

- [ ] T063 [US2] Ensure cycle detection marks this as `needs_trampoline=True`
- [ ] T064 [US2] Trampoline handles returning to same/earlier label
- [ ] T065 [US2] Test for RecursionError: execute 10,000+ iterations without stack overflow

### 6.2 Tests

- [ ] T066 [US2] Test backward loop: `TEST S X=0` / `LOOP S X=X+1 W X I X<3 G LOOP Q` → "123"
- [ ] T067 [US2] Test iteration count: 10,000 iterations without RecursionError
- [ ] T068 [US2] Test variable state preserved across iterations
- [ ] T069 [US2] Test nested labels with backward: A→B→C→A pattern

**Checkpoint**: User Story 2 complete - cyclic patterns work with trampoline

---

## Phase 7: User Story 3 - Variable Visibility (Priority: P1)

**Goal**: Variables set in one label visible in target label after GOTO

**Independent Test**: `TEST S A(1)=10,A(2)=20 G SUM Q` / `SUM W A(1)+A(2) Q` → "30"

### 7.1 Implementation

- [ ] T070 [US3] State class includes all cross-label variables
- [ ] T071 [US3] Variables from source label packed into state on GOTO
- [ ] T072 [US3] Variables unpacked in target label

### 7.2 Tests

- [ ] T073 [US3] Test simple variable (distinct from T059 by focusing on visibility semantics): `TEST S X=1 G NEXT Q` / `NEXT W X Q` → "1"
- [ ] T074 [US3] Test multiple variables: `TEST S A=1,B=2,C=3 G CALC Q` / `CALC W A+B+C Q` → "6"
- [ ] T075 [US3] Test subscripted locals: `TEST S A(1)=10,A(2)=20 G SUM Q` / `SUM W A(1)+A(2) Q` → "30"
- [ ] T076 [US3] Test modification in target: `TEST S X=1 G ADD Q` / `ADD S X=X+10 W X Q` → "11"
- [ ] T076a [US3] [FR-021] Test NEWed variable isolation: `TEST N X S X=1 G NEXT Q` / `NEXT W X Q` → "" (X not visible - NEWed)
- [ ] T076b [US3] [FR-022] Test formal param isolation: `TEST D SUB(5) Q` / `SUB(X) G SHOW Q` / `SHOW W X Q` → "" (X is local to SUB)
- [ ] T076c [US3] [Edge Case] Test undefined variable on skipped init: `TEST I 0 S X=99 G DONE Q` / `DONE W X Q` → "" (X never set)

**Checkpoint**: User Story 3 complete - variable visibility works

---

## Phase 8: User Story 4 - Cross-Label Loop Exit (Priority: P2)

**Goal**: GOTO from inside FOR loops to label outside FOR (spec US4)

**Independent Test**: `TEST F I=1:1:10 I I=3 G DONE W I` / `DONE W "done" Q` → "12done"

### 8.1 Implementation

- [ ] T077 [US4] [FR-004] Integrate with existing loop exit infrastructure from Spec 005
- [ ] T078 [US4] Cross-label exit: break from FOR, then transfer to target label
- [ ] T079 [US4] Multi-loop cross-label exit: raise _LoopExit, catch, transfer

### 8.2 Tests

- [ ] T080 [US4] Test single FOR exit: `TEST F I=1:1:10 I I=3 G DONE W I` / `DONE W "done" Q` → "12done"
- [ ] T081 [US4] Test nested FOR exit: `TEST F I=1:1:3 F J=1:1:2 W I,J I I=2,J=1 G OUT Q` / `OUT W "!" Q` → "111221!"
- [ ] T082 [US4] Test triple nested exit: `TEST F I=1:1:2 F J=1:1:2 F K=1:1:2 I I=1,J=2,K=1 G OUT W I,J,K Q` / `OUT W "!" Q` → "111112121!"
- [ ] T083 [US4] Test exit target variable access (loop var visible in target)

**Checkpoint**: User Story 4 complete - loop exits to labels work

---

## Phase 9: User Story 5 - Trampoline Pattern (Priority: P2)

**Goal**: Explicit test of trampoline mechanics for cyclic GOTOs (spec US5)

**Independent Test**: Generated Python uses `while label:` dispatch loop

### 9.1 Implementation

- [ ] T084 [US5] Verify trampoline structure in generated code
- [ ] T085 [US5] Verify no Python recursion for cyclic patterns

### 9.2 Tests

- [ ] T086 [US5] Test trampoline generated for cyclic: `needs_trampoline=True` → has `while` dispatch
- [ ] T087 [US5] Test no trampoline for forward-only: `needs_trampoline=False` → no dispatch loop
- [ ] T088 [US5] Test trampoline exits correctly on QUIT/None return
- [ ] T089 [US5] Test 1000+ cyclic iterations without RecursionError (A→B→A pattern)

**Checkpoint**: User Story 5 complete - trampoline mechanics verified

---

## Phase 10: User Story 6 - State Machine Fallback (Priority: P2)

**Goal**: State machine pattern for `has_unstructured_goto=True` routines (spec US6)

**Independent Test**: Backward GOTO to preamble generates match-case

### 10.1 Implementation

- [ ] T090 [US6] Create state machine generator in src/m2py/codegen/state_machine.py
- [ ] T091 [US6] Emit `while True: match state:` pattern
- [ ] T092 [US6] Handle variables in outer scope (not state class)
- [ ] T093 [US6] Integrate with strategy selector: `has_unstructured_goto=True` → state machine

### 10.2 Tests

- [ ] T094 [US6] Test state machine triggers for backward preamble GOTO
- [ ] T095 [US6] Test match-case structure in generated code
- [ ] T096 [US6] Test state transitions execute correctly (A→B→C→EXIT)
- [ ] T097 [US6] Test variables accessible across states

**Checkpoint**: User Story 6 complete - state machine fallback works

---

## Phase 11: User Story 7 - Multiple GOTO Targets (Priority: P3)

**Goal**: Sequential execution of multiple targets: `G A,B,C` (spec US7)

**Independent Test**: `TEST G A,B Q` / `A W "A"` / `B W "B" Q` → "AB" (A has no QUIT, falls through)

### 11.1 Implementation

- [ ] T098 [US7] Modify `_generate_goto()` to handle multiple targets
- [ ] T099 [US7] Generate sequential calls within single trampoline iteration
- [ ] T100 [US7] Handle early exit if any target QUITs

### 11.2 Tests

- [ ] T101 [US7] Test early QUIT stops sequence: `TEST G A,B Q` / `A W "A" Q` / `B W "B" Q` → "A" (per spec: first QUIT stops)
- [ ] T102 [US7] Test fall-through: `TEST G A,B Q` / `A W "A"` / `B W "B" Q` → "AB" (A has no QUIT)
- [ ] T103 [US7] Test three targets all execute: `TEST G A,B,C Q` / `A W "1"` / `B W "2"` / `C W "3" Q` → "123"

**Checkpoint**: User Story 7 complete - multiple targets work

---

## Phase 12: User Story 8 - Strategy Selection (Priority: P2)

**Goal**: Automatic strategy selection with no manual flags (spec US8)

**Independent Test**: Strategy chosen automatically based on ASG analysis

### 12.1 Implementation

- [ ] T104 [US8] Verify strategy selection uses only ASG flags (no user input)
- [ ] T105 [US8] Document selection logic in code comments

### 12.2 Tests

- [ ] T106 [US8] Test simple routine → SIMPLE_FUNCTIONS
- [ ] T107 [US8] Test cyclic routine → TRAMPOLINE
- [ ] T108a [US8] Test irreducible routine → STATE_MACHINE
- [ ] T108b [US8] Test mixed: routine with both cyclic and irreducible → STATE_MACHINE wins

**Checkpoint**: User Story 8 complete - automatic strategy selection

---

## Phase 13: Validation & Documentation

**Purpose**: Full validation against YDB, update documentation

### 13.1 V1GO1.m Validation

- [ ] T109 Generate Python for all V1GO1.m patterns
- [ ] T110 Run generated code against YDB reference: `uv run python utils/validate.py tests/functional/mugj/inref/V1GO1.m`
- [ ] T111 Document any patterns requiring manual review or deferral

### 13.2 Success Criteria Verification

- [ ] T112 SC-001: 100% of cross-label test cases match YDB
- [ ] T113 SC-002: 10,000+ iteration test passes (no RecursionError)
- [ ] T114 SC-003: State machine handles all `has_unstructured_goto=True` patterns
- [ ] T115 SC-004: Run `ast.parse()` on all generated Python files to validate syntax
- [ ] T116 SC-005: Variable visibility tests pass 100%
- [ ] T117 SC-006: Strategy selection is automatic (no manual flags)
- [ ] T118 SC-007: Multiple targets execute in sequence with correct QUIT handling
- [ ] T119a SC-008: Code coverage ≥85% on new codegen additions

### 13.3 Documentation Updates

- [ ] T120 [P] Update docs/codegen/goto_handling.md with cross-label patterns
- [ ] T121 [P] Update docs/limitations.md with Spec 006 deferrals (007, 008, 009)
- [ ] T122 [P] Update docs/architecture.md with trampoline/state machine patterns
- [ ] T123 Update specs/codegen-plan.md: mark Spec 006 deliverables complete
- [ ] T124 Add pre-requisites section to Spec 007 in codegen-plan.md

**Checkpoint**: All validation passes, documentation complete

---

## Dependencies & Execution Order

### Phase Dependencies

```
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
Loop Exit               Trampoline              State Machine
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

### User Story Mapping (Spec → Tasks)

| Spec US | Tasks Phase | Description |
|---------|-------------|-------------|
| US1 | Phase 5 | Forward Cross-Label GOTO |
| US2 | Phase 6 | Backward Cross-Label GOTO |
| US3 | Phase 7 | Variable Visibility |
| US4 | Phase 8 | Cross-Label Loop Exit |
| US5 | Phase 9 | Trampoline Pattern |
| US6 | Phase 10 | State Machine Fallback |
| US7 | Phase 11 | Multiple GOTO Targets |
| US8 | Phase 12 | Strategy Selection |

### Risk Mitigation

| Risk | Mitigation in Tasks |
|------|---------------------|
| Strategy fails V1GO1 | Spikes tested both strategies before commitment |
| Subscripted locals complex | Mini-spike validated before integration |
| ASG gaps | Explicit ASG work before codegen |
| RecursionError | 10,000 iteration test |
| Variable analysis gaps | Verify and extend if needed |
