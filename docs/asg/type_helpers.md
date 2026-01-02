# ASG Type Helpers

This document describes the type narrowing utilities provided for working with ASG types in a type-safe manner.

**Source**: [`src/m2py/asg/type_helpers.py`](../../src/m2py/asg/type_helpers.py)

---

## Purpose

MUMPS statement types have different attributes depending on their kind:
- `MForStatement` has a `body` attribute
- `MIfStatement` has a `then_scope` attribute
- `MElseStatement` has a `body` attribute

When iterating over statements generically, pyright (the type checker) doesn't know which attributes are available. The type helpers provide:

1. **TypeGuard functions**: Narrow the type so pyright knows what attributes exist
2. **Accessor functions**: Safely extract optional nested scopes

---

## TypeGuard Functions

### has_body

Checks if a statement has a `body` attribute (MScope):

```python
from m2py.asg.type_helpers import has_body

for stmt in scope.walk_statements():
    if has_body(stmt):
        # pyright now knows: stmt is MForStatement | MDoStatement | MElseStatement
        for inner_stmt in stmt.body.statements:
            process(inner_stmt)
```

**Applies to**: `MForStatement`, `MDoStatement`, `MElseStatement`

### has_then_scope

Checks if a statement has a `then_scope` attribute:

```python
from m2py.asg.type_helpers import has_then_scope

for stmt in scope.walk_statements():
    if has_then_scope(stmt):
        # pyright now knows: stmt is MIfStatement
        for inner_stmt in stmt.then_scope.statements:
            process(inner_stmt)
```

**Applies to**: `MIfStatement`

---

## Accessor Functions

These functions safely extract nested scopes without type errors:

### get_body_scope

Get the body scope if present:

```python
from m2py.asg.type_helpers import get_body_scope

for stmt in scope.walk_statements():
    body = get_body_scope(stmt)
    if body is not None:
        # body is MScope
        for inner_stmt in body.statements:
            process(inner_stmt)
```

**Returns**: `MScope | None`

### get_then_scope

Get the then_scope if present:

```python
from m2py.asg.type_helpers import get_then_scope

for stmt in scope.walk_statements():
    then_scope = get_then_scope(stmt)
    if then_scope is not None:
        # then_scope is MScope
        for inner_stmt in then_scope.statements:
            process(inner_stmt)
```

**Returns**: `MScope | None`

### get_else_scope

Looks for an `else_scope` attribute and returns it when present. Currently no ASG statement type defines an `else_scope` attribute - in MUMPS, ELSE is a separate command that checks `$TEST` rather than being structurally linked to IF. `MElseStatement` uses `body`, not `else_scope`. This helper is provided for future extensibility and currently always returns None.

```python
from m2py.asg.type_helpers import get_else_scope

# Currently returns None - no statement defines else_scope
for stmt in scope.walk_statements():
    else_scope = get_else_scope(stmt)
    if else_scope is not None:
        for inner_stmt in else_scope.statements:
            process(inner_stmt)
```

**Returns**: `MScope | None` (currently always `None`)

---

## Usage in MScope.walk_statements

The `walk_statements()` method uses these helpers internally for recursive traversal:

```python
# From src/m2py/asg/elements.py
def walk_statements(self) -> Iterator["MStatement"]:
    from m2py.asg.type_helpers import get_body_scope, get_else_scope, get_then_scope

    for stmt in self.statements:
        yield stmt
        
        # Recurse into nested scopes using type-safe helpers
        body = get_body_scope(stmt)
        if body is not None:
            yield from body.walk_statements()
            
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            yield from then_scope.walk_statements()
            
        else_scope = get_else_scope(stmt)
        if else_scope is not None:
            yield from else_scope.walk_statements()
```

---

## Type Aliases

The module defines type aliases for statement categories:

```python
StatementWithBody = Union[MForStatement, MDoStatement, MElseStatement]
StatementWithThenScope = Union[MIfStatement]
StatementWithScopes = Union[MIfStatement, MElseStatement]
```

These can be used for type annotations:

```python
def process_loop_body(stmt: StatementWithBody) -> None:
    for inner in stmt.body.statements:
        ...
```

---

## Why Use These Helpers?

Without type helpers, you'd need explicit type checks:

```python
# Without helpers - more verbose, less maintainable
from m2py.asg.statements import MForStatement, MIfStatement, MDoStatement

for stmt in scope.walk_statements():
    if isinstance(stmt, MForStatement):
        for inner in stmt.body.statements:
            process(inner)
    elif isinstance(stmt, MIfStatement):
        for inner in stmt.then_scope.statements:
            process(inner)
    # ... etc
```

With type helpers:

```python
# With helpers - cleaner, more generic
from m2py.asg.type_helpers import get_body_scope, get_then_scope

for stmt in scope.walk_statements():
    for scope_getter in [get_body_scope, get_then_scope]:
        nested = scope_getter(stmt)
        if nested:
            for inner in nested.statements:
                process(inner)
```

---

## Best Practices

1. **Use walk_statements() when possible**: It handles all nested scopes automatically
2. **Use accessor functions for null-safety**: They return None instead of raising errors
3. **Use TypeGuards for type narrowing**: When you need pyright to know the exact type
4. **Avoid hasattr() directly**: Use the provided helpers for consistency
