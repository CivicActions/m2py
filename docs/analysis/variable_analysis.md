# Variable Analysis

The variable analyzer tracks reads, writes, and NEW scopes to compute function signatures.

**Source**: [`src/m2py/analysis/variables.py`](../../src/m2py/analysis/variables.py)

## Overview

Variable analysis enables generating Python functions with proper signatures instead of runtime scope lookups:

1. Collect variable reads and writes per label
2. Track NEW commands for scope boundaries
3. Compute input variables (read before first write)
4. Compute output variables (written and visible to caller)
5. Build call graphs for transitive closure
6. Generate `FunctionSignature` for each label

## MUMPS Variable Scoping

Understanding MUMPS scoping is essential for this analysis.

### Default Visibility

Variables not NEWed are visible from caller scope:

```mumps
CALLER S X=1
       D SUB
       W X      ; X now equals 2
       Q
SUB    S X=2    ; Modifies caller's X
       Q
```

### NEW Creates Local Scope

NEW saves the current value and creates a new empty variable:

```mumps
CALLER S X=1
       D SUB
       W X      ; X still equals 1
       Q
SUB    N X      ; Save caller's X, create new local X
       S X=2    ; Only affects local X
       Q        ; Restore caller's X
```

### Formal Parameters are Implicitly NEWed

Per MDC spec 8.1.14:

```mumps
CALLER D FUNC(5)
       Q
FUNC(X)         ; X is implicitly NEWed
       S X=X+1  ; Only affects local X
       Q
```

## Usage

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")
parser.analyze_variables(routine)

# Access computed sets on labels
for label in routine.labels:
    print(f"{label.name}:")
    print(f"  Inputs: {label.input_variables}")
    print(f"  Outputs: {label.output_variables}")
    print(f"  NEWed: {label.variables_newed}")
```

## Data Structures

### ScopeVariables

Per-label variable information:

```python
@dataclass
class ScopeVariables:
    reads: Set[str]           # All variables read
    writes: Set[str]          # All variables written
    newed: Set[str]           # Variables with NEW
    formal_params: Set[str]   # Formal parameter names
    input_variables: Set[str]  # Read before first write
    output_variables: Set[str] # Written, visible to caller
```

### FunctionSignature

Computed signature for code generation:

```python
@dataclass
class FunctionSignature:
    label_name: str
    formal_params: List[str]
    required_inputs: Set[str]       # Must come from caller
    optional_inputs: Set[str]       # May come from caller
    byref_outputs: Set[str]         # Modified via call-by-ref
    side_effect_outputs: Set[str]   # Other visible modifications
    has_value_quit: bool            # QUIT with return value
    has_void_quit: bool             # QUIT without value
    scope_strategy: ScopeStrategy   # Code gen approach
    transitive_inputs: Set[str]     # Including callee needs
    transitive_outputs: Set[str]    # Including callee effects
```

## MLabel Fields Populated

| Field | Description |
|-------|-------------|
| `variables_read` | All variables read in label |
| `variables_written` | All variables written in label |
| `variables_newed` | Variables with NEW command |
| `input_variables` | Computed inputs (read before write, not NEWed) |
| `output_variables` | Computed outputs (written, not NEWed) |

## Input/Output Computation

### Input Variables

A variable is an input if:
- It is read before any write to it
- It is not NEWed (which creates local scope)
- It is not a formal parameter (implicitly NEWed)

```mumps
SUB(A)         ; A is formal → not an input
       N X     ; X is NEWed → not an input
       S Y=Z   ; Z read first → input
       S Y=Y+1 ; Y written before read here → not input
       W B     ; B read only → input
       Q
```

Inputs: `{Z, B}`

### Output Variables

A variable is an output if:
- It is written
- It is not NEWed (value survives return)
- It is not a formal parameter (restored on return)

```mumps
SUB(A)
       N X
       S A=5   ; A is formal → not output
       S X=1   ; X is NEWed → not output
       S Y=2   ; Y visible to caller → output
       Q
```

Outputs: `{Y}`

## Transitive Closure

For call chains, inputs/outputs propagate:

```mumps
MAIN   D OUTER
       Q
OUTER  S X=1
       D INNER
       Q
INNER  W Y      ; Y is input to INNER
       S Z=1    ; Z is output from INNER
       Q
```

After transitive analysis:
- `OUTER.transitive_inputs` includes `Y` (from INNER)
- `OUTER.transitive_outputs` includes `Z` (from INNER)

## ScopeStrategy Classification

| Strategy | Meaning | Code Gen |
|----------|---------|----------|
| `PURE_FUNCTION` | No side effects, value return | Pure Python function |
| `SUBROUTINE` | No return value, may have side effects | Procedure |
| `VALUE_RETURNING` | Returns value, may have side effects | Function with side effects |
| `REQUIRES_SCOPE` | Uses indirection/XECUTE | Runtime scope needed |

## RoutineAnalysisCache

For IDE scenarios with incremental updates:

```python
from m2py.analysis.variables import RoutineAnalysisCache

cache = RoutineAnalysisCache(routine)
cache.ensure_analyzed()

# After editing a label:
cache.invalidate_label("FOO")
cache.ensure_analyzed()  # Only recomputes affected labels
```

The cache tracks:
- Call graph (which labels call which)
- Reverse call graph (callers of each label)
- Hash of each label's content for change detection

## Code Generation Implications

### Pure Function

```mumps
ADD(A,B)
       N R
       S R=A+B
       Q R
```
```python
def add(a, b):
    return a + b
```

### Subroutine with Side Effects

```mumps
INIT   S X=1
       S Y=2
       Q
```
```python
def init():
    global x, y
    x = 1
    y = 2
```

### Mixed Inputs/Outputs

```mumps
PROC(A)
       S B=A+X     ; X is input (not formal, not NEWed)
       S Y=B*2     ; Y is output (not NEWed)
       Q
```
```python
def proc(a, x):     # X added as parameter
    global y        # Y is side effect
    b = a + x
    y = b * 2
```

## Call-by-Reference Tracking

```mumps
CALLER S X=1
       D MODIFY(.X)  ; Pass by reference
       W X           ; X now equals 2
       Q
MODIFY(R)
       S R=R+1       ; Modifies caller's X via alias
       Q
```

The analyzer tracks `PassingMode.BY_REFERENCE` to identify `byref_outputs`.
