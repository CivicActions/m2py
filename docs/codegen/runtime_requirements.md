# Runtime Requirements

When static Python generation is insufficient.

## Overview

Some MUMPS features cannot be translated to static Python and require runtime support:

- Dynamic variable access (indirection)
- Dynamic code execution (XECUTE)
- Naked global references
- Cross-routine calls
- Some intrinsic functions

## Detection Flags

The analysis pipeline sets flags indicating runtime requirements:

| Flag | Location | Meaning |
|------|----------|---------|
| `requires_runtime_eval` | MRoutine | Any unresolvable indirection |
| `requires_runtime_scope` | FunctionSignature | Scope cannot be statically determined |
| `call_type == INDIRECT_CALL` | MCall | Target is dynamic |
| `is_constant == False` | MXecuteStatement | XECUTE code is dynamic |

## Indirection

### Resolvable (Static)

```mumps
S NAME="X"    ; Constant assignment
W @NAME       ; Can resolve to X at compile time
```

Generate static Python if the value is known.

### Unresolvable (Dynamic)

```mumps
R NAME
W @NAME       ; Don't know NAME at compile time
```

**Runtime Variable Access:**
```python
from m2py.runtime import MUMPSRuntime

# MUMPSRuntime provides output capture and code execution
rt = MUMPSRuntime()

# Current API for output capture
rt.write("Hello")      # Capture WRITE output
output = rt.get_output()  # Get accumulated output
rt.clear()             # Clear output buffer

# Execute generated Python code
result = rt.execute(python_code, entry_point="MAIN")
print(result.output)   # Captured WRITE output
print(result.success)  # True if no exception
```

**Format Control Methods:**
```python
# Tab to column (0-indexed per YDB semantics)
rt.write_tab(10)       # Move to column 10 (pad with spaces if needed)
```

**Special Variable Accessors:**
```python
# Intrinsic Special Variables (ISVs)
rt.horolog()           # $HOROLOG - "days,seconds" since epoch
rt.job()               # $JOB - process ID
rt.io()                # $IO - current I/O device
rt.x()                 # $X - cursor column position
rt.y()                 # $Y - cursor row position
rt.stack_level()       # $STACK - call stack depth
rt.quit_flag()         # Check if routine should exit
```

**Stack Frame Management:**
```python
rt.push_frame()        # Enter new scope (increments $STACK)
rt.pop_frame()         # Exit scope (decrements $STACK)
```

**Note**: Dynamic variable access via `runtime.get_var()` / `runtime.set_indirected()` 
is used for indirection and global variables. Local variables use 
`_scope.setdefault('name', MArray()).value` for reliable MArray semantics.

## XECUTE Command

### Constant Code

```mumps
X "S X=1"     ; Known at compile time
```

Can inline the code directly:
```python
# Conceptual Python equivalent

x = 1
```

### Dynamic Code

```mumps
R CMD
X CMD         ; Unknown code
```

**Runtime Execution:**
```python
# Conceptual Python equivalent

def execute_mumps(runtime, code_string):
    """Parse and execute MUMPS code at runtime."""
    # Parse the code string
    # Execute in current context
    pass

# Generated code
execute_mumps(runtime, input())
```

## Naked Global References

Naked globals use the last global reference:

```mumps
S ^A(1,2)=1   ; Sets last global context
S ^(3)=2      ; Actually ^A(1,3)
```

**Runtime Tracking:**

Global variable storage uses the `GlobalStorageBackend` protocol with `InMemoryGlobalStorage` as the default implementation:

```python
from m2py.runtime import MUMPSRuntime, get_global_storage

# MUMPSRuntime provides access to global storage
rt = MUMPSRuntime()

# Set global variable: ^A(1,2)=1
rt.globals.set("A", ("1", "2"), "1")

# Naked reference: ^(3)=2 -> ^A(1,3)=2
# The naked indicator is updated after each global access
name, subs = rt.globals.resolve_naked(("3",))
rt.globals.set(name, subs, "2")

# Get value
value = rt.globals.get("A", ("1", "3"))  # Returns "2"

# $DATA function
data_code = rt.globals.data("A", ("1",))  # Returns 10, 1, 11, or 0

# Backend selection via environment variable
# M2PY_GLOBAL_BACKEND=inmemory (default)
# M2PY_GLOBAL_BACKEND=yottadb (requires yottadb package)
# M2PY_GLOBAL_BACKEND=iris (requires iris package)
storage = get_global_storage()  # Uses M2PY_GLOBAL_BACKEND env var
```

**Naked Indicator Semantics:**

- After `^G(1,2,3)`: naked indicator = `("G", ("1", "2"))`, so `^(4)` = `^G(1,2,4)`
- After `^G(1)`: naked indicator = `("G", ())`, so `^(2)` = `^G(2)`
- After `^G` (no subscripts): naked indicator is cleared, naked refs are illegal

## External Routine Calls

Calls to other routines require:

1. Loading the other routine
2. Calling the specified label
3. Sharing variable scope

```mumps
D UTIL^LIBRARY
```

**Module System:**
```python
# Conceptual Python equivalent

# library.py (generated from LIBRARY.m)
def util():
    ...

# current.py
import library
library.util()
```

**Module Caching:**

Python's standard `sys.modules` dictionary automatically caches imported modules. Multiple imports of the same routine use the cached module instance:

```python
# First import loads and caches the module
import ext2
ext2.helper()

# Subsequent imports use cached version from sys.modules
import ext2  # No reload - uses cached module
ext2.other_label()
```

Benefits:
- No custom caching mechanism needed
- Standard Python import semantics apply
- Module initialization runs only once
- Shared state across all references

The transpiler generates standard `import` statements rather than dynamic imports (importlib) to ensure proper caching behavior.

**Or with runtime:**
```python
# Conceptual Python equivalent

runtime.call_external("LIBRARY", "UTIL")
```

## $TEXT Function

Returns source code lines - requires original source:

```mumps
S X=$T(+1)    ; First line of routine
```

**Runtime Access:**
```python
# Conceptual Python equivalent

class MUMPSRuntime:
    def __init__(self):
        self.source_lines = {}  # routine -> list of lines
    
    def load_routine(self, name, lines):
        self.source_lines[name] = lines
    
    def text(self, routine, offset):
        return self.source_lines.get(routine, [])[offset]
```

The `MRoutine.source_lines` field stores the original source for this purpose.

## Exclusive NEW

```mumps
N (A,B)       ; NEW all except A and B
```

Cannot enumerate all variables at compile time:
```python
# Conceptual Python equivalent

def exclusive_new(runtime, except_list):
    """Save all current variables except those in except_list."""
    saved = {}
    for name, value in runtime.variables.items():
        if name not in except_list:
            saved[name] = value
            del runtime.variables[name]
    return saved

def restore_scope(runtime, saved):
    """Restore saved variables."""
    runtime.variables.update(saved)
```

## Argumentless KILL

```mumps
K             ; Kill all local variables
```

Similar to exclusive NEW - cannot enumerate:
```python
# Conceptual Python equivalent

def kill_all(runtime):
    runtime.variables.clear()
```

## MArray: Local Subscripted Variables

MUMPS local variables can be subscripted arrays with unique semantics:
- Each node can have BOTH a value AND children
- Undefined access returns empty string `""`
- Numeric and string subscripts follow collation order

```mumps
S A=1          ; Root value
S A(1)=2       ; Child (1) has value
S A(1,2)=3     ; Grandchild (1,2) has value
W A,A(1),A(1,2)  ; Outputs: 123
```

The `MArray` class provides these semantics for generated Python:

```python
from m2py.runtime import MArray

# Create array variable
A = MArray()
A.value = 1            # Root value: S A=1
A[1] = 2               # S A(1)=2
A[1, 2] = 3            # S A(1,2)=3

# Access
A.get()                # → 1 (W A)
A.get(1)               # → 2 (W A(1))
A.get(1, 2)            # → 3 (W A(1,2))
A.get(9)               # → "" (undefined returns empty string)
```

### $DATA Semantics

```python
A.defined()            # → 11 (has value AND children)
A.defined(1)           # → 11 (has value AND children)
A.defined(1, 2)        # → 1  (has value only)
A.defined(9)           # → 0  (undefined)
```

| Return | Meaning |
|--------|---------|
| 0 | Undefined |
| 1 | Has value only |
| 10 | Has children only |
| 11 | Has value AND children |

### KILL Command

```python
A.kill(1)              # K A(1) - removes node and all descendants
A.kill()               # K A - clears entire array
```

## LHS Function Helpers

MUMPS allows functions on the left-hand side of SET to modify portions of variables in-place:

```mumps
S $P(X,"^",2)="NEW"    ; Replace second piece of X
S $E(X,2,3)="AB"       ; Replace characters 2-3 of X
```

The `m2py.runtime.helpers` module provides helper functions for these operations:

### m_set_piece (LHS $PIECE)

```python
from m2py.runtime.helpers import m_set_piece

# S X="A^B^C" S $P(X,"^",2)="NEW" → X="A^NEW^C"
m_set_piece(
    lambda: _scope.get('X', ''),     # getter
    lambda v: _scope.__setitem__('X', v),  # setter
    "^",                              # delimiter
    2,                                # piece_from (1-indexed)
    None,                             # piece_to (None = single piece)
    "NEW"                             # replacement value
)
```

**Behavior:**
- Replaces piece(s) at position piece_from (to piece_to if specified)
- Pads with empty pieces/delimiters if needed: `$P(Y,"^",3)="C"` → `"^^C"`
- Range replacement collapses pieces: `$P(X,"^",2,4)="X"` replaces pieces 2-4

**Generated Code Example:**
```python
# For: S X="A^B^C" S $P(X,"^",2)="NEW" W X Q
_scope['X'] = "A^B^C"
m_set_piece(lambda: _scope.get('X', ''), lambda v: _scope.__setitem__('X', v), "^", 2, None, "NEW")
_rt.write(_scope.get('X', ''))
```

### m_set_extract (LHS $EXTRACT)

```python
from m2py.runtime.helpers import m_set_extract

# S X="HELLO" S $E(X,2,3)="XX" → X="HXXLO"
m_set_extract(
    lambda: _scope.get('X', ''),     # getter
    lambda v: _scope.__setitem__('X', v),  # setter
    2,                                # from_pos (1-indexed)
    3,                                # to_pos (1-indexed, inclusive)
    "XX"                              # replacement value
)
```

**Behavior:**
- Replaces characters at positions from_pos to to_pos (inclusive)
- Pads with spaces if needed: `$E(X,5)="Y"` on `"AB"` → `"AB  Y"`
- Replacement can be shorter or longer than the range
- Single position: `$E(X,2)="A"` replaces only character at position 2

**Generated Code Example:**
```python
# For: S X="HELLO" S $E(X,2,3)="XX" W X Q
_scope['X'] = "HELLO"
m_set_extract(lambda: _scope.get('X', ''), lambda v: _scope.__setitem__('X', v), 2, 3, "XX")
_rt.write(_scope.get('X', ''))
```

### m_format_output (Numeric Formatting)

```python
from m2py.runtime.helpers import m_format_output

# Convert values to MUMPS canonical format for output
m_format_output(1.0)    # → "1"
m_format_output(0.5)    # → ".5"
m_format_output(-0.5)   # → "-.5"
m_format_output(3.14)   # → "3.14"
```

**Behavior:**
- Integers formatted without trailing `.0`: `1.0` → `"1"`
- Leading zero removed for decimals < 1: `0.5` → `".5"`
- Negative values preserve sign: `-0.5` → `"-.5"`
- Non-numeric values converted with `str()`
- Decimal values expanded without scientific notation: `1E+11` → `"100000000000"`
- Extreme negative exponents (< -43) return `"0"` matching YDB precision limits

This function is used internally by `MUMPSRuntime.write()` and ZWRITE formatting to ensure numeric output matches MUMPS formatting conventions.

### $ORDER Traversal

```python
A["alpha"] = 1
A["beta"] = 2  
A["gamma"] = 3

A.order("")            # → "alpha" (first subscript)
A.order("alpha")       # → "beta" (next subscript)
A.order("gamma")       # → "" (past end)
```

Numbers sort before strings in MUMPS collation.

### Use in Cross-Label Control Flow

When subscripted variables flow across label boundaries (cross-label GOTOs), they are represented as MArray fields in RoutineState:

```python
@dataclass
class RoutineState:
    X: Any = None                             # Simple variable
    A: MArray = field(default_factory=MArray) # Subscripted variable
```

See `src/m2py/codegen/shared_state.py` for RoutineState generation.

## Error Handling

MUMPS $ETRAP/$ECODE error handling is implemented with try/except wrappers at
MUMPS stack frame boundaries.

### Setting Up Error Handlers

```mumps
S $ECODE=""
S $ETRAP="S $ECODE="""" W ""Handled"",!"
```

Generated Python uses `_rt.set_etrap()` and `_rt.set_ecode()`:
```python
_rt.set_etrap('S $ECODE="" W "Handled",!')
_rt.set_ecode("")
```

### Runtime Error Handling Methods

```python
class MUMPSRuntime:
    def _exception_to_ecode(self, exc: Exception) -> str:
        """Map Python exception to MUMPS $ECODE format.
        
        Returns comma-delimited format: ",Mnn," or ",Zxxx,"
        Examples:
        - ZeroDivisionError → ",M9,"
        - KeyError → ",M6,"
        - MRuntimeError("SELECTFALSE") → ",M4,"
        """
        ...
    
    def _handle_etrap(self, exc: Exception, _scope: dict) -> bool:
        """Handle exception using $ETRAP if set.
        
        Returns True if error was handled ($ECODE cleared),
        False if error should propagate.
        """
        if not self._etrap:
            return False  # No handler, propagate
        
        self._ecode = self._exception_to_ecode(exc)
        self._zerror = str(exc)
        self.execute_mumps(self._etrap, _scope)
        
        return self._ecode == ""  # True if handler cleared $ECODE
```

### Generated Code Pattern

Simple functions are wrapped in try/except:
```python
def SUB(_rt, _scope=None, **_kwargs):
    global _test
    _scope = _scope if _scope is not None else {}
    try:
        # Function body...
        _rt.write("In SUB")
        return
    except Exception as _e:
        if _rt._handle_etrap(_e, _scope):
            return  # $ETRAP cleared $ECODE, implicit QUIT
        raise  # Propagate to caller
```

Trampoline dispatchers wrap the loop:
```python
def TEST(_rt, _scope=None):
    """Trampoline dispatcher for routine execution."""
    _scope = _scope if _scope is not None else {}
    state = RoutineState()
    target: str | int | None = "TEST"

    while target is not None:
        try:
            func = _labels[target]
            target, state = func(_rt, state, _scope)
        except Exception as _e:
            if _rt._handle_etrap(_e, _scope):
                return state  # $ETRAP cleared $ECODE, implicit QUIT
            raise  # Propagate to caller

    return state
```

### Error Code Mapping

| Python Exception | MUMPS $ECODE | Description |
|-----------------|--------------|-------------|
| `ZeroDivisionError` | `,M9,` | Divide by zero |
| `KeyError` | `,M6,` | Undefined local variable |
| `MRuntimeError("SELECTFALSE")` | `,M4,` | No $SELECT argument true |
| `MRuntimeError("RANDARGNEG")` | `,M28,` | $RANDOM argument negative |
| `IndirectionError` | `,M26,` | Non-existent environment |
| `LabelNotFoundError` | `,M13,` | Label not found |
| Other | `,Z150373210,` | Generic system error |

## Runtime Library Structure

```python
# Conceptual Python equivalent

# mumps_runtime.py

class MUMPSRuntime:
    def __init__(self):
        self.variables = {}           # Local variables
        self.globals = {}             # Global variables
        self.last_global = None       # For naked references
        self.test = 0                 # $TEST
        self.routines = {}            # Loaded routines
        self.call_stack = []          # For scope management
    
    # Variable access
    def get_local(self, name): ...
    def set_local(self, name, value): ...
    def get_global(self, name, *subs): ...
    def set_global(self, name, value, *subs): ...
    
    # Indirection
    def resolve_name(self, expr): ...
    def eval_indirection(self, expr): ...
    
    # Control flow
    def call_external(self, routine, label, *args): ...
    def execute(self, code): ...
    
    # Scope
    def push_scope(self): ...
    def pop_scope(self): ...
    def new_var(self, name): ...
    def exclusive_new(self, except_list): ...
```

## Code Generation Strategy

```python
# Conceptual Python equivalent

def generate_routine(routine):
    if routine.requires_runtime_eval:
        return generate_with_runtime(routine)
    
    # Check individual labels
    for label in routine.labels:
        if label.signature.requires_runtime_scope:
            # This label needs runtime
            pass
        else:
            # Can generate static Python
            pass
```

## Performance Considerations

Runtime support is slower than static Python:
- Dictionary lookups vs direct variables
- String parsing for indirection
- Additional function call overhead

Prefer static generation when possible:
1. Resolve constant indirection at compile time
2. Inline constant XECUTE
3. Use static imports for known external calls
