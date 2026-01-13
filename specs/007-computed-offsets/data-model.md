# Data Model: Computed Offsets & Line Dispatch

**Created**: 2026-01-12

## Entities

### LineMapEntry

Represents a mapping from source line number to label entry point.

| Field | Type | Description | Validation |
|-------|------|-------------|------------|
| `line_number` | `int` | 1-indexed source line number | Must be > 0 |
| `label_name` | `str` | Name of containing label | Must exist in routine |
| `offset` | `int` | Offset from label (0 = label line) | Must be >= 0 |

**Relationships**:
- Many LineMapEntry → One MLabel
- One MRoutine → Many LineMapEntry

**Notes**: This is a generated Python data structure (`_line_map: Dict[int, Tuple[str, int]]`), not an ASG node.

---

### MCall (Existing - Offset Field)

The `MCall` ASG node already has the offset field populated by the parser.

| Field | Type | Description | Status |
|-------|------|-------------|--------|
| `name` | `str` | Label name | Existing |
| `offset` | `Optional[MExpr]` | Offset expression | **Existing** - populated by parser |
| `call_type` | `CallType` | Classification | `OFFSET_CALL` for offset presence |
| `target` | `Optional[MLabel]` | Resolved label | Existing |

**No changes needed** - read existing fields.

---

### DispatchTarget (Runtime)

At runtime, dispatch targets can be either label names or line numbers.

| Variant | Type | Description |
|---------|------|-------------|
| Label dispatch | `str` | Label name (current pattern) |
| Line dispatch | `int` | Source line number (new pattern) |

**Union type in generated code**: `target: str | int | None`

---

## State Transitions

### Dispatch Flow

```
GOTO with offset
    │
    ├─► Offset = None ──────────► Label dispatch (current pattern)
    │                                return ("LABEL", state)
    │
    └─► Offset = MExpr ──────────► Line dispatch (new pattern)
                                     target_line = label_line + int(offset_expr)
                                     return (target_line, state)

Trampoline dispatcher
    │
    ├─► target is str ───────────► func = _labels[target]
    │                                target, state = func(state)
    │
    └─► target is int ───────────► label, offset = _line_map[target]
                                     func = _labels[label]
                                     target, state = func(state, _start_offset=offset)
```

---

## Generated Code Patterns

### Line Map Generation

```python
# Generated at routine level when routine has offset calls
_line_map = {
    1: ("TEST", 0),   # Line 1: TEST label line
    2: ("TEST", 1),   # Line 2: first statement in TEST
    3: ("TEST", 2),   # Line 3: second statement in TEST
    5: ("NEXT", 0),   # Line 5: NEXT label line
    6: ("NEXT", 1),   # Line 6: first statement in NEXT
}
```

### Extended Trampoline Dispatcher

```python
def TEST():
    """Trampoline dispatcher with line dispatch support."""
    state = RoutineState()
    target: str | int | None = "TEST"
    
    while target is not None:
        if isinstance(target, int):
            # Line-based dispatch
            if target not in _line_map:
                # Find next executable line or raise error
                target = _find_next_executable(target)
            label, offset = _line_map[target]
            func = _labels[label]
            target, state = func(state, _start_offset=offset)
        else:
            # Label-based dispatch (existing pattern)
            func = _labels[target]
            target, state = func(state)
    
    return state
```

### Label Function with Start Offset

```python
def _TEST(state, _start_offset=0) -> Tuple[Optional[str | int], RoutineState]:
    """Label function supporting offset entry."""
    global _test
    
    # Statement 0 (label line): may be skipped if _start_offset > 0
    if _start_offset <= 0:
        # Execute label line commands
        ...
    
    # Statement 1
    if _start_offset <= 1:
        # Execute first statement
        ...
    
    # Statement 2
    if _start_offset <= 2:
        # Execute second statement
        ...
    
    return ("NEXT", state)  # Fall-through to next label
```

### GOTO with Offset Generation

```python
# For: G STAR+2 (literal offset)
return (5 + 2, state)  # label_line + offset

# For: G STAR+N (variable offset)
return (5 + int(m_num(N)), state)

# For: G STAR+A-B (arithmetic offset)
return (5 + int(m_num(A) - m_num(B)), state)
```

---

## Validation Rules

| Rule | Enforced At | Error |
|------|-------------|-------|
| Offset must resolve to non-negative integer | Runtime | ValueError |
| Target line must exist or have next executable | Runtime | "Entry point LABEL+N not valid" |
| Label must exist for offset calculation | Compile (resolution) | Reference error |
| Line map only generated for TRAMPOLINE strategy | Compile | N/A |

---

## Key Design Decisions

### D1: Line Map vs Per-Line Functions

**Decision**: Use `_line_map` dictionary over per-line functions.

**Rationale**:
- Fewer generated functions (1 per label vs 1 per line)
- Easier debugging (label functions match source structure)
- Consistent with trampoline pattern from Spec 006
- `_start_offset` parameter enables entry at any point

### D2: Union Dispatch Target

**Decision**: Dispatcher accepts `str | int | None` as target.

**Rationale**:
- `str` - label name (backward compatible with Spec 006)
- `int` - line number (new offset dispatch)
- `None` - exit routine
- Single dispatcher handles both patterns

### D3: Offset Skip Pattern

**Decision**: Use `if _start_offset <= N:` guards for statements.

**Rationale**:
- Simple, readable generated code
- Each statement has clear skip condition
- Offset=0 executes all, offset=2 skips first two
- No runtime offset tracking complexity

### D4: Non-Executable Line Handling

**Decision**: Skip to next executable line rather than error.

**Rationale**:
- Matches YDB behavior (validated in research)
- Common pattern: offset lands on comment, should continue
- Error only if no executable line exists after target
