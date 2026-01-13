# API Contracts: Cross-Label Control Flow

**Spec**: 006-cross-label-control-flow  
**Date**: 2026-01-11

## Overview

This document defines the function signatures and interfaces for cross-label GOTO code generation.

---

## Analysis Functions

### goto_analysis.py

```python
def _detect_goto_cycles(routine: MRoutine) -> bool:
    """Detect cycles in cross-label GOTO graph.
    
    Args:
        routine: The MRoutine to analyze
        
    Returns:
        True if cycles detected, False otherwise
        
    Side Effects:
        None (pure function)
        
    Called By:
        classify_gotos() after individual GOTO classification
    """
    ...
```

### classify_gotos() modification

```python
def classify_gotos(routine: MRoutine) -> None:
    """Classify all GOTO statements in a routine.
    
    MODIFIED: Now also sets routine.needs_trampoline after
    detecting cycles via _detect_goto_cycles().
    
    Side Effects (additions for Spec 006):
        - Sets MRoutine.needs_trampoline if cycles detected
    """
    ...
```

---

## Codegen Functions

### Strategy Selection

```python
def select_codegen_strategy(routine: MRoutine) -> CodegenStrategy:
    """Select code generation strategy based on routine analysis.
    
    Args:
        routine: Analyzed MRoutine with all flags set
        
    Returns:
        CodegenStrategy enum value:
        - STATE_MACHINE: has_unstructured_goto=True
        - TRAMPOLINE: needs_trampoline=True
        - LABELS_AS_FUNCTIONS: default (neither flag set)
        
    Raises:
        ValueError: If routine not analyzed (missing flags)
    """
    ...
```

### Trampoline Generation

```python
def generate_trampoline_wrapper(
    routine: MRoutine,
    ctx: GeneratorContext
) -> None:
    """Generate trampoline dispatcher for cyclic GOTO patterns.
    
    Emits:
        _labels = {"LABEL1": LABEL1, "LABEL2": LABEL2, ...}
        def _run():
            state = RoutineState()
            label = "ENTRY_LABEL"
            while label is not None:
                label = _labels[label](state)
    
    Args:
        routine: MRoutine with needs_trampoline=True
        ctx: Generator context with emitter
        
    Side Effects:
        Writes to ctx.emitter
    """
    ...
```

### State Machine Generation

```python
def generate_state_machine(
    routine: MRoutine,
    ctx: GeneratorContext
) -> None:
    """Generate state machine for irreducible control flow.
    
    Emits:
        def _run_routine():
            state = "ENTRY_LABEL"
            # variables in outer scope
            while True:
                match state:
                    case "LABEL1":
                        ...
                    case None:
                        break
    
    Args:
        routine: MRoutine with has_unstructured_goto=True
        ctx: Generator context with emitter
        
    Side Effects:
        Writes to ctx.emitter
    """
    ...
```

### Label Function Generation (Modified)

```python
def generate_label_with_state(
    label: MLabel,
    state_class: type,
    ctx: GeneratorContext
) -> None:
    """Generate label function that receives/returns shared state.
    
    Emits:
        def LABEL(state: RoutineState) -> tuple[str | None, RoutineState]:
            # Extract input variables from state
            x = state.x
            # ... body ...
            # Return next label and updated state
            state.y = y
            return ("NEXT_LABEL", state)
    
    Args:
        label: MLabel to generate
        state_class: RoutineState class with shared variables
        ctx: Generator context
        
    Side Effects:
        Writes to ctx.emitter
    """
    ...
```

---

## Shared State

### RoutineState (if spike selects)

```python
@dataclass
class RoutineState:
    """Shared state for cross-label variable visibility.
    
    Generated per-routine based on variable analysis.
    Contains union of all label.input_variables and label.output_variables.
    
    Attributes:
        Field per cross-label variable, initialized to None
        
    Example:
        class _State:
            x: Any = None
            y: Any = None
            A: MArray = field(default_factory=MArray)
    """
    ...


def build_routine_state_class(routine: MRoutine) -> type:
    """Dynamically build RoutineState class for routine.
    
    Args:
        routine: Analyzed MRoutine
        
    Returns:
        Dataclass type with fields for all cross-label variables
    """
    ...
```

---

## MArray (if spike confirms)

```python
class MArray:
    """MUMPS sparse array with value AND children at each node.
    
    Unlike Python dict, each node can have both:
    - _value: The value at this node
    - _children: Child nodes keyed by subscript
    
    Example:
        A = MArray()
        A.value = 1       # A has value 1
        A[1] = 2          # A(1) has value 2
        A[1, 2] = 3       # A(1,2) has value 3
        # A.value still 1, A[1].value still 2
    """
    
    def __init__(self, value: Any = None) -> None: ...
    
    def __getitem__(self, key: Any | tuple) -> "MArray": 
        """Get or create child node at key."""
        ...
    
    def __setitem__(self, key: Any | tuple, value: Any) -> None:
        """Set value at key (creates path if needed)."""
        ...
    
    @property
    def value(self) -> Any:
        """Get this node's value (empty string if None)."""
        ...
    
    @value.setter
    def value(self, val: Any) -> None:
        """Set this node's value."""
        ...
```

---

## Enums

```python
class CodegenStrategy(Enum):
    """Code generation strategy for routine."""
    LABELS_AS_FUNCTIONS = "labels"     # Simple, no trampoline
    TRAMPOLINE = "trampoline"          # Cyclic GOTOs
    STATE_MACHINE = "state_machine"    # Irreducible flow
```

---

## Error Types

```python
class UnsupportedGotoPatternError(Exception):
    """Raised for GOTO patterns not supported in current spec.
    
    Examples:
        - Computed offset: G LABEL+expr (Spec 007)
        - External: G LABEL^ROUTINE (Spec 008)
        - Indirect: G @VAR (Spec 012)
    """
    pass
```

---

## Test Contracts

### Unit Test Interface

```python
def test_cross_label_forward_goto():
    """FR-001: Forward cross-label GOTO skips intermediate code."""
    source = """TEST S X=1 G NEXT S X=99 Q
NEXT W X Q"""
    result = execute_generated(source)
    assert result.output == "1"


def test_cross_label_backward_goto():
    """FR-002: Backward cross-label GOTO creates loop."""
    source = """TEST S X=0
LOOP S X=X+1 W X I X<5 G LOOP Q"""
    result = execute_generated(source)
    assert result.output == "12345"


def test_trampoline_prevents_stack_overflow():
    """FR-007: Trampoline handles 10000+ iterations."""
    source = """TEST S X=0
LOOP S X=X+1 I X<10000 G LOOP W X Q"""
    result = execute_generated(source)
    assert result.output == "10000"
    # No RecursionError


def test_variable_visibility_across_labels():
    """FR-003: Variables visible across label boundaries."""
    source = """TEST S A=10,B=20 G SUM Q
SUM W A+B Q"""
    result = execute_generated(source)
    assert result.output == "30"
```

### Integration Test Interface

```python
def test_v1go1_patterns():
    """All V1GO1.m patterns produce correct output."""
    source = read_file("tests/functional/mugj/inref/V1GO1.m")
    m2py_output = execute_generated(source)
    ydb_output = run_ydb(source)
    assert m2py_output == ydb_output
```
