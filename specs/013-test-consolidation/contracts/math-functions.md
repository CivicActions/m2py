# Math Library Functions Contract

**Spec**: 013-test-consolidation  
**Scope**: Mathematical library functions (FR-034 through FR-038)

## Overview

Standard MUMPS math functions are NOT intrinsics (like $LENGTH or $PIECE). Instead, they are
implemented as **library functions** using the standard extrinsic function syntax:

```mumps
; Standard MUMPS library function syntax
W $$%SIN^MATH(radians)    ; NOT $SIN(radians)
W $$%SQRT^MATH(4)         ; NOT $SQRT(4)
```

**Why Library Functions?**
1. The 1977/1990/1995 MUMPS standards do NOT define math functions as intrinsics
2. YDB rejects `$SIN(x)` with "Invalid function name"
3. Standard M implementations provide math via `%MATH` routine (or vendor-specific)
4. This approach is YDB-compatible and validates correctly

| Function | MUMPS Syntax | Python Implementation | Notes |
|----------|--------------|----------------------|-------|
| Exponential | $$%EXP^MATH(x) | math.exp(x) | e^x |
| Natural Log | $$%LOG^MATH(x) | math.log(x) | ln(x), alias %LN |
| Square Root | $$%SQRT^MATH(x) | math.sqrt(x) | √x |
| Sine | $$%SIN^MATH(x) | math.sin(x) | radians |
| Cosine | $$%COS^MATH(x) | math.cos(x) | radians |
| Tangent | $$%TAN^MATH(x) | math.tan(x) | radians |
| Arc Sine | $$%ARCSIN^MATH(x) | math.asin(x) | alias %ASIN |
| Arc Cosine | $$%ARCCOS^MATH(x) | math.acos(x) | alias %ACOS |
| Arc Tangent | $$%ARCTAN^MATH(x) | math.atan(x) | alias %ATAN |

---

## %MATH Routine Implementation

The `%MATH` routine provides all math functions as callable labels. In m2py, this is implemented
as a pre-compiled Python routine that can be called via the standard extrinsic function mechanism.

```python
# src/m2py/runtime/routines/MATH.py (or bundled routine)
import math
from m2py.runtime import m_num

def EXP(x):
    """$$%EXP^MATH(x) - returns e^x"""
    return str(math.exp(m_num(x)))

def LOG(x):
    """$$%LOG^MATH(x) - returns ln(x), domain error if x <= 0"""
    n = m_num(x)
    if n <= 0:
        raise ValueError("DOMAIN error in %LOG")
    return str(math.log(n))

# ... etc for each function
```

---

## $$%EXP^MATH Function (FR-034)

**MUMPS**: `$$%EXP^MATH(number)`

**Behavior**:
- Returns e raised to the power of number
- Argument must be numeric

**Examples**:
```mumps
W $$%EXP^MATH(0)    ; 1
W $$%EXP^MATH(1)    ; 2.718281828... (e)
W $$%EXP^MATH(2)    ; 7.389056099...
```

---

## $$%LOG^MATH Function (FR-035)

**MUMPS**: `$$%LOG^MATH(number)` (alias: `$$%LN^MATH`)

**Behavior**:
- Returns natural logarithm (base e)
- Argument must be positive

**Examples**:
```mumps
W $$%LOG^MATH(1)    ; 0
W $$%LOG^MATH(2.718281828)  ; ~1
W $$%LOG^MATH(10)   ; 2.302585093...
```

**Error Handling**:
- $$%LOG^MATH(0) → domain error
- $$%LOG^MATH(-1) → domain error

---

## $$%SQRT^MATH Function (FR-036)

**MUMPS**: `$$%SQRT^MATH(number)`

**Behavior**:
- Returns square root
- Argument must be non-negative

**Examples**:
```mumps
W $$%SQRT^MATH(4)   ; 2
W $$%SQRT^MATH(2)   ; 1.414213562...
W $$%SQRT^MATH(0)   ; 0
```

**Error Handling**:
- $$%SQRT^MATH(-1) → domain error

---

## Trigonometric Library Functions (FR-037)

### $$%SIN^MATH(x)

**MUMPS**: `$$%SIN^MATH(radians)`

**Examples**:
```mumps
W $$%SIN^MATH(0)          ; 0
W $$%SIN^MATH(3.14159/2)  ; ~1 (sin π/2)
W $$%SIN^MATH(3.14159)    ; ~0 (sin π)
```

### $$%COS^MATH(x)

**MUMPS**: `$$%COS^MATH(radians)`

**Examples**:
```mumps
W $$%COS^MATH(0)          ; 1
W $$%COS^MATH(3.14159/2)  ; ~0 (cos π/2)
W $$%COS^MATH(3.14159)    ; -1 (cos π)
```

### $$%TAN^MATH(x)

**MUMPS**: `$$%TAN^MATH(radians)`

**Examples**:
```mumps
W $$%TAN^MATH(0)          ; 0
W $$%TAN^MATH(3.14159/4)  ; ~1 (tan π/4)
```

**Error Handling**:
- $$%TAN^MATH(π/2) → infinity (domain consideration)
    return str(math.cos(m_num(x)))

def _tan(x: str) -> str:
    return str(math.tan(m_num(x)))
```

---

## Inverse Trigonometric Library Functions (FR-038)

### $$%ARCSIN^MATH(x) (alias: $$%ASIN^MATH)

**MUMPS**: `$$%ARCSIN^MATH(number)` where -1 ≤ number ≤ 1

**Returns**: Radians in range [-π/2, π/2]

**Examples**:
```mumps
W $$%ARCSIN^MATH(0)   ; 0
W $$%ARCSIN^MATH(1)   ; 1.570796327 (π/2)
W $$%ARCSIN^MATH(-1)  ; -1.570796327 (-π/2)
```

### $$%ARCCOS^MATH(x) (alias: $$%ACOS^MATH)

**MUMPS**: `$$%ARCCOS^MATH(number)` where -1 ≤ number ≤ 1

**Returns**: Radians in range [0, π]

**Examples**:
```mumps
W $$%ARCCOS^MATH(1)   ; 0
W $$%ARCCOS^MATH(0)   ; 1.570796327 (π/2)
W $$%ARCCOS^MATH(-1)  ; 3.14159265 (π)
```

### $$%ARCTAN^MATH(x) (alias: $$%ATAN^MATH)

**MUMPS**: `$$%ARCTAN^MATH(number)` (any real number)

**Returns**: Radians in range (-π/2, π/2)

**Examples**:
```mumps
W $$%ARCTAN^MATH(0)   ; 0
W $$%ARCTAN^MATH(1)   ; 0.785398163 (π/4)
```

**Error Handling**:
- $$%ARCSIN^MATH(2) → domain error (|x| must be ≤ 1)
- $$%ARCCOS^MATH(2) → domain error (|x| must be ≤ 1)

---

## Implementation Approach

### Option A: Built-in %MATH Routine (Recommended)

m2py ships with a pre-compiled `%MATH` routine that the runtime automatically loads. When
user code calls `$$%SIN^MATH(x)`, the standard extrinsic function mechanism resolves the call.

```
User Code                          Generated Python
---------                          ----------------
W $$%SIN^MATH(3.14/2)   →   _write(_rt.call_extrinsic('%SIN', '%MATH', [str(3.14/2)]))
```

### Option B: Routine Search Path

The `%MATH` routine is discovered via the standard routine search path, allowing users
to override with their own implementation if needed.

### Validation

Unlike the intrinsic approach, this implementation can be validated against YDB:

```bash
# YDB accepts standard library function syntax
echo -e 'TEST\n W $$%SQRT^MATH(4),!' | docker run --rm -i ydb
; Expected output: 2
```

---

## Precision Considerations

MUMPS implementations typically provide at least 15 significant digits. Python's `float` (IEEE 754 double) provides ~15-17 significant digits, which is compatible.

For output formatting, results should match YDB output:
- Use `validate.py` to verify exact output format
- May need to handle trailing zeros or scientific notation
