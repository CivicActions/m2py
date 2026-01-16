# Data Model: Extended Operators, Commands & Completion

**Feature**: Spec 011 - Extended Operators, Commands & Completion
**Date**: 2026-01-15

## Existing Entities (from previous specs)

### MBinaryOp (ASG - expressions.py)
Binary operation expression with operator, left, and right operands.

**Spec 011 additions** to supported operators:
- `&` - Logical AND
- `!` - Logical OR
- `[` - Contains
- `]` - Follows
- `]]` - Sorts after (strictly)
- `?` - Pattern match

### MUnaryOp (ASG - expressions.py)
Unary operation expression with operator and operand.

**Spec 011 fix**: NOT (`'`) must return `int` (0/1), not Python `bool`.

### MFormatControl (ASG - expressions.py)
Format control element in WRITE/READ arguments.

| Field | Type | Description |
|-------|------|-------------|
| `control_type` | `FormatControlType` | Type of format control |
| `argument` | `Optional[MExpr]` | Expression for TAB/CHARCODE |

### FormatControlType (ASG - enums.py)
Enum for format control types:
- `NEWLINE` - `!`
- `FORMFEED` - `#`
- `TAB` - `?n`
- `CHARCODE` - `*n`

### MStatement (ASG - statements.py)
Base class for all statements.

| Field | Type | Description |
|-------|------|-------------|
| `postcondition` | `Optional[MExpr]` | Condition for conditional execution |

### MSpecialVariable (ASG - expressions.py)
Special variable reference ($HOROLOG, $JOB, etc.)

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Variable name without $ prefix |

## New Entities

### SpecialVariableType (optional - enums.py)

> **Note**: This enum is optional. The codegen can use string matching on `MSpecialVariable.name` instead. Only create if enum-based dispatch improves maintainability.

Enum for special variable classification:

```python
class SpecialVariableType(Enum):
    # Already implemented (Spec 005)
    TEST = auto()       # $TEST / $T
    
    # Spec 011 additions
    HOROLOG = auto()    # $HOROLOG / $H
    JOB = auto()        # $JOB / $J
    IO = auto()         # $IO
    STORAGE = auto()    # $STORAGE / $S
    STACK = auto()      # $STACK / $ST
    QUIT = auto()       # $QUIT / $Q
    X = auto()          # $X - column position
    Y = auto()          # $Y - line position
```

Note: Special variable names have abbreviations (e.g., $H for $HOROLOG).

## Runtime State Extensions

### MUMPSRuntime (runtime/__init__.py)

**New fields for Spec 011**:

```python
class MUMPSRuntime:
    # Existing fields...
    
    # Column/line tracking for $X, $Y
    _x: int = 0  # Current column position
    _y: int = 0  # Current line position
    
    # Call stack tracking for $STACK
    _stack_level: int = 0
    
    # Extrinsic context for $QUIT
    _in_extrinsic: bool = False
```

### New Runtime Helpers (runtime/helpers.py)

**m_contains(haystack, needle) -> int**
Check if needle is substring of haystack.

**m_follows(a, b) -> int**
Check if a sorts after b in ASCII order.

**m_sorts_after(a, b) -> int**
Check if a strictly sorts after b (empty string never sorts after).

**m_pattern_match(string, pattern) -> int**
Match string against MUMPS pattern using compiled regex.

**m_horolog() -> str**
Return current date/time in MUMPS $HOROLOG format.

**m_read(timeout=None) -> str**
Read input with optional timeout, set $TEST.

## Relationships

```
MWriteStatement.arguments → [MExpr | MFormatControl]
                                      ↓
                              FormatControlType
                              - NEWLINE
                              - FORMFEED
                              - TAB (+ argument)
                              - CHARCODE (+ argument)

MStatement.postcondition → MExpr (condition to evaluate)

MSpecialVariable.name → maps to SpecialVariableType
                       → generates runtime access

MBinaryOp.operator → extended operator set
                     &, !, [, ], ]], ?
                     → generates helper calls
```

## Validation Rules

1. **Format controls in WRITE**: Only valid as WRITE arguments
2. **Postcondition expressions**: Must evaluate to truth value
3. **Pattern match patterns**: Must be valid MUMPS pattern syntax
4. **$X/$Y tracking**: Updated by all write operations
5. **$QUIT context**: Only meaningful inside extrinsic functions
