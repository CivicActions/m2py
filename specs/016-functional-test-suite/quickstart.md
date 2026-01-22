# Quickstart: Functional Test Suite

**Feature**: 016-functional-test-suite  
**Date**: 2026-01-21

## Overview

The functional test suite validates m2py transpilation against YottaDB reference output. Tests execute MUMPS routines via m2py and compare output byte-for-byte against outref files.

## Running Tests

### Full Suite

```bash
# Run all functional tests (~489 tests, ~37 seconds)
uv run pytest tests/functional/ -q
# 147 failed, 336 passed, 1 skipped, 5 xfailed

# Run with verbose output
uv run pytest tests/functional/ -v
```

### Individual Suites

```bash
# Run specific test file
uv run pytest tests/functional/test_mugj.py -v
# 63 failed, 12 passed, 1 skipped

uv run pytest tests/functional/test_basic.py -v
# 57 tests for core MUMPS functionality

uv run pytest tests/functional/test_mvts.py -v
# 354 tests for MVTS standard compliance
```

### Filtering Tests

```bash
# Run tests matching pattern
uv run pytest tests/functional/ -k "V1WR" -v
# 3 passed in 1.00s

# Run only xfail tests (known limitations)
uv run pytest tests/functional/ -k "view" -v
# 2 xfailed in 1.10s

# Run without parallelization (for debugging)
uv run pytest tests/functional/ -n0 -v
```

## Test Structure

```
tests/functional/
├── conftest.py              # Shared fixtures and helpers
├── suite_definitions.py     # Static routine definitions
├── test_mugj.py             # MUGJ suite (76 routines)
├── test_basic.py            # Basic suite (61 routines)
├── test_mvts.py             # MVTS suite (354 sub-drivers)
├── test_merge.py            # Merge suite (25 subtests)
└── <suite>/
    ├── inref/               # MUMPS source files (.m)
    ├── outref/              # Reference output (.txt)
    └── u_inref/             # Test drivers (.csh)
```

## Understanding Results

### Pass

Output matches outref exactly (after normalization):

```
tests/functional/test_mugj.py::TestMugjSuite::test_routine[V1WR] PASSED
```

### Fail

Output differs from outref - check the diff:

```
tests/functional/test_mugj.py::TestMugjSuite::test_routine[V1CMT] FAILED
    Output mismatch for routine V1CMT
    Expected lines: 5
    Actual lines: 3
```

### xfail (Expected Failure)

Test for known m2py limitation:

```
tests/functional/test_basic.py::TestBasicSuite::test_routine[view] XFAIL
```

Limitations are defined in `src/m2py/limitations.py` with IDs like LIM-005.

### Skip

Test skipped due to missing expected output or other precondition:

```
tests/functional/test_mugj.py::TestMugjSuite::test_routine[V1TST] SKIPPED
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
# Using the ydb docker container
echo 'NEWTEST W "Hello",!' | docker run --rm -i ydb
```

### 3. Add to Suite Definitions

Update `tests/functional/suite_definitions.py`:

```python
MUGJ_ROUTINES: list[RoutineDefinition] = [
    ...
    RoutineDefinition("NEWTEST", "NEWTEST"),
]
```

## Marking Limitations

Routines using known limited features are mapped in `conftest.py`:

```python
ROUTINE_LIMITATIONS: dict[str, str] = {
    "view": "LIM-005",   # VIEW command
    "view2": "LIM-005",
    "zbrk": "LIM-015",   # Z-debugging commands
    ...
}
```

Common limitation IDs:
- **LIM-005**: VIEW command implementation-specific keywords
- **LIM-015**: Zero-VistA-usage YDB Z-commands (ZBREAK, ZSTEP)

## Debugging Failed Tests

### View Generated Python

```bash
# Use validate.py with --debug
uv run python utils/validate.py --debug tests/functional/mugj/inref/V1WR.m
```

### Compare Against YDB

```bash
# Run same MUMPS code through YDB
uv run python utils/validate.py tests/functional/mugj/inref/V1WR.m
```

### Check a Specific Routine

```bash
# Run just one test with full traceback
uv run pytest "tests/functional/test_mugj.py::TestMugjSuite::test_routine[V1WR]" -v --tb=long
```

## Configuration

### Timeout

Tests have a default 30-second timeout. Routines that exceed this are reported as failures with "Execution timed out".

### Parallelization

Tests run in parallel by default (10 workers). Disable for debugging:

```bash
uv run pytest tests/functional/ -n0 -v
```

## Troubleshooting

### "Module not found" Errors

Ensure m2py is installed in development mode:

```bash
uv sync
```

### Timeout Errors

Some routines may hang due to infinite loops or missing input:
1. Does routine use READ command? → Likely requires interactive input
2. Does routine use HANG command? → Waiting for elapsed time
3. Is there a control flow bug? → Debug with validate.py --debug

### Output Mismatch

Many failures are due to functional gaps in m2py (numeric precision, string operations). Check the diff to understand what differs.
