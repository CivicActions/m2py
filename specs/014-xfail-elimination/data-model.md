# Data Model: Spec 014 xfail Elimination

**Branch**: `014-xfail-elimination` | **Date**: 2025-01-19 | **Spec**: [spec.md](spec.md)

## Overview

This spec focuses on code generation modifications and test conversions. The data model
is minimal - primarily tracking which tests need which action.

---

## 1. Test State Transitions

```
┌─────────────┐     ┌─────────────────────────┐     ┌─────────────┐
│   XFAIL     │ ──► │ Implementation/ErrorFix │ ──► │   PASSING   │
│  (current)  │     │                         │     │  (target)   │
└─────────────┘     └─────────────────────────┘     └─────────────┘
```

### Test Categories

| Category | Action Required | Result |
|----------|-----------------|--------|
| Error Handling (LIM-XXX) | Add `raise NotImplementedError("LIM-XXX: ...")` | Test uses `pytest.raises()` |
| Feature Implementation | Implement codegen/runtime | Test asserts correct output |
| Control Flow (Spec 006/007/008) | Implement using existing infrastructure | Test passes ✓ |

**Note**: All specs 001-013 are ✅ COMPLETE. Nothing is blocked.

**Full test distribution**: See [research.md](research.md#test-distribution-by-category)

---

## 2. Limitation Entity

**Source**: [src/m2py/limitations.py](../../src/m2py/limitations.py)

```python
class Limitation(NamedTuple):
    id: str                    # "LIM-003"
    category: str              # "MWAPI SSVNs"
    type: LimitationType       # PARSES_OK
    short_description: str     # "^$EVENT, ^$WINDOW, ^$DISPLAY"
    sections: tuple[str, ...]  # Test section IDs
    details: str               # Full markdown
    behavior: str              # Expected behavior
```

### Relevant Limitations

| ID | Type | Tests Affected | Action |
|----|------|----------------|--------|
| LIM-003 | PARSES_OK | 3 | Raise `NotImplementedError` |
| LIM-004 | PARSES_OK | 2 | Already working ✓ |
| LIM-011 | PARSES_OK | 1 | Raise `NotImplementedError` |
| LIM-014 | PARSES_OK | 68 | Raise `NotImplementedError` |
| LIM-015 | PARSES_OK | 15 | Raise `NotImplementedError` |
| LIM-016 | PARSES_OK | 6 | Raise `NotImplementedError` |

---

## 3. Test File Organization

### Spec-Aligned Pattern
```
tests/unit/codegen/s{section}_{name}/test_s{section}_{subsection}_{name}.py
```

### Example Mappings

| MUMPS Section | Test Path |
|---------------|-----------|
| §7.1.3 SSVNs | `s7_expressions/test_s7_1_3_ssvns.py` |
| §7.1.5 Intrinsic Functions | `s7_expressions/test_s7_1_5_intrinsic_functions.py` |
| §7.1.6.5 Library Functions | `s7_expressions/test_s7_1_6_5_library_functions_*.py` |
| §8.2.21 TROLLBACK | `s8_commands/test_s8_2_21_trollback.py` |

### Extension Tests (Non-Standard)

| Category | Test Path |
|----------|-----------|
| YDB Z-Commands | `extensions/ydb/test_z*.py` |
| Pre-1995 Legacy | `legacy/test_pre1995_behavior.py` |

---

## 4. Codegen Context

```python
class GeneratorContext:
    """Context passed through code generation."""
    emitter: CodeEmitter       # Output handling
    routine: MRoutine          # Current routine ASG
    current_label: MLabel      # Current label being generated
    scope_strategy: ScopeStrategy  # Variable handling strategy
    # ... other fields
```

The xfail tests primarily need changes in these generation functions:

| Function | File | Handles |
|----------|------|---------|
| `_generate_ssvn()` | expressions.py | ^$EVENT, ^$LIBRARY, etc. |
| `_generate_extrinsic()` | expressions.py | $$%FUNC^ROUTINE |
| `generate_statement()` | statements.py | Z-commands, TROLLBACK |

---

## 5. Error Response Contract

### Format
```python
raise NotImplementedError("LIM-XXX: {human-readable description}")
```

### Test Pattern
```python
def test_lim_xxx_feature(self, generate_python):
    """Feature should raise NotImplementedError (LIM-XXX)."""
    with pytest.raises(NotImplementedError, match="LIM-XXX"):
        generate_python('TEST W unsupported_feature Q')
```

### Examples

| Limitation | Error Message |
|------------|---------------|
| LIM-003 | `"LIM-003: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) not supported"` |
| LIM-011 | `"LIM-011: ^$LIBRARY SSVN not supported"` |
| LIM-014 | `"LIM-014: ANSI library function $$%SIN^MATH not implemented"` |
| LIM-015 | `"LIM-015: ZBREAK command not implemented (zero VistA usage)"` |
| LIM-016 | `"LIM-016: TROLLBACK:n (level argument) not implemented"` |

---

## 6. State Tracking

### Test Inventory Matrix

| Phase | Category | xfail Start | Target End |
|-------|----------|-------------|------------|
| A | Error Handling | 99 | 0 |
| B | Core Semantics | 12 | 0 |
| C | Data Operations | 8 | 0 |
| D | Routine Structure | 6 | 0 |
| E | Advanced Features | 14 | 0 |
| F | Control Flow Advanced | 17 | 0 |
| Misc | Cross-cutting | 7 | 0 |
| **Total** | | **163** | **0** |

**Goal**: Reduce from 163 xfail to 0 xfail (all specs 001-013 are complete).
See [research.md](research.md) for detailed test distribution by category.

---

## 7. Validation Queries

### Count xfail Tests
```bash
uv run pytest --collect-only -m xfail -q 2>/dev/null | tail -1
```

### List xfail by Category
```bash
uv run pytest --collect-only -m xfail -q tests/unit/codegen/extensions/ydb/
uv run pytest --collect-only -m xfail -q tests/unit/codegen/s7_expressions/
```

### Verify No Regressions
```bash
uv run pytest  # All tests must pass
```
