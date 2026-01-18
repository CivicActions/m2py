# Data Model: Indirection & XECUTE Runtime

**Date**: 2026-01-16  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Overview

This document defines the data structures and relationships for implementing indirection and XECUTE support.

---

## Existing Entities (No Changes)

### MIndirection (ASG Node)

Already exists in [expressions.py#L262](../../src/m2py/asg/expressions.py#L262).

```python
@dataclass
class MIndirection(MExpr):
    """Indirection expression representing @expr."""
    expression: Optional[MExpr] = None
    indirection_type: IndirectionType = IndirectionType.UNKNOWN
    subscripts: Optional[List[MExpr]] = None  # For @X(1,2) form
    name_indirection_subscripts: Optional[List[List[MExpr]]] = None  # For @X@(1,2) form
    can_resolve_statically: bool = False
    resolved_value: Optional[str] = None
    requires_runtime_eval: bool = True
    result_type: Optional[str] = None
```

### MXecuteStatement (ASG Node)

Already exists in [statements.py#L547](../../src/m2py/asg/statements.py#L547).

```python
@dataclass
class MXecuteStatement(MStatement):
    """XECUTE command - runtime code execution."""
    code_expressions: List[MExpr] = field(default_factory=list)
    requires_runtime_eval: bool = True
    is_constant: bool = False  # True if all expressions are string literals
    constant_values: List[str] = field(default_factory=list)
```

### IndirectionType (Enum)

Already exists in [enums.py#L136](../../src/m2py/asg/enums.py#L136).

```python
class IndirectionType(Enum):
    NAME = auto()       # @X where X contains variable name
    SUBSCRIPT = auto()  # Y(@X) where X provides subscript
    ARGUMENT = auto()   # D @X where X contains label/routine
    PATTERN = auto()    # Y?@X where X contains pattern
    UNKNOWN = auto()    # Cannot determine statically
```

---

## New Entities

### IndirectionError (Exception)

New exception class for runtime indirection errors.

```python
@dataclass
class IndirectionError(Exception):
    """Raised for invalid indirection operations at runtime.
    
    Attributes:
        expression: The expression that caused the error (string representation)
        reason: Human-readable error description
        variable_name: Name of the variable being indirected (if applicable)
        variable_value: Value found in the variable (if applicable)
    """
    expression: str
    reason: str
    variable_name: Optional[str] = None
    variable_value: Optional[Any] = None
    
    def __str__(self) -> str:
        msg = f"Indirection error: {self.expression} - {self.reason}"
        if self.variable_name:
            msg += f" (variable '{self.variable_name}'"
            if self.variable_value is not None:
                msg += f" = '{self.variable_value}'"
            msg += ")"
        return msg
```

### CallTarget (Named Tuple)

Parsed representation of indirect DO/GOTO target.

```python
from typing import NamedTuple

class CallTarget(NamedTuple):
    """Parsed indirect call target.
    
    Represents the components of a DO/GOTO target string like:
    - "LABEL" → (label="LABEL", routine=None, offset=None)
    - "^ROUTINE" → (label=None, routine="ROUTINE", offset=None)
    - "LABEL^ROUTINE" → (label="LABEL", routine="ROUTINE", offset=None)
    - "LABEL+5" → (label="LABEL", routine=None, offset=5)
    - "LABEL+5^ROUTINE" → (label="LABEL", routine="ROUTINE", offset=5)
    """
    label: Optional[str] = None
    routine: Optional[str] = None
    offset: Optional[int] = None
```

---

## Runtime Extensions

### MUMPSRuntime Additions

Extend existing `MUMPSRuntime` class in [runtime/__init__.py](../../src/m2py/runtime/__init__.py).

```python
class MUMPSRuntime:
    # Existing fields...
    
    # New fields for indirection support
    _exec_cache: Dict[str, types.CodeType] = field(default_factory=dict)
    
    # New methods
    def get_var(self, name: str, _scope: Dict[str, Any]) -> Any:
        """Get variable by dynamic name (name indirection read).
        
        Args:
            name: Variable name (may include subscripts, may start with ^)
            _scope: Current scope dictionary
            
        Returns:
            Variable value, or empty string if undefined
            
        Raises:
            IndirectionError: If name is invalid
        """
        ...
    
    def set_var(self, name: str, value: Any, _scope: Dict[str, Any]) -> None:
        """Set variable by dynamic name (name indirection write).
        
        Args:
            name: Variable name (may include subscripts, may start with ^)
            value: Value to set
            _scope: Current scope dictionary
            
        Raises:
            IndirectionError: If name is invalid
        """
        ...
    
    def resolve_indirection(self, expr: str, levels: int, _scope: Dict[str, Any]) -> str:
        """Resolve N levels of name indirection.
        
        For @@X: expr="X", levels=2
        For @@@X: expr="X", levels=3
        
        Args:
            expr: Initial variable name
            levels: Number of @ levels to resolve
            _scope: Current scope dictionary
            
        Returns:
            Final resolved variable name or value
        """
        ...
    
    def execute(self, mumps_code: str, _scope: Dict[str, Any]) -> Any:
        """Execute MUMPS code string at runtime (XECUTE command).
        
        Uses existing m2py pipeline: parse → ASG → Python → exec()
        
        Args:
            mumps_code: MUMPS code to execute (single line or multiple)
            _scope: Scope dictionary for variable access
            
        Returns:
            Return value if code contains QUIT with value, else None
            
        Raises:
            SyntaxError: If MUMPS code has syntax errors
            IndirectionError: If indirection within code fails
            Exception: Any error from executed code
        """
        ...
    
    def parse_call_target(self, target_str: str) -> CallTarget:
        """Parse indirect DO/GOTO target string.
        
        Args:
            target_str: Target like "LABEL", "^ROUTINE", "LABEL+5^ROUTINE"
            
        Returns:
            CallTarget with parsed components
            
        Raises:
            IndirectionError: If target format is invalid
        """
        ...
    
    def compile_pattern_indirect(self, pattern_str: str) -> str:
        """Compile MUMPS pattern string to regex at runtime.
        
        Args:
            pattern_str: MUMPS pattern like "1N.N" or "1A.A"
            
        Returns:
            Compiled regex pattern string
            
        Raises:
            IndirectionError: If pattern is invalid
        """
        ...
```

---

## State Transitions

### Indirection Resolution Flow

```
┌─────────────────┐
│ @X encountered  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Get value of X  │
│ from _scope     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     Yes    ┌─────────────────┐
│ Is @@X (multi)? │───────────▶│ Recursively     │
└────────┬────────┘            │ resolve value   │
         │ No                  └────────┬────────┘
         │                              │
         ▼                              ▼
┌─────────────────┐            ┌─────────────────┐
│ Use resolved    │◀───────────│ Get value of    │
│ name for access │            │ resolved name   │
└─────────────────┘            └─────────────────┘
```

### XECUTE Execution Flow

```
┌─────────────────┐
│ XECUTE expr     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     Yes    ┌─────────────────┐
│ Is constant?    │───────────▶│ Use pre-inlined │
│ (compile-time)  │            │ Python code     │
└────────┬────────┘            └────────┬────────┘
         │ No                           │
         ▼                              │
┌─────────────────┐                     │
│ Evaluate expr   │                     │
│ to get code str │                     │
└────────┬────────┘                     │
         │                              │
         ▼                              │
┌─────────────────┐                     │
│ Parse MUMPS     │                     │
│ code string     │                     │
└────────┬────────┘                     │
         │                              │
         ▼                              │
┌─────────────────┐                     │
│ Generate Python │                     │
│ via m2py        │                     │
└────────┬────────┘                     │
         │                              │
         ▼                              │
┌─────────────────┐                     │
│ exec() with     │◀────────────────────┘
│ _scope context  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Continue after  │
│ XECUTE          │
└─────────────────┘
```

---

## Validation Rules

### Variable Name Validation

```python
def is_valid_varname(name: str) -> bool:
    """Check if name is valid MUMPS variable name.
    
    Valid names:
    - Start with letter or %
    - Contain letters, digits
    - Can be global (^prefix)
    - Can have subscripts (name(sub1,sub2))
    
    Examples:
        "X" → True
        "VAR" → True  
        "%ZOS" → True
        "^GLOBAL" → True
        "A(1,2)" → True
        "123" → False (starts with digit)
        "X Y" → False (contains space)
    """
    ...
```

### Call Target Validation

```python
def is_valid_call_target(target: str) -> bool:
    """Check if target is valid for indirect DO/GOTO.
    
    Valid targets:
    - "LABEL"
    - "^ROUTINE"
    - "LABEL^ROUTINE"
    - "LABEL+N" (N is integer)
    - "LABEL+N^ROUTINE"
    
    Invalid:
    - Empty string
    - Just "+"
    - Invalid label/routine names
    """
    ...
```

---

## Relationships

```
MIndirection ─────────────┐
    │                     │
    │ expression          │ indirection_type
    ▼                     ▼
  MExpr              IndirectionType
                          │
                          │ NAME → get_var()
                          │ SUBSCRIPT → normal eval
                          │ ARGUMENT → parse_call_target()
                          │ PATTERN → compile_pattern_indirect()
                          ▼
                    MUMPSRuntime

MXecuteStatement ─────────┐
    │                     │
    │ code_expressions    │ is_constant
    ▼                     ▼
  List[MExpr]        bool
    │                     │
    │                     │ True → inline generated Python
    │                     │ False → runtime.execute()
    ▼                     ▼
  evaluate ──────────▶ MUMPSRuntime.execute()
```

---

## References

- [research.md](research.md) - Decision rationale
- [expressions.py](../../src/m2py/asg/expressions.py) - MIndirection definition
- [statements.py](../../src/m2py/asg/statements.py) - MXecuteStatement definition
- [runtime/__init__.py](../../src/m2py/runtime/__init__.py) - MUMPSRuntime class
