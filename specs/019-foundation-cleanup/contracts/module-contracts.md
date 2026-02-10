# Module Contracts: Phase 1 — Foundation & Cleanup

These contracts define the public interfaces of the new modules created in Phase 1.
They are the "API" that callers depend on — changing them after Phase 2 begins
would require updating Phase 2's work.

## `core/values.py`

```python
"""MUMPS value semantics — canonical source of truth.

All MUMPS value-model functions live here. codegen/helpers.py re-exports
them for backward compatibility with generated code.
"""
from decimal import Decimal
from typing import Any, Union

def mumps_canonical_str(value: Union[int, float, Decimal]) -> str:
    """Convert a numeric value to MUMPS canonical string representation.
    
    Rules:
    - No trailing zeros after decimal point
    - No unnecessary decimal point for integers
    - No leading zero for |value| < 1 (0.5 → ".5")
    - No scientific notation (1E+2 → "100")
    - Exponent guard: exponent < -43 → "0"
    
    Args:
        value: A numeric value (int, float, or Decimal)
    
    Returns:
        MUMPS canonical string representation
    """
    ...

def m_str(value: Any) -> str:
    """Convert any value to MUMPS string representation.
    
    - str → returned as-is
    - MArray → unwrap .value, then format
    - numeric types → mumps_canonical_str()
    - None/empty → ""
    """
    ...

def m_num(value: Any) -> Union[int, float, Decimal]:
    """Convert any value to MUMPS numeric.
    
    Scans left-to-right for leading numeric portion.
    - "" → 0
    - "123ABC" → 123
    - ".5" → Decimal("0.5")
    """
    ...

def m_truth(value: Any) -> bool:
    """Evaluate MUMPS truth value.
    
    True if m_num(value) != 0.
    """
    ...

def m_compare(left: Any, op: str, right: Any) -> int:
    """MUMPS comparison returning 1 (true) or 0 (false).
    
    ops: "=", "'=", "<", "'>", ">", "'<", ">=", "<=", "]]", "']]", "[", "'["
    String comparison is byte-by-byte; numeric if both canonic.
    """
    ...

def m_add(left: Any, right: Any) -> Union[int, Decimal]:
    """MUMPS addition: m_num(left) + m_num(right)."""
    ...

def m_sub(left: Any, right: Any) -> Union[int, Decimal]:
    """MUMPS subtraction: m_num(left) - m_num(right)."""
    ...

def m_mul(left: Any, right: Any) -> Union[int, Decimal]:
    """MUMPS multiplication: m_num(left) * m_num(right)."""
    ...
```

## `core/parsing.py`

```python
"""String-level parsing utilities for MUMPS name/subscript expressions."""

def parse_subscripted_name(name: str) -> tuple[str, list[str]]:
    """Parse a possibly-subscripted MUMPS name.
    
    Args:
        name: e.g. 'ARR(1,"A,B",3)' or 'X'
    
    Returns:
        (base_name, subscript_list) where subscript_list is [] for
        unsubscripted names. Subscripts are raw strings — no numeric
        conversion.
    
    Examples:
        'ARR(1,2)' → ('ARR', ['1', '2'])
        'X' → ('X', [])
        'A("B,C")' → ('A', ['"B,C"'])
    """
    ...

def canonicalize_subscript(sub: str) -> Union[int, float, str]:
    """Convert a raw subscript string to its canonical Python type.
    
    Numeric strings → int or float. Non-numeric → str.
    Used only by runtime storage operations where type matters
    for lookup matching.
    """
    ...
```

## `core/tokenizer.py`

```python
"""Delimiter-aware string splitting respecting nesting and quotes."""

def split_at_toplevel(
    s: str,
    delimiter: str = ",",
    respect_quotes: bool = True,
) -> list[str]:
    """Split a string at top-level occurrences of delimiter.
    
    "Top-level" means not inside parentheses or (optionally) quotes.
    
    Args:
        s: Input string
        delimiter: Character to split on (default: comma)
        respect_quotes: If True, don't split inside double quotes
    
    Returns:
        List of substrings. Empty input → [''].
    
    Examples:
        'A,B,C' → ['A', 'B', 'C']
        'A(1,2),B' → ['A(1,2)', 'B']
        'A,"B,C",D' → ['A', '"B,C"', 'D']  (with respect_quotes=True)
    """
    ...
```

## `codegen/helpers.py` — Independent Implementations

```python
# codegen/helpers.py retains its own implementations of:
#   m_str, m_num, m_truth, m_compare, m_add, m_sub, m_mul
#   m_div, m_mod, m_range (codegen-only)
#
# core/values.py is the canonical source for runtime/ and core/ imports.
# codegen/helpers.py keeps independent copies because generated Python code
# imports from codegen.helpers. Both implementations must stay in sync.
```

## `codegen/shared_state.py` — Updated Predicate

```python
def routine_uses_dynamic_locals(routine: "MRoutine") -> bool:
    return (
        routine.has_argumentless_kill
        or routine.has_argumentless_new
        or routine.has_exclusive_kill      # NEW
        or routine.has_exclusive_new       # NEW
        or routine.has_name_indirection_on_locals
        or routine.has_external_gotos
    )
```

## `asg/elements.py` — Extended MRoutine & MScope

```python
@dataclass
class MRoutine(ASGElement):
    # ... existing fields ...
    has_exclusive_kill: bool = False    # NEW — K (X) forms
    has_exclusive_new: bool = False     # NEW — N (X) forms

@dataclass
class MScope(ASGElement):
    statements: List["MStatement"] = field(default_factory=list)

    def walk_statements(self) -> Iterator["MStatement"]:
        """Yield all statements recursively, including nested scopes.

        Walks through all statements in this scope and recurses into
        any nested scopes (IF then/else bodies, FOR bodies, DO blocks, etc.).
        Covers get_body_scope, get_then_scope, and get_else_scope
        to ensure complete statement coverage (S-10, FR-010).
        """
        ...
```

## Runtime Callback Contract

```python
class MUMPSRuntime:
    def __init__(self, ..., codegen_callback=None):
        """
        codegen_callback: Optional callable with signature
            (code: str, routine_name: str) -> str
        Used for XECUTE to compile MUMPS code to Python at runtime.
        If None, XECUTE raises an error.
        """
        self._codegen_callback = codegen_callback
```
