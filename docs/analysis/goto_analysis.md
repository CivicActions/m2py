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
| `FORWARD_JUMP` | Jumps ahead (any label) | If/elif chain or function call |
| `BACKWARD_JUMP` | Jumps to earlier position | Loop or recursive call |
| `LOOP_EXIT` | Exits a single FOR loop | `break` statement |
| `MULTI_LOOP_EXIT` | Exits nested FOR loops | Labeled break or exception |
| `EXTERNAL` | Jumps to other routine | Cross-module call |
| `UNRESOLVED` | Target not found | Runtime dispatch |

### is_cross_label Flag

The `is_cross_label` boolean field on `MGotoStatement` indicates whether the target is in a different label than the source. This is orthogonal to direction:

- **`FORWARD_JUMP` + `is_cross_label=False`**: Intra-label forward jump (e.g., `G LABEL+n` with offset ahead). Can be translated to if/elif chains.
- **`BACKWARD_JUMP` + `is_cross_label=False`**: Intra-label backward jump (e.g., `G LABEL` without offset, or `G LABEL+n` with offset behind). Creates implicit loop.
- **`FORWARD_JUMP` + `is_cross_label=True`**: Cross-label forward jump to a later label. Typically requires converting labels to functions.
- **`BACKWARD_JUMP` + `is_cross_label=True`**: Cross-label backward jump to an earlier label. Creates implicit loop requiring state machine.
- **`LOOP_EXIT` + `is_cross_label=True`**: Exit FOR and jump to different label. Requires break + dispatch.

## What Gets Populated

### On MGotoStatement

```python
@dataclass
class MGotoStatement(MStatement):
    targets: List[MCall]
    postcondition: Optional[MExpr]
    goto_type: GotoType = GotoType.FORWARD_JUMP
    is_cross_label: bool = False  # True if target in different label
    exits_loops: List[MForStatement] = field(default_factory=list)
    target_stmt_index: Optional[int] = None  # For intra-label forward restructuring
    
    # Pre-computed codegen hints
    is_restructurable: bool = False  # True if can become if/else
    codegen_pattern: Optional[GotoCodegenPattern] = None  # Pattern for codegen
```

**Note**: There is no `is_loop_continue` field. Per MDC 3.6.5, GOTO terminates all enclosing FOR loops—it cannot create Python `continue` semantics.

### is_restructurable Field

The `is_restructurable` boolean indicates whether a GOTO can be restructured to an
if/else block instead of requiring function calls or other patterns. This is set to
`True` when:
- `goto_type == FORWARD_JUMP`
- `is_cross_label == False` (intra-label forward jump)

This field is populated by `_compute_codegen_fields()` during `classify_gotos()`.

### codegen_pattern Field

The `codegen_pattern` field (type `GotoCodegenPattern`) provides a pre-computed hint
for code generation. This eliminates pattern computation at codegen time:

| Pattern | When Set | Python Code |
|---------|----------|-------------|
| `BREAK` | Single loop exit | `break` |
| `MULTI_BREAK` | Exits 2+ nested FOR loops | `raise LoopExit()` |
| `FORWARD` | Intra-label forward (`is_restructurable=True`) | if/else restructuring |
| `FUNCTION_CALL` | Cross-label forward jump | `label_func(); return` |
| `UNSUPPORTED` | External, unresolved, or backward | Error/limitation |

This field is populated by `_compute_codegen_fields()` during `classify_gotos()`.

### target_stmt_index

For intra-label forward GOTOs (`is_cross_label=False`, `goto_type=FORWARD_JUMP`), this field
contains the index of the target statement in the label body. Used by code generation to
restructure the GOTO to an if/else block.

**MUMPS Offset Semantics**: `LABEL+n` targets line n from LABEL (0-indexed).
For example, `G TEST+4` from TEST at line 1 targets line 5.

The value is computed by `_find_stmt_index_for_line()` which maps the target line number
to a statement index in the label body.

### On MIfStatement

```python
@dataclass
class MIfStatement(MStatement):
    # Back-reference for intra-label forward GOTO restructuring
    restructurable_goto: Optional[MGotoStatement] = None
```

The `restructurable_goto` field provides a direct back-reference from an IF statement to
the restructurable GOTO inside its then-branch. This allows code generation to quickly find
the GOTO without scanning the IF body.

**When set**: The field is populated by `_compute_codegen_fields()` during `classify_gotos()`
when a GOTO with `is_restructurable=True` is found inside an IF statement's then-scope.

### On MForStatement (back-references and codegen hints)

```python
@dataclass
class MForStatement(MStatement):
    # Back-references
    has_internal_goto: bool = False
    exit_points: List[MGotoStatement] = field(default_factory=list)
    
    # Pre-computed codegen hints
    has_cross_label_exit: bool = False  # Exit GOTO targets different label
    needs_exception_wrapper: bool = False  # Outermost FOR for multi-loop exit
    exit_target: Optional[str] = None  # Target label name (MUMPS name)
```

The codegen hint fields are populated during `classify_gotos()` to avoid recomputing
this information during code generation. The `exit_target` stores the raw MUMPS name;
code generation translates it to a valid Python identifier when needed.

## Classification Logic

### Position-Based Classification

```mumps
EARLY  ; Position 0
       S X=1
MIDDLE ; Position 1
       G EARLY    ; BACKWARD_JUMP, is_cross_label=True (1 → 0)
       G LATER    ; FORWARD_JUMP, is_cross_label=True (1 → 2)
       G MIDDLE   ; BACKWARD_JUMP, is_cross_label=False (same label, no offset = backward to start)
       G MIDDLE+3 ; FORWARD_JUMP, is_cross_label=False (same label, offset ahead)
LATER  ; Position 2
       Q
```

The analyzer builds a label position map and compares indices.

**Intra-Label Jumps** (`is_cross_label=False`): When GOTO targets the same label it's contained in:

- **Without offset** (`G LABEL`): Always `BACKWARD_JUMP` - jumps to start of label, creating an implicit loop
- **With offset** (`G LABEL+n`): Direction depends on whether offset `n` is ahead or behind current position
  - If line number info available: Compare target offset vs GOTO position
  - If line number unavailable: Defaults to `FORWARD_JUMP` (conservative assumption)

The `is_cross_label=False` flag indicates the jump stays within local scope.

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

**Note**: GOTO always terminates enclosing FOR loops per MDC 3.6.5. There is no `continue` pattern—GOTO cannot skip to the next loop iteration.

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
