# Math Functions Contract

**Spec**: 013-test-consolidation  
**Scope**: Mathematical intrinsic functions (FR-034 through FR-038)

## Overview

Standard MUMPS math functions map directly to Python's `math` module.

| Function | MUMPS | Python | Notes |
|----------|-------|--------|-------|
| Exponential | $EXP(x) | math.exp(x) | e^x |
| Natural Log | $LOG(x) | math.log(x) | ln(x) |
| Square Root | $SQRT(x) | math.sqrt(x) | √x |
| Sine | $SIN(x) | math.sin(x) | radians |
| Cosine | $COS(x) | math.cos(x) | radians |
| Tangent | $TAN(x) | math.tan(x) | radians |
| Arc Sine | $ARCSIN(x) | math.asin(x) | radians |
| Arc Cosine | $ARCCOS(x) | math.acos(x) | radians |
| Arc Tangent | $ARCTAN(x) | math.atan(x) | radians |

---

## $EXP Function (FR-034)

**MUMPS**: `$EXP(number)`

**Behavior**:
- Returns e raised to the power of number
- Argument must be numeric

**Examples**:
```mumps
W $EXP(0)    ; 1
W $EXP(1)    ; 2.718281828... (e)
W $EXP(2)    ; 7.389056099...
```

**Python Implementation**:
```python
import math

def _exp(x: str) -> str:
    return str(math.exp(m_num(x)))
```

---

## $LOG Function (FR-035)

**MUMPS**: `$LOG(number)`

**Behavior**:
- Returns natural logarithm (base e)
- Argument must be positive

**Examples**:
```mumps
W $LOG(1)    ; 0
W $LOG(2.718281828)  ; ~1
W $LOG(10)   ; 2.302585093...
```

**Error Handling**:
- $LOG(0) → domain error
- $LOG(-1) → domain error

**Python Implementation**:
```python
def _log(x: str) -> str:
    n = m_num(x)
    if n <= 0:
        raise ValueError("DOMAIN error in $LOG")
    return str(math.log(n))
```

---

## $SQRT Function (FR-036)

**MUMPS**: `$SQRT(number)`

**Behavior**:
- Returns square root
- Argument must be non-negative

**Examples**:
```mumps
W $SQRT(4)   ; 2
W $SQRT(2)   ; 1.414213562...
W $SQRT(0)   ; 0
```

**Error Handling**:
- $SQRT(-1) → domain error

**Python Implementation**:
```python
def _sqrt(x: str) -> str:
    n = m_num(x)
    if n < 0:
        raise ValueError("DOMAIN error in $SQRT")
    return str(math.sqrt(n))
```

---

## Trigonometric Functions (FR-037)

### $SIN(x)

**MUMPS**: `$SIN(radians)`

**Examples**:
```mumps
W $SIN(0)          ; 0
W $SIN(3.14159/2)  ; ~1 (sin π/2)
W $SIN(3.14159)    ; ~0 (sin π)
```

### $COS(x)

**MUMPS**: `$COS(radians)`

**Examples**:
```mumps
W $COS(0)          ; 1
W $COS(3.14159/2)  ; ~0 (cos π/2)
W $COS(3.14159)    ; -1 (cos π)
```

### $TAN(x)

**MUMPS**: `$TAN(radians)`

**Examples**:
```mumps
W $TAN(0)          ; 0
W $TAN(3.14159/4)  ; ~1 (tan π/4)
```

**Error Handling**:
- $TAN(π/2) → infinity (domain consideration)

**Python Implementation**:
```python
def _sin(x: str) -> str:
    return str(math.sin(m_num(x)))

def _cos(x: str) -> str:
    return str(math.cos(m_num(x)))

def _tan(x: str) -> str:
    return str(math.tan(m_num(x)))
```

---

## Inverse Trigonometric Functions (FR-038)

### $ARCSIN(x)

**MUMPS**: `$ARCSIN(number)` where -1 ≤ number ≤ 1

**Returns**: Radians in range [-π/2, π/2]

**Examples**:
```mumps
W $ARCSIN(0)   ; 0
W $ARCSIN(1)   ; 1.570796327 (π/2)
W $ARCSIN(-1)  ; -1.570796327 (-π/2)
```

### $ARCCOS(x)

**MUMPS**: `$ARCCOS(number)` where -1 ≤ number ≤ 1

**Returns**: Radians in range [0, π]

**Examples**:
```mumps
W $ARCCOS(1)   ; 0
W $ARCCOS(0)   ; 1.570796327 (π/2)
W $ARCCOS(-1)  ; 3.14159265 (π)
```

### $ARCTAN(x)

**MUMPS**: `$ARCTAN(number)` (any real number)

**Returns**: Radians in range (-π/2, π/2)

**Examples**:
```mumps
W $ARCTAN(0)   ; 0
W $ARCTAN(1)   ; 0.785398163 (π/4)
```

**Error Handling**:
- $ARCSIN(2) → domain error (|x| must be ≤ 1)
- $ARCCOS(2) → domain error (|x| must be ≤ 1)

**Python Implementation**:
```python
def _arcsin(x: str) -> str:
    n = m_num(x)
    if n < -1 or n > 1:
        raise ValueError("DOMAIN error in $ARCSIN")
    return str(math.asin(n))

def _arccos(x: str) -> str:
    n = m_num(x)
    if n < -1 or n > 1:
        raise ValueError("DOMAIN error in $ARCCOS")
    return str(math.acos(n))

def _arctan(x: str) -> str:
    return str(math.atan(m_num(x)))
```

---

## Precision Considerations

MUMPS implementations typically provide at least 15 significant digits. Python's `float` (IEEE 754 double) provides ~15-17 significant digits, which is compatible.

For output formatting, results should match YDB output:
- Use `validate.py` to verify exact output format
- May need to handle trailing zeros or scientific notation
