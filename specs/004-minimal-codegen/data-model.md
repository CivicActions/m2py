# Data Model: Minimal Control Flow Foundation

**Date**: 2026-01-09  
**Feature**: [spec.md](spec.md)

## Overview

This document defines the data structures and contracts for the code generation module. Since Spec 004 is primarily about code transformation (ASG → Python text), the "data model" is the shape of generated code and the helper function signatures.

## Entities

### 1. Generated Module Structure

Every generated Python module follows this structure:

```python
# Imports (always present)
from m2py.codegen.helpers import m_num, m_truth, m_compare
from m2py.runtime import MUMPSRuntime

# Runtime instance
_rt = MUMPSRuntime()

# $TEST tracking
_test = False

# Label functions (one per MUMPS label)
def LABEL1():
    global _test
    # ... body ...

def LABEL2():
    global _test
    # ... body ...

# Entry point (optional, for standalone execution)
if __name__ == "__main__":
    LABEL1()  # Call first label
```

### 2. Helper Functions

#### m_num(value: Any) -> float | int

Implements MUMPS numeric coercion (ANSI 7.1.4.5).

**Input**: Any Python value (typically str or numeric)
**Output**: Numeric interpretation

**Rules**:
1. If already numeric, return as-is
2. For strings:
   - Apply sign reduction rules (++→+, +-→-, etc.)
   - Find longest left-head matching numeric literal syntax
   - Return 0 if no numeric prefix
   - Return canonicalized number (strip leading zeros, normalize signs)

**Examples**:
| Input | Output |
|-------|--------|
| `3` | `3` |
| `"3"` | `3` |
| `"3A"` | `3` |
| `"A3"` | `0` |
| `""` | `0` |
| `"007"` | `7` |
| `"  42"` | `42` |
| `"+-5"` | `-5` |
| `"--5"` | `5` |
| `"3.14ABC"` | `3.14` |

#### m_truth(value: Any) -> bool

Implements MUMPS truth evaluation (ANSI 1.2.4).

**Input**: Any Python value
**Output**: Boolean

**Rule**: `m_num(value) != 0`

**Examples**:
| Input | Output |
|-------|--------|
| `1` | `True` |
| `0` | `False` |
| `""` | `False` |
| `"0"` | `False` |
| `"1"` | `True` |
| `"1A"` | `True` |
| `"A"` | `False` |
| `"A1"` | `False` |

#### m_compare(left: Any, op: str, right: Any) -> bool

Implements MUMPS comparison with numeric coercion.

**Input**: Two values and an operator string
**Output**: Boolean comparison result

**Operators**:
- `"="`: Equality (string comparison)
- `"<"`: Less than (numeric comparison)  
- `">"`: Greater than (numeric comparison)

**Rules**:
- `"="`: Compare as strings (exact match)
- `"<"` and `">"`: Convert both operands via m_num(), then compare numerically

**Examples**:
| Left | Op | Right | Output |
|------|-----|-------|--------|
| `"3"` | `"="` | `3` | `False` (string "3" ≠ int 3) |
| `3` | `"="` | `3` | `True` |
| `"3A"` | `"<"` | `5` | `True` (3 < 5) |
| `""` | `"<"` | `1` | `True` (0 < 1) |

### 3. NameTranslator

Handles conversion between MUMPS names and Python identifiers.

**Methods**:

#### translate(mumps_name: str) -> str

Convert MUMPS name to valid Python identifier.

**Rules** (applied in order):
1. If starts with `%`: replace with `_pct_` prefix
2. If pure numeric (matches `^[0-9]+$`): add `_n_` prefix
3. If Python keyword: add `_m_` prefix
4. Otherwise: use as-is (MUMPS is already valid Python in most cases)

**Examples**:
| MUMPS | Python |
|-------|--------|
| `TEST` | `TEST` |
| `%START` | `_pct_START` |
| `01` | `_n_01` |
| `if` | `_m_if` |
| `FOO` | `FOO` |
| `foo` | `foo` |

#### reverse(python_name: str) -> str

Recover original MUMPS name from Python identifier.

**Rules**:
1. If starts with `_pct_`: strip prefix, prepend `%`
2. If starts with `_n_`: strip prefix
3. If starts with `_m_`: strip prefix
4. Otherwise: identity

### 4. MUMPSRuntime

Minimal runtime for test harness support.

**Properties**:
- `_output: list[str]` - accumulated WRITE output
- `_test: bool` - current $TEST value (exposed for advanced scenarios)

**Methods**:

#### write(value: str) -> None

Append value to output buffer.

#### get_output() -> str

Return concatenated output.

#### execute(python_code: str, capture_output: bool = True) -> ExecutionResult

Execute generated Python in isolated namespace.

**ExecutionResult**:
```python
@dataclass
class ExecutionResult:
    output: str          # Captured WRITE output
    success: bool        # True if no exceptions
    error: Optional[str] # Exception message if failed
    test_value: bool     # Final $TEST value
```

### 5. GeneratorContext

Internal context passed through code generation.

```python
@dataclass
class GeneratorContext:
    routine: MRoutine           # Source routine
    emitter: CodeEmitter        # Output emitter
    name_translator: NameTranslator
    imports: set[str]           # Collected imports
    current_label: Optional[MLabel]  # Current label being generated
```

## Relationships

```
MRoutine
    └── labels: List[MLabel]
           └── body: MScope
                  └── statements: List[MStatement]
                         └── (MSetStatement, MWriteStatement, etc.)

generate_python(source: str)
    └── parse(source) → MRoutine
    └── RoutineGenerator(routine)
           └── generate() → str
                  └── for label in routine.labels:
                         └── generate_label(label)
                                └── for stmt in label.body.statements:
                                       └── generate_statement(stmt)
                                              └── generate_expr(expr) as needed
```

## Validation Rules

1. **Generated code must parse**: `ast.parse(generated_code)` must succeed
2. **Output must match YDB**: For all acceptance scenarios, output equals YDB reference
3. **Names must be reversible**: `reverse(translate(name)) == name` for all valid MUMPS names
4. **Coercion must be deterministic**: Same input always produces same output
5. **$TEST must track IF conditions**: After IF, `_test` equals condition result
