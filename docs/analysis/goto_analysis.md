# GOTO Analysis

The GOTO analyzer classifies GOTO statements and tracks loop exits.

**Source**: [`src/m2py/analysis/goto_analysis.py`](../../src/m2py/analysis/goto_analysis.py)

## Overview

GOTO analysis:

1. Walks all statements looking for `MGotoStatement`
2. Classifies each by target location and context
3. Tracks enclosing FOR loops to detect loop exits
4. Sets `goto_type` and `exits_loops` on statements
5. Sets `has_internal_goto` and populates `exit_points` on FOR statements

## Usage

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")
parser.resolve_references(routine)  # Required first
parser.classify_gotos(routine)      # Then classify

# Check GOTO types
for label in routine.labels:
    for stmt in label.body.walk_statements():
        if isinstance(stmt, MGotoStatement):
            print(f"GOTO: {stmt.goto_type}")
            if stmt.exits_loops:
                print(f"  Exits {len(stmt.exits_loops)} loops")
```

## GotoType Classification

| GotoType | Meaning | Code Gen Approach |
|----------|---------|-------------------|
| `FORWARD_JUMP` | Jumps to later label | May use function call or goto |
| `BACKWARD_JUMP` | Jumps to earlier label | Loop or recursive call |
| `LOOP_EXIT` | Exits a single FOR loop | `break` statement |
| `MULTI_LOOP_EXIT` | Exits nested FOR loops | Labeled break or exception |
| `EXTERNAL` | Jumps to other routine | Cross-module call |
| `UNRESOLVED` | Target not found | Error handling |

## What Gets Populated

### On MGotoStatement

```python
@dataclass
class MGotoStatement(MStatement):
    targets: List[MCall]
    postcondition: Optional[MExpr]
    goto_type: GotoType = GotoType.FORWARD_JUMP
    exits_loops: List[MForStatement] = field(default_factory=list)
```

### On MForStatement (back-references)

```python
@dataclass
class MForStatement(MStatement):
    has_internal_goto: bool = False
    exit_points: List[MGotoStatement] = field(default_factory=list)
```

## Classification Logic

### Position-Based Classification

```mumps
EARLY  ; Position 0
       S X=1
MIDDLE ; Position 1
       G EARLY    ; BACKWARD_JUMP (1 → 0)
       G LATER    ; FORWARD_JUMP (1 → 2)
LATER  ; Position 2
       Q
```

The analyzer builds a label position map and compares indices.

### Loop Exit Detection

```mumps
LOOP   F I=1:1:10 D
       . I X=5 G DONE    ; LOOP_EXIT - exits the FOR
       Q
DONE   Q
```

The analyzer tracks enclosing FOR loops during traversal. When a GOTO is found inside a FOR:
- `goto_type` is set to `LOOP_EXIT` or `MULTI_LOOP_EXIT`
- `exits_loops` is populated with enclosing FORs
- `has_internal_goto` is set on the FOR statements

### External vs Same-Routine

```mumps
       G LABEL^OTHER   ; EXTERNAL (different routine)
       G LABEL^SAME    ; Resolved if SAME matches routine name
       G LABEL         ; Resolved locally
```

## Helper Functions

### get_loop_exiting_gotos

Find all GOTOs that exit FOR loops:

```python
from m2py.analysis.goto_analysis import get_loop_exiting_gotos

exits = get_loop_exiting_gotos(routine)
for goto in exits:
    print(f"GOTO exits {len(goto.exits_loops)} loops")
```

### get_gotos_by_type

Filter GOTOs by classification:

```python
from m2py.analysis.goto_analysis import get_gotos_by_type
from m2py.asg.enums import GotoType

backwards = get_gotos_by_type(routine, GotoType.BACKWARD_JUMP)
for goto in backwards:
    print("Backward jump detected")
```

## Code Generation Implications

| Scenario | Strategy |
|----------|----------|
| Forward to same label | Continue/fallthrough |
| Forward to different label | Function call |
| Backward jump | Loop construct or recursion |
| Single loop exit | `break` |
| Multi-loop exit | Labeled break, exception, or state machine |
| Conditional GOTO | `if condition: break/return` |

### Example Patterns

**Loop Exit to Break**:
```mumps
F I=1:1:10 D
. I X=5 G DONE
```
```python
for i in range(1, 11):
    if x == 5:
        break  # LOOP_EXIT becomes break
```

**Multi-Loop Exit**:
```mumps
F I=1:1:10 D
. F J=1:1:10 D
. . I X=Y G ALLDONE
```
```python
# Requires special handling - exception or flag pattern
class LoopExit(Exception): pass
try:
    for i in range(1, 11):
        for j in range(1, 11):
            if x == y:
                raise LoopExit()
except LoopExit:
    pass
```

## Routine-Level Flag

`classify_gotos()` automatically sets `MRoutine.has_unstructured_goto` based on GOTO patterns in the routine:

```python
# After classify_gotos(), check the flag:
if routine.has_unstructured_goto:
    # Use state machine or other unstructured approach
    pass
else:
    # Can use structured Python (if/else, break, function calls)
    pass
```

**Patterns that set the flag to True:**
- `BACKWARD_JUMP`: Creates implicit loops across labels
- `UNRESOLVED`: Target unknown, needs runtime dispatch
- Cross-label `FORWARD_JUMP` not inside a FOR loop
