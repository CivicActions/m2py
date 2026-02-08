# CurrentScope Interface Contract

**Component**: `src/m2py/core/scope.py`  
**Type**: Runtime Adapter Class

## Purpose

Unified interface for variable access that abstracts over different storage mechanisms (Python locals, _scope dict, state._locals). Ensures all variable access - static or indirected - uses the same lookup path.

## Interface

```python
class CurrentScope:
    """Unified variable access abstraction.
    
    Constitution VII: All variable access (static or indirected) uses
    same path, preventing "variable not found" bugs that occur when
    codegen uses Python locals but runtime uses _scope dict.
    
    This adapter unifies:
    - Python locals (PURE_FUNCTION strategy)
    - _scope dict (FUNCTION_WITH_OUTPUTS, SUBROUTINE strategies)
    - state._locals (REQUIRES_RUNTIME strategy)
    
    FR-036, FR-037: Provides the "Current Scope" abstraction from spec.
    """
    
    def __init__(
        self,
        scope_dict: Optional[Dict[str, Any]] = None,
        locals_dict: Optional[Dict[str, Any]] = None,
        state_locals: Optional['MArray'] = None,
        name_translator: Optional[NameTranslator] = None
    ):
        """Initialize scope with available storage mechanisms.
        
        Args:
            scope_dict: The _scope dict passed through generated code
            locals_dict: Python locals() for PURE_FUNCTION access
            state_locals: state._locals MArray for REQUIRES_RUNTIME
            name_translator: Optional custom translator (defaults to standard)
            
        At least one storage mechanism must be provided.
        Lookup order: scope_dict > locals_dict > state_locals
        """
        ...
    
    def get(
        self, 
        name: str, 
        default: Any = ""
    ) -> Any:
        """Get variable value by MUMPS name.
        
        Args:
            name: MUMPS variable name (e.g., "X", "%FOO", "A(1,2)")
            default: Value to return if not found (MUMPS undefined = "")
            
        Returns:
            Variable value, or default if undefined
            
        Note: Handles subscripted names by parsing and traversing.
        FR-038: Extracts .value from MArray objects automatically.
        """
        ...
    
    def get_subscripted(
        self,
        name: str,
        subscripts: List[Any],
        default: Any = ""
    ) -> Any:
        """Get subscripted variable value.
        
        Args:
            name: Base MUMPS variable name (no subscripts)
            subscripts: List of subscript values
            default: Value to return if not found
            
        Returns:
            Value at NAME(subscripts), or default
            
        Example:
            get_subscripted("A", [1, 2]) → value of A(1,2)
        """
        ...
    
    def set(
        self, 
        name: str, 
        value: Any
    ) -> None:
        """Set variable value by MUMPS name.
        
        Args:
            name: MUMPS variable name (may include subscripts)
            value: Value to set
            
        Creates intermediate MArray structures as needed for subscripted vars.
        """
        ...
    
    def set_subscripted(
        self,
        name: str,
        subscripts: List[Any],
        value: Any
    ) -> None:
        """Set subscripted variable value.
        
        Args:
            name: Base MUMPS variable name
            subscripts: List of subscript values
            value: Value to set
            
        Creates intermediate MArray structures as needed.
        """
        ...
    
    def exists(
        self, 
        name: str
    ) -> bool:
        """Check if variable is defined.
        
        Args:
            name: MUMPS variable name
            
        Returns:
            True if variable has a value (not just descendants)
            
        Corresponds to $DATA(name) in {1, 11} (has value)
        """
        ...
    
    def kill(
        self, 
        name: str
    ) -> None:
        """Remove variable and all descendants.
        
        Args:
            name: MUMPS variable name (may include subscripts)
            
        KILL A removes A and all A(subs)
        KILL A(1) removes A(1) and all A(1,subs) but not A or A(2)
        """
        ...
    
    @staticmethod
    def from_generated_context(
        _scope: Dict[str, Any],
        _locals: Optional[Dict[str, Any]] = None
    ) -> 'CurrentScope':
        """Factory for use in generated code.
        
        Creates CurrentScope from the context available in generated functions.
        
        Args:
            _scope: The _scope parameter passed to generated functions
            _locals: Result of locals() call, if available
            
        Returns:
            CurrentScope configured for the execution context
        """
        ...
```

## Implementation Notes

### Storage Priority

When multiple storage mechanisms are configured:
1. **scope_dict** checked first (most common case)
2. **locals_dict** checked second (PURE_FUNCTION optimization)
3. **state_locals** checked last (REQUIRES_RUNTIME fallback)

For sets, the primary mechanism (first non-None in order above) is used.

### Subscript Parsing

For names like `"A(1,2)"`, the scope parses out the base name and subscripts:

```python
def _parse_subscripted_name(self, name: str) -> Tuple[str, List[str]]:
    """Parse 'A(1,2)' into ('A', ['1', '2'])"""
    if "(" not in name:
        return (name, [])
    # Handle nested parens, quoted strings, etc.
    ...
```

### MArray Value Extraction

FR-038 requires extracting `.value` from MArray objects:

```python
def _extract_value(self, obj: Any) -> Any:
    """Extract value from MArray if needed."""
    if hasattr(obj, "value"):
        v = obj.value
        # Recursively extract if nested
        return self._extract_value(v) if v is not obj else v
    return obj
```

## Test Cases

```python
# Basic get/set
scope = CurrentScope(scope_dict={})
scope.set("X", 5)
assert scope.get("X") == 5
assert scope.get("Y") == ""  # Undefined returns empty string

# Subscripted access
scope.set_subscripted("A", [1, 2], "hello")
assert scope.get_subscripted("A", [1, 2]) == "hello"
assert scope.get("A(1,2)") == "hello"  # String form works too

# MArray value extraction
arr = MArray()
arr.value = "test"
scope.set("M", arr)
assert scope.get("M") == "test"  # Extracts .value

# Name translation
scope.set("%FOO", 42)  # Stored as _pct_FOO internally
assert scope.get("%FOO") == 42

# Exists check
scope.set("X", "value")
assert scope.exists("X")
assert not scope.exists("Y")

# Kill
scope.set_subscripted("A", [1], "a1")
scope.set_subscripted("A", [1, 1], "a11")
scope.set_subscripted("A", [2], "a2")
scope.kill("A(1)")  # Removes A(1) and A(1,1), keeps A(2)
assert not scope.exists("A(1)")
assert not scope.exists("A(1,1)")
assert scope.exists("A(2)")
```

## Usage Examples

### In Generated Code
```python
# Generated function signature
def MYROUTINE(_rt, _scope=None, _test=False):
    _scope = _scope if _scope is not None else {}
    _cs = CurrentScope.from_generated_context(_scope)
    
    # Variable access uses CurrentScope
    _cs.set("X", 5)
    result = _cs.get("Y")
    
    # Indirection uses same scope
    name = _cs.get("A")  # A contains variable name
    value = _cs.get(name)  # Unified lookup
```

### In Runtime
```python
# IndirectionResolver uses CurrentScope
class IndirectionResolver:
    def __init__(self, state, scope: CurrentScope):
        self._scope = scope
    
    def resolve(self, name, ...):
        value = self._scope.get(name)
        # ... resolution logic
```

## Dependencies

- `src/m2py/core/names.py` - NameTranslator for MUMPS↔Python
- `src/m2py/core/subscripts.py` - SubscriptCanonicalizer
- `src/m2py/runtime/__init__.py` - MArray class

## Consumers

- `src/m2py/codegen/*.py` - Generated code uses CurrentScope
- `src/m2py/runtime/indirection.py` - IndirectionResolver
- `src/m2py/runtime/__init__.py` - Various runtime methods
