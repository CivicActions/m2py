# Quickstart: Minimal Control Flow Foundation

**Date**: 2026-01-09  
**Feature**: [spec.md](spec.md)

## Prerequisites

- Python 3.10+
- uv package manager
- Repository cloned with dependencies installed (`uv sync`)

## Usage

### Generate Python from MUMPS

```python
from m2py.codegen import generate_python

mumps_source = """TEST S X=1 W X Q"""
python_code = generate_python(mumps_source)
print(python_code)
```

Output:
```python
from m2py.codegen.helpers import m_num, m_truth, m_compare
from m2py.runtime import MUMPSRuntime

_rt = MUMPSRuntime()
_test = False

def TEST():
    global _test
    X = 1
    _rt.write(str(X))
```

### Execute Generated Code

```python
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime

source = """TEST S X=5 I X>3 W "GT" Q E W "LE" Q"""
code = generate_python(source)

runtime = MUMPSRuntime()
result = runtime.execute(code)
print(result.output)  # "GT"
```

### Testing with pytest Fixtures

```python
def test_basic_set(execute_mumps):
    result = execute_mumps("TEST S X=1 W X Q")
    assert result.output == "1"

def test_if_condition(execute_mumps):
    result = execute_mumps("TEST S X=5 I X>3 W \"GT\" Q E W \"LE\" Q")
    assert result.output == "GT"

def test_for_loop(execute_mumps):
    result = execute_mumps("TEST F I=1:1:3 W I Q")
    assert result.output == "123"
```

## Key APIs

### generate_python(source: str, routine_name: str | None = None) -> str

Generate Python code from MUMPS source.

**Parameters**:
- `source`: MUMPS source code (single routine)
- `routine_name`: Optional name for generated module

**Returns**: Python source code as string

### MUMPSRuntime

```python
runtime = MUMPSRuntime()

# Execute generated code
result = runtime.execute(python_code)

# Access results
print(result.output)      # WRITE output
print(result.success)     # True if no errors
print(result.error)       # Error message if any
print(result.test_value)  # Final $TEST value
```

### Helper Functions

```python
from m2py.codegen.helpers import m_num, m_truth, m_compare

# Numeric coercion
m_num("3A")   # → 3
m_num("")     # → 0
m_num("A")    # → 0

# Truth evaluation  
m_truth("0")  # → False
m_truth("1")  # → True
m_truth("A")  # → False

# Comparison
m_compare(3, "=", 3)      # → True
m_compare("3A", "<", 5)   # → True (3 < 5)
```

## Supported Syntax (Spec 004)

| Feature | Example | Status |
|---------|---------|--------|
| Integer literals | `1`, `-5`, `42` | ✓ |
| String literals | `"hello"`, `""` | ✓ |
| Local variables | `X`, `COUNT` | ✓ |
| SET (single) | `S X=1` | ✓ |
| WRITE (single) | `W X`, `W "text"` | ✓ |
| QUIT (no value) | `Q` | ✓ |
| IF | `I X>3 W "yes"` | ✓ |
| ELSE | `E W "no"` | ✓ |
| FOR (bounded) | `F I=1:1:10 ...` | ✓ |
| FOR (list) | `F I="A","B" ...` | ✓ |
| DO (label) | `D SUB` | ✓ |
| GOTO (label) | `G DONE` | ✓ |
| Arithmetic | `+`, `-` | ✓ |
| Comparison | `=`, `<`, `>` | ✓ |

## Not Yet Supported

See [spec.md](spec.md) "Explicitly Deferred" section for full list:
- Global variables (^name)
- Intrinsic functions ($PIECE, $LENGTH)
- Multiple assignments (S X=1,Y=2)
- Subscripted variables
- Postconditions (S:cond X=1)
- And more...

## Running Tests

```bash
# Run all codegen tests
uv run pytest tests/unit/codegen/ -v

# Run specific test file
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_1_values.py -v

# Run with coverage
uv run pytest tests/unit/codegen/ --cov=m2py.codegen
```

## Generating YDB Reference Output

```bash
# Run MUMPS file through YDB
docker run --rm -v "$(pwd):/workspace" ydb routine.m

# Run inline MUMPS
echo -e 'TEST\n write 1+2,!' | docker run --rm -i ydb
```
