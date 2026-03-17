# Routine Overrides

This directory contains native Python implementations that replace
transpiled MUMPS routines. When the `MumpsAutoImporter` encounters a
module name that has a matching `.py` file here, it loads the override
**instead of** transpiling the `.m` source.

## How It Works

1. Place a `<ROUTINE>.py` file in this directory (e.g. `DIC.py`).
2. The auto-importer finds it during `import DIC` and loads it directly.
3. All callers (`D FIND^DIC(...)`, etc.) use the native implementation.

## Module Protocol

Override modules must provide the same attributes that transpiled code does:

```python
_routine_name = "DIC"           # MUMPS routine name
_source_lines = []              # Empty for overrides (no .m source)
_label_lines = {"FIND": 0, ...} # Label → line number mapping
_line_map = {}                  # Line → (label, offset) for +N dispatch

def FIND(_rt, *args, _scope=None, **kwargs):
    """Native implementation of FIND^DIC."""
    ...

_entry_function = FIND          # Default entry point
```

## Partial Overrides

To override only specific entry points and delegate the rest to the
transpiled version:

```python
from m2py.runtime.overrides import partial_override

# Load transpiled base for non-overridden labels
_base = partial_override("DIC")

# Inherit base protocol
_routine_name = _base._routine_name
_source_lines = _base._source_lines
_label_lines = _base._label_lines
_line_map = _base._line_map
_entry_function = _base._entry_function

# Override specific entry points
def FIND(_rt, *args, _scope=None, **kwargs):
    """Optimized FIND^DIC."""
    ...

# Delegate everything else to transpiled version
def __getattr__(name):
    return getattr(_base, name)
```

## File Naming

- Files must be named exactly as the MUMPS routine: `DIC.py`, `DICF.py`, etc.
- Files starting with `_` are ignored (e.g. `__init__.py`).
- For `%`-prefix routines, use `_pct_` prefix: `_pct_DT.py` for `%DT`.

## Long-Term Vision

These overrides serve dual purpose:

1. **Short-term**: Performance optimization — replace hot transpiled code
   with efficient native Python while m2py itself is being improved.
2. **Long-term**: Clean rewrites — gradually replace transpiled code with
   well-structured Python. When a rewrite is complete, the `.m` source
   is no longer needed for that routine.
