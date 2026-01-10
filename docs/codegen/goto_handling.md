# GOTO Handling Strategies

How to translate MUMPS GOTO into structured Python code.

## Overview

GOTO is MUMPS's primary control flow mechanism. The challenge is mapping it to Python's structured constructs.

## GOTO Classifications

After `classify_gotos()`, each MGotoStatement has a `goto_type`:

| GotoType | Meaning | Strategy |
|----------|---------|----------|
| `FORWARD_JUMP` | To later code | If/elif chain |
| `BACKWARD_JUMP` | To earlier code | Loop |
| `LOOP_EXIT` | Out of one FOR | `break` |
| `MULTI_LOOP_EXIT` | Out of nested FORs | Exception |
| `CROSS_LABEL` | To different label | Function call + return |
| `EXTERNAL` | To other routine | Module import + call |
| `UNRESOLVED` | Dynamic target | Runtime dispatch |

## Forward Jump

### Intra-Label Forward (is_cross_label=False)

When a GOTO targets a line within the same label, the code generator restructures
it to an inverted if/else block. This is handled by `generate_scope_statements()`
which detects restructurable GOTOs and transforms them.

**MUMPS Offset Semantics**: `LABEL+n` targets line n from LABEL (0-indexed).
For example, `G TEST+4` from TEST at line 1 targets line 5.

```mumps
TEST   I 1 G TEST+4    ; Line 1 - if true, skip to line 5
       W "A",!         ; Line 2 - skipped when GOTO fires
       W "B",!         ; Line 3 - skipped when GOTO fires
       W "C",!         ; Line 4 - skipped when GOTO fires
       W "D",!         ; Line 5 - target (TEST+4)
       Q
```

**Generated Python (Spec 005):**
```python
def TEST():
    global _test
    _test = m_truth(1)
    if not _test:
        _rt.write(str("A"))
        _rt.write(str("\n"))
        _rt.write(str("B"))
        _rt.write(str("\n"))
        _rt.write(str("C"))
        _rt.write(str("\n"))
    _rt.write(str("D"))
    _rt.write(str("\n"))
```

**Implementation Details**:
- `_find_forward_goto_in_if()` detects restructurable GOTOs inside IF statements
- `_restructure_forward_goto()` generates the inverted if/else structure
- `target_stmt_index` (computed in `classify_gotos()`) identifies which statements to wrap

### Cross-Label Forward (is_cross_label=True)

Forward jumps to a different label use function call pattern (Spec 006):

```mumps
START  I X=1 G DONE
       W "X is not 1"
DONE   W "Finished"
```

**Conceptual Python (Spec 006):**
```python
if x == 1:
    return DONE()  # Function call + return
print("X is not 1")

def DONE():
    print("Finished")
```

### Multiple Forwards (If/Elif Chain)

```mumps
       I X=1 G ONE
       I X=2 G TWO
       G OTHER
ONE    W "One" Q
TWO    W "Two" Q
OTHER  W "Other"
```

```python
# Conceptual Python equivalent

if x == 1:
    print("One")
elif x == 2:
    print("Two")
else:
    print("Other")
```

## Backward Jump

Creates a loop structure:

```mumps
START  S X=0
LOOP   S X=X+1
       W X
       I X<10 G LOOP
       W "Done"
```

**While Loop:**
```python
# Conceptual Python equivalent

x = 0
while True:
    x = x + 1
    print(x)
    if x >= 10:
        break
print("Done")
```

## Loop Exit

### Single Loop

```mumps
F I=1:1:100 D
. I ERR G ERROR
. D WORK
ERROR W "Exited"
```

**Break Pattern:**
```python
# Conceptual Python equivalent

for i in range(1, 101):
    if err:
        break
    work()
print("Exited")
```

### With Distinct Exit Points

```mumps
F I=1:1:100 D
. I ERR G ERROR
. I DONE G SUCCESS
. D WORK
ERROR W "Error!"
Q
SUCCESS W "Success!"
```

**Flag Pattern:**
```python
# Conceptual Python equivalent

exit_type = None
for i in range(1, 101):
    if err:
        exit_type = "error"
        break
    if done:
        exit_type = "success"
        break
    work()

if exit_type == "error":
    print("Error!")
elif exit_type == "success":
    print("Success!")
```

## Loop Continue (is_loop_continue=True)

When `is_loop_continue=True`, the GOTO simulates Python's `continue` statement:

```mumps
LOOP   F I=1:1:10 D
       . I I#2=0 G LOOP    ; Skip even numbers
       . W I,!
       Q
```

**Continue Pattern:**
```python
# Conceptual Python equivalent

for i in range(1, 11):
    if i % 2 == 0:
        continue
    print(i)
```

The analyzer sets `is_loop_continue=True` when:
1. GOTO is inside a FOR loop
2. GOTO target is the same label containing the FOR

This is a common MUMPS idiom for skipping to the next iteration without exiting the loop.

## Multi-Loop Exit

```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=Y G ALLDONE
. W I
W "After outer"
Q
ALLDONE W "Jumped out!"
```

### Exception Pattern

```python
# Conceptual Python equivalent

class LoopExit(Exception):
    pass

try:
    for i in range(1, 11):
        for j in range(1, 11):
            if x == y:
                raise LoopExit()
        print(i)
    print("After outer")
except LoopExit:
    print("Jumped out!")
```

### Nested Flag Pattern

```python
# Conceptual Python equivalent

exit_outer = False
for i in range(1, 11):
    for j in range(1, 11):
        if x == y:
            exit_outer = True
            break
    if exit_outer:
        break
    print(i)

if exit_outer:
    print("Jumped out!")
else:
    print("After outer")
```

## External GOTO

```mumps
G LABEL^OTHERROUTINE
```

**Module Call:**
```python
# Conceptual Python equivalent

import otherroutine
otherroutine.label()
# No return - control transfers permanently
```

Or with return value if needed:
```python
# Conceptual Python equivalent

return otherroutine.label()  # If in a function context
```

## Conditional GOTO

```mumps
G:CONDITION TARGET
```

**Conditional Break/Call:**
```python
# Conceptual Python equivalent

if condition:
    break  # or return, or function_call()
```

## Unstructured GOTO

When GOTOs create irreducible control flow (not mappable to structured constructs):

```mumps
LABEL1 I X=1 G LABEL3
LABEL2 W "Two"
       G LABEL4
LABEL3 W "Three"
       I Y=2 G LABEL2
LABEL4 W "Four"
```

### State Machine Pattern

```python
# Conceptual Python equivalent

state = "LABEL1"
while True:
    if state == "LABEL1":
        if x == 1:
            state = "LABEL3"
        else:
            state = "LABEL2"
    elif state == "LABEL2":
        print("Two")
        state = "LABEL4"
    elif state == "LABEL3":
        print("Three")
        if y == 2:
            state = "LABEL2"
        else:
            state = "LABEL4"
    elif state == "LABEL4":
        print("Four")
        break
```

## Detection: has_unstructured_goto

The routine-level flag indicates complex GOTO patterns that cannot be easily translated to structured Python:

```python
# Conceptual Python equivalent

if routine.has_unstructured_goto:
    return generate_state_machine(routine)
else:
    return generate_structured(routine)
```

**Patterns that set `has_unstructured_goto=True`:**
- `BACKWARD_JUMP`: Cross-label backward jump creates implicit loops
- `UNRESOLVED`: Target unknown at compile time, needs runtime dispatch
- Cross-label `FORWARD_JUMP` not inside a FOR loop: Can't use simple break

**Patterns that remain structured (`has_unstructured_goto=False`):**
- `LOOP_EXIT` / `MULTI_LOOP_EXIT`: Translates to break or exception
- `FORWARD_JUMP` within same label: Translates to if/else
- `EXTERNAL`: Translates to function call to another module

## Analysis Fields Used

```python
goto_stmt.goto_type            # Classification (GotoType enum)
goto_stmt.postcondition        # Conditional GOTO expression
goto_stmt.exits_loops          # List of FOR loops exited
goto_stmt.is_cross_label       # True if target is different label
goto_stmt.is_loop_continue     # True if simulates continue
goto_stmt.target_stmt_index    # Statement index for intra-label forward (Spec 005)
goto_stmt.targets[0].target    # Resolved MLabel
goto_stmt.targets[0].routine   # External routine name

for_stmt.has_internal_goto     # Has GOTO in body
for_stmt.exit_points           # List of exiting GOTOs
```

## Decision Algorithm

```python
# Conceptual Python equivalent

def translate_goto(goto_stmt, context):
    match goto_stmt.goto_type:
        case GotoType.FORWARD_JUMP:
            if can_restructure_as_if(goto_stmt, context):
                return generate_if_branch(goto_stmt)
            return generate_forward_call(goto_stmt)
        
        case GotoType.BACKWARD_JUMP:
            return generate_loop_structure(goto_stmt, context)
        
        case GotoType.LOOP_EXIT:
            if len(goto_stmt.exits_loops) == 1:
                return generate_break(goto_stmt)
            return generate_multi_exit(goto_stmt)
        
        case GotoType.MULTI_LOOP_EXIT:
            return generate_exception_exit(goto_stmt)
        
        case GotoType.EXTERNAL:
            return generate_module_call(goto_stmt)
        
        case GotoType.UNRESOLVED:
            return generate_runtime_dispatch(goto_stmt)
```
