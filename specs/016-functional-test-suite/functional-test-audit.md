# Functional Test Failure Audit

**Date**: 2026-01-22
**Total Failures**: 147 (unchanged - some fixed, others newly visible)
**Total Passed**: 336
**Total xfailed**: 5

## Fixes Applied

1. **V1RN SyntaxError** - Translate % routine names to valid Python module names
2. **new TypeError** - Handle MIndirection in exclusive NEW except_list  
3. **VV2LHP1 ValueError** - Default LHS $PIECE piece_from to 1 when not specified
4. **for/forloop Timeout** - Fixed m_num/m_compare to normalize floats to ints (0.0 → 0)

## Priority 1: SyntaxErrors (Codegen Bugs) - 2 routines

These generate invalid Python and must be fixed.

- [X] **V1RN** - `SyntaxError: invalid decimal literal (line 95)` - **FIXED** (translate routine names with %)
- [ ] **VV2VNIA** - `SyntaxError: unmatched ')' (line 131)` - **SKIPPED** (complex indirection with string concat - functional gap)

## Priority 2: TypeError/ValueError (Likely Codegen Bugs) - 2 routines

- [X] **new** - `TypeError: unhashable type: 'MIndirection'` - **FIXED** (handle MIndirection in exclusive NEW except_list)
- [X] **VV2LHP1** - `ValueError: LHS $PIECE requires at least 3 arguments, got 2` - **FIXED** (default piece_from to 1), now fails on NakedGlobal (functional gap)

## Priority 3: Timeout Issues - 2 routines

- [X] **for** - `Execution timed out after 30s` - **FIXED** (m_compare float normalization), now has output mismatch
- [X] **forloop** - `Execution timed out after 30s` - **FIXED** (same)

## Priority 4: UnsupportedFeatureError - 2 routines

- [ ] **V1NST1** - `UnsupportedFeatureError: UNRESOLVED GOTO not supported - See Spec 012`
- [ ] **V1NST2** - `UnsupportedFeatureError: UNRESOLVED GOTO not supported - See Spec 012`

## Category C: NotImplementedError (Functional Gaps) - ~60 failures

These are known limitations - track but don't fix now.

### Argumentless KILL (14 failures)
- V1PRGD, V1OV, V1SEQ, V1CALL, V1NST3, VV2VNIB, VV2LCC1, and others
- **Reason**: TRAMPOLINE strategy doesn't support argumentless KILL

### Argumentless NEW (6 failures)  
- per02397, setpiece, fifo, and others
- **Reason**: TRAMPOLINE strategy doesn't support argumentless NEW

### $ZTRAP related (16 failures)
- Special variable $ZTRAP (6), NEW $ZTRAP (4), SET $zt (2), etc.
- **Reason**: Error trapping not implemented

### ZSYSTEM command (6 failures)
- zlfix, stream, per2968, etc.
- **Reason**: LIM-015 - Z-commands not supported

### $ZVERSION function (4 failures)
- V1AC, char, etc.
- **Reason**: YDB-specific intrinsic function

### Other Z-functions (4 failures)
- $ZPREVIOUS (2), $ZPOSITION (2)
- **Reason**: YDB-specific intrinsic functions

### LHS $PIECE edge cases (4 failures)
- VV2LHP2 (NakedGlobal), VV2VNIC (Indirection)
- **Reason**: Complex SET $PIECE targets not supported

### Other gaps (6 failures)
- ExtendedGlobalBracket (2), MZWriteSubscriptAll (2), binary operator ']' (2), $i (2)

## Category D: Output Mismatches (Functional Gaps) - ~70 failures

These run but produce different output than YDB. Common causes:
- Numeric precision differences
- String formatting differences  
- Driver routines with empty expected output

### Driver Routines (empty expected output)
- V1BOA, V1BOB, V1BOC, V1FN, V1FC, etc.

### Numeric/Boolean Differences
- bool, arith, ebmuldiv, etc.

### Other Output Mismatches
- Remaining tests that execute but diff from expected

---

## Triage Order

1. [x] Get categorized summary (this file)
2. [ ] Fix V1RN SyntaxError
3. [ ] Fix VV2VNIA SyntaxError  
4. [ ] Fix "new" TypeError
5. [ ] Fix VV2LHP1 ValueError
6. [ ] Review UnsupportedFeatureError cases
7. [ ] Document remaining as known limitations
