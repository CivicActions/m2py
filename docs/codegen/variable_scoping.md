# Variable Scoping and Function Signatures

How to generate Python functions with proper arguments and returns.

## MUMPS Scoping Model

MUMPS variables have unique scoping semantics:

1. **Default visibility**: Variables are visible to callees unless NEWed
2. **NEW creates local scope**: `N X` saves caller's X, creates new local X
3. **Formal parameters are implicitly NEWed**: Parameters are local to callee
4. **Call-by-reference creates aliases**: `.X` in argument list

## Variable Analysis Fields

After `analyze_variables()`, each MLabel has:

| Field | Description |
|-------|-------------|
| `formal_list` | Parameter names from label definition |
| `variables_read` | All variables read |
| `variables_written` | All variables written |
| `variables_newed` | Explicitly NEWed variables |
| `input_variables` | Read before write, not NEWed (from caller) |
| `output_variables` | Written, not NEWed (visible to caller) |

## Computing Function Signatures

### FunctionSignature Structure

```python
# Conceptual Python equivalent

@dataclass
class FunctionSignature:
    formal_params: List[str]      # From label(A,B)
    required_inputs: Set[str]     # Non-formal inputs
    optional_inputs: Set[str]     # May come from caller
    return_value: Optional[Any]   # From QUIT analysis
    byref_outputs: Set[str]       # Formal params written (modified by-ref)
    side_effect_outputs: Set[str] # Non-NEWed writes
    scope_strategy: ScopeStrategy # Code gen approach
    transitive_inputs: Set[str]   # Inputs including callee needs
    transitive_outputs: Set[str]  # Outputs including callee effects
```

**byref_outputs Population**: During `compute_function_signature()`, each formal 
parameter is checked against `scope_vars.writes`. If a formal param is written 
within the label body, it is added to `byref_outputs`. This enables precise 
detection of which parameters actually modify caller variables when passed by reference.

### ScopeStrategy Classification

| Strategy | Meaning | Python Pattern |
|----------|---------|----------------|
| `PURE_FUNCTION` | No side effects, returns value | `def f(args) -> T` |
| `FUNCTION_WITH_OUTPUTS` | Returns + side effects | `def f(args) -> Tuple` |
| `SUBROUTINE` | Side effects only | `def f(args) -> None` |
| `REQUIRES_RUNTIME` | Static analysis failed | Runtime scope |

## Translation Strategies

### Pure Function

```mumps
ADD(A,B)
    N R
    S R=A+B
    Q R
```

All variables are local (formal params + NEWed):
```python
# Conceptual Python equivalent

def add(a, b):
    r = a + b
    return r
```

### Subroutine with Side Effects

```mumps
INIT   S X=1
       S Y=2
       Q
```

X and Y are outputs (visible to caller):
```python
# Conceptual Python equivalent

def init():
    global x, y
    x = 1
    y = 2
```

Or with explicit return:
```python
# Conceptual Python equivalent

def init():
    return {"X": 1, "Y": 2}
```

### Function with Inputs from Caller

```mumps
CALC(A)
    S B=A+X     ; X comes from caller
    S Y=B*2     ; Y visible to caller
    Q B
```

Analysis:
- `formal_params = ["A"]`
- `input_variables = {"X"}` (read before write, not NEWed)
- `output_variables = {"Y"}` (written, not NEWed)

```python
# Conceptual Python equivalent

def calc(a, x):
    b = a + x
    y = b * 2
    return b, y

# At call site:
result, y = calc(a, x)
```

### Call-by-Reference

```mumps
SWAP(X,Y)
    N T
    S T=X,X=Y,Y=T
    Q
```

If called with `.X,.Y`, the caller's variables are modified:

```python
# Conceptual Python equivalent

def swap(x, y):
    return y, x  # Return swapped values

# At call site: x, y = swap(x, y)
```

Or with mutable container:
```python
# Conceptual Python equivalent

def swap(refs):
    refs["X"], refs["Y"] = refs["Y"], refs["X"]
```

## NEW Command Handling

### Selective NEW

```mumps
PROC   N X,Y
       S X=1,Y=2
       ; X and Y are local
       Q
```

Variables X and Y are shadowed:
```python
# Conceptual Python equivalent

def proc():
    x = 1  # Local to this function
    y = 2
```

### Exclusive NEW

```mumps
PROC   N (A,B)
       ; All vars except A,B are saved/local
       S X=1
       Q
```

This defeats static analysis - cannot enumerate affected variables:
```python
# Conceptual Python equivalent

def proc(a, b):
    # Requires runtime scope management
    runtime.exclusive_new(["A", "B"])
    runtime.set_local("X", 1)
```

## Transitive Analysis

For call chains, inputs/outputs propagate:

```mumps
MAIN   D OUTER
       W X
       Q
OUTER  D INNER
       Q
INNER  S X=1
       Q
```

After transitive analysis:
- INNER.output_variables = {X}
- OUTER.transitive_outputs = {X}
- MAIN sees X modified by calling OUTER

```python
# Conceptual Python equivalent

def main():
    outer()
    print(x)  # x was set by inner()

def outer():
    inner()

def inner():
    global x
    x = 1
```

## Decision Tree

The `scope_strategy` classification uses `byref_outputs` to determine optimal code generation:

```python
# Conceptual Python equivalent

sig = label.signature

if sig.scope_strategy == ScopeStrategy.PURE_FUNCTION:
    # No byref_outputs, no side_effect_outputs, has return value
    # def name(formal_params) -> T:
    #     return value
    pass

elif sig.scope_strategy == ScopeStrategy.FUNCTION_WITH_OUTPUTS:
    # Has return value AND (byref_outputs OR side_effect_outputs)
    # By-ref outputs require returning modified values for caller to update
    # def name(formal_params, required_inputs) -> Tuple[return, *outputs]:
    #     return value, modified_arg1, modified_arg2
    pass

elif sig.scope_strategy == ScopeStrategy.SUBROUTINE:
    if sig.byref_outputs:
        # No return value but modifies by-ref params
        # def name(formal_params) -> Tuple[...]:
        #     return modified_arg1, modified_arg2
        pass
    elif sig.side_effect_outputs:
        # def name(formal_params) -> Dict[str, Any]:
        #     return {"output1": val1, ...}
        pass
    else:
        # def name(formal_params) -> None:
        pass

elif sig.scope_strategy == ScopeStrategy.REQUIRES_RUNTIME:
    # def name():
    #     x = runtime.get_local("X")
    #     runtime.set_local("Y", value)
    pass
```

### By-Reference Handling Examples

**Minimal return values**: Only return by-ref params that are actually modified:

```mumps
; READER only reads A, doesn't modify
READER(A)
    W A
    Q

; byref_outputs = {} → caller can pass by-ref but no return needed
```

**Accurate modification tracking**:

```mumps
; SWAP modifies both parameters
SWAP(X,Y)
    N T
    S T=X,X=Y,Y=T
    Q

; byref_outputs = {"X", "Y"} → both must be returned
```

```python
# Conceptual Python equivalent

def swap(x, y):
    return y, x  # Return both modified params

# Caller: x, y = swap(x, y)
```

## Special Cases

### Indirection Defeats Analysis

```mumps
DYNAMIC
    S @VAR=1    ; Can't know which variable
    Q
```

Sets `requires_runtime_scope = True`.

### XECUTE Defeats Analysis

```mumps
EXEC   X CODE   ; Arbitrary code execution
       Q
```

Sets `requires_runtime_scope = True`.

### Argumentless KILL

```mumps
CLEAN  K        ; Kills all locals
       Q
```

Cannot enumerate affected variables.

## Best Practices

1. **Prefer pure functions** when analysis shows no side effects
2. **Use return values** for outputs rather than globals
3. **Fall back to runtime** only when necessary
4. **Document scope strategy** in generated code comments
