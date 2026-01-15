# Quickstart: Intrinsic Functions Implementation

**Spec**: 010-intrinsic-functions | **Date**: 2026-01-14

## Prerequisites

Ensure Spec 009 is complete:
- [X] MArray class in `runtime/__init__.py`
- [X] GlobalStorageBackend protocol in `runtime/globals.py`
- [X] `m_data()` and `m_data_global()` in `runtime/helpers.py`
- [X] Subscripted local variable codegen working

## Implementation Order

### Phase 1: Core Infrastructure

1. **Create exception class**
   - File: `src/m2py/runtime/exceptions.py` (new)
   - Add `MRuntimeError` with code attribute
   - Export from `runtime/__init__.py`

2. **Add intrinsic function dispatcher**
   - File: `src/m2py/codegen/expressions.py`
   - Add `generate_intrinsic_function()` function
   - Add `INTRINSIC_GENERATORS` dispatch table
   - Update `generate_expr()` to dispatch MIntrinsicFunction

### Phase 2: String Functions (P1)

3. **$LENGTH implementation**
   - Simple: `len(string)` for character count
   - Two args: `string.count(delimiter) + 1` for piece count
   - Test: `W $L("HELLO")` → "5"

4. **$PIECE implementation**
   - Add `m_piece()` to `runtime/helpers.py`
   - Generator produces: `m_piece(string, delim, start, end)`
   - Test: `W $P("A^B^C","^",2)` → "B"

5. **$EXTRACT implementation**
   - Add `m_extract()` to `runtime/helpers.py`
   - Generator produces: `m_extract(string, start, end)`
   - Test: `W $E("HELLO",2,4)` → "ELL"

### Phase 3: Data Functions (P1)

6. **$GET implementation**
   - Add `m_get()` to `runtime/helpers.py`
   - Handle undefined variables with default
   - Test: `K X W $G(X,"DEF")` → "DEF"

7. **$DATA extension**
   - Already exists from Spec 009
   - Verify integration with new dispatcher
   - Test: `S A=1 W $D(A)` → "1"

8. **$ORDER implementation**
   - Add `m_order()` to `runtime/helpers.py`
   - Handle forward and reverse direction
   - Test: `S A(1)=1,A(3)=3,A(2)=2 W $O(A(""))` → "1"

### Phase 4: Conditional Function (P1)

9. **$SELECT implementation**
   - Generate chained conditional expression
   - Add `_raise_select_false()` helper inline
   - Handle MSelectArg arguments
   - Test: `W $S(1=1:"YES",1:"NO")` → "YES"

### Phase 5: Extrinsic Functions (P1)

10. **Complete extrinsic support**
    - Review existing `_generate_extrinsic()`
    - Add by-reference parameter handling
    - Verify $TEST save/restore
    - Test: `W $$DBL(21)` with `DBL(N) Q N*2` → "42"

### Phase 6: Remaining String Functions (P2)

11. **$FIND implementation**
    - Add `m_find()` to `runtime/helpers.py`
    - Returns position AFTER match
    - Test: `W $F("HELLO","LL")` → "5"

12. **$TRANSLATE implementation**
    - Use Python `str.translate()` with `str.maketrans()`
    - Handle deletion (missing to-string)
    - Test: `W $TR("HELLO","L")` → "HEO"

13. **$ASCII implementation**
    - Inline: `ord(string[pos-1])` with bounds check
    - Return -1 for invalid positions
    - Test: `W $A("ABC",2)` → "66"

14. **$CHAR implementation**
    - Inline: `chr(code)` for each argument
    - Return "" for negative codes
    - Test: `W $C(65,66,67)` → "ABC"

15. **$JUSTIFY implementation**
    - Use Python f-string formatting
    - Handle decimal places
    - Test: `W $J(12,5)` → "   12"

16. **$REVERSE implementation**
    - Inline: `string[::-1]`
    - Test: `W $RE("HELLO")` → "OLLEH"

17. **$FNUMBER implementation**
    - Add `m_fnumber()` to `runtime/helpers.py`
    - Handle format codes
    - Test: `W $FN(12345.67,",")` → "12,345.67"

### Phase 7: Numeric & Array Functions (P2-P3)

18. **$RANDOM implementation**
    - Inline: `random.randint(0, limit-1)`
    - Raise MRuntimeError for limit ≤ 0
    - Test: `S X=$R(10) W X>=0&(X<10)` → "1"

19. **$QUERY implementation**
    - Add `m_query()` to `runtime/helpers.py`
    - Depth-first traversal
    - Test: `S A(1,1)=1 W $Q(A(""))` → "A(1,1)"

20. **$NAME implementation**
    - Add `m_name()` to `runtime/helpers.py`
    - Test: `S A(1,2,3)=1 W $NA(A(1,2,3))` → "A(1,2,3)"

21. **$QLENGTH implementation**
    - Add `m_qlength()` to `runtime/helpers.py`
    - Test: `W $QL("A(1,2,3)")` → "3"

22. **$QSUBSCRIPT implementation**
    - Add `m_qsubscript()` to `runtime/helpers.py`
    - Test: `W $QS("A(1,2,3)",2)` → "2"

### Phase 8: Offset Evaluator Upgrade

23. **Enable intrinsic functions in computed offsets**
    - Locate offset expression evaluation in codegen
    - Update to use full `generate_expr()` for offset expressions
    - Test: `G LABEL+$L(X)` with X="AB" → jumps to LABEL+2

## Testing Strategy

### Unit Tests

Replace stubs in `tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py`:
- One test class per function category
- Test both full name and abbreviation
- Test edge cases (empty strings, out of bounds, etc.)

### Integration Tests

- Run V1FN* MUGJ test suite
- Compare output against YottaDB
- Use `uv run python utils/validate.py` for each test

### Validation Commands

```bash
# Test individual function
uv run python utils/validate.py --code 'TEST W $L("HELLO"),! Q'

# Run MUGJ test suite
docker run --rm -v "$(pwd):/workspace" ydb tests/functional/mugj/inref/V1FNL.m

# Compare with m2py
uv run python utils/validate.py tests/functional/mugj/inref/V1FNL.m
```

## Success Criteria

- [X] All acceptance scenarios from spec.md pass (validated via unit tests)
- [ ] MUGJ V1FN* tests produce matching output (blocked by MFormatControl - deferred to Spec 011)
- [X] No xfail markers remain on intrinsic function tests (except MUGJ-dependent stubs)
- [X] `ast.parse()` succeeds on all generated Python
- [X] Documentation updated (docs/codegen/functions.md)
