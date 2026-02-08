# Variable System

## Overview

The unified variable system provides consistent semantics for variable access across:
- Compile-time (direct variable references like `S A=1`)
- Runtime (indirection like `S @X=1` where X="A")

Both paths produce identical behavior through shared canonicalization and resolution logic
in the `src/m2py/core/` module.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        Unified Variable System                              │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         core/ Module                                 │   │
│  │   NameTranslator ← Bidirectional name translation                   │   │
│  │   SubscriptCanonicalizer ← Subscript normalization                  │   │
│  │   CurrentScope ← Unified variable access abstraction                │   │
│  │   IndirectionResolver ← Runtime @-expression resolution             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                    ▲                                        │
│                      ┌─────────────┴─────────────┐                          │
│                      │                           │                          │
│               ┌──────┴──────┐             ┌──────┴──────┐                   │
│               │   codegen/  │             │   runtime/  │                   │
│               │  (compile)  │             │ (execution) │                   │
│               └─────────────┘             └─────────────┘                   │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. NameTranslator (`src/m2py/core/names.py`)

Translates between MUMPS and Python identifiers:
- `%` prefix → `_pct_` prefix
- Reserved words → `_m_` prefix
- Numeric-starting names → `_n_` prefix

```python
from m2py.core.names import NameTranslator, translate_name

# MUMPS → Python
translate_name("%ZU")   # → "_pct_ZU"
translate_name("for")   # → "_m_for"
translate_name("01")    # → "_n_01"

# Python → MUMPS
NameTranslator.from_python("_pct_ZU")  # → "%ZU"

# Validation
NameTranslator.is_valid_mumps_name("ABC")   # → True
NameTranslator.is_valid_mumps_name("1ABC")  # → False
```

### 2. SubscriptCanonicalizer (`src/m2py/core/subscripts.py`)

Normalizes subscript values for consistent storage and lookup:
- Numeric strings canonicalized: "01.00" → "1"
- Trailing zeros removed: "1.50" → "1.5"
- String subscripts preserved: "01" stays "01"

```python
from m2py.core.subscripts import SubscriptCanonicalizer

# Numeric canonicalization
SubscriptCanonicalizer.canonicalize(01.00)   # → "1"
SubscriptCanonicalizer.canonicalize("1.50")  # → "1.5"

# String preservation (important!)
SubscriptCanonicalizer.canonicalize("01")    # → "01" (not "1")
SubscriptCanonicalizer.canonicalize("hello") # → "hello"

# Check if numeric string is canonical
SubscriptCanonicalizer.is_canonical_numeric_string("1")   # → True
SubscriptCanonicalizer.is_canonical_numeric_string("01")  # → False

# Subscript equality
SubscriptCanonicalizer.subscripts_equal(1, "1")   # → True
SubscriptCanonicalizer.subscripts_equal(1, "01")  # → False
```

### 3. CurrentScope (`src/m2py/core/scope.py`)

Unified scope abstraction for variable access:
- Works with generated code's `_scope` dictionary
- Handles MArray value extraction automatically
- Provides consistent get/set/exists/kill operations

```python
from m2py.core.scope import CurrentScope

cs = CurrentScope.from_generated_context(_scope)

# Simple variable access
cs.set("X", 5)
value = cs.get("X")              # → 5
value = cs.get("Y", default="")  # → "" (if undefined)

# Subscripted access
cs.set_subscripted("A", [1, 2], "hello")
value = cs.get_subscripted("A", [1, 2])  # → "hello"

# Existence check
if cs.exists("X"):
    ...

# Kill variable and descendants
cs.kill("A")      # Removes A, A(1), A(1,2), etc.
cs.kill("A(1)")   # Removes A(1), A(1,1), etc.
```

### 4. IndirectionResolver (`src/m2py/core/indirection.py`)

Resolves indirection at runtime with context-aware behavior:
- **NAME context**: Returns variable name (for SET targets)
- **VALUE context**: Returns variable value (for expressions)
- **ARGUMENT context**: Evaluates expression (for IF conditions)

```python
from m2py.core.indirection import IndirectionResolver, IndirectionContext

resolver = IndirectionResolver(state, scope)

# @X where X="Y" - get name "Y" for SET target
name = resolver.resolve("X", levels=1, context=IndirectionContext.NAME)

# @X where X="Y", Y=42 - get value 42
value = resolver.resolve("X", levels=1, context=IndirectionContext.VALUE)

# I @A where A="1=0" - evaluates to 0 (FALSE)
result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
```

## Key Behaviors

### Argument Indirection Expression Evaluation

`I @A` where `A="1=0"` evaluates to FALSE. The string "1=0" is parsed as an
expression (1≠0 → 0), not treated as a truthy string.

### Subscript Evaluation in Indirection Strings

`@X` where `X="A(AA)"` evaluates AA as a variable reference. If AA=11, this
resolves to `A(11)`, not literal `A("AA")`.

### Per-Level Subscript Merging

`@A@(1)` where `A="B(2,3)"` produces `B(2,3,1)` (subscripts merged),
not `B(2,3)(1)` (invalid subscript syntax).

## Generated Code Integration

The unified components integrate with generated code through runtime methods:

```python
# FOR loop with indirection
_for_indirect_var = _rt.resolve_for_target("A", _scope, levels=1)

# SET with indirection  
_rt.set_indirected("A", value, _scope, levels=1)

# IF with argument indirection
result = _rt.evaluate_argument_indirection("A", _scope, levels=1)

# SET $PIECE with subscript indirection
_rt.resolve_for_target("A", _scope, levels=1, per_level_subscripts=[[1]])
```

## Test Coverage

- **Unit tests**: `tests/unit/core/test_*.py` - Core component tests
- **Integration tests**: `tests/integration/test_indirection_*.py` - End-to-end indirection
- **MUGJ validation**: V1IDNM, V1IDARG, V1IDDO, V1IDGO, V1XECA tests
- **Complex patterns**: VV2VNIA, VV2VNIB, VV2VNIC multi-level indirection tests

## Related Documentation

- [Architecture: core/ Module](../architecture.md#core-module) - Module structure and purpose
- [quickstart.md](../../specs/018-unified-variable-system/quickstart.md) - Usage examples
- [research.md](../../specs/018-unified-variable-system/research.md) - MUMPS semantics research
