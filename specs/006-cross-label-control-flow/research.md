# Research: Cross-Label Control Flow

**Spec**: 006-cross-label-control-flow  
**Date**: 2026-01-11  
**Status**: In Progress

## Overview

This document captures research findings for Spec 006. All NEEDS CLARIFICATION items from the plan should be resolved here before Phase 1 design.

## Research Tasks

### R1: Current ASG Infrastructure

**Status**: ✅ Complete

**Questions to answer**:
1. What fields does `MGotoStatement` currently have?
2. When is `is_cross_label` set?
3. What triggers `has_unstructured_goto=True`?
4. Are `input_variables`/`output_variables` populated on MLabel?

**Findings**:

#### 1. MGotoStatement Fields (src/m2py/asg/statements.py:247)

```python
@dataclass
class MGotoStatement(MStatement):
    targets: List["MCall"]                    # Target labels (usually 1, can be multiple)
    
    # Classification (populated in analysis pass)
    goto_type: Optional[GotoType] = None      # FORWARD_JUMP, BACKWARD_JUMP, LOOP_EXIT, etc.
    exits_loops: List["MForStatement"]        # FOR loops this GOTO exits
    is_cross_label: bool = False              # True if target is in different label
    
    # For intra-label forward GOTOs
    target_stmt_index: Optional[int] = None   # Index of target statement in label body
    
    # Pre-computed codegen fields
    is_restructurable: bool = False           # Can be restructured to if/else
    codegen_pattern: Optional[GotoCodegenPattern] = None
```

#### 2. is_cross_label Setting (src/m2py/analysis/goto_analysis.py:220-268)

Set in `_classify_single_goto()`:
- `is_cross_label = False`: Target label is SAME as current label (intra-label jump)
- `is_cross_label = True`: Target label is DIFFERENT from current label

Direction is orthogonal - both forward and backward jumps can be cross-label or not.

#### 3. has_unstructured_goto Trigger (src/m2py/analysis/goto_analysis.py:399-440)

Set in `_has_unstructured_gotos()` - returns True if:
- `goto_type == UNRESOLVED`: Target unknown at compile time
- `goto_type == BACKWARD_JUMP`: Creates implicit loops (any backward jump)
- `is_cross_label=True AND NOT exits_loops`: Cross-label forward jump not exiting a loop

**Important**: This definition means ALL cross-label GOTOs (not inside FOR) trigger `has_unstructured_goto=True`. This is the flag Spec 006 needs to handle.

#### 4. input_variables/output_variables Population (src/m2py/analysis/variables.py)

**Yes, both are populated on MLabel** during `compute_signatures()`:
- Line 371: `label.input_variables = scope_vars.input_variables`
- Line 372: `label.output_variables = scope_vars.output_variables`

**Definition**:
- `input_variables`: Variables read before first write (need to be passed in)
- `output_variables`: Variables written and visible to caller (can be returned)

These sets exclude formal parameters and NEWed variables (proper scoping).

#### 5. MRoutine Analysis Fields (src/m2py/asg/elements.py:259-298)

```python
@dataclass
class MRoutine(ASGElement):
    has_unstructured_goto: bool = False         # True if non-structured GOTO patterns
    needs_loop_exit_exception: bool = False     # True if MULTI_LOOP_EXIT exists
```

**Note for Spec 006**: Plan.md proposes adding `needs_trampoline: bool` to MRoutine for cyclic cross-label patterns. This would complement `has_unstructured_goto` for strategy selection.

---

### R2: V1GO1.m Pattern Analysis

**Status**: ✅ Complete

**Questions to answer**:
1. What GOTO patterns does V1GO1.m contain?
2. How many are cross-label forward jumps?
3. How many are cross-label backward jumps?
4. Are any patterns truly irreducible (requiring state machine)?

**Findings**:

#### 1. GOTO Statistics

| Type | Count |
|------|-------|
| Cross-label FORWARD | 20 |
| Cross-label BACKWARD | 10 |
| Intra-label FORWARD | 0 |
| Intra-label BACKWARD | 0 |
| EXTERNAL | 0 |
| UNRESOLVED | 0 |
| **Total** | **30** |

`has_unstructured_goto = True` (due to backward jumps)

#### 2. Control Flow Pattern Analysis

**Key Finding**: V1GO1.m exhibits a **"scrambled order" pattern**, NOT a cyclic pattern.

Despite having 10 "backward" GOTOs (jumping to labels positioned earlier in the file), the actual execution flow is **completely linear** - each label is visited exactly once in a specific execution order.

**Execution trace** (31 labels, 30 transitions):
```
V1GO1 -> % -> %A -> %ABCDEFG -> %0 -> %90 -> %0000000 -> %2345678 -> %A1 -> 
%A1B2C3D -> A -> Q -> Z -> DO -> IF -> QUIT -> SET -> ABCDEFGH -> 0 -> 1 -> 
01 -> 10 -> 12 -> 100 -> 012 -> 0012 -> 92345678 -> 00000000 -> A1 -> Z012 -> 
ZXY987A0 -> (END via fall-through)
```

The "backward" edges like `%0 -> %90` appear to go back in file position, but the execution never returns to `%0` after visiting `%90`. This is a one-way traversal.

#### 3. Cycle Analysis

**No true cycles exist in V1GO1.m.**

The DFS cycle detection found zero cycles in the control flow graph. All backward edges are part of the single linear execution path, not loop-back patterns.

This means:
- **Trampoline pattern**: Will work efficiently (no infinite loops)
- **State machine pattern**: Will work but is overkill for this pattern
- **Direct function calls**: Would cause stack overflow without trampoline (30 nested calls)

#### 4. Irreducible Pattern Assessment

**V1GO1.m contains NO irreducible patterns.**

The "scrambled order" pattern is fully reducible to:
1. A sequence of function calls following the execution order, OR
2. A trampoline that visits each label once in sequence, OR
3. A state machine (works but unnecessarily complex)

**Recommendation**: V1GO1.m is an excellent test case for the **trampoline pattern** - it validates that cross-label control flow works without requiring cycle handling or state machine complexity.

#### 5. Variable Flow Observation

All labels in V1GO1.m share access to these variables:
- `PASS`, `FAIL`, `ITEM`, `VCOMP`, `VCORR` (test state)
- `ROUTINE`, `TESTS`, `AUTO`, `VISUAL` (reporting)

This confirms the need for **shared state** across labels - variables set in one label must be visible after GOTO to another label.

---

### R2.5: VistA Production Codebase Analysis

**Status**: ✅ Complete

**Questions to answer**:
1. How representative is V1GO1.m of real VistA GOTO patterns?
2. What percentage of real routines have cyclic control flow?
3. Are there module-specific patterns we should account for?
4. What architecture does the data support?

**Analysis Method**: Used m2py parser and ASG (not regex) via `utils/analyze_vista_gotos.py`

**Findings**:

#### 1. Overall Statistics (33,951 files)

| Metric | Value | Percentage |
|--------|-------|------------|
| Files parsed successfully | 33,928 | 99.9% |
| Files with GOTOs | 13,566 | 40.0% |
| Parse failures | 23 | 0.07% |

**GOTO Breakdown** (124,920 total):

| GOTO Type | Count | % of Total |
|-----------|-------|------------|
| Cross-label FORWARD | 62,029 | 49.7% |
| Cross-label BACKWARD | 29,582 | 23.7% |
| Intra-label BACKWARD (self-loops) | 17,118 | 13.7% |
| External (^routine) | 13,367 | 10.7% |
| Loop exit (single) | 1,173 | 0.9% |
| Unresolved | 1,448 | 1.2% |
| Loop exit (multi) | 203 | 0.2% |
| Conditional | 24,157 | 19.3% |

#### 2. V1GO1.m Representativeness - NOT REPRESENTATIVE

**Critical Finding**: V1GO1.m (0% cycles) is **not representative** of real VistA code.

| Metric | V1GO1.m | VistA Production |
|--------|---------|-----------------|
| Files with cycles | 0% | **47.5%** |
| Cross-label backward | 33% | 23.7% |
| Total cycles detected | 0 | 13,015 |

**Key Insight**: Nearly half of all VistA routines with GOTOs have cyclic control flow patterns. V1GO1.m's "scrambled order" pattern (linear, no cycles) is an edge case, not the norm.

#### 3. Module-Specific Variability

**High-cycle modules** (complex control flow):
| Module | Files | GOTOs | %Cycles |
|--------|-------|-------|---------|
| Remote Order Entry System | 86 | 1,126 | **84%** |
| Automated Lab Instruments | 354 | 1,484 | **82%** |
| Dietetics | 612 | 3,263 | **73%** |
| Surgery | 653 | 2,319 | **65%** |
| PAID | 402 | 1,356 | **65%** |
| Lab Service | 1,247 | 4,409 | **63%** |

**Low-cycle modules** (simpler control flow):
| Module | Files | GOTOs | %Cycles |
|--------|-------|-------|---------|
| Order Entry Results Reporting | 1,142 | 1,101 | **17%** |
| Text Integration Utility | 465 | 1,727 | **22%** |
| Medicine | 353 | 1,644 | **23%** |
| Asists | 87 | 108 | **23%** |

**Observation**: Module complexity varies significantly. "Data lookup" modules (AICS) have low GOTO density. Clinical modules (Lab, Surgery) have higher cycles.

#### 4. Architecture Decision Support

**Key Metrics** (Spec 006 Scope):

| Metric | Count | Implication |
|--------|-------|-------------|
| Cross-label GOTOs | 91,611 (73.3%) | Spec 006 addresses majority of GOTOs |
| Backward jumps (need trampoline) | 46,700 (37.4%) | ~1/3 need cycle-safe execution |
| Files with cycles | 6,440 (47.5% of GOTO files) | Trampoline is REQUIRED, not optional |

**Architecture Recommendation**:

1. **Trampoline pattern is MANDATORY** for correctness - half of files have cycles
2. **State machine pattern may be unnecessary** - trampoline handles cycles correctly
3. **Self-loop patterns** (17,118) are common - labels GOTO to themselves for retry/input loops

#### 5. Common Cycle Patterns

**Self-loop examples** (single-label cycles):
```
LR7OAPKM.m: ASKORDER → ASKORDER
PRCAAPR.m: ASK → ASK  
DG10.m: START → START
```
These are typically "ask user input, validate, retry if invalid" patterns.

**Multi-label cycles**:
```
DG10.m: A1 → EMBOS → A → SKIP → A1
DDBR0.m: COLA → COLERR → COLA
```
These are state machine-like patterns with error recovery paths.

#### 6. Revised Conclusions

| V1GO1.m Finding | VistA Reality | Adjustment |
|-----------------|---------------|------------|
| No cycles | 47.5% have cycles | Trampoline is critical |
| "Scrambled order" only | True cycles exist | Must handle indefinite iteration |
| State machine may be overkill | Still may be overkill | Trampoline handles cycles fine |

**Final Recommendation**: V1GO1.m validates the trampoline implementation works for acyclic cases. VistA analysis confirms trampoline is required for the ~50% of routines with true cycles. No evidence that state machine is needed beyond trampoline.

---

### R3: Strategy Bake-off Results

**Status**: ⬜ Not started

**Trampoline Pattern Prototype**:

```python
# Template - to be filled with actual spike code
def _trampoline(entry_label, state):
    """Dispatch loop that prevents stack growth."""
    label = entry_label
    while label is not None:
        func = _labels[label]
        label, state = func(state)
    return state
```

**State Machine Pattern Prototype**:

```python
# Template - to be filled with actual spike code
def _run_routine():
    """State machine with match-case."""
    state = "ENTRY"
    # variables in outer scope
    while True:
        match state:
            case "ENTRY":
                # code...
                state = "NEXT"
            case "NEXT":
                # code...
                state = None
            case None:
                break
```

**Evaluation Matrix**:

| Metric | Trampoline | State Machine | Winner |
|--------|------------|---------------|--------|
| Correctness (V1GO1 patterns) | TBD | TBD | TBD |
| Line count | TBD | TBD | TBD |
| Rope refactorability | TBD | TBD | TBD |
| % patterns requiring state machine | N/A | N/A | N/A |
| Implementation complexity | TBD | TBD | TBD |

**Decision**: *To be determined after spike*

**Rationale**: *To be documented*

---

### R4: Shared State Pattern Evaluation

**Status**: ⬜ Not started

**RoutineState Class**:

```python
# Template
class _State:
    def __init__(self):
        self.x = None
        self.y = None
```

Pros:
- TBD

Cons:
- TBD

**Outer-Scope Variables**:

```python
# Template
x = None
y = None

def LABEL():
    global x, y
    x = 1
```

Pros:
- TBD

Cons:
- TBD

**Runtime Dict**:

```python
# Template
_rt.set("x", 1)
val = _rt.get("x")
```

Pros:
- TBD

Cons:
- TBD

**Decision**: *To be determined after spike*

---

### R5: Subscripted Locals Spike

**Status**: ⬜ Not started

**Test Case**: 
```mumps
S A(1)=10,A(2)=20 G SUM Q
SUM W A(1)+A(2) Q
```
Expected output: `30`

**MArray Class Approach**:

```python
# Template
class MArray:
    """MUMPS array with value AND children at each node."""
    def __init__(self, value=None):
        self._value = value
        self._children = {}
    
    def __getitem__(self, key):
        # Returns MArray node at key
        pass
    
    def __setitem__(self, key, value):
        # Sets value at key (creates path if needed)
        pass
    
    @property
    def value(self):
        return self._value if self._value is not None else ""
```

**Nested Dict Approach**:

```python
# Template
A = {"_value": None}
A[1] = {"_value": 10}
A[2] = {"_value": 20}
# Access: A[1]["_value"] + A[2]["_value"]
```

**Evaluation**:

| Criteria | MArray | Nested Dict |
|----------|--------|-------------|
| MUMPS semantics match | TBD | TBD |
| Integration with shared state | TBD | TBD |
| Code clarity | TBD | TBD |
| Implementation effort | TBD | TBD |

**Decision**: *To be determined after spike*

---

## Resolved Clarifications

Items from spec "Clarifications" section that were resolved:

1. **`has_unstructured_goto` trigger**: Only backward GOTO to preamble sets the flag
2. **Subscripted locals scope**: In scope with mini-spike validation
3. **Multiple GOTO + trampoline**: Sequential within one iteration
4. **Spike timing**: Spike IS first implementation phase
5. **Additional spikes**: V1GO1.m extended + subscripted locals
6. **ASG gaps**: Fix in ASG first per layer separation principle

---

## References

- [codegen-plan.md](../codegen-plan.md) - Overall codegen strategy
- [Spec 005 spec.md](../005-structured-control-flow/spec.md) - Prerequisite infrastructure
- [goto_analysis.py](../../src/m2py/analysis/goto_analysis.py) - Current GOTO analysis
- [constitution.md](../../.specify/memory/constitution.md) - Project principles
