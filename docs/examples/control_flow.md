# Control Flow: IF, ELSE, FOR, GOTO

Examples of MUMPS control flow constructs and their ASG representation.

## IF Command

### Simple IF

```mumps
I X=1 W "yes"
```

**ASG Structure:**
```
MIfStatement(
    condition=MBinaryOp(operator="=", left=MVariable(name="X"), right=MLiteral(value=1)),
    then_scope=MScope(
        statements=[
            MWriteStatement(arguments=[MLiteral(value="yes")])
        ]
    )
)
```

**Python Equivalent:**
```python
if x == 1:
    print("yes")
```

### IF with Multiple Conditions (AND)

```mumps
I X=1,Y=2 W "both"
```

Comma-separated conditions are ANDed together.

**ASG Structure:**
```
MIfStatement(
    conditions=[
        MBinaryOp(operator="=", left=MVariable(name="X"), right=MLiteral(value=1)),
        MBinaryOp(operator="=", left=MVariable(name="Y"), right=MLiteral(value=2))
    ],
    then_scope=MScope(...)
)
```

**Python Equivalent:**
```python
if x == 1 and y == 2:
    print("both")
```

### Argumentless IF

```mumps
I  W "test was true"
```

Tests current value of `$TEST`.

**ASG Structure:**
```
MIfStatement(
    condition=None,  # Uses $TEST
    then_scope=MScope(...)
)
```

---

## ELSE Command

### Basic ELSE

```mumps
I X=1 W "yes"
E  W "no"
```

**ASG Structure:**
```
MIfStatement(
    condition=MBinaryOp(...),
    then_scope=MScope(...)
)
MElseStatement(
    body=MScope(
        statements=[MWriteStatement(arguments=[MLiteral(value="no")])]
    )
)
```

**Important:** ELSE depends on `$TEST`, not direct linkage to IF.

### Multiple ELSE

```mumps
I X=1 W "one"
E  I X=2 W "two"
E  W "other"
```

**Python Equivalent:**
```python
if x == 1:
    print("one")
elif x == 2:
    print("two")
else:
    print("other")
```

---

## FOR Command

### Bounded Range

```mumps
F I=1:1:10 W I
```

**ASG Structure:**
```
MForStatement(
    loop_var=MVariable(name="I"),
    parameters=[
        MForParameter(
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=MLiteral(value=10),
            param_type=ForParamType.RANGE
        )
    ],
    loop_type=ForLoopType.BOUNDED,
    body=MScope(...)
)
```

**Python Equivalent:**
```python
for i in range(1, 11):
    print(i)
```

### Open-Ended FOR

```mumps
F I=1:1 Q:I>10 W I
```

No end value - must exit with QUIT.

**ASG Structure:**
```
MForStatement(
    loop_var=MVariable(name="I"),
    parameters=[
        MForParameter(
            start=MLiteral(value=1),
            step=MLiteral(value=1),
            end=None,
            param_type=ForParamType.OPEN_RANGE
        )
    ],
    loop_type=ForLoopType.OPEN_ENDED,
    has_internal_quit=True,
    body=MScope(
        statements=[
            MQuitStatement(postcondition=MBinaryOp(...)),
            MWriteStatement(...)
        ]
    )
)
```

**Python Equivalent:**
```python
i = 1
while True:
    if i > 10:
        break
    print(i)
    i += 1
```

### Argumentless FOR (Infinite)

```mumps
F  R X Q:X=""
```

**ASG Structure:**
```
MForStatement(
    loop_var=None,
    parameters=[],
    loop_type=ForLoopType.ARGUMENTLESS,
    is_infinite=True,
    body=MScope(...)
)
```

**Python Equivalent:**
```python
while True:
    x = input()
    if x == "":
        break
```

### Value List FOR

```mumps
F I="A","B","C" W I
```

**ASG Structure:**
```
MForStatement(
    loop_var=MVariable(name="I"),
    parameters=[
        MForParameter(start=MLiteral(value="A"), param_type=ForParamType.VALUE),
        MForParameter(start=MLiteral(value="B"), param_type=ForParamType.VALUE),
        MForParameter(start=MLiteral(value="C"), param_type=ForParamType.VALUE)
    ],
    loop_type=ForLoopType.STRING_LIST,
    body=MScope(...)
)
```

**Python Equivalent:**
```python
for i in ["A", "B", "C"]:
    print(i)
```

### Nested FOR with Dot Syntax

```mumps
F I=1:1:3 D
. F J=1:1:3 D
. . W I*J," "
```

**ASG Structure:**
```
MForStatement(
    loop_var=MVariable(name="I"),
    body=MScope(
        statements=[
            MDoStatement(
                targets=[],  # Argumentless DO
                body=MScope(
                    statements=[
                        MForStatement(
                            loop_var=MVariable(name="J"),
                            body=MScope(
                                statements=[
                                    MDoStatement(targets=[], body=MScope(...))
                                ]
                            )
                        )
                    ]
                )
            )
        ]
    )
)
```

---

## GOTO Command

### Simple GOTO

```mumps
G LABEL
```

**ASG Structure:**
```
MGotoStatement(
    targets=[
        MCall(name="LABEL", routine=None)
    ],
    goto_type=GotoType.FORWARD_JUMP  # or BACKWARD_JUMP after classification
)
```

### Conditional GOTO

```mumps
G:X=1 DONE
```

**ASG Structure:**
```
MGotoStatement(
    targets=[MCall(name="DONE")],
    postcondition=MBinaryOp(operator="=", left=MVariable(name="X"), right=MLiteral(value=1))
)
```

**Python Equivalent:**
```python
if x == 1:
    goto_done()  # Needs structured conversion
```

### GOTO Exiting Loop

```mumps
F I=1:1:10 D
. I X=5 G DONE
DONE W "finished"
```

After GOTO analysis:
```
MGotoStatement(
    targets=[MCall(name="DONE")],
    goto_type=GotoType.LOOP_EXIT,
    exits_loops=[<the MForStatement>]
)
```

### External GOTO

```mumps
G LABEL^ROUTINE
```

**ASG Structure:**
```
MGotoStatement(
    targets=[MCall(name="LABEL", routine="ROUTINE")],
    goto_type=GotoType.EXTERNAL
)
```

---

## Code Generation Notes

### IF/ELSE

- `$TEST` side effect must be tracked
- Argumentless IF tests `$TEST`
- Generate Python if/elif/else chains

### FOR

| loop_type | Python Pattern |
|-----------|---------------|
| BOUNDED | `for i in range(...)` |
| OPEN_ENDED | `while True:` with break |
| ARGUMENTLESS | `while True:` |
| STRING_LIST | `for i in [...]` |

Check `has_internal_quit`, `loop_var_modified_in_body` for strategy.

### GOTO

| goto_type | Strategy |
|-----------|----------|
| FORWARD_JUMP | Function call or continue |
| BACKWARD_JUMP | Loop construct |
| LOOP_EXIT | `break` |
| MULTI_LOOP_EXIT | Exception or state machine |
| EXTERNAL | Cross-module call |
