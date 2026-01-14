# Quickstart: LHS Functions & Global Variables (Spec 009)

This guide covers implementing and using the new features added in Spec 009.

## Prerequisites

- Spec 008 complete (`_scope` dictionary for local variable visibility)
- MArray class exists in `m2py.runtime`
- Parser captures GlobalVariable, NakedGlobal, IntrinsicFunction nodes

## Quick Test Commands

After implementation, verify with:

```bash
# LHS $PIECE
uv run python utils/validate.py --code 'TEST S X="A^B^C" S $P(X,"^",2)="NEW" W X,! Q'
# Expected: A^NEW^C

# LHS $EXTRACT  
uv run python utils/validate.py --code 'TEST S X="HELLO" S $E(X,2,3)="XX" W X,! Q'
# Expected: HXXLO

# Subscripted locals
uv run python utils/validate.py --code 'TEST S X(1)=1,X(1,2)=3 W X(1),"-",X(1,2),! Q'
# Expected: 1-3

# Global variables
uv run python utils/validate.py --code 'TEST S ^G("a")=1 W ^G("a"),! Q'
# Expected: 1

# Naked references
uv run python utils/validate.py --code 'TEST S ^G(1)=1,^(2)=2 W ^(2),! Q'
# Expected: 2

# $DATA
uv run python utils/validate.py --code 'TEST S X(1)=1,X(1,2)=3 W $D(X),"-",$D(X(1)),"-",$D(X(1,2)),! Q'
# Expected: 10-11-1

# KILL
uv run python utils/validate.py --code 'TEST S X=1,X(1)=2 K X(1) W $D(X),"-",$D(X(1)),! Q'
# Expected: 1-0
```

## New Runtime Components

### GlobalStorageBackend

```python
from m2py.runtime.globals import InMemoryGlobalStorage

# Create storage
storage = InMemoryGlobalStorage()

# Use it
storage.set("PATIENT", ("12345", "NAME"), "John Doe")
value = storage.get("PATIENT", ("12345", "NAME"))  # "John Doe"
data_code = storage.data("PATIENT", ("12345",))    # 11 (has value and children)
```

### MArray $DATA

```python
from m2py.runtime import MArray

arr = MArray()
arr.value = "root"
arr["child"] = MArray(value="child_val")

print(arr.data())  # 11 - has value AND children
print(arr["child"].data())  # 1 - has value, no children
print(arr["missing"].data())  # 0 - undefined
```

### Runtime Helpers

```python
from m2py.runtime.helpers import m_set_piece, m_set_extract, m_data

# LHS $PIECE example
current = "A^B^C"
def setter(v): global current; current = v
m_set_piece(lambda: current, setter, "^", 2, None, "NEW")
print(current)  # A^NEW^C
```

## Codegen Patterns

### Before Spec 009

```python
# S X=1 generated as:
_scope['X'] = 1
```

### After Spec 009

```python
# S X(1,2)=5 generates:
_scope.setdefault('X', MArray())[1, 2] = 5

# S ^G("a")=1 generates:
_rt.globals.set("G", ("a",), "1")

# S $P(X,"^",2)="NEW" generates:
m_set_piece(
    lambda: _scope.get('X', MArray()).value or '',
    lambda v: _scope.setdefault('X', MArray()).__setattr__('value', v),
    '^', 2, None, 'NEW'
)
```

## Running Tests

```bash
# Run spec 009 tests
uv run pytest tests/test_spec_009*.py -v

# Run all tests with coverage
uv run pytest --cov=src/m2py --cov-report=term-missing
```

## Troubleshooting

### "NAKEDERR: Naked reference without prior global access"

A naked reference `^(subscripts)` was used before any global variable access.

```mumps
; Wrong - naked before global access:
TEST S ^(1)=5

; Correct - global access first:
TEST S ^G(1)=1,^(2)=2
```

### "Unsupported SET target type"

The codegen encountered a target type not yet implemented. Check:
- Is target a GlobalVariable? → Implement global codegen
- Is target an IntrinsicFunction? → Check if it's $PIECE or $EXTRACT
- Is target a NakedGlobal? → Implement naked reference codegen

### $DATA returns unexpected value

Remember the return codes:
- `0` = undefined, no children
- `1` = defined, no children
- `10` = undefined at this node, but has children
- `11` = defined AND has children

## What's NOT in Spec 009

- `$ORDER`, `$QUERY` (iteration functions)
- `$GET` (value with default)
- `MERGE` command
- Exclusive `NEW`/`KILL` (`NEW (X,Y)`, `KILL (X)`)
- Variable indirection (`@variable`)
- Multidimensional $PIECE (`$P(X,"^",2,5)` range)
- Lock commands

These will be addressed in future specs.
