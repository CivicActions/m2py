# Variable System

## Overview

The unified variable system provides consistent semantics for variable access across:
- Compile-time (direct variable references like `S A=1`)
- Runtime (indirection like `S @X=1` where X="A")

Both paths produce identical behavior through shared canonicalization and resolution logic.

## Core Components

### 1. NameTranslator (`src/m2py/core/names.py`)

Translates between MUMPS and Python identifiers:
- `%` prefix → `_pct_` prefix
- Reserved words → `_m_` prefix

```python
from m2py.core.names import NameTranslator, translate_name

# MUMPS → Python
translate_name("%ZU")  # → "_pct_ZU"
translate_name("for")  # → "_m_for"

# Python → MUMPS
NameTranslator.from_python("_pct_ZU")  # → "%ZU"
```

### 2. SubscriptCanonicalizer (`src/m2py/core/subscripts.py`)

Normalizes subscript values for consistent storage and lookup:
- Numeric strings canonicalized: "01.00" → "1"
- Trailing zeros removed: "1.50" → "1.5"

```python
from m2py.core.subscripts import SubscriptCanonicalizer

SubscriptCanonicalizer.canonicalize("01.00")  # → "1"
SubscriptCanonicalizer.canonicalize("hello")  # → "hello"
```

### 3. CurrentScope (`src/m2py/core/scope.py`)

Unified scope abstraction for variable access:
- Works with generated code's `_scope` dictionary
- Handles MArray value extraction
- Supports all three storage mechanisms (locals, globals, NEW'ed vars)

```python
from m2py.core.scope import CurrentScope

cs = CurrentScope.from_generated_context(_scope)
value = cs.get("A")
cs.set("A", 123)
value = cs.get_subscripted("A", [1, 2])
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

## Generated Code Integration

The unified components integrate with generated code through runtime methods:

```python
# FOR loop with indirection
_for_indirect_var = _rt.resolve_for_target("A", _scope, levels=1)

# SET with indirection  
_rt.set_indirected("A", value, _scope, levels=1)

# IF with argument indirection
result = _rt.evaluate_argument_indirection("A", _scope, levels=1)
```

## Test Coverage

- Unit tests: `tests/unit/core/test_*.py`
- Integration tests: `tests/integration/test_indirection_*.py`
- MUGJ validation tests: V1IDNM, V1IDARG, V1IDDO, V1IDGO, V1XECA
- Complex patterns: VV2VNIA, VV2VNIB, VV2VNIC

## Architecture Notes

Some runtime methods retain alternative implementations for:
1. Backward compatibility with existing generated code
2. Naked global references requiring runtime state tracking
3. Complex edge cases with deeply nested indirection
