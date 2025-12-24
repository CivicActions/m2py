# Subroutines: DO, QUIT, Parameter Passing

Examples of MUMPS subroutine calls and their ASG representation.

## DO Command

### Simple DO

```mumps
D LABEL
```

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(
            name="LABEL",
            routine=None,
            call_type=CallType.LABEL_CALL,  # After resolution
            is_resolved=True,
            target=<MLabel object>
        )
    ]
)
```

**Python Equivalent:**
```python
label()
```

### DO with Arguments

```mumps
D CALC(A,B)
```

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(
            name="CALC",
            arguments=[
                MActualParameter(
                    expression=MVariable(name="A"),
                    passing_mode=PassingMode.BY_VALUE
                ),
                MActualParameter(
                    expression=MVariable(name="B"),
                    passing_mode=PassingMode.BY_VALUE
                )
            ]
        )
    ]
)
```

**Python Equivalent:**
```python
calc(a, b)
```

### DO with By-Reference

```mumps
D SWAP(.X,.Y)
```

The dot prefix indicates call-by-reference.

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(
            name="SWAP",
            arguments=[
                MActualParameter(
                    expression=MVariable(name="X"),
                    passing_mode=PassingMode.BY_REFERENCE,
                    variable_name="X"
                ),
                MActualParameter(
                    expression=MVariable(name="Y"),
                    passing_mode=PassingMode.BY_REFERENCE,
                    variable_name="Y"
                )
            ]
        )
    ]
)
```

**Python Equivalent:**
```python
# Requires special handling - return modified values
x, y = swap(x, y)
```

### External DO

```mumps
D LABEL^ROUTINE
```

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(
            name="LABEL",
            routine="ROUTINE",
            call_type=CallType.ROUTINE_CALL,
            is_resolved=False
        )
    ]
)
```

### Multiple Targets

```mumps
D INIT,PROCESS,CLEANUP
```

**ASG Structure:**
```
MDoStatement(
    targets=[
        MCall(name="INIT"),
        MCall(name="PROCESS"),
        MCall(name="CLEANUP")
    ]
)
```

### Argumentless DO (Block)

```mumps
D
. S X=1
. W X
```

**ASG Structure:**
```
MDoBlockStatement(
    body=MScope(
        statements=[
            MSetStatement(...),
            MWriteStatement(...)
        ]
    )
)
```

The dot-prefixed lines form a block scope.

---

## QUIT Command

### Simple QUIT

```mumps
Q
```

**ASG Structure:**
```
MQuitStatement(
    return_value=None
)
```

### QUIT with Value

```mumps
Q X+1
```

Returns a value from extrinsic function.

**ASG Structure:**
```
MQuitStatement(
    return_value=MBinaryOp(
        operator="+",
        left=MVariable(name="X"),
        right=MLiteral(value=1)
    )
)
```

**Python Equivalent:**
```python
return x + 1
```

### Conditional QUIT

```mumps
Q:X>10
```

**ASG Structure:**
```
MQuitStatement(
    postcondition=MBinaryOp(operator=">", left=MVariable(name="X"), right=MLiteral(value=10)),
    return_value=None
)
```

**Python Equivalent:**
```python
if x > 10:
    return  # or break if in FOR loop
```

### QUIT in FOR Loop

```mumps
F I=1:1:100 Q:I>10
```

After analysis:
```
MQuitStatement(
    postcondition=...,
    exits_for=True  # Set during analysis
)
```

Becomes `break` instead of `return`.

---

## NEW Command

### Selective NEW

```mumps
N X,Y,Z
```

Creates new local scope for specified variables.

**ASG Structure:**
```
MNewStatement(
    variables=[
        MVariable(name="X"),
        MVariable(name="Y"),
        MVariable(name="Z")
    ],
    exclusive=False
)
```

### Exclusive NEW

```mumps
N (X,Y)
```

NEW all variables EXCEPT X and Y.

**ASG Structure:**
```
MNewStatement(
    variables=[],
    exclusive=True,
    except_list=[
        MVariable(name="X"),
        MVariable(name="Y")
    ]
)
```

### Argumentless NEW

```mumps
N
```

NEW all local variables.

**ASG Structure:**
```
MNewStatement(
    variables=[],
    exclusive=False
)
```

---

## Extrinsic Functions

### Definition

```mumps
DOUBLE(X)
    Q X*2
```

**ASG Structure (MLabel):**
```
MLabel(
    name="DOUBLE",
    formal_list=["X"],
    body=MScope(
        statements=[
            MQuitStatement(
                return_value=MBinaryOp(operator="*", left=MVariable(name="X"), right=MLiteral(value=2))
            )
        ]
    )
)
```

### Call Site

```mumps
S Y=$$DOUBLE(5)
```

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(
            target=MVariable(name="Y"),
            value=MExtrinsicFunction(
                target=MCall(name="DOUBLE", arguments=[
                    MActualParameter(expression=MLiteral(value=5))
                ]),
                arguments=[MLiteral(value=5)]
            )
        )
    ]
)
```

**Python Equivalent:**
```python
def double(x):
    return x * 2

y = double(5)
```

### External Extrinsic

```mumps
S Y=$$CALC^MATH(A,B)
```

**ASG Structure:**
```
MExtrinsicFunction(
    target=MCall(
        name="CALC",
        routine="MATH",
        call_type=CallType.ROUTINE_CALL
    ),
    arguments=[MVariable(name="A"), MVariable(name="B")]
)
```

---

## Code Generation Notes

### DO/QUIT

- Simple DO → function call
- QUIT without value → `return` or `break`
- QUIT with value → `return value`
- By-reference → return modified values

### NEW

- Creates local scope boundary
- Affects variable analysis
- May translate to nested functions or context managers

### Formal Parameters

Per MUMPS spec, formal parameters are implicitly NEWed:

```mumps
PROC(A,B)
    S A=A+1  ; Only affects local A
    Q
```

The caller's A is unchanged.

### FunctionSignature

After variable analysis, `MLabel.signature` contains:

```python
FunctionSignature(
    label_name="CALC",
    formal_params=["A", "B"],
    required_inputs={"X"},      # Non-formal inputs
    output_variables={"RESULT"}, # Non-NEWed writes
    has_value_quit=True,
    scope_strategy=ScopeStrategy.VALUE_RETURNING
)
```
