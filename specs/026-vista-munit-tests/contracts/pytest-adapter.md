# Module Contract: pytest M-Unit Adapter

**Module**: `vista_test.munit.adapter`  
**Location**: `vista-test/src/vista_test/munit/adapter.py`  
**Plugin entry point**: `vista-test/tests/vista/munit/conftest.py`  
**Used by**: pytest discovery and execution (Phase 0b)

## Public Interface

### `class MUnitTestItem(pytest.Item)`

Custom pytest item representing one M-Unit test routine.

```python
class MUnitTestItem(pytest.Item):
    def __init__(
        self,
        name: str,                      # e.g. "test_munit_utt1" 
        parent: pytest.Collector,
        config: TestRoutineConfig,       # Routine configuration
        baseline: MUnitResult | None,    # VEHU baseline result (if available)
    ): ...

    def runtest(self) -> None:
        """Transpile, execute, parse, and compare to baseline."""
        ...

    def repr_failure(self, excinfo, style=None) -> str:
        """Custom failure representation with M-Unit context."""
        ...

    def reportinfo(self) -> tuple[str, int | None, str]:
        """Display info: (file, line, test_id)."""
        ...
```

### `class MUnitCollector(pytest.Collector)`

Discovers M-Unit test routines from TestList files.

```python
class MUnitCollector(pytest.Collector):
    def collect(self) -> Iterator[MUnitTestItem]:
        """Discover test routines from VistA submodule TestList files."""
        ...
```

### `transpile_and_execute(config: TestRoutineConfig, runtime: MUMPSRuntime) -> str`

Transpile a test routine and its dependencies, execute it, and return raw output.

**Parameters**:
- `config`: Routine configuration with source path and dependencies
- `runtime`: Shared MUMPSRuntime instance (for global state)

**Returns**: Raw M-Unit output text from the transpiled execution.

**Behavior**:
1. Read MUMPS source for the routine and all its dependencies
2. Transpile each using `m2py.codegen.generate_python()`
3. Load transpiled modules into `sys.modules`
4. Transpile and load `%ut` and `%ut1` (M-Unit framework) if not already loaded
5. Call the M-Unit entry point (e.g., `EN^%ut(routine_name)`)
6. Capture and return output from `runtime.get_output()`

**Error handling**:
- Transpilation error → raise `MUnitTranspileError(routine, error_details)`
- Runtime error → return partial output + error info
- Import error → raise `MUnitDependencyError(routine, missing_dep)`

### conftest.py Plugin

```python
# vista-test/tests/vista/munit/conftest.py

def pytest_collect_file(parent, file_path):
    """Hook: discover TestList files in VistA submodule."""
    if file_path.name == "TestList" and "MUnit" in str(file_path):
        return MUnitCollector.from_parent(parent, path=file_path)

@pytest.fixture(scope="session")
def munit_baseline():
    """Load committed VEHU baseline from baselines/vehu-baseline.json."""
    baseline_path = Path(__file__).parents[3] / "baselines" / "vehu-baseline.json"
    if baseline_path.exists():
        return BaselineData.from_json(baseline_path)
    return None

@pytest.fixture(scope="session")
def munit_runtime():
    """Shared MUMPSRuntime for all M-Unit tests."""
    from m2py.runtime import MUMPSRuntime
    runtime = MUMPSRuntime()
    runtime._capture_output = True
    return runtime

@pytest.fixture(scope="session")
def munit_framework(munit_runtime):
    """Transpile and load the M-Unit framework (%ut, %ut1)."""
    # Transpile %ut and %ut1 once per session
    ...
    return framework_modules
```

## xfail Logic

```python
def runtest(self):
    result = transpile_and_execute(self.config, self.runtime)
    parsed = parse_munit_output(result, self.config.routine_name, self.config.package_name)

    if self.baseline:
        baseline_result = self.baseline.packages[self.config.package_name].routines[self.config.routine_name]
        if baseline_result.status in ("fail", "error"):
            # VEHU itself fails this test — mark as xfail
            pytest.xfail(f"Baseline failure on VEHU: {baseline_result.failures} failures, {baseline_result.errors} errors")

    if parsed.status == "error":
        raise MUnitExecutionError(parsed.error_message, parsed.raw_output)

    if parsed.failures > 0 or parsed.errors > 0:
        raise MUnitAssertionError(
            f"{parsed.failures} failures, {parsed.errors} errors in {self.config.routine_name}",
            parsed.failure_details,
        )
```

## Dependencies

- `m2py.codegen.generate_python` — transpilation
- `m2py.runtime.MUMPSRuntime` — execution
- `vista_test.munit.parser` — output parsing
- `vista_test.munit.models` — data classes
- `pytest` — test framework

## Test Contract

```python
# Unit tests: tests/unit/test_munit_adapter.py

def test_collector_discovers_testlist(tmp_path):
    """MUnitCollector finds routines from a TestList file."""
    testlist = tmp_path / "TestList"
    testlist.write_text("D TEST^MXMLBLD\nD ^MXMLDOMT\n")
    # Verify collector yields MUnitTestItem for each line

def test_xfail_when_baseline_fails():
    """Routine marked xfail when baseline shows failure."""
    baseline = MUnitResult(status="fail", failures=2, ...)
    item = MUnitTestItem(..., baseline=baseline)
    # Verify pytest.xfail is called

def test_transpile_error_reported():
    """Transpilation errors include routine name and traceback."""
    # Use intentionally broken MUMPS input
    # Verify MUnitTranspileError raised with context

# Integration tests: tests/vista/munit/test_self_tests.py
def test_utt1_transpiles_and_passes():
    """M-Unit self-test %utt1 transpiles and all assertions pass."""
    # Full pipeline: read .m → transpile → execute → parse → assert pass
```
