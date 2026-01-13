# Research: Cross-Label Control Flow

**Spec**: 006-cross-label-control-flow  
**Date**: 2026-01-11  
**Status**: ✅ Complete

## Overview

This document captures research findings for Spec 006. All research tasks and spikes are complete with decisions documented.

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

**Status**: ✅ Complete

**Spike Files**:
- `spikes/trampoline_v1go1.py` - Trampoline pattern implementation
- `spikes/state_machine_v1go1.py` - State machine pattern implementation
- `spikes/compare_spikes.py` - Comparison analysis script

#### Trampoline Pattern Prototype

```python
# Core pattern from spikes/trampoline_v1go1.py
@dataclass
class RoutineState:
    """Shared state passed through all labels."""
    PASS_COUNT: int = 0
    FAIL: int = 0
    # ... other variables

_labels: Dict[str, LabelFunc] = {}  # Label registry

def label(name: str):
    """Decorator to register a label function."""
    def decorator(func: LabelFunc) -> LabelFunc:
        _labels[name] = func
        return func
    return decorator

@label("V1GO1")
def V1GO1(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    """Entry point."""
    # ... code ...
    return ("NEXT_LABEL", s)  # GOTO NEXT_LABEL

def run_trampoline(entry_label: str = "V1GO1") -> RoutineState:
    """Execute routine via trampoline dispatch loop."""
    state = RoutineState()
    label = entry_label
    while label is not None:
        func = _labels[label]
        label, state = func(state)
    return state
```

#### State Machine Pattern Prototype

```python
# Core pattern from spikes/state_machine_v1go1.py
def V1GO1() -> str:
    """Execute V1GO1 routine using state machine pattern."""
    # Shared variables in outer scope
    PASS_COUNT = 0
    FAIL = 0
    # ...
    
    def examiner():
        nonlocal PASS_COUNT, FAIL  # Must declare nonlocal
        # ...
    
    state = "V1GO1"
    while state is not None:
        match state:
            case "V1GO1":
                # ... code ...
                state = "NEXT_LABEL"  # GOTO NEXT_LABEL
            case "NEXT_LABEL":
                # ... code ...
                state = None  # End
            case _:
                raise RuntimeError(f"Unknown state: {state}")
    
    return output
```

#### Evaluation Matrix

| Metric | Trampoline | State Machine | Winner |
|--------|------------|---------------|--------|
| **Correctness** | 30/30 PASS | 30/30 PASS | Tie |
| **Lines of code** | 412 | 310 | State Machine |
| **Functions** | 38 | 3 | - |
| **Classes** | 1 | 0 | - |
| **Match cases** | 0 | 33 | - |
| **Branch statements** | 8 | 7 | Tie |

#### Refactorability Analysis

**Trampoline Pattern**:
- ✅ Each label is separate function - easily extractable
- ✅ Functions can be renamed independently via Rope
- ✅ New labels add new functions without touching dispatch
- ✅ State explicitly passed - easy to test individual labels
- ❌ More boilerplate (function signatures, decorators)

**State Machine Pattern**:
- ✅ All logic in single function - simpler scoping
- ✅ match/case naturally maps to label dispatch
- ✅ Fewer lines of code overall
- ❌ Extracting a case to function requires manual refactor
- ❌ Single large function harder to test in isolation
- ❌ Variables must use `nonlocal` for nested write access

#### VistA Production Implications

From VistA analysis (R2.5): **47.5% of files have cycles**

Both patterns handle cycles correctly:
- **Trampoline**: Returns to dispatch loop, no recursion
- **State machine**: Reassigns state variable, single while loop

Both have bounded stack depth regardless of cycle count.

#### Decision: **TRAMPOLINE PATTERN**

**Rationale**:

1. **Better decomposition**: Labels as functions map naturally to MUMPS routine structure and support IDE navigation (Go to Definition, Find References)

2. **Easier testing**: Individual label functions can be unit tested in isolation with mock state

3. **Better Rope refactorability**: Extract Method, Rename Symbol operations work on individual label functions

4. **Uniform code generation**: Same pattern for each label - generator emits function definition + decorator registration

5. **Acceptable overhead**: 102 extra lines (33%) is acceptable for maintainability benefits, especially for VistA routines with 100+ labels

6. **Cycle handling validated**: VistA analysis confirms 47.5% of routines have cycles; trampoline handles these correctly without state machine complexity

**Note**: State machine pattern may be considered as a future optimization for very simple routines (< 10 labels, no cycles) if code size becomes a concern, but trampoline is the primary strategy for Spec 006.

---

### R4: Shared State Pattern Evaluation

**Status**: ✅ Complete

**Spike Files**:
- `spikes/shared_state_class.py` - RoutineState dataclass approach
- `spikes/shared_state_outer.py` - Outer-scope variables with nonlocal
- `spikes/shared_state_runtime.py` - Runtime dict with get/set methods
- `spikes/compare_shared_state.py` - Comparison analysis script

#### Pattern Comparison

**1. RoutineState Class**:

```python
@dataclass
class RoutineState:
    X: Any = None
    Y: Any = None

@label("ENTRY")
def ENTRY(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.X = 10
    return ("NEXT", s)
```

**2. Outer-Scope Variables**:

```python
X = None
Y = None

@label("ENTRY")
def ENTRY() -> Optional[str]:
    nonlocal X  # MUST declare for writes!
    X = 10
    return "NEXT"
```

**3. Runtime Dict**:

```python
@label("ENTRY")
def ENTRY(rt: Runtime) -> tuple[Optional[str], Runtime]:
    rt.set("X", 10)  # String-based access
    return ("NEXT", rt)
```

#### Evaluation Matrix

| Criterion | Class | Outer-Scope | Runtime | Winner |
|-----------|-------|-------------|---------|--------|
| **Rope: Rename Symbol** | GOOD | MODERATE | POOR | Class |
| **Rope: Extract Method** | GOOD | POOR | GOOD | Class |
| **Rope: Find References** | GOOD | MODERATE | POOR | Class |
| **IDE Autocomplete** | GOOD | GOOD | POOR | Tie |
| **Type Checking** | GOOD | MODERATE | POOR | Class |
| **Dynamic Variables** | POOR | POOR | GOOD | Runtime |
| **Name Collision Risk** | LOW | LOW | HIGH | Tie |
| **Subscript Support** | NEEDS WORK | NEEDS WORK | NATURAL | Runtime |
| **MUMPS Semantics Match** | MODERATE | MODERATE | GOOD | Runtime |

#### Detailed Analysis

**RoutineState Class - RECOMMENDED**:
- ✅ Best IDE/Rope support (symbols, autocomplete, type hints)
- ✅ Fields are explicit and documented
- ✅ Easy to pass state to helper functions
- ✅ Natural fit with trampoline pattern (state passed through)
- ❌ Must pre-declare all variables (analysis pass provides this)
- ❌ Subscripted variables need MArray integration

**Outer-Scope Variables - NOT RECOMMENDED**:
- ✅ Natural Python variable syntax
- ✅ No class boilerplate for simple routines
- ❌ Must declare `nonlocal` for EVERY write in EVERY label
- ❌ Forgetting `nonlocal` creates silent bugs (new local instead of modifying outer)
- ❌ Hard to extract helper functions (scope issues)
- ❌ Code gen must track which vars each label writes

**Runtime Dict - ALTERNATIVE**:
- ✅ Perfect MUMPS semantics (dynamic creation, undefined=empty string)
- ✅ Natural fit for subscripted variables (nested dicts)
- ✅ Easy to implement NEW/KILL commands
- ❌ No IDE support (strings not symbols)
- ❌ Typos in variable names not caught at edit time
- ❌ Verbose syntax: `rt.get("X")` vs `s.X`

#### Decision: **ROUTINESTATE CLASS PATTERN**

**Rationale**:

1. **Best Rope refactorability**: Rename Symbol, Extract Method, Find References all work correctly on dataclass fields

2. **IDE autocomplete**: Catches variable name errors at edit time, not runtime

3. **Type hints**: Enable static analysis with pyright/mypy

4. **Clean syntax**: `s.X = 10` vs `rt.set("X", 10)`

5. **Consistent with trampoline**: State naturally passed through label functions

6. **Analysis pass provides variable list**: Code gen knows all variables from ASG, so pre-declaration is not a burden

**For subscripted variables**:
- Add MArray instances as RoutineState fields: `A: MArray = field(default_factory=MArray)`
- Access via: `s.A[1, 2]` or `s.A.get(1, 2)`
- Combines class-level organization with dict-like subscript semantics

**Hybrid fallback for edge cases**:
- If routine has truly dynamic variable creation (rare), add: `_vars: Dict[str, Any] = field(default_factory=dict)`
- Access via: `s._vars["DYNAMIC_NAME"]`

---

### R5: Subscripted Locals Spike

**Status**: ✅ Complete

**Spike File**: `spikes/marray_spike.py`

#### Test Results

**T026: Cross-Label Array Access** ✅ PASS
```mumps
S A(1)=10,A(2)=20 G SUM Q
SUM W A(1)+A(2) Q
```
Expected output: `30` - Array values set in one label are visible after GOTO to another label.

**T027: Nested Subscripts** ✅ PASS
```mumps
S A=1,A(1)=2,A(1,2)=3
```
Each node can have both a value AND children:
- `A` = 1, `$D(A)` = 11 (has value AND children)
- `A(1)` = 2, `$D(A,1)` = 11 (has value AND children)
- `A(1,2)` = 3, `$D(A,1,2)` = 1 (has value only)

**T028: Integration with RoutineState** ✅ PASS
- MArray instances as dataclass fields work correctly
- Multiple arrays are independent
- Arrays survive through trampoline dispatch

#### MArray Implementation

```python
class MArray:
    """MUMPS array with hierarchical subscript support."""
    
    def __init__(self, value: Any = None):
        self._value: Any = value
        self._children: Dict[Any, "MArray"] = {}
    
    @property
    def value(self) -> Any:
        """Get value at this node (empty string if undefined)."""
        return self._value if self._value is not None else ""
    
    @value.setter
    def value(self, val: Any) -> None:
        self._value = val
    
    def __getitem__(self, key: Any) -> "MArray":
        """Get child node: arr[1] or arr[1, 2]"""
        if isinstance(key, tuple):
            node = self
            for k in key:
                node = node[k]
            return node
        if key not in self._children:
            self._children[key] = MArray()
        return self._children[key]
    
    def __setitem__(self, key: Any, value: Any) -> None:
        """Set value at subscript: arr[1] = 10 or arr[1, 2] = 20"""
        # ... implementation in spike
    
    def get(self, *subscripts: Any) -> Any:
        """Get value at subscripts (empty string if undefined)."""
        # ... implementation in spike
    
    def defined(self, *subscripts: Any) -> int:
        """$DATA equivalent: 0, 1, 10, or 11"""
        # ... implementation in spike
    
    def kill(self, *subscripts: Any) -> None:
        """KILL command - delete node and descendants"""
        # ... implementation in spike
```

#### Integration with RoutineState

```python
@dataclass
class RoutineState:
    """Shared state with MArray support for subscripted variables."""
    # Simple variables
    X: Any = None
    Y: Any = None
    
    # Array variables (MArray instances)
    A: MArray = field(default_factory=MArray)
    B: MArray = field(default_factory=MArray)
    
    # Output buffer
    _output: io.StringIO = field(default_factory=io.StringIO)
```

**Usage in label functions**:
```python
@label("ENTRY")
def ENTRY(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    s.A[1] = 10           # S A(1)=10
    s.A[2] = 20           # S A(2)=20
    return ("SUM", s)

@label("SUM")
def SUM(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    result = s.A.get(1) + s.A.get(2)  # A(1)+A(2)
    s.write(result)
    return (None, s)
```

#### Evaluation Matrix

| Criteria | MArray Class | Nested Dict |
|----------|-------------|-------------|
| **MUMPS semantics** | ✅ Perfect | ⚠️ Awkward `["_value"]` access |
| **Integration** | ✅ Natural dataclass field | ❌ Requires manual management |
| **Code clarity** | ✅ `arr[1, 2]` syntax | ❌ `arr[1]["_value"]` |
| **IDE support** | ✅ Type hints work | ❌ Dynamic dict |
| **$DATA support** | ✅ Built-in `defined()` | ❌ Manual implementation |
| **KILL support** | ✅ Built-in `kill()` | ❌ Manual implementation |

#### Decision: **MARRAY CLASS PATTERN**

**Rationale**:

1. **Perfect MUMPS semantics**: Each node can have value AND children simultaneously

2. **Clean Python syntax**: `arr[1, 2]` for access, `arr.get(1, 2)` for safe access

3. **Integrates with RoutineState**: MArray fields work seamlessly with dataclass pattern

4. **Built-in MUMPS operations**: `defined()` for $DATA, `kill()` for KILL, `order()` for $ORDER

5. **Cross-label visibility verified**: Arrays set in one label are visible after GOTO to another

6. **IDE/Rope support**: Type hints on MArray class enable autocomplete and static analysis

---

### R6: Extension Analysis for Deferred GOTO Features

**Status**: ✅ Complete

**Questions to answer**:
1. Can selected patterns extend to computed offsets (G LABEL+expr)?
2. Can selected patterns extend to external routine GOTO (G LABEL^ROUTINE)?
3. Can selected patterns extend to indirect GOTO (G @VAR)?
4. Is another spike needed before committing to the selected approach?

**Context**: Before finalizing our Phase 2 architecture decisions, we evaluated whether the selected patterns (Trampoline + RoutineState + MArray) can accommodate deferred GOTO features planned for future specs:
- Spec 012: Indirect GOTO (`G @VAR`)
- Spec 007: Computed offsets (`G LABEL+expr`)
- Spec 008: External routine GOTO (`G LABEL^ROUTINE`)

#### Existing ASG Infrastructure

The ASG already has fields for all deferred features:

```python
# MCall (src/m2py/asg/elements.py)
@dataclass
class MCall:
    offset: Optional["MExpr"] = None          # For LABEL+offset
    routine: Optional[str] = None              # For ^ROUTINE
    indirection: Optional["MExpr"] = None      # For @VAR
    routine_indirection: Optional["MExpr"] = None  # For @VAR^@RTN
    label_is_indirect: bool = False
    routine_is_indirect: bool = False

# GotoType enum includes
class GotoType(Enum):
    EXTERNAL = auto()      # For ^routine
    UNRESOLVED = auto()    # For indirection
```

#### Feature 1: Indirect GOTO (`G @VAR`) → Spec 012

**MUMPS Semantics**:
- `G @VAR` evaluates VAR at runtime to get label name
- `G @VAR^@ROUTINE`: both label and routine from variables
- Target is completely dynamic

**Trampoline Extension**: **NATURALLY SUPPORTED** ✅

The trampoline already uses string-based dispatch:
```python
# Current pattern
return ('STATIC_LABEL', state)

# Extended pattern (no dispatch changes needed!)
label_name = evaluate(s.INDIRECT_VAR)  # Runtime evaluation
return (label_name, state)             # Dynamic dispatch

# Dispatcher already does string lookup:
while label is not None:
    func = _labels[label]  # String key lookup - works with dynamic labels
    label, state = func(state)
```

**Verdict**: This is the BEST case for trampoline - just need runtime evaluation of @VAR expression.

#### Feature 2: Computed Offsets (`G LABEL+expr`) → Spec 007

**MUMPS Semantics**:
- `G LABEL+3` jumps to 3 lines after LABEL
- `G LABEL+N` where N is computed at runtime
- Target may not be a labeled line

**Trampoline Extension Options**:

| Approach | Description | Complexity |
|----------|-------------|------------|
| **Static offsets** | Analyze at compile time, pre-compute target label | Low |
| **Statement indexing** | Index every statement, dispatch to any | Medium |
| **Hybrid (recommended)** | Static for constants, runtime for dynamic | Medium |

**Verdict**: FEASIBLE with extensions. Static offsets work naturally; dynamic requires finer-grained dispatch.

#### Feature 3: External Routine GOTO (`G LABEL^ROUTINE`) → Spec 008

**MUMPS Semantics**:
- `G LABEL^ROUTINE` transfers control to another routine entirely
- Current stack is unwound (caller doesn't continue)
- Different from `DO LABEL^ROUTINE` (which returns)

**Trampoline Extension Options**:

| Approach | Description | Pros/Cons |
|----------|-------------|-----------|
| **Exception-based** | Raise `GotoExternal(routine, label)` | Clean stack unwinding ✅ |
| **Return sentinel** | Return `('__EXTERNAL__', 'RTN^LABEL', state)` | Requires checking every iteration |
| **Unified dispatcher** | Global registry routes across routines | Most flexible |

**State Considerations**:
- External GOTO may need to pass state to other routine
- RoutineState may need shared/global state layer for cross-routine variables
- Or serialization for state transfer

**Verdict**: FEASIBLE with architectural extension. Exception-based is cleanest for stack unwinding.

#### Extension Feasibility Matrix

| Feature | Trampoline | RoutineState | Effort |
|---------|------------|--------------|--------|
| Computed static (`G LABEL+3`) | ✅ Easy | N/A | Low |
| Computed dynamic (`G LABEL+N`) | ⚠️ Possible | N/A | Medium |
| External (`G LABEL^ROUTINE`) | ⚠️ Possible | ⚠️ Extend | Medium |
| Indirect (`G @VAR`) | ✅ Natural | N/A | Low |
| Indirect external (`G @VAR^@RTN`) | ⚠️ Possible | ⚠️ Extend | Medium |

#### Comparison: State Machine Alternative

If we had chosen state machine instead of trampoline:

| Feature | State Machine | Trampoline |
|---------|--------------|------------|
| Computed offsets | Equally complex | Equally complex |
| External routines | Same problem (per-routine) | Same problem |
| Indirect GOTO | Works equally well | Works equally well |

**Conclusion**: Both patterns have similar extension capabilities. Trampoline wins on modularity (labels as functions) without sacrificing extensibility.

#### Decision: **PROCEED WITH SELECTED PATTERNS**

**Rationale**:

1. **Indirect GOTO is naturally supported**: String-based dispatch requires no changes

2. **External GOTO is architecturally feasible**: Exception-based transfer is clean

3. **Computed offsets are tractable**: Static resolution handles common case; dynamic is deferrable

4. **No additional spike needed**: Implementation details can be addressed in their respective specs

5. **ASG infrastructure already exists**: All required fields are in place

**Optional Architecture Prep** (can defer):
- Consider making label registry global vs per-routine (for external GOTOs)
- Consider `GotoExternal` exception class skeleton

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
