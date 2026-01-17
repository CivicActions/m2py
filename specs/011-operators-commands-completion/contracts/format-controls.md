# Format Controls and Write API Contract

**Spec 011**: Extended Operators, Commands & Completion

## Format Control Types

Format controls are parsed into `MFormatControl` ASG nodes with `control_type` enum.

### FormatControlType Enum

| Value | MUMPS | Description | Argument |
|-------|-------|-------------|----------|
| `NEWLINE` | `!` | Write newline | None |
| `FORMFEED` | `#` | Write form feed | None |
| `TAB` | `?n` | Tab to column n | Expression |
| `CHARCODE` | `*n` | Write ASCII char n | Expression |

## Codegen Patterns

### MWriteStatement Arguments

Write arguments can be:
1. `MExpr` - Expression to write
2. `MFormatControl` - Format control

```python
def _generate_write(stmt: MWriteStatement, ctx: "GeneratorContext") -> None:
    for arg in stmt.arguments:
        if isinstance(arg, MExpr):
            expr = generate_expr(arg, ctx)
            ctx.emitter.line(f"_rt.write({expr})")
        elif isinstance(arg, MFormatControl):
            _generate_format_control(arg, ctx)
```

### Format Control Generation

| Control | Python Output |
|---------|--------------|
| NEWLINE | `_rt.write("\n")` |
| FORMFEED | `_rt.write("\f")` |
| CHARCODE | `_rt.write(chr(int(expr)))` |
| TAB | `_rt.write_tab(int(expr))` |

## Runtime API Extensions

### _rt.write(value)
Write value to current output device.
- Updates `$X` (column position)
- Updates `$Y` on newline

### _rt.write_tab(column)
Tab to specified column.
- If current column < target: write spaces
- If current column >= target: no-op (MUMPS semantics)

### Column/Line Tracking

```python
class MUMPSRuntime:
    def __init__(self):
        self._x = 0  # Current column
        self._y = 0  # Current line
    
    def write(self, value):
        s = str(value)
        for char in s:
            if char == '\n':
                self._x = 0
                self._y += 1
            elif char == '\f':
                self._x = 0
                self._y = 0  # Form feed resets line too
            else:
                self._x += 1
        print(s, end='')
    
    def write_tab(self, column):
        if self._x < column:
            spaces = column - self._x
            self.write(' ' * spaces)
    
    def x(self) -> int:
        return self._x
    
    def y(self) -> int:
        return self._y
```

## Acceptance Criteria

| Input | Expected Output | $X after |
|-------|-----------------|----------|
| `W "ABC"` | `ABC` | 3 |
| `W "A",!` | `A\n` | 0 |
| `W "X",?10,"Y"` | `X         Y` | 11 |
| `W *65,*66` | `AB` | 2 |
| `W #` | `\f` | 0 |
