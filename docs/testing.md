# Testing and Validation

How to test and validate parser output.

## Test Organization

M2PY tests are organized to systematically map to the MUMPS 1995 ANSI specification sections (§5-§9). This spec-aligned structure ensures verifiable, gap-free coverage tracking against the standard.

### Directory Structure

```
tests/
├── unit/
│   ├── parser/                    # Parser-level tests (textX grammar)
│   │   ├── s5_metalanguage/       # §5 Metalanguage (informative)
│   │   ├── s6_routine/            # §6 Routine Structure
│   │   ├── s7_expressions/        # §7 Expressions
│   │   ├── s8_commands/           # §8 Commands
│   │   ├── s9_charset/            # §9 Character Set
│   │   ├── extensions/ydb/        # YottaDB Z-commands
│   │   └── legacy/                # Pre-1995 syntax tests
│   ├── asg/                       # ASG-level tests (semantic analysis)
│   │   └── (parallel structure to parser/)
│   ├── codegen/                   # Codegen-level tests (Python output)
│   │   └── (parallel structure to parser/)
│   ├── cross_cutting/             # Features spanning multiple commands
│   ├── analysis/                  # Internal algorithm tests
│   └── meta/                      # Tooling and infrastructure tests
├── integration/                   # Integration tests
└── functional/                    # YDBTest functional suites
```

### Three-Level Testing

Each MUMPS language feature is tested at three levels, mirroring the transpiler architecture:

| Level | What it tests | Example assertion |
|-------|--------------|-------------------|
| **Parser** | textX grammar produces correct AST | `assert stmt.command == 'SET'` |
| **ASG** | Semantic analyzer produces correct ASG | `assert node.loop_type == ForLoopType.BOUNDED` |
| **Codegen** | Generated Python matches MUMPS behavior | `assert runtime.get('X') == 'value'` |

**File naming convention**: Test files mirror spec sections with a parallel structure:
```
tests/unit/parser/s8_commands/test_s8_2_18_set.py   # §8.2.18 SET - parser level
tests/unit/asg/s8_commands/test_s8_2_18_set.py      # §8.2.18 SET - ASG level
tests/unit/codegen/s8_commands/test_s8_2_18_set.py  # §8.2.18 SET - codegen level
```

### Test Markers

Tests use pytest markers to categorize and filter:

| Marker | Purpose | Example |
|--------|---------|---------|
| `@pytest.mark.parser` | Parser-level test | Required in `tests/unit/parser/` |
| `@pytest.mark.asg` | ASG-level test | Required in `tests/unit/asg/` |
| `@pytest.mark.codegen` | Codegen-level test | Required in `tests/unit/codegen/` |
| `@pytest.mark.stub` | Placeholder test (xfail) | Pending implementation |
| `@pytest.mark.slow` | Long-running test | Skipped by default |
| `@pytest.mark.pre1995` | Pre-1995 MUMPS syntax | Backward compatibility |
| `@pytest.mark.ydb` | YottaDB-specific | Z-commands, Z-functions |

**Marker enforcement**: Tests in `parser/`, `asg/`, and `codegen/` directories require a category marker. Tests in `analysis/`, `meta/`, and `cross_cutting/` do not (they test internal algorithms, not spec compliance).

### Stub/XFail Workflow

Stub tests mark unimplemented functionality while keeping CI green:

```python
@pytest.mark.stub
@pytest.mark.parser
@pytest.mark.xfail(reason="Not yet implemented: §8.2.18 SET multi-target assignment")
def test_set_multi_target():
    """Parse SET with multiple targets: SET (A,B)=value."""
    pytest.fail("Stub - implement test")
```

**Converting a stub to an implemented test**:
```python
# After implementation, remove @stub and @xfail, add real test:
@pytest.mark.parser
def test_set_multi_target(parser):
    """Parse SET with multiple targets: SET (A,B)=value."""
    routine = parser.parse_string('TEST S (A,B)="x"')
    stmt = routine.labels[0].body.statements[0]
    assert len(stmt.assignments) == 1
    assert len(stmt.assignments[0].targets) == 2
```

### Common pytest Commands

```bash
# Run all tests
uv run pytest

# Run by category
uv run pytest -m parser              # All parser-level tests
uv run pytest -m asg                 # All ASG-level tests
uv run pytest -m codegen             # All codegen-level tests

# Run only implemented tests (exclude stubs)
uv run pytest -m "not stub"

# Run only stubs (see pending work)
uv run pytest -m stub --collect-only

# Run specific spec section
uv run pytest tests/unit/parser/s8_commands/ -v
uv run pytest -k "s8_2_18"           # All SET command tests

# Run by extension
uv run pytest -m ydb -v              # YottaDB-specific tests
uv run pytest -m pre1995 -v          # Backward compatibility tests

# Include slow tests
uv run pytest -m ''                  # All tests including slow
uv run pytest -m slow -v -s          # Only slow tests
```

## Running Tests

### Full Test Suite

Tests run in parallel by default using `pytest-xdist`:

```bash
uv run pytest              # Parallel execution on all CPU cores
uv run pytest -n 1         # Sequential execution (for debugging)
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

### Including Slow Tests

The summary report test is marked as `@pytest.mark.slow` and skipped by default:

```bash
uv run pytest                           # Skip slow tests (default)
uv run pytest -m slow -v -s             # Run only slow tests
uv run pytest -m ''                     # Run all tests including slow
```

### Coverage Report

```bash
uv run pytest --cov=src/m2py --cov-report=html
open htmlcov/index.html
```

## Test Coverage Audit

The `utils/audit_tests.py` script audits test coverage against MUMPS 1995 ANSI spec sections (§5-§9):

```bash
# Full coverage report
uv run python utils/audit_tests.py

# Filter by section
uv run python utils/audit_tests.py --section s7              # All §7 sections
uv run python utils/audit_tests.py --section s8_2_18         # Just SET command
uv run python utils/audit_tests.py --section extensions/ydb  # YottaDB extensions

# Save report to file
uv run python utils/audit_tests.py --output docs/coverage-matrix.md

# Check coverage only (returns exit code 0 if all sections covered)
uv run python utils/audit_tests.py --check-only

# Quiet mode (only exit code, no output)
uv run python utils/audit_tests.py -q
```

### Report Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Implemented (tests pass) |
| 🚧 | Stub (xfail, pending implementation) |
| ⚠️ | XFail (needs investigation) |
| ⏭️ | Skipped (out of scope or implementation-defined) |
| ❌ | Missing (no test file) |
| — N/A | Not applicable for this category |

### Exit Codes

- `0` - All required sections have test files
- `1` - One or more sections missing test files

## Test Suites

The project includes multiple MUMPS test suites from YottaDB (YDBTest) for comprehensive validation:

### Test Suite Summary

| Suite | Tests | Description | Location |
|-------|-------|-------------|----------|
| **MUGJ** | 76 | MUMPS User Group Japan validation suite | `tests/functional/mugj/` |
| **MVTS** | 354 | MUMPS Validation Test Suite | `tests/functional/mvts/` |
| **basic** | 61 | Core language tests (FOR, KILL, arithmetic) | `tests/functional/basic/` |
| **merge** | 25 | MERGE command tests | `tests/functional/merge/` |

### Functional Tests (End-to-End)

The `tests/functional/` directory contains end-to-end tests that execute MUMPS routines via m2py transpilation and compare output against YottaDB reference files (outrefs).

```bash
# Run all functional tests (~489 tests, ~37 seconds)
uv run pytest tests/functional/ -q

# Run specific suite
uv run pytest tests/functional/test_mugj.py -v
uv run pytest tests/functional/test_basic.py -v
uv run pytest tests/functional/test_mvts.py -v
uv run pytest tests/functional/test_merge.py -v

# Run specific routine by pattern
uv run pytest tests/functional/ -k "V1WR" -v
```

**Test markers for filtering:**
- `@pytest.mark.mugj` - MUGJ suite tests
- `@pytest.mark.basic` - Basic suite tests
- `@pytest.mark.mvts` - MVTS suite tests
- `@pytest.mark.merge` - MERGE command tests
- `@pytest.mark.functional` - All functional tests

**Known limitation handling:**
Tests using features with documented limitations (VIEW command, Z-commands) are marked as `xfail` with references to limitation IDs:

```bash
# View xfailed tests
uv run pytest tests/functional/ -k "view" -v
# 2 xfailed in 1.10s
```

### Integration Tests

The `tests/integration/` directory contains cross-module tests:

- `test_external_calls.py` - Cross-routine coordination (43 tests)
- `test_indirection_edge_cases.py` - Indirection edge cases (10 tests)

```bash
# Run all integration tests
uv run pytest tests/integration/ -v
# 48 passed
```

### Test Fixtures

Each test directory has corresponding fixtures in `tests/functional/conftest.py`:

```python
# Core functions (not fixtures)
from tests.functional.conftest import (
    normalize_outref,   # Strip YDB infrastructure from outref content
    run_mumps,          # Execute MUMPS via m2py transpilation
    compare_output,     # Byte-for-byte comparison with diff reporting
    load_routine_source,  # Load MUMPS routine source
)
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
addopts = "-n auto -m 'not slow'"  # Parallel, skip slow tests
pythonpath = ["src"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
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
## Backward Compatibility

M2PY supports MUMPS code written to older ANSI standards (1977, 1984, 1990) as well as the current 1995 standard. This section documents syntax differences across standards and how M2PY handles legacy constructs.

### Supported Standards

| Standard | Year | Key Features |
|----------|------|--------------|
| ANSI X11.1-1977 | 1977 | Base language (SET, IF, FOR, GOTO, etc.) |
| ANSI X11.1-1984 | 1984 | NEW command, $ORDER, $QUERY, $GET, parameter passing |
| ANSI M X11.1-1990 | 1990 | MERGE command, $TRANSLATE, $NAME, $FNUMBER, $REVERSE |
| ANSI M X11.1-1995 | 1995 | Transaction processing, SSVNs, structured error handling |

### Deprecated Constructs

#### $NEXT Function (Pre-1995)

The `$NEXT` function was deprecated in the 1995 standard in favor of `$ORDER`.

**Syntax**: `$N[EXT](glvn)` or `$NEXT(glvn)`

**M2PY Behavior**: 
- Parses and transpiles correctly
- Emits `MUMPSDeprecationWarning` at runtime:
  ```
  MUMPSDeprecationWarning: $NEXT is deprecated per 1995 spec §7.1.5; use $ORDER instead
  ```

**Usage in legacy code**:
- VistA-M repository: ~488 occurrences
- MVTS test suite: ~58 occurrences (explicit compatibility tests)

**Example**:
```mumps
; Legacy (deprecated)
S X=$N(^GLOBAL(""))
; Modern (preferred)
S X=$O(^GLOBAL(""))
```

#### $DEXTRACT and $DPIECE (Never Standardized)

These functions were proposed for the 1984/1990 standards but never included in the final ANSI standard.

**M2PY Behavior**: Not supported; raises parse error.

### Pre-1995 Test Marker

Tests for backward compatibility features use the `@pytest.mark.pre1995` marker:

```python
@pytest.mark.pre1995
def test_next_function_parsing():
    """Verify $NEXT parses correctly (deprecated but supported)."""
    parser = MUMPSParser()
    routine = parser.parse_string('TEST S X=$N(^A(""))')
    # Assertions...
```

**Running pre-1995 tests**:
```bash
# Run only pre-1995 compatibility tests
uv run pytest -m pre1995 -v

# Exclude pre-1995 tests
uv run pytest -m "not pre1995"
```

### Feature Evolution Reference

For detailed information about which features were added in each standard version, see:
- [specs/002-spec-unit-test-organization/research.md](../specs/002-spec-unit-test-organization/research.md#backward-compatibility-research) - Complete evolution table
- [mumps-reference/INDEX.md](../mumps-reference/INDEX.md) - MUMPS specification reference documents

### VistA Compatibility

M2PY is designed to parse the VistA codebase without syntax errors due to standard version differences. The primary compatibility considerations are:

1. **$NEXT usage**: Approximately 488 occurrences in VistA-M; all parse correctly
2. **Core syntax**: All 1977 core commands/functions are stable across versions
3. **Additions only**: No breaking syntax changes between standards; features are only added

To verify VistA compatibility:
```bash
uv run python utils/verify_vista_parse.py
```