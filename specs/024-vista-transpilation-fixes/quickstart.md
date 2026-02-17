# Quickstart: VistA-VEHU-M Transpilation Fixes

**Feature**: 024-vista-transpilation-fixes | **Date**: 2026-02-17

## Overview

This feature resolves 2,592 transpilation failures across 13 root causes to achieve ≥99% VistA-VEHU-M transpilation success. Changes span three layers: semantic analyzer, codegen, and runtime.

## Implementation Order

Work in priority order (P0 → P12). Each priority level is independently testable.

### Priority Cross-Reference (Failure Analysis → User Stories)

| Failure Analysis Priority | Issue | User Story | Task IDs |
|--------------------------|-------|------------|----------|
| P0 | ParenExpr / UnaryPrefixedExpr | US1 | T002, T003, T004 |
| P1 | f-string nested quotes | US1 | T005, T006 |
| P2 | Empty TRAMPOLINE block | US1 | T007 |
| P3 | >= / <= operators | US1 | T008 |
| P4 | SET $X / SET $Y | US1 | T009, T010 |
| P5 | LHS $EXTRACT 1-arg | US2 | T013 |
| P6 | Computed GOTO | US2 | T016 |
| P7 | Tuple SET $P/$E | US2 | T014 |
| P8 | ZLINK/ZLOAD | US3 | T020 |
| P9 | RecursionError | US3 | T019 |
| P10 | NEW indirection | US2 | T015 |
| P11a–h | IRIS vendor functions | US4 | T023–T033 |
| P12 | Misc stubs (device ctl, SVNs, $&, ZPRINT/ZMESSAGE) | US5 | T034–T038, T046 |

### Sprint 1: Quick Wins (P0, P3, P4, P5) — ~1,418 routines

1. **ParenExpr fallback** (P0): Add defensive handler in `generate_expr()` at [expressions.py](../../src/m2py/codegen/expressions.py) before the `NotImplementedError` fallthrough. Same for `UnaryPrefixedExpr`.

2. **`>=`/`<=` operators** (P3): Add two `elif` branches in `_generate_binary_op()` at [expressions.py](../../src/m2py/codegen/expressions.py) after the existing `'>` handler (around L736). Pattern identical to `'<`/`'>`.

3. **SET $X/$Y** (P4): Add `elif` branches in `_generate_single_assignment()` at [statements.py](../../src/m2py/codegen/statements.py) around L1104. Add `set_x()`/`set_y()` to `MRuntime` in [runtime/__init__.py](../../src/m2py/runtime/__init__.py).

4. **LHS $E 1-arg** (P5): Change validation in `_generate_lhs_extract()` at [statements.py](../../src/m2py/codegen/statements.py) L1478 to default start=1, end=1 when len(args)==1.

### Sprint 2: Generated Code Quality (P1, P2) — ~790 routines

5. **f-string fix** (P1): Replace f-string generation in [indirection.py](../../src/m2py/codegen/indirection.py) L575/L578 with string concatenation. Audit all codegen files for similar patterns.

6. **Empty block fix** (P2): In TRAMPOLINE GOTO handling at [statements.py](../../src/m2py/codegen/statements.py) around L3282-3935, ensure conditional GOTOs produce `return` statements inside the `if` block, not after it.

### Sprint 3: Advanced Features (P6-P10) — ~149 routines

7. **Tuple SET $P/$E** (P7): Add `elif isinstance(target, MIntrinsicFunction)` in tuple SET handler at [statements.py](../../src/m2py/codegen/statements.py) L1061.

8. **ZLOAD stub** (P8): Add `elif isinstance(stmt, MZLoadStatement)` dispatch at [statements.py](../../src/m2py/codegen/statements.py) L811-812.

9. **RecursionError** (P9): Add `sys.setrecursionlimit(5000)` in CLI/transpilation entry point.

10. **NEW indirection** (P10): Replace `raise NotImplementedError` at [statements.py](../../src/m2py/codegen/statements.py) L4843 with runtime call.

11. **Computed GOTO** (P6): Generate label-name-string return for indirected GOTO targets in TRAMPOLINE.

### Sprint 4: IRIS Vendor Functions (P11) — ~62 routines

12. **$REPLACE**: Add `m_replace()` to [helpers.py](../../src/m2py/runtime/helpers.py). Wire in codegen intrinsic dispatch.
13. **$ZBOOLEAN**: Add `m_zboolean()` to helpers.py. 16-entry bitwise dispatch.
14. **$ZV/$ZVERSION**: Add `zversion()` to MRuntime. Wire in special variable reader.
15. **$ZF**: Add `m_zf()` to helpers.py. subprocess-based.
16. **$ZR/$ZREFERENCE**: Add property to MRuntime. Update globals.py to track.
17. **$ZA**: Add `za()` property to MRuntime. Default 0.
18. **$NAMESPACE**: Add property + setter to MRuntime. Default "VISTA".
19. **$ZU**: Add `m_zu()` dispatch to helpers.py. ~12 codes.

### Sprint 5: Stubs & Cleanup (P12) — ~49 routines

20. **$ZC/$ZCALL, $VIEW stubs**: Add stub functions to helpers.py.
21. **Device control mnemonics**: Add handler in WRITE codegen + runtime.
22. **SET $ZINTERRUPT/$ZERR/$ZSOURCE**: Add to SET SVN dispatcher.
23. **$DEVICE/$REFERENCE/$ZGBLDIR readers**: Add to SVN reader.
24. **$& external calls**: Stub in codegen.
25. **Non-UTF-8 encoding**: Add fallback in file reader.
26. **Limitations doc**: Add LIM-017, regenerate docs.

## How to Validate

```bash
# Run unit tests for a specific fix
uv run pytest tests/unit/codegen/ -k "paren_expr"

# Run the full VistA scan (slow — ~30 minutes)
uv run python utils/scan_vista.py VistA-VEHU-M/

# Validate a specific routine against YDB
uv run python utils/validate.py --code 'TEST\n I 5>=3 W "yes",! Q'

# Check for Python syntax errors in generated code
uv run python -c "compile(open('output.py').read(), 'output.py', 'exec')"
```

## Key Files to Modify

| File | Changes |
|------|---------|
| `src/m2py/codegen/expressions.py` | ParenExpr/UnaryPrefixedExpr fallback, >=/<= operators, IRIS function dispatch, SVN readers |
| `src/m2py/codegen/statements.py` | SET $X/$Y, LHS $E 1-arg, tuple SET, TRAMPOLINE empty blocks, ZLOAD, NEW indirection, computed GOTO, device control, SET SVNs, $& stubs |
| `src/m2py/codegen/indirection.py` | f-string → string concatenation |
| `src/m2py/runtime/__init__.py` | $X/$Y setters, $ZA, $ZR, $ZV, $NAMESPACE, $DEVICE, $REFERENCE, $ZGBLDIR, computed GOTO dispatch |
| `src/m2py/runtime/helpers.py` | m_replace, m_zboolean, m_zu, m_zf, m_zcall_stub, m_view_func_stub |
| `src/m2py/runtime/devices.py` | Device control mnemonics handler |
| `src/m2py/limitations.py` | LIM-017 (IRIS partial support) |
| `src/m2py/cli/` | RecursionError limit, encoding fallback |

## Dependencies Between Fixes

Most fixes are independent. The only dependencies are:

- **$ZU(5)** depends on **$NAMESPACE** being implemented first
- **$ZR** tracking depends on `globals.py` changes
- **Computed GOTO** depends on TRAMPOLINE dispatcher understanding string return values
- **f-string fix** should be done before the full VistA scan validation (since it affects 580 routines)
