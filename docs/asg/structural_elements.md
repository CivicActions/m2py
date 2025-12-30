# ASG Structural Elements

This document describes the core structural elements of the ASG: `MRoutine`, `MLabel`, `MScope`, and `MCall`.

## ASGElement Base Class

All ASG nodes inherit from `ASGElement`:

```python
@dataclass
class ASGElement(ABC):
    # Source tracking
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    # Tree structure
    parent: Optional["ASGElement"] = None

    def to_dict(self, include_position=False, max_depth=10) -> dict:
        """Serialize to dictionary for debugging/JSON output."""
```

**Note**: textX automatically adds `_tx_position` and `_tx_position_end` attributes
to parsed objects at runtime. We use our own source tracking fields (`line_number`,
`column`, etc.) which provide line/column information rather than absolute byte offsets.

**Source**: [`src/m2py/asg/elements.py`](../../src/m2py/asg/elements.py)

## MRoutine

The top-level container for a MUMPS routine (source file).

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Routine name (from filename) |
| `labels` | `List[MLabel]` | All labels in the routine |
| `source_lines` | `List[str]` | Original source lines (for `$TEXT`) |
| `has_unstructured_goto` | `bool` | True if has cross-label GOTOs |
| `requires_runtime_eval` | `bool` | True if has unresolvable indirection |
| `global_refs` | `List[str]` | All global variable names referenced (populated by `resolve_references()`) |

### Methods

```python
def get_label(self, name: str) -> Optional[MLabel]:
    """Look up label by name."""

def add_label(self, label: MLabel) -> None:
    """Add a label, setting parent reference."""

def get_text_line(self, line_number: int) -> str:
    """Get source line by 1-indexed line number (for $TEXT(+n))."""

def get_text_at_label(self, label_name: str, offset: int = 0) -> str:
    """Get source line by label+offset (for $TEXT(label+n))."""
```

### Code Generation Implications

- **`source_lines`**: Required for `$TEXT` function support. Store original source to return at runtime.
- **`has_unstructured_goto`**: If True, may need state machine or exception-based control flow. Set automatically by `classify_gotos()` when cross-label jumps, backward jumps, or unresolved GOTOs are detected.
- **`requires_runtime_eval`**: If True, cannot generate purely static Python; need runtime variable lookup. Set automatically by `compute_all_signatures()` - True if ANY label in the routine has XECUTE statements or indirected calls (D @VAR, G @VAR).
- **`global_refs`**: List of global variable names (without `^` prefix) referenced in the routine. Populated by `resolve_references()`. Useful for generating global declarations or imports at the top of generated Python modules.

### Example

```python
# Parse a routine
parser = MUMPSParser()
routine = parser.parse_file("MYROUTINE.m")

print(f"Routine: {routine.name}")
print(f"Labels: {[label.name for label in routine.labels]}")
print(f"Source lines: {len(routine.source_lines)}")
```

---

## MLabel

An entry point (subroutine) within a routine.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Label name |
| `formal_list` | `List[str]` | Formal parameter names |
| `body` | `MScope` | Statement container |

**Back-references** (populated by resolver):

| Field | Type | Description |
|-------|------|-------------|
| `callers` | `List[MCall]` | All DO calls to this label |
| `goto_sources` | `List[MGotoStatement]` | All GOTOs targeting this label |

**Variable analysis** (populated by `analyze_variables`):

| Field | Type | Description |
|-------|------|-------------|
| `variables_read` | `set` | Variables read in this label |
| `variables_written` | `set` | Variables written in this label |
| `variables_newed` | `set` | Variables NEW'd in this label |
| `input_variables` | `set` | Variables read before written (inputs) |
| `output_variables` | `set` | Variables written (outputs) |
| `signature` | `FunctionSignature` | Complete function signature |

### Properties

```python
@property
def has_explicit_exit(self) -> bool:
    """True if label ends with QUIT, GOTO, or HALT without postcondition."""
```

### Code Generation Implications

- **`formal_list`**: Maps to Python function parameters
- **`input_variables`**: Additional parameters needed beyond formal_list
- **`output_variables`**: Values that should be returned or passed by reference
- **`signature.scope_strategy`**: Determines code generation approach:
  - `PURE_FUNCTION`: Clean Python function
  - `FUNCTION_WITH_OUTPUTS`: Returns tuple
  - `SUBROUTINE`: Returns None
  - `REQUIRES_RUNTIME`: Needs runtime support

### Example

```python
for label in routine.labels:
    print(f"Label: {label.name}")
    print(f"  Params: {label.formal_list}")
    print(f"  Callers: {len(label.callers)}")
    print(f"  Inputs: {label.input_variables}")
    print(f"  Outputs: {label.output_variables}")
```

---

## MScope

A container for statements with support for recursive walking.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `statements` | `List[MStatement]` | Ordered statements |

### Methods

```python
def add_statement(self, stmt: MStatement) -> None:
    """Add statement, setting parent references."""

def walk_statements(self) -> Iterator[MStatement]:
    """Yield all statements recursively, including nested scopes."""
```

### Scope Nesting

Scopes can be nested:

```
Label body scope
├── MIfStatement
│   └── then_scope: MScope
│       ├── MSetStatement
│       └── MForStatement
│           └── body: MScope
│               └── MWriteStatement
└── MDoStatement (argumentless)
    └── body: MScope
        └── ...
```

### Code Generation Implications

- `walk_statements()` provides a flat iteration over all statements
- Use `stmt.parent` to navigate up the ASG tree for enclosing context
- Use `stmt.scope` to access the containing MScope

### Example

```python
# Walk all statements in a label
for stmt in label.body.walk_statements():
    print(f"{stmt.__class__.__name__} at line {stmt.line_number}")

# Count statement types
from collections import Counter
types = Counter(type(s).__name__ for s in label.body.walk_statements())
```

---

## MCall

A reference to a label (for DO, GOTO, or extrinsic functions).

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | `str` | Target label name |
| `offset` | `Optional[MExpr]` | Offset for `label+n` |
| `routine` | `Optional[str]` | Routine name for `^routine` |
| `arguments` | `List[MActualParameter]` | Call arguments (with passing mode) |
| `postcondition` | `Optional[MExpr]` | Conditional execution |
| `indirection` | `Optional[MExpr]` | For `@expr` label indirection |
| `routine_indirection` | `Optional[MExpr]` | For `^@expr` routine indirection |

**Indirection flags**:

| Field | Type | Description |
|-------|------|-------------|
| `label_is_indirect` | `bool` | Label from indirection |
| `routine_is_indirect` | `bool` | Routine from indirection |
| `indirection_levels` | `int` | Number of `@` levels |

**Resolution** (populated by resolver):

| Field | Type | Description |
|-------|------|-------------|
| `target` | `Optional[MLabel]` | Resolved target label |
| `call_type` | `CallType` | Classification |
| `is_resolved` | `bool` | True if successfully resolved |

### CallType Values

| Value | Description | Example |
|-------|-------------|---------|
| `LABEL_CALL` | Simple label | `D LABEL` |
| `OFFSET_CALL` | Label with offset | `D LABEL+2` |
| `ROUTINE_CALL` | External routine | `D LABEL^ROUTINE` |
| `INDIRECT_CALL` | Indirect call | `D @CMD` |
| `UNRESOLVED` | Cannot determine | Dynamic target |

### Code Generation Implications

- **`LABEL_CALL`**: Direct Python function call
- **`ROUTINE_CALL`**: Import and call from another module
- **`OFFSET_CALL`**: Complex - may need source line lookup
- **`INDIRECT_CALL`**: Requires runtime dispatch

### Example

```python
# Find all DO statements
for stmt in label.body.walk_statements():
    if isinstance(stmt, MDoStatement):
        for call in stmt.targets:
            if call.is_resolved:
                print(f"DO {call.name} -> {call.target.name}")
            else:
                print(f"DO {call.name} (unresolved, type={call.call_type})")
```

---

## Relationships

```
MRoutine
    │
    ├── labels ──────────────────────┐
    │                                │
    ▼                                │
MLabel ─────────────────────────────┐│
    │                               ││
    ├── body ─────────────┐         ││
    │                     │         ││
    ├── callers ──────────┼─────────┤│
    │                     │         ││
    └── goto_sources ─────┼─────────┤│
                          │         ││
                          ▼         ││
                       MScope       ││
                          │         ││
                          ├── statements ──┐
                          │                │
                          ▼                ▼
                     MStatement ──────► MCall
                                          │
                                          └──► target: MLabel (back-ref)
```

## Source Code

All structural elements are defined in [`src/m2py/asg/elements.py`](../../src/m2py/asg/elements.py).
