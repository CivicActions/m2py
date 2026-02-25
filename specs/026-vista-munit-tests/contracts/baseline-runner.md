# Module Contract: baseline_runner

**Module**: `vista_test.munit.baseline`  
**Location**: `vista-test/src/vista_test/munit/baseline.py`  
**Used by**: CLI script for baseline capture (Phase 0a)

## Public Interface

### `class BaselineRunner`

```python
class BaselineRunner:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 2222,
        username: str = "osehravista",
        password: str = "osehravista",
        timeout: int = 120,
    ): ...
```

Captures M-Unit test results from a running osehravista Docker container.

### `run_routine(self, config: TestRoutineConfig) -> MUnitResult`

Execute a single M-Unit test routine on osehravista and capture its output.

**Parameters**:
- `config`: A `TestRoutineConfig` specifying the routine to run

**Returns**: `MUnitResult` with parsed output from the osehravista execution.

**Behavior**:
1. Ensure SSH connection is established (lazy connect)
2. If routine needs import, load the `.m` source into osehravista first
3. Send the invocation command (e.g., `D EN^%ut("%utt1")`)
4. Wait for output and next prompt (with `timeout` seconds)
5. Parse captured output using `parse_munit_output()`
6. Return structured result

**Error handling**:
- SSH connection failure → `MUnitResult(status="error", error_message="SSH connection failed: ...")`
- Timeout → `MUnitResult(status="timeout", error_message="Exceeded {timeout}s")`
- Import failure → `MUnitResult(status="error", error_message="Failed to import routine: ...")`

### `run_package(self, package_name: str, configs: list[TestRoutineConfig]) -> PackageBaseline`

Execute all routines for a package and return aggregated results.

### `run_all(self, configs: list[TestRoutineConfig]) -> BaselineData`

Execute all configured test routines grouped by package.

**Returns**: `BaselineData` with results for all packages and routines.

### `import_routine(self, config: TestRoutineConfig) -> bool`

Import a MUMPS routine from the VistA submodule into the osehravista instance.

**Parameters**:
- `config`: Routine config with `source_path` to the `.m` file

**Returns**: `True` if import succeeded.

**Behavior**:
1. Read the `.m` file from the VistA submodule
2. Send routine to osehravista via programmer mode (ZL/ZS or %RI equivalent)
3. Verify routine was loaded

### CLI Entry Point

```bash
# Run all packages
uv run python -m vista_test.munit.baseline --output baselines/osehravista-baseline.json

# Run single package
uv run python -m vista_test.munit.baseline --package "MASH Utilities" --output baselines/osehravista-baseline.json

# Run single routine
uv run python -m vista_test.munit.baseline --routine "%utt1" --output baselines/osehravista-baseline.json

# With custom connection
uv run python -m vista_test.munit.baseline --host osehravista.local --port 2222 --timeout 180
```

## Dependencies

- `vista_test.munit.parser` — for output parsing
- `vista_test.munit.models` — for data classes
- `vista_test.terminal.session.VistATerminal` — for SSH connection
- `paramiko` — SSH transport (via VistATerminal)
- Standard library: `json`, `argparse`, `datetime`

## Test Contract

```python
# Integration tests (require osehravista Docker): tests/integration/test_baseline.py
# Mark with @pytest.mark.smoke (requires live server)

def test_baseline_single_routine(osehra_runner):
    """Can execute a single M-Unit self-test on osehravista."""
    config = TestRoutineConfig(routine_name="%utt1", ...)
    result = osehra_runner.run_routine(config)
    assert result.status in ("pass", "fail")
    assert result.total_tests > 0

def test_baseline_imports_routine(osehra_runner):
    """Can import a test routine into osehravista before running."""
    config = TestRoutineConfig(routine_name="MXMLBLD", source_path="...")
    result = osehra_runner.run_routine(config)
    assert result.status != "error" or "import" not in result.error_message

def test_baseline_timeout(osehra_runner):
    """Timeout produces error status, not hang."""
    # Use artificially short timeout
    runner = BaselineRunner(timeout=1)
    config = TestRoutineConfig(...)  # long-running routine
    result = runner.run_routine(config)
    assert result.status == "timeout"

def test_baseline_json_output(osehra_runner, tmp_path):
    """Baseline data serializes to valid JSON matching schema."""
    baseline = osehra_runner.run_all([...])
    path = tmp_path / "baseline.json"
    # serialize and validate
```
