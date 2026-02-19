# Module Contract: global_bootstrap

**Module**: `vista_test.munit.bootstrap`  
**Location**: `vista-test/src/vista_test/munit/bootstrap.py`  
**Used by**: Tier 3+ test fixtures (Phase D onward)

## Public Interface

### `class GlobalBootstrap`

```python
class GlobalBootstrap:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 2222,
        username: str = "vehuprog",
        password: str = "prog",
        cache_dir: Path = Path("baselines/globals"),
    ): ...
```

Exports globals from VEHU Docker and imports them into the m2py global store.

### `export_globals(self, global_names: list[str], output_path: Path) -> Path`

Export specified globals from VEHU in ZWR format.

**Parameters**:
- `global_names`: List of global names to export (e.g., `["^DD", "^DIC", "^%ZOSF"]`)
- `output_path`: Path to write the ZWR export file

**Returns**: Path to the exported file.

**Behavior**:
1. Connect to VEHU via SSH
2. For each global, use `%GO` (Global Output) or `$ORDER` traversal to export in ZWR format
3. Write combined output to `output_path`
4. Cache locally so subsequent runs skip the export

### `import_globals(self, zwr_path: Path, runtime: MUMPSRuntime) -> int`

Import ZWR-format globals into the m2py runtime's global store.

**Parameters**:
- `zwr_path`: Path to a ZWR export file
- `runtime`: MUMPSRuntime instance whose global store receives the data

**Returns**: Number of globals imported.

**Behavior**:
1. Parse ZWR format: `^GLOBAL(subscripts)=value`
2. Import each entry into `runtime.globals` (MDict)
3. Return count of entries imported

### `bootstrap_tier(self, tier: int, runtime: MUMPSRuntime) -> None`

Convenience method: export and import all globals needed for a specific tier.

**Parameters**:
- `tier`: Tier number (3, 4)
- `runtime`: Target MUMPSRuntime

**Behavior**:
- Tier 3: exports `^DD`, `^DIC`, `^%ZOSF`
- Tier 4: exports Tier 3 + `^DPT`, `^SC`, `^AUPNPROB`, `^GMPL*`, `^SD*`, `^DG*`

### pytest Fixture

```python
# vista-test/tests/vista/munit/conftest.py

@pytest.fixture(scope="session")
def fileman_bootstrap(munit_runtime):
    """Bootstrap FileMan globals (Tier 3)."""
    bootstrap = GlobalBootstrap()
    bootstrap.bootstrap_tier(3, munit_runtime)
    return munit_runtime

@pytest.fixture(scope="session")
def clinical_bootstrap(fileman_bootstrap):
    """Bootstrap clinical globals (Tier 4) — depends on FileMan."""
    bootstrap = GlobalBootstrap()
    bootstrap.bootstrap_tier(4, fileman_bootstrap)
    return fileman_bootstrap
```

## Dependencies

- `vista_test.terminal.session.VistATerminal` — SSH connection to VEHU
- `m2py.runtime.MUMPSRuntime` — target global store
- `paramiko` — SSH transport (via VistATerminal)
- Standard library: `pathlib`, `re`

## Test Contract

```python
# Integration tests: tests/integration/test_bootstrap.py
# Mark with @pytest.mark.smoke (requires live VEHU)

def test_export_dd_global(vehu_bootstrap, tmp_path):
    """Can export ^DD global from VEHU in ZWR format."""
    path = vehu_bootstrap.export_globals(["^DD"], tmp_path / "dd.zwr")
    assert path.exists()
    assert path.stat().st_size > 0
    # Verify ZWR format
    first_line = path.read_text().split("\n")[0]
    assert first_line.startswith("^DD(")

def test_import_zwr_into_runtime(munit_runtime, zwr_fixture):
    """Can import ZWR data into MUMPSRuntime global store."""
    bootstrap = GlobalBootstrap()
    count = bootstrap.import_globals(zwr_fixture, munit_runtime)
    assert count > 0
    # Verify data accessible via MDict
    assert munit_runtime.globals["DD"]["0"] is not None

def test_bootstrap_caches_exports(vehu_bootstrap, tmp_path):
    """Second export uses cached file, not SSH."""
    # First export
    vehu_bootstrap.export_globals(["^DD"], tmp_path / "dd.zwr")
    # Second export should be fast (cached)
    import time
    start = time.time()
    vehu_bootstrap.export_globals(["^DD"], tmp_path / "dd.zwr")
    assert time.time() - start < 1.0  # cached, no SSH
```
