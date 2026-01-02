# Advanced Patterns: Complex FOR/GOTO

Examples of complex control flow patterns and their ASG analysis results.

## Nested FOR with QUIT

### Which Loop Does QUIT Exit?

```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=5 Q      ; Exits inner FOR (J loop)
. . W I,J
. W "After J loop"
```

QUIT exits the **innermost** FOR loop only.

**ASG Analysis:**
```
MForStatement (I loop)
    has_internal_quit=False  ; No QUIT directly in its body
    body=MScope(
        MForStatement (J loop)
            has_internal_quit=True  ; QUIT is in its body
            body=MScope(
                MQuitStatement(exits_for=True)
            )
    )
```

**Python Equivalent:**
```python
for i in range(1, 11):
    for j in range(1, 11):
        if x == 5:
            break  # Exits j loop only
        print(i, j)
    print("After J loop")
```

---

## GOTO Exiting Multiple Loops

```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=Y G ALLDONE
. . W I,J
W "After loops"
Q
ALLDONE W "Jumped out!"
Q
```

The GOTO exits **both** FOR loops.

**ASG Analysis (after classify_gotos):**
```
MGotoStatement(
    targets=[MCall(name="ALLDONE")],
    goto_type=GotoType.MULTI_LOOP_EXIT,
    exits_loops=[<I loop MForStatement>, <J loop MForStatement>]
)

MForStatement (I loop)
    has_internal_goto=True
    exit_points=[<the MGotoStatement>]

MForStatement (J loop)
    has_internal_goto=True
    exit_points=[<the MGotoStatement>]
```

**Python Equivalent (exception pattern):**
```python
class LoopExit(Exception):
    pass

try:
    for i in range(1, 11):
        for j in range(1, 11):
            if x == y:
                raise LoopExit()
            print(i, j)
    print("After loops")
except LoopExit:
    print("Jumped out!")
```

---

## Loop Variable Modification

```mumps
F I=1:1:10 D
. S I=I+5        ; Modifies loop variable!
. W I
```

**ASG Analysis:**
```
MForStatement(
    loop_var=MVariable(name="I"),
    loop_var_modified_in_body=True,
    body=MScope(
        MSetStatement(target=MVariable(name="I"))
    )
)
```

**Python Challenge:**

Python's `for` doesn't allow modifying the loop variable:

```python
# WRONG - Python for ignores reassignment
for i in range(1, 11):
    i = i + 5  # Next iteration resets i
    print(i)

# CORRECT - Use while loop
i = 1
while i <= 10:
    i = i + 5
    print(i)
    i = i + 1  # Manual step
```

---

## Forward vs Backward GOTO

```mumps
START  S X=0
LOOP   S X=X+1
       I X<10 G LOOP      ; Backward jump (to earlier label)
       G DONE             ; Forward jump (to later label)
END    W "Not reached"
DONE   W "Finished"
```

**ASG Analysis (after classify_gotos):**
```
MGotoStatement (G LOOP)
    goto_type=GotoType.BACKWARD_JUMP

MGotoStatement (G DONE)
    goto_type=GotoType.FORWARD_JUMP
```

**Python Strategy:**

Backward jump → loop structure:
```python
x = 0
while True:  # Replaces G LOOP pattern
    x = x + 1
    if x >= 10:
        break
done()
```

---

## Conditional GOTO Exiting Loop

```mumps
F I=1:1:100 D
. I I#10=0 W I,!
. I I>50 G HALFWAY
HALFWAY W "Past 50"
```

**ASG Analysis:**
```
MGotoStatement(
    targets=[MCall(name="HALFWAY")],
    postcondition=MBinaryOp(operator=">", ...),
    goto_type=GotoType.LOOP_EXIT,
    exits_loops=[<the FOR statement>]
)
```

**Python Equivalent:**
```python
for i in range(1, 101):
    if i % 10 == 0:
        print(i)
    if i > 50:
        break
print("Past 50")
```

---

## Complex Loop Patterns from MUGJ

### V1FORC.m - FOR with GOTO

Key patterns tested:
- GOTO inside FOR body
- GOTO to label inside same FOR
- GOTO to label outside FOR

### V1FORC2.m - Nested FOR with GOTO

Key patterns:
- GOTO exiting inner FOR only
- GOTO exiting both FORs
- Forward vs backward targets

### V1GO.m - Various GOTO Patterns

Key patterns:
- Simple forward/backward
- Conditional GOTO
- External GOTO

---

## Analysis Checklist for Complex Control Flow

For each FOR loop:
- [ ] `loop_type` - What kind of iteration?
- [ ] `is_infinite` - Can it exit naturally?
- [ ] `has_internal_quit` - QUIT in body?
- [ ] `has_internal_goto` - GOTO in body?
- [ ] `loop_var_modified_in_body` - Can use Python `for`?
- [ ] `exit_points` - Which GOTOs exit this loop?

For each GOTO:
- [ ] `goto_type` - Forward, backward, loop exit?
- [ ] `exits_loops` - Which loops does it exit?
- [ ] `postcondition` - Is it conditional?
- [ ] `targets[0].is_resolved` - Known target?

---

## Code Generation Decision Tree

```
Is GOTO present?
├─ No → Use simple Python structures
└─ Yes → Check goto_type
    ├─ FORWARD_JUMP
    │   └─ Can restructure as if/elif? → Python conditionals
    ├─ BACKWARD_JUMP
    │   └─ Creates loop → while True with break
    ├─ LOOP_EXIT
    │   └─ Single loop? → break
    ├─ MULTI_LOOP_EXIT
    │   └─ Use exception or state machine
    └─ EXTERNAL
        └─ Function call to other module
```

---

## State Machine Pattern

For very complex GOTO patterns, generate a state machine:

```mumps
START  S X=1
       G MIDDLE
TOP    W "top"
       G END
MIDDLE W "middle"
       I X=1 G TOP
       G END
END    W "end"
```

**Python (state machine):**
```python
state = "START"
while True:
    if state == "START":
        x = 1
        state = "MIDDLE"
    elif state == "TOP":
        print("top")
        state = "END"
    elif state == "MIDDLE":
        print("middle")
        if x == 1:
            state = "TOP"
        else:
            state = "END"
    elif state == "END":
        print("end")
        break
```

This pattern handles any GOTO structure but is less readable than structured code.
