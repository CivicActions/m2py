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
| `conditions` | `List[MExpr]` | All conditions (comma-separated AND) |
| `condition` | `Optional[MExpr]` | Convenience: first condition (set when `len(conditions) == 1`) |
| `then_scope` | `MScope` | Commands to execute if true |

**Important**: Always use `conditions` (plural) for iteration. The `condition` field is a convenience accessor set only when there's exactly one condition.

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
| `has_internal_goto` | `bool` | GOTO inside loop body |
| `exit_points` | `List[MStatement]` | Exit statements (QUIT/GOTO) |
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
| `goto_type` | `GotoType` | Direction/behavior classification |
| `exits_loops` | `List[MForStatement]` | FOR loops exited |
| `is_cross_label` | `bool` | True if target is in a different label |
| `is_loop_continue` | `bool` | True if GOTO simulates `continue` |

**is_cross_label**: Set to True when the GOTO target is in a different label than the GOTO source. This is orthogonal to the direction (forward/backward) and loop-exit status. Code generators can use this to determine whether simple if/else suffices or function-call-based control flow is needed.

**is_loop_continue**: Set to True when a GOTO inside a FOR loop jumps back to the label containing that FOR loop. This pattern is equivalent to Python's `continue` statement - it exits the current iteration and starts the next one.

**GotoType values**:
- `FORWARD_JUMP` - Jump ahead (check `is_cross_label` for scope)
- `BACKWARD_JUMP` - Jump back (creates loop)
- `LOOP_EXIT` - Exits single FOR loop
- `MULTI_LOOP_EXIT` - Exits multiple nested FORs
- `EXTERNAL` - Jumps to external routine
- `UNRESOLVED` - Cannot determine statically
- `CROSS_LABEL` - **Deprecated**: use `is_cross_label` flag instead

**Code Generation by goto_type + is_cross_label**:
- `LOOP_EXIT` with `is_loop_continue=True`: `continue`
- `LOOP_EXIT` with `is_loop_continue=False`: `break`
- `MULTI_LOOP_EXIT`: Exception or state machine
- `FORWARD_JUMP` + `is_cross_label=False`: If/elif chain
- `FORWARD_JUMP` + `is_cross_label=True`: Function call with return
- `BACKWARD_JUMP`: While loop wrapper

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
| `exits_do_block` | `Optional[MDoStatement]` | Argumentless DO block being exited |

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
K (X,Y,Z),(X,W) ; Multiple exclusive groups - keep intersection
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List[MVariable\|MGlobal\|MIndirection]` | Variables to kill |
| `exclusive` | `bool` | True for exclusive form |
| `except_list` | `List[str]` | Computed intersection of all exclusive groups |
| `except_groups` | `List[List[str]]` | Raw exclusive groups before intersection |
| `is_kill_all` | `bool` (property) | True if kills all locals |

**Multiple Exclusive Groups**: When multiple exclusive groups are present (e.g., `K (X,Y,Z),(X,W)`), only variables appearing in ALL groups are kept (intersection). The `except_groups` field stores the raw groups `[['X','Y','Z'],['X','W']]`, while `except_list` stores the computed intersection `['X']`.

### MMergeStatement

Copy variable tree. Supports multiple merge pairs per MUMPS 1995 specification:

```mumps
M ^DEST=^SOURCE
M LOCAL=^GLOBAL(1)
M X=Y,Z=W           ; Multiple merge pairs
```

| Field | Type | Description |
|-------|------|-------------|
| `merges` | `List[MMergePair]` | List of destination=source pairs |
| `destination` | `Any` (property) | Backward-compat: first pair's destination |
| `source` | `Any` (property) | Backward-compat: first pair's source |

**MMergePair** structure:

| Field | Type | Description |
|-------|------|-------------|
| `destination` | `MVariable\|MGlobal` | Target |
| `source` | `MVariable\|MGlobal` | Source |

**Example**: `M X=Y,Z=W` produces:
```python
stmt.merges = [
    MMergePair(destination=MVariable('X'), source=MVariable('Y')),
    MMergePair(destination=MVariable('Z'), source=MVariable('W'))
]
```

---

## Other Statements

### MHangStatement

Pause execution:

```mumps
H 5           ; Hang 5 seconds
HANG DURATION
```

| Field | Type | Description |
|-------|------|-------------|
| `duration` | `Optional[MExpr]` | Seconds to pause |

**Note**: `H` alone (without argument) is HALT, not HANG. See MHaltStatement.

### MHaltStatement

Terminate execution:

```mumps
H             ; Argumentless H = halt
HALT
```

No additional fields.

**Note**: Per MUMPS spec, `H` and `HALT` share the same abbreviation. The grammar distinguishes them by argument presence:
- `H` (no argument) → HALT (terminate)
- `H 5` (with argument) → HANG (pause 5 seconds)

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
| `targets` | `List[dict]` | Lock target dicts with keys: `target`/`indirection`, `timeout`, `postcondition`, `indirection_levels` |
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

All I/O device statements support multiple devices per MUMPS 1995 specification.

**MOpenStatement**: Open one or more devices

```mumps
O device
O device:params:timeout
O DEV1,DEV2             ; Multiple devices
O DEV1:("A"):5,DEV2     ; Multiple with params
```

| Field | Type | Description |
|-------|------|-------------|
| `devices` | `List[MOpenDevice]` | List of devices to open |
| `device_expr` | `MExpr` (property) | Backward-compat: first device |
| `parameters` | `List[MExpr]` (property) | Backward-compat: first device params |
| `timeout` | `MExpr` (property) | Backward-compat: first device timeout |

**MOpenDevice** structure:

| Field | Type | Description |
|-------|------|-------------|
| `device_expr` | `MExpr` | Device expression |
| `parameters` | `List[MExpr]` | Device parameters |
| `timeout` | `Optional[MExpr]` | Timeout in seconds |

**MCloseStatement**: Close one or more devices

```mumps
C device
C device:(params)
C DEV1,DEV2             ; Multiple devices
```

| Field | Type | Description |
|-------|------|-------------|
| `devices` | `List[MCloseDevice]` | List of devices to close |
| `device_expr` | `MExpr` (property) | Backward-compat: first device |
| `parameters` | `List[MExpr]` (property) | Backward-compat: first device params |

**MCloseDevice** structure:

| Field | Type | Description |
|-------|------|-------------|
| `device_expr` | `MExpr` | Device expression |
| `parameters` | `List[MExpr]` | Device parameters |

**MUseStatement**: Select one or more devices as current

```mumps
U device
U device:(params)
U DEV1,DEV2             ; Multiple devices
```

| Field | Type | Description |
|-------|------|-------------|
| `devices` | `List[MUseDevice]` | List of devices |
| `device_expr` | `MExpr` (property) | Backward-compat: first device |
| `parameters` | `List[MExpr]` (property) | Backward-compat: first device params |

**MUseDevice** structure:

| Field | Type | Description |
|-------|------|-------------|
| `device_expr` | `MExpr` | Device expression |
| `parameters` | `List[MExpr]` | Device parameters |

**MJobStatement**: Start one or more concurrent jobs

```mumps
J label^routine
J label:params:timeout
J LABEL1,LABEL2         ; Multiple targets
J @VAR                   ; Indirection
J @VAR^@ROUTINE          ; Full indirection
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List[MCall]` | List of job targets |
| `calls` | `List[MCall]` (property) | Deprecated alias for `targets` |
| `call` | `MCall` (property) | Backward-compat: first target |
| `parameters` | `List[MExpr]` | Process parameters |
| `timeout` | `Optional[MExpr]` | Timeout in seconds |

**Note**: The `targets` field aligns with `MDoStatement.targets` and `MGotoStatement.targets` for consistency. The `calls` property is a deprecated alias maintained for backward compatibility.

**Indirection Support**: MJobStatement supports both direct labels and indirection (J @VAR). When indirection is used, the corresponding MCall will have:
- `label_is_indirect = True`
- `indirection` set to the indirection expression (e.g., MVariable)

---

## Statement Type Summary

| Category | Statements |
|----------|------------|
| Assignment | `MSetStatement` |
| I/O | `MWriteStatement`, `MReadStatement` |
| Conditional | `MIfStatement`, `MElseStatement` |
| Loops | `MForStatement` |
| Jumps | `MGotoStatement`, `MQuitStatement` |
| Subroutines | `MDoStatement` |
| Variables | `MNewStatement`, `MKillStatement`, `MMergeStatement` |
| Control | `MHangStatement`, `MHaltStatement`, `MBreakStatement` |
| Dynamic | `MXecuteStatement` |
| Resources | `MLockStatement`, `MViewStatement` |
| Devices | `MOpenStatement`, `MCloseStatement`, `MUseStatement`, `MJobStatement` |
