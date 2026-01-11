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

**Analysis fields** (populated by `analyze_for_loops` and `classify_gotos`):

| Field | Type | Populated By | Description |
|-------|------|--------------|-------------|
| `loop_type` | `ForLoopType` | `analyze_for_loops` | Classification |
| `is_infinite` | `bool` | `analyze_for_loops` | True for step=0 or ARGUMENTLESS |
| `has_internal_quit` | `bool` | `analyze_for_loops` | QUIT directly in body |
| `has_internal_goto` | `bool` | `classify_gotos` | GOTO inside loop body |
| `exit_points` | `List[MStatement]` | `classify_gotos` | Exit statements (QUIT/GOTO) |
| `loop_var_modified_in_body` | `bool` | `analyze_for_loops` | SET of loop var |
| `has_cross_label_exit` | `bool` | `classify_gotos` | Exit GOTO targets different label |
| `needs_exception_wrapper` | `bool` | `classify_gotos` | Outermost FOR for multi-loop exit |
| `exit_target` | `Optional[str]` | `classify_gotos` | Target label name (MUMPS name) |

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
| `target_stmt_index` | `Optional[int]` | Statement index for intra-label forward restructuring |
| `is_restructurable` | `bool` | True if can be restructured to if/else |
| `codegen_pattern` | `Optional[GotoCodegenPattern]` | Pre-computed pattern for codegen |

**Pre-computed codegen fields** (Phase 14 refactoring):

The `is_restructurable` and `codegen_pattern` fields are populated during analysis
to avoid recomputing at code generation time:

- `is_restructurable`: True when `goto_type=FORWARD_JUMP` and `is_cross_label=False`
- `codegen_pattern`: One of `BREAK`, `MULTI_BREAK`, `FORWARD`, `FUNCTION_CALL`, `UNSUPPORTED`

**target_stmt_index**: For intra-label forward GOTOs (`is_cross_label=False`, `goto_type=FORWARD_JUMP`),
this field contains the index of the target statement in the label body. Computed from MUMPS offset
semantics: `LABEL+n` targets line n from the label. Used by code generation to restructure the GOTO
to an if/else block.

**is_cross_label**: Set to True when the GOTO target is in a different label than the GOTO source. Set to False when the GOTO targets the same label it's contained in (intra-label). Code generators can use this to determine whether simple control flow restructuring suffices or function-call-based control flow is needed.

**MUMPS Semantic Note (MDC 3.6.5)**: GOTO terminates all FOR loops on the line containing the GOTO.
GOTO cannot create Python `continue` semantics. To skip to the next iteration in MUMPS, use
conditional execution (`I cond <commands>`) or QUIT from within a DO block.

**GotoType values**:
- `FORWARD_JUMP` - Jump ahead (intra-label with offset ahead, or cross-label to later label)
- `BACKWARD_JUMP` - Jump back (intra-label without offset, intra-label with offset behind, or cross-label to earlier label)
- `LOOP_EXIT` - Exits single FOR loop
- `MULTI_LOOP_EXIT` - Exits multiple nested FORs
- `EXTERNAL` - Jumps to external routine
- `UNRESOLVED` - Cannot determine statically
- `CROSS_LABEL` - **Deprecated**: use `is_cross_label` flag instead

**Intra-label GOTO classification**:
- `G LABEL` (no offset) from within `LABEL`: Always `BACKWARD_JUMP` - jumps to start of label
- `G LABEL+n` (with offset) from within `LABEL`: `FORWARD_JUMP` if offset ahead, `BACKWARD_JUMP` if offset behind

**Code Generation by goto_type + is_cross_label**:
- `LOOP_EXIT`: `break`
- `MULTI_LOOP_EXIT`: Exception or state machine
- `FORWARD_JUMP` + `is_cross_label=False`: If/elif chain (restructurable)
- `FORWARD_JUMP` + `is_cross_label=True`: Function call with return
- `BACKWARD_JUMP` + `is_cross_label=False`: Implicit loop (deferred to Spec 006)
- `BACKWARD_JUMP` + `is_cross_label=True`: While loop wrapper or state machine

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

Pause execution for specified duration(s):

```mumps
H 5           ; Hang 5 seconds
HANG DURATION
H 0,1,2,3     ; Hang for 0, then 1, then 2, then 3 seconds
H:X>0 5       ; Conditional hang with postcondition
```

| Field | Type | Description |
|-------|------|-------------|
| `duration` | `Optional[MExpr]` | First duration (deprecated, use `durations`) |
| `durations` | `List[MExpr]` | All duration expressions |

**Note**: `H` alone (without argument) is HALT, not HANG. See MHaltStatement.

### MHaltStatement

Terminate execution:

```mumps
H             ; Argumentless H = halt
HALT
H:X           ; Conditional halt with postcondition
```

No additional fields.

**Note**: Per MUMPS spec, `H` and `HALT` share the same abbreviation. The grammar distinguishes them by argument presence:
- `H` (no argument) → HALT (terminate)
- `H:X` (postcondition, no argument) → HALT with postcondition
- `H 5` (with argument) → HANG (pause 5 seconds)
- `H:X>0 5` (postcondition with argument) → HANG with postcondition

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
L +^GLOBAL            ; Incremental lock
L -^GLOBAL            ; Decremental unlock
L ^GLOBAL:5           ; With timeout
L +^A,+^B,+^C         ; Multiple incremental locks
L +^A,-^B,^C          ; Mixed lock types per target
L +(^A,^B,^C)         ; List-level incremental
L -(^A):5             ; List-level decremental with timeout
```

| Field | Type | Description |
|-------|------|-------------|
| `targets` | `List[dict]` | Lock target dicts with keys: `target`/`indirection`, `timeout`, `postcondition`, `indirection_levels`, `lockop` |
| `lock_type` | `str` | `""`, `"+"`, or `"-"` (derived from targets when all have same lockop) |
| `timeout` | `Optional[MExpr]` | Shared timeout for parenthesized list |

Each target dict contains `lockop` with values `""`, `"+"`, or `"-"` for individual lock operations.

### MViewStatement

Implementation-specific per MUMPS 1995 MDC spec section 8.2.24:

```mumps
V "STATUS"
VIEW expr
```

| Field | Type | Description |
|-------|------|-------------|
| `arguments` | `List[MExpr]` | View arguments (implementation-specific) |

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
parameters` | `List[MExpr]` | Process parameters |
| `timeout` | `Optional[MExpr]` | Timeout in seconds |

**Note**: The `targets` field aligns with `MDoStatement.targets` and `MGotoStatement.targets` for consistenc

---

## Transaction Statements

### MTStartStatement

Begin a transaction (MUMPS 1995 spec 8.2.22):

```mumps
TS                  ; Non-restartable transaction
TSTART              ; Full keyword
TS ()               ; Restartable (no variables saved)
TS (X,Y,Z)          ; Restartable, save specified variables on restart
TS *                ; Restartable, save all variables on restart
TS:COND             ; Conditional TSTART
TS (X):SERIAL       ; With parameters
```

| Field | Type | Description |
|-------|------|-------------|
| `restart_vars` | `List[MExpr]` | Variables to restore on TRESTART |
| `restart_all` | `bool` | True if `*` (restore all variables) |
| `parameters` | `List[MExpr]` | Transaction parameters (SERIAL, TRANSACTIONID, etc.) |

**Special Variables**:
- `$TLEVEL` - Transaction nesting level (0 = no transaction)
- `$TRESTART` - Restart counter for current transaction

### MTCommitStatement

Commit the current transaction (MUMPS 1995 spec 8.2.19):

```mumps
TC                  ; Commit
TCOMMIT             ; Full keyword
TC:COND             ; Conditional commit
```

If `$TLEVEL = 1`, commits the transaction. If `$TLEVEL > 1`, decrements nesting level.

### MTRestartStatement

Restart the current transaction (MUMPS 1995 spec 8.2.20):

```mumps
TRE                 ; Restart
TRESTART            ; Full keyword
TRE:COND            ; Conditional restart
```

If in a restartable transaction, performs restart and increments `$TRESTART`.

### MTRollbackStatement

Rollback the current transaction (MUMPS 1995 spec 8.2.21):

```mumps
TRO                 ; Rollback all
TROLLBACK           ; Full keyword
TRO 1               ; Rollback to specified level
TRO:COND            ; Conditional rollback
```

| Field | Type | Description |
|-------|------|-------------|
| `level` | `Optional[MExpr]` | Transaction level to rollback to |

Rolls back all changes since transaction start. Sets `$TLEVEL = 0` and `$TRESTART = 0`.

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
| Transactions | `MTStartStatement`, `MTCommitStatement`, `MTRestartStatement`, `MTRollbackStatement` |
