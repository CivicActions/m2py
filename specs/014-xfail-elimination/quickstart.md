# Quickstart: Spec 014 xfail Elimination

**Branch**: `014-xfail-elimination` | **Date**: 2025-01-19 | **Spec**: [spec.md](spec.md)

## Goal

Eliminate ALL 163 xfail tests by:
1. Implementing missing features (64 tests)
2. Adding explicit `NotImplementedError` for limitations (99 tests)

**Note**: All specs 001-013 are ✅ COMPLETE. Nothing is blocked!

---

## Quick Validation

```bash
# Current xfail count (baseline)
uv run pytest --collect-only -m xfail -q 2>/dev/null | tail -1
# Expected: 163/4992 tests collected

# After completion
# Expected: 0 tests collected (zero xfail!)
```

---

## Phase Order (Recommended)

| Order | Phase | Tests | Effort | Status |
|-------|-------|-------|--------|--------|
| 1 | A: Error Handling | 99 | 1-2 days | Ready |
| 2 | B: Core Semantics | 12 | 2-3 days | Ready |
| 3 | C: Data Operations | 8 | 1-2 days | Ready |
| 4 | D: Routine Structure | 6 | 1 day | Ready |
| 5 | E: Advanced Features | 14 | 2-3 days | Ready |
| 6 | F: Control Flow | 17 | 2-3 days | Ready (Spec 006/007/008 ✅) |
| 7 | G: Misc/Cross-cutting | 7 | 1 day | Ready |

---

## Phase A: Error Handling (99 tests)

### Changes Required

**1. SSVN Error Handling** (`src/m2py/codegen/expressions.py`)
```python
# Line ~320 - Replace silent returns with errors
elif name in ("EVENT", "E", "WINDOW", "W", "DISPLAY", "DI"):
    raise NotImplementedError("LIM-003: MWAPI SSVNs not supported")
elif name in ("LIBRARY", "LI"):
    raise NotImplementedError("LIM-011: ^$LIBRARY SSVN not supported")
```

**2. Library Function Errors** (`src/m2py/codegen/expressions.py`)
```python
# In _generate_extrinsic() - Wrap external imports
ANSI_LIBRARY_ROUTINES = {"MATH", "STRING", "CHARACTER"}
if routine_name in ANSI_LIBRARY_ROUTINES:
    raise NotImplementedError(f"LIM-014: ANSI library function $$%{label_name}^{routine_name} not implemented")
```

**3. Z-Command Errors** (`src/m2py/codegen/statements.py`)
```python
# Add Z-command detection
Z_COMMANDS = {"ZALLOCATE", "ZBREAK", "ZCOMPILE", ...}
if command_name in Z_COMMANDS:
    raise NotImplementedError(f"LIM-015: {command_name} command not implemented")
```

**4. TROLLBACK:n Error** (`src/m2py/codegen/statements.py`)
```python
# In TROLLBACK handler - check for level argument
if trollback.level is not None:
    raise NotImplementedError("LIM-016: TROLLBACK:n (level argument) not implemented")
```

### Test Conversions

Convert from xfail pattern:
```python
@pytest.mark.xfail(reason="LIM-XXX: ...")
def test_feature(self):
    result = generate_python('...')
    assert something in result
```

To pytest.raises pattern:
```python
def test_feature(self):
    """Feature raises NotImplementedError (LIM-XXX)."""
    with pytest.raises(NotImplementedError, match="LIM-XXX"):
        generate_python('...')
```

---

## Phase B: Core Semantics (12 tests)

### Task 14.1: Special Variables (4 tests)
- `$TLEVEL` - Transaction level tracking
- `$QUIT` - Context awareness (1 in extrinsic, 0 in DO)
- `$TEXT` - External routine references

### Task 14.2: Indirection (3 tests)
- Subscript indirection (`@var(subscript)`)
- Argument indirection (`@var`)
- Runtime resolution

### Task 14.3: Transaction (2 tests)
- Basic TSTART/TCOMMIT
- Note: TROLLBACK:n and $TRESTART → LIM-016 error

### Task 14.4: Error Processing (1 test)
- Error propagation across label calls

---

## Phase C: Data Operations (8 tests)

### Task 14.8: MERGE Globals (2 tests)
```python
# M ^GLO=LOCAL
# M ^GLO1=^GLO2
```

### Task 14.9: Naked References (5 tests)
- Error without prior global
- Support in $DATA, $ORDER, MERGE, LOCK

### Task 14.10: KILL Global (1 test)
```python
# K ^GLO
```

---

## Phase D: Routine Structure (6 tests)

### Task 14.11: Routine Metadata (3 tests)
- Docstring from MUMPS header
- Empty label translation
- Comment preservation

### Task 14.12: Extrinsic Advanced (3 tests)
- Module caching
- Cross-routine variable passing
- Routine name translation (%, numeric)

---

## Phase E: Advanced Features (14 tests)

### Task 14.13: Language Semantics (5 tests)
- $TEST stacking rules
- Execution level tracking
- Extrinsic return semantics

### Task 14.14: Postconditions (3 tests)
- Independent evaluation
- Evaluation order
- Side effects

### Task 14.15: XECUTE Runtime (3 tests)
- Global access in XECUTE
- ZOSF optimization
- ZOSF fallback

### Task 14.16: Character Set (3 tests)
- M character encoding
- Graphic/control characters

---

## Phase F: Control Flow Advanced (17 tests) 🎯 NOW IMPLEMENTABLE

These tests use Spec 006/007/008 infrastructure which is ✅ COMPLETE:

| Task | Tests | Prerequisite |
|------|-------|-------------|
| 14.5: DO External | 6 | Spec 008 ✅ |
| 14.6: GOTO Advanced | 5 | Spec 006 ✅ |
| 14.7: Computed Offsets | 6 | Spec 007 ✅ |

---

## Verification Commands

```bash
# After Phase A (error handling)
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py -v
uv run pytest tests/unit/codegen/extensions/ydb/ -v
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_*.py -v

# After each phase
uv run pytest --collect-only -m xfail -q 2>/dev/null | tail -1

# Full regression
uv run pytest
```

---

## Success Metrics

| Metric | Before | After |
|--------|--------|-------|
| xfail tests | 163 | **0** |
| Blocked tests | 0 | 0 |
| Silent failures | Many | 0 |
| Tests with LIM-XXX | ~10 | 99+ |
