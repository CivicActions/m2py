# Data Model: Codegen Refactoring (Phase 2)

**Branch**: `020-codegen-refactoring` | **Date**: 2026-02-10

## Overview

Phase 2 is a refactoring effort — it restructures existing code without changing
external behavior (with two exceptions: C-09 ZWRITE fix and C-07 by-ref fix).
The data model changes are minimal: one new ASG dataclass, one new ASG field,
and removal of deprecated fields.

## New Entities

### MLockTarget (ASG Dataclass)

Replaces untyped `dict` objects in `MLockStatement.targets: List[Any]`.

```python
@dataclass
class MLockTarget(ASGElement):
    """A single lock target in a LOCK statement."""
    name: Optional[str] = None               # Variable name (e.g., "A", "^G")
    subscripts: List["MExpr"] = field(default_factory=list)
    is_global: bool = False                   # True for ^NAME
    lockop: str = ""                          # "", "+", "-"
    timeout: Optional["MExpr"] = None         # Per-target timeout
    postcondition: Optional["MExpr"] = None   # Per-target postcondition
    is_indirect: bool = False                 # True for @NAME
    indirection: Optional["MExpr"] = None     # Indirection expression
    indirection_levels: int = 0               # Indirection nesting depth
```

**Validation rules**: If `is_indirect` is True, `name` may be None (resolved at runtime).

### MStatement.comment Field

New optional field on the ASG base class:

```python
@dataclass
class MStatement(ASGElement):
    scope: Optional[MScope] = field(default=None, repr=False)
    postcondition: Optional["MExpr"] = None
    is_unreachable: bool = False
    comment: Optional[str] = None            # NEW: inline MUMPS comment text
    _dot_level: int = field(default=0, repr=False)
```

**Population**: Extracted during parsing in `parser/textx_classes.py` or `parser/line_parser.py`.

## Modified Entities

### MIfStatement — Remove `condition`

```python
# BEFORE
@dataclass
class MIfStatement(MStatement):
    condition: Optional["MExpr"] = None    # REMOVE
    conditions: List["MExpr"] = field(default_factory=list)
    then_scope: MScope = field(default_factory=MScope)

# AFTER
@dataclass
class MIfStatement(MStatement):
    conditions: List["MExpr"] = field(default_factory=list)
    then_scope: MScope = field(default_factory=MScope)
    restructurable_goto: Optional["MGotoStatement"] = field(default=None, repr=False)
```

### MHangStatement — Remove `duration`

```python
# BEFORE
@dataclass
class MHangStatement(MStatement):
    duration: Optional["MExpr"] = None     # REMOVE
    durations: List["MExpr"] = field(default_factory=list)

# AFTER
@dataclass
class MHangStatement(MStatement):
    durations: List["MExpr"] = field(default_factory=list)
```

### MXecuteStatement — Remove `code_expressions`

```python
# BEFORE
@dataclass
class MXecuteStatement(MStatement):
    arguments: List[MXecuteArg] = field(default_factory=list)
    code_expressions: List["MExpr"] = field(default_factory=list)  # REMOVE
    is_constant: bool = False
    constant_values: List[str] = field(default_factory=list)

# AFTER
@dataclass
class MXecuteStatement(MStatement):
    arguments: List[MXecuteArg] = field(default_factory=list)
    is_constant: bool = False
    constant_values: List[str] = field(default_factory=list)
```

### MLockStatement — Type `targets`

```python
# BEFORE
@dataclass
class MLockStatement(MStatement):
    targets: List[Any] = field(default_factory=list)

# AFTER
@dataclass
class MLockStatement(MStatement):
    targets: List[MLockTarget] = field(default_factory=list)
```

## New Modules

### codegen/var_access.py

New module encapsulating 3-way strategy dispatch:

```python
"""Variable access helpers for codegen strategy dispatch.

Centralizes the TRAMPOLINE+dynamic_locals / TRAMPOLINE+static / SIMPLE_FUNCTIONS
dispatch pattern used ~69 times across codegen.
"""

def var_read_expr(var_name: str, ctx: "GeneratorContext") -> str:
    """Generate expression to read a local variable's value."""

def var_write_stmt(var_name: str, value_expr: str, ctx: "GeneratorContext") -> str:
    """Generate statement to write a value to a local variable."""

def var_base_expr(var_name: str, ctx: "GeneratorContext") -> str:
    """Generate expression for the base MArray/dict of a local variable."""
```

### No New Runtime Entities

The runtime changes are extensions to existing functions (`zwrite_local`, `zwrite_global`)
and modifications to call-site generation patterns. No new runtime classes are introduced.

## Relationships

```text
MStatement (base)
├── comment: Optional[str]        # NEW field (S-19)
├── MIfStatement
│   └── conditions: List[MExpr]   # Only field (condition removed, S-16)
├── MHangStatement
│   └── durations: List[MExpr]    # Only field (duration removed, S-16)
├── MLockStatement
│   └── targets: List[MLockTarget]  # Typed (S-16)
│       └── MLockTarget            # NEW dataclass (S-16)
└── MXecuteStatement
    └── arguments: List[MXecuteArg]  # Only field (code_expressions removed, S-16)
```
