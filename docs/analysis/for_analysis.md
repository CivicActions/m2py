# FOR Loop Analysis

The FOR loop analyzer detects loop patterns and internal control flow.

**Source**: [`src/m2py/analysis/for_analysis.py`](../../src/m2py/analysis/for_analysis.py)

## Overview

FOR loop analysis:

1. Scans all `MForStatement` nodes in the routine
2. Detects if the loop variable is modified inside the body
3. Detects if QUIT statements are present in the body
4. Sets analysis flags for code generation decisions

## Usage

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")
parser.analyze_for_loops(routine)

# Check loop analysis results
for label in routine.labels:
    for stmt in label.body.walk_statements():
        if isinstance(stmt, MForStatement):
            if stmt.has_internal_quit:
                print("Loop has internal QUIT")
            if stmt.loop_var_modified_in_body:
                print("Loop variable modified in body")
```

## What Gets Analyzed

### MForStatement Fields Populated

| Field | Type | Meaning | Source |
|-------|------|---------|--------|
| `loop_var_modified_in_body` | `bool` | Loop variable SET within body | `for_analysis.py` |
| `has_internal_quit` | `bool` | QUIT statement in body (not in nested FORs) | `for_analysis.py` |
| `loop_type` | `ForLoopType` | Classification of loop structure | Parser/Semantic Analyzer |
| `is_infinite` | `bool` | True for argumentless or step=0 loops | Parser/Semantic Analyzer |

### Combined with GOTO Analysis

From `classify_gotos()`:

| Field | Type | Meaning |
|-------|------|---------|
| `has_internal_goto` | `bool` | GOTO that exits this loop |
| `exit_points` | `List[MGotoStatement]` | GOTOs that exit this loop |

## Loop Variable Modification Detection

The analyzer checks if the loop variable is modified via:

1. **SET command**: `S I=value` - direct assignment
2. **READ command**: `R I` - reading into the variable
3. **KILL command**: `K I` or `K` (kill all) - removing the variable

```mumps
F I=1:1:10 D
. S I=I+5        ; loop_var_modified_in_body = True (SET)
. D SOMETHING

F I=1:1 R I Q:I=0  ; loop_var_modified_in_body = True (READ)

F D="+"... K D Q   ; loop_var_modified_in_body = True (KILL)
```

This affects code generation because Python `for` loops don't allow modifying the loop variable.

### Pass-by-Reference Detection

The analyzer detects when a loop variable is passed by reference to a subroutine,
e.g., `D BLANK(.I)`. When the loop variable is passed by-ref, the analyzer
conservatively assumes it may be modified (since the callee could modify the variable).

```mumps
; Pass-by-reference detection
F I=1:1:30 D BLANK(.I)      ; loop_var_modified_in_body = True (by-ref)
F I=1:1:10 D WORK(.X)       ; loop_var_modified_in_body = False (different var)
F NEXT=1:1 D ITER(.NEXT) Q:NEXT=0  ; loop_var_modified_in_body = True (iterator pattern)
```

> **Note**: Analysis of 33,951 VistA files found:
> - **Pass-by-reference DO** (11 cases): Most significant pattern. Used for iterator patterns where callee sets loop var to 0 to exit. Example: `F NEXT=1:1 D PTNEXT(.NEXT) Q:NEXT=0`. **Now detected.**
> - **KILL** (few real cases): "K D Q" idiom kills loop var to exit early. Example: `F D="+"... I cond K D Q`. **Now detected.**
> - **READ** (3 cases): Rare dynamic loop control via user input. **Now detected.**
> - **MERGE** (0 cases): Not used in practice for loop variable modification.

### Detection Rules

The following modifications are detected:

```mumps
; SET detection
F I=1:1:10 D
. S I=20         ; Direct modification → True
. S X=I          ; Read only → False
. S ^DATA(I)=X   ; Subscript only → False

; READ detection
F I=1:1 R I      ; READ into loop var → True
F I=1:1 R X      ; READ into other var → False

; KILL detection
F I=1:1:10 K I   ; KILL loop var → True
F I=1:1:10 K     ; KILL all → True
F I=1:1:10 K X   ; KILL other var → False

; Pass-by-reference detection
F I=1:1:30 D BLANK(.I)  ; Loop var passed by-ref → True
F I=1:1:10 D WORK(.X)   ; Other var passed by-ref → False
F I=1:1:10 D WORK(I)    ; Loop var passed by-val → False
```

The check also recurses into IF/ELSE blocks:

```mumps
F I=1:1:10 D
. I X=1 S I=I+1  ; Modified in IF → True
```

## Internal QUIT Detection

Detects QUIT statements that would exit the FOR loop:

```mumps
F I=1:1:10 D
. I X=5 Q        ; has_internal_quit = True
. D WORK
```

### QUIT Scoping Rules

QUIT only exits the innermost FOR or subroutine:

```mumps
F I=1:1:10 D
. F J=1:1:5 D
. . I Y=1 Q     ; Exits inner FOR only
. D MORE        ; This still executes after inner Q
```

The analyzer correctly tracks which FOR each QUIT belongs to.

## Code Generation Implications

### Standard Loop (no modifications)

```mumps
F I=1:1:10 D
. W I,!
```
```python
for i in range(1, 11):
    print(i)
```

### Loop with Internal QUIT

```mumps
F I=1:1:10 D
. I X=5 Q
. D WORK
```
```python
for i in range(1, 11):
    if x == 5:
        break
    do_work()
```

### Loop with Variable Modification

When the loop variable is modified, Python's `for` cannot be used directly:

```mumps
F I=1:1:10 D
. S I=I*2
. W I,!
```
```python
# Option 1: While loop
i = 1
while i <= 10:
    i = i * 2
    print(i)
    i = i + 1  # Step from original

# Option 2: Iterator pattern with manual control
```

### Decision Matrix

| has_internal_quit | loop_var_modified | Strategy |
|-------------------|-------------------|----------|
| False | False | Simple `for` loop |
| True | False | `for` with `break` |
| False | True | `while` loop |
| True | True | `while` with `break` |

## ForLoopType Classification

The `loop_type` enum (set during parsing/semantic analysis) combines with analysis:

| ForLoopType | Example | Python Pattern |
|-------------|---------|----------------|
| `ARGUMENTLESS` | `F  D` | `while True:` |
| `STRING_LIST` | `F I=5 D` or `F I="A","B"` | Iteration over values |
| `BOUNDED` | `F I=1:1:10 D` | `for i in range()` |
| `OPEN_ENDED` | `F I=1:1 D` | `while` or itertools |
| `MIXED` | `F I=1:1:3,5:1:7 D` | Chained iterators |

## Example: Complex Loop Analysis

```mumps
LOOP   F I=1:1:100 D
       . S X=$$CALC(I)
       . I X<0 Q              ; has_internal_quit = True
       . I X>50 S I=I+10      ; loop_var_modified_in_body = True
       . I X=99 G DONE        ; has_internal_goto = True
       W "Done",!
       Q
DONE   W "Early exit",!
       Q
```

After analysis:
```
loop_type = BOUNDED
has_internal_quit = True
loop_var_modified_in_body = True
has_internal_goto = True
exit_points = [MGotoStatement(targets=[MCall(name="DONE")])]
```

This loop requires a `while` construct with both `break` and cross-label handling.
