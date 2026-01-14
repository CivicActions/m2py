# GlobalStorageBackend Protocol Contract

**Module**: `m2py.runtime.globals`  
**Type**: Protocol (structural typing)

## Interface Definition

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class GlobalStorageBackend(Protocol):
    """
    Protocol for MUMPS global variable storage backends.
    
    Implementations must provide persistent (or in-memory) storage
    for global variables with support for hierarchical subscripts,
    $DATA introspection, KILL operations, and naked reference tracking.
    """
    
    def get(self, name: str, subscripts: tuple[str, ...]) -> str | None:
        """
        Get value at ^NAME(subscripts).
        
        Args:
            name: Global name without caret (e.g., "PATIENT")
            subscripts: Tuple of string subscript values, may be empty
            
        Returns:
            String value if defined, None if undefined
            
        Side Effects:
            Updates naked indicator to (name, subscripts)
        """
        ...
    
    def set(self, name: str, subscripts: tuple[str, ...], value: str) -> None:
        """
        Set value at ^NAME(subscripts).
        
        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values, may be empty
            value: String value to store (MUMPS values are always strings)
            
        Side Effects:
            Updates naked indicator to (name, subscripts)
            Creates intermediate nodes if needed (auto-vivification)
        """
        ...
    
    def kill(self, name: str, subscripts: tuple[str, ...]) -> None:
        """
        Kill node and all descendants at ^NAME(subscripts).
        
        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values
                       Empty tuple kills entire global tree
                       
        Side Effects:
            Updates naked indicator to (name, subscripts)
            Removes value AND all descendant nodes
        """
        ...
    
    def kill_all(self) -> None:
        """
        Kill all globals. Used for testing/reset.
        
        Side Effects:
            Clears all global data
            Clears naked indicator
        """
        ...
    
    def data(self, name: str, subscripts: tuple[str, ...]) -> int:
        """
        Return $DATA value for ^NAME(subscripts).
        
        Args:
            name: Global name without caret
            subscripts: Tuple of string subscript values
            
        Returns:
            0 - Undefined, no descendants
            1 - Defined, no descendants  
            10 - Undefined, has descendants
            11 - Defined AND has descendants
            
        Side Effects:
            Updates naked indicator to (name, subscripts)
        """
        ...
    
    def get_naked_indicator(self) -> tuple[str, tuple[str, ...]] | None:
        """
        Get current naked indicator for ^(subscripts) resolution.
        
        Returns:
            (name, subscripts) from last global access, or None if unset
        """
        ...
    
    def set_naked_indicator(self, name: str, subscripts: tuple[str, ...]) -> None:
        """
        Explicitly set naked indicator (for internal use).
        
        Args:
            name: Global name
            subscripts: Last-accessed subscripts (not including final subscript)
        """
        ...
    
    def resolve_naked(self, subscripts: tuple[str, ...]) -> tuple[str, tuple[str, ...]]:
        """
        Resolve naked reference ^(subscripts) to full reference.
        
        Args:
            subscripts: Subscripts from naked reference
            
        Returns:
            (name, full_subscripts) where full_subscripts = indicator_subscripts[:-1] + subscripts
            
        Raises:
            RuntimeError: If no prior global reference (naked indicator unset)
        """
        ...
```

## Naked Indicator Semantics

The naked indicator tracks the **base** for subsequent naked references:

```
After ^G(1,2,3):
  naked_indicator = ("G", ("1", "2"))  # Note: only first n-1 subscripts
  
^(4) resolves to ^G(1,2,4)
^(5,6) resolves to ^G(1,2,5,6)
```

After a global SET/GET/KILL with **no subscripts**:
```
After ^G:
  naked_indicator = ("G", ())
  
^(1) resolves to ^G(1)
```

## Error Conditions

| Condition | Behavior |
|-----------|----------|
| Naked ref with no prior global access | `RuntimeError("NAKEDERR: Naked reference without prior global access")` |
| Invalid global name | Implementation-defined (may reject non-alpha start) |

## Implementation Notes

1. **Thread Safety**: Implementations for production use should be thread-safe
2. **Subscript Canonicalization**: All subscripts stored as strings in canonical form
3. **Empty String Value**: Empty string `""` is a valid defined value (distinct from undefined)
