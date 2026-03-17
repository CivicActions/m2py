# Module Contract: ZWR Import/Export

**Module**: `m2py.runtime.zwr`  
**Location**: `src/m2py/runtime/zwr.py`  
**Used by**: m2py CLI (`m2py globals import/export`), vista-test fixtures (Tier 3+ global bootstrap)

## Summary

ZWR (ZWRITE) is the standard MUMPS global interchange format. This module provides parsing, serialization, and bulk import/export of ZWR data into any `GlobalStorageBackend`. It lives in m2py (not vista-test) because it's a general-purpose capability.

## Public Interface

### `parse_zwr_line(line: str) -> tuple[str, list[str], str]`

Parse a single ZWR-format line into components.

**Parameters**:
- `line`: A ZWR line like `^GLOBAL("sub1","sub2")="value"`

**Returns**: Tuple of `(global_name, subscripts, value)`.

**Behavior**:
1. Extract global name (e.g., `^DD`)
2. Parse subscripts — handles quoted strings, `$C()` escapes, numeric subscripts
3. Extract value — handles quoted strings with embedded quotes (`""`)
4. Raises `ValueError` for malformed lines

### `parse_zwr_stream(stream: TextIO) -> Iterator[tuple[str, list[str], str]]`

Iterate parsed ZWR entries from a file or stream.

**Parameters**:
- `stream`: File-like text object with ZWR-format lines

**Returns**: Iterator of `(global_name, subscripts, value)` tuples.

**Behavior**:
- Skips blank lines and comment lines (starting with `;`)
- Yields one tuple per valid ZWR line
- Raises `ValueError` on malformed lines (fail-fast, no silent skipping)

### `serialize_zwr_node(global_name: str, subscripts: list[str], value: str) -> str`

Produce a single ZWR-format line.

**Parameters**:
- `global_name`: Global name with caret (e.g., `^DD`)
- `subscripts`: List of subscript strings
- `value`: The node value

**Returns**: ZWR-format string like `^DD("sub")="value"`.

**Behavior**:
- Properly quotes string subscripts (wraps in `""`, doubles internal quotes)
- Numeric subscripts are unquoted
- Value is always quoted with proper escaping

### `import_zwr(backend: GlobalStorageBackend, source: Path | TextIO) -> int`

Import ZWR data into a global storage backend.

**Parameters**:
- `backend`: Any `GlobalStorageBackend` implementation (MDict, SQLite, YottaDB, IRIS)
- `source`: Path to a ZWR file, or an open text stream

**Returns**: Number of nodes imported.

**Behavior**:
1. Open file if `source` is a `Path`
2. Parse each ZWR line via `parse_zwr_stream()`
3. Store each node into `backend` using the appropriate set operation
4. Return total count of nodes stored

### `export_zwr(backend: GlobalStorageBackend, global_names: list[str], dest: Path | TextIO) -> int`

Export globals from a backend to ZWR format.

**Parameters**:
- `backend`: Source `GlobalStorageBackend`
- `global_names`: List of global names to export (e.g., `["^DD", "^DIC"]`)
- `dest`: Path to write ZWR output, or an open text stream

**Returns**: Number of nodes exported.

**Behavior**:
1. For each global, traverse all nodes via `$ORDER` equivalent
2. Serialize each node via `serialize_zwr_node()`
3. Write to destination (one line per node)
4. Return total count of nodes written

## CLI Integration

**Location**: `src/m2py/cli/globals.py`

```
m2py globals import <file.zwr> [--backend <type>]
m2py globals export <file.zwr> [--globals '^DD,^DIC'] [--backend <type>]
```

## Dependencies

- `m2py.runtime.globals.GlobalStorageBackend` — target storage protocol
- Standard library: `pathlib`, `re`, `typing`

## Vista-Test Integration

Vista-test fixtures consume this module for Tier 3+ test data loading:

```python
# vista-test/tests/vista/munit/conftest.py

@pytest.fixture(scope="session")
def fileman_bootstrap(munit_runtime):
    """Bootstrap FileMan globals (Tier 3)."""
    from m2py.runtime.zwr import import_zwr
    zwr_path = Path("baselines/globals/fileman.zwr")
    import_zwr(munit_runtime.globals, zwr_path)
    return munit_runtime

@pytest.fixture(scope="session")
def clinical_bootstrap(fileman_bootstrap):
    """Bootstrap clinical globals (Tier 4) — depends on FileMan."""
    from m2py.runtime.zwr import import_zwr
    for zwr_file in Path("baselines/globals").glob("clinical_*.zwr"):
        import_zwr(fileman_bootstrap.globals, zwr_file)
    return fileman_bootstrap
```

## Test Contract

```python
# m2py root: tests/test_zwr.py

def test_parse_zwr_line_simple():
    """Parse simple ZWR line with string subscript."""
    name, subs, val = parse_zwr_line('^DD(2,0)="PATIENT"')
    assert name == "^DD"
    assert subs == ["2", "0"]
    assert val == "PATIENT"

def test_parse_zwr_line_quoted():
    """Parse ZWR line with embedded quotes in value."""
    name, subs, val = parse_zwr_line('^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30 X"')
    assert name == "^DD"
    assert val == 'NAME^RF^^0;1^K:$L(X)>30 X'

def test_round_trip():
    """serialize → parse round-trip preserves data."""
    original = ("^DD", ["2", "0"], "PATIENT")
    line = serialize_zwr_node(*original)
    result = parse_zwr_line(line)
    assert result == original

def test_import_export_round_trip(tmp_path):
    """import → export round-trip with MDict backend."""
    from m2py.runtime.globals import MDict
    backend = MDict()
    zwr_file = tmp_path / "test.zwr"
    zwr_file.write_text('^DD(2,0)="PATIENT"\n^DD(2,.01,0)="NAME"\n')
    count = import_zwr(backend, zwr_file)
    assert count == 2
    out_file = tmp_path / "out.zwr"
    export_zwr(backend, ["^DD"], out_file)
    assert out_file.read_text().strip().count("\n") == 1  # 2 lines
```
