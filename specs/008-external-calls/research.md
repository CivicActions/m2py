# Research: External Calls & Cross-Routine Infrastructure

**Spec**: 008-external-calls  
**Date**: 2025-01-12

## Research Questions

### 1. How should Python modules be loaded at runtime?

**Decision**: Use regular Python `import` statements (generated at transpile time)

**Rationale**: 
- Routine names are known at transpile time (`D ^ext2` → `import ext2`)
- Python's import system handles caching automatically
- No custom module loader needed - simpler generated code
- Circular imports handled by Python (lazy binding)
- Search paths = `sys.path` (standard mechanism)

**Alternatives Rejected**:
- `importlib.util.spec_from_file_location()` - Overkill since we pre-transpile
- `exec(compile(...))` - Too low-level, no proper module semantics
- Custom loader class - Unnecessary complexity

**Implementation Pattern**:
```python
# Generated code for: D HELPER^ext2
import ext2
ext2.HELPER(_rt, _scope)

# Generated code for: G ^ext2  
import ext2
raise GotoExternal(ext2, "ext2")  # Module reference for trampoline

# Generated code for: S X=$$ADD^ext2(3,5)
import ext2
X = ext2.ADD(_rt, _scope, 3, 5)
```

---

### 2. How should shared variable scope work across routine boundaries?

**Decision**: Pass a shared `scope` dictionary to all routine functions

**Rationale**:
- MUMPS variables are visible across routine boundaries by default
- A shared dictionary makes scope explicit and testable
- Supports NEW semantics by saving/restoring dictionary entries
- Aligns with existing `GeneratorContext.state_vars` pattern

**Alternatives Considered**:
- Python globals - Pollutes global namespace, hard to test
- Thread-local storage - Overcomplicates for single-threaded use case
- Class instance variables - Would require refactoring all generated code

**Pattern for Generated Code**:
```python
# At top-level entry point (main.py or test harness):
_rt = MUMPSRuntime()
_scope = {}  # Shared scope - created ONCE at entry point

# In caller routine
_scope['X'] = 100
ext2_module.EXT2(_rt, _scope)  # Pass scope to external routine
print(_scope['X'])  # See modifications from callee

# In callee routine (ext2.py)
def EXT2(_rt, _scope):
    _scope['X'] = 999  # Visible to caller
```

**Key point**: `_scope` is created once at the top-level entry point and passed through all calls. It is never re-created - all routines share the same dictionary instance.

**Pattern for NEW**:
```python
def LABEL(_rt, _scope):
    _saved = {}
    if 'X' in _scope:
        _saved['X'] = _scope['X']
        del _scope['X']
    try:
        _scope['X'] = 999  # New local X
        # ... body ...
    finally:
        del _scope['X']
        if 'X' in _saved:
            _scope['X'] = _saved['X']
```

---

### 3. How should $TEXT access source lines?

**Decision**: Store source lines as module-level constant in each generated `.py` file

**Rationale**:
- `MRoutine.source_lines` already populated by parser (Spec 007)
- Each module self-contained: `_source_lines` and `_label_lines` embedded
- Standard import gives access: `import ext2; ext2._source_lines[n]`
- No runtime registry needed - Python's `sys.modules` handles caching

**Implementation Pattern**:
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
_label_lines = {"ext2": 0, "HELPER": 3}  # Label name -> index in _source_lines
```

**For $TEXT(+0)**:
- YDB returns the routine name, not empty
- Access via `_routine_name` constant

---

### 4. How should external GOTO differ from external DO?

**Decision**: 
- External DO: Call function and return to caller after QUIT
- External GOTO: Transfer control permanently (no return)
- **Cross-routine GOTO allowed** (YDB-permissive, not strict MDC)

**Rationale**: Matches MUMPS semantics exactly. GOTO terminates all FOR loops and doesn't create a stack frame for return.

**MDC Reference Deviation (8.2.6)**:
Strict MDC states GOTO source and target "must be in the same routine" (otherwise M45 error). However:
- YottaDB allows cross-routine GOTO
- VistA contains **11,474 cross-routine GOTOs** across **3,177 files**
- Strict compliance would break the primary target codebase

**Decision**: Use YDB-permissive behavior. Document as intentional deviation per Constitution II (YDB as reference).

**Implementation Pattern**:
```python
# External DO - returns after callee QUITs
def EXT1(_rt, _scope):
    ext2.HELPER(_rt, _scope)  # Call and return
    _rt.write("Back")  # This executes after HELPER QUITs

# External GOTO - raise exception to unwind stack
class GotoExternal(Exception):
    def __init__(self, module: types.ModuleType, label: str = None):
        self.module = module  # Already-imported module reference
        self.label = label

def EXT1(_rt, _scope):
    import ext2
    raise GotoExternal(ext2, "HELPER")  # Module ref, not string
```

The trampoline dispatcher catches `GotoExternal` and transfers to the target module.

---

### 5. How should module caching work?

**Decision**: Rely on Python's built-in import caching (`sys.modules`)

**Rationale**:
- Python already caches imported modules in `sys.modules`
- No custom caching code needed
- Import statement is idempotent - second `import ext2` is a no-op
- Reduces runtime surface area per Constitution VII

**Implementation**:
```python
# No runtime code needed!
# Python handles this automatically:
import ext2  # First call: loads module, caches in sys.modules
import ext2  # Second call: returns cached module instantly
```

---

### 6. How should search paths be configured?

**Decision**: Use Python's standard `sys.path` mechanism

**Rationale**:
- VistA directories added to `sys.path` before execution
- Test fixtures configure `sys.path` in pytest fixtures
- Standard Python pattern - no custom infrastructure
- Works with PYTHONPATH environment variable

**Implementation**:
```python
# At execution entry point (not in generated code):
import sys
sys.path.insert(0, "/path/to/vista/routines")
sys.path.insert(0, "/path/to/more/routines")

# Or via environment:
# PYTHONPATH=/path/to/vista/routines:/path/to/more/routines python main.py
```

---

## Technical Decisions Summary

| Question | Decision | Key Reason |
|----------|----------|------------|
| Module loading | Regular `import` | Routine names known at transpile time; Python handles caching |
| Shared scope | Pass dictionary | Explicit, testable, supports NEW |
| $TEXT | `_source_lines` in module | Each module embeds its source; access via `ext2._source_lines` |
| DO vs GOTO | GOTO raises exception | Unwinds stack correctly |
| Caching | Python's `sys.modules` | Built-in, no custom code needed |
| Search paths | `sys.path` | Standard Python mechanism |

## Edge Cases Resolved

1. **Circular calls (A→B→A)**: Python's import system handles this naturally since we create in-memory modules
2. **Missing routine**: Python raises standard `ImportError` (no custom exception needed)
3. **Missing label**: Raise `LabelNotFoundError` with routine and label names
4. **$TEXT past end**: Return empty string (YDB behavior verified)
5. **$TEXT(+0)**: Return routine name (YDB behavior verified)
6. **Cross-routine GOTO**: Allowed per YDB behavior (MDC 8.2.6 intentionally relaxed)

---

## MDC Reference Validation

| MDC Section | Topic | Spec Alignment |
|-------------|-------|----------------|
| 8.2.3 (DO) | External calls, parameter passing | ✅ Matches |
| 8.2.6 (GOTO) | LEVEL restrictions, same-routine | ⚠️ **Intentionally deviated** for YDB/VistA compatibility |
| 7.1.5.20 ($TEXT) | +0 returns routinename, M5 for negative | ✅ Matches |
| 8.1.7 | Parameter passing semantics | ✅ Matches |
