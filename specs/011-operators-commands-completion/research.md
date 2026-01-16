# Research: Extended Operators, Commands & Completion

**Feature**: Spec 011 - Extended Operators, Commands & Completion
**Date**: 2026-01-15
**Branch**: `011-operators-commands-completion`

## Research Tasks

### 1. Extended Operators - Current State

**Decision**: Extend `_generate_binary_op()` with missing operators

**Current Implementation** (from `src/m2py/codegen/expressions.py:294-332`):
- ✅ Implemented: `+`, `-`, `*`, `/`, `\` (int div), `#` (modulo), `=`, `<`, `>`, `_` (concat)
- ❌ Missing: `&` (AND), `!` (OR), `[` (contains), `]` (follows), `]]` (sorts after), `?` (pattern match)
- ⚠️ Broken: `'` (NOT) returns Python `False` instead of `0`

**Rationale**: Binary operators dispatch via `_generate_binary_op()`. Each operator needs a Python translation with proper MUMPS semantics.

**Alternatives considered**: None - this is the established pattern.

### 2. Logical Operators Implementation

**Decision**: Use `m_truth()` for coercion, emit `int()` for MUMPS 0/1 output

**Pattern for AND**:
```python
# MUMPS: 1&1 → 1
# Python: int(m_truth(1) and m_truth(1))
```

**Pattern for OR**:
```python
# MUMPS: 1!0 → 1
# Python: int(m_truth(1) or m_truth(0))
```

**Pattern for NOT** (unary, fix existing):
```python
# MUMPS: '1 → 0
# Current (broken): (not m_truth(1)) → False
# Fixed: int(not m_truth(1)) → 0
```

**Rationale**: MUMPS boolean operations always produce 0 or 1, never True/False.

### 3. Contains and Follows Operators

**Decision**: Inline Python expressions with MUMPS semantics

**Contains `[`**:
```python
# MUMPS: "ABC"["B" → 1
# Python: int(str(right) in str(left))
```

**Follows `]`**:
```python
# MUMPS: "B"]"A" → 1 (B sorts after A)
# Python: int(str(left) > str(right))
```

**Sorts After `]]`**:
```python
# MUMPS: "B"]]"A" → 1 (B strictly after A in MUMPS collation)
# Per ANSI: empty string never sorts after anything
# Python: int(left != "" and str(left) > str(right))
```

**Rationale**: String comparison uses ASCII ordering which matches MUMPS for ASCII content.

### 4. Pattern Match Operator

**Decision**: Use existing `compile_pattern_to_regex()` in analysis/pattern_compiler.py

**Discovery**: The pattern compiler already exists at `src/m2py/analysis/pattern_compiler.py`.
- Function: `compile_pattern_to_regex(pattern: str) -> str`
- Returns Python regex for use with `re.fullmatch()`
- Supports all MUMPS pattern codes: A, C, E, L, N, P, U

**Pattern for `?`**:
```python
# MUMPS: "ABC"?1A.A → 1
# Python: int(bool(re.fullmatch(compile_pattern_to_regex("1A.A"), "ABC", re.DOTALL)))
```

**Note**: The pattern expression needs to be evaluated at codegen time if it's a literal,
or at runtime if it's a variable. For now, focus on literal patterns.

### 5. Format Controls - ASG Structure

**Discovery**: Format controls are already parsed to `MFormatControl` ASG nodes.

**From `src/m2py/analysis/semantic_analyzer.py:720-752`**:
- `Newline` → `MFormatControl(control_type=FormatControlType.NEWLINE)`
- `FormFeed` → `MFormatControl(control_type=FormatControlType.FORMFEED)`
- `Tab` → `MFormatControl(control_type=FormatControlType.TAB, argument=expr)`
- `CharCode` → `MFormatControl(control_type=FormatControlType.CHARCODE, argument=expr)`

**From `src/m2py/asg/enums.py`**:
```python
class FormatControlType(Enum):
    NEWLINE = auto()    # !
    FORMFEED = auto()   # #
    TAB = auto()        # ?n
    CHARCODE = auto()   # *n
```

**Decision**: Extend `_generate_write()` in statements.py to handle `MFormatControl` nodes.

### 6. Format Control Python Patterns

**NEWLINE `!`**:
```python
_rt.write("\n")
```

**FORMFEED `#`**:
```python
_rt.write("\f")
```

**TAB `?n`** (move to column n):
```python
# Requires runtime $X tracking
# If current column < n: write spaces to reach column n
_rt.write_tab(n)  # New runtime helper needed
```

**CHARCODE `*n`**:
```python
_rt.write(chr(int(n)))
```

### 7. Postconditions - Current State

**Discovery**: Postconditions are already in ASG structure.

From `src/m2py/asg/statements.py:25`:
```python
@dataclass
class MStatement(ASGElement):
    postcondition: Optional["MExpr"] = None
```

**Current codegen**: `generate_statement()` does NOT check postcondition.

**Decision**: Wrap statement execution in `if m_truth(postcondition):` when present.

**Pattern**:
```python
# MUMPS: S:X>3 Y=1
# Python:
if m_truth(X > 3):
    Y = 1
```

### 8. NEW Command - Scope Implementation

**Decision**: Use runtime or inline based on scope strategy

**SIMPLE_FUNCTIONS strategy** (default):
- Variables in `_scope` dict
- NEW X → save `_scope.get('X')`, set `_scope['X'] = MArray()`
- On exit → restore saved value

**TRAMPOLINE strategy**:
- Variables in `state` dataclass
- NEW X → save `state.X`, set `state.X = MArray()`
- On exit → restore saved value

**Challenge**: NEW is scoped - must restore on label/subroutine exit.
**Decision**: Generate try/finally for proper cleanup.

### 9. KILL Command - Current State

**Discovery**: `_generate_kill()` exists in `statements.py:2015-2100`.

**Current status**:
- ✅ Local variable kill (K X)
- ✅ Subscripted local kill (K X(1,2))
- ✅ Global kill (K ^G)
- ✅ Naked global kill (K ^(1,2))
- ❌ Exclusive kill not implemented (K (X,Y))
- ❌ Argumentless kill not implemented (K)

### 10. MERGE Command - Implementation

**Decision**: Use MArray.merge() method

**Pattern**:
```python
# MUMPS: M B=A
# Python (SIMPLE_FUNCTIONS):
_scope.setdefault('B', MArray()).merge(_scope.get('A', MArray()))
```

**For globals**:
```python
# MUMPS: M L=^G
# Python: Copy global tree to local
L = MArray()
L.merge(_rt.globals.get_tree("G"))
```

### 11. HANG and HALT Commands

**HANG**:
```python
# MUMPS: H 0.5
# Python:
import time
time.sleep(0.5)
```

**HALT** (argumentless H):
```python
# MUMPS: H
# Python:
raise SystemExit(0)  # Or sys.exit(0)
```

### 12. Special Variables - Implementation

**$HOROLOG**:
```python
# MUMPS epoch: December 31, 1840
# Python: Calculate days since epoch + seconds since midnight
import datetime
def _horolog():
    now = datetime.datetime.now()
    epoch = datetime.datetime(1840, 12, 31)
    days = (now.date() - epoch.date()).days
    seconds = now.hour * 3600 + now.minute * 60 + now.second
    return f"{days},{seconds}"
```

**$JOB**:
```python
import os
_job = os.getpid()
```

**$IO**:
```python
_io = "0"  # Default to principal device
```

**$X, $Y** (column/line tracking):
```python
# Requires runtime tracking via _rt
_rt._x = 0  # Column position
_rt._y = 0  # Line position
# Updated by _rt.write() based on output content
```

**$STORAGE**:
```python
_storage = 2147483647  # Return large value (Python has no fixed memory limit)
```

**$STACK**:
```python
# Track call depth in runtime
_rt._stack_level = 0  # Incremented on calls, decremented on returns
```

**$QUIT**:
```python
# Track whether current context was invoked as extrinsic
# 1 if in extrinsic function, 0 otherwise
# Decision: Use runtime flag `_rt._in_extrinsic` set by extrinsic call codegen
# When generating $$LABEL call, set flag True before call, restore after
_rt._in_extrinsic  # Returns 1 if True, 0 if False
```

### 13. READ Command - Implementation

**Basic READ**:
```python
# MUMPS: R X
# Python:
X = input()
```

**READ with timeout** (sets $TEST):
```python
# MUMPS: R X:timeout
# Python: Requires select/signal for timeout
import select
import sys

def _read_with_timeout(timeout):
    global _test
    ready, _, _ = select.select([sys.stdin], [], [], timeout)
    if ready:
        _test = 1
        return input()
    else:
        _test = 0
        return ""
```

### 14. Decimal Literals - Current State

**Discovery**: Decimal literals already work in expressions.

From `codegen/expressions.py:132-145`:
```python
elif lit.literal_type == LiteralType.DECIMAL:
    return str(lit.value)
```

**Verified**: `W 1.5+2.7` outputs `4.2` correctly.

## Summary of Implementation Order

Based on dependencies and priority:

### Phase 1: Operators (P1)
1. Fix NOT operator to return 0/1
2. Add AND operator (`&`)
3. Add OR operator (`!`)
4. Add negated comparisons (`'=`, `'<`, `'>`)

### Phase 2: Format Controls (P1)
1. Handle MFormatControl in _generate_write()
2. Implement NEWLINE, FORMFEED, CHARCODE
3. Implement TAB with column tracking

### Phase 3: Postconditions (P1)
1. Check postcondition in generate_statement()
2. Wrap statement in conditional

### Phase 4: Contains/Follows (P2)
1. Add contains (`[`)
2. Add follows (`]`)
3. Add sorts after (`]]`)

### Phase 5: Pattern Match (P2)
1. Import pattern compiler
2. Handle literal patterns
3. Handle variable patterns

### Phase 6: Commands (P2-P3)
1. Complete NEW command
2. Complete KILL command (exclusive)
3. Add MERGE command
4. Add HANG command
5. Add HALT command
6. Add READ command (basic)

### Phase 7: Special Variables (P2)
1. Add $HOROLOG, $JOB, $IO
2. Add $X, $Y with column tracking
3. Add $STORAGE, $STACK, $QUIT
