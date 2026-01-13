# Implementation Plan: Cross-Label Control Flow

**Branch**: `006-cross-label-control-flow` | **Date**: 2026-01-11 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/006-cross-label-control-flow/spec.md`

## Summary

Implement cross-label GOTO code generation for MUMPS-to-Python transpilation. This spec extends Spec 005's labels-as-functions pattern to handle GOTOs that cross label boundaries, including:

1. **Forward cross-label jumps** that skip intermediate code
2. **Backward cross-label jumps** creating implicit loops
3. **Variable visibility** across label boundaries via RoutineState class
4. **Trampoline pattern** to prevent stack overflow for ALL cross-label GOTOs
5. **MArray class** for subscripted local variables with MUMPS semantics

**Technical approach**: Spike-first development completed. Decisions made in Phase 2:
- **Execution**: Trampoline pattern (labels as functions returning next label)
- **Shared State**: RoutineState dataclass passed through trampoline
- **Arrays**: MArray class with value + children at each node
- **State machine**: Deferred (trampoline handles all patterns including cycles)

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parsing), pytest (testing), uv (package management)  
**Storage**: N/A (transpiler, no persistence)  
**Testing**: pytest with YDB validation via `utils/validate.py`  
**Target Platform**: Local development (macOS/Linux)
**Project Type**: Single project (library/CLI)  
**Performance Goals**: No specific constraints; correctness > performance  
**Constraints**: Must handle 10,000+ cyclic iterations without RecursionError  
**Scale/Scope**: Single routine translation; batch transpilation out of scope

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Semantic Correctness First | ✅ Pass | All acceptance scenarios validated against YDB |
| II. YDB as Reference | ✅ Pass | Using `validate.py` + Docker YDB image for all tests |
| III. Strict Layer Separation | ✅ Pass | Anticipated ASG gaps documented; fix in ASG first |
| IV. Explicit Over Implicit | ✅ Pass | Variable visibility explicit via shared state pattern |
| V. Foundational Correctness | ✅ Pass | Cross-label GOTO is foundational; tackled early per spec |
| VI. Cross-Cutting Semantics | ✅ Pass | $TEST semantics already handled in Spec 005 |
| VII. Minimize Runtime Surface | ✅ Pass | Prefer inline Python; runtime only for REQUIRES_RUNTIME |
| VIII. Research Before Implementation | ✅ Pass | Spike phase IS first implementation phase |

**Pre-design verdict**: PASS - proceed with Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/006-cross-label-control-flow/
├── plan.md              # This file
├── research.md          # Phase 0 output (spike results)
├── data-model.md        # Phase 1 output (ASG additions)
├── quickstart.md        # Phase 1 output (developer guide)
├── contracts/           # Phase 1 output (function signatures)
└── tasks.md             # Phase 2 output (from /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── asg/
│   └── elements.py              # MRoutine.needs_trampoline (NEW)
├── analysis/
│   ├── goto_analysis.py         # Cycle detection (MODIFY)
│   └── variables.py             # Cross-label flow (VERIFY)
├── codegen/
│   ├── __init__.py              # Strategy selection (MODIFY)
│   ├── routine.py               # Trampoline wrapper (MODIFY)
│   ├── statements.py            # GOTO codegen (MODIFY)
│   └── shared_state.py          # RoutineState class (NEW)
└── runtime/
    └── __init__.py              # MArray class (NEW, if spike confirms)

tests/
├── unit/
│   └── codegen/
│       ├── test_cross_label.py  # NEW - cross-label GOTO tests
│       ├── test_trampoline.py   # NEW - trampoline pattern tests
│       └── test_shared_state.py # NEW - RoutineState/MArray tests
├── integration/
│   └── test_v1go1.py            # NEW - V1GO1.m validation
└── functional/
    └── mugj/inref/
        └── V1GO1.m              # Reference test file (existing)
```

**Structure Decision**: Single project following existing m2py layout. New modules in `codegen/` for shared state; potentially `runtime/` for MArray if spike confirms. Test files organized by pattern under `tests/unit/codegen/`.

## Complexity Tracking

No constitution violations requiring justification. All complexity is inherent to the problem domain (cross-label control flow is the hardest GOTO pattern).

## Phases

### Phase 0: Research & Spikes

**Goal**: Answer key technical questions before committing to implementation approach.

#### 0.1 Environment Validation ✅ COMPLETE

- [x] Verify YDB Docker image works: `echo -e 'TEST\n write 1+2,!' | docker run --rm -i ydb`
- [x] Verify validate.py works: `uv run python utils/validate.py --code 'TEST W "Hi" Q'`
- [x] Confirm Spec 005 infrastructure is complete (run existing tests)

#### 0.2 ASG Structure Review ✅ COMPLETE

- [x] Read `docs/analysis/goto_analysis.md` (if exists)
- [x] Read `docs/asg/` structure documentation
- [x] Inspect `MGotoStatement` fields via `validate.py --debug`
- [x] Document current `is_cross_label`, `goto_type` population
- [x] Verify `input_variables`, `output_variables` availability on MLabel

See [research.md R1](research.md#r1-current-asg-infrastructure) for findings.

#### 0.3 V1GO1.m Strategy Bake-off Spike ✅ COMPLETE

**Input**: `tests/functional/mugj/inref/V1GO1.m`  
**Output**: `research.md` R3 with decision + rationale

**Decision**: TRAMPOLINE PATTERN selected

**Findings**:
- Both patterns pass 30/30 tests
- Trampoline: 412 lines, 38 functions - better refactorability
- State machine: 310 lines - harder to test/refactor individual labels
- VistA analysis (R2.5): 47.5% of files have cycles - trampoline is REQUIRED
- State machine offers no advantage - deferred to future specs

**Shared State Decision**: ROUTINESTATE CLASS selected
- Best Rope refactorability (Rename, Extract, Find References)
- IDE autocomplete catches errors at edit time
- Clean syntax: `s.X` vs `rt.get("X")`

#### 0.4 Subscripted Locals Mini-Spike ✅ COMPLETE

**Goal**: Validate approach for MUMPS arrays (node has value AND children)

**Decision**: MARRAY CLASS selected

**Findings**:
- Cross-label array access verified: `S A(1)=10,A(2)=20 G SUM` / `SUM W A(1)+A(2)` → "30"
- Nested subscripts work: `S A=1,A(1)=2,A(1,2)=3` - each node has value AND children
- Integrates cleanly with RoutineState dataclass
- Methods: `get()`, `defined()`, `kill()` for MUMPS operations
- Clean syntax: `arr[1, 2]` for access, `arr.get(1, 2)` for safe access

### Phase 1: ASG Extensions

**Prerequisites**: Phase 0 spikes complete with documented decisions in `research.md`

#### 1.1 Add `needs_trampoline` to MRoutine

- [ ] Add field to `src/m2py/asg/elements.py`
- [ ] Document in `data-model.md`

#### 1.2 Detect Cross-Label GOTOs

- [ ] Add `_detect_cross_label_gotos()` to `analysis/goto_analysis.py`
- [ ] Set `routine.needs_trampoline = True` if ANY cross-label GOTOs exist
- [ ] Cycle detection is optional (useful for optimization, not strategy selection)
- [ ] Per research R2.5: 47.5% of VistA files have cycles - trampoline handles all

#### 1.3 Verify Variable Flow Analysis

- [ ] Confirm `input_variables` and `output_variables` exist on MLabel
- [ ] Test cross-label variable flow with `validate.py --debug`
- [ ] Document any gaps requiring analysis enhancement

### Phase 2: Codegen Implementation

**Prerequisites**: Phase 1 complete; ASG has all required fields

*Tasks to be populated after spike decision. Stub structure:*

**Note**: Implementation details for Phase 2 are tracked in [tasks.md](tasks.md) Phases 4-13. The sections below are summaries only.

#### 2.1 Shared State Pattern → See tasks.md Phase 4 (T047-T054)

#### 2.2 Strategy Selector → See tasks.md Phase 4 (T043-T046)

#### 2.3 Trampoline Pattern → See tasks.md Phase 5 (T055-T062b)

#### 2.4 State Machine Pattern *(DEFERRED)*

Deferred based on Phase 2 spike results. Trampoline handles all known patterns including cycles. Reconsider if truly irreducible patterns discovered (e.g., computed offsets in Spec 007).

#### 2.5 Cross-Label Variable Visibility → See tasks.md Phase 7 (T070-T076c)

#### 2.6 Multiple GOTO Targets → See tasks.md Phase 11 (T098-T103)

### Phase 3: Validation & Documentation

#### 3.1 V1GO1.m Full Validation

- [ ] Run generated Python against YDB for all V1GO1 patterns
- [ ] Document any patterns requiring manual review
- [ ] Achieve 100% match for supported patterns

#### 3.2 Coverage & Documentation

- [ ] Achieve 85%+ code coverage on new codegen
- [ ] Update `docs/codegen/` with cross-label patterns
- [ ] Update `docs/limitations.md` with deferrals (008, 009)

## Anticipated ASG Gaps

Per spec "ASG Gap Handling" section:

| Gap | Location | What's Needed | Phase |
|-----|----------|---------------|-------|
| `needs_trampoline` flag | `MRoutine` | True if ANY cross-label GOTOs exist | Phase 1.1 |
| Cross-label detection | `goto_analysis.py` | Set flag when cross-label GOTOs found | Phase 1.2 |
| Variable flow verification | `variables.py` | Confirm `input_variables`/`output_variables` work | Phase 1.3 |
| RoutineState field list | `MRoutine` or analysis | All variables needing RoutineState fields | Phase 2.1 |
| MArray variable detection | `variables.py` | Which variables are subscripted arrays | Phase 2.1 |

**Note**: Cycle detection is useful for optimization but NOT required for strategy selection - trampoline handles all cross-label patterns.

**Handling unexpected gaps**: If spike or implementation reveals codegen needs ASG information not available:
1. STOP codegen work
2. Create ASG/analysis task
3. Implement ASG fix
4. Resume codegen

## Out of Scope

See [spec.md "Explicitly Deferred" section](spec.md#explicitly-deferred) for the canonical list of deferred items.

**Key deferrals**:
- Computed offsets (`G LABEL+expr`) → Spec 007
- External routine GOTO (`G LABEL^ROUTINE`) → Spec 008
- Indirect GOTO (`G @VAR`) → Spec 012
- **State machine pattern** → Deferred (trampoline handles all patterns)

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Trampoline fails complex patterns | Very Low | High | VistA analysis validated 47.5% cyclic patterns work |
| Subscripted locals too complex | Low | Low | MArray spike validated approach |
| Variable analysis gaps | Medium | Medium | Verify in Phase 0; fix in analysis layer |
| Performance overhead from trampoline | Low | Low | Acceptable for correctness; optimize later if needed |

## Success Criteria Tracking

| Criterion | Measurement | Target | Status |
|-----------|-------------|--------|--------|
| SC-001 | Cross-label tests vs YDB | 100% match | ⬜ |
| SC-002 | Cyclic iteration test | 10,000+ | ⬜ |
| SC-003 | Trampoline handles all patterns | Including cycles | ⬜ |
| SC-004 | `ast.parse()` validation | All generated Python | ⬜ |
| SC-005 | Variable visibility tests | 100% match | ⬜ |
| SC-006 | Automatic strategy selection | No manual flags | ⬜ |
| SC-007 | Multiple target tests | Sequential + early-exit | ⬜ |
| SC-008 | Code coverage | ≥85% | ⬜ |
