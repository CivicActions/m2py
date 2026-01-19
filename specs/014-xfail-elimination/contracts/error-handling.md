# Contract: Limitation Error Handling

**Version**: 1.0 | **Status**: Draft | **Spec**: [spec.md](../spec.md)

## Overview

This contract defines the error handling behavior for documented limitations.
When codegen encounters a feature documented in `docs/limitations.md` with type
`PARSES_OK`, it MUST raise `NotImplementedError` with the limitation ID.

---

## Error Format

### Required Format
```python
raise NotImplementedError("LIM-XXX: {human-readable description}")
```

### Components
| Component | Description | Example |
|-----------|-------------|---------|
| `LIM-XXX` | Limitation ID from limitations.py | `LIM-014` |
| Description | Human-readable explanation | `ANSI library function $$%SIN^MATH not implemented` |

---

## Limitation ID Mapping

### LIM-003: MWAPI SSVNs
```python
# Trigger: ^$EVENT, ^$WINDOW, ^$DISPLAY
raise NotImplementedError("LIM-003: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) not supported")
```

### LIM-011: ^$LIBRARY
```python
# Trigger: ^$LIBRARY(name)
raise NotImplementedError("LIM-011: ^$LIBRARY SSVN not supported")
```

### LIM-014: ANSI Library Functions
```python
# Trigger: $$%FUNC^MATH, $$%FUNC^STRING, $$%FUNC^CHARACTER
raise NotImplementedError(f"LIM-014: ANSI library function $$%{name}^{routine} not implemented")
```

### LIM-015: YDB Z-Commands
```python
# Trigger: ZBREAK, ZEDIT, ZCOMPILE, etc.
raise NotImplementedError(f"LIM-015: {command} command not implemented (zero VistA usage)")
```

### LIM-016: Zero-VistA Features
```python
# Trigger: TROLLBACK:n, $TRESTART, legacy behaviors
raise NotImplementedError(f"LIM-016: {feature} not implemented (zero VistA usage)")
```

---

## Test Contract

### Test Pattern
```python
def test_lim_xxx_feature(self, generate_python):
    """Feature raises NotImplementedError (LIM-XXX).
    
    Reference: docs/limitations.md - LIM-XXX
    """
    with pytest.raises(NotImplementedError, match="LIM-XXX"):
        generate_python('TEST W unsupported_feature Q')
```

### Test Requirements
1. Test name SHOULD include limitation ID: `test_lim003_*`, `test_lim014_*`
2. Test docstring MUST reference limitation
3. Match pattern MUST use limitation ID: `match="LIM-XXX"`
4. Test MUST NOT be marked xfail

---

## Implementation Checklist

### SSVN Handler (expressions.py)
- [ ] LIM-003: ^$EVENT → NotImplementedError
- [ ] LIM-003: ^$WINDOW → NotImplementedError
- [ ] LIM-003: ^$DISPLAY → NotImplementedError
- [ ] LIM-011: ^$LIBRARY → NotImplementedError

### Extrinsic Handler (expressions.py)
- [ ] LIM-014: $$%*^MATH → NotImplementedError
- [ ] LIM-014: $$%*^STRING → NotImplementedError
- [ ] LIM-014: $$%*^CHARACTER → NotImplementedError

### Statement Handler (statements.py)
- [ ] LIM-015: Z-commands → NotImplementedError
- [ ] LIM-016: TROLLBACK:n → NotImplementedError

---

## Validation

```bash
# Verify error message format
uv run python -c "
from m2py import transpile
try:
    transpile('TEST W ^$EVENT(1) Q')
except NotImplementedError as e:
    assert 'LIM-003' in str(e), 'Missing LIM-003 in error'
    print('✓ LIM-003 error format correct')
"
```
