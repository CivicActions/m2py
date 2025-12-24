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

| Field | Type | Meaning |
|-------|------|---------|
| `loop_var_modified_in_body` | `bool` | Loop variable SET within body |
| `has_internal_quit` | `bool` | QUIT statement in body (not in nested FORs) |

### Combined with GOTO Analysis

From `classify_gotos()`:

| Field | Type | Meaning |
|-------|------|---------|
| `has_internal_goto` | `bool` | GOTO that exits this loop |
| `exit_points` | `List[MGotoStatement]` | GOTOs that exit this loop |

## Loop Variable Modification Detection

The analyzer checks if the loop variable appears as a SET target:

```mumps
F I=1:1:10 D
. S I=I+5        ; loop_var_modified_in_body = True
. D SOMETHING
```

This affects code generation because Python `for` loops don't allow modifying the loop variable.

### Detection Rules

```mumps
F I=1:1:10 D
. S I=20         ; Direct modification → True
. S X=I          ; Read only → False
. S ^DATA(I)=X   ; Subscript only → False
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

The `loop_type` enum (set during parsing) combines with analysis:

| ForLoopType | Example | Python Pattern |
|-------------|---------|----------------|
| `INFINITE` | `F  D` | `while True:` |
| `SINGLE_VALUE` | `F I=5 D` | Single iteration |
| `SIMPLE_RANGE` | `F I=1:1:10 D` | `for i in range()` |
| `STEP_RANGE` | `F I=1:2:10 D` | `for i in range()` with step |
| `INDEFINITE` | `F I=1:1 D` | `while` or itertools |
| `MULTI_RANGE` | `F I=1:1:3,5:1:7 D` | Chained iterators |

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
loop_type = SIMPLE_RANGE
has_internal_quit = True
loop_var_modified_in_body = True
has_internal_goto = True
exit_points = [MGotoStatement(targets=[MCall(name="DONE")])]
```

This loop requires a `while` construct with both `break` and cross-label handling.
