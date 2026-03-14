# Routine Overrides

The override mechanism allows specific MUMPS routines to be replaced with native Python implementations at import time. This provides two benefits:

1. **Performance** — bypass line-by-line transpiled execution for hot code paths
2. **Correctness** — implement complex FileMan APIs directly in Python when the transpiler can't yet handle the full complexity

## How It Works

```
import DIC          ← MumpsAutoImporter intercepts
     │
     ▼
overrides/DIC.py    ← Found? Load native Python override
     │ (miss)
     ▼
VistA-M/DIC.m       ← Transpile .m → .py as usual
```

The `MumpsAutoImporter` (in `tests/functional/munit/conftest.py`) checks an `overrides/` directory before transpiling `.m` source. If a matching `.py` file exists, it's loaded directly via `load_override()` from `src/m2py/runtime/overrides.py`.

## Directory Layout

```
overrides/
├── README.md       # Convention documentation
├── DIC.py          # FIND^DIC and LIST^DIC (FileMan lookup APIs)
└── ...             # Future overrides
```

Override files are named exactly as the MUMPS routine (`DIC.py` for `DIC.m`). Files starting with `_` are ignored.

## Module Protocol

Override modules must be importable as drop-in replacements for transpiled code. The minimum interface:

```python
_routine_name = "DIC"            # MUMPS routine name

def FIND(_rt, *args, _scope=None, **kwargs):
    """Native implementation of FIND^DIC."""
    ...

def LIST(_rt, *args, _scope=None, **kwargs):
    """Native implementation of LIST^DIC."""
    ...
```

Every label function receives `(_rt, *args, _scope=None, **kwargs)` where `_rt` is the `MUMPSRuntime` instance and positional args correspond to the MUMPS call's actual parameters.

## Partial Overrides

Most overrides only replace a few entry points while delegating the rest to the transpiled base. The `partial_override()` helper supports this:

```python
from m2py.runtime.overrides import partial_override

_base = partial_override("DIC")   # Load transpiled DIC.m
_routine_name = "DIC"

def FIND(_rt, *args, _scope=None, **kwargs):
    """Override only FIND^DIC."""
    ...

def __getattr__(name):
    """Delegate everything else to transpiled base."""
    return getattr(_base, name)
```

With this pattern:
- `D FIND^DIC(...)` → calls the native `FIND()` above
- `D ^DIC` → falls through to `_base._entry_function` (the classic lookup)
- `_label_lines`, `_line_map`, `_source_lines` → all resolve from `_base`

The transpiled base is registered under a private `sys.modules` key (`_m2py_base_DIC`) so it doesn't shadow the override.

## Runtime API Reference

### `partial_override(routine_name: str) → ModuleType`

Loads the transpiled version of a routine for use as a delegation base. Uses duck-typed `get_source_path()` on `sys.meta_path` finders to locate the `.m` source.

### `load_override(py_path: Path, routine_name: str) → ModuleType`

Compiles and executes a `.py` override file, registering it in `sys.modules` under both the MUMPS name and the Python module name (handling `%`-prefix → `_pct_` translation).

Both functions live in `src/m2py/runtime/overrides.py`.

## Accessing Globals

Override code interacts with the global store through `_rt.globals`:

```python
g = _rt.globals
j = str(_rt.job())  # $J for ^TMP subscripts

# Read a global node
value = g.get("DMU", ("1009.802", ien, "0"))   # ^DMU(1009.802,ien,0)

# Write a global node
g.set("TMP", ("DILIST", j, "2", "1"), ien)     # ^TMP("DILIST",$J,2,1)=ien

# Walk an index ($ORDER)
key = g.order("DMU", ("1009.802", "B", prev_key))

# Check existence ($DATA)
d = g.data("DMU", ("1009.802", ien))

# Delete subtree (KILL)
g.kill("TMP", ("DILIST", j))
```

All subscripts and values are strings (MUMPS convention). The `GlobalStorageBackend` protocol is defined in `src/m2py/runtime/globals.py`.

## Existing Overrides

### `DIC.py` — FIND^DIC and LIST^DIC

Native implementations of FileMan's two primary database-server lookup APIs. These are the performance-critical entry points that caused DMUDIC00 test timeouts (>18,000s) when run through the transpiler.

**FIND^DIC** walks the B-index matching a prefix value, extracts requested fields (including computed fields like `COUNT(COUNTY)`), validates field types (pointer targets, dates, set-of-codes), and writes results to `^TMP("DILIST",$J,...)`.

**LIST^DIC** lists all entries from the B-index. With the `X` flag, supports:
- Sorting by unindexed fields (e.g., sort by CAPITAL)
- Screening by computed expressions (e.g., `COUNT(COUNTY)>100`)
- Sort templates from `^DIBT` (multi-level sort with direction and filters)

**Flags supported**: `E` (error tolerance — return entries even with bad data), `X` (enable unindexed sorting and computed expression evaluation).

**Performance**: DMUDIC00 completes in ~10s with the override vs >18,000s timeout without — approximately 1,800× speedup.

## Writing a New Override

1. **Create** `overrides/<ROUTINE>.py`
2. **Use** `partial_override()` if you only need to replace some labels
3. **Implement** label functions with the `(_rt, *args, _scope=None, **kwargs)` signature
4. **Coerce** all args to `str` — the transpiler may pass `int`, `Decimal`, or `MArray` values
5. **Test** by running the relevant munit tests with `-m slow`
6. **Verify** no regressions with `uv run pytest tests/`

For `%`-prefix routines, name the file `_pct_<NAME>.py` (e.g., `_pct_DT.py` for `%DT`).
