# SubscriptCanonicalizer Interface Contract

**Component**: `src/m2py/core/subscripts.py`  
**Type**: Utility Module (static methods)

## Purpose

Canonicalize subscript values according to MUMPS rules. Numeric subscripts have a single canonical form; string subscripts are preserved unless they represent canonical numeric values.

## Interface

```python
class SubscriptCanonicalizer:
    """Canonicalize subscript values per MUMPS specification.
    
    MUMPS subscript canonicalization rules:
    - Numeric literals are canonicalized (01 → 1, 1.0 → 1)
    - Purely numeric strings are canonicalized ("1" → "1", same as 1)
    - Non-numeric strings are preserved exactly ("01" with leading zero preserved)
    
    Constitution II: YDB behavior is authoritative for edge cases.
    """
    
    @staticmethod
    def canonicalize(value: Any) -> str:
        """Return canonical string representation of subscript value.
        
        Args:
            value: Subscript value (int, float, str, or MArray with value)
            
        Returns:
            Canonical string representation
            
        Examples:
            canonicalize(1) → "1"
            canonicalize(01) → "1"        # Numeric literal
            canonicalize(1.0) → "1"       # Float to int when possible
            canonicalize(1.5) → "1.5"
            canonicalize("1") → "1"       # Purely numeric string
            canonicalize("01") → "01"     # Leading zero preserved (not canonical numeric)
            canonicalize("1X") → "1X"     # Non-numeric preserved
        """
        ...
    
    @staticmethod
    def canonicalize_numeric(n: Union[int, float]) -> str:
        """Canonicalize a numeric value.
        
        Rules:
        - Integer: str(n)
        - Float equal to int: str(int(n))
        - Float with fractional: Remove trailing zeros
        
        Examples:
            1 → "1"
            1.0 → "1"
            1.50 → "1.5"
            0.5 → ".5"
        """
        ...
    
    @staticmethod
    def is_canonical_numeric_string(s: str) -> bool:
        """Check if string represents a canonical numeric value.
        
        A string is canonical numeric if:
        - It can be parsed as a number
        - AND it equals its canonical form
        
        Examples:
            "1" → True
            "01" → False (leading zero)
            "1.0" → False (trailing zero)
            "1.5" → True
            "1X" → False (not numeric)
            "" → False (empty)
        
        Used to determine if string subscript should be treated
        as equivalent to numeric subscript.
        """
        ...
    
    @staticmethod
    def subscripts_equal(a: Any, b: Any) -> bool:
        """Check if two subscript values refer to the same node.
        
        Compares canonical forms.
        
        Examples:
            subscripts_equal(1, "1") → True
            subscripts_equal(1, "01") → False
            subscripts_equal(01, 1) → True (numeric literal)
        """
        return canonicalize(a) == canonicalize(b)
```

## Test Cases (from MUGJ and YDB verification)

```python
# Numeric canonicalization
assert SubscriptCanonicalizer.canonicalize(1) == "1"
assert SubscriptCanonicalizer.canonicalize(01) == "1"  # Numeric literal
assert SubscriptCanonicalizer.canonicalize(1.0) == "1"
assert SubscriptCanonicalizer.canonicalize(1.5) == "1.5"
assert SubscriptCanonicalizer.canonicalize(1.50) == "1.5"
assert SubscriptCanonicalizer.canonicalize(0.5) == ".5"

# String handling - canonical numeric strings
assert SubscriptCanonicalizer.canonicalize("1") == "1"
assert SubscriptCanonicalizer.canonicalize("1.5") == "1.5"

# String handling - non-canonical (PRESERVED)
assert SubscriptCanonicalizer.canonicalize("01") == "01"  # Leading zero
assert SubscriptCanonicalizer.canonicalize("1.0") == "1.0"  # Trailing zero
assert SubscriptCanonicalizer.canonicalize("1X") == "1X"  # Non-numeric

# Equality checks
assert SubscriptCanonicalizer.subscripts_equal(1, "1")
assert SubscriptCanonicalizer.subscripts_equal(01, 1)
assert not SubscriptCanonicalizer.subscripts_equal(1, "01")
assert not SubscriptCanonicalizer.subscripts_equal("1", "01")

# is_canonical_numeric_string
assert SubscriptCanonicalizer.is_canonical_numeric_string("1")
assert SubscriptCanonicalizer.is_canonical_numeric_string("1.5")
assert SubscriptCanonicalizer.is_canonical_numeric_string(".5")
assert not SubscriptCanonicalizer.is_canonical_numeric_string("01")
assert not SubscriptCanonicalizer.is_canonical_numeric_string("1.0")
assert not SubscriptCanonicalizer.is_canonical_numeric_string("1X")
assert not SubscriptCanonicalizer.is_canonical_numeric_string("")
```

## YDB Verification Commands

```bash
# 1 and "1" are same node
echo 'TEST S A(1)="one" W A("1") Q' | docker run --rm -i ydb
# Output: one

# 1 and "01" are DIFFERENT nodes
echo 'TEST S A(1)="one" S A("01")="zero-one" W A(1),!,A("01") Q' | docker run --rm -i ydb
# Output:
# one
# zero-one

# Numeric literal 01 canonicalizes to 1
echo 'TEST S A(01)="x" W A(1) Q' | docker run --rm -i ydb
# Output: x
```

## Usage Examples

### Codegen Usage
```python
# When generating subscript access
from m2py.core.subscripts import SubscriptCanonicalizer

def generate_subscript(sub: MLiteral) -> str:
    # Canonicalize literal subscripts at compile time
    canonical = SubscriptCanonicalizer.canonicalize(sub.value)
    return repr(canonical)
```

### Runtime Usage  
```python
# When building subscript key for MArray
from m2py.core.subscripts import SubscriptCanonicalizer

def build_key(subscripts: List[Any]) -> Tuple:
    return tuple(SubscriptCanonicalizer.canonicalize(s) for s in subscripts)
```

## Dependencies

- None (standalone utility)

## Consumers

- `src/m2py/codegen/*.py` - Codegen subscript generation
- `src/m2py/runtime/__init__.py` - Runtime subscript handling
- `src/m2py/runtime/globals.py` - Global variable subscript access
