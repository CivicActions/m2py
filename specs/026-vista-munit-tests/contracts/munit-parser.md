# Module Contract: munit_parser

**Module**: `vista_test.munit.parser`  
**Location**: `vista-test/src/vista_test/munit/parser.py`  
**Used by**: Baseline runner (Phase 0a), pytest adapter (Phase 0b)

## Public Interface

### `parse_munit_output(raw_output: str, routine: str, package: str) -> MUnitResult`

Parse raw M-Unit framework output text into a structured result.

**Parameters**:
- `raw_output`: Complete captured text output from a single M-Unit routine execution
- `routine`: Name of the routine that was executed (e.g., `"%utt1"`, `"MXMLBLD"`)
- `package`: Package name (e.g., `"MASH Utilities"`, `"M XML Parser"`)

**Returns**: `MUnitResult` dataclass with parsed counts, status, and failure details.

**Behavior**:
1. Search for summary line: `"Checked N test(s), with N failure(s) and encountered N error(s)."`
2. Extract `total_tests`, `failures`, `errors` from summary
3. Search for "Ran N Routine(s), M Entry Tag(s)" to get `entry_tags` and `routines_ran`
4. Parse failure lines matching `"{entry}^{routine} - {name} - {message}"` pattern
5. Parse CHKEQ failures matching `"<{expected}> vs <{actual}>"` sub-pattern
6. Parse error lines matching `"- Error: {error_text}"` pattern
7. If no summary line found, set `status = "error"` and `error_message` describing partial output
8. Count `.` characters before summary for assertion dot tracking

**Error handling**:
- Empty output → `MUnitResult(status="error", error_message="No output captured")`
- Partial output (no summary) → extract available failures/errors, status="error"
- Malformed summary → status="error", include raw_output for debugging

### `parse_testlist(testlist_path: str, package_name: str) -> list[TestRoutineConfig]`

Parse an OSEHRA TestList file into routine configurations.

**Parameters**:
- `testlist_path`: Path to TestList file (e.g., `VistA/Packages/M XML Parser/Testing/MUnit/TestList`)
- `package_name`: Package name for all routines in this list

**Returns**: List of `TestRoutineConfig` entries.

**Behavior**:
1. Read file line by line
2. Match invocation patterns: `D\s+(\w+\^)?(\w+)` or `D\s+EN\^%ut\("(\w+)"(?:,\d+)?\)`
3. Extract routine name from invocation
4. Locate the `.m` source file in the same MUnit directory
5. Assign tier based on package name mapping

**Error handling**:
- Missing file → raise `FileNotFoundError`
- Unparseable line → log warning, skip line
- Missing `.m` source → include config with `source_path = ""` and log warning

## Dependencies

- Standard library only (`re`, `dataclasses`)
- No m2py imports
- No network/Docker/SSH
- Data classes from `vista_test.munit.models`

## Test Contract

```python
# Unit tests: tests/unit/test_munit_parser.py

def test_parse_passing_output():
    """Summary: 0 failures, 0 errors → status='pass'"""
    raw = ".........\nRan 1 Routine(s), 5 Entry Tag(s)\nChecked 9 tests, with 0 failures and encountered 0 errors."
    result = parse_munit_output(raw, "%utt1", "MASH Utilities")
    assert result.status == "pass"
    assert result.total_tests == 9
    assert result.failures == 0
    assert result.errors == 0

def test_parse_failure_chktf():
    """CHKTF failure line parsed with entry, name, message"""
    raw = "...\nT1^%utt1 - Test 1 - Expected TRUE but got FALSE\nChecked 3 tests, with 1 failure and encountered 0 errors."
    result = parse_munit_output(raw, "%utt1", "MASH Utilities")
    assert result.failures == 1
    assert result.failure_details[0].kind == "failure"
    assert result.failure_details[0].entry_tag == "T1"

def test_parse_failure_chkeq():
    """CHKEQ failure line parsed with expected vs actual"""
    raw = "T1^%utt1 - Test 1 - <hello> vs <world> - Values differ\nChecked 1 test, with 1 failure and encountered 0 errors."
    result = parse_munit_output(raw, "%utt1", "MASH Utilities")
    assert result.failure_details[0].expected == "hello"
    assert result.failure_details[0].actual == "world"

def test_parse_error_output():
    """Error line parsed correctly"""
    raw = "T1^%utt1 - Test 1 - Error: 150374082,Z,%utt1+5^%utt1\nChecked 1 test, with 0 failures and encountered 1 error."
    result = parse_munit_output(raw, "%utt1", "MASH Utilities")
    assert result.errors == 1
    assert result.failure_details[0].kind == "error"

def test_parse_empty_output():
    """Empty output → error status"""
    result = parse_munit_output("", "%utt1", "MASH Utilities")
    assert result.status == "error"

def test_parse_partial_output():
    """No summary line → error with extracted failures"""
    raw = "...\nT1^%utt1 - Test 1 - Something failed\n"
    result = parse_munit_output(raw, "%utt1", "MASH Utilities")
    assert result.status == "error"
    assert len(result.failure_details) == 1

def test_parse_testlist():
    """TestList parsed into routine configs"""
    configs = parse_testlist("path/to/TestList", "M XML Parser")
    assert all(isinstance(c, TestRoutineConfig) for c in configs)
```
