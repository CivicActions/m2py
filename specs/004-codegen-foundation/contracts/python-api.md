# Python API Contracts: Codegen Foundation

**Feature**: Spec 004 - Codegen Foundation  
**Date**: 2026-01-08  
**Status**: Complete

## Overview

This document defines the Python API contracts for the code generation module. All public functions and classes are documented with type signatures, docstrings, and usage examples.

---

## Module: `m2py.codegen`

### `generate_python(source: str, *, routine_name: str | None = None) -> str`

Generate Python code from MUMPS source.

**Parameters**:
- `source`: MUMPS source code as string
- `routine_name`: Optional routine name (inferred from first label if not provided)

**Returns**: Python source code as string

**Raises**:
- `MUMPSParseError`: If source has syntax errors
- `MUMPSSemanticError`: If source has unresolved references

**Example**:
```python
from m2py.codegen import generate_python

python_code = generate_python("""
TEST
 S X=5
 W X
 Q
""")
# Result: Python code with function TEST() that sets X, writes X, returns
```

---

## Module: `m2py.codegen.helpers`

### `m_num(value: str) -> int | float`

Extract numeric value from string per ANSI MUMPS 7.1.4.5.

**Parameters**:
- `value`: Any string value

**Returns**: Numeric interpretation (int if no decimal, else float)

**Examples**:
```python
from m2py.codegen.helpers import m_num

assert m_num("3A") == 3
assert m_num("A3") == 0
assert m_num("3.14") == 3.14
assert m_num("") == 0
assert m_num("  42") == 42
```

### `m_truth(value: str) -> bool`

Evaluate truth of value per ANSI MUMPS 1.2.4.

**Parameters**:
- `value`: Any string value

**Returns**: True if numeric interpretation != 0, else False

**Examples**:
```python
from m2py.codegen.helpers import m_truth

assert m_truth("3A") == True   # 3 != 0
assert m_truth("A3") == False  # 0 == 0
assert m_truth("") == False    # 0 == 0
assert m_truth("1") == True    # 1 != 0
```

### `m_compare(a: str, op: str, b: str) -> int`

Compare two values using M semantics.

**Parameters**:
- `a`: Left operand (string)
- `b`: Right operand (string)
- `op`: Comparison operator (`"="`, `"<"`, `">"`)

**Returns**: 1 (true) or 0 (false)

**Examples**:
```python
from m2py.codegen.helpers import m_compare

assert m_compare("5", "<", "10") == 1
assert m_compare("10", "<", "5") == 0
assert m_compare("5", "=", "5") == 1
```

---

## Module: `m2py.codegen.names`

### Class: `NameTranslator`

Translate MUMPS names to valid Python identifiers.

**Methods**:

#### `translate(name: str) -> str`

Translate a MUMPS name to a Python identifier.

**Parameters**:
- `name`: MUMPS label, variable, or routine name

**Returns**: Valid Python identifier

**Translation Rules**:
| MUMPS Pattern | Python Pattern |
|---------------|----------------|
| `%name` | `_pct_name` |
| Numeric only | `_n_digits` |
| Python keyword | `_m_name` |
| Regular | unchanged |

**Examples**:
```python
from m2py.codegen.names import NameTranslator

nt = NameTranslator()
assert nt.translate("%UTIL") == "_pct_UTIL"
assert nt.translate("01") == "_n_01"
assert nt.translate("for") == "_m_for"
assert nt.translate("FOO") == "FOO"
```

#### `reverse(py_name: str) -> str`

Recover original MUMPS name from Python identifier.

**Parameters**:
- `py_name`: Python identifier from previous translation

**Returns**: Original MUMPS name

**Example**:
```python
nt = NameTranslator()
assert nt.reverse("_pct_UTIL") == "%UTIL"
assert nt.reverse("_n_01") == "01"
```

---

## Module: `m2py.runtime`

### Class: `MUMPSRuntime`

Execution context for generated Python code.

**Constructor**:
```python
def __init__(self) -> None:
    """Initialize runtime with empty state."""
```

**Methods**:

#### `get(name: str) -> str`

Get variable value, returning empty string if undefined.

**Parameters**:
- `name`: Variable name

**Returns**: Value as string, or `""` if undefined

**Example**:
```python
rt = MUMPSRuntime()
assert rt.get("X") == ""  # Undefined
rt.set("X", "5")
assert rt.get("X") == "5"
```

#### `set(name: str, value: Any) -> None`

Set variable value (converts to string).

**Parameters**:
- `name`: Variable name
- `value`: Value (will be converted to string)

#### `write(value: Any) -> None`

Append value to output buffer.

**Parameters**:
- `value`: Value to write (converted to string)

#### `execute(code: str, *, capture_output: bool = True) -> ExecutionResult`

Execute generated Python code.

**Parameters**:
- `code`: Python source code from `generate_python()`
- `capture_output`: Whether to capture WRITE output (default True)

**Returns**: `ExecutionResult` with output, variables, and return value

**Example**:
```python
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime

code = generate_python("TEST\n S X=5\n W X\n Q\n")
rt = MUMPSRuntime()
result = rt.execute(code)
assert result.output == "5"
```

### Class: `ExecutionResult`

Result from `MUMPSRuntime.execute()`.

**Attributes**:
- `output: str` - Captured output from WRITE commands
- `variables: dict[str, str]` - Final variable values
- `return_value: str | None` - QUIT return value if any

---

## Test Fixtures (from `conftest.py`)

These fixtures are available for codegen tests:

### `generate_python`

```python
def test_example(generate_python):
    code = generate_python("TEST\n S X=1\n Q")
    assert "X = " in code
```

### `execute_mumps`

```python
def test_example(execute_mumps):
    result = execute_mumps("TEST\n W 1+2\n Q")
    assert result.output == "3"
```

### `execute_expr`

```python
def test_example(execute_expr):
    assert execute_expr('W 1+2') == "3"
```

### `eval_mumps`

```python
def test_example(eval_mumps):
    assert eval_mumps('1+2') == "3"
```
