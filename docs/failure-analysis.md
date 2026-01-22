# Functional Test Failure Analysis

**Date**: 2026-01-22  
**Total Failures**: 147 (142 unique tests, 5 duplicates across test files)  
**Passing Tests**: 336 passed, 5 xfailed  

## Summary

| Category | Count | Action |
|----------|-------|--------|
| TRAMPOLINE Strategy Gaps | 10 | Implement hybrid dict-based state |
| LIM-015 Z-extensions | 12 | Configure xfail |
| Other Functional Gaps | 11 | Implement missing features |
| External Dependencies | 33 | Review test infrastructure |
| Codegen Bugs | 1 | Fix generated Python |
| Behavioral Bugs (output mismatch) | 75 | Debug and fix |

---

## Section 1: TRAMPOLINE Strategy Gaps → Architecture Enhancement

These failures require enhancing the TRAMPOLINE code generation strategy to support
argumentless KILL and NEW commands. These have VistA usage (~50 files) so cannot
be treated as limitations.

### Argumentless KILL (7 tests)

| Test | Error |
|------|-------|
| v1call | `Argumentless KILL not supported in TRAMPOLINE strategy` |
| v1nst3 | `Argumentless KILL not supported in TRAMPOLINE strategy` |
| v1ov | `Argumentless KILL not supported in TRAMPOLINE strategy` |
| v1prgd | `Argumentless KILL not supported in TRAMPOLINE strategy` |
| v1seq | `Argumentless KILL not supported in TRAMPOLINE strategy` |
| vv2lcc1 | `Argumentless KILL not supported in TRAMPOLINE strategy` |
| vv2vnib | `Argumentless KILL not supported in TRAMPOLINE strategy` |

### Argumentless NEW (3 tests)

| Test | Error |
|------|-------|
| fifo | `Argumentless NEW not supported in TRAMPOLINE strategy` |
| per02397 | `Argumentless NEW not supported in TRAMPOLINE strategy` |
| setpiece | `Argumentless NEW not supported in TRAMPOLINE strategy` |

### Proposed Solution: Hybrid Dict-Based State

**Status**: Needs further analysis before implementation.

The current TRAMPOLINE strategy uses a `RoutineState` dataclass with individual fields
for each cross-label variable. This doesn't support argumentless KILL/NEW because:

- `KILL` (argumentless) must clear ALL local variables
- `NEW` (argumentless) must save and restore ALL local variables

**Proposed approach**: When a routine uses argumentless KILL or NEW, store ALL local
variables in a dictionary within `RoutineState` instead of as individual fields:

```python
@dataclass
class RoutineState:
    _locals: dict = field(default_factory=dict)      # All local variables
    _new_stack: list = field(default_factory=list)   # Stack for NEW saves
```

This enables:
- `KILL` (argumentless) → `state._locals.clear()`
- `NEW` (argumentless) → `state._new_stack.append(dict(state._locals)); state._locals.clear()`

**Changes needed** (requires further analysis):

1. **Analysis phase**: Detect if routine uses argumentless KILL or NEW
2. **RoutineState generation**: Add `_locals: dict` field (and `_new_stack: list`)
3. **Variable codegen**: Use `state._locals[name]` instead of `state.name`
4. **KILL/NEW codegen**: Implement the clear/stack operations

**SUBTOTAL: 10 tests → architecture enhancement**

---

## Section 2: LIM-015 Z-Extensions → Configure xfail

These failures use YDB Z-extensions with zero VistA usage (documented in LIM-015).

### ZSYSTEM Command (3 tests)

| Test | Error |
|------|-------|
| zlfix | `LIM-015: ZSYSTEM command not supported` |
| stream | `LIM-015: ZSYSTEM command not supported` |
| per2968 | `LIM-015: ZSYSTEM command not supported` |

### $ZTRAP Related (6 tests)

| Test | Error |
|------|-------|
| per2586a | `Special variable $ZTRAP not yet supported` |
| per2586b | `Special variable $ZTRAP not yet supported` |
| per2586c | `Special variable $ZTRAP not yet supported` |
| set | `NEW $ZTRAP not supported` |
| zbits | `NEW $ZTRAP not supported` |
| ztrp | `SET $zt not supported` |

### Z-functions (3 tests)

| Test | Error |
|------|-------|
| char | `Intrinsic function $ZVersion not yet implemented` |
| v1ac | `Intrinsic function $ZVersion not yet implemented` |
| zprev | `Intrinsic function $ZPREVIOUS not yet implemented` |

**SUBTOTAL: 12 tests → xfail (LIM-015)**

---

## Section 3: Other Functional Gaps → Need Implementation

These failures indicate features that need to be implemented.

### Special Variables (3 tests)

| Test | Error | Notes |
|------|-------|-------|
| new | `Special variable $ZPOSITION not yet supported` | YDB-specific |
| kill1 | `Special variable $ZPOSITION not yet supported` | YDB-specific |
| vv2lcf2 | `Special variable $i not yet supported` | May be $I (device $IO?) |

### LHS $PIECE with Non-Local Variables (3 tests)

Left-hand side $PIECE currently only supports local variables.

| Test | Error |
|------|-------|
| vv2lhp1 | `LHS $PIECE first argument must be a variable, got NakedGlobal` |
| vv2lhp2 | `LHS $PIECE first argument must be a variable, got NakedGlobal` |
| vv2vnic | `LHS $PIECE first argument must be a variable, got Indirection` |

### Expression Types (1 test)

| Test | Error |
|------|-------|
| largeexp1 | `Unsupported expression type: MZWriteSubscriptAll` |

### Operators (1 test)

| Test | Error |
|------|-------|
| relation | `Unsupported binary operator: ']'` |

This is the "sorts after" operator - needs implementation.

### SET Target Types (1 test)

| Test | Error |
|------|-------|
| per02276 | `Unsupported SET target type: ExtendedGlobalBracket` |

### UNRESOLVED GOTO (2 tests)

| Test | Error |
|------|-------|
| v1nst1 | `UNRESOLVED GOTO not supported - See Spec 012` |
| v1nst2 | `UNRESOLVED GOTO not supported - See Spec 012` |

These reference Spec 012 - GOTO analysis improvements needed.

**SUBTOTAL: 11 tests → implement**

---

## Section 4: Code Generation Bugs → Fix

### SyntaxError in Generated Python (1 test)

| Test | Error |
|------|-------|
| vv2vnia | `Generated Python has syntax error: unmatched ')' (line 131)` |

This is a codegen bug that needs debugging.

**SUBTOTAL: 1 test → debug**

---

## Section 5: External Dependencies → Review Infrastructure

These tests fail with "No result for X" indicating external routine dependencies
that aren't being handled correctly.

### Merge Suite Subtests (21 tests)

| Test | Notes |
|------|-------|
| gbl2gbl | merge suite subtest |
| gbl2lcl | merge suite subtest |
| lcl2gbl | merge suite subtest |
| lcl2lcl | merge suite subtest |
| ugbl2gbl | merge suite subtest |
| ugbl2lcl | merge suite subtest |
| ulcl2gbl | merge suite subtest |
| ulcl2lcl | merge suite subtest |
| extgbl1 | merge suite subtest |
| extgbl2 | merge suite subtest |
| falsedsc | merge suite subtest |
| indirection | merge suite subtest |
| misclv | merge suite subtest |
| mrgclnup | merge suite subtest |
| nullsubs | merge suite subtest |
| tp_simple | merge suite subtest |
| tp_stress | merge suite subtest |
| zshowgbl | merge suite subtest |
| zshowlcl | merge suite subtest |
| errors | merge suite subtest |
| mvts_merge | merge suite subtest |

### Merge Routines (12 tests)

| Test | Notes |
|------|-------|
| mbyexam | merge routine |
| mrgstp | merge routine |
| errors | merge routine |
| mindr1 | merge routine |
| mindr2 | merge routine |
| mindr3 | merge routine |
| mindr4 | merge routine |
| mindmisc | merge routine |
| v4merge | merge routine |
| mergelv | merge routine |
| list | merge routine |
| nullfill | merge routine |
| mrgitp | merge routine |

**SUBTOTAL: 33 tests → review infrastructure**

---

## Section 6: Behavioral Bugs → Output Mismatches

These tests execute but produce incorrect output compared to YDB.

### Arithmetic Operations (5 tests)

| Test | Sample Error Pattern |
|------|---------------------|
| arith | Multiplication failures, scientific notation handling |
| barith | Boolean arithmetic issues |
| ebmuldiv | Exponent multiplication/division |
| largeexp2 | Large exponent handling |
| largeexp3 | Large exponent handling |

Common issues:
- Scientific notation formatting (1e-17 vs .000000000000000001)
- Float precision (10.000000011111112 vs 10.0000000111111111)
- Exponent handling (10 * 1.234E+5 giving 12.34 instead of 1234000)

### Boolean/Comparison (3 tests)

| Test | Notes |
|------|-------|
| bool | Boolean operations |
| cmptst | Comparison tests |
| expr2 | Expression evaluation |

### String Operations (5 tests)

| Test | Notes |
|------|-------|
| piece | $PIECE function issues |
| pattst | Pattern matching |
| v1pat | Pattern matching |
| vv2pat1 | Pattern matching |
| vv2pat2 | Pattern matching |
| vv2pat3 | Pattern matching |

### Control Flow (6 tests)

| Test | Notes |
|------|-------|
| for | FOR loop |
| forloop | FOR loop |
| v1fora | FOR loop |
| v1forb | FOR loop |
| v1forc | FOR loop |
| xecute | XECUTE command |

### Variables and Storage (10+ tests)

| Test | Notes |
|------|-------|
| globals | Global variable handling |
| locals | Local variable handling |
| larray | Local array handling |
| order | $ORDER function |
| query | $QUERY function |
| v1lvn | Local variable names |
| v1dga | Data global A |
| v1dgb | Data global B |
| v1dla | Data local A |
| v1dlb | Data local B |

### I/O Operations (3 tests)

| Test | Notes |
|------|-------|
| iowrite | I/O write |
| text4 | Text processing |
| stpfail | Stop failure |
| putfail | Put failure |

### Function Tests (10+ tests)

| Test | Notes |
|------|-------|
| v1fn | Functions |
| vv2fn1 | Functions |
| vv2fn2 | Functions |
| v1fc | Function calls |
| v1ll1 | Line labels |
| v1ll2 | Line labels |
| v1pc | $PIECE |
| v1jst | $JUSTIFY |
| v1svh | Special variables H |
| v1svs | Special variables S |

### Other Tests

| Test | Notes |
|------|-------|
| extcall | External calls |
| miscdb | Misc database |
| sortsaft | Sort |
| tstp | Transaction |
| v1bo* | Boolean ops |
| v1br | Branch |
| v1do | DO |
| v1go | GOTO |
| v1id* | Indirection |
| v1ie | IF/ELSE |
| v1max | MAX |
| v1nr | $NEXT/$REFERENCE |
| v1num | Numeric |
| v1nx | $NEXT |
| v1rn | Routine names |
| v1set | SET |
| v1uo | Unary ops |
| v1xeca | XECUTE |
| v1xecb | XECUTE |
| vv2lcc2 | LCC |
| vv2lcf1 | LCF |
| vv2no | Numeric ops |
| vv2nr | $NEXT/$REFERENCE |
| vv2ss1 | Subscript |
| vv2ss2 | Subscript |

**SUBTOTAL: 75 tests → debug output mismatches**

---

## Action Items

### Short-term: Configure xfail for LIM-015 (12 tests)

Update `tests/functional/conftest.py` ROUTINE_LIMITATIONS dict:

```python
ROUTINE_LIMITATIONS: dict[str, str] = {
    # Existing entries...
    
    # LIM-015: ZSYSTEM
    "zlfix": "LIM-015",
    "stream": "LIM-015", 
    "per2968": "LIM-015",
    
    # LIM-015: $ZTRAP
    "per2586a": "LIM-015",
    "per2586b": "LIM-015",
    "per2586c": "LIM-015",
    "set": "LIM-015",
    "zbits": "LIM-015",
    "ztrp": "LIM-015",
    
    # LIM-015: Z-functions
    "char": "LIM-015",
    "v1ac": "LIM-015",
    "zprev": "LIM-015",
}
```

### Short-term: Implement Functional Gaps (11 tests)

1. **LHS $PIECE with NakedGlobal/Indirection** - Extend codegen
2. **"Sorts after" operator** (`]`) - Add operator support
3. **ExtendedGlobalBracket SET** - Handle in statements.py
4. **MZWriteSubscriptAll** - Handle in expressions.py
5. **$ZPOSITION** - Add special variable support (or xfail as LIM-015)
6. **$i** special variable - Identify and implement or xfail

### Medium-term: TRAMPOLINE Architecture Enhancement (10 tests)

Implement hybrid dict-based state for argumentless KILL/NEW support.
See Section 1 for detailed proposal - requires further analysis.

### Medium-term: Debug Behavioral Bugs (75 tests)

Priority areas based on frequency:
1. **Arithmetic/numeric handling** - Scientific notation, exponents
2. **Pattern matching** - Multiple tests failing
3. **FOR loops** - Control flow issues
4. **$ORDER/$QUERY** - Iterator functions

### Investigation: External Dependencies (33 tests)

These "No result" failures need infrastructure review:
- Are the required helper routines being loaded?
- Is the merge test harness working correctly?
- Are there missing outref files?

---

## Appendix: Test Name to Error Mapping

For reference, the full mapping of each failed test to its error:

[See categorize_failures.py output for complete list]
