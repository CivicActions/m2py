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
    requires_runtime_scope: bool    # True if indirection/XECUTE
    scope_strategy: ScopeStrategy   # Code gen approach
    transitive_inputs: Set[str]     # Including callee needs
    transitive_outputs: Set[str]    # Including callee effects
```

**requires_runtime_scope**: Set to True when a label contains:
- XECUTE statements (executes arbitrary code at runtime)
- ANY MIndirection node anywhere in expressions:
  - `S @VAR=expr` (SET to indirect variable)
  - `W @VAR` (WRITE with indirect variable)
  - `$O(@VAR)` (indirect in function arguments)
  - `A(@I)` (indirect subscripts)
  - `D @VAR`, `G @VAR` (indirect DO/GOTO targets)
  - Pattern indirection (`X?@PAT`)

The detection is comprehensive - it walks ALL expressions in the ASG
to find any MIndirection nodes, ensuring no indirection is missed.

When True, static analysis is insufficient - the code generator must include runtime scope support.

## MRoutine Fields Populated

| Field | Description |
|-------|-------------|
| `requires_runtime_eval` | True if ANY label requires runtime scope |

The routine-level `requires_runtime_eval` is a rollup of all label signatures. It enables quick checks during code generation to determine if a routine needs runtime scope infrastructure.

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

## Expression Variable Extraction

The `_extract_expression_variables()` function extracts variable references from all expression types. This is critical for accurate input/output computation.

### Handled Expression Types

| Expression Type | Variable Extraction |
|-----------------|---------------------|
| `MVariable` | Extract variable name and recursively check subscripts |
| `MBinaryOp` | Extract from left and right operands |
| `MUnaryOp` | Extract from operand |
| `MLiteral` | None (no variables) |
| `MIntrinsicFunction` | Extract from arguments |
| `MExtrinsicFunction` | Extract from arguments |
| `MSpecialVariable` | None ($TEST, $HOROLOG are not variables) |
| `MActualParameter` | Extract from expression |
| `MSelectArg` | Extract from condition and value |
| `MPatternMatch` | Extract from subject and pattern_indirect |
| `MGlobal` | Extract from subscripts (global name excluded) |
| `MNakedGlobal` | Extract from subscripts |
| `MFormatControl` | Extract from expression (for ?X and *N formats) |
| `MIndirection` | Extract from expression, subscripts, and name_indirection_subscripts |

### Examples

```mumps
; Pattern match: X?1N.A
; Extracts: {X} (subject of pattern match)

; Global with local subscripts: ^DATA(I,J)
; Extracts: {I, J} (local vars used as subscripts)

; Format control: W ?COL
; Extracts: {COL} (tab column expression)

; Indirection: S @VAR(I)=1
; Extracts: {VAR, I} (indirect name and subscript)
```

### byref_outputs Computation

The `byref_outputs` field is populated by `compute_function_signature()`:

1. Scan the label's `formal_params` list
2. Check if each formal parameter is in `scope_vars.writes`
3. If written, add to `byref_outputs`

```python
# In compute_function_signature():
for formal_param in sig.formal_params:
    if formal_param in scope_vars.writes:
        sig.byref_outputs.add(formal_param)
```

This enables precise detection of which formal parameters are modified:

```mumps
SWAP(X,Y)     ; Both X and Y written → byref_outputs = {X, Y}
       N T
       S T=X,X=Y,Y=T
       Q

ADD(A,B)      ; A and B only read → byref_outputs = {}
       N R
       S R=A+B
       Q R
```

### Transitive Output Propagation

For nested call chains with by-ref parameters:

```mumps
OUTER  D MIDDLE(.X)
       Q
MIDDLE(A)
       D INNER(.A)
       Q
INNER(B)
       S B=B*2       ; B written → in INNER's byref_outputs
       Q
```

The `compute_transitive_outputs()` function propagates modifications:
- INNER writes B → B in INNER's `byref_outputs`
- MIDDLE passes A to INNER by-ref → A in MIDDLE's `transitive_outputs`
- OUTER passes X to MIDDLE by-ref → X in OUTER's `transitive_outputs`

This enables detecting all variables modified through call chains.
