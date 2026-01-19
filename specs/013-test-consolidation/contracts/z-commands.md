# Z-Commands Contract

**Spec**: 013-test-consolidation  
**Scope**: Z-commands with VistA usage (FR-039 through FR-045)

## Overview

All 7 Z-commands with VistA usage require full implementation (no stubs).

| Z-Command | VistA Files | Priority |
|-----------|-------------|----------|
| ZWRITE | 54 | High |
| ZLINK | 20 | Medium |
| ZSHOW | 9 | Medium |
| ZKILL | 5 | High (protocol exists) |
| ZGOTO | 2 | Low (complex) |
| ZHALT | 1 | Low |
| $ZERROR | 121 | High |

---

## ZWRITE Command (FR-039)

**MUMPS**: `ZWRITE variable` or `ZWRITE`

**Behavior**:
- Displays variable(s) with their subscript structure
- Argumentless ZWRITE shows all local variables
- Shows both value and array structure

**Output Format**:
```
ZWRITE X
X="value"
X(1)="sub1"
X(1,2)="sub2"
```

**Examples**:
```mumps
S X=1,X(1)="A",X(2)="B"
ZW X
; Output:
; X=1
; X(1)="A"
; X(2)="B"
```

**Python Implementation**:
```python
def _zwrite(var_name: str | None = None, scope: dict = None) -> None:
    if var_name is None:
        # All local variables
        for name in sorted(scope.keys()):
            _zwrite_var(name, scope[name])
    else:
        _zwrite_var(var_name, scope.get(var_name, ''))

def _zwrite_var(name: str, value) -> None:
    if isinstance(value, MArray):
        if value._value is not None:
            print(f'{name}={_quote(value._value)}')
        for sub, child in sorted(value._children.items()):
            _zwrite_var(f'{name}({_quote(sub)})', child)
    else:
        print(f'{name}={_quote(value)}')
```

---

## ZLINK Command (FR-040)

**MUMPS**: `ZLINK routinename`

**Behavior**:
- Dynamically links/loads a routine
- Makes routine available for execution
- In transpiler context: imports Python module

**Examples**:
```mumps
ZLINK "MYROUTINE"
D ^MYROUTINE
```

**Python Implementation**:
```python
def _zlink(routine_name: str) -> None:
    import importlib
    # Assumes transpiled routines are Python modules
    module = importlib.import_module(routine_name.lower())
    # Register in routine registry
    _rt._routines[routine_name] = module
```

**Notes**:
- Requires routine search path configuration
- May need to handle .m source files (transpile on demand)

---

## ZSHOW Command (FR-041)

**MUMPS**: `ZSHOW info_type`

**Behavior**:
- Displays system information based on type code
- Common codes: "D" (devices), "S" (stack), "V" (variables)

**Examples**:
```mumps
ZSHOW "S"    ; Show call stack
ZSHOW "V"    ; Show variables (like ZWRITE)
```

**Python Implementation**:
```python
def _zshow(info_type: str) -> None:
    if info_type == "S":
        import traceback
        traceback.print_stack()
    elif info_type == "V":
        _zwrite()  # Same as argumentless ZWRITE
    elif info_type == "D":
        # Device information
        print(f"$IO={_rt._io}")
        print(f"$PRINCIPAL={_rt._principal}")
    # ... other info types
```

---

## ZKILL Command (FR-042)

**MUMPS**: `ZKILL variable` or `ZWITHDRAW variable`

**Behavior**:
- Kills node value but preserves descendants
- Unlike KILL which removes entire subtree

**Examples**:
```mumps
S ^A=1,^A(1)=2,^A(2)=3
ZKILL ^A           ; Removes ^A value, keeps ^A(1) and ^A(2)
W $D(^A)           ; 10 (has descendants but no value)
```

**Python Implementation**:
Already in protocol as `kill_node()`:
```python
def kill_node(self, name: str, subscripts: tuple[str, ...]) -> None:
    """Kill only the value at node, preserving descendants."""
    # Navigate to node
    # Set node._value = None
    # Keep node._children intact
```

---

## ZGOTO Command (FR-043)

**MUMPS**: `ZGOTO level:label` or `ZGOTO level`

**Behavior**:
- Unwinds stack to specified level
- Optionally transfers control to label
- Level 0 exits program

**Examples**:
```mumps
ZGOTO 0            ; Exit program
ZGOTO 1:ERROR      ; Unwind to level 1, go to ERROR
```

**Complexity**: This requires TRAMPOLINE-like infrastructure for stack unwinding.

**Python Implementation Options**:

1. **Exception-based**:
```python
class ZGotoException(Exception):
    def __init__(self, level: int, label: str | None = None):
        self.level = level
        self.label = label

def _zgoto(level: int, label: str | None = None) -> None:
    raise ZGotoException(level, label)
```

2. **Requires wrapper in all functions**:
```python
def LABEL(_rt, _scope=None, **_kwargs):
    try:
        # ... function body ...
    except ZGotoException as e:
        if e.level == current_level:
            if e.label:
                return _dispatch_label(e.label, _rt, _scope)
            return
        raise  # Propagate to higher level
```

---

## ZHALT Command (FR-044)

**MUMPS**: `ZHALT status`

**Behavior**:
- Terminates process with exit status
- Similar to HALT but with explicit status code

**Examples**:
```mumps
ZHALT 0     ; Exit with success
ZHALT 1     ; Exit with error
```

**Python Implementation**:
```python
def _zhalt(status: int = 0) -> None:
    import sys
    sys.exit(status)
```

---

## $ZERROR Special Variable (FR-045)

**MUMPS**: `$ZERROR` (read-only)

**Behavior**:
- Contains YDB-specific error information
- Set when error occurs
- More detailed than standard $ECODE

**Format**: `error-code,error-message,error-location`

**Examples**:
```mumps
; After error:
W $ZE    ; "150372994,UNDEF,%YDB-E-UNDEF, Undefined local variable: X"
```

**Python Implementation**:
```python
class MUMPSRuntime:
    def __init__(self):
        self._zerror = ""
    
    def set_error(self, code: int, message: str, location: str = ""):
        self._zerror = f"{code},{message},{location}"
    
    @property
    def zerror(self) -> str:
        return self._zerror
```

**Error Mapping**: Map Python exceptions to YDB-style error codes.
