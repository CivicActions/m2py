# Basic Commands: SET, WRITE, READ

Examples of fundamental MUMPS commands and their ASG representation.

## SET Command

### Single Assignment

```mumps
S X=1
```

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(
            target=MVariable(name="X"),
            value=MLiteral(value=1, literal_type=LiteralType.INTEGER)
        )
    ]
)
```

### Multiple Assignments

```mumps
S A=1,B=2,C=A+B
```

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(target=MVariable(name="A"), value=MLiteral(value=1)),
        MAssignment(target=MVariable(name="B"), value=MLiteral(value=2)),
        MAssignment(target=MVariable(name="C"), value=MBinaryOp(
            operator="+",
            left=MVariable(name="A"),
            right=MVariable(name="B")
        ))
    ]
)
```

**Python Equivalent:**
```python
a = 1
b = 2
c = a + b
```

### Multi-Target Assignment

```mumps
S (A,B,C)=1
```

Multiple targets receive the same value.

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(target=MVariable(name="A"), value=MLiteral(value=1)),
        MAssignment(target=MVariable(name="B"), value=MLiteral(value=1)),
        MAssignment(target=MVariable(name="C"), value=MLiteral(value=1))
    ]
)
```

### Subscripted Variables

```mumps
S A(1,2)="value"
```

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(
            target=MVariable(
                name="A",
                subscripts=[
                    MLiteral(value=1),
                    MLiteral(value=2)
                ]
            ),
            value=MLiteral(value="value", literal_type=LiteralType.STRING)
        )
    ]
)
```

### Global Variables

```mumps
S ^GLOBAL(1)="data"
```

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(
            target=MGlobal(
                name="GLOBAL",
                subscripts=[MLiteral(value=1)]
            ),
            value=MLiteral(value="data")
        )
    ]
)
```

### SET with Postcondition

```mumps
S:X>0 Y=1
```

**ASG Structure:**
```
MSetStatement(
    assignments=[
        MAssignment(
            target=MVariable(name="Y"),
            value=MLiteral(value=1),
            postcondition=MBinaryOp(operator=">", left=MVariable(name="X"), right=MLiteral(value=0))
        )
    ]
)
```

**Python Equivalent:**
```python
if x > 0:
    y = 1
```

---

## WRITE Command

### Basic WRITE

```mumps
W "Hello"
```

**ASG Structure:**
```
MWriteStatement(
    arguments=[
        MLiteral(value="Hello", literal_type=LiteralType.STRING)
    ]
)
```

### Multiple Arguments

```mumps
W "X=",X,!
```

**ASG Structure:**
```
MWriteStatement(
    arguments=[
        MLiteral(value="X="),
        MVariable(name="X"),
        MFormatControl(control_type=FormatControlType.NEWLINE)
    ]
)
```

### Format Controls

| MUMPS | FormatControlType | Python |
|-------|-------------------|--------|
| `!` | NEWLINE | `print()` or `\n` |
| `#` | FORMFEED | `\f` |
| `?n` | TAB (to column n) | Tab/space to column |
| `*n` | CHARCODE | `chr(n)` |

```mumps
W "Name:",?10,NAME,!
```

**ASG Structure:**
```
MWriteStatement(
    arguments=[
        MLiteral(value="Name:"),
        MFormatControl(control_type=FormatControlType.TAB, expression=MLiteral(value=10)),
        MVariable(name="NAME"),
        MFormatControl(control_type=FormatControlType.NEWLINE)
    ]
)
```

### Character Code

```mumps
W *65
```

Writes ASCII 65 ('A').

**ASG Structure:**
```
MWriteStatement(
    arguments=[
        MFormatControl(control_type=FormatControlType.CHARCODE, expression=MLiteral(value=65))
    ]
)
```

**Python Equivalent:**
```python
print(chr(65), end='')  # Prints 'A'
```

---

## READ Command

### Simple READ

```mumps
R X
```

**ASG Structure:**
```
MReadStatement(
    arguments=[
        MReadTarget(target=MVariable(name="X"))
    ]
)
```

### READ with Prompt

```mumps
R "Enter name: ",NAME
```

**ASG Structure:**
```
MReadStatement(
    arguments=[
        MLiteral(value="Enter name: "),
        MReadTarget(target=MVariable(name="NAME"))
    ]
)
```

### READ with Timeout

```mumps
R X:10
```

Wait up to 10 seconds for input.

**ASG Structure:**
```
MReadStatement(
    arguments=[
        MReadTarget(
            target=MVariable(name="X"),
            timeout=MLiteral(value=10)
        )
    ]
)
```

**Key Field:** `timeout` - if present, sets `$TEST` based on whether input was received.

### Fixed-Length READ

```mumps
R X#5
```

Read exactly 5 characters.

**ASG Structure:**
```
MReadStatement(
    arguments=[
        MReadTarget(
            target=MVariable(name="X"),
            fixed_length=MLiteral(value=5)
        )
    ]
)
```

### Single Character READ

```mumps
R *X
```

Read single character as ASCII code.

**ASG Structure:**
```
MReadStatement(
    arguments=[
        MReadTarget(
            target=MVariable(name="X"),
            is_char_read=True
        )
    ]
)
```

---

## Code Generation Notes

### SET

- Multiple assignments → multiple Python statements
- Postconditions → wrap in `if`
- Global variables → special storage mechanism

### WRITE

- Translate to `print()` calls
- Handle format controls appropriately
- `!` → newline, `?n` → tab to column

### READ

- Use `input()` or equivalent
- Timeout requires asyncio or threading
- `$TEST` must be set if timeout present
