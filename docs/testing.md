# Testing and Validation

How to test and validate parser output.

## Running Tests

### Full Test Suite

```bash
uv run pytest
```

### Specific Test Files

```bash
uv run pytest tests/integration/
uv run pytest tests/unit/
```

### Verbose Output

```bash
uv run pytest -v tests/integration/test_ydb_suites.py
```

### Coverage Report

```bash
uv run pytest --cov=src/m2py --cov-report=html
open htmlcov/index.html
```

## Test Suites

The project includes multiple MUMPS test suites from YottaDB (YDBTest) for comprehensive validation:

### Test Suite Summary

| Suite | Files | Description | Location |
|-------|-------|-------------|----------|
| **MUGJ** | 376 | MUMPS User Group Japan validation suite | `tests/functional/mugj/inref/` |
| **MVTS** | 714 | MUMPS Validation Test Suite | `tests/functional/mvts_inref/` |
| **basic** | 107 | Core language tests (FOR, KILL, arithmetic) | `tests/functional/basic_inref/` |
| **merge** | 54 | MERGE command tests | `tests/functional/merge_inref/` |
| **indirection** | 9 | Indirection operator (@) tests | `tests/functional/indirection_inref/` |
| **m_commands** | 27 | M command tests including Z-commands | `tests/functional/m_commands_inref/` |
| **io** | 116 | I/O operation tests | `tests/functional/io_inref/` |
| **tp** | 109 | Transaction processing tests | `tests/functional/tp_inref/` |
| **triggers** | 101 | Trigger tests | `tests/functional/triggers_inref/` |
| **longname** | 34 | Long variable name tests | `tests/functional/longname_inref/` |
| **unicode** | 47 | Unicode handling tests | `tests/functional/unicode_inref/` |

**Total: 1,694 test files**

### Running YDBTest Suite Tests

All YDB test suites are tested via `test_ydb_suites.py`:

```bash
# Run all YDB suite tests (summary + all suite validations)
uv run pytest tests/integration/test_ydb_suites.py -v

# Run just the summary report
uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_all_suites_summary -v -s

# Run a specific suite's validation
uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_suite_parses[mugj] -v
uv run pytest tests/integration/test_ydb_suites.py::TestYDBSuites::test_suite_parses[mvts] -v
```

The test class provides:
- `test_all_suites_summary` - Displays parsing status across all 11 suites
- `test_suite_parses[<suite>]` - Validates all files in a specific suite parse

The summary displays:
- **Parsed**: Files that parsed without raising exceptions
- **Clean**: Files with zero `parse_errors` (no masked failures)
- **Clean%**: Percentage of files that are truly error-free

**Note**: `tests/integration/test_mugj.py` contains 90 detailed semantic tests for specific MUGJ files (FOR loop classification, GOTO targets, DO blocks, pattern matching, variable analysis, etc.).

### Parse Result Tracking API

The test infrastructure provides reusable classes for tracking parse results:

```python
from tests.integration.test_ydb_suites import (
    ParseResult,
    SuiteParseResults,
    parse_suite,
)
from m2py.parser import MUMPSParser

# Parse an entire suite and get detailed results
parser = MUMPSParser()
results = parse_suite("mugj", parser)

# Check aggregate statistics
print(f"Total files: {results.total_files}")
print(f"Parsed (no exceptions): {results.parsed_count}")
print(f"Clean (zero errors): {results.clean_count}")
print(f"Success rate: {results.success_rate:.1f}%")
print(f"Clean rate: {results.clean_rate:.1f}%")

# Get files with masked parse errors
for r in results.files_with_errors:
    print(f"{r.filename}: {r.error_count} error(s)")

# Get files that failed to parse
for r in results.files_that_failed:
    print(f"{r.filename}: {r.exception}")
```

**Classes**:
- `ParseResult` - Result for a single file (filename, success, error_count, exception)
- `SuiteParseResults` - Aggregate results for a suite with computed properties
- `parse_suite(suite_name, parser)` - Parse all files in a suite

### Test Fixtures

Each test suite has corresponding fixtures in `tests/conftest.py`:

```python
# Directory fixtures
mvts_inref_dir      # Path to MVTS test directory
basic_inref_dir     # Path to basic test directory
# ... etc

# File loader fixtures
mvts_file("filename.m")    # Load a specific file
basic_file("filename.m")   # Load a specific file

# Iterator fixtures
for name, content in mvts_files():
    # Process each file
```

## Validating Parser Output

### Using validate_asg.py

The validation utility displays ASG structure for any MUMPS file:

```bash
uv run python utils/validate_asg.py tests/functional/mugj/inref/V1SET.m
```

Output includes:
1. Original MUMPS source with line numbers
2. Formatted ASG structure
3. Validation checklist

### Using Python REPL

```python
from m2py import MUMPSParser
from m2py.asg.statements import MSetStatement

parser = MUMPSParser()
routine = parser.parse_file("tests/functional/mugj/inref/V1SET.m")

# Inspect structure
print(f"Routine: {routine.name}")
for label in routine.labels:
    print(f"\nLabel: {label.name}")
    for stmt in label.body.statements:
        print(f"  {type(stmt).__name__}")
```

### Running Analysis Passes

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("file.m")

# All analysis passes
parser.resolve_references(routine)
parser.classify_gotos(routine)
parser.analyze_for_loops(routine)
parser.analyze_variables(routine)

# Check results
for label in routine.labels:
    print(f"{label.name}:")
    print(f"  Inputs: {label.input_variables}")
    print(f"  Outputs: {label.output_variables}")
```

### JSON Output

```python
from m2py.parser import dump_asg_json

json_str = dump_asg_json(routine)
with open("output.json", "w") as f:
    f.write(json_str)
```

## MUGJ Test Suite

### Overview

The MUGJ (MUMPS User Group Japan) validation suite provides comprehensive test coverage:

- **376 test files** in `tests/functional/mugj/inref/`
- Tests all language features
- Reference implementation for correctness

### File Naming

| Prefix | Content |
|--------|---------|
| `V1*` | Version 1 tests (core features) |
| `VV1*` | Extended version 1 tests |
| `VV2*` | Version 2 tests |
| `VVE*` | Error handling tests |

### Key Test Files

| File | Features Tested |
|------|-----------------|
| `V1SET.m` | SET command variations |
| `V1WR.m` | WRITE command |
| `V1FORA*.m` | FOR loop patterns |
| `V1DO*.m` | DO/QUIT subroutines |
| `V1IE*.m` | IF/ELSE patterns |
| `V1GO*.m` | GOTO patterns |
| `V1PAT*.m` | Pattern matching |
| `V1IDNM*.m` | Indirection |
| `V1FN*.m` | Intrinsic functions |

### Test Structure

Each test file contains:
1. **Test cases** with expected results
2. **EXAMINER** subroutine for validation
3. **PASS/FAIL counters**

```mumps
V1SET   ;SET COMMAND;...
    S PASS=0,FAIL=0
    ...
    S ITEM="I-781.1"
    SET A(1)="value"
    S VCOMP=A(1)
    S VCORR="value" D EXAMINER
```

## Adding New Tests

### Unit Tests

Create tests in `tests/unit/`:

```python
# tests/unit/test_set_statement.py
import pytest
from m2py import MUMPSParser
from m2py.asg.statements import MSetStatement

def test_simple_set():
    parser = MUMPSParser()
    routine = parser.parse_string("TEST S X=1")
    
    stmt = routine.labels[0].body.statements[0]
    assert isinstance(stmt, MSetStatement)
    assert len(stmt.assignments) == 1
    assert stmt.assignments[0].target.name == "X"

def test_multiple_set():
    parser = MUMPSParser()
    routine = parser.parse_string("TEST S A=1,B=2")
    
    stmt = routine.labels[0].body.statements[0]
    assert len(stmt.assignments) == 2
```

### Functional Tests

Add MUMPS files to `tests/functional/` with corresponding test code:

```python
# tests/functional/test_custom.py
import pytest
from pathlib import Path
from m2py import MUMPSParser

def test_my_feature():
    parser = MUMPSParser()
    routine = parser.parse_file("tests/functional/custom/mytest.m")
    # Assertions
```

## Debugging Parser Issues

### Parse Errors

```python
from m2py import MUMPSParser
from m2py.parser.exceptions import MUMPSParseError

parser = MUMPSParser()
try:
    routine = parser.parse_string("TEST S X=")  # Invalid
except MUMPSParseError as e:
    print(f"Parse error at line {e.line}, col {e.col}")
    print(f"Message: {e.message}")
```

### Inspecting Grammar

The textX grammar files are in `src/m2py/grammar/`:

```bash
ls src/m2py/grammar/
# mumps.tx, line.tx, commands.tx, expressions.tx
```

### Debug Mode

```python
parser = MUMPSParser(debug=True)  # Enable debug output
```

## Continuous Integration

### pytest Configuration

See `pyproject.toml` for pytest settings:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
```

### Coverage Thresholds

```bash
uv run pytest --cov=src/m2py --cov-fail-under=80
```

## Common Issues

### Missing Analysis

If fields like `input_variables` are empty, ensure analysis passes ran:

```python
parser.resolve_references(routine)
parser.analyze_variables(routine)
```

### Encoding Issues

MUMPS files should be UTF-8 or ASCII:

```python
routine = parser.parse_file("file.m", encoding="utf-8")
```

### Large Files

For performance testing with large files:

```python
import time
start = time.time()
routine = parser.parse_file("large.m")
print(f"Parse time: {time.time() - start:.2f}s")
```

## Testing Conventions

### Test Docstrings

Test docstrings should describe the **behavior being tested**, not reference internal task numbers or bug IDs:

```python
# Good - describes behavior
def test_double_negative(self):
    """Parse double unary minus (chained unary operators are valid MUMPS syntax)."""

# Avoid - references internal tracking
def test_double_negative(self):
    """Parse double unary minus (BUG-002 fix)."""  # ❌
```

### API Property Naming

When testing statement properties, use the **primary field names** rather than deprecated aliases:

```python
# Good - uses primary field name
assert len(stmt.targets) == 2  # MJobStatement, MDoStatement, MGotoStatement

# Avoid - uses deprecated alias
assert len(stmt.calls) == 2  # ❌ deprecated for MJobStatement
```

### Deprecated Properties

The following properties are deprecated but maintained for backward compatibility:

| Statement | Deprecated | Use Instead |
|-----------|------------|-------------|
| `MJobStatement` | `.calls` | `.targets` |
| `MJobStatement` | `.call` | `.targets[0]` |

Tests for backward compatibility should explicitly document the deprecation:

```python
def test_backward_compat_calls_property(self):
    """Verify deprecated .calls property works for backward compatibility."""
    stmt = ...
    # .calls is deprecated alias for .targets
    assert stmt.calls is stmt.targets
```
