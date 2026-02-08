# Quickstart: Unified Variable System

This guide shows how to use the unified variable system components after implementation.

## 1. Name Translation

Translate MUMPS names to/from Python identifiers:

```python
from m2py.core.names import NameTranslator

# MUMPS → Python
py_name = NameTranslator.to_python("%FOO")  # → "_pct_FOO"
py_name = NameTranslator.to_python("if")    # → "_m_if"
py_name = NameTranslator.to_python("01")    # → "_n_01"

# Python → MUMPS (for runtime parsing)
mumps_name = NameTranslator.from_python("_pct_FOO")  # → "%FOO"

# Validation
if NameTranslator.is_valid_mumps_name(user_input):
    # Safe to use as variable name
    ...
```

## 2. Subscript Canonicalization

Ensure subscripts are in canonical form:

```python
from m2py.core.subscripts import SubscriptCanonicalizer

# Numeric canonicalization
key = SubscriptCanonicalizer.canonicalize(01)    # → "1"
key = SubscriptCanonicalizer.canonicalize(1.0)   # → "1"
key = SubscriptCanonicalizer.canonicalize(1.50)  # → "1.5"

# String handling
key = SubscriptCanonicalizer.canonicalize("1")   # → "1" (numeric)
key = SubscriptCanonicalizer.canonicalize("01")  # → "01" (preserved!)
key = SubscriptCanonicalizer.canonicalize("1X")  # → "1X" (preserved)

# Check if subscripts refer to same node
same = SubscriptCanonicalizer.subscripts_equal(1, "1")    # True
same = SubscriptCanonicalizer.subscripts_equal(1, "01")   # False!
```

## 3. Unified Scope Access

Access variables consistently across all code paths:

```python
from m2py.core.scope import CurrentScope

# In generated code
def MY_ROUTINE(_rt, _scope=None, _test=False):
    _scope = _scope if _scope is not None else {}
    cs = CurrentScope.from_generated_context(_scope)
    
    # Get/set variables
    cs.set("X", 5)
    value = cs.get("Y", default="")
    
    # Subscripted access
    cs.set_subscripted("A", [1, 2], "hello")
    value = cs.get_subscripted("A", [1, 2])
    
    # Check existence
    if cs.exists("X"):
        ...
    
    # Kill (remove variable and descendants)
    cs.kill("A(1)")  # Removes A(1), A(1,1), etc.
```

## 4. Indirection Resolution

Resolve @-expressions at runtime:

```python
from m2py.core.indirection import IndirectionResolver, IndirectionContext

# Create resolver with state and scope
resolver = IndirectionResolver(state, current_scope)

# Simple name indirection: @X where X="Y", Y=5
value = resolver.resolve("X", levels=1, context=IndirectionContext.NAME)
# → 5 (looked up Y)

# Multi-level: @@X where X="Y", Y="Z", Z=99
value = resolver.resolve("X", levels=2, context=IndirectionContext.NAME)
# → 99 (resolved X→Y→Z, returned value of Z)

# With subscripts: @X@(1,2) where X="A", A(1,2)="hello"
value = resolver.resolve(
    "X", 
    levels=1, 
    context=IndirectionContext.NAME,
    per_level_subscripts=[[(1, 2)]]
)
# → "hello"

# Argument indirection: @A where A="1=0" (IF context)
result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
# → False (evaluates "1=0" as expression)

# Argument with variable reference: @A where A="X>5", X=10
result = resolver.resolve("A", levels=1, context=IndirectionContext.ARGUMENT)
# → True (evaluates "X>5" with current scope)
```

## 5. Codegen Integration

### Static Variable Access

For statically-resolvable references, generate direct Python:

```python
# MUMPS: S X=5
# Generated: X = 5

# MUMPS: S A(1,2)=5  
# Generated: 
if "A" not in _scope:
    _scope["A"] = MArray()
_scope["A"].set((1, 2), 5)
```

### Dynamic Indirection

For runtime-required indirection, generate resolver calls:

```python
# MUMPS: S @Y=5 (where Y is dynamic)
# Generated:
_resolver = IndirectionResolver(_rt, CurrentScope.from_generated_context(_scope))
_target = _resolver.resolve_name_indirection(Y)
_scope[_target] = 5

# MUMPS: I @A (argument indirection in IF)
# Generated:
_resolver = IndirectionResolver(_rt, CurrentScope.from_generated_context(_scope))
if m_truth(_resolver.resolve_argument_indirection(A)):
    ...
```

## 6. Testing Patterns

### Unit Test for Name Translation

```python
def test_name_translation_round_trip():
    """Verify all MUMPS names survive translation round-trip."""
    names = ["%FOO", "01", "if", "SIMPLE", "A123"]
    for name in names:
        py = NameTranslator.to_python(name)
        back = NameTranslator.from_python(py)
        assert back == name, f"Round-trip failed for {name}"
```

### YDB Validation Test

```python
def test_argument_indirection_expression():
    """I @A where A='1=0' must evaluate expression (false)."""
    code = '''TEST
    S A="1=0"
    I @A W "TRUE"
    E  W "FALSE"
    Q
    '''
    result = validate_with_ydb(code)
    assert result.strip() == "FALSE"
```

### MUGJ-Extracted Test

```python
def test_vv2vnia_ii127_multilevel_subscripts():
    """Multi-level with per-level subscripts (MUGJ VV2VNIA II-127)."""
    # S X="A",A(1,2)="B(3,4)" S @@X@(1,2)@(5,6)=1
    scope = {"X": "A", "A": MArray()}
    scope["A"].set((1, 2), "B(3,4)")
    scope["B"] = MArray()
    
    resolver = IndirectionResolver(state, CurrentScope(scope_dict=scope))
    
    # Should resolve to B(3,4,5,6)
    target = resolver.resolve(
        "X", 
        levels=2,
        context=IndirectionContext.NAME,
        per_level_subscripts=[[(1, 2)], [(5, 6)]]
    )
    
    # The target should be "B(3,4,5,6)" for setting
    # (actual implementation returns the reference to set)
```

## 7. Error Handling

```python
from m2py.runtime.exceptions import VarExpectedError, LVUNDEFError

# Name indirection with invalid result
scope = {"A": "1+1"}  # Not a valid variable name
resolver = IndirectionResolver(state, CurrentScope(scope_dict=scope))

try:
    resolver.resolve("A", 1, IndirectionContext.NAME)
except VarExpectedError as e:
    # e.invalid_name == "2" (result of 1+1)
    print(f"Error: {e.invalid_name} is not a valid variable name")

# Empty string in name context
scope = {"A": ""}
try:
    resolver.resolve("A", 1, IndirectionContext.NAME)
except VarExpectedError:
    # Empty string is not valid variable name
    pass

# Empty string in argument context is OK (evaluates to false)
scope = {"A": ""}
result = resolver.resolve("A", 1, IndirectionContext.ARGUMENT)
assert result == False  # Empty string → 0 → false
```

## 8. Migration Checklist

When migrating a command to use the unified system:

1. **Identify indirection type**: Is it NAME or ARGUMENT context?
2. **Check for static resolution**: Can codegen resolve at compile time?
3. **Generate appropriate code**:
   - Static: Direct Python assignment/access
   - Dynamic: IndirectionResolver call
4. **Update tests**: Add MUGJ-extracted tests for the command
5. **Remove old code**: Delete superseded indirection handling
6. **Run full test suite**: Ensure no regressions
