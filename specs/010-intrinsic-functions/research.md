# Research: Intrinsic Functions

**Spec**: 010-intrinsic-functions | **Date**: 2026-01-14

## Research Tasks

### 1. Current ASG Infrastructure for Intrinsic Functions

**Finding**: MIntrinsicFunction is fully defined in `src/m2py/asg/expressions.py`:
```python
@dataclass
class MIntrinsicFunction(MExpr):
    name: str = ""  # Function name without $
    arguments: List["MExpr"] = field(default_factory=list)
```

**Finding**: MSelectArg exists for $SELECT condition:value pairs:
```python
@dataclass
class MSelectArg(ASGElement):
    condition: Optional["MExpr"] = None
    value: Optional["MExpr"] = None
```

**Finding**: Parser already produces MIntrinsicFunction nodes with correct structure. Custom classes in `textx_classes.py`:
- `IntrinsicFunction` → general intrinsic functions
- `IntrinsicFunctionNoArgs` → no-argument intrinsics
- `SelectFunction` → $SELECT with MSelectArg handling
- `TextFunction` → $TEXT with line_ref handling (already implemented in Spec 008)

### 2. Current Codegen Expression Handling

**Finding**: `generate_expr()` in `expressions.py` currently handles:
- MLiteral, MVariable, GlobalVariable, NakedGlobal
- MBinaryOp, MUnaryOp, MExtrinsicFunction, MSpecialVariable
- $DATA (partial - special case for IntrinsicFunction)
- $TEXT (special case for TextFunction)

**Gap**: No general MIntrinsicFunction dispatch. Need to add dispatcher for all intrinsic functions.

**Decision**: Add function dispatch table mapping function names to generator functions. Pattern from docs/codegen/functions.md:
```python
FUNCTION_MAP = {
    "L": "_gen_length", "LENGTH": "_gen_length",
    "P": "_gen_piece", "PIECE": "_gen_piece",
    # ... etc
}
```

### 3. Runtime Helper Strategy

**Finding**: `runtime/helpers.py` already has:
- `m_set_piece()` - LHS $PIECE (Spec 009)
- `m_set_extract()` - LHS $EXTRACT (Spec 009)
- `m_data()` - $DATA for local arrays
- `m_data_global()` - $DATA for global variables

**Decision**: Add new helpers for complex functions:

| Function | Strategy | Notes |
|----------|----------|-------|
| $LENGTH | Inline | `len(x)` or `x.count(d) + 1` |
| $PIECE | Helper | Edge cases require careful handling |
| $EXTRACT | Helper | Edge cases for padding, negative indices |
| $FIND | Helper | Returns position AFTER match, 1-based |
| $TRANSLATE | Inline | Python `str.translate()` with maketrans |
| $JUSTIFY | Inline | Python f-string formatting |
| $ASCII | Inline | `ord(x[pos-1])` with bounds checking |
| $CHAR | Inline | `chr()` with edge case handling |
| $REVERSE | Inline | `x[::-1]` |
| $FNUMBER | Helper | Complex formatting codes |
| $RANDOM | Inline | `random.randint(0, n-1)` with error check |
| $DATA | Helper | Already exists (Spec 009) |
| $GET | Helper | Variable existence check with default |
| $ORDER | Helper | Next subscript in collation order |
| $QUERY | Helper | Full reference of next node |
| $NAME | Helper | Convert variable reference to string |
| $QLENGTH | Helper | Count subscripts in name string |
| $QSUBSCRIPT | Helper | Extract subscript from name string |
| $SELECT | Inline | Chained conditional expression |

### 4. Error Handling Strategy

**Decision**: Create `MRuntimeError` exception class in `runtime/exceptions.py`:
```python
class MRuntimeError(Exception):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(f"M-{code}: {message}" if message else f"M-{code}")
```

Used for:
- `SELECTFALSE` - $SELECT with no true condition
- `RANDARGNEG` - $RANDOM(0) or negative argument

### 5. $CHAR Edge Cases (YottaDB Validated)

**Tested behavior**:
- `$C(256)` → "Ā" (Unicode chr(256))
- `$C(-1)` → "" (empty string)
- `$A($C(-1))` → -1 (empty string ASCII)

**Decision**: Match YottaDB - use Python chr() for ≥0, return "" for negative codes.

### 6. Extrinsic Function Infrastructure

**Finding**: `_generate_extrinsic()` already exists and handles:
- Internal calls: `_call_extrinsic(_rt, func, args)`
- External calls: `_call_extrinsic(_rt, module.func, args, _scope=_scope)`
- $TEST save/restore is handled by `_call_extrinsic` helper

**Gap**: By-reference parameter passing for extrinsics not fully implemented.
Per spec FR-024: "System MUST support by-value and by-reference parameter passing for extrinsics"

**Decision**: Extend `_generate_extrinsic_arguments()` to handle PassingMode.BY_REFERENCE.

### 7. Offset Evaluator Upgrade

**Requirement**: FR-028 - "Computed offset expressions MUST support intrinsic function calls"

Example: `G LABEL+$L(X)` - GOTO with computed offset using $LENGTH

**Finding**: Current offset evaluator in codegen handles simple expressions. Need to extend to call `generate_expr()` for complex expressions including intrinsic functions.

**Decision**: Modify offset expression handling to use full expression generator.

### 8. Validation Test Coverage

**MUGJ test files for intrinsic functions**:
- `V1FN.m` - Driver for all function tests
- `V1FNE1.m`, `V1FNE2.m` - $EXTRACT tests
- `V1FNF1.m`, `V1FNF2.m`, `V1FNF3.m` - $FIND tests
- `V1FNL.m` - $LENGTH tests
- `V1FNP1.m`, `V1FNP2.m` - $PIECE tests
- `VV2FN1.m`, `VV2FN2.m` - Additional function tests

**Success criterion**: All V1FN* tests pass with matching YottaDB output.

## Decisions Summary

| Decision | Rationale | Alternatives Rejected |
|----------|-----------|----------------------|
| Function dispatch table | Clean, extensible, matches docs pattern | Giant if/elif chain |
| Inline for simple functions | Constitution VII - minimize runtime | All functions in runtime |
| Helper functions for complex | Separation of concerns, testability | Inline everything |
| MRuntimeError exception | Clean error identification | Generic Exception |
| Match YottaDB for $CHAR edge cases | Constitution II - YDB as reference | Python ValueError |
| Extend extrinsic arguments | Complete by-ref support | Defer to later spec |

## Implementation Priority

1. **String functions** (P1) - $LENGTH, $PIECE, $EXTRACT - most commonly used
2. **Data functions** (P1) - $DATA, $GET, $ORDER - essential for array handling
3. **Conditional** (P1) - $SELECT - heavily used for conditionals
4. **Extrinsic** (P1) - $$label - code organization
5. **Other string** (P2) - $FIND, $TRANSLATE, $ASCII, $CHAR, $JUSTIFY, $REVERSE, $FNUMBER
6. **Numeric** (P2) - $RANDOM
7. **Array traversal** (P2) - $QUERY
8. **Array utilities** (P3) - $NAME, $QLENGTH, $QSUBSCRIPT
9. **Offset evaluator** - Cross-cutting, do last

## Open Questions

None - all clarifications resolved in spec.md.
