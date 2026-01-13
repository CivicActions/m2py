# Research: Computed Offsets & Line Dispatch

**Created**: 2026-01-12  
**Status**: Complete

## Research Questions

### R1: Parser Infrastructure for Offset Expressions

**Question**: Does the parser correctly capture offset expressions in `MCall.offset`?

**Finding**: ✅ **YES - Parser fully supports offsets**

Verified via ASG dump that `MCall.offset` captures:
- Literal integers: `G STAR+2` → `NumericLiteral(2)`
- Variables: `G STAR+N` → `LocalVariable('N')`  
- Arithmetic: `G STAR+A-B` → `MBinaryOp('-', LocalVariable('A'), LocalVariable('B'))`
- Chained: `G STAR+1+1` → `MBinaryOp('+', MBinaryOp('+', ...), NumericLiteral(1))`

**Evidence**: 
```python
# From parser testing
call = ast.labels[0].body.statements[0].targets[0]  # MCall from G STAR+2
assert call.offset == NumericLiteral(2)
assert call.call_type == CallType.OFFSET_CALL
```

**Decision**: No parser changes needed. This spec is codegen-only.

---

### R2: Statement Line Number Population

**Question**: Are statement line numbers correctly populated by the parser?

**Finding**: ✅ **YES - Line numbers already populated**

The parser's `_set_line_number_recursive()` function in [parser.py](../../src/m2py/parser/parser.py) sets `line_number` on all statements during parsing. This was verified by dumping the ASG and checking `MStatement.line_number` values.

**Evidence**:
- `MLabel.line_number` - 1-indexed source line of label definition
- `MStatement.line_number` - Set recursively for all statements in label bodies
- `MRoutine.source_lines` - Original source stored for $TEXT support

**Decision**: No parser enhancement needed. Use existing line numbers directly.

---

### R3: Current GOTO Codegen Behavior

**Question**: How does the current codegen handle offset calls?

**Finding**: ⚠️ **Offsets are IGNORED**

The current `_generate_single_target_goto()` in [statements.py](../../src/m2py/codegen/statements.py) only uses `target.name` - it completely ignores `target.offset`:

```python
# Current code (line ~1050)
if ctx.strategy == GotoStrategy.TRAMPOLINE:
    ctx.emitter.line(f'return ("{target.name}", state)')
```

For `G STAR+2`, this generates `return ("STAR", state)` which jumps to STAR's first line, not STAR+2.

**Decision**: Modify codegen to detect offset presence and emit line-based dispatch.

---

### R4: Trampoline Pattern Extension

**Question**: How should the trampoline pattern be extended for line-based dispatch?

**Finding**: Extend dispatcher to accept either label name (string) OR line number (int)

**Current Pattern** (Spec 006):
```python
_labels = {"TEST": _TEST, "NEXT": _NEXT}

def TEST():
    state = RoutineState()
    label = "TEST"
    while label is not None:
        func = _labels[label]
        label, state = func(state)
```

**Extended Pattern** (Spec 007):
```python
_labels = {"TEST": _TEST, "NEXT": _NEXT}
_line_map = {
    1: ("TEST", 0),   # Line 1 → label TEST, offset 0
    2: ("TEST", 1),   # Line 2 → label TEST, offset 1
    5: ("NEXT", 0),   # Line 5 → label NEXT, offset 0
}

def TEST():
    state = RoutineState()
    target = "TEST"  # Can be str (label) or int (line number)
    while target is not None:
        if isinstance(target, int):
            label, offset = _line_map[target]
            func = _labels[label]
            target, state = func(state, _start_offset=offset)
        else:
            func = _labels[target]
            target, state = func(state)
```

**Alternative Considered**: Generate per-line entry functions (`_line_1`, `_line_3`, etc.)
- Rejected: Would create many small functions, harder to debug
- Rejected: Doesn't match trampoline pattern established in Spec 006

**Decision**: Use line map to resolve line → (label, offset), then dispatch to label with offset parameter.

---

### R5: YDB Offset Semantics Validation

**Question**: What are the exact MUMPS semantics for offsets?

**Findings**: All validated against YDB docker:

| Pattern | MUMPS | YDB Output | Notes |
|---------|-------|------------|-------|
| `G STAR+0` | Offset 0 | Executes STAR's line | 0-indexed from label |
| `G STAR+2` | Offset 2 | Skips 2 lines from STAR | |
| `G STAR+N` | Variable | Evaluates N at runtime | |
| `G STAR+A-B` | Arithmetic | Evaluates expression | Left-to-right |
| `G STAR+1+1` | Chained | Equals +2 | |
| `G STAR+6/3` | Division | Equals +2 | |
| `G STAR+2.7` | Float | Truncates to +2 | floor toward zero |
| `G STAR+100` | Invalid | Error: "Entry point STAR+100 not valid" | |
| `G STAR+1` (comment) | Non-exec | Continues to next executable | Skips comments/blanks |

**Decision**: Implement all these semantics. Error handling for invalid offsets is P2 priority.

---

### R6: Line Map Generation Strategy

**Question**: How to generate the `_line_map` efficiently?

**Finding**: Build during routine generation by iterating labels and their statements

**Algorithm**:
```python
def _generate_line_map(routine: MRoutine) -> Dict[int, Tuple[str, int]]:
    """Build line → (label_name, offset_within_label) mapping."""
    line_map = {}
    for label in routine.labels:
        label_line = label.line_number
        line_map[label_line] = (label.name, 0)  # Label line itself
        
        if label.body:
            for i, stmt in enumerate(label.body.statements, start=1):
                stmt_line = stmt.line_number
                line_map[stmt_line] = (label.name, i)  # Offset from label
    
    return line_map
```

**Non-executable Lines**: Comments and blank lines are NOT in line_map. If offset lands on them:
1. Check if target_line is in line_map
2. If not, find next executable line (first line > target_line in line_map)
3. If no next line exists, raise error

**Decision**: Generate line_map in `RoutineGenerator._generate_preamble()` for TRAMPOLINE strategy.

---

### R7: Offset Expression Evaluation

**Question**: How to evaluate offset expressions at runtime?

**Finding**: Use existing expression codegen to generate Python expression for offset

**Approach**: The offset is an `MExpr`. Use `generate_expr(target.offset, ctx)` to emit Python code that evaluates to the offset value at runtime:

```python
# For G STAR+2
target_line = 5 + 2  # label_line + literal

# For G STAR+N  
target_line = 5 + int(m_num(N))  # label_line + variable

# For G STAR+A-B
target_line = 5 + int(m_num(A) - m_num(B))  # label_line + expression
```

**Coercion**: Wrap result in `int()` for MUMPS integer truncation semantics.

**Decision**: Use existing `generate_expr()` plus `int()` wrapper for offset evaluation.

---

## Summary

All research questions answered. Key findings:

1. **Parser is complete** - No parser changes needed
2. **Line numbers exist** - Statement line numbers already populated  
3. **Codegen ignores offsets** - Must modify GOTO generation
4. **Trampoline extension** - Add `_line_map` and line-based dispatch
5. **YDB semantics clear** - All edge cases documented
6. **Line map algorithm** - Iterate labels/statements, build mapping
7. **Offset evaluation** - Use existing `generate_expr()` + `int()` wrapper

**No NEEDS CLARIFICATION items remaining.**
