# Contract: Test Conversion

**Version**: 1.0 | **Status**: Draft | **Spec**: [spec.md](../spec.md)

## Overview

This contract defines how xfail tests are converted to passing tests. There are
two conversion patterns depending on whether the feature is implemented or deferred.

---

## Pattern 1: Feature Implementation

When a feature is implemented, convert the xfail test to verify correct behavior.

### Before (xfail)
```python
@pytest.mark.xfail(reason="$TLEVEL not implemented")
def test_sv_tlevel(self, execute_mumps):
    """$TLEVEL returns transaction nesting level."""
    result = execute_mumps('TEST TSTART W $TL Q')
    assert result.output == "1"
```

### After (passing)
```python
def test_sv_tlevel(self, execute_mumps):
    """$TLEVEL returns transaction nesting level (§7.1.7)."""
    result = execute_mumps('TEST TSTART W $TL Q')
    assert result.output == "1"
    assert result.success is True
```

### Requirements
1. Remove `@pytest.mark.xfail` decorator
2. Update docstring to reference spec section
3. Add `assert result.success is True` where applicable
4. Verify output matches expected MUMPS behavior

---

## Pattern 2: Error Handling (Limitation)

When a feature is documented as unsupported (LIM-XXX), convert to verify the error.

### Before (xfail)
```python
@pytest.mark.xfail(reason="LIM-014: Math library not implemented")
def test_math_sin_codegen(self, generate_python):
    """$$%SIN^MATH generates Python math call."""
    code = generate_python('TEST W $$%SIN^MATH(1) Q')
    assert "math.sin" in code
```

### After (passing)
```python
def test_math_sin_codegen(self, generate_python):
    """$$%SIN^MATH raises NotImplementedError (LIM-014).
    
    Reference: docs/limitations.md - LIM-014: ANSI Library Functions
    """
    with pytest.raises(NotImplementedError, match="LIM-014"):
        generate_python('TEST W $$%SIN^MATH(1) Q')
```

### Requirements
1. Remove `@pytest.mark.xfail` decorator
2. Change assertion to `pytest.raises(NotImplementedError, match="LIM-XXX")`
3. Update docstring to explain it's a limitation test
4. Add reference to docs/limitations.md

---

## Pattern 3: Blocked (Dependency)

When a test is blocked on another spec, keep as xfail with clear documentation.

### Format
```python
@pytest.mark.xfail(
    reason="Blocked: Spec 006 (cross-label GOTO) required",
    strict=False  # Allow unexpected pass
)
def test_goto_computed(self, generate_python):
    """GOTO with computed offset (G LABEL+n).
    
    Dependency: Spec 006 cross-label infrastructure
    """
    code = generate_python('TEST G NEXT+1 Q\nNEXT Q')
    assert "state_machine" in code or "dispatch" in code
```

### Requirements
1. Reason MUST include "Blocked: Spec NNN"
2. `strict=False` allows unexpected pass when dependency implemented
3. Docstring MUST document the dependency

---

## Test Class Organization

### Error Handling Tests
```python
@pytest.mark.codegen
class TestAnsiLibraryErrorHandling:
    """Tests for ANSI library function error handling (LIM-014).
    
    These functions parse correctly but are not implemented.
    Codegen must raise NotImplementedError with LIM-014 in message.
    
    Reference: docs/limitations.md - LIM-014
    """
    
    def test_lim014_math_sin_raises_error(self, generate_python):
        """$$%SIN^MATH raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST W $$%SIN^MATH(1) Q')
```

### Implementation Tests
```python
@pytest.mark.codegen
class TestTransactionCodegen:
    """Tests for transaction command code generation (§6.3.1).
    
    Reference: MUMPS 1995 Standard, Section 6.3.1
    """
    
    def test_tstart_to_begin(self, execute_mumps):
        """TSTART begins a transaction."""
        result = execute_mumps('TEST TSTART W "OK" Q')
        assert result.output == "OK"
```

---

## Naming Conventions

### Test Names
| Pattern | Use Case | Example |
|---------|----------|---------|
| `test_lim{NNN}_{feature}` | Limitation error test | `test_lim014_math_sin_raises_error` |
| `test_{feature}_{behavior}` | Implementation test | `test_tstart_begins_transaction` |
| `test_{feature}_codegen` | Codegen output test | `test_merge_global_codegen` |

### Class Names
| Pattern | Use Case | Example |
|---------|----------|---------|
| `Test{Feature}ErrorHandling` | Limitation tests | `TestAnsiLibraryErrorHandling` |
| `Test{Feature}Codegen` | Implementation tests | `TestTransactionCodegen` |

---

## Validation Commands

```bash
# Check no remaining xfail in a test file
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py --collect-only -m xfail -q

# Verify test passes
uv run pytest tests/unit/codegen/s7_expressions/test_s7_1_3_ssvns.py::TestMwapiSsvnsCodegen -v

# Check for xpass (unexpected pass)
uv run pytest --tb=short 2>&1 | grep -i xpass
```

---

## Anti-Patterns

### ❌ DON'T: Remove tests without implementing
```python
# BAD: Just deleting the test
# (test removed)
```

### ❌ DON'T: Leave xfail when fixed
```python
# BAD: Implementation done but xfail remains
@pytest.mark.xfail(reason="Fixed but forgot to remove")
def test_feature(self):
    result = execute_mumps('...')  # This now works!
    assert result.output == "expected"
```

### ❌ DON'T: Use generic NotImplementedError match
```python
# BAD: Match anything
with pytest.raises(NotImplementedError):
    generate_python('...')

# GOOD: Match specific limitation
with pytest.raises(NotImplementedError, match="LIM-014"):
    generate_python('...')
```

### ❌ DON'T: Duplicate tests
```python
# BAD: Same test in multiple files
# test_s7_1_6_5_library_functions_math.py has test_math_sin
# test_math_library.py also has test_math_sin  # DUPLICATE!
```
