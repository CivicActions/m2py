# Data Model: Minimal Control Flow Foundation

**Feature**: Spec 004 - Codegen Foundation  
**Date**: 2026-01-08  
**Status**: Complete

## Overview

This document defines the data model for the code generation foundation. Since Spec 004 consumes the existing ASG (no new ASG nodes needed), this focuses on the **codegen module entities** and **runtime classes**.

## Entity Definitions

### 1. CodeGenerator

**Purpose**: Transforms ASG to Python source code

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `runtime_name` | `str` | Variable name for runtime in generated code (default: `_rt`) |
| `indent_level` | `int` | Current indentation depth (starts at 0) |
| `output` | `list[str]` | Accumulated lines of Python code |

**Relationships**:
- Consumes: `MRoutine`, `MLabel`, `MStatement`, `MExpr` (ASG)
- Produces: Python source code as string

**Validation Rules**:
- `indent_level >= 0`
- Output must be valid Python 3.10+ syntax

### 2. NameTranslator

**Purpose**: Converts MUMPS names to valid Python identifiers

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `reserved_words` | `frozenset[str]` | Python reserved keywords |
| `translations` | `dict[str, str]` | Cache of translated names |

**Methods**:
| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `translate(name)` | MUMPS name | Python identifier | Case-preserving, injective translation |
| `reverse(py_name)` | Python identifier | MUMPS name | Recover original MUMPS name |

**Validation Rules**:
- Translation is injective (no two MUMPS names → same Python name)
- Translation is reversible
- Output is valid Python identifier (matches `[a-zA-Z_][a-zA-Z0-9_]*`)

**State Transitions**: None (stateless utility)

### 3. MUMPSRuntime

**Purpose**: Execution context for generated Python code

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `_variables` | `dict[str, str]` | Local variable storage (name → value) |
| `_output` | `list[str]` | Output buffer for WRITE |
| `_test` | `bool` | $TEST value (placeholder for Spec 005) |

**Methods**:
| Method | Input | Output | Description |
|--------|-------|--------|-------------|
| `get(name)` | variable name | `str` | Returns value or `""` if undefined |
| `set(name, value)` | name, value | None | Stores value (auto-converts to string) |
| `write(value)` | value | None | Appends to output buffer |
| `execute(code)` | Python code | `ExecutionResult` | Runs code and returns result |

**Validation Rules**:
- All values stored as strings (M semantics)
- `get()` never raises for undefined (returns `""`)

### 4. ExecutionResult

**Purpose**: Return type from `MUMPSRuntime.execute()`

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| `output` | `str` | Captured output from WRITE commands |
| `variables` | `dict[str, str]` | Final variable values |
| `return_value` | `str | None` | QUIT return value if any |

## Coercion Helpers

These are pure functions, not classes, but central to the data model:

### m_num(value: str) -> int | float

**Purpose**: Extract numeric prefix per ANSI MUMPS 7.1.4.5

**Algorithm**:
1. Strip leading whitespace
2. Match longest valid numeric prefix: `[+-]?(\d+\.?\d*|\.\d+)`
3. Return 0 if no match
4. Return int if no decimal, else float

**Examples**:
| Input | Output | Reason |
|-------|--------|--------|
| `"3A"` | `3` | Prefix is "3" |
| `"A3"` | `0` | No numeric prefix |
| `"3.14"` | `3.14` | Full string is numeric |
| `""` | `0` | No prefix |
| `"  42"` | `42` | Leading whitespace stripped |

### m_truth(value: str) -> bool

**Purpose**: Evaluate truth per ANSI MUMPS 1.2.4

**Algorithm**:
1. Call `m_num(value)` to get numeric interpretation
2. Return `result != 0`

**Examples**:
| Input | Output | Reason |
|-------|--------|--------|
| `"3A"` | `True` | m_num → 3 ≠ 0 |
| `"A3"` | `False` | m_num → 0 = 0 |
| `""` | `False` | m_num → 0 = 0 |
| `"1"` | `True` | m_num → 1 ≠ 0 |

### m_compare(a: str, op: str, b: str) -> int

**Purpose**: M comparison with coercion

**Algorithm**:
1. Convert both values: `m_num(a)`, `m_num(b)`
2. Apply operator and return 1 (true) or 0 (false)

**Operators** (Spec 004 scope):
| Op | Meaning |
|----|---------|
| `=` | Equals (string equality for non-numeric, numeric for numeric context) |
| `<` | Less than (numeric) |
| `>` | Greater than (numeric) |

## ASG Nodes Consumed (Existing)

Spec 004 codegen consumes these existing ASG types without modification:

### Expressions
- `MNumericLiteral` - integer literals
- `MStringLiteral` - string literals  
- `MLocalVariable` - local variable reference
- `MBinaryExpr` - binary operation (left, op, right)
- `MUnaryExpr` - unary operation (op, operand)

### Statements
- `MSetStatement` - SET command
- `MWriteStatement` - WRITE command
- `MQuitStatement` - QUIT command
- `MIfStatement` - IF command
- `MElseStatement` - ELSE command
- `MForStatement` - FOR command (all loop types)
- `MDoStatement` - DO command
- `MGotoStatement` - GOTO command

### Structural
- `MRoutine` - top-level routine
- `MLabel` - label definition
- `MScope` - block scope (dot blocks)

## Relationships Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Code Generation Flow                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  MUMPS Source ──► Parser ──► ASG ──► CodeGenerator ──► Python  │
│                                          │                      │
│                                          ├── NameTranslator     │
│                                          └── Coercion Helpers   │
│                                                                 │
│  Python Code ──► MUMPSRuntime ──► ExecutionResult               │
│                      │                                          │
│                      ├── _variables                             │
│                      ├── _output                                │
│                      └── _test                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Migration Notes

This is the first codegen spec - no migration needed. The `src/m2py/codegen/` and `src/m2py/runtime/` directories are new.
