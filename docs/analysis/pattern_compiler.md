# Pattern Compiler

The pattern compiler converts MUMPS pattern match expressions to Python regex.

**Source**: [`src/m2py/analysis/pattern_compiler.py`](../../src/m2py/analysis/pattern_compiler.py)

## Overview

MUMPS has a built-in pattern matching operator (`?`) with its own syntax:

```mumps
IF X?1A.N WRITE "Valid"
```

This module converts MUMPS patterns to Python regex for runtime matching.

## Usage

```python
from m2py.analysis.pattern_compiler import compile_pattern_to_regex
import re

# Convert MUMPS pattern to regex
pattern = "1A.N"  # One letter, any digits
regex = compile_pattern_to_regex(pattern)
# regex = "[A-Za-z][0-9]*"

# Use with Python regex
if re.fullmatch(regex, value):
    print("Match!")
```

## MUMPS Pattern Codes

| Code | Meaning | Regex Equivalent |
|------|---------|------------------|
| `A` | Alphabetic (a-z, A-Z) | `[A-Za-z]` |
| `C` | Control (ASCII 0-31, 127) | `[\x00-\x1f\x7f]` |
| `E` | Everything (any char) | `.` |
| `L` | Lowercase (a-z) | `[a-z]` |
| `N` | Numeric (0-9) | `[0-9]` |
| `P` | Punctuation (space + symbols) | `[ !"#$%...]` |
| `U` | Uppercase (A-Z) | `[A-Z]` |

### Combined Codes

Pattern codes can be combined to match any of them:

```mumps
X?1AN      ; One alphanumeric
```
```python
"[A-Za-z0-9]"
```

## Repeat Count Syntax

| Syntax | Meaning | Regex |
|--------|---------|-------|
| `n` | Exactly n | `{n}` |
| `n.` | At least n | `{n,}` |
| `.n` | At most n (0 to n) | `{0,n}` |
| `n.m` | Between n and m | `{n,m}` |
| `.` | Any number (0+) | `*` |

### Examples

| MUMPS | Meaning | Regex |
|-------|---------|-------|
| `3N` | Exactly 3 digits | `[0-9]{3}` |
| `1.A` | 1 or more letters | `[A-Za-z]+` |
| `.5N` | 0 to 5 digits | `[0-9]{0,5}` |
| `2.4A` | 2 to 4 letters | `[A-Za-z]{2,4}` |
| `.N` | Any number of digits | `[0-9]*` |

## String Literals

Literal strings are quoted:

```mumps
X?3N1"-"4N    ; 3 digits, dash, 4 digits
```
```python
"[0-9]{3}-[0-9]{4}"  # Phone format
```

Double quotes escape quotes:

```mumps
X?1"He said ""Hi"""
```

## Alternation

Parentheses with commas for alternatives:

```mumps
X?(1"Mr",1"Mrs",1"Ms")1" "1.A
```

Matches "Mr Smith", "Mrs Jones", "Ms Doe".

```python
"(?:Mr|Mrs|Ms) [A-Za-z]+"
```

## Complete Examples

### US Phone Number

```mumps
X?3N1"-"3N1"-"4N
```
```python
"[0-9]{3}-[0-9]{3}-[0-9]{4}"
```

### Valid Identifier

```mumps
X?1A.AN
```
```python
"[A-Za-z][A-Za-z0-9]*"
```

### Date Format

```mumps
X?(1N,2N)1"/"(1N,2N)1"/"4N
```
```python
"(?:[0-9]|[0-9]{2})/(?:[0-9]|[0-9]{2})/[0-9]{4}"
```

### Email (simplified)

```mumps
X?1.AN1"@"1.AN1"."2.4A
```
```python
"[A-Za-z0-9]+@[A-Za-z0-9]+\.[A-Za-z]{2,4}"
```

## Error Handling

```python
from m2py.analysis.pattern_compiler import (
    compile_pattern_to_regex,
    PatternCompileError
)

try:
    regex = compile_pattern_to_regex("1X")  # Invalid code
except PatternCompileError as e:
    print(f"Pattern error: {e}")
```

## Code Generation

For pattern match expressions in MUMPS:

```mumps
IF X?1A.N W "Valid"
```

Generate:

```python
import re
if re.fullmatch(r"[A-Za-z][0-9]*", x):
    print("Valid")
```

### Precompilation for Performance

For patterns used in loops:

```python
# At module level
_PATTERN_1A_N = re.compile(r"[A-Za-z][0-9]*")

# In generated code
if _PATTERN_1A_N.fullmatch(x):
    print("Valid")
```

## Internal Functions

| Function | Purpose |
|----------|---------|
| `compile_pattern_to_regex()` | Main entry point |
| `_parse_pattern_atom()` | Parse one pattern element |
| `_parse_repeat_count()` | Parse n, n., .n, n.m |
| `_parse_string_literal()` | Parse quoted strings |
| `_parse_alternation()` | Parse (alt1,alt2) |
| `_apply_quantifier()` | Convert count to regex quantifier |
| `_combine_patcodes()` | Merge multiple codes into char class |

## Limitations

The current implementation handles standard MUMPS patterns. Some edge cases:

- Unicode: MUMPS pattern codes are ASCII-based
- Locale: Pattern behavior may vary by MUMPS implementation
- Complex nesting: Deeply nested alternations supported but generate complex regex
