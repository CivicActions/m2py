# Runtime API Contract: Indirection & XECUTE

**Date**: 2026-01-16  
**Spec**: [../spec.md](../spec.md)

## Overview

This document defines the runtime API contract for indirection and XECUTE support.

---

## Indirection API

### get_var

Read variable by dynamic name (name indirection).

```python
def get_var(self, name: str, _scope: Dict[str, Any]) -> Any:
    """
    Get variable value by name.
    
    Behavior:
    - Local variables: Look up in _scope dict
    - Global variables (^prefix): Use global storage
    - Undefined variables: Return empty string ""
    - Invalid names: Raise IndirectionError
    
    Args:
        name: Variable name, optionally with subscripts
              Examples: "X", "ARR(1,2)", "^GLO", "^GLO(1)"
        _scope: Current scope dictionary
        
    Returns:
        str | int | float: Variable value
        "": If undefined
        
    Raises:
        IndirectionError: If name is not a valid variable name
        
    Examples:
        >>> rt.get_var("X", {"X": 5})
        5
        >>> rt.get_var("UNDEF", {})
        ""
        >>> rt.get_var("^GLO", {})  # Global lookup
        42
    """
```

### set_var

Write variable by dynamic name (name indirection).

```python
def set_var(self, name: str, value: Any, _scope: Dict[str, Any]) -> None:
    """
    Set variable value by name.
    
    Behavior:
    - Local variables: Store in _scope dict
    - Global variables (^prefix): Use global storage
    - Creates variable if doesn't exist
    - Invalid names: Raise IndirectionError
    
    Args:
        name: Variable name, optionally with subscripts
        value: Value to set
        _scope: Current scope dictionary
        
    Raises:
        IndirectionError: If name is not a valid variable name
        
    Examples:
        >>> scope = {}
        >>> rt.set_var("X", 5, scope)
        >>> scope["X"]
        5
    """
```

### resolve_indirection

Resolve multi-level indirection.

```python
def resolve_indirection(
    self, 
    expr: str, 
    levels: int, 
    _scope: Dict[str, Any]
) -> str:
    """
    Resolve N levels of name indirection.
    
    For @@X: resolve X once, then use that value as variable name
    For @@@X: resolve X twice
    
    Args:
        expr: Initial variable name to start resolving
        levels: Number of indirection levels (1 for @, 2 for @@, etc.)
        _scope: Current scope dictionary
        
    Returns:
        str: Final resolved value
        
    Raises:
        IndirectionError: If any resolution step fails
        
    Examples:
        >>> scope = {"A": "B", "B": "C", "C": 100}
        >>> rt.resolve_indirection("A", 1, scope)  # @A
        "B"
        >>> rt.resolve_indirection("A", 2, scope)  # @@A
        "C"
        >>> rt.resolve_indirection("A", 3, scope)  # @@@A
        100
    """
```

---

## XECUTE API

### execute

Execute MUMPS code string at runtime.

```python
def execute(
    self, 
    mumps_code: str, 
    _scope: Dict[str, Any]
) -> Any:
    """
    Execute MUMPS code string using m2py pipeline.
    
    Behavior:
    - Parses code as MUMPS
    - Generates Python via m2py codegen
    - Executes with exec() in _scope context
    - $TEST is NOT stacked (mutations visible to caller)
    - Supports all MUMPS constructs (depends on Specs 004-011)
    
    Args:
        mumps_code: MUMPS code to execute (one or more commands)
        _scope: Scope dictionary shared with caller
        
    Returns:
        Any: Return value if code contains QUIT with value
        None: If code ends without return value
        
    Raises:
        SyntaxError: If MUMPS code has parse errors
        Any exception from executed code
        
    Examples:
        >>> scope = {}
        >>> rt.execute("S X=1", scope)
        >>> scope["X"]
        1
        
        >>> scope = {"Y": 5}
        >>> rt.execute("S X=Y+1", scope)
        >>> scope["X"]
        6
        
        >>> rt.execute("W 42,!", scope)
        # Outputs: 42 and newline
    """
```

---

## Indirect Call API

### parse_call_target

Parse indirect DO/GOTO target string.

```python
def parse_call_target(self, target_str: str) -> CallTarget:
    """
    Parse indirect call target into components.
    
    Formats supported:
    - "LABEL" → local label
    - "^ROUTINE" → entry label of external routine
    - "LABEL^ROUTINE" → specific label in external routine
    - "LABEL+N" → label with offset (N is integer)
    - "LABEL+N^ROUTINE" → external with offset
    
    Args:
        target_str: Target string from indirection resolution
        
    Returns:
        CallTarget(label, routine, offset)
        
    Raises:
        IndirectionError: If format is invalid
        
    Examples:
        >>> rt.parse_call_target("LABEL")
        CallTarget(label="LABEL", routine=None, offset=None)
        
        >>> rt.parse_call_target("LABEL^ROUTINE")
        CallTarget(label="LABEL", routine="ROUTINE", offset=None)
        
        >>> rt.parse_call_target("LABEL+5^ROUTINE")
        CallTarget(label="LABEL", routine="ROUTINE", offset=5)
    """
```

---

## Pattern Indirection API

### compile_pattern_indirect

Compile MUMPS pattern at runtime.

```python
def compile_pattern_indirect(self, pattern_str: str) -> str:
    """
    Compile MUMPS pattern string to regex.
    
    Uses existing pattern compiler from analysis/pattern_compiler.py
    
    Args:
        pattern_str: MUMPS pattern like "1N.N", "1A.A"
        
    Returns:
        str: Regex pattern string for matching
        
    Raises:
        IndirectionError: If pattern is invalid
        
    Examples:
        >>> rt.compile_pattern_indirect("1N.N")
        "^[0-9][0-9]*$"  # (actual regex varies)
        
        >>> rt.compile_pattern_indirect("1A.A")
        "^[A-Za-z][A-Za-z]*$"
    """
```

---

## Error Handling

### IndirectionError

Exception for indirection failures.

```python
class IndirectionError(Exception):
    """
    Raised when indirection fails at runtime.
    
    Attributes:
        expression: The indirection expression (for error message)
        reason: Why it failed
        variable_name: Variable involved (optional)
        variable_value: Value found (optional)
        
    Error conditions:
    - Invalid variable name format
    - Undefined variable in multi-level indirection
    - Invalid call target format
    - Invalid pattern string
    
    Examples:
        IndirectionError("123VAR", "invalid variable name - cannot start with digit")
        IndirectionError("UNDEF", "undefined variable in indirection chain", 
                        variable_name="X", variable_value="UNDEF")
    """
```

---

## Codegen Contracts

### Name Indirection (Read)

Generated Python for `W @X`:

```python
# Input: W @X
# Output:
_rt.write(_rt.get_var(_scope.get("X", ""), _scope))
```

### Name Indirection (Write)

Generated Python for `S @X=1`:

```python
# Input: S @X=1
# Output:
_rt.set_var(_scope.get("X", ""), 1, _scope)
```

### Multi-Level Indirection

Generated Python for `W @@X`:

```python
# Input: W @@X
# Output:
_rt.write(_rt.resolve_indirection("X", 2, _scope))
```

### XECUTE (Constant)

Generated Python for `X "S X=1"` (constant string):

```python
# Input: X "S X=1"
# Output (inlined):
_scope["X"] = 1
```

### XECUTE (Dynamic)

Generated Python for `X CODE` (variable):

```python
# Input: X CODE
# Output:
_rt.execute(_scope.get("CODE", ""), _scope)
```

### Indirect DO

Generated Python for `D @CMD`:

```python
# Input: D @CMD
# Output:
_target = _rt.parse_call_target(_scope.get("CMD", ""))
_rt.indirect_do(_target, _scope)
```

### Pattern Indirection

Generated Python for `I X?@PAT`:

```python
# Input: I X?@PAT
# Output:
import re
_pattern = _rt.compile_pattern_indirect(_scope.get("PAT", ""))
_rt._test = 1 if re.match(_pattern, str(_scope.get("X", ""))) else 0
```

---

## Testing Contract

Each API method must have:
1. Unit tests with valid inputs
2. Unit tests with edge cases (empty strings, special characters)
3. Unit tests for error conditions (invalid names, undefined variables)
4. Integration tests matching MUGJ test patterns

### Required Test Coverage

| Method | Test Class | Location |
|--------|------------|----------|
| `get_var` | `TestGetVar` | test_indirection.py |
| `set_var` | `TestSetVar` | test_indirection.py |
| `resolve_indirection` | `TestResolveIndirection` | test_indirection.py |
| `execute` | `TestExecute` | test_s8_2_26_xecute.py |
| `parse_call_target` | `TestParseCallTarget` | test_indirection.py |
| `compile_pattern_indirect` | `TestPatternIndirection` | test_indirection.py |
