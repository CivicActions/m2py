# Data Model: External Calls & Cross-Routine Infrastructure

**Spec**: 008-external-calls  
**Date**: 2025-01-12

## Overview

This document defines the data structures for cross-routine coordination: shared variable scope, source line storage, and external GOTO exception. Module loading uses standard Python `import` statements (no custom loader needed).

## Entity Definitions

### 1. Source Lines (per module)

**Purpose**: Store original source lines for $TEXT function in each generated module.

**Location**: Module-level constant in each generated `.py` file

```python
# In generated ext2.py:
_source_lines = [
    "ext2 ; Entry point",
    " W \"Hello\",!",
    " Q",
    "HELPER ; Helper label",
    " W \"In helper\",!",
    " Q",
]
_routine_name = "ext2"
```

**Invariants**:
- Lines preserve original content (no normalization)
- 0-indexed list (MUMPS $TEXT(+1) accesses index 0)
- $TEXT(+0) returns `_routine_name`, not `_source_lines[0]`
- Every generated module has `_source_lines`, `_routine_name`, and `_label_lines`

---

### 1b. Label-to-Line Index

**Purpose**: Map label names to their line indices for `$TEXT(LABEL^ROUTINE)` support.

**Location**: Module-level constant in each generated `.py` file

```python
# In generated ext2.py:
_label_lines = {
    "ext2": 0,     # Entry label at line 1 (index 0)
    "HELPER": 3,   # HELPER label at line 4 (index 3)
}
```

**Generation Logic** (from ASG at transpile time):
```python
# In codegen, MLabel.line_number is available from parser
# Generate: label_name -> (line_number - 1) to convert to 0-indexed
_label_lines = {label.name: label.line_number - 1 for label in routine.labels}
```

**Invariants**:
- Keys are label names exactly as they appear in source (case-sensitive)
- Values are 0-indexed (subtract 1 from MUMPS 1-based line numbers)
- Entry label (first label) is always present
- Used only for $TEXT; normal calls use function names directly

---

### 2. Shared Scope

**Purpose**: MUMPS variable storage visible across routine boundaries.

**Location**: Passed as parameter to all generated functions.

```python
# Type: Dict[str, Any]
# Key: Variable name (after name translation)
# Value: Variable value (can be MArray for subscripted)

_scope: Dict[str, Any] = {}
```

**Invariants**:
- All routines share same scope dictionary reference
- NEW creates save/restore pattern, does not create new dict
- Undefined variable access returns empty string ""

---

### 3. Module Search Paths

**Purpose**: Directories to search for pre-transpiled `.py` routine modules.

**Location**: Standard Python `sys.path`

```python
# Configured at execution entry point (not in generated code):
import sys
sys.path.insert(0, "/path/to/vista/routines")

# Or via environment:
# PYTHONPATH=/path/to/routines python main.py
```

**Invariants**:
- Uses standard Python import mechanism
- No custom search path configuration in runtime
- ImportError raised if module not found (standard Python behavior)

---

### 4. GotoExternal Exception

**Purpose**: Signal external GOTO for stack unwinding.

**Location**: `src/m2py/runtime/__init__.py`

```python
class GotoExternal(Exception):
    """Raised to transfer control to external routine (no return)."""
    
    module: types.ModuleType  # Target module (already imported)
    label: Optional[str]      # Target label (None = entry label)
    offset: Optional[int]     # Optional line offset
    
    def __init__(self, module: types.ModuleType, label: str = None, offset: int = None):
        self.module = module
        self.label = label
        self.offset = offset
        routine_name = getattr(module, '_routine_name', module.__name__)
        super().__init__(f"GOTO {label or ''}^{routine_name}")
```

**Invariants**:
- Module is never None (import happens before raise)
- Label can be None (means entry label)
- Offset requires label to be set

**Note**: RoutineNotFoundError is no longer needed - Python's standard `ImportError` is raised if the module doesn't exist.

---

### 5. LabelNotFoundError

**Purpose**: Raised when label doesn't exist in loaded routine.

```python
class LabelNotFoundError(Exception):
    """Raised when label not found in routine."""
    
    label: str
    routine: str
    available_labels: List[str]
    
    def __init__(self, label: str, routine: str, available: List[str]):
        self.label = label
        self.routine = routine
        self.available_labels = available
        super().__init__(f"Label '{label}' not found in routine '{routine}'")
```

---

## Runtime Method Signatures

### MUMPSRuntime Extensions

```python
class MUMPSRuntime:
    """Extended for Spec 008 external call support."""
    
    # Existing fields
    _output: List[str]
    _test: bool
    
    # New fields for Spec 008
    _current_routine: Optional[str]           # Routine name for $TEXT(+0)
    _current_source_lines: Optional[List[str]] # Source lines for $TEXT(+N) in current routine
    _current_label_lines: Optional[Dict[str, int]]  # Label->line index for $TEXT(LABEL+N)
    
    def get_text(
        self,
        offset: int,
        label: str = None,
        module: types.ModuleType = None
    ) -> str:
        """
        Get source text line ($TEXT function).
        
        Args:
            offset: Line offset (0 = routine name, 1+ = source line)
            label: Optional label for label+offset (looks up label's line index first)
            module: Module containing _source_lines (None = current routine's module)
            
        Returns:
            Source line text or empty string if past end or invalid
        """
        if offset == 0 and label is None:
            return module._routine_name if module else self._current_routine
        
        # Get source lines and label map from module or current context
        lines = module._source_lines if module else self._current_source_lines
        label_lines = module._label_lines if module else self._current_label_lines
        
        # Calculate actual line index
        if label:
            base_idx = label_lines.get(label, -1)
            if base_idx < 0:
                return ""  # Label not found
            line_idx = base_idx + offset
        else:
            line_idx = offset - 1  # Convert 1-based offset to 0-based index
        
        # Bounds check and return
        if 0 <= line_idx < len(lines):
            return lines[line_idx]
        return ""
```

**Note**: Most external call functionality is now handled by generated `import` statements and direct function calls - no runtime methods needed for DO, GOTO, or extrinsics.
```

---

## Generated Code Patterns

### External DO Call

```python
# MUMPS: D ^ext2
import ext2
ext2.ext2(_rt, _scope)  # Entry label has same name as routine (VistA convention)

# MUMPS: D HELPER^ext2
import ext2
ext2.HELPER(_rt, _scope)

# MUMPS: D HELPER^ext2(X,Y)
import ext2
ext2.HELPER(_rt, _scope, X, Y)

# MUMPS: D HELPER+2^ext2 - label+offset (uses line dispatch)
import ext2
_target_line = ext2._label_lines["HELPER"] + 2  # 0-indexed line number
ext2._line_map[_target_line](_rt, _scope)  # Call via line dispatch map

# MUMPS: D +5^ext2 - absolute line offset (uses line dispatch)
import ext2
ext2._line_map[4](_rt, _scope)  # Line 5 = index 4 (0-indexed)
```

### External GOTO

```python
# MUMPS: G ^ext2
import ext2
raise GotoExternal(ext2, None)  # Module ref + no label = entry

# MUMPS: G LABEL^ext2
import ext2
raise GotoExternal(ext2, "LABEL")

# MUMPS: G LABEL+2^ext2 - label+offset (uses line dispatch at target)
import ext2
raise GotoExternal(ext2, "LABEL", offset=2)

# MUMPS: G +5^ext2 - absolute line offset
import ext2
raise GotoExternal(ext2, None, offset=5)  # No label, just line number
```

### External Extrinsic

```python
# MUMPS: S X=$$ADD^ext2(3,5)
import ext2
_saved_test = _rt._test
try:
    X = ext2.ADD(_rt, _scope, 3, 5)
finally:
    _rt._test = _saved_test
```

### $TEXT Function

```python
# MUMPS: $T(+1) - current routine
_source_lines[0] if len(_source_lines) >= 1 else ""

# MUMPS: $T(+0) - routine name
_routine_name

# MUMPS: $T(LABEL+2) - label+offset in current routine
# First get label's line index, then add offset
_idx = _label_lines.get("LABEL", -1)
_source_lines[_idx + 2] if _idx >= 0 and _idx + 2 < len(_source_lines) else ""

# MUMPS: $T(+1^ext2) - external routine
import ext2
ext2._source_lines[0] if len(ext2._source_lines) >= 1 else ""

# MUMPS: $T(LABEL^ext2) - external routine label (offset 0 = label line itself)
import ext2
ext2._source_lines[ext2._label_lines["LABEL"]] if "LABEL" in ext2._label_lines else ""

# MUMPS: $T(LABEL+2^ext2) - external routine label+offset
import ext2
_idx = ext2._label_lines.get("LABEL", -1)
ext2._source_lines[_idx + 2] if _idx >= 0 and _idx + 2 < len(ext2._source_lines) else ""
```

### Variable Storage in _scope

MUMPS variables are stored in the shared `_scope` dictionary to enable cross-routine visibility:

```python
# MUMPS: S X=42 - Store variable
_scope['X'] = 42

# MUMPS: W X - Read variable (returns empty string if undefined)
_rt.write(_scope.get('X', ''))

# MUMPS: S X=Y+1 - Read and write
_scope['X'] = _scope.get('Y', '') + 1

# Function entry: copy formal parameters to _scope
def MYLABEL(_rt, _scope=None, N=None, **_kwargs):
    _scope = _scope if _scope is not None else {}
    _scope['N'] = N  # Formal param accessible in _scope
    ...

# By-reference returns: return from _scope
def INCR(_rt, _scope=None, N=None, **_kwargs):
    _scope = _scope if _scope is not None else {}
    _scope['N'] = N
    _scope['N'] = _scope.get('N', '') + 1
    return _scope.get('N', '')

# By-reference call sites: assign result back to _scope
_scope['X'] = INCR(_rt, N=_scope.get('X', ''), _scope=_scope)
```

**Key invariants**:
- All variable storage uses `_scope['varname']` for SIMPLE_FUNCTIONS strategy
- All variable reads use `_scope.get('varname', '')` for undefined safety
- Formal parameters are copied to `_scope` at function entry
- By-reference parameters return from and assign to `_scope`
- Cross-routine visibility is automatic since all routines share the same `_scope` dict

---

## State Transitions

### Module Import Flow (Python Standard)

```
1. Generated code contains: import ext2
2. Python checks sys.modules for "ext2"
   - If cached: returns cached module instantly
   - If not: proceeds to import
3. Python searches sys.path for ext2.py
   - If not found: raises ImportError
4. Python executes ext2.py, caches in sys.modules
5. Generated code calls ext2.LABEL(_rt, _scope)
```

### GOTO Exception Flow

```
1. Generated code: raise GotoExternal(ext2, "LABEL")
2. Exception propagates up call stack (unwinding FOR loops, etc.)
3. Caught by top-level trampoline/dispatcher
4. Dispatcher extracts module and label from exception
5. Dispatcher calls ext2.LABEL(_rt, _scope)
6. Normal execution continues in ext2
```

### $TEXT Access Flow

```
1. Generated code: import ext2; ext2._source_lines[n]
2. Module already cached in sys.modules (from import)
3. Direct attribute access - no runtime call needed
4. Returns source line or empty string if out of bounds
```

---

## Entry Point and Context Initialization

### Top-Level Entry Point

The main entry point (e.g., generated `if __name__ == "__main__":` block or test harness) initializes shared context:

```python
# In generated main.py or test harness:
from m2py.runtime import MUMPSRuntime

_rt = MUMPSRuntime()
_scope = {}  # Shared variable scope for all routines

# Set current routine context for $TEXT in this routine
_rt._current_routine = _routine_name
_rt._current_source_lines = _source_lines  
_rt._current_label_lines = _label_lines

# Call entry point
main(_rt, _scope)
```

### Routine Entry Context Update

When control transfers to a different routine (via DO or GOTO), the `_current_*` fields must be updated:

```python
# Generated at start of each routine's entry function (or by dispatcher):
def ext2(_rt, _scope):
    # Update context so $TEXT references this routine
    _rt._current_routine = _routine_name
    _rt._current_source_lines = _source_lines
    _rt._current_label_lines = _label_lines
    # ... rest of routine body ...
```

### Trampoline Dispatcher for External GOTO

The top-level dispatcher catches `GotoExternal` and transfers control:

```python
# Extended from Spec 006 trampoline pattern
def run_with_goto_support(entry_module, entry_label, _rt, _scope):
    """Execute entry point, handling cross-routine GOTO."""
    current_module = entry_module
    current_label = entry_label
    current_offset = None
    
    while True:
        try:
            # Update context for $TEXT
            _rt._current_routine = current_module._routine_name
            _rt._current_source_lines = current_module._source_lines
            _rt._current_label_lines = current_module._label_lines
            
            # Dispatch to target
            if current_offset is not None:
                # Line-based dispatch (G LABEL+N or G +N)
                if current_label:
                    line_idx = current_module._label_lines[current_label] + current_offset
                else:
                    line_idx = current_offset - 1  # Convert 1-based to 0-based
                current_module._line_map[line_idx](_rt, _scope)
            elif current_label:
                # Label-based dispatch
                getattr(current_module, current_label)(_rt, _scope)
            else:
                # Entry label (first label, same name as module)
                entry_func = getattr(current_module, current_module._routine_name)
                entry_func(_rt, _scope)
            
            return  # Normal completion
            
        except GotoExternal as goto:
            # Transfer to new target, loop continues
            current_module = goto.module
            current_label = goto.label
            current_offset = goto.offset
```
