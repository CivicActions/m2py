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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
class MUMPSRuntime:
    def __init__(self):
        self.variables = {}
    
    def get_var(self, name):
        return self.variables.get(name, "")
    
    def set_var(self, name, value):
        self.variables[name] = value
    
    def resolve_indirection(self, expr):
        """Parse and evaluate variable reference at runtime."""
        # Parse "A(1,2)" into name and subscripts
        # Return the value
        pass

# Generated code
runtime = MUMPSRuntime()
runtime.set_var(runtime.get_var("NAME"), value)  # @NAME=value
```

## XECUTE Command

### Constant Code

```mumps
X "S X=1"     ; Known at compile time
```

Can inline the code directly:
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
x = 1
```

### Dynamic Code

```mumps
R CMD
X CMD         ; Unknown code
```

**Runtime Execution:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
class MUMPSRuntime:
    def __init__(self):
        self.last_global_name = ""
        self.last_global_subs = []
    
    def set_global(self, name, subscripts, value):
        self.last_global_name = name
        self.last_global_subs = subscripts[:-1]  # All but last
        # Actually store value
    
    def set_naked(self, subscripts, value):
        # Use last_global_name with combined subscripts
        full_subs = self.last_global_subs + subscripts
        self.set_global(self.last_global_name, full_subs, value)
```

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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
# library.py (generated from LIBRARY.m)
def util():
    ...

# current.py
import library
library.util()
```

**Or with runtime:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
runtime.call_external("LIBRARY", "UTIL")
```

## $TEXT Function

Returns source code lines - requires original source:

```mumps
S X=$T(+1)    ; First line of routine
```

**Runtime Access:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
def kill_all(runtime):
    runtime.variables.clear()
```

## Error Handling

```mumps
S $ECODE=""
S $ETRAP="G ERROR^HANDLER"
```

Requires runtime error handling infrastructure:
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
class MUMPSRuntime:
    def __init__(self):
        self.ecode = ""
        self.etrap = ""
    
    def handle_error(self, error):
        self.ecode = error.code
        if self.etrap:
            self.execute(self.etrap)
```

## Runtime Library Structure

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
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
