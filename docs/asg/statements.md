# ASG Statement Types

This document describes all statement types in the ASG. Statements represent executable commands in MUMPS.

## Base Statement

All statements inherit from `MStatement`:

```python
@dataclass
class MStatement(ASGElement):
    scope: Optional[MScope] = None       # Enclosing scope
    postcondition: Optional[MExpr] = None  # Conditional execution (cmd:cond)
    is_unreachable: bool = False         # Set by analysis if unreachable
    _dot_level: int = 0                  # Internal: dot indentation level
```

**Postconditions**: Most statements can have a postcondition that controls execution:
```mumps
S:X>0 Y=X    ; SET only if X>0
G:DONE END   ; GOTO only if DONE is true
```

**Source**: [`src/m2py/asg/statements.py`](../../src/m2py/asg/statements.py)

---

## Assignment Statements

### MSetStatement

Variable assignment. Can assign to multiple targets:

```mumps
S X=1
S A=1,B=2,C=3
S (A,B,C)=0
S:COND X=1
```

| Field | Type | Description |
|-------|------|-------------|
| `assignments` | `List[MAssignment]` | List of target=value pairs |

**MAssignment** structure:

| Field | Type | Description |
|-------|------|-------------|
| `target` | `MVariable\|MGlobal\|MIndirection` | Assignment target |
| `value` | `MExpr` | Value to assign |
| `postcondition` | `Optional[MExpr]` | Per-assignment condition |

**Code Generation**:
- Single assignment: `x = value`
- Multiple: Multiple statements or tuple unpacking
- With postcondition: `if cond: x = value`

---

## I/O Statements

### MWriteStatement

Output to current device:

```mumps
W "Hello"
W "Name: ",NAME,!
W !,?10,"Col 10",*65
```

| Field | Type | Description |
|-------|------|-------------|
| `arguments` | `List[MExpr\|MFormatControl]` | Output items |

**Format controls** (via `MFormatControl`):
- `!` - Newline
- `#` - Form feed  
- `?n` - Tab to column n
- `*n` - Output char with ASCII code n

### MFormatControl

I/O format control element (used in WRITE/READ):

```mumps
W !              ; Newline
W #              ; Form feed
W ?10            ; Tab to column 10
W *65            ; Output char 65 (ASCII 'A')
```

| Field | Type | Description |
|-------|------|-------------|
| `control_type` | `FormatControlType` | NEWLINE, FORMFEED, TAB, or CHARCODE |
| `expression` | `Optional[MExpr]` | Column (TAB) or char code (CHARCODE) |

**FormatControlType enum:**
- `NEWLINE` - `!` - Output newline
- `FORMFEED` - `#` - Output form feed (page break)
- `TAB` - `?n` - Tab to column n
- `CHARCODE` - `*n` - Output character with ASCII code n

**Code Generation:**
```python
# Newline
print()  # or '\n'
# Form feed
print('\f')  # or page handling logic
# Tab to column
print(' ' * (n - current_column))
# Charcode
print(chr(n))
```

### MReadStatement

Input from current device:

```mumps
R X
R "Enter: ",X
R X:10
R *X
R X#5
```

| Field | Type | Description |
|-------|------|-------------|
| `arguments` | `List[MReadTarget\|MLiteral\|MFormatControl]` | Input items |

**MReadTarget** structure:

| Field | Type | Description |
|-------|------|-------------|
| `variable` | `MVariable\|MGlobal` | Variable to read into |
| `is_char_read` | `bool` | True for `*VAR` (single char) |
| `timeout` | `Optional[MExpr]` | Timeout in seconds |
| `fixed_length` | `Optional[MExpr]` | Max characters (`VAR#n`) |

---

## Control Flow - Conditional

### MIfStatement

Conditional execution:

```mumps
I X=1 W "yes"
I X=1,Y=2 W "both"    ; comma = AND
```

| Field | Type | Description |
|-------|------|-------------|
| `condition` | `Optional[MExpr]` | Single condition |
| `conditions` | `List[MExpr]` | Multiple comma-separated conditions |
| `then_scope` | `MScope` | Commands to execute if true |

**Note**: IF sets `$TEST` special variable, which affects subsequent ELSE.

**Code Generation**:
- Single: `if condition:`
- Multiple: `if cond1 and cond2 and cond3:`

### MElseStatement

Executes if previous `$TEST` is false:

```mumps
I X=1 W "yes"
E W "no"
```

| Field | Type | Description |
|-------|------|-------------|
| `body` | `MScope` | Commands to execute |

**Code Generation**: Must track `$TEST` state; typically pairs with preceding IF.

---

## Control Flow - Loops

### MForStatement

Iteration over values, ranges, or indefinite:

```mumps
F I=1:1:10 W I,!           ; BOUNDED
F I=1:1 Q:I>10 W I,!       ; OPEN_ENDED
F  R X Q:X=""              ; ARGUMENTLESS
F I="A","B","C" W I,!      ; STRING_LIST
F I="A",1:1:3 W I,!        ; MIXED
```

| Field | Type | Description |
|-------|------|-------------|
| `loop_var` | `str\|MVariable\|MExpr` | Loop variable |
| `loop_var_indirect` | `bool` | True if loop var is indirection |
| `parameters` | `List[MForParameter]` | Loop parameters |
| `body` | `MScope` | Loop body statements |

**Analysis fields** (populated by `analyze_for_loops`):

| Field | Type | Description |
|-------|------|-------------|
| `loop_type` | `ForLoopType` | Classification |
| `is_infinite` | `bool` | True for step=0 or ARGUMENTLESS |
| `has_internal_quit` | `bool` | QUIT directly in body |
| `has_internal_goto` | `bool` | GOTO exiting loop |
| `goto_exits_loop` | `bool` | GOTO targets outside |
| `exit_points` | `List[MStatement]` | Exit statements |
| `loop_var_modified_in_body` | `bool` | SET of loop var |

**MForParameter** structure:

| Field | Type | Description |
|-------|------|-------------|
| `param_type` | `ForParamType` | VALUE, RANGE, or OPEN_RANGE |
| `value` | `Optional[MExpr]` | For VALUE type |
| `start` | `Optional[MExpr]` | For RANGE types |
| `step` | `Optional[MExpr]` | For RANGE types |
| `end` | `Optional[MExpr]` | For RANGE (bounded) |

**Code Generation by loop_type**:
- `BOUNDED`: `for i in range(start, end+1, step)`
- `OPEN_ENDED`: `while True:` with break
- `ARGUMENTLESS`: `while True:` with break  
- `STRING_LIST`: `for i in [v1, v2, ...]`
- `MIXED`: Combination strategy

---

## Control Flow - Jumps

### MGotoStatement

Transfer control to label:

```mumps
G LABEL
G LABEL^ROUTINE
G:COND LABEL
G LABEL1,LABEL2:COND
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List[MCall]` | Target labels |

**Analysis fields** (populated by `classify_gotos`):

| Field | Type | Description |
|-------|------|-------------|
| `goto_type` | `GotoType` | Classification |
| `exits_loops` | `List[MForStatement]` | FOR loops exited |
| `is_loop_continue` | `bool` | True if continues loop |

**GotoType values**:
- `FORWARD_JUMP` - Jump ahead in same label
- `BACKWARD_JUMP` - Jump back (creates loop)
- `LOOP_EXIT` - Exits single FOR loop
- `MULTI_LOOP_EXIT` - Exits multiple nested FORs
- `CROSS_LABEL` - Jumps to different label
- `EXTERNAL` - Jumps to external routine
- `UNRESOLVED` - Cannot determine statically

**Code Generation by goto_type**:
- `LOOP_EXIT`: `break`
- `MULTI_LOOP_EXIT`: Exception or state machine
- `CROSS_LABEL`: Function call with return handling
- `FORWARD_JUMP`/`BACKWARD_JUMP`: May need restructuring

---

## Subroutine Statements

### MDoStatement

Call subroutine(s) or create block:

```mumps
D LABEL
D LABEL^ROUTINE
D LABEL(A,B,.C)
D LABEL1,LABEL2
D                    ; argumentless - block follows
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List[MCall]` | Called labels |
| `body` | `MScope` | For argumentless DO block |

### MDoBlockStatement

Explicit block for dot-indented lines:

```mumps
D
. S X=1
. W X,!
```

| Field | Type | Description |
|-------|------|-------------|
| `body` | `MScope` | Block statements |

### MQuitStatement

Return from current context:

```mumps
Q
Q VALUE        ; return from extrinsic
Q:COND
```

| Field | Type | Description |
|-------|------|-------------|
| `return_value` | `Optional[MExpr]` | Return value for extrinsics |
| `exits_for` | `Optional[MForStatement]` | FOR loop being exited |
| `exits_do_block` | `Optional[MDoBlockStatement]` | Block being exited |

---

## Variable Statements

### MNewStatement

Create local variable scope:

```mumps
N X           ; NEW single variable
N X,Y,Z       ; NEW multiple
N             ; NEW all (argumentless)
N (X,Y)       ; NEW all EXCEPT X,Y (exclusive)
```

| Field | Type | Description |
|-------|------|-------------|
| `variables` | `List[str]` | Variables to NEW |
| `exclusive` | `bool` | True for exclusive form |
| `except_list` | `List[str]` | Variables to keep (exclusive) |

**Code Generation**: Creates scope boundary. Variables NEW'd are undefined on entry to block, restored on exit.

### MKillStatement

Delete variables:

```mumps
K X           ; Kill single
K X,Y,^GLOBAL ; Kill multiple
K             ; Kill all locals
K (X,Y)       ; Kill all EXCEPT X,Y
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List[MVariable\|MGlobal]` | Variables to kill |
| `exclusive` | `bool` | True for exclusive form |
| `except_list` | `List[str]` | Variables to keep |
| `is_kill_all` | `bool` | True if kills all locals |

### MMergeStatement

Copy variable tree:

```mumps
M ^DEST=^SOURCE
M LOCAL=^GLOBAL(1)
```

| Field | Type | Description |
|-------|------|-------------|
| `destination` | `MVariable\|MGlobal` | Target |
| `source` | `MVariable\|MGlobal` | Source |

---

## Other Statements

### MHangStatement

Pause execution:

```mumps
H 5           ; Hang 5 seconds
H DURATION
```

| Field | Type | Description |
|-------|------|-------------|
| `duration` | `Optional[MExpr]` | Seconds to pause |

### MHaltStatement

Terminate execution:

```mumps
H             ; Argumentless - halt
HALT
```

No additional fields.

### MBreakStatement

Enter debugger:

```mumps
B
BREAK
```

No additional fields.

### MXecuteStatement

Runtime code execution:

```mumps
X "SET X=1"
X CODE
X EXPR1,EXPR2:COND
```

| Field | Type | Description |
|-------|------|-------------|
| `code_expressions` | `List[MExpr]` | Code to execute |
| `requires_runtime_eval` | `bool` | Always True |
| `is_constant` | `bool` | True if all string literals |
| `constant_values` | `List[str]` | Values if constant |

### MLockStatement

Resource locking:

```mumps
L ^GLOBAL
L +^GLOBAL        ; Incremental lock
L -^GLOBAL        ; Decremental unlock
L ^GLOBAL:5       ; With timeout
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List` | Lock targets |
| `lock_type` | `str` | `""`, `"+"`, or `"-"` |
| `timeout` | `Optional[MExpr]` | Timeout seconds |

### MViewStatement

Implementation-specific:

```mumps
V "STATUS"
VIEW expr
```

| Field | Type | Description |
|-------|------|-------------|
| `keyword` | `Optional[MExpr]` | View keyword |
| `arguments` | `List[MExpr]` | Additional args |

### I/O Device Statements

**MOpenStatement**: Open device

```mumps
O device
O device:params:timeout
```

**MCloseStatement**: Close device

```mumps
C device
C device:params
```

**MUseStatement**: Select current device

```mumps
U device
U device:params
```

**MJobStatement**: Start concurrent job

```mumps
J label^routine
J label:params:timeout
```

| Field | Type | Description |
|-------|------|-------------|
| `device_expr` / `call` | `MExpr` / `MCall` | Device or call target |
| `parameters` | `List[MExpr]` | Device parameters |
| `timeout` | `Optional[MExpr]` | Timeout (OPEN, JOB) |

---

## Statement Type Summary

| Category | Statements |
|----------|------------|
| Assignment | `MSetStatement` |
| I/O | `MWriteStatement`, `MReadStatement` |
| Conditional | `MIfStatement`, `MElseStatement` |
| Loops | `MForStatement` |
| Jumps | `MGotoStatement`, `MQuitStatement` |
| Subroutines | `MDoStatement`, `MDoBlockStatement` |
| Variables | `MNewStatement`, `MKillStatement`, `MMergeStatement` |
| Control | `MHangStatement`, `MHaltStatement`, `MBreakStatement` |
| Dynamic | `MXecuteStatement` |
| Resources | `MLockStatement`, `MViewStatement` |
| Devices | `MOpenStatement`, `MCloseStatement`, `MUseStatement`, `MJobStatement` |
