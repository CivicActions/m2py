# IndirectionResolver Interface Contract

**Component**: `src/m2py/runtime/indirection.py`  
**Type**: Runtime Service Class

## Purpose

Runtime resolution of @-expressions (indirection). Handles single-level, multi-level, per-level subscripts, recursive @-expressions, and context-aware finalization (NAME vs ARGUMENT).

## Interface

```python
class IndirectionResolver:
    """Runtime resolver for @-expressions.
    
    Constitution VII: Used ONLY for truly dynamic cases where
    codegen cannot statically resolve the indirection.
    
    Supports:
    - Single level: @X
    - Multi-level: @@X, @@@X, etc.
    - Direct subscripts: @X(1,2)
    - Name indirection subscripts: @X@(1,2), @X@(1)@(2,3)
    - Recursive @-expressions: Value contains @, re-evaluated
    - Context-aware: NAME (variable lookup) vs ARGUMENT (expression eval)
    """
    
    def __init__(
        self, 
        state: 'MState',
        scope: 'CurrentScope'
    ):
        """Initialize resolver with runtime state and scope.
        
        Args:
            state: MState instance for global state, naked indicator, etc.
            scope: CurrentScope instance for unified variable access
        """
        self._state = state
        self._scope = scope
    
    def resolve(
        self,
        source: str,
        levels: int = 1,
        context: IndirectionContext = IndirectionContext.NAME,
        direct_subscripts: Optional[List[Any]] = None,
        per_level_subscripts: Optional[List[List[Any]]] = None
    ) -> Any:
        """Resolve indirection and return final value.
        
        Args:
            source: Initial variable name or expression string
            levels: Number of @ levels (1 for @X, 2 for @@X, etc.)
            context: How to use final resolved value
            direct_subscripts: Subscripts for @X(subs) form
            per_level_subscripts: Subscripts per resolution level for @X@(s1)@(s2)
            
        Returns:
            - NAME context: Variable value (string, MArray, etc.)
            - ARGUMENT context: Expression evaluation result
            
        Raises:
            VarExpectedError: NAME context and result not valid variable name
            LVUNDEFError: Reference to undefined variable (when required)
            SyntaxError: ARGUMENT context with invalid expression
            
        Examples:
            # @X where X="Y", Y=5
            resolve("X", 1, NAME) → 5
            
            # @@X where X="Y", Y="Z", Z=99
            resolve("X", 2, NAME) → 99
            
            # @X@(1,2) where X="A", A(1,2)="hello"
            resolve("X", 1, NAME, per_level_subscripts=[[1,2]]) → "hello"
            
            # @A where A="1=0" in IF context
            resolve("A", 1, ARGUMENT) → False
        """
        ...
    
    def resolve_name_indirection(
        self,
        name: str,
        subscripts: Optional[List[Any]] = None
    ) -> Any:
        """Convenience method for simple NAME indirection.
        
        Equivalent to resolve(name, 1, NAME, direct_subscripts=subscripts)
        """
        ...
    
    def resolve_argument_indirection(
        self,
        name: str
    ) -> Any:
        """Convenience method for ARGUMENT indirection.
        
        Equivalent to resolve(name, 1, ARGUMENT)
        """
        ...


class IndirectionContext(Enum):
    """Context for indirection final step.
    
    NAME: Result used as variable identifier
          SET @X=, WRITE @X, KILL @X, $DATA(@X)
          Error if result is not valid variable name
          
    ARGUMENT: Result evaluated as MUMPS expression  
              IF @A, FOR args, XECUTE @A, postconditions
              Empty string allowed (evaluates to false)
              
    SUBSCRIPT: Result used as subscript value
               A(1,@B,3) - indirection within subscript
               
    PATTERN: Result used as pattern for pattern match
             X?@P - pattern indirection
    """
    NAME = "name"
    ARGUMENT = "argument"
    SUBSCRIPT = "subscript"
    PATTERN = "pattern"
```

## Resolution Algorithm

```
resolve(source, levels, context, direct_subs, per_level_subs):
    current = source
    
    # 1. Resolve intermediate levels (NAME semantics)
    for i in range(levels - 1):
        value = scope.get(current)
        
        # Handle recursive @-expression
        while value.startswith("@"):
            value = resolve_recursive_at(value)
        
        # Apply per-level subscripts if any
        if per_level_subs and i < len(per_level_subs):
            value = append_subscripts(value, per_level_subs[i])
        
        current = value
    
    # 2. Apply direct subscripts to final reference
    if direct_subs:
        current = append_subscripts(current, direct_subs)
    
    # 3. Final resolution based on context
    if context == NAME:
        # Validate that result is valid variable name
        if not is_valid_var_name(current):
            raise VarExpectedError(current)
        return scope.get(current)
    
    elif context == ARGUMENT:
        # Evaluate as MUMPS expression
        return evaluate_expression(current)
```

## Expression Evaluation Requirement (Challenge 6 Fix)

The `evaluate_expression(expr_string)` function is **CRITICAL** for correct ARGUMENT indirection.

**Current bug**: Codegen returns string `"1=0"` to `m_truth()`, which converts to `1` (TRUE).

**Required behavior**: Parse and evaluate `"1=0"` as MUMPS expression → `0` (FALSE).

**Implementation options**:

1. **Lightweight expression parser** (preferred):
   - Parse expression string using textX MUMPS grammar
   - Transpile to Python expression
   - `eval()` with injected scope
   - ~100 lines, fast execution

2. **Reuse execute_mumps** (heavyweight fallback):
   - `execute_mumps(f"S TEMP={expr}", scope)`
   - Full transpilation overhead
   - Works but slow for repeated use

**evaluate_expression interface**:
```python
def evaluate_expression(self, expr_string: str) -> Any:
    """Evaluate MUMPS expression string and return result.
    
    Args:
        expr_string: MUMPS expression like "1=0", "X>5", "$E(S,1,3)"
        
    Returns:
        Evaluated result (number, string, etc.)
        
    Raises:
        SyntaxError: If expr_string is not valid MUMPS expression
        
    Examples:
        evaluate_expression("1=0") → 0  # False
        evaluate_expression("X>5") → 1  # True if X=10
        evaluate_expression("$E(\"ABC\",2)") → "B"
    """
```

## Test Cases (from MUGJ)

```python
# V1IDNM2 I-497: Basic name indirection
# S A="B",@A=1  ; Sets B=1
resolver = IndirectionResolver(state, scope)
scope.set("A", "B")
# When codegen calls: _rt.set_var(resolver.resolve("A", 1, NAME), 1)
# Result: B is set to 1

# V1IDNM2 I-507: Two levels
# S A1="@B2",B2="C3(2)",@@A*2  ; Gets C3(2)=4 → 4*2=8
scope.set("A1", "@B2")
scope.set("B2", "C3")
scope.set("C3", 4)
assert resolver.resolve("A1", 2, NAME) == 4

# VV2VNIA II-127: Multi-level with subscripts
# S X="A",A(1,2)="B(3,4)",@@X@(1,2)@(5,6)=1  ; B(3,4,5,6)=1
scope.set("X", "A")
scope.set("A", MArray())
scope["A"].set((1,2), "B(3,4)")
ref = resolver.resolve("X", 2, NAME, per_level_subscripts=[[(1,2)], [(5,6)]])
# ref should be "B(3,4,5,6)"

# V1IDARG1 I-417: Argument indirection
# S A="1=0" I @A  ; Evaluates "1=0" → False
scope.set("A", "1=0")
assert resolver.resolve("A", 1, ARGUMENT) == False

# S A="X>5",X=10 I @A  ; Evaluates "X>5" with X=10 → True
scope.set("A", "X>5")
scope.set("X", 10)
assert resolver.resolve("A", 1, ARGUMENT) == True

# V1IDNM2 I-503: Recursive @-expression
# S A="@$E(""ABCDEF"",3)",C=40
# S @A=50  ; @A resolves: A→"@$E(...)"; contains @, evaluate $E→"C"; @C→C
scope.set("A", "@$E(\"ABCDEF\",3)")
scope.set("C", 40)
# resolve("A", 1, NAME) should:
#   1. Get A → "@$E(\"ABCDEF\",3)"
#   2. Detect leading @, recursively resolve
#   3. Evaluate $E("ABCDEF",3) → "C"
#   4. Return value of C → 40
assert resolver.resolve("A", 1, NAME) == 40
```

## Error Cases

```python
# Invalid variable name in NAME context
scope.set("A", "1+1")
with pytest.raises(VarExpectedError):
    resolver.resolve("A", 1, NAME)

# Empty string in NAME context
scope.set("A", "")
with pytest.raises(VarExpectedError):
    resolver.resolve("A", 1, NAME)

# Empty string in ARGUMENT context - succeeds, returns False
scope.set("A", "")
assert resolver.resolve("A", 1, ARGUMENT) == False
```

## Dependencies

- `src/m2py/core/names.py` - NameTranslator for validation
- `src/m2py/core/subscripts.py` - SubscriptCanonicalizer
- `src/m2py/core/scope.py` - CurrentScope for variable access
- `src/m2py/runtime/__init__.py` - MState, execute_mumps for expression eval

## Consumers

- `src/m2py/codegen/indirection.py` - Generates calls to IndirectionResolver
- `src/m2py/runtime/__init__.py` - Direct use for XECUTE'd indirection
