# FOR Loop Translation Strategies

How to generate Python code for MUMPS FOR loops.

## Overview

MUMPS FOR loops map to different Python patterns based on:

1. **Loop type** (bounded, open-ended, argumentless)
2. **Internal control flow** (QUIT, GOTO)
3. **Loop variable modification**

## Analysis Fields

| Field | Purpose |
|-------|---------|
| `loop_type` | Classification of loop structure |
| `is_infinite` | Cannot exit naturally |
| `has_internal_quit` | QUIT in body → `break` |
| `has_internal_goto` | GOTO exits loop |
| `loop_var_modified_in_body` | Cannot use `for in range()` |
| `exit_points` | GOTOs that exit this loop |

## Bounded FOR

### Simple Case

```mumps
F I=1:1:10 W I
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
for i in range(1, 11):  # Adjust for MUMPS inclusive end
    print(i)
```

### With Step

```mumps
F I=10:-2:0 W I
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
for i in range(10, -1, -2):  # Negative step
    print(i)
```

### With QUIT (break)

```mumps
F I=1:1:100 Q:I>50 W I
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
for i in range(1, 101):
    if i > 50:
        break
    print(i)
```

## Open-Ended FOR

No end value - must have QUIT or GOTO to exit.

```mumps
F I=1:1 Q:I>10 W I
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
i = 1
while True:
    if i > 10:
        break
    print(i)
    i += 1
```

Alternative using `itertools`:
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
from itertools import count
for i in count(1):
    if i > 10:
        break
    print(i)
```

## Argumentless FOR (Infinite)

```mumps
F  R X Q:X=""
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
while True:
    x = input()
    if x == "":
        break
```

## Value List FOR

```mumps
F I="A","B","C" W I
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
for i in ["A", "B", "C"]:
    print(i)
```

## Mixed Parameters

```mumps
F I=1:1:3,"X",10:2:20 D WORK
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
from itertools import chain

def value_range(start, step, end):
    i = start
    while (step > 0 and i <= end) or (step < 0 and i >= end):
        yield i
        i += step

for i in chain(value_range(1, 1, 3), ["X"], value_range(10, 2, 20)):
    work()
```

## Loop Variable Modification

When the loop variable is SET inside the body, Python's `for` cannot be used:

```mumps
F I=1:1:10 D
. S I=I+5
. W I
```

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
# WRONG - Python resets i each iteration
for i in range(1, 11):
    i = i + 5  # Ignored by for loop
    print(i)

# CORRECT - Use while
i = 1
while i <= 10:
    i = i + 5
    print(i)
    i = i + 1  # Manual step
```

## GOTO Exiting Loop

When a GOTO exits the loop (not the whole routine):

```mumps
F I=1:1:100 D
. I ERR G ERROR
. D WORK
ERROR W "Error!"
```

**Single Loop Exit:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
for i in range(1, 101):
    if err:
        break
    work()
print("Error!")
```

**If code continues after ERROR label:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
exited_via_error = False
for i in range(1, 101):
    if err:
        exited_via_error = True
        break
    work()
if exited_via_error:
    print("Error!")
```

## Multi-Loop Exit

```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=Y G ALLDONE
ALLDONE W "Done"
```

**Exception Pattern:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
class LoopExit(Exception):
    pass

try:
    for i in range(1, 11):
        for j in range(1, 11):
            if x == y:
                raise LoopExit()
except LoopExit:
    pass
print("Done")
```

**Flag Pattern:**
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
exit_all = False
for i in range(1, 11):
    for j in range(1, 11):
        if x == y:
            exit_all = True
            break
    if exit_all:
        break
print("Done")
```

## Decision Matrix

```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
def generate_for_loop(for_stmt):
    if for_stmt.loop_type == ForLoopType.ARGUMENTLESS:
        return generate_while_true(for_stmt)
    
    if for_stmt.loop_var_modified_in_body:
        return generate_while_loop(for_stmt)
    
    if for_stmt.loop_type == ForLoopType.OPEN_ENDED:
        return generate_while_true(for_stmt)
    
    if for_stmt.loop_type == ForLoopType.STRING_LIST:
        return generate_for_in_list(for_stmt)
    
    # Bounded range
    if for_stmt.has_internal_goto:
        return generate_for_with_exit_tracking(for_stmt)
    
    return generate_simple_for_range(for_stmt)
```

## Edge Cases

### Step of Zero (Infinite)

```mumps
F I=1:0:10 Q:X W I
```

Step=0 never advances, creating infinite loop:
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
i = 1
while True:  # Never naturally exits
    if x:
        break
    print(i)
    # i += 0 (no change)
```

### Decreasing Range with Positive Step

```mumps
F I=10:1:5 W I
```

Start > End with positive step executes zero times:
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
# range(10, 6, 1) is empty
for i in range(10, 6, 1):  # Skipped
    print(i)
```

### Empty Body

```mumps
F I=1:1:10
```

Valid MUMPS but does nothing useful:
```python
# Illustrative code - do not use this as a design reference
# TODO: Update with final design/syntax when ready
for i in range(1, 11):
    pass
```
