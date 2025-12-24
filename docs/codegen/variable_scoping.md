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
@dataclass
class FunctionSignature:
    formal_params: List[str]      # From label(A,B)
    required_inputs: Set[str]     # Non-formal inputs
    optional_inputs: Set[str]     # May come from caller
    return_value: Optional[Any]   # From QUIT analysis
    byref_outputs: Set[str]       # Modified by-ref params
    side_effect_outputs: Set[str] # Non-NEWed writes
    scope_strategy: ScopeStrategy # Code gen approach
```

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
def init():
    global x, y
    x = 1
    y = 2
```

Or with explicit return:
```python
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
def swap(x, y):
    return y, x  # Return swapped values

# At call site: x, y = swap(x, y)
```

Or with mutable container:
```python
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

```python
sig = label.signature

if sig.scope_strategy == ScopeStrategy.PURE_FUNCTION:
    # def name(formal_params) -> T:
    #     return value
    pass

elif sig.scope_strategy == ScopeStrategy.FUNCTION_WITH_OUTPUTS:
    # def name(formal_params, required_inputs) -> Tuple[return, outputs]:
    #     return value, output1, output2
    pass

elif sig.scope_strategy == ScopeStrategy.SUBROUTINE:
    if sig.side_effect_outputs:
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
