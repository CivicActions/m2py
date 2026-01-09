# Research: Minimal Control Flow Foundation

**Date**: 2026-01-09  
**Feature**: [spec.md](spec.md)

## Resolved Questions

### Q1: What is the exact ASG structure for each statement type?

**Decision**: Use existing ASG classes directly

**Rationale**: The parser already produces well-structured ASG nodes:
- `MSetStatement.assignments[].target` → `MVariable` with `name` field
- `MSetStatement.assignments[].value` → `MExpr` subclass
- `MWriteStatement.arguments` → list of `MExpr` or `MFormatControl`
- `MIfStatement.condition` / `conditions` → single or multiple `MExpr`
- `MForStatement.parameters` → `MForParameter` with `param_type`, `start`, `step`, `end`, `value`
- `MDoStatement.targets` → `MCall` with `name`, `target` (resolved label)
- `MGotoStatement.targets` → `MCall` with `name`, `target` (resolved label)

**Alternatives considered**: 
- Creating wrapper types: Rejected (adds indirection without benefit)
- String manipulation: Rejected (loses type safety)

---

### Q2: Where should coercion helpers live?

**Decision**: Create `src/m2py/codegen/helpers.py` with pure functions

**Rationale**: 
- Pure functions can be inlined in generated code
- No runtime state required for coercion logic
- Easy to unit test in isolation
- Matches Constitution VII (minimize runtime)

**Alternatives considered**:
- In MUMPSRuntime class: Rejected (would force runtime import for simple operations)
- Inline in expression generator: Rejected (duplicates logic, harder to test)

---

### Q3: How should $TEST be tracked?

**Decision**: Module-level `_test` variable with `global _test` in each function

**Rationale**:
- Simple and explicit
- Maps to MUMPS's process-wide $TEST
- Easy to extend for $TEST stacking in Spec 005
- Follows existing pattern from codegen-plan.md

**Alternatives considered**:
- Thread-local: Overkill for single-threaded transpilation
- MUMPSRuntime.test property: Would require runtime for IF/ELSE

---

### Q4: How to handle name translation edge cases?

**Decision**: `NameTranslator` class with reversible mapping

| MUMPS Pattern | Python Translation | Reverse |
|---------------|-------------------|---------|
| `%FOO` | `_pct_FOO` | Strip `_pct_` prefix |
| `01` (pure numeric) | `_n_01` | Strip `_n_` prefix |
| `if` (reserved) | `_m_if` | Strip `_m_` prefix |
| `FOO` (normal) | `FOO` | Identity |

**Rationale**:
- Prefixes are unambiguous (don't collide)
- Case preserved (FOO ≠ foo)
- Leading zeros preserved (01 ≠ 1)
- Reversible for debugging/error messages

**Alternatives considered**:
- Hash-based mangling: Rejected (not human-readable)
- Universal prefix: Rejected (verbose for common cases)

---

### Q5: What's the minimal MUMPSRuntime API for Spec 004?

**Decision**: Three methods only

```python
class MUMPSRuntime:
    def __init__(self):
        self._output: list[str] = []
    
    def write(self, value: str) -> None:
        """Capture WRITE output."""
        self._output.append(value)
    
    def get_output(self) -> str:
        """Return accumulated output."""
        return "".join(self._output)
    
    def execute(self, python_code: str, capture_output: bool = True) -> ExecutionResult:
        """Execute generated Python code."""
        ...
```

**Rationale**:
- WRITE needs output capture for testing
- No variable storage (locals are Python locals)
- No $TEST access (handled by `_test` global)
- Minimal surface per Constitution VII

---

### Q6: How to generate FOR loops?

**Decision**: Pattern by `ForParamType`

| ForParamType | Python Pattern |
|--------------|----------------|
| RANGE (bounded) | `for i in range(start, end + 1, step):` (adjusted for M inclusive end) |
| OPEN_RANGE | `while True:` with manual increment (deferred to Spec 005) |
| VALUE (list) | `for i in [v1, v2, v3]:` |

**Rationale**:
- BOUNDED → Python range handles most cases
- List iteration → Python for-in
- Off-by-one risk: MUMPS FOR is end-inclusive; Python range is end-exclusive

**Implementation note**: For decreasing ranges (step < 0), need `range(start, end - 1, step)` to include end value.

---

### Q7: How to handle GOTO within same routine?

**Decision**: Labels-as-functions with direct calls (Spec 004 only handles intra-routine)

```python
def TEST():
    X = 1
    return DONE()  # GOTO DONE
    X = 2  # Unreachable

def DONE():
    _rt.write(str(X))  # But X isn't visible!
```

**Problem identified**: Cross-label variable visibility. For Spec 004, defer complex GOTO patterns to Spec 006. Support only:
1. Forward GOTO to label at end (can restructure as early return)
2. Conditional GOTO (can restructure as if/else)

**Alternatives considered**:
- State machine: Deferred to Spec 006 for complex cases
- Exception-based jumps: Overly complex for simple cases

---

## Key Implementation Decisions

### Generated Code Structure

```python
# Header (always)
from m2py.codegen.helpers import m_num, m_truth, m_compare

# Runtime instance (always)
_rt = MUMPSRuntime()

# $TEST tracking (always)
_test = False

# Labels as functions
def TEST():
    global _test
    X = 1
    _rt.write(str(X))

def SUB():
    global _test
    _rt.write("SUB")

# Entry point
if __name__ == "__main__":
    TEST()
```

### Expression Generation Rules

| ASG Node | Python Output |
|----------|---------------|
| `MLiteral(value=1, literal_type=INTEGER)` | `1` |
| `MLiteral(value="foo", literal_type=STRING)` | `"foo"` |
| `MVariable(name="X")` | `X` (translated) |
| `MBinaryOp(op="+", left, right)` | `m_num(left) + m_num(right)` |
| `MBinaryOp(op="=", left, right)` | `m_compare(left, "=", right)` |
| `MBinaryOp(op="<", left, right)` | `m_compare(left, "<", right)` |

### Statement Generation Rules

| ASG Node | Python Output |
|----------|---------------|
| `MSetStatement` | `var = value` |
| `MWriteStatement` | `_rt.write(str(value))` |
| `MQuitStatement` (no value) | `return` |
| `MIfStatement` | `if m_truth(cond): ...` |
| `MElseStatement` | `if not _test: ...` |
| `MForStatement` (bounded) | `for var in range(...): ...` |
| `MDoStatement` | `label_func()` |
| `MGotoStatement` | `return label_func()` (simple case) |

---

## Dependencies for Implementation

1. **Existing**: `CodeEmitter` ✓
2. **Existing**: ASG classes ✓  
3. **Existing**: Analysis infrastructure ✓
4. **New**: `helpers.py` - m_num, m_truth, m_compare
5. **New**: `names.py` - NameTranslator
6. **New**: `expressions.py` - generate_expr()
7. **New**: `statements.py` - generate_statement()
8. **New**: `routine.py` - RoutineGenerator
9. **New**: `codegen/__init__.py` - generate_python() public API
10. **New**: `runtime/__init__.py` - MUMPSRuntime class
