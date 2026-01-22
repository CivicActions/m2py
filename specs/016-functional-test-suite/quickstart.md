# Quickstart: Functional Test Suite

**Feature**: 016-functional-test-suite  
**Date**: 2026-01-21

## Overview

The functional test suite validates m2py transpilation against YottaDB reference output. Tests execute MUMPS routines via m2py and compare output byte-for-byte against outref files.

## Running Tests

### Full Suite

```bash
# Run all functional tests
uv run pytest tests/functional/ -v

# Run with coverage
uv run pytest tests/functional/ --cov=m2py
```

### Individual Suites

```bash
# Run specific suite by directory
uv run pytest tests/functional/mugj/ -v

# Run specific suite by marker
uv run pytest tests/functional/ -m mugj -v

# Run specific test file
uv run pytest tests/functional/test_mugj.py -v
```

### Filtering Tests

```bash
# Run tests matching pattern
uv run pytest tests/functional/ -k "V1WR" -v

# Run only xfail tests (known limitations)
uv run pytest tests/functional/ -m xfail -v

# Show xfail reason when they pass unexpectedly
uv run pytest tests/functional/ --runxfail -v
```

## Test Structure

```
tests/functional/
├── conftest.py              # Functional test fixtures
├── test_mugj.py             # mugj suite (376 routines)
├── test_basic.py            # basic suite (107 routines)
└── <suite>/
    ├── inref/               # MUMPS source files (.m)
    ├── outref/              # Reference output (.txt)
    └── u_inref/             # Test drivers (.csh)
```

## Understanding Results

### Pass

Output matches outref exactly (after normalization):

```
tests/functional/test_mugj.py::test_V1WR PASSED
```

### Fail

Output differs from outref - shows diff:

```
tests/functional/test_mugj.py::test_V1CMT FAILED
    Expected: "V1CMT\n; Comment test\n"
    Actual:   "V1CMT\n"
    Diff: Line 2 differs
```

### xfail (Expected Failure)

Test for known m2py limitation:

```
tests/functional/test_mugj.py::test_V1VIEW XFAIL (LIM-005: VIEW command implementation-specific keywords)
```

### xpass (Unexpected Pass)

Previously failing test now passes - may indicate fixed limitation:

```
tests/functional/test_mugj.py::test_V1NEW XPASS
```

## Adding New Tests

### 1. Add MUMPS Source

Place `.m` file in appropriate `inref/` directory:

```
tests/functional/<suite>/inref/NEWTEST.m
```

### 2. Generate Reference Output

Run through YDB to generate expected output:

```bash
docker run --rm -v "$(pwd):/workspace" ydb tests/functional/<suite>/inref/NEWTEST.m >> tests/functional/<suite>/outref/<suite>.txt
```

### 3. Update Test Driver (if multi-routine)

Add to driver script in `u_inref/`:

```csh
W !!,"NEWTEST" D ^NEWTEST
```

## Marking Limitations

Use `limitations.py` IDs for xfail markers:

```python
import pytest
from m2py.limitations import LIMITATIONS

@pytest.mark.xfail(
    reason=f"LIM-005: {LIMITATIONS['LIM-005'].short_description}",
    strict=False
)
def test_view_specific():
    ...
```

Common limitation IDs:
- **LIM-003**: MWAPI SSVNs (`^$EVENT`, `^$WINDOW`, `^$DISPLAY`)
- **LIM-005**: VIEW command implementation-specific keywords
- **LIM-012**: Unknown Z-extensions from other MUMPS implementations
- **LIM-015**: Zero-VistA-usage YDB Z-commands

## Debugging Failed Tests

### View Generated Python

```bash
# Use validate.py with --debug
uv run python utils/validate.py --debug tests/functional/mugj/inref/V1WR.m
```

### Compare Against YDB

```bash
# Run same file through YDB
docker run --rm -v "$(pwd):/workspace" ydb tests/functional/mugj/inref/V1WR.m
```

### Check Normalization

If test fails due to YDB markers, check outref normalization is stripping correctly:

```python
from tests.functional.conftest import normalize_outref

raw = open("tests/functional/mugj/outref/mugj.txt").read()
normalized = normalize_outref(raw)
print(normalized)
```

## Configuration

### Timeout

Tests have a default timeout (configured in pytest.ini or conftest.py):

```ini
# pytest.ini
[pytest]
timeout = 30
```

### Parallelization

Tests support parallel execution:

```bash
uv run pytest tests/functional/ -n auto
```

## Troubleshooting

### "Module not found" Errors

Ensure m2py is installed in development mode:

```bash
uv sync
```

### Timeout Errors

Some routines may hang due to infinite loops or missing input. Check:
1. Does routine use READ command? → Mark as xfail
2. Does routine use HANG command? → Mark as xfail
3. Is there a control flow bug? → Debug with validate.py

### Encoding Errors

All files should be UTF-8. Convert if needed:

```bash
file --mime-encoding tests/functional/mugj/inref/PROBLEM.m
iconv -f ISO-8859-1 -t UTF-8 PROBLEM.m > PROBLEM.m.utf8
```
