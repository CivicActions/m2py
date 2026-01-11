# FOR Loop Translation Strategies

Python code generation for MUMPS FOR loops.

## Overview

MUMPS FOR loops translate to different Python patterns based on:

1. **Loop type** (bounded, open-ended, argumentless, string-list, mixed)
2. **Internal control flow** (QUIT, GOTO)
3. **Loop variable modification**

## Analysis Fields

These fields are populated by analysis passes before code generation:

| Field | Purpose | Populated By |
|-------|---------|-------------|
| `loop_type` | Classification of loop structure | `analyze_for_loops` |
| `is_infinite` | Cannot exit naturally | `analyze_for_loops` |
| `has_internal_quit` | QUIT in body → `break` | `analyze_for_loops` |
| `has_internal_goto` | GOTO exits loop | `classify_gotos` |
| `loop_var_modified_in_body` | Uses `while` instead of `for` | `analyze_for_loops` |
| `exit_points` | GOTOs that exit this loop | `classify_gotos` |
| `has_cross_label_exit` | Exit jumps to different label | `classify_gotos` |
| `needs_exception_wrapper` | Wrap in try/except for multi-loop exit | `classify_gotos` |
| `exit_target` | Target label name (MUMPS name) | `classify_gotos` |

## Bounded FOR

`F I=1:1:10` translates to Python `range()` with adjusted end for MUMPS end-inclusive semantics.

```mumps
F I=1:1:3 W I
```

```python
_for_step = m_num(1)
_for_end = m_num(3) + (1 if _for_step > 0 else -1)
for I in range(m_num(1), _for_end, _for_step):
    _rt.write(str(I))
```

The step direction determines the end adjustment: `+1` for positive step, `-1` for negative.

### With Negative Step

```mumps
F I=10:-2:0 W I
```

```python
_for_step = m_num(-2)
_for_end = m_num(0) + (1 if _for_step > 0 else -1)  # Results in -1
for I in range(m_num(10), _for_end, _for_step):
    _rt.write(str(I))
```

## Open-Ended FOR

`F I=1:1` (no end value) uses `itertools.count()` for unbounded iteration.

```mumps
F I=1:1 D
. W I
. I I=3 Q
```

```python
for I in count(m_num(1), m_num(1)):
    _rt.write(str(I))
    _test = m_truth(m_compare(I, "=", 3))
    if _test:
        break
```

Open-ended FOR loops require QUIT or GOTO to exit.

## Argumentless FOR

`F` (no loop variable) translates to `while True:`.

```mumps
F  R X Q:X=""
```

```python
while True:
    X = _rt.read()
    _test = m_truth(m_compare(X, "=", ""))
    if _test:
        break
```

## String List FOR

`F I="A","B","C"` translates to Python list iteration.

```mumps
F I="A","B","C" W I
```

```python
for I in ["A", "B", "C"]:
    _rt.write(str(I))
```

## Mixed Parameters

`F I=1:1:3,"X",10:2:14` combines ranges and values using `itertools.chain()`.

```mumps
F I=1:1:3,"X",10:2:14 W I
```

```python
for I in chain(
    range(m_num(1), m_num(3) + (1 if m_num(1) > 0 else -1), m_num(1)),
    ["X"],
    range(m_num(10), m_num(14) + (1 if m_num(2) > 0 else -1), m_num(2))
):
    _rt.write(str(I))
```

## Loop Variable Modification

When the loop variable is SET inside the body, Python's `for` cannot be used because it would overwrite the modification. These loops use `while` with explicit stepping.

```mumps
F I=1:1:10 D
. S I=I+5
. W I
```

```python
I = m_num(1)
_for_step = m_num(1)
_for_end = m_num(10)
while (_for_step > 0 and I <= _for_end) or (_for_step < 0 and I >= _for_end):
    I = (m_num(I) + m_num(5))
    _rt.write(str(I))
    I = I + _for_step
```

The loop increment happens at the end of each iteration.

## GOTO Exiting Loop

### Single Loop Exit

When a GOTO exits just the current loop, it generates `break`:

```mumps
F I=1:1:100 D
. I ERR G DONE
. D WORK
DONE W "Done"
```

```python
for I in range(1, 101):
    _test = m_truth(ERR)
    if _test:
        break
    WORK()
# Label DONE continues here
_rt.write("Done")
```

### Multi-Loop Exit

When a GOTO exits multiple nested loops, it uses an exception pattern:

```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=Y G ALLDONE
ALLDONE W "Done"
```

```python
class _LoopExit(Exception):
    pass

try:
    for I in range(1, 11):
        for J in range(1, 11):
            _test = m_truth(m_compare(X, "=", Y))
            if _test:
                raise _LoopExit()
except _LoopExit:
    pass  # Multi-loop exit completed
# Label ALLDONE continues here
_rt.write("Done")
```

The `_LoopExit` exception class is generated in the module preamble only when needed.

## Decision Matrix

```python
def generate_for_loop(for_stmt):
    if for_stmt.loop_type == ForLoopType.ARGUMENTLESS:
        return generate_while_true(for_stmt)
    
    if for_stmt.loop_var_modified_in_body:
        return generate_while_loop(for_stmt)
    
    if for_stmt.loop_type == ForLoopType.OPEN_ENDED:
        return generate_for_count(for_stmt)
    
    if for_stmt.loop_type == ForLoopType.STRING_LIST:
        return generate_for_in_list(for_stmt)
    
    if for_stmt.loop_type == ForLoopType.MIXED:
        return generate_for_chain(for_stmt)
    
    # Default: bounded range
    return generate_for_range(for_stmt)
```

## Edge Cases

### Step of Zero

Step=0 never advances, creating an infinite loop. Python `range()` raises `ValueError` for step=0.

### Decreasing Range with Positive Step

Start > End with positive step executes zero times:

```mumps
F I=10:1:5 W I
```

```python
_for_step = m_num(1)
_for_end = m_num(5) + 1  # = 6
for I in range(m_num(10), 6, 1):  # Empty range
    _rt.write(str(I))  # Never executes
```

### Empty Body

Valid MUMPS but generates `pass`:

```mumps
F I=1:1:10
```

```python
_for_step = m_num(1)
_for_end = m_num(10) + 1
for I in range(m_num(1), _for_end, _for_step):
    pass
```

## Loop Variable Visibility

After a FOR loop completes, the loop variable retains its final value. This is MUMPS semantics per MDC 7.1.10:

```mumps
F I=1:1:3 W I
W " Final: ",I
```

Output: `123 Final: 4`

The loop variable `I` is 4 after the loop (one past the end value).
