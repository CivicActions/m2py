# Quickstart: Codegen Foundation

**Feature**: Spec 004 - Codegen Foundation  
**Date**: 2026-01-08

## What This Spec Delivers

Spec 004 provides the foundational code generation infrastructure for transpiling MUMPS to Python:

1. **M value coercion helpers** - `m_num()`, `m_truth()`, `m_compare()` implementing ANSI MUMPS semantics
2. **Code generators** - For basic statements (SET, WRITE, QUIT, IF, ELSE, FOR, DO, GOTO)
3. **Name translation** - Case-preserving, injective translation of MUMPS names to Python identifiers
4. **Runtime support** - Minimal `MUMPSRuntime` class for executing generated code

## Quick Usage

### Generate Python from MUMPS

```python
from m2py.codegen import generate_python

mumps_source = """
TEST
 S X=5
 W X
 Q
"""

python_code = generate_python(mumps_source)
print(python_code)
```

### Execute Generated Code

```python
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime

code = generate_python("TEST\n S X=5\n W X\n Q\n")
rt = MUMPSRuntime()
result = rt.execute(code)
print(result.output)  # Output: 5
```

### Use Coercion Helpers

```python
from m2py.codegen.helpers import m_num, m_truth, m_compare

# Numeric extraction
assert m_num("3A") == 3
assert m_num("A3") == 0

# Truth evaluation
assert m_truth("3A") == True
assert m_truth("A3") == False

# Comparison
assert m_compare("5", "<", "10") == 1
```

### Name Translation

```python
from m2py.codegen.names import NameTranslator

nt = NameTranslator()
assert nt.translate("%UTIL") == "_pct_UTIL"
assert nt.translate("01") == "_n_01"
assert nt.translate("for") == "_m_for"  # Python keyword
```

## Running Tests

```bash
# Run all codegen tests
uv run pytest tests/unit/codegen/ -v

# Run specific test class
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_1_values.py -v

# Run with coverage
uv run pytest tests/unit/codegen/ --cov=src/m2py/codegen
```

## Scope Boundaries

### In Scope (Spec 004)

- Numeric and string literals
- Local variables (simple names only)
- Operators: `=`, `<`, `>`, `+`, `-`, `*`
- Statements: SET, WRITE, QUIT, IF, ELSE, FOR, DO, GOTO
- M coercion helpers
- Name translation

### Deferred to Later Specs

- Intrinsic functions ($PIECE, $LENGTH, etc.) → Spec 008
- Global variables (^name) → Spec 007/008
- $TEST stack semantics → Spec 005
- Cross-label GOTO patterns → Spec 006

## Key Files

| File | Purpose |
|------|---------|
| `src/m2py/codegen/__init__.py` | Public API (`generate_python`) |
| `src/m2py/codegen/helpers.py` | Coercion helpers |
| `src/m2py/codegen/names.py` | Name translation |
| `src/m2py/runtime/runtime.py` | MUMPSRuntime class |
| `tests/unit/codegen/conftest.py` | Test fixtures |

## Validating Against YDB

Use Docker to validate expected outputs:

```bash
# Run MUMPS from stdin
echo -e 'TEST\n W 1+2\n Q' | docker run --rm -i ydb

# Run a file
docker run --rm -v "$(pwd):/workspace" ydb routine.m
```

All expected outputs in the spec were validated against YDB.
