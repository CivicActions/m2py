# Feature Specification: Cross-Label Control Flow

**Feature Branch**: `006-cross-label-control-flow`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: Spec 006 from codegen-plan.md - Cross-Label Control Flow

## Overview

This specification extends the code generation infrastructure from Spec 005 to handle GOTO patterns that cross label boundaries. This is the **highest complexity** area of the codegen plan because:

1. **Cross-label jumps break the labels-as-functions model** - Variables set in one label must be visible in another
2. **Backward cross-label jumps create implicit loops** - Requires restructuring or state machine
3. **Forward cross-label jumps not in loops** - Cannot use simple if/else restructuring
4. **Stack growth with naive function calls** - Repeated GOTO creates RecursionError without trampoline

The spec establishes the code generation strategy:
- **Labels-as-functions with trampoline** - Required for cross-label GOTOs, preserves refactorability
- **RoutineState class** - Shared state passed through trampoline for variable visibility
- **MArray class** - Subscripted local variables with MUMPS semantics (value AND children at each node)

**Note**: State machine pattern was evaluated in research (R3) but found unnecessary - trampoline handles all patterns including cycles. State machine is deferred to future specs if truly irreducible patterns are discovered.

## Pre-requisites from Spec 004/005

The following infrastructure is now available:

- `MRoutine.has_unstructured_goto` flag set by `classify_gotos()` analysis
- `MGotoStatement.is_cross_label` flag indicating label boundary crossing
- `MGotoStatement.goto_type` classification (FORWARD_JUMP, BACKWARD_JUMP, etc.)
- Labels as Python functions callable via `LABEL()` / `return LABEL()`
- Intra-label forward GOTO restructuring to if/else
- Loop exit patterns (`break`, `raise _LoopExit()`)
- `NameTranslator` for variable/label name translation
- `FunctionSignature.input_variables` and `output_variables` per label from variable analysis
- `MUMPSRuntime.execute()` with isolated namespace injection

### Key Limitation Discovered in Spec 004/005

Current pattern `return LABEL()` causes stack growth for repeated cross-label GOTO:
```python
def A(): 
    return B()  # Calls B, which calls C, which calls A -> stack grows
def B():
    return C()
def C():
    return A()  # Back to A but stack depth = 3 now
```

This means **trampoline pattern is required** for cross-label GOTO to avoid RecursionError.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cross-Label Forward Jump (Priority: P1)

As a developer, when I generate Python from MUMPS code with GOTO statements that target a later label, the code generator produces correct control transfer that skips intermediate code between the GOTO and target label.

**Why this priority**: Forward cross-label GOTOs are the most common pattern in real MUMPS code. They're used for early exit, error handling, and branching logic. Getting this wrong breaks basic program flow.

**Independent Test**: Can be tested by generating and executing code with forward cross-label GOTOs and verifying intermediate code is skipped.

**Acceptance Scenarios**:

1. **Given** `TEST S X=1 G NEXT S X=99 Q` / `NEXT W X Q`, **When** generated and executed, **Then** output is "1" (X=99 skipped, control jumps to NEXT)
2. **Given** `TEST S X=5 G A Q` / `A S Y=X*2 G B Q` / `B W Y Q`, **When** generated and executed, **Then** output is "10" (chained cross-label GOTOs work)
3. **Given** `TEST S X=1 I X=1 G PASS G FAIL Q` / `PASS W "P" Q` / `FAIL W "F" Q`, **When** generated and executed, **Then** output is "P" (conditional forward jump)

---

### User Story 2 - Cross-Label Backward Jump Creating Implicit Loop (Priority: P1)

As a developer, when I generate Python from MUMPS code with GOTO statements that target an earlier label, the code generator correctly creates an implicit loop structure that iterates until a terminating condition.

**Why this priority**: Backward GOTOs are used throughout legacy MUMPS code to create loops before FOR existed or for patterns that don't fit FOR semantics. Many VistA routines use this pattern.

**Independent Test**: Can be tested by executing generated code with backward GOTOs and verifying correct iteration count and termination.

**Acceptance Scenarios**:

1. **Given** `TEST S X=0` / `LOOP S X=X+1 W X I X<5 G LOOP Q`, **When** generated and executed, **Then** output is "12345" (backward GOTO creates loop)
2. **Given** `TEST S I=0` / `LOOP S I=I+1 W I I I<3 G LOOP W "END" Q`, **When** generated and executed, **Then** output is "123END" (loop terminates and continues)
3. **Given** `TEST S A=1,B=1` / `FIB W A," " S T=A+B,A=B,B=T I A<100 G FIB Q`, **When** generated and executed, **Then** output is "1 1 2 3 5 8 13 21 34 55 89 " (Fibonacci sequence via backward GOTO)

---

### User Story 3 - Cross-Label Variable Visibility (Priority: P1)

As a developer, when I generate Python from MUMPS code with cross-label GOTOs, variables set before the GOTO remain visible in the target label without explicit parameter passing, matching MUMPS semantics.

**Why this priority**: MUMPS variables have dynamic scope - they're visible to callees unless NEWed. Cross-label GOTOs inherit this visibility. Incorrect handling would break most real programs.

**Independent Test**: Can be tested by setting variables before GOTO and reading them in target label.

**Acceptance Scenarios**:

1. **Given** `TEST S X=1,Y=2 G NEXT Q` / `NEXT S Z=X+Y W Z Q`, **When** generated and executed, **Then** output is "3" (X, Y visible in NEXT)
2. **Given** `TEST S X=5 G A Q` / `A S X=X+1 G B Q` / `B W X Q`, **When** generated and executed, **Then** output is "6" (X modified across labels)
3. **Given** `TEST S A(1)=10,A(2)=20 G SUM Q` / `SUM W A(1)+A(2) Q`, **When** generated and executed, **Then** output is "30" (subscripted variables visible)

---

### User Story 4 - Cross-Label GOTO from Nested FOR Loops (Priority: P2)

As a developer, when I generate Python from MUMPS code with GOTO inside nested FOR loops that targets a label outside the loops, the code generator correctly exits all enclosing loops and transfers control to the target label.

**Why this priority**: This combines loop exit mechanics with cross-label transfer. It's a common error-handling pattern in MUMPS.

**Independent Test**: Can be tested by executing code with nested loops containing cross-label GOTOs.

**Acceptance Scenarios**:

1. **Given** `TEST F I=1:1:3 F J=1:1:2 W I,J I I=2,J=1 G OUT Q` / `OUT W "!" Q`, **When** generated and executed, **Then** output is "111221!" (exits both loops at I=2,J=1)
2. **Given** `TEST F I=1:1:5 I I=3 G DONE W I Q` / `DONE W "X" Q`, **When** generated and executed, **Then** output is "12X" (single loop exit to label)
3. **Given** `TEST F I=1:1:2 F J=1:1:2 F K=1:1:2 I I=1,J=2,K=1 G OUT W I,J,K Q` / `OUT W "!" Q`, **When** generated and executed, **Then** output is "111112121!" (triple nested loop exit)

---

### User Story 5 - Trampoline Pattern for Cyclic GOTOs (Priority: P2)

As a developer, when I generate Python from MUMPS code with cyclic cross-label GOTOs (A->B->C->A), the code generator uses a trampoline pattern that prevents Python stack overflow regardless of iteration count.

**Why this priority**: Without trampoline, cyclic GOTOs cause RecursionError. Many state-machine-like MUMPS patterns are cyclic.

**Independent Test**: Can be tested by executing code with cyclic GOTOs for many iterations (>1000) without stack overflow.

**Acceptance Scenarios**:

1. **Given** cyclic GOTO pattern `A->B->A` running 1000 iterations, **When** generated and executed, **Then** completes without RecursionError
2. **Given** routine with cyclic cross-label pattern, **When** generated, **Then** `needs_trampoline=True` and uses trampoline wrapper
3. **Given** simple forward-only routine with no cross-label GOTOs, **When** generated, **Then** `needs_trampoline=False` and does NOT emit trampoline overhead

---

### User Story 6 - RoutineState Shared Variables (Priority: P2)

As a developer, when I generate Python from MUMPS routines with cross-label GOTOs, all labels share a common RoutineState class that maintains variable visibility across label boundaries.

**Why this priority**: MUMPS variables are visible across labels. The RoutineState pattern (selected in research R4) provides clean IDE support, type hints, and Rope refactorability while preserving MUMPS semantics.

**Independent Test**: Can be tested by verifying variables set in one label are accessible in target label via RoutineState.

**Acceptance Scenarios**:

1. **Given** routine with cross-label GOTO, **When** generated, **Then** Python uses `RoutineState` dataclass passed through all label functions
2. **Given** RoutineState with fields X, Y, **When** ENTRY sets `s.X = 10` and GOTOs to NEXT, **Then** NEXT can read `s.X` as 10
3. **Given** routine with subscripted arrays, **When** generated, **Then** RoutineState contains MArray fields for array variables

**Concrete Example** (US6 acceptance scenario 3):
```python
# Generated RoutineState for routine with subscripted array A
@dataclass
class RoutineState:
    X: Any = None           # Simple variable
    A: MArray = field(default_factory=MArray)  # Subscripted array

# Label function using MArray
def _label_SUM(state: RoutineState) -> tuple[str | None, RoutineState]:
    result = m_num(state.A[1].value) + m_num(state.A[2].value)
    _rt.write(str(result))
    return (None, state)
```

---

### User Story 7 - Multiple GOTO Targets (Priority: P3)

As a developer, when I generate Python from MUMPS code with multiple GOTO targets (`G A,B,C`), the code generator executes each label in sequence, stopping if a label QUITs.

**Why this priority**: Multiple targets are rarely used but appear in some VistA code. Sequential execution with early-exit semantics must be correct.

**Independent Test**: Can be tested by executing code with multiple GOTO targets.

**Acceptance Scenarios**:

1. **Given** `TEST G A,B Q` / `A W "A" Q` / `B W "B" Q`, **When** generated and executed, **Then** output is "A" (first label QUITs, doesn't reach B)
2. **Given** `TEST G A,B Q` / `A W "A"` / `B W "B" Q`, **When** generated and executed, **Then** output is "AB" (A falls through to B, both execute)
3. **Given** `TEST G A,B,C Q` / `A W "1"` / `B W "2"` / `C W "3" Q`, **When** generated and executed, **Then** output is "123" (all three execute in sequence)

**Clarification**: "Fall-through" means label A's code completes without QUIT, then label B executes as a direct call within the same trampoline iteration. This is NOT trampoline dispatch - it's sequential execution of the target list `[A, B, C]` within a single dispatch.

---

### User Story 8 - Strategy Selection Based on Analysis (Priority: P2)

As a developer, the code generator automatically selects the appropriate strategy (trampoline vs simple labels-as-functions) based on the routine's control flow analysis, without manual intervention.

**Why this priority**: Automatic strategy selection enables batch transpilation of large codebases. Manual per-routine decisions don't scale.

**Independent Test**: Can be tested by generating different routine types and verifying correct strategy selection.

**Note**: State machine pattern was evaluated but DEFERRED. Only two strategies remain: TRAMPOLINE (for cross-label GOTOs) and SIMPLE_FUNCTIONS (for intra-label only).

**Acceptance Scenarios**:

1. **Given** routine with `needs_trampoline=False` (no cross-label GOTOs), **When** generated, **Then** uses simple labels-as-functions (no trampoline overhead)
2. **Given** routine with cross-label GOTOs (forward or backward), **When** generated, **Then** uses trampoline pattern with RoutineState
3. **Given** routine with cyclic cross-label GOTOs, **When** generated, **Then** trampoline handles cycles without stack overflow

---

### Edge Cases

- **GOTO to labelless preamble**: If routine starts with code before first label, can GOTO reach it? (Typically no - labels define entry points)
- **GOTO from inside IF/ELSE**: Cross-label GOTO from within IF branch must still transfer control correctly (FR-005)
- **Variable initialized in one path only**: If GOTO skips initialization, variable should be undefined (MUMPS behavior)
- **GOTO target label has no body**: Empty label should work as GOTO target (control falls through to next label)
- **Self-referential label GOTO**: `LABEL ... G LABEL` jumps back to same label - handled by trampoline as a cycle (returns `("LABEL", state)` which dispatcher handles without recursion)
- **Mixed FOR and cross-label patterns**: GOTO exiting FOR to another label that later GOTOs back must work

**Edge cases explicitly deferred to later specs**:
- Computed offsets (`G LABEL+expr`) -> Spec 007
- External routine GOTO (`G LABEL^OTHER`) -> Spec 008
- Indirect GOTO (`G @VAR`) -> Spec 012
- Argumentless GOTO (`G` alone) - appears invalid in YDB, verify and document

## Requirements *(mandatory)*

### Functional Requirements

#### Cross-Label Jump Generation

- **FR-001**: System MUST translate forward cross-label GOTO to control transfer that skips intermediate code
- **FR-002**: System MUST translate backward cross-label GOTO to loop construct or state transition
- **FR-003**: System MUST preserve variable visibility across label boundaries (no implicit NEW at label entry)
- **FR-004**: System MUST handle cross-label GOTO from inside FOR loops using combined loop-exit + label-transfer pattern
- **FR-005**: System MUST handle cross-label GOTO from inside IF/ELSE without corrupting condition state

#### Trampoline Pattern

- **FR-006**: System MUST emit trampoline wrapper when routine contains cyclic cross-label GOTOs
- **FR-007**: Trampoline MUST prevent Python stack growth regardless of iteration count
- **FR-008**: Labels-as-functions MUST return next label name (or None for exit) instead of calling directly
- **FR-009**: Trampoline MUST dispatch to label functions via name lookup, not direct call

#### RoutineState Pattern

- **FR-010**: System MUST emit RoutineState dataclass when routine has cross-label GOTOs
- **FR-011**: RoutineState MUST contain typed fields for all routine variables from analysis
- **FR-012**: RoutineState MUST contain MArray fields for subscripted array variables
- **FR-013**: Label functions MUST accept RoutineState and return `(next_label, state)` tuple
- **FR-014**: Trampoline MUST pass RoutineState through all label transitions

#### Strategy Selection

- **FR-015**: System MUST use trampoline pattern for ALL routines with cross-label GOTOs
- **FR-016**: System MUST use simple labels-as-functions (no trampoline) for routines with ONLY intra-label GOTOs
- **FR-017**: System SHOULD set `MRoutine.needs_trampoline=True` during analysis for cross-label patterns
- **FR-018**: Strategy selection MUST happen before code emission based on ASG analysis

**Note**: State machine pattern was evaluated but deferred. Trampoline handles all known cross-label patterns including cycles. If truly irreducible patterns are discovered (e.g., computed offsets requiring line-level dispatch), state machine may be reconsidered in Spec 007.

#### Variable Visibility

- **FR-019**: System MUST generate RoutineState dataclass for cross-label variable visibility
- **FR-020**: System MUST populate RoutineState fields from `input_variables` and `output_variables` analysis
- **FR-021**: NEWed variables in one label MUST NOT be visible after GOTO to another label
- **FR-022**: Formal parameters MUST remain local to their label (implicitly NEWed)

#### Subscripted Arrays (MArray)

- **FR-027**: System MUST use MArray class for subscripted local variables
- **FR-028**: MArray MUST support both value and children at each node (MUMPS semantics)
- **FR-029**: MArray MUST provide `get()`, `defined()`, `kill()` methods for MUMPS operations
- **FR-030**: MArray instances MUST be fields in RoutineState for cross-label array visibility

#### Multiple GOTO Targets

- **FR-023**: System MUST execute multiple GOTO targets (`G A,B,C`) sequentially within one trampoline iteration
- **FR-024**: QUIT in any target MUST stop execution (not continue to next target)
- **FR-025**: Fall-through from one target to the next MUST work when no QUIT
- **FR-026**: Trampoline MUST only dispatch the first target; subsequent targets execute via sequential calls within that dispatch

### Key Entities

- **MGotoStatement.is_cross_label**: Boolean - True if GOTO target is in different label
- **MGotoStatement.goto_type**: GotoType enum - FORWARD_JUMP, BACKWARD_JUMP, LOOP_EXIT, etc.
- **MRoutine.has_unstructured_goto**: Boolean - DEFERRED (reserved for future state machine if needed)
- **MRoutine.needs_trampoline**: Boolean (NEW) - True if ANY cross-label GOTOs detected
- **MLabel.input_variables**: Set[str] - Variables read from caller/outer scope
- **MLabel.output_variables**: Set[str] - Variables written that are visible after label
- **RoutineState**: Dataclass (NEW) - Shared variables passed through trampoline
- **MArray**: Class (NEW) - Subscripted array with MUMPS semantics (value + children at each node)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of cross-label GOTO test cases produce output matching YDB reference
- **SC-002**: Cyclic GOTO patterns execute 10,000+ iterations without RecursionError
- **SC-003**: Trampoline pattern handles all cross-label patterns including cycles correctly
- **SC-004**: Generated Python passes `ast.parse()` validation for all inputs
- **SC-005**: Variables set before GOTO are visible in target label in 100% of test cases
- **SC-006**: Strategy selection (trampoline vs simple labels-as-functions) is automatic with no manual flags
- **SC-007**: Multiple GOTO targets execute in sequence with correct early-exit on QUIT
- **SC-008**: Test suite achieves at least 85% code coverage on new codegen additions

## Clarifications

### Session 2025-01-11

- Q: What control flow patterns should trigger `has_unstructured_goto=True` and force state machine generation? → A: **DEFERRED** - `has_unstructured_goto` is not set in Spec 006. All cross-label patterns use trampoline. State machine was evaluated but found unnecessary; if truly irreducible patterns are discovered (e.g., computed offsets in Spec 007), `has_unstructured_goto` may be reconsidered.
- Q: Should subscripted local variables be in scope for Spec 006? → A: Yes, include minimal dict-based implementation for subscripted locals (needed for realistic cross-label variable visibility tests)
- Q: How should multiple GOTO targets (`G A,B,C`) interact with trampoline? → A: Execute all targets in sequence within one trampoline iteration; trampoline only dispatches the initial target
- Q: When should the V1GO1.m spike execute relative to implementation? → A: Spike IS first implementation phase (prototypes both strategies); followed by analysis/decision phase; then productionization phase (stub populated with tasks after decision)
- Q: Are there other high-risk technical decisions needing spikes? → A: Yes - (1) Extend V1GO1.m spike to test all three shared state patterns (RoutineState vs outer-scope vs runtime dict); (2) Add subscripted locals mini-spike to validate MArray approach before committing
- Q: How should ASG/analysis gaps discovered during implementation be handled? → A: Per layer separation principle - codegen must remain straightforward; push complexity to ASG/analysis. Anticipated gaps go in plan; unexpected gaps get fixed in ASG before codegen proceeds.

## Assumptions

- Spec 005 infrastructure is complete (intra-label GOTOs, loop exits, labels-as-functions)
- Analysis passes populate `is_cross_label`, `goto_type` correctly
- `has_unstructured_goto` is DEFERRED for Spec 006 - not set or used; all cross-label patterns use trampoline
- `needs_trampoline=True` is set for ANY cross-label GOTOs (not just cycles)
- `FunctionSignature.input_variables` and `output_variables` are computed by variable analysis
- Computed offsets (`G LABEL+expr`) are deferred to Spec 007
- External routine calls (`G LABEL^ROUTINE`) are deferred to Spec 008
- Indirect GOTO (`G @VAR`) is deferred to Spec 012
- Argumentless GOTO (`G` alone) is invalid in YDB (verified - causes syntax error)

## ASG Gap Handling (Critical)

**Principle**: Per codegen-plan.md "layer separation" - codegen translates a complete, resolved ASG to Python. It should NOT:
- Build parse-like logic
- Perform complex analysis inline
- Use `getattr(stmt, field, default)` fallback patterns
- Work around missing ASG fields

**When codegen discovers missing information**:
1. STOP - do not build a workaround in codegen
2. Identify what ASG field or analysis pass is missing
3. Fix it in parser (`src/m2py/parser/`) or analysis (`src/m2py/analysis/`)
4. Update ASG dataclasses (`src/m2py/asg/`) if new fields needed
5. Resume codegen with the proper ASG support

**Anticipated ASG gaps for Spec 006** (include in plan):

| Gap | Location | What's Needed |
|-----|----------|---------------|
| `needs_trampoline` flag | `MRoutine` | True if ANY cross-label GOTOs exist (not just cycles) |
| Cross-label variable flow | `analysis/variables.py` | Which variables flow between specific labels |
| Multiple GOTO target list | `MGotoStatement` | Verify targets are accessible as list |
| RoutineState field list | `MRoutine` or analysis | All variables needing RoutineState fields |
| MArray variable detection | `analysis/variables.py` | Which variables are subscripted arrays |

**Note**: Cycle detection is useful for optimization but not required for strategy selection - trampoline handles all cross-label patterns.

**Unexpected gaps** (handle during implementation):
- If spike reveals codegen needs information not in ASG → create task to add ASG support FIRST
- Document all ASG additions in implementation notes for future specs
- Update `docs/asg/` with new fields

**Why this matters**: Keeping codegen straightforward enables:
- Easier debugging (ASG is the source of truth)
- Better test isolation (test analysis separately from codegen)
- Cleaner architecture for future specs
- Rope/refactoring tool compatibility

## Explicitly Deferred

The following are explicitly **out of scope** for Spec 006:

- **Computed offsets** (`G LABEL+expr`, `G LABEL+^VAR`) -> Spec 007
- **Line-based dispatch** for computed targets -> Spec 007  
- **External routine GOTO** (`G LABEL^ROUTINE`) -> Spec 008
- **Indirect GOTO** (`G @VAR`) -> Spec 012
- **REQUIRES_RUNTIME scope strategy** (indirection defeats analysis) -> Spec 012
- **XECUTE command** -> Spec 012
- **Global variables** (`^name`) -> Spec 009
- **Intrinsic functions** ($PIECE, $LENGTH, etc.) -> Spec 010
- **Subscripted local variables** - NOW IN SCOPE for Spec 006 (MArray class implementation for cross-label visibility tests)
- **State machine pattern** - Deferred (trampoline handles all known patterns; reconsider if truly irreducible flow discovered)

### Extension Analysis for Deferred Features

See [research.md section R6](research.md#r6-extension-analysis-for-deferred-goto-features) for detailed extensibility analysis.

**Summary**: Selected patterns (Trampoline + RoutineState + MArray) extend naturally to deferred specs:
- **Indirect GOTO** (`G @VAR`) → Low effort (string-based dispatch works)
- **Static offsets** (`G LABEL+3`) → Low effort (compile-time resolution)
- **External GOTO** (`G ^RTN`) → Medium effort (exception-based stack unwinding)

## Research Phase

**Note on `has_unstructured_goto`**: This legacy flag from Spec 004/005 is **ignored in Spec 006**. The new `needs_trampoline` flag is the sole trigger for trampoline pattern. `has_unstructured_goto` remains in the ASG for backward compatibility but has no effect on Spec 006 codegen.

Review before implementing:

- **Docs**: `docs/analysis/goto_analysis.md`, `docs/codegen/goto_handling.md`, `docs/analysis/variable_analysis.md`
- **Cross-label detection**: `analysis/goto_analysis.py` -> `is_cross_label`, `_has_unstructured_gotos()`
- **Routine flags**: `asg/elements.py` -> `MRoutine.has_unstructured_goto`
- **Variable visibility**: `analysis/variables.py` -> `input_variables`, `output_variables` per label
- **Current GOTO codegen**: `codegen/statements.py` -> `_generate_goto()` - cross-label as function call
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1GO1.m`

### Key Implementation Questions (To Answer in Research Phase)

1. **Shared state pattern**: ✅ DECIDED in research R4
   - **Selected**: `RoutineState` dataclass passed to all label functions
   - Rejected: Outer-scope variables (nonlocal issues), Runtime dict (poor IDE support)
   
   **Rationale**: Best Rope refactorability, IDE autocomplete, type hints

2. **Execution pattern**: ✅ DECIDED in research R3
   - **Selected**: Trampoline pattern for ALL cross-label GOTOs
   - Deferred: State machine (found unnecessary - trampoline handles all patterns including cycles)
   
3. **Trampoline trigger**: ✅ DECIDED in research R2.5 (VistA analysis)
   - Set `needs_trampoline=True` for ANY cross-label GOTOs (not just cycles)
   - VistA analysis showed 47.5% of routines have cycles - trampoline is mandatory
   - Cycle detection still useful for optimization but not for strategy selection

4. **Multiple target execution**: How to implement `G A,B,C`:
   - Generate: `A(); B(); C()` with early-return on QUIT
   - Or: Trampoline with target list: `targets = ["A", "B", "C"]`

5. **Subscripted arrays**: ✅ DECIDED in research R5
   - **Selected**: MArray class with value + children at each node
   - Rejected: Nested dict (awkward `["_value"]` access)
   - Provides: `arr[1, 2]` access, `get()`, `defined()`, `kill()` methods

### Spike: Strategy Bake-off (REQUIRED)

**Execution**: This spike is the FIRST implementation phase, not a pre-implementation activity. The plan should include:
1. **Spike Phase**: Prototype both strategies against V1GO1.m
2. **Analysis/Decision Phase**: Evaluate metrics, document decision
3. **Productionization Phase**: Stub populated with tasks after decision

**From codegen-plan.md**: Translate V1GO1.m using both strategies. Measure:

1. **Correctness**: Both produce same output as YDB?
2. **Line count**: Which is more concise?
3. **Refactorability**: Can Rope extract/rename in each?
4. **Percentage needing state machine**: How many V1GO1 patterns are truly irreducible?
5. **Variable visibility**: Does state class feel natural or awkward?

**Extended scope - Shared State Pattern**: Also test all three variable sharing approaches:

| Pattern | Implementation | Test For |
|---------|----------------|----------|
| RoutineState class | `class RoutineState: x = 0` passed to all labels | Rope refactorability, clarity |
| Outer-scope variables | `x = 0` at module level, `global x` in labels | Simplicity, name collision risk |
| Runtime dict | `_rt.set("x", 1)` / `_rt.get("x")` | Fallback viability, performance |

**Results** (from research R3):
- ✅ Labels-as-functions (trampoline) handles 100% of V1GO1.m patterns
- ✅ VistA analysis (R2.5): Trampoline handles all patterns including 47.5% with cycles
- ✅ State machine found unnecessary - offers no advantage over trampoline
- ✅ Shared state: RoutineState selected for best Rope compatibility + clarity

---

### Spike: Subscripted Locals (REQUIRED)

**Risk**: MUMPS arrays have unusual semantics where each node can have BOTH a value AND children:

```mumps
S A=1         ; A has value 1
S A(1)=2      ; A still has value 1, A(1) has value 2  
S A(1,2)=3    ; A(1) still has value 2, A(1,2) has value 3
```

This is NOT a Python dict - naive implementation will fail.

**Test approaches**:

| Approach | Implementation | Pros | Cons |
|----------|----------------|------|------|
| Custom MArray class | `class MArray` with value + children | Clean API, MUMPS-native | More code |
| Nested dict + _value key | `{"_value": 1, 1: {"_value": 2}}` | Uses stdlib | Awkward access pattern |
| Defer to Spec 007 | Remove from Spec 006 scope | Reduce risk | Acceptance scenario #3 invalid |

**Results** (from research R5):
- ✅ MArray class works for User Story 3 scenario: `S A(1)=10,A(2)=20 G SUM` / `SUM W A(1)+A(2)`
- ✅ MArray integrates cleanly with RoutineState (MArray instances as dataclass fields)
- ✅ Full MUMPS semantics: value AND children at each node, `defined()` for $DATA, `kill()` for KILL
- ✅ Clean syntax: `arr[1, 2]` for access, `arr.get(1, 2)` for safe access

**Spike files**: See `spikes/marray_spike.py` for validated implementation.
