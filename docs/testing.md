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
uv run pytest -v tests/integration/test_mugj.py
```

### Coverage Report

```bash
uv run pytest --cov=src/m2py --cov-report=html
open htmlcov/index.html
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
