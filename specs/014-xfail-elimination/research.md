# Research: Spec 014 xfail Elimination

**Branch**: `014-xfail-elimination` | **Date**: 2025-01-19 | **Spec**: [spec.md](spec.md)

**Status**: ✅ COMPLETE (2026-01-20) - All xfail tests resolved. Zero remaining.

## Summary

This research documents findings from investigating the 163 xfail tests that need to be
eliminated by either implementing the feature or ensuring explicit `NotImplementedError`
is raised.

---

## 1. Current xfail Test Distribution

### Final Count (2026-01-20)
```
uv run pytest --collect-only -m xfail -q 2>/dev/null | tail -1
# 0 tests collected - ALL XFAILS RESOLVED
```

### Historical Count Evolution

| Date | Count | Notes |
|------|-------|-------|
| Spec 013 (plan) | 156 | Original estimate from gap analysis |
| 2025-01-19 (start) | 163 | +7 tests added for limitation error coverage (Task 14.23) |
| 2026-01-20 (end) | 0 | All xfails eliminated via implementation or explicit errors |

**Note**: The spec.md and codegen-plan.md originally referenced 156 tests, but actual
starting count was 163. The 7 additional tests were added for limitation error coverage.

### Original Test Distribution by Category

| Category | Count | Location |
|----------|-------|----------|
| Math Library (LIM-014) | 57 | `s7_expressions/test_s7_1_6_5_library_functions_math.py` |
| Z-Commands (LIM-015) | 15 | `extensions/ydb/test_z*.py` |
| String Library (LIM-014) | 6 | `s7_expressions/test_s7_1_6_5_library_functions_string.py` |
| Character Library (LIM-014) | 5 | `s7_expressions/test_s7_1_6_5_library_functions_character.py` |
| SSVN Error Tests (LIM-003/011) | 4 | `s7_expressions/test_s7_1_3_ssvns.py` |
| Routine Structure | 3 | `s6_routine/test_s6_1_routine_head.py`, `test_s6_2_routine_body.py` |
| Transaction (LIM-016) | 2 | `s6_routine/test_s6_3_1_transaction.py` |
| Error Processing | 1 | `s6_routine/test_s6_3_2_error_processing.py` |
| Legacy/$NEXT (LIM-016) | 5 | `legacy/test_pre1995_behavior.py` |
| Library Error Tests (LIM-014) | 2 | `s7_expressions/test_s7_1_6_5_library_functions_character.py` |
| External Calls | 1 | `integration/test_external_calls.py` |
| **Total** | **163** | |

---

## 2. Root Cause Analysis

### 2.1 Silent Failures (PARSES_OK Limitations)

The main issue is that some limitations return empty strings instead of raising errors:

**File**: [src/m2py/codegen/expressions.py](../../src/m2py/codegen/expressions.py#L320-L328)
```python
# Current (WRONG):
elif name in ("EVENT", "E", "WINDOW", "W", "DISPLAY", "DI"):
    # MWAPI SSVNs - documented limitation (LIM-003)
    return "''"
elif name in ("LIBRARY", "LI"):
    # ^$LIBRARY - documented limitation (LIM-011)
    return "''"

# Required (CORRECT):
elif name in ("EVENT", "E", "WINDOW", "W", "DISPLAY", "DI"):
    raise NotImplementedError("LIM-003: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) not supported")
elif name in ("LIBRARY", "LI"):
    raise NotImplementedError("LIM-011: ^$LIBRARY SSVN not supported")
```

### 2.2 Library Function Import Errors

When calling `$$%SIN^MATH`, the codegen attempts to import the MATH module but:
1. The bundled `m2py.runtime.routines.MATH` module exists
2. BUT individual functions like `_SIN` aren't implemented
3. Currently fails with `AttributeError`, not `NotImplementedError`

**Fix needed**: Wrap extrinsic function imports with try/except that raises
`NotImplementedError("LIM-014: ...")` for ANSI library functions.

### 2.3 Z-Commands Missing Codegen Handlers

The Z-commands (ZBREAK, ZEDIT, etc.) currently have parser support but codegen
produces `pass` statements. Need to raise `NotImplementedError("LIM-015: ...")`.

**File**: `src/m2py/codegen/statements.py` - Need to add Z-command dispatch.

---

## 3. Implementation Strategy

### 3.1 Phase 6 Error Handling (99 tests) - LOW COMPLEXITY

**Decision**: Implement explicit error handling first (quickest path to test reduction)

**Rationale**:
- 99 tests can pass immediately with simple error checks
- No functional implementation needed
- Establishes explicit contracts about unsupported features
- Other phases have dependencies (Spec 006, 007, 008)

**Alternatives Rejected**:
- Implementing all features: Too much scope, many have zero VistA usage
- Removing tests: Loses visibility into unsupported features

### 3.2 Error Message Format

**Decision**: Use standard format with limitation ID
```python
raise NotImplementedError("LIM-XXX: {description}")
```

**Rationale**:
- Tests can use `pytest.raises(NotImplementedError, match="LIM-XXX")`
- Limitation ID enables traceability to docs/limitations.md
- Consistent format across all limitations

### 3.3 Test Pattern

**Decision**: Convert xfail tests to use `pytest.raises()`
```python
# Before (xfail):
@pytest.mark.xfail(reason="LIM-014: Not implemented")
def test_math_sin_codegen(self, generate_python):
    code = generate_python('TEST W $$%SIN^MATH(1) Q')
    assert "math.sin" in code

# After (passing):
def test_math_sin_codegen(self, generate_python):
    """$$%SIN^MATH should raise NotImplementedError (LIM-014)."""
    with pytest.raises(NotImplementedError, match="LIM-014"):
        generate_python('TEST W $$%SIN^MATH(1) Q')
```

---

## 4. Files to Modify

### 4.1 Error Handling Files (Phase 6)

| File | Changes Needed |
|------|----------------|
| `src/m2py/codegen/expressions.py` | SSVN handlers for LIM-003, LIM-011 |
| `src/m2py/codegen/expressions.py` | Extrinsic function error wrapping for LIM-014 |
| `src/m2py/codegen/statements.py` | Z-command handlers for LIM-015 |
| `src/m2py/codegen/statements.py` | TROLLBACK:n check for LIM-016 |

### 4.2 Test Files (Convert xfail → pytest.raises)

| File | Tests to Convert |
|------|------------------|
| `tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py` | 4 tests |
| `tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py` | 57 tests |
| `tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_string.py` | 6 tests |
| `tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_character.py` | 7 tests |
| `tests/unit/codegen/extensions/ydb/test_z*.py` | 15 tests |
| `tests/unit/codegen/legacy/test_pre1995_behavior.py` | 5 tests |
| `tests/unit/codegen/s6_routine/test_s6_3_1_transaction.py` | 1 test (TROLLBACK:n) |

---

## 5. Dependencies Analysis

### Blocked Tasks (Spec 006/007/008)

| Task | Dependency | Status | Impact |
|------|------------|--------|--------|
| Task 14.5 (DO External) | Spec 008 | Blocked | 6 tests remain xfail |
| Task 14.6 (GOTO Advanced) | Spec 006 | Blocked | 5 tests remain xfail |
| Task 14.7 (Computed Offsets) | Spec 007 | Blocked | 6 tests remain xfail |

**Decision**: These 17 tests will remain xfail until dependencies are resolved.
Document in plan.md as "Blocked" items.

### Unblocked Tasks

All Phase 6 (error handling) tasks have no dependencies and can proceed immediately.
Phase 1 (Core Language Semantics) tasks 14.1-14.4 have partial dependencies on database backend,
but stub implementation is acceptable per codegen-plan.md.

---

## 6. Validation Strategy

### 6.1 Before Each Phase

```bash
# Capture baseline
uv run pytest --collect-only -m xfail -q 2>/dev/null | tail -1
```

### 6.2 After Error Handling Changes

```bash
# Run affected tests to verify xfail → pass
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py -v
uv run pytest tests/unit/codegen/extensions/ydb/ -v
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_6_5_library_functions_math.py -v
```

### 6.3 Full Regression

```bash
# Must not break existing tests
uv run pytest
# Expected: all tests pass, 0 xfail, 0 xpass
```

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | Low | High | Run full suite after each phase |
| Missing edge cases in error handling | Medium | Low | Error message includes context |
| Blocked tasks delaying completion | High | Medium | Document as "Blocked", focus on unblocked |
| Test count discrepancy (156 vs 163) | N/A | None | Updated to actual count of 163 |

---

## 8. Phase Sizing

Based on complexity analysis:

| Phase | Tasks | Tests | Complexity | Effort |
|-------|-------|-------|------------|--------|
| Phase A: Error Handling | 14.17-14.23 | 99 | LOW | 1-2 days |
| Phase B: Core Semantics | 14.1-14.4 | 12 | MEDIUM | 2-3 days |
| Phase C: Data Operations | 14.8-14.10 | 8 | MEDIUM | 1-2 days |
| Phase D: Routine Structure | 14.11-14.12 | 6 | LOW | 1 day |
| Phase E: Advanced Features | 14.13-14.16 | 14 | MEDIUM | 2-3 days |
| Phase F: Blocked (defer) | 14.5-14.7 | 17 | HIGH | Blocked |

**Recommended Order**: A → B → C → D → E (F blocked on Spec 006/007/008)

---

## 9. Conclusions

1. **99 tests can pass immediately** by adding error handling (Phase 6 → Phase A)
2. **17 tests are blocked** on Spec 006/007/008 dependencies
3. **47 tests require actual implementation** across Phases B-E
4. **Error handling should be done first** - quickest path to reducing xfail count
5. **All error messages must include LIM-XXX** for traceability
