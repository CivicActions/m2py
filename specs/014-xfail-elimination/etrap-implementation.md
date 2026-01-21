# $ETRAP/$ECODE Implementation Plan

**Status**: Research Complete, Ready for Implementation  
**Related Tasks**: T055-T056 (Task B4: Error Processing)  
**Branch**: `014-xfail-elimination`

## Executive Summary

This document details the implementation plan for MUMPS $ETRAP/$ECODE error handling semantics in m2py. Based on extensive research of MUMPS standards, YottaDB behavior, and VistA usage patterns (527 files use $ETRAP), we've identified an approach that achieves 100% semantic fidelity with manageable complexity.

---

## 1. MUMPS Error Handling Semantics

### 1.1 Core Behavior (from YDB ProgrammersGuide/errproc.rst)

When an error occurs with $ETRAP non-empty:

1. **$ECODE is set** to the error code (e.g., ",M9,")
2. **$ETRAP code executes** "as if inserted at the point of the error"
3. **Implicit QUIT follows**: After $ETRAP completes, `QUIT:$QUIT "" QUIT` executes
4. **Stack unwinding**: If $ECODE still non-empty at QUIT, $ETRAP re-invokes at caller's level
5. **Continues until**: $ECODE is cleared OR stack is exhausted

### 1.2 Key Semantic Details

| Aspect | Behavior |
|--------|----------|
| $ETRAP cleared $ECODE | Execution continues at caller (after the DO) |
| $ETRAP didn't clear $ECODE | Implicit QUIT, $ETRAP fires at caller's level |
| NEW $ETRAP | Saves/restores per stack frame (already implemented) |
| GOTO + error | Same stack level, returns to original caller after implicit QUIT |
| Error at top level | Process exits (no caller to return to) |

### 1.3 Verified YDB Test Cases

```mumps
; Test 1: Error with handler that clears $ECODE
MAIN
 W "MAIN start",!
 D TEST
 W "MAIN end",!        ; ← This prints after error is handled
 Q
TEST
 S $ETRAP="W ""TRAPPED"",! S $ECODE="""""
 S X=1/0               ; Error here
 W "After error",!     ; ← This does NOT print (implicit QUIT)
 Q

; Output: MAIN start / TRAPPED / MAIN end
```

```mumps
; Test 2: Nested NEW $ETRAP
TEST
 S $ETRAP="W ""OUTER"",! S $ECODE="""""
 D A
 W "TEST end",!
 Q
A N $ETRAP S $ETRAP="W ""A TRAP"",! S $ECODE="""""
 D B
 W "A end",!           ; ← Prints (A's handler cleared $ECODE)
 Q
B S X=1/0
 Q

; Output: A TRAP / A end / TEST end
```

```mumps
; Test 3: GOTO doesn't create stack frame
MAIN
 D TEST
 W "MAIN end",!
 Q
TEST
 S $ETRAP="W ""TRAPPED"",! S $ECODE="""""
 G SUB                 ; GOTO, not DO
SUB
 S X=1/0
 Q

; Output: TRAPPED / MAIN end
; (GOTO stays at $STACK=1, implicit QUIT returns to MAIN)
```

---

## 2. Current m2py Architecture

### 2.1 Code Generation Patterns

| Pattern | Python Output | Description |
|---------|---------------|-------------|
| Simple routine | `def TEST()`, `def SUB()` | One function per label |
| Trampoline (GOTO) | `def _TEST()`, `def _SUB()`, `def TEST()` (dispatcher) | Labels return `(next_label, state)` |
| DO blocks | Inline `while True: ... break` | No separate function |
| DO to label | Direct function call: `SUB(_rt, _scope=_scope)` | Creates Python stack frame |

### 2.2 Existing Infrastructure

- ✅ `_rt.etrap()` / `_rt.set_etrap()` - Store/retrieve $ETRAP code
- ✅ `_rt.ecode()` / `_rt.set_ecode()` - Store/retrieve $ECODE
- ✅ `_rt.execute_mumps(code, _scope)` - Execute MUMPS code dynamically (for XECUTE)
- ✅ `NewScopeManager.new_special_var("etrap", ...)` - NEW $ETRAP save/restore
- ❌ No error handler that invokes $ETRAP on exceptions

### 2.3 Key Insight: Stack Frame Alignment

MUMPS stack frames align with:
- **Simple functions**: Each `def LABEL()` = one MUMPS stack frame
- **Trampoline dispatcher**: The `def TEST()` entry point = one MUMPS stack frame
- **Trampoline labels**: `def _LABEL()` are NOT separate frames (GOTO stays at same level)

---

## 3. Implementation Plan

### 3.1 Overview

Add try/except wrappers at **MUMPS stack frame boundaries**:
1. Simple label functions (no trampoline)
2. Trampoline dispatcher functions (entry points)
3. NOT internal `_LABEL` trampoline functions

### 3.2 Runtime Changes

#### New Method: `_rt._handle_etrap(exception, scope)`

```python
def _handle_etrap(self, exc: Exception, _scope: dict) -> bool:
    """Handle an exception using $ETRAP if set.
    
    Args:
        exc: The Python exception that occurred
        _scope: Current variable scope
        
    Returns:
        True if error was handled ($ECODE cleared), False otherwise
        
    Side Effects:
        - Sets $ECODE based on exception type
        - Executes $ETRAP code via execute_mumps()
    """
    if not self._etrap:
        return False  # No handler, propagate exception
    
    # Map Python exception to MUMPS $ECODE
    self._ecode = self._exception_to_ecode(exc)
    self._zerror = str(exc)
    
    # Execute $ETRAP code
    try:
        self.execute_mumps(self._etrap, _scope)
    except Exception:
        # Error in $ETRAP itself - propagate original
        return False
    
    # Check if handler cleared $ECODE
    return self._ecode == ""
```

#### New Method: `_rt._exception_to_ecode(exception)`

```python
def _exception_to_ecode(self, exc: Exception) -> str:
    """Map Python exception to MUMPS error code.
    
    Returns comma-delimited $ECODE format: ",Mnn," or ",Zxxx,"
    """
    if isinstance(exc, ZeroDivisionError):
        return ",M9,"  # Divide by zero
    elif isinstance(exc, KeyError):
        return ",M6,"  # Undefined local variable
    elif isinstance(exc, MRuntimeError):
        return f",{exc.code},"
    # ... more mappings
    else:
        return ",Z150373210,"  # Generic error (YDB code)
```

### 3.3 Codegen Changes

#### 3.3.1 Simple Functions (routine.py)

Current:
```python
def SUB(_rt, _scope=None, **_kwargs):
    global _test
    _scope = _scope if _scope is not None else {}
    _rt.write("In SUB")
    _scope.setdefault('X', MArray()).value = (m_num(1) / m_num(0))
    return
```

New:
```python
def SUB(_rt, _scope=None, **_kwargs):
    global _test
    _scope = _scope if _scope is not None else {}
    try:
        _rt.write("In SUB")
        _scope.setdefault('X', MArray()).value = (m_num(1) / m_num(0))
        return
    except Exception as _e:
        if _rt._handle_etrap(_e, _scope):
            return  # Handler cleared $ECODE, implicit QUIT
        raise  # Propagate to caller
```

#### 3.3.2 Trampoline Dispatcher (routine.py)

Current:
```python
def TEST(_rt, _scope=None):
    """Trampoline dispatcher for routine execution."""
    _scope = _scope if _scope is not None else {}
    state = RoutineState()
    target: str | int | None = "TEST"

    while target is not None:
        func = _labels[target]
        target, state = func(_rt, state, _scope)

    return state
```

New:
```python
def TEST(_rt, _scope=None):
    """Trampoline dispatcher for routine execution."""
    _scope = _scope if _scope is not None else {}
    state = RoutineState()
    target: str | int | None = "TEST"

    while target is not None:
        try:
            func = _labels[target]
            target, state = func(_rt, state, _scope)
        except Exception as _e:
            if _rt._handle_etrap(_e, _scope):
                return state  # Handler cleared $ECODE, implicit QUIT
            raise  # Propagate to caller

    return state
```

#### 3.3.3 Internal Trampoline Labels (NO CHANGE)

`_TEST()`, `_SUB()` etc. do NOT get wrapped - they're not separate MUMPS stack frames.

### 3.4 Files to Modify

| File | Change |
|------|--------|
| `src/m2py/runtime/__init__.py` | Add `_handle_etrap()`, `_exception_to_ecode()` |
| `src/m2py/codegen/routine.py` | Modify `_generate_label()` to wrap body in try/except |
| `src/m2py/codegen/routine.py` | Modify `_generate_trampoline_code()` to wrap dispatcher loop |
| `tests/unit/codegen/s6_routine/test_s6_3_2_error_processing.py` | Convert xfail stub to real tests |
| `tests/unit/runtime/test_error_processing.py` | Add tests for `_handle_etrap()` |

---

## 4. Implementation Tasks

### Phase 1: Runtime Infrastructure

- [ ] **E001**: Add `_exception_to_ecode()` method to `MUMPSRuntime`
  - Map common Python exceptions to MUMPS error codes
  - Support custom `MRuntimeError` codes
  - Document mapping table

- [ ] **E002**: Add `_handle_etrap()` method to `MUMPSRuntime`
  - Check if $ETRAP is set
  - Set $ECODE and $ZERROR
  - Execute $ETRAP via `execute_mumps()`
  - Return whether $ECODE was cleared

- [ ] **E003**: Add unit tests for runtime error handling
  - Test `_exception_to_ecode()` mappings
  - Test `_handle_etrap()` with various scenarios
  - Test $ETRAP code that clears vs doesn't clear $ECODE

### Phase 2: Codegen - Simple Functions

- [ ] **E004**: Modify `_generate_label()` in `routine.py`
  - Detect when generating simple (non-trampoline) label
  - Wrap function body in try/except
  - Generate error handler that calls `_rt._handle_etrap()`

- [ ] **E005**: Add codegen tests for simple function error handling
  - Verify try/except is generated
  - Verify handler pattern is correct

### Phase 3: Codegen - Trampoline Pattern

- [ ] **E006**: Modify `_generate_trampoline_code()` in `routine.py`
  - Wrap the dispatcher's while loop in try/except
  - Return from dispatcher if error handled
  - Re-raise if not handled

- [ ] **E007**: Add codegen tests for trampoline error handling
  - Verify dispatcher has try/except
  - Verify `_LABEL` functions do NOT have try/except

### Phase 4: Integration Tests

- [ ] **E008**: Convert `test_error_propagation` xfail stub
  - Remove xfail marker
  - Add real assertions for error handling codegen

- [ ] **E009**: Add end-to-end error handling tests
  - Simple error with $ETRAP
  - Nested calls with NEW $ETRAP
  - GOTO + error (trampoline pattern)
  - Error propagation when $ECODE not cleared

### Phase 5: Validation

- [ ] **E010**: Run full test suite, verify xfail count decreased
- [ ] **E011**: Run coverage_check
- [ ] **E012**: Validate against YDB with complex VistA-like patterns

---

## 5. Error Code Mapping

| Python Exception | MUMPS $ECODE | Description |
|-----------------|--------------|-------------|
| `ZeroDivisionError` | `,M9,` | Divide by zero |
| `KeyError` (undefined var) | `,M6,` | Undefined local variable |
| `MRuntimeError("SELECTFALSE")` | `,M4,` | No $SELECT argument true |
| `MRuntimeError("RANDARGNEG")` | `,M28,` | $RANDOM argument negative |
| `IndirectionError` | `,M26,` | Non-existent environment |
| `LabelNotFoundError` | `,M13,` | Label not found |
| `RuntimeError("NAKEDERR")` | `,M1,` | Naked reference error |
| `RuntimeError("M44")` | `,M44,` | TCOMMIT without TSTART |
| Other | `,Z150373210,` | Generic system error |

---

## 6. VistA Compatibility Notes

### Common VistA Pattern (fully supported)
```mumps
MAIN
 N $ETRAP,$ESTACK S $ETRAP="D ERR^ROUTINE Q"
 ; ... code that might error ...
 Q
ERR
 ; Log error
 S $ECODE=""  ; Clear to continue
 Q
```

### What This Implementation Supports
- ✅ $ETRAP as MUMPS code string executed on error
- ✅ $ECODE clearing to continue execution
- ✅ Error propagation when $ECODE not cleared
- ✅ NEW $ETRAP for per-frame handlers
- ✅ GOTO-based control flow (trampoline pattern)
- ✅ Nested DO calls with different handlers

### Not Yet Supported (future work)
- ⚠️ $ESTACK tracking (relative stack depth)
- ⚠️ $ZTRAP (legacy error handling - less common in VistA)
- ⚠️ Device EXCEPTION handlers

---

## 7. Testing Strategy

### Unit Tests (runtime)
```python
def test_handle_etrap_clears_ecode():
    rt = MUMPSRuntime()
    rt.set_etrap('S $ECODE=""')
    scope = {}
    result = rt._handle_etrap(ZeroDivisionError(), scope)
    assert result == True  # Handler cleared $ECODE
    assert rt.ecode() == ""

def test_handle_etrap_preserves_ecode():
    rt = MUMPSRuntime()
    rt.set_etrap('W "Logged"')  # Doesn't clear $ECODE
    scope = {}
    result = rt._handle_etrap(ZeroDivisionError(), scope)
    assert result == False  # $ECODE not cleared
    assert rt.ecode() == ",M9,"
```

### Codegen Tests
```python
def test_simple_function_has_error_handling(generate_python):
    result = generate_python('TEST S X=1 Q')
    assert 'try:' in result
    assert '_rt._handle_etrap(_e, _scope)' in result

def test_trampoline_dispatcher_has_error_handling(generate_python):
    result = generate_python('TEST G NEXT Q\nNEXT W 1 Q')
    # Dispatcher should have try/except
    assert 'while target is not None:' in result
    assert 'except Exception as _e:' in result
```

### Integration Tests (via validate.py)
```python
def test_error_handling_e2e():
    code = '''TEST
 S $ETRAP="W ""TRAPPED"",! S $ECODE="""""
 D SUB
 W "After",!
 Q
SUB S X=1/0 Q'''
    # Should output: TRAPPED / After
    result = run_m2py(code)
    assert "TRAPPED" in result
    assert "After" in result
```

---

## 8. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Performance overhead of try/except | Low | Python try/except has minimal overhead when no exception |
| Complex GOTO patterns | Medium | Trampoline already handles; wrap dispatcher only |
| $ETRAP code with errors | Low | Catch errors in $ETRAP execution, propagate original |
| Incomplete exception mapping | Low | Default to generic error code; expand mapping as needed |

---

## 9. Success Criteria

1. ✅ `test_error_propagation` xfail converted to passing test
2. ✅ All existing tests still pass
3. ✅ VistA-like error patterns work correctly (verified via YDB comparison)
4. ✅ NEW $ETRAP correctly scopes handlers
5. ✅ Trampoline (GOTO) patterns handle errors at correct stack level
