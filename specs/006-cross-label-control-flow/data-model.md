# Data Model: Cross-Label Control Flow

**Spec**: 006-cross-label-control-flow  
**Date**: 2026-01-11  
**Status**: Draft

## Overview

This document defines the ASG additions required for cross-label GOTO code generation. All additions follow the layer separation principle: ASG provides complete information; codegen consumes it.

## New ASG Fields

### MRoutine.needs_trampoline

**Location**: `src/m2py/asg/elements.py`

**Purpose**: Indicates routine has ANY cross-label GOTOs that require trampoline pattern for proper control flow.

```python
@dataclass
class MRoutine(ASGElement):
    # ... existing fields ...
    
    # T006: Cross-label control flow analysis
    needs_trampoline: bool = False  # True if ANY cross-label GOTOs detected
```

**Set by**: `classify_gotos()` in `analysis/goto_analysis.py` after detecting cross-label GOTO targets.

**Used by**: Strategy selector in `codegen/__init__.py` to choose:
- `needs_trampoline=True` → trampoline pattern with RoutineState
- `needs_trampoline=False` → simple labels-as-functions (no cross-label GOTOs)

**Note**: State machine pattern was evaluated but DEFERRED. Trampoline handles all patterns including cycles (47.5% of VistA routines).

**Relationship to `has_unstructured_goto`**:
- `has_unstructured_goto=True` → DEFERRED (state machine for irreducible flow)
- `needs_trampoline=True` → trampoline (handles all cross-label patterns)
- Both `False` → simple labels-as-functions

---

## Modified Analysis Functions

### _detect_goto_cycles() (NEW)

**Location**: `src/m2py/analysis/goto_analysis.py`

**Purpose**: Build label→label edge graph and detect cycles using DFS.

```python
def _detect_goto_cycles(routine: MRoutine) -> bool:
    """Detect cycles in cross-label GOTO graph.
    
    Builds directed graph where nodes are labels and edges are 
    cross-label GOTOs. Uses DFS to detect back edges (cycles).
    
    Args:
        routine: The MRoutine to analyze
        
    Returns:
        True if cycles detected, False otherwise
    """
    # Implementation in Phase 1.2
    pass
```

**Called from**: `classify_gotos()` after individual GOTO classification.

**Algorithm**:
1. Build adjacency list: `{label_name: [target_label_names]}` for cross-label GOTOs
2. DFS with coloring (WHITE=unvisited, GRAY=in-progress, BLACK=done)
3. Cycle exists if we visit a GRAY node

---

## Verified Existing Fields

These fields from Spec 005 are required and verified to exist:

### MGotoStatement

| Field | Type | Purpose | Verification |
|-------|------|---------|--------------|
| `targets` | `List[MCall]` | GOTO target(s) | ✅ Used in current codegen |
| `is_cross_label` | `bool` | True if target in different label | ✅ Set by `classify_gotos()` |
| `goto_type` | `GotoType` | FORWARD_JUMP, BACKWARD_JUMP, etc. | ✅ Set by `classify_gotos()` |
| `exits_loops` | `List[MForStatement]` | Enclosing FORs if loop exit | ✅ Set by `classify_gotos()` |

### MLabel

| Field | Type | Purpose | Verification |
|-------|------|---------|--------------|
| `input_variables` | `Set[str]` | Variables read from caller scope | ✅ Set by variable analysis |
| `output_variables` | `Set[str]` | Variables written and visible to caller | ✅ Set by variable analysis |
| `goto_sources` | `List[MGotoStatement]` | Back-references from GOTOs targeting this label | ✅ Populated in resolution |
| `signature` | `FunctionSignature` | Clean function signature | ✅ Computed by `compute_signatures()` |

### MRoutine

| Field | Type | Purpose | Verification |
|-------|------|---------|--------------|
| `has_unstructured_goto` | `bool` | DEFERRED - reserved for future state machine | Not set in Spec 006 |
| `needs_trampoline` | `bool` | Trampoline required (ANY cross-label GOTOs) | ✅ Set by `classify_gotos()` |
| `labels` | `List[MLabel]` | All labels in routine | ✅ Core field |

---

## New Codegen Types

### RoutineState (Conditional)

**Location**: `src/m2py/codegen/shared_state.py` (if spike selects this pattern)

**Purpose**: Shared state class for cross-label variable visibility.

```python
@dataclass
class RoutineState:
    """Shared state for labels-as-functions with trampoline.
    
    All variables that flow between labels are stored here.
    Each label function receives and returns this state object.
    """
    # Fields populated from union of all label.input_variables + label.output_variables
    # Example:
    x: Any = None
    y: Any = None
    
    # For subscripted locals (if MArray approach selected):
    A: MArray = field(default_factory=MArray)
```

**Generation**: Built dynamically per-routine based on cross-label variable analysis.

### MArray (Conditional)

**Location**: `src/m2py/runtime/__init__.py` (if subscripted locals spike confirms)

**Purpose**: MUMPS array with value AND children at each node.

```python
class MArray:
    """MUMPS sparse array implementation.
    
    Each node can have both a value and children, unlike Python dicts.
    Example: A has value 1, A(1) has value 2, A(1,2) has value 3
    """
    
    def __init__(self, value=None):
        self._value = value
        self._children = {}
    
    def __getitem__(self, key):
        """Get child node at key (creates if not exists)."""
        if key not in self._children:
            self._children[key] = MArray()
        return self._children[key]
    
    def __setitem__(self, key, value):
        """Set value at key."""
        if key not in self._children:
            self._children[key] = MArray()
        self._children[key]._value = value
    
    @property
    def value(self):
        """Get this node's value (empty string if None)."""
        return self._value if self._value is not None else ""
    
    @value.setter
    def value(self, val):
        """Set this node's value."""
        self._value = val
```

**Usage in codegen**:
```python
# MUMPS: S A(1)=10,A(2)=20
A = MArray()
A[1] = 10  # or A[1].value = 10
A[2] = 20

# MUMPS: W A(1)+A(2)
_rt.write(str(m_num(A[1].value) + m_num(A[2].value)))
```

---

## Entity Relationships

```
MRoutine
├── has_unstructured_goto: bool  → DEFERRED (state machine if truly irreducible)
├── needs_trampoline: bool (NEW) → triggers trampoline (ANY cross-label GOTOs)
└── labels: List[MLabel]
    ├── input_variables: Set[str]  → shared state fields (reads)
    ├── output_variables: Set[str] → shared state fields (writes)
    ├── signature: FunctionSignature
    └── body: MScope
        └── statements: List[MStatement]
            └── MGotoStatement
                ├── targets: List[MCall]
                ├── is_cross_label: bool
                ├── goto_type: GotoType
                └── exits_loops: List[MForStatement]
```

**Strategy Selection Logic**:
```
if routine.needs_trampoline:
    strategy = TRAMPOLINE  # Handles all cross-label patterns including cycles
else:
    strategy = LABELS_AS_FUNCTIONS
# Note: STATE_MACHINE deferred - trampoline handles all known patterns
```

---

## Validation Rules

| Rule | Validation | Error |
|------|------------|-------|
| `needs_trampoline` when ANY cross-label GOTOs | Assert cross-label GOTO detected | "needs_trampoline set without cross-label GOTOs" |
| `has_unstructured_goto` reserved for future | DEFERRED - not currently set | "has_unstructured_goto set (unexpected)" |
| All cross-label GOTOs have `is_cross_label=True` | Assert target label != source label | "Cross-label GOTO not flagged" |

---

## Migration Notes

- No breaking changes to existing ASG
- `needs_trampoline` defaults to `False` (backward compatible)
- Existing `has_unstructured_goto` logic unchanged
- Spike results may modify this document before implementation
